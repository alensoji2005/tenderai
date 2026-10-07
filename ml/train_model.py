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
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import logging
import json
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
ML_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from ml.data_prep import clean_tenders, clean_bids
except ImportError:  # run as a script from inside ml/
    from data_prep import clean_tenders, clean_bids

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

WIN_CURVE_RATIO_RANGE = (0.05, 5)  # bid / median bid outside this is bad data
WIN_CURVE_MIN_BIDS = 1000


def fit_win_curve(bids):
    """
    Learn P(a bid wins | its price relative to the tender's median bid, number of bidders).

    Trained on every real bid, so it captures how awards really work: price matters, but
    undercutting the winner does not guarantee a win and the very lowest prices do not win
    more often. Returns {'model': classifier on [log ratio, bidders], 'n_sample': typical
    bidder counts, used to average over the unknown when the user gives no bidder count}.
    """
    lo, hi = WIN_CURVE_RATIO_RANGE
    bids = [b for b in bids if lo < b['ratio'] < hi]
    X = np.array([[np.log(b['ratio']), b['n_bidders']] for b in bids])
    y = np.array([b['is_winner'] for b in bids], dtype=int)
    model = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, random_state=0)
    model.fit(X, y)
    per_tender = {b['tender_no']: b['n_bidders'] for b in bids}  # one count per tender
    n_sample = np.quantile(list(per_tender.values()), np.linspace(0.025, 0.975, 20)).round().astype(int)
    return {'model': model, 'n_sample': n_sample}


async def train_win_curve_model_async():
    """P(win) curve: the basis of P2W win probabilities and My Bids calibration."""
    db = Prisma()
    await db.connect()
    tenders = await db.awardedtender.find_many(include={'bids': True})
    await db.disconnect()

    bids = clean_bids(tenders)
    if len(bids) < WIN_CURVE_MIN_BIDS:
        logger.error(f"Not enough bids for the win-curve model ({len(bids)}).")
        return
    path = os.path.join(ML_DIR, 'win_curve.pkl')
    joblib.dump(fit_win_curve(bids), path)
    logger.info(f"Win-curve model saved to {path} ({len(bids)} bids)")

def train_win_curve_model():
    asyncio.run(train_win_curve_model_async())

if __name__ == '__main__':
    train_model()
    train_competitor_model()
    train_win_curve_model()
