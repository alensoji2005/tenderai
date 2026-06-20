# api/tenders.py
from fastapi import APIRouter, HTTPException
from api.main import db
from typing import Optional

router = APIRouter()

@router.get("/")
async def get_tenders(
    status: Optional[str] = "active",
    limit: int = 50
):
    """
    Fetch a list of tenders from the database.
    """
    try:
        tenders = await db.tender.find_many(
            where={"status": status},
            take=limit,
            order={"closing_date": "asc"}
        )
        return {"count": len(tenders), "data": tenders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{tender_id}")
async def get_tender_details(tender_id: str):
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