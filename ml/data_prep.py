import asyncio
import pandas as pd
from prisma import Prisma
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def extract_and_prepare_data():
    """
    Connects to Prisma, fetches all Awarded Tenders and their associated Bids,
    and constructs a Pandas DataFrame suitable for training the Bid Optimization Model.
    """
    db = Prisma()
    await db.connect()
    
    try:
        logger.info("Fetching Awarded Tenders from database...")
        # Include nested bids
        awarded_tenders = await db.awardedtender.find_many(
            include={'bids': True}
        )
        
        if not awarded_tenders:
            logger.warning("No awarded tenders found in database.")
            return pd.DataFrame()
            
        logger.info(f"Found {len(awarded_tenders)} awarded tenders. Building DataFrame...")
        
        rows = []
        for tender in awarded_tenders:
            # Basic tender features
            entity = tender.entity_name
            category_grade = tender.category_grade
            title = tender.tender_title
            
            bids = tender.bids
            if not bids:
                continue
                
            # To model Win Probability, we treat each bid as a sample
            for bid in bids:
                rows.append({
                    'tender_no': tender.tender_no,
                    'title': title,
                    'entity': entity,
                    'category_grade': category_grade,
                    'company_name': bid.company_name,
                    'quoted_value': bid.total_quoted_value,
                    'is_winner': 1 if bid.is_winner else 0
                })
                
        df = pd.DataFrame(rows)
        logger.info(f"Generated DataFrame with {len(df)} bid records.")
        
        return df
        
    finally:
        await db.disconnect()

MAX_BID_VALUE = 1e8  # OMR; larger values are scrape/entry errors


def clean_tenders(tenders):
    """
    Reduce awarded tenders (with .bids loaded) to rows fit for price modelling.

    Per tender we keep only priced "Main" offers (no alternates, no technical-only rows),
    one per company, and require 2+ distinct bidders and exactly one winning company.
    Multi-lot awards (several winning companies) are dropped: bids cannot be split by lot.
    Returns dicts: tender_no, title, entity, category_grade, n_bidders, winning_bid,
    median_bid, mean_bid.
    """
    rows = []
    for t in tenders:
        best = {}  # company -> (value, is_winner)
        for b in (t.bids or []):
            v = b.total_quoted_value
            if b.offer_type != 'Main' or not (0 < v <= MAX_BID_VALUE):
                continue
            cur = best.get(b.company_name)
            if cur is None or v < cur[0]:
                best[b.company_name] = (v, bool(b.is_winner) or (cur[1] if cur else False))
        if len(best) < 2:
            continue
        winners = [v for v, w in best.values() if w]
        if len(winners) != 1:
            continue
        values = [v for v, _ in best.values()]
        rows.append({
            'tender_no': t.tender_no,
            'title': t.tender_title,
            'entity': t.entity_name,
            'category_grade': t.category_grade,
            'n_bidders': len(values),
            'winning_bid': winners[0],
            'median_bid': float(np.median(values)),
            'mean_bid': float(np.mean(values)),
        })
    return rows


def get_ml_dataframe():
    """Wrapper to run the async extraction synchronously for scikit-learn."""
    return asyncio.run(extract_and_prepare_data())

if __name__ == "__main__":
    df = get_ml_dataframe()
    if not df.empty:
        print(df.head())
        print(f"\nTotal Shape: {df.shape}")
