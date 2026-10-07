"""
Out-of-time check of the win-probability model: train on older tenders, test on the newest year.

    python -m ml.evaluate

Compares the model with trivial baselines on real bids it has not seen, and prints a reliability
table (predicted vs actual win rate). Lower Brier / log-loss is better; the calibration gap is the
average distance between predicted and actual win rate across probability buckets.
"""
import asyncio

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from prisma import Prisma

from ml.data_prep import clean_bids
from ml.train_model import fit_win_curve, WIN_CURVE_RATIO_RANGE

PROB_BUCKETS = [0, .1, .25, .5, .75, 1.0]


def tender_year(tender_no):
    """Tender numbers look like 'X/2026/123'; the middle part is the year."""
    try:
        return int(tender_no.split('/')[1])
    except (IndexError, ValueError):
        return None


def score(name, p, y):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    brier = float(np.mean((p - y) ** 2))
    logloss = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    df = pd.DataFrame({'p': p, 'y': y})
    t = df.groupby(pd.cut(df.p, PROB_BUCKETS), observed=True).agg(n=('y', 'size'), predicted=('p', 'mean'), actual=('y', 'mean'))
    gap = float((t.n * (t.predicted - t.actual).abs()).sum() / t.n.sum())
    print(f"{name:28s} Brier {brier:.4f}   log-loss {logloss:.4f}   calibration gap {gap:.3f}")
    return t


def evaluate(bids):
    lo, hi = WIN_CURVE_RATIO_RANGE
    bids = [dict(b, year=tender_year(b['tender_no'])) for b in bids if lo < b['ratio'] < hi]
    years = sorted({b['year'] for b in bids if b['year']})
    test_year = years[-1]
    train = [b for b in bids if b['year'] and b['year'] < test_year]
    test = [b for b in bids if b['year'] == test_year]
    print(f"train: {len(train)} bids before {test_year}; test: {len(test)} bids from {test_year}\n")

    y = np.array([b['is_winner'] for b in test], dtype=float)
    n = np.array([b['n_bidders'] for b in test], dtype=float)
    base = float(np.mean([b['is_winner'] for b in train]))
    score('base rate only', np.full(len(test), base), y)
    score('1 / bidders only', 1 / n, y)

    curve = fit_win_curve(train)
    X = np.array([[np.log(b['ratio']), b['n_bidders']] for b in test])
    table = score('win-curve model', curve['model'].predict_proba(X)[:, 1], y)
    print("\nReliability of the win-curve model (does '25%' win about 25% of the time?)")
    print(table.round(3).to_string())


async def _load():
    db = Prisma()
    await db.connect()
    tenders = await db.awardedtender.find_many(include={'bids': True})
    await db.disconnect()
    return tenders


if __name__ == '__main__':
    load_dotenv()
    evaluate(clean_bids(asyncio.run(_load())))
