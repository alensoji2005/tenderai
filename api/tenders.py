from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from api.main import db
from api.auth import get_current_user
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class TenderCreate(BaseModel):
    tender_id: str
    title: str
    category: str = "Uncategorized"
    closing_date: datetime
    estimated_value: Optional[float] = None
    currency: str = "OMR"
    status: str = "active"
    source: str = "public_scraper"

@router.post("/bulk")
async def bulk_insert_tenders(tenders: List[TenderCreate], current_user = Depends(get_current_user)):
    """
    Ingest scraped tenders into the database.
    """
    try:
        inserted = 0
        for tender in tenders:
            # Upsert to prevent duplicates
            await db.tender.upsert(
                where={"tender_id": tender.tender_id},
                data={
                    "create": tender.dict(exclude={"source"}),
                    "update": {
                        "title": tender.title,
                        "closing_date": tender.closing_date,
                        "status": tender.status
                    }
                }
            )
            inserted += 1
        return {"message": f"Successfully upserted {inserted} tenders."}
    except Exception:
        logger.exception("bulk upsert failed")
        raise HTTPException(status_code=500, detail="Failed to save tenders.")

@router.get("/")
async def get_tenders(
    status: Optional[str] = None,
    category: Optional[str] = None,
    title_search: Optional[str] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """
    Fetch a list of tenders from the database with robust filtering.
    """
    try:
        take_arg = limit if limit > 0 else None

        # Awarded (historical) tenders live in their own table, with their bids.
        if status == "awarded":
            where = {}
            if category:
                where["category_grade"] = {"contains": category, "mode": "insensitive"}
            if title_search:
                where["tender_title"] = {"contains": title_search, "mode": "insensitive"}
            if min_value is not None or max_value is not None:
                f = {}
                if min_value is not None:
                    f["gte"] = min_value
                if max_value is not None:
                    f["lte"] = max_value
                where["winning_amount"] = f
            rows = await db.awardedtender.find_many(
                where=where, take=take_arg, order={"awarded_date": "desc"}, include={"bids": True}
            )
            data = [{
                "tender_id": r.tender_no,
                "title": r.tender_title,
                "category": r.category_grade,
                "entity": r.entity_name,
                "status": "awarded",
                "estimated_value": r.winning_amount,
                "closing_date": r.awarded_date,
                "bids": r.bids,
            } for r in rows]
            return {"count": len(data), "data": data}

        where_clause = {}
        if status:
            where_clause["status"] = status
        if category:
            where_clause["category"] = {"contains": category, "mode": "insensitive"}
        if title_search:
            where_clause["title"] = {"contains": title_search, "mode": "insensitive"}
        if min_value is not None or max_value is not None:
            value_filter = {}
            if min_value is not None:
                value_filter["gte"] = min_value
            if max_value is not None:
                value_filter["lte"] = max_value
            where_clause["estimated_value"] = value_filter

        tenders = await db.tender.find_many(
            where=where_clause,
            take=take_arg,
            order={"closing_date": "desc"}
        )
        return {"count": len(tenders), "data": tenders}
    except Exception:
        logger.exception("get_tenders failed")
        raise HTTPException(status_code=500, detail="Failed to load tenders.")

@router.get("/{tender_id}")
async def get_tender_details(tender_id: str, current_user = Depends(get_current_user)):
    """
    Fetch full details for a specific tender, including its BOQ items.
    """
    tender = await db.tender.find_unique(
        where={"tender_id": tender_id},
        include={"boq_items": True}
    )
    
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
        
    return tender