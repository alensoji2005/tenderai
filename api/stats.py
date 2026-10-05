from fastapi import APIRouter, HTTPException, Depends
from api.main import db
from api.auth import get_current_user
from collections import defaultdict
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/dashboard")
async def get_dashboard_stats(current_user = Depends(get_current_user)):
    try:
        # Total Tenders
        tenders_query = 'SELECT COUNT(id)::int as count FROM "AwardedTender"'
        tenders_res = await db.query_raw(tenders_query)
        total_tenders = tenders_res[0]["count"] if tenders_res else 0
        
        # Total Competitors
        competitors_query = 'SELECT COUNT(DISTINCT company_name)::int as count FROM "AwardedTenderBid"'
        competitors_res = await db.query_raw(competitors_query)
        total_competitors = competitors_res[0]["count"] if competitors_res else 0
        
        # Tender Volume over Time (Last 6 months)
        # We group by YYYY-MM
        volume_query = """
        SELECT 
            TO_CHAR(awarded_date, 'YYYY-MM') as month,
            COUNT(id)::int as count
        FROM "AwardedTender"
        WHERE awarded_date IS NOT NULL
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
        """
        volume_res = await db.query_raw(volume_query)
        
        # Sort chronologically for the chart
        chart_data = [{"name": row["month"], "Tenders": row["count"]} for row in volume_res]
        chart_data.reverse()
        # Top 5 Entities by Volume
        entity_query = """
        SELECT 
            entity_name as name,
            COUNT(id)::int as count
        FROM "AwardedTender"
        WHERE entity_name IS NOT NULL
        GROUP BY entity_name
        ORDER BY count DESC
        LIMIT 5
        """
        entity_res = await db.query_raw(entity_query)
        top_entities = [{"name": row["name"], "count": row["count"]} for row in entity_res]
        
        # Top 5 Categories by Volume
        category_query = """
        SELECT 
            category_grade as name,
            COUNT(id)::int as count
        FROM "AwardedTender"
        WHERE category_grade IS NOT NULL
        GROUP BY category_grade
        ORDER BY count DESC
        LIMIT 5
        """
        category_res = await db.query_raw(category_query)
        top_categories = [{"name": row["name"], "count": row["count"]} for row in category_res]
        
        # Average % by which the winning bid undercuts the mean bid (tenders with 2+ priced bids)
        margin_query = """
        SELECT AVG((1 - win / avg_bid) * 100)::float AS margin FROM (
            SELECT
                MIN(CASE WHEN is_winner THEN total_quoted_value END) AS win,
                AVG(total_quoted_value) AS avg_bid
            FROM "AwardedTenderBid"
            WHERE total_quoted_value > 0
            GROUP BY awarded_tender_no
            HAVING COUNT(*) >= 2 AND MIN(CASE WHEN is_winner THEN total_quoted_value END) IS NOT NULL
        ) x
        """
        margin_res = await db.query_raw(margin_query)
        avg_win_margin = round(margin_res[0]["margin"], 1) if margin_res and margin_res[0]["margin"] is not None else 0.0

        return {
            "total_tenders": total_tenders,
            "total_competitors": total_competitors,
            "avg_win_margin": avg_win_margin,
            "chart_data": chart_data,
            "top_entities": top_entities,
            "top_categories": top_categories
        }
    except Exception:
        logger.exception("stats query failed")
        raise HTTPException(status_code=500, detail="Failed to load statistics.")

@router.get("/scraper")
async def get_scraper_stats(current_user = Depends(get_current_user)):
    try:
        tenders_query = 'SELECT COUNT(id)::int as count FROM "AwardedTender"'
        tenders_res = await db.query_raw(tenders_query)
        total_scraped = tenders_res[0]["count"] if tenders_res else 0
        
        return {
            "total_scraped": total_scraped,
            "target": 30000,
            "progress_percent": round((total_scraped / 30000) * 100, 2)
        }
    except Exception:
        logger.exception("stats query failed")
        raise HTTPException(status_code=500, detail="Failed to load statistics.")
