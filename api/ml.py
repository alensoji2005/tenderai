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

def win_curve():
    """The trained P(win) model, or None if it has not been trained yet."""
    return _load('win_curve.pkl')

def win_probabilities(curve, ratios, bidders=None):
    """
    Chance (0.01-0.99) that each price wins, where a price is given as bid / typical (median) bid.
    With no bidder count, averages over the bidder counts seen in past tenders.
    """
    ratios = np.asarray(ratios, dtype=float)
    counts = [bidders] if bidders else list(curve['n_sample'])
    X = np.array([[np.log(r), n] for n in counts for r in ratios])
    probs = curve['model'].predict_proba(X)[:, 1].reshape(len(counts), len(ratios)).mean(axis=0)
    return np.clip(probs, 0.01, 0.99)

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
    target_probability: float = 35.0
    title: str
    entity: str = "Ministry of Health"
    category: str = "Construction"
    company_name: str = "Oman Poles LLC"
    bidders: Optional[int] = None  # expected number of bidders; narrows the win-ratio distribution


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
        if request.estimated_value <= 0:
            raise ValueError("Estimated value must be greater than 0.")
        if request.bidders is not None and request.bidders < 2:
            raise ValueError("Bidders must be at least 2.")

        # estimated_value is the expected typical (median) bid. The win curve, learned from real past
        # bids, gives the chance that a price relative to that typical bid wins.
        curve = win_curve()
        if curve is None:
            raise ValueError("Win-probability model not trained yet. Run a sync or ml/train_model.py.")

        # Simulate margins from 0.80 (20% loss) to 2.00 (100% profit) in 1% increments
        margins = [(80 + i) / 100.0 for i in range(121)]
        bid_prices = [request.base_cost * m for m in margins]
        probs = win_probabilities(curve, [p / request.estimated_value for p in bid_prices], request.bidders)

        simulations = [{
            "margin": round(margin * 100 - 100, 1),
            "bid_price": round(price, 2),
            "profit": round(price - request.base_cost, 2),
            "win_probability": round(float(prob) * 100, 1),
        } for margin, price, prob in zip(margins, bid_prices, probs)]

        # Never recommend a loss-making bid when a profitable one exists
        profitable = [s for s in simulations if s["profit"] >= 0] or simulations
        profitable_by_prob = sorted(profitable, key=lambda x: x["win_probability"], reverse=True)

        # Recommended: highest profit among bids that reach the target win probability
        valid_options = [s for s in profitable if s["win_probability"] >= request.target_probability]
        target_reached = bool(valid_options)
        if target_reached:
            best_match = max(valid_options, key=lambda x: x["profit"])
        else:
            # Nothing hits the target at a profit: pick the best expected profit (win chance x profit),
            # which beats the break-even bid (zero profit even when it wins)
            best_match = max(profitable, key=lambda x: x["win_probability"] * x["profit"])

        # Aggressive: riskier, accepts half the target win chance for more profit
        agg_options = [s for s in profitable if s["win_probability"] >= request.target_probability / 2]
        if agg_options:
            aggressive = max(agg_options, key=lambda x: x["profit"])
        else:
            aggressive = profitable_by_prob[0]

        # Conservative: lowest risk (highest win probability)
        conservative = profitable_by_prob[0]

        # How much the recommended win chance moves if the typical-bid estimate is 10% off
        sensitivity = {}
        for label, factor in (("typical_bid_10pct_lower", 0.9), ("typical_bid_10pct_higher", 1.1)):
            p = win_probabilities(curve, [best_match["bid_price"] / (request.estimated_value * factor)], request.bidders)[0]
            sensitivity[label] = round(float(p) * 100, 1)

        return {
            "recommended": best_match,
            "aggressive": aggressive,
            "conservative": conservative,
            "target_reached": target_reached,
            "recommended_sensitivity": sensitivity,
            "simulations": simulations
        }
    except Exception as e:
        logger.error(f"Error in predict-p2w: {e}", exc_info=True)
        raise _bad_request(e)
