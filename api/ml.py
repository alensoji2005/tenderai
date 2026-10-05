# api/ml.py
from fastapi import APIRouter, HTTPException, Depends
from api.auth import get_current_user
from pydantic import BaseModel
from typing import Optional
import joblib
import json
import numpy as np
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])

ML_DIR = os.path.join(os.path.dirname(__file__), '..', 'ml')
_cache = {}

def _load(filename):
    """Load a joblib artefact, re-reading it whenever the file changes (e.g. after nightly retraining)."""
    path = os.path.join(ML_DIR, filename)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    cached = _cache.get(filename)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        obj = joblib.load(path)
    except Exception as e:
        logger.warning(f"Failed to load {filename}: {e}")
        return None
    _cache[filename] = (mtime, obj)
    logger.info(f"Loaded {filename}")
    return obj

def get_model():
    return _load('model.pkl')

def get_competitor_model():
    return _load('competitor_model.pkl')

def get_model_mae():
    """Typical error (in margin units) of the margin model on its held-out test set."""
    try:
        with open(os.path.join(ML_DIR, 'model_meta.json')) as f:
            return json.load(f).get('mae')
    except Exception:
        return None

def _bad_request(e):
    if isinstance(e, ValueError):
        return HTTPException(status_code=400, detail=str(e))
    logger.exception("prediction failed")
    return HTTPException(status_code=400, detail="Prediction failed. Check the inputs and try again.")

class BidPredictionRequest(BaseModel):
    tender_id: str
    company_id: int
    proposed_bid_price: float
    estimated_cost: float
    competitor_count: int
    client: str = "Ministry of Health"
    category: str = "Construction"
    title: str = "Maintenance Project"

class OptimalBidRequest(BaseModel):
    title: str
    estimated_value: float
    duration_months: int = 12
    is_sme: bool = True
    entity: str = "Ministry of Health"
    category: str = "Construction"

class P2WRequest(BaseModel):
    base_cost: float
    estimated_value: float
    target_probability: float = 85.0
    title: str
    entity: str = "Ministry of Health"
    category: str = "Construction"
    company_name: str = "Oman Poles LLC"


@router.post("/predict")
async def predict_win_probability(request: BidPredictionRequest):
    """
    Real ML Predictor using Scikit-Learn RandomForestRegressor to predict optimal margin.
    """
    try:
        if request.estimated_cost <= 0:
            raise ValueError("Estimated cost must be greater than 0.")
            
        proposed_margin = request.proposed_bid_price / request.estimated_cost
        
        model = get_model()
        if model is None:
            # Fallback heuristic if model isn't trained yet
            probability = 50.0 - ((proposed_margin - 1.0) * 100)
            model_type = "heuristic_fallback"
        else:
            # Prepare input features as a DataFrame
            input_data = pd.DataFrame([{
                'title': request.title,
                'entity': request.client,
                'category_grade': request.category
            }])
            
            # Predict the optimal margin
            predicted_target_margin = model.predict(input_data)[0]
            
            # Calculate probability based on how close proposed margin is to optimal target margin
            diff = proposed_margin - predicted_target_margin
            
            if diff <= 0:
                probability = 80.0 - (diff * 100) # diff is negative, so prob increases
            else:
                probability = 80.0 - (diff * 200)
                
            model_type = "random_forest_margin + heuristic_curve"
            
        probability = max(1.0, min(99.0, probability))
        margin_percent = (proposed_margin - 1.0) * 100
        
        return {
            "tender_id": request.tender_id,
            "company_id": request.company_id,
            "proposed_price": request.proposed_bid_price,
            "margin_percent": round(margin_percent, 2),
            "win_probability": round(probability, 1),
            "model_type": model_type,
            "factors": [
                f"Proposed Margin: {round(margin_percent, 1)}%",
                f"Client: {request.client}",
                "Probability is a heuristic curve around the model's predicted winning margin"
            ]
        }
        
    except Exception as e:
        raise _bad_request(e)

