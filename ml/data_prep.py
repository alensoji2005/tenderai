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


def is_sane_amount(v):
    """True for a plausible money amount: positive and not an entry error."""
    return v is not None and 0 < v <= MAX_BID_VALUE


def _priced_offers(t):
    """
    Cleaned offers of one awarded tender as {company: (value, is_winner)}, or None if unusable.

    Only priced "Main" offers count (no alternates, no technical-only rows), one per company
    (the lowest). A tender needs 2+ distinct bidders and exactly one winning company: multi-lot
    awards (several winners) are dropped because bids cannot be split by lot.
    """
    best = {}
    for b in (t.bids or []):
        v = b.total_quoted_value
        if b.offer_type != 'Main' or not is_sane_amount(v):
            continue
        cur = best.get(b.company_name)
        if cur is None or v < cur[0]:
            best[b.company_name] = (v, bool(b.is_winner) or (cur[1] if cur else False))
    if len(best) < 2 or sum(w for _, w in best.values()) != 1:
        return None
    return best


def clean_tenders(tenders):
    """
    One row per usable awarded tender (see _priced_offers for the rules).
    Returns dicts: tender_no, title, entity, category_grade, n_bidders, winning_bid,
    median_bid, mean_bid.
    """
    rows = []
    for t in tenders:
        best = _priced_offers(t)
        if best is None:
            continue
        values = [v for v, _ in best.values()]
        rows.append({
            'tender_no': t.tender_no,
            'title': t.tender_title,
            'entity': t.entity_name,
            'category_grade': t.category_grade,
            'n_bidders': len(values),
            'winning_bid': next(v for v, w in best.values() if w),
            'median_bid': float(np.median(values)),
            'mean_bid': float(np.mean(values)),
        })
    return rows


def clean_bids(tenders):
    """
    One row per cleaned bid, for modelling the chance that a price wins.
    Returns dicts: tender_no, n_bidders, ratio (bid / median bid of its tender), is_winner.
    """
    rows = []
    for t in tenders:
        best = _priced_offers(t)
        if best is None:
            continue
        median = float(np.median([v for v, _ in best.values()]))
        for v, w in best.values():
            rows.append({'tender_no': t.tender_no, 'n_bidders': len(best), 'ratio': v / median, 'is_winner': w})
    return rows


def get_ml_dataframe():
    """Wrapper to run the async extraction synchronously for scikit-learn."""
    return asyncio.run(extract_and_prepare_data())

if __name__ == "__main__":
    df = get_ml_dataframe()
    if not df.empty:
        print(df.head())
        print(f"\nTotal Shape: {df.shape}")
