import asyncio
import pandas as pd
from prisma import Prisma
import logging

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

def get_ml_dataframe():
    """Wrapper to run the async extraction synchronously for scikit-learn."""
    return asyncio.run(extract_and_prepare_data())

if __name__ == "__main__":
    df = get_ml_dataframe()
    if not df.empty:
        print(df.head())
        print(f"\nTotal Shape: {df.shape}")