# Keep the old heuristic endpoint for backwards compatibility during transition
@router.post("/predict-heuristic")
async def predict_heuristic(request: BidPredictionRequest):
    return await predict_win_probability(request)

@router.post("/predict-optimal")
async def predict_optimal_amount(request: OptimalBidRequest):
    try:
        if request.estimated_value <= 0:
            raise ValueError("Estimated value must be greater than 0.")
            
        model = get_model()
        competitor_model = get_competitor_model()
        if model is None:
            target_margin = 0.85
        else:
            input_data = pd.DataFrame([{
                'title': request.title,
                'entity': request.entity,
                'category_grade': request.category
            }])
            target_margin = model.predict(input_data)[0]
            
        likely_competitors = []
        if competitor_model is not None:
            # Try entity first
            comp_list = competitor_model.get('entities', {}).get(request.entity)
            if not comp_list:
                comp_list = competitor_model.get('categories', {}).get(request.category)
            if not comp_list:
                comp_list = competitor_model.get('global', [])
            likely_competitors = comp_list[:3] # Return top 3
            
        predicted_winning_amount = request.estimated_value * target_margin

        return {
            "predicted_winning_amount": predicted_winning_amount,
            "margin_mae": get_model_mae() if model is not None else None,
            "likely_competitors": likely_competitors
        }
    except Exception as e:
        raise _bad_request(e)

@router.post("/predict-p2w")
async def predict_price_to_win(request: P2WRequest):
    try:
        if request.base_cost <= 0:
            raise ValueError("Base cost must be greater than 0.")
            
        target_prob = request.target_probability / 100.0
        
        simulations = []
        
        # Simulate margins from 0.80 (20% loss) to 2.00 (100% profit) in 1% increments
        margins = [(80 + i) / 100.0 for i in range(121)]
        
        # Empirical winner/median-bid ratios from past awards. estimated_value is the expected
        # typical (median) bid; we win if we price below what the winner historically did.
        ratios = _load('win_ratios.pkl')
        if ratios is None:
            raise ValueError("Win-ratio model not trained yet. Run a sync or ml/train_model.py.")
        if request.estimated_value <= 0:
            raise ValueError("Estimated value must be greater than 0.")

        for margin in margins:
            bid_price = request.base_cost * margin
            profit = bid_price - request.base_cost
            r = bid_price / request.estimated_value
            prob = 1.0 - float(np.searchsorted(ratios, r, side='left')) / len(ratios)
            prob = max(0.01, min(0.99, prob))

            simulations.append({
                "margin": round(margin * 100 - 100, 1),
                "bid_price": round(bid_price, 2),
                "profit": round(profit, 2),
                "win_probability": round(prob * 100, 1)
            })

        # Sort simulations by probability descending
        sims_sorted_by_prob = sorted(simulations, key=lambda x: x["win_probability"], reverse=True)
        
        # Best Match: highest profit among those with prob >= target_probability
        # Never recommend a loss-making bid when a profitable one exists
        profitable = [s for s in simulations if s["profit"] >= 0] or simulations
        profitable_by_prob = sorted(profitable, key=lambda x: x["win_probability"], reverse=True)
        valid_options = [s for s in profitable if s["win_probability"] >= request.target_probability]
        if valid_options:
            best_match = max(valid_options, key=lambda x: x["profit"])
        else:
            # If nothing hits the target, give the most likely profitable bid
            best_match = profitable_by_prob[0]
            
        # Aggressive: high risk (e.g., lower prob, but much higher profit)
        agg_options = [s for s in profitable if s["win_probability"] >= 30.0]
        if agg_options:
            aggressive = max(agg_options, key=lambda x: x["profit"])
        else:
            aggressive = profitable_by_prob[0]
            
        # Conservative: lowest risk (highest win probability)
        conservative = profitable_by_prob[0]
        
        return {
            "recommended": best_match,
            "aggressive": aggressive,
            "conservative": conservative,
            "simulations": simulations
        }
    except Exception as e:
        logger.error(f"Error in predict-p2w: {e}", exc_info=True)
        raise _bad_request(e)
