import numpy as np
import pytest
from fastapi.testclient import TestClient

import api.main  # noqa: F401  (must load before api.ml: avoids circular import via api.auth)
from api import ml as ml_module
from api.auth import get_current_user
from api.main import app

# Winners historically bid between 0.5x and 1.5x of the median bid
OVERALL = np.linspace(0.5, 1.5, 1001)
LOW_COMPETITION = np.linspace(0.8, 1.6, 801)   # few bidders: winners price higher
HIGH_COMPETITION = np.linspace(0.4, 1.0, 601)  # many bidders: winners price lower
MODEL = {"all": OVERALL, "buckets": [(2, 3, LOW_COMPETITION), (10, 10**6, HIGH_COMPETITION)]}

BODY = {"base_cost": 80000, "estimated_value": 100000, "title": "t", "target_probability": 60}


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: object()
    monkeypatch.setattr(ml_module, "_load", lambda name: MODEL if name == "win_ratios.pkl" else None)
    yield TestClient(app)
    app.dependency_overrides.clear()


def post(client, **extra):
    return client.post("/api/ml/predict-p2w", json={**BODY, **extra})


def test_requires_auth():
    app.dependency_overrides.clear()
    assert TestClient(app).post("/api/ml/predict-p2w", json=BODY).status_code == 401


def test_returns_121_scenarios(client):
    sims = post(client).json()["simulations"]
    assert len(sims) == 121
    assert sims[0]["margin"] == -20.0 and sims[-1]["margin"] == 100.0


def test_probability_never_rises_with_price(client):
    probs = [s["win_probability"] for s in post(client).json()["simulations"]]
    assert all(a >= b for a, b in zip(probs, probs[1:]))
    assert all(1.0 <= p <= 99.0 for p in probs)


def test_probability_matches_empirical_share(client):
    sims = post(client).json()["simulations"]
    at_cost = next(s for s in sims if s["margin"] == 0.0)  # r = 0.8: ~70% of winners bid above
    assert at_cost["win_probability"] == pytest.approx(70.0, abs=1.0)


def test_recommended_is_profitable_and_meets_target(client):
    d = post(client).json()
    rec = d["recommended"]
    assert rec["profit"] >= 0 and rec["win_probability"] >= 60
    meets = [s for s in d["simulations"] if s["profit"] >= 0 and s["win_probability"] >= 60]
    assert rec["profit"] == max(s["profit"] for s in meets)


def test_unreachable_target_falls_back_to_most_likely_profitable(client):
    d = post(client, target_probability=99).json()
    best = max(s["win_probability"] for s in d["simulations"] if s["profit"] >= 0)
    assert d["recommended"]["win_probability"] == best
    assert d["conservative"]["win_probability"] == best


def test_never_recommends_loss_when_profit_possible(client):
    d = post(client).json()
    for key in ("recommended", "aggressive", "conservative"):
        assert d[key]["profit"] >= 0


def test_bidders_selects_bucket(client):
    base = {s["margin"]: s["win_probability"] for s in post(client).json()["simulations"]}
    low = {s["margin"]: s["win_probability"] for s in post(client, bidders=2).json()["simulations"]}
    high = {s["margin"]: s["win_probability"] for s in post(client, bidders=15).json()["simulations"]}
    assert low[0.0] > base[0.0] > high[0.0]


def test_unbucketed_bidder_count_uses_overall(client):
    base = post(client).json()["simulations"]
    assert post(client, bidders=5).json()["simulations"] == base


def test_untrained_model_is_400(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: object()
    monkeypatch.setattr(ml_module, "_load", lambda name: None)
    r = TestClient(app).post("/api/ml/predict-p2w", json=BODY)
    app.dependency_overrides.clear()
    assert r.status_code == 400 and "not trained" in r.json()["detail"]


@pytest.mark.parametrize("field", ["base_cost", "estimated_value"])
def test_rejects_non_positive_inputs(client, field):
    assert post(client, **{field: 0}).status_code == 400


def test_aggressive_is_most_profitable_option_with_at_least_30_percent(client):
    d = post(client).json()
    agg = d["aggressive"]
    eligible = [s for s in d["simulations"] if s["profit"] >= 0 and s["win_probability"] >= 30]
    assert agg["win_probability"] >= 30
    assert agg["profit"] == max(s["profit"] for s in eligible)
    assert agg["profit"] > d["recommended"]["profit"]  # riskier pick earns more than the 60% target pick
