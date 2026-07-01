from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from api.main import db
from api.auth import get_current_user
from typing import Optional, List
from datetime import datetime

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
async def bulk_insert_tenders(tenders: List[TenderCreate]):
    """
    Ingest scraped tenders into the database.
    Note: Can be protected by a different token in production if scraped by a script.
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        where_clause = {}
        if status:
            where_clause["status"] = status
        if category:
            where_clause["category"] = category
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
            take=limit,
            order={"closing_date": "desc"}
        )
        return {"count": len(tenders), "data": tenders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{tender_id}")
async def get_tender_details(tender_id: str, current_user = Depends(get_current_user)):
    """
    Fetch full details for a specific tender, including its BOQ items.
    """
    tender = await db.tender.find_unique(
        where={"tender_id": tender_id},
        include={"boq_items": True, "bids": True}
    )
    
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
        
    return tender