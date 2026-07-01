import asyncio
import pandas as pd
import numpy as np
import os
import joblib
from prisma import Prisma
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def fetch_data():
    db = Prisma()
    await db.connect()
    logger.info("Fetching awarded tenders and bids from DB...")
    
    tenders = await db.awardedtender.find_many(include={'bids': True})
    await db.disconnect()
    
    data = []
    for t in tenders:
        if not t.bids or len(t.bids) < 2:
            continue
            
        # Get all valid bids
        bid_values = [b.total_quoted_value for b in t.bids if b.total_quoted_value > 0]
        if not bid_values:
            continue
            
        mean_bid = np.mean(bid_values)
        winning_bid = np.min(bid_values) # The winner is usually the lowest valid bid
        
        # We calculate the margin as winning_bid / mean_bid
        # e.g., if mean is 100k, and winning is 80k, margin is 0.8
        target_margin = winning_bid / mean_bid
        
        # Only keep reasonable margins (exclude crazy outliers from bad data entry)
        if target_margin < 0.2 or target_margin > 1.5:
            continue
            
        data.append({
            'title': t.tender_title,
            'entity': t.entity_name,
            'target_margin': target_margin
        })
        
    df = pd.DataFrame(data)
    return df

def train_model():
    df = asyncio.run(fetch_data())
    
    if len(df) < 50:
        logger.error(f"Not enough data to train model. Found {len(df)} valid records.")
        return
        
    logger.info(f"Training on {len(df)} tender records...")
    
    # Features: TF-IDF on title
    preprocessor = ColumnTransformer(
        transformers=[
            ('title_tfidf', TfidfVectorizer(max_features=500, stop_words='english'), 'title'),
            # We can also add entity name if needed, but TF-IDF on title is strong enough
        ]
    )
    
    # We use a Random Forest Regressor
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10))
    ])
    
    X = df[['title', 'entity']]
    y = df['target_margin']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    logger.info(f"Model trained successfully.")
    logger.info(f"Mean Absolute Error (Margin): {mae:.4f}")
    logger.info(f"R2 Score: {r2:.4f}")
    
    # Ensure ml directory exists
    os.makedirs('ml', exist_ok=True)
    
    model_path = os.path.join('ml', 'model.pkl')
    joblib.dump(pipeline, model_path)
    logger.info(f"Model saved to {model_path}")

if __name__ == '__main__':
    train_model()
