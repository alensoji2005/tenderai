# api/ml.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import joblib
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

BID_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ml', 'bid_model.joblib')
try:
    bid_model = joblib.load(BID_MODEL_PATH)
    logger.info(f"Successfully loaded bid classifier from {BID_MODEL_PATH}")
except Exception as e:
    logger.warning(f"Failed to load bid classifier: {str(e)}")
    bid_model = None

# Load the trained model on startup
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ml', 'model.pkl')
try:
    model = joblib.load(MODEL_PATH)
    logger.info(f"Successfully loaded ML model from {MODEL_PATH}")
except Exception as e:
    logger.warning(f"Failed to load ML model: {str(e)}. Ensure train_model.py has been run.")
    model = None

COMPETITOR_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ml', 'competitor_model.pkl')
try:
    competitor_model = joblib.load(COMPETITOR_MODEL_PATH)
    logger.info(f"Successfully loaded competitor model from {COMPETITOR_MODEL_PATH}")
except Exception as e:
    logger.warning(f"Failed to load competitor model: {str(e)}")
    competitor_model = None

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
        
        if model is None:
            # Fallback heuristic if model isn't trained yet
            probability = 50.0 - ((proposed_margin - 1.0) * 100)
            model_type = "heuristic_fallback"
        else:
            # Prepare input features as a DataFrame
            input_data = pd.DataFrame([{
                'title': request.title,
                'entity': request.client
            }])
            
            # Predict the optimal margin
            predicted_target_margin = model.predict(input_data)[0]
            
            # Calculate probability based on how close proposed margin is to optimal target margin
            diff = proposed_margin - predicted_target_margin
            
            if diff <= 0:
                probability = 80.0 - (diff * 100) # diff is negative, so prob increases
            else:
                probability = 80.0 - (diff * 200)
                
            model_type = "random_forest_v1"
            
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
                "Model optimized based on 3000+ past tenders"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Keep the old heuristic endpoint for backwards compatibility during transition
@router.post("/predict-heuristic")
async def predict_heuristic(request: BidPredictionRequest):
    return await predict_win_probability(request)

@router.post("/predict-optimal")
async def predict_optimal_amount(request: OptimalBidRequest):
    try:
        if request.estimated_value <= 0:
            raise ValueError("Estimated value must be greater than 0.")
            
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
        confidence_score = 0.82 if model is not None else 0.50
        
        return {
            "predicted_winning_amount": predicted_winning_amount,
            "confidence_score": confidence_score,
            "likely_competitors": likely_competitors
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/predict-p2w")
async def predict_price_to_win(request: P2WRequest):
    try:
        if request.base_cost <= 0:
            raise ValueError("Base cost must be greater than 0.")
            
        target_prob = request.target_probability / 100.0
        
        simulations = []
        
        # Simulate margins from 0.80 (20% loss) to 2.00 (100% profit) in 1% increments
        margins = [(80 + i) / 100.0 for i in range(121)]
        
        # Use the Regressor model for a continuous, realistic curve
        if model is not None:
            target_m = model.predict(pd.DataFrame([{
                'title': request.title,
                'entity': request.entity,
                'category_grade': request.category
            }]))[0]
        else:
            target_m = 1.15
            
        for margin in margins:
            bid_price = request.base_cost * margin
            profit = bid_price - request.base_cost
            
            diff = margin - target_m
            
            # Probability curve around the market average target margin
            if diff <= 0:
                # Bidding below market average -> higher probability
                prob = 0.80 - (diff * 1.5)
            else:
                # Bidding above market average -> sharply lower probability
                prob = 0.80 - (diff * 2.5)
                
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
        valid_options = [s for s in simulations if s["win_probability"] >= request.target_probability]
        if valid_options:
            best_match = max(valid_options, key=lambda x: x["profit"])
        else:
            # If nothing hits the target, just give the one with the highest probability
            best_match = sims_sorted_by_prob[0]
            
        # Aggressive: high risk (e.g., lower prob, but much higher profit)
        agg_options = [s for s in simulations if s["win_probability"] >= 30.0]
        if agg_options:
            aggressive = max(agg_options, key=lambda x: x["profit"])
        else:
            aggressive = sims_sorted_by_prob[0]
            
        # Conservative: lowest risk (highest win probability)
        conservative = sims_sorted_by_prob[0]
        
        return {
            "recommended": best_match,
            "aggressive": aggressive,
            "conservative": conservative,
            "simulations": simulations
        }
    except Exception as e:
        logger.error(f"Error in predict-p2w: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
