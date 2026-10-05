import asyncio
import pandas as pd
import numpy as np
import os
import joblib
from prisma import Prisma
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import logging
import json
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
ML_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from ml.data_prep import clean_tenders
except ImportError:  # run as a script from inside ml/
    from data_prep import clean_tenders

async def fetch_data():
    db = Prisma()
    await db.connect()
    logger.info("Fetching awarded tenders and bids from DB...")
    
    tenders = await db.awardedtender.find_many(include={'bids': True})
    await db.disconnect()
    
    data = []
    for r in clean_tenders(tenders):
        # margin = winning_bid / mean_bid, e.g. mean 100k and winner 80k -> 0.8
        target_margin = r['winning_bid'] / r['mean_bid']
        if target_margin < 0.2 or target_margin > 1.5:
            continue
        data.append({
            'title': r['title'],
            'entity': r['entity'],
            'category_grade': r['category_grade'],
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
            ('cat_entity', OneHotEncoder(handle_unknown='ignore'), ['entity', 'category_grade'])
        ]
    )
    
    # We use a Random Forest Regressor
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10))
    ])
    
    X = df[['title', 'entity', 'category_grade']]
    y = df['target_margin']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    logger.info(f"Model trained successfully.")
    logger.info(f"Mean Absolute Error (Margin): {mae:.4f}")
    logger.info(f"R2 Score: {r2:.4f}")
    
    os.makedirs(ML_DIR, exist_ok=True)
    
    with open(os.path.join(ML_DIR, 'model_meta.json'), 'w') as f:
        json.dump({'mae': float(mae), 'r2': float(r2), 'n_records': int(len(df))}, f)
    
    model_path = os.path.join(ML_DIR, 'model.pkl')
    joblib.dump(pipeline, model_path)
    logger.info(f"Model saved to {model_path}")

async def train_competitor_model_async():
    db = Prisma()
    await db.connect()
    logger.info("Training Competitor Model...")
    tenders = await db.awardedtender.find_many(include={'bids': True})
    await db.disconnect()
    
    # Maps entity -> dict of {company: count}
    entity_competitors = defaultdict(lambda: defaultdict(int))
    category_competitors = defaultdict(lambda: defaultdict(int))
    global_competitors = defaultdict(int)
    
    for t in tenders:
        if not t.bids: continue
        for b in t.bids:
            c_name = b.company_name
            entity_competitors[t.entity_name][c_name] += 1
            category_competitors[t.category_grade][c_name] += 1
            global_competitors[c_name] += 1
            
    # Extract top 10 for each
    def get_top(counts_dict, n=10):
        sorted_counts = sorted(counts_dict.items(), key=lambda x: x[1], reverse=True)
        return [c[0] for c in sorted_counts[:n]]

    competitor_model = {
        'entities': {e: get_top(counts) for e, counts in entity_competitors.items()},
        'categories': {c: get_top(counts) for c, counts in category_competitors.items()},
        'global': get_top(global_competitors)
    }
    
    comp_model_path = os.path.join(ML_DIR, 'competitor_model.pkl')
    joblib.dump(competitor_model, comp_model_path)
    logger.info(f"Competitor Model saved to {comp_model_path}")

def train_competitor_model():
    asyncio.run(train_competitor_model_async())

WIN_RATIO_BUCKETS = [(2, 2), (3, 4), (5, 7), (8, 11), (12, 10**6)]

async def train_win_ratio_model_async():
    """Empirical distribution of (winning bid / median bid) per tender: the basis of P2W win probabilities."""
    db = Prisma()
    await db.connect()
    tenders = await db.awardedtender.find_many(include={'bids': True})
    await db.disconnect()

    ratios = []  # (bidder count, ratio)
    for r in clean_tenders(tenders):
        ratio = r['winning_bid'] / r['median_bid']
        if 0.2 < ratio < 3:  # drop bad-data outliers
            ratios.append((r['n_bidders'], ratio))

    if len(ratios) < 100:
        logger.error(f"Not enough tenders for the win-ratio model ({len(ratios)}).")
        return
    path = os.path.join(ML_DIR, 'win_ratios.pkl')
    all_r = np.array([r for _, r in ratios])
    buckets = []
    for lo, hi in WIN_RATIO_BUCKETS:
        sel = np.sort(np.array([r for n, r in ratios if lo <= n <= hi]))
        if len(sel) >= 100:
            buckets.append((lo, hi, sel))
    joblib.dump({'all': np.sort(all_r), 'buckets': buckets}, path)
    logger.info(f"Win-ratio model saved to {path} ({len(ratios)} tenders)")

def train_win_ratio_model():
    asyncio.run(train_win_ratio_model_async())

if __name__ == '__main__':
    train_model()
    train_competitor_model()
    train_win_ratio_model()
