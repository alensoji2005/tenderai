# api/competitors.py
from fastapi import APIRouter, HTTPException, Depends, Query
from api.main import db
from api.auth import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

@router.get("/")
async def get_competitors(
    limit: int = 50, 
    entity: Optional[str] = None,
    search: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Fetch a leaderboard of competitors aggregated from real scraped AwardedTenderBid data.
    """
    try:
        query = """
        SELECT 
            b.company_name, 
            COUNT(b.id)::int as total_bids,
            SUM(CASE WHEN b.is_winner THEN 1 ELSE 0 END)::int as tenders_won,
            SUM(CASE WHEN b.is_winner THEN b.total_quoted_value ELSE 0 END)::float as total_won_amount,
            AVG(CASE WHEN b.is_winner THEN b.total_quoted_value ELSE NULL END)::float as avg_winning_amount
        FROM "AwardedTenderBid" b
        JOIN "AwardedTender" t ON b.awarded_tender_no = t.tender_no
        WHERE 1=1
        """
        
        args = []
        if entity:
            args.append(f"%{entity}%")
            query += f" AND t.entity_name ILIKE ${len(args)}"
        if search:
            args.append(f"%{search}%")
            query += f" AND b.company_name ILIKE ${len(args)}"
            
        query += f" GROUP BY b.company_name ORDER BY total_won_amount DESC LIMIT ${len(args) + 1}"
        args.append(limit)
        
        competitors = await db.query_raw(query, *args)
        
        # Prisma query_raw returns a list of dicts. We need to handle null floats.
        for c in competitors:
            c['avg_winning_amount'] = c['avg_winning_amount'] if c['avg_winning_amount'] is not None else 0.0
            
        return {"count": len(competitors), "data": competitors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entities")
async def get_entities(current_user = Depends(get_current_user)):
    """
    Fetch a distinct list of entity names for the filter dropdown.
    """
    try:
        query = 'SELECT DISTINCT entity_name FROM "AwardedTender" ORDER BY entity_name'
        entities = await db.query_raw(query)
        return {"data": [e["entity_name"] for e in entities]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{company_name}")
async def get_competitor_details(company_name: str, current_user = Depends(get_current_user)):
    """
    Fetch full deep-dive details for a specific competitor.
    """
    try:
        # 1. Get overall stats
        stats_query = """
        SELECT 
            b.company_name, 
            COUNT(b.id)::int as total_bids,
            SUM(CASE WHEN b.is_winner THEN 1 ELSE 0 END)::int as tenders_won,
            SUM(CASE WHEN b.is_winner THEN b.total_quoted_value ELSE 0 END)::float as total_won_amount
        FROM "AwardedTenderBid" b
        WHERE b.company_name = $1
        GROUP BY b.company_name
        """
        stats_res = await db.query_raw(stats_query, company_name)
        if not stats_res:
            raise HTTPException(status_code=404, detail="Competitor not found")
        stats = stats_res[0]
        
        # 2. Get bid history
        history_query = """
        SELECT 
            t.tender_no,
            t.tender_title,
            t.entity_name,
            t.awarded_date,
            b.total_quoted_value,
            b.is_winner
        FROM "AwardedTenderBid" b
        JOIN "AwardedTender" t ON b.awarded_tender_no = t.tender_no
        WHERE b.company_name = $1
        ORDER BY t.awarded_date DESC
        LIMIT 100
        """
        history = await db.query_raw(history_query, company_name)
        
        # Convert awarded_date from string to ISO format if necessary
        
        # 3. Get entity distribution
        entity_query = """
        SELECT 
            t.entity_name as name,
            COUNT(b.id)::int as value
        FROM "AwardedTenderBid" b
        JOIN "AwardedTender" t ON b.awarded_tender_no = t.tender_no
        WHERE b.company_name = $1
        GROUP BY t.entity_name
        ORDER BY value DESC
        LIMIT 10
        """
        entity_distribution = await db.query_raw(entity_query, company_name)
        
        # 4. Frequently Beats
        beats_query = """
        SELECT b2.company_name as name, COUNT(b2.id)::int as count
        FROM "AwardedTenderBid" b1
        JOIN "AwardedTenderBid" b2 ON b1.awarded_tender_no = b2.awarded_tender_no
        WHERE b1.company_name = $1 AND b1.is_winner = true AND b2.company_name != $1
        GROUP BY b2.company_name
        ORDER BY count DESC
        LIMIT 5
        """
        frequently_beats = await db.query_raw(beats_query, company_name)
        
        # 5. Pricing Behavior
        market_query = """
        SELECT AVG(total_quoted_value)::float as avg_market
        FROM "AwardedTenderBid"
        WHERE is_winner = true AND total_quoted_value > 0
        """
        market_res = await db.query_raw(market_query)
        market_avg = market_res[0]['avg_market'] if market_res and market_res[0]['avg_market'] else 0
        comp_avg = (stats['total_won_amount'] / stats['tenders_won']) if stats['tenders_won'] > 0 else 0
        
        pricing_behavior = "Moderate"
        if comp_avg > 0 and market_avg > 0:
            if comp_avg < market_avg * 0.5:
                pricing_behavior = "Aggressive (Low Cost)"
            elif comp_avg > market_avg * 1.5:
                pricing_behavior = "Premium (High Value)"
                
        stats['pricing_behavior'] = pricing_behavior
        
        return {
            "stats": stats,
            "history": history,
            "entity_distribution": entity_distribution,
            "frequently_beats": frequently_beats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
