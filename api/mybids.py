# api/mybids.py
"""Bids Oman Poles placed itself: log them, record results, and check P2W against real outcomes."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from api.main import db
from api.auth import get_current_user
from api.ml import win_ratios_for, win_probability

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)

RESULTS = ("pending", "won", "lost")
FIELDS = ("id", "tender_no", "title", "entity", "our_price", "base_cost", "typical_bid", "bidders",
          "predicted_probability", "result", "winning_price", "created_at")
BUCKETS = [(0, 25), (25, 50), (50, 75), (75, 100.01)]  # predicted win chance, percent


class MyBidCreate(BaseModel):
    tender_no: str
    title: str
    entity: Optional[str] = None
    our_price: float
    base_cost: float
    typical_bid: Optional[float] = None
    bidders: Optional[int] = None
    predicted_probability: Optional[float] = None  # percent; computed from the model when omitted


class MyBidResult(BaseModel):
    result: str
    winning_price: Optional[float] = None


def _to_dict(row):
    return {f: getattr(row, f) for f in FIELDS}


def predict_percent(our_price, typical_bid, bidders):
    """P2W win chance (percent) for this price, or None when it can't be computed."""
    ratios = win_ratios_for(bidders)
    if ratios is None or not typical_bid:
        return None
    return round(win_probability(ratios, our_price / typical_bid) * 100, 1)


def calibration(rows):
    """How P2W's predicted win chances compare with real results (rows are dicts)."""
    won = [r for r in rows if r["result"] == "won"]
    lost = [r for r in rows if r["result"] == "lost"]
    summary = {
        "total": len(rows),
        "pending": len(rows) - len(won) - len(lost),
        "won": len(won),
        "lost": len(lost),
        "win_rate": round(100 * len(won) / (len(won) + len(lost)), 1) if won or lost else None,
        "realised_profit": round(sum(r["our_price"] - r["base_cost"] for r in won), 2),
    }
    scored = [r for r in won + lost if r["predicted_probability"] is not None]
    if not scored:
        return {**summary, "scored": 0, "mean_predicted": None, "brier": None, "buckets": []}

    brier = sum((r["predicted_probability"] / 100 - (r["result"] == "won")) ** 2 for r in scored) / len(scored)
    buckets = []
    for lo, hi in BUCKETS:
        sel = [r for r in scored if lo <= r["predicted_probability"] < hi]
        if sel:
            buckets.append({
                "range": f"{lo}-{min(hi, 100):.0f}%",
                "n": len(sel),
                "predicted": round(sum(r["predicted_probability"] for r in sel) / len(sel), 1),
                "actual": round(100 * sum(r["result"] == "won" for r in sel) / len(sel), 1),
            })
    return {
        **summary,
        "scored": len(scored),
        "mean_predicted": round(sum(r["predicted_probability"] for r in scored) / len(scored), 1),
        "brier": round(brier, 4),
        "buckets": buckets,
    }


@router.post("/")
async def log_bid(bid: MyBidCreate):
    if bid.our_price <= 0 or bid.base_cost <= 0:
        raise HTTPException(status_code=400, detail="Our price and base cost must be greater than 0.")
    if bid.typical_bid is not None and bid.typical_bid <= 0:
        raise HTTPException(status_code=400, detail="Typical bid must be greater than 0.")
    if bid.bidders is not None and bid.bidders < 2:
        raise HTTPException(status_code=400, detail="Bidders must be at least 2.")
    if bid.predicted_probability is not None and not 0 <= bid.predicted_probability <= 100:
        raise HTTPException(status_code=400, detail="Predicted probability must be between 0 and 100.")

    data = bid.model_dump() if hasattr(bid, "model_dump") else bid.dict()
    if data["predicted_probability"] is None:
        data["predicted_probability"] = predict_percent(bid.our_price, bid.typical_bid, bid.bidders)
    try:
        row = await db.mybid.create(data=data)
    except Exception:
        logger.exception("log_bid failed")
        raise HTTPException(status_code=500, detail="Failed to save bid.")
    return _to_dict(row)


@router.get("/")
async def list_bids():
    try:
        rows = await db.mybid.find_many(order={"created_at": "desc"})
    except Exception:
        logger.exception("list_bids failed")
        raise HTTPException(status_code=500, detail="Failed to load bids.")
    return {"count": len(rows), "data": [_to_dict(r) for r in rows]}


@router.patch("/{bid_id}/result")
async def set_result(bid_id: int, body: MyBidResult):
    if body.result not in RESULTS:
        raise HTTPException(status_code=400, detail=f"Result must be one of: {', '.join(RESULTS)}.")
    if body.winning_price is not None and body.winning_price <= 0:
        raise HTTPException(status_code=400, detail="Winning price must be greater than 0.")
    try:
        row = await db.mybid.update(
            where={"id": bid_id},
            data={"result": body.result, "winning_price": body.winning_price},
        )
    except Exception:
        logger.exception("set_result failed")
        raise HTTPException(status_code=500, detail="Failed to update bid.")
    if row is None:
        raise HTTPException(status_code=404, detail="Bid not found.")
    return _to_dict(row)


@router.delete("/{bid_id}")
async def delete_bid(bid_id: int):
    try:
        row = await db.mybid.delete(where={"id": bid_id})
    except Exception:
        logger.exception("delete_bid failed")
        raise HTTPException(status_code=500, detail="Failed to delete bid.")
    if row is None:
        raise HTTPException(status_code=404, detail="Bid not found.")
    return {"deleted": bid_id}


@router.get("/calibration")
async def get_calibration():
    try:
        rows = await db.mybid.find_many()
    except Exception:
        logger.exception("calibration failed")
        raise HTTPException(status_code=500, detail="Failed to load bids.")
    return calibration([_to_dict(r) for r in rows])
