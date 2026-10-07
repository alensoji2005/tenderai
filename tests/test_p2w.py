import numpy as np
import pytest
from fastapi.testclient import TestClient

import api.main  # noqa: F401  (must load before api.ml: avoids circular import via api.auth)
from api import ml as ml_module
from api.auth import get_current_user
from api.main import app


class StubModel:
    """Stand-in win curve: a price under the typical bid wins 1.2/n of the time, above it only 0.2/n."""

    def predict_proba(self, X):
        ratio, n = np.exp(X[:, 0]), X[:, 1]
        p = np.where(ratio < 1.0, 0.6, 0.1) * 2 / n
        return np.c_[1 - p, p]


CURVE = {"model": StubModel(), "n_sample": np.array([2, 4])}

BODY = {"base_cost": 80000, "estimated_value": 100000, "title": "t", "target_probability": 40}


def use_curve(monkeypatch, curve):
    monkeypatch.setattr(ml_module, "_load", lambda name: curve if name == "win_curve.pkl" else None)


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: object()
    use_curve(monkeypatch, CURVE)
    yield TestClient(app)
    app.dependency_overrides.clear()


def post(client, **extra):
    return client.post("/api/ml/predict-p2w", json={**BODY, **extra})


def prob_at(d, bid_price):
    return next(s["win_probability"] for s in d["simulations"] if s["bid_price"] == bid_price)


def test_requires_auth():
    app.dependency_overrides.clear()
    assert TestClient(app).post("/api/ml/predict-p2w", json=BODY).status_code == 401


def test_returns_121_scenarios(client):
    sims = post(client).json()["simulations"]
    assert len(sims) == 121
    assert sims[0]["margin"] == -20.0 and sims[-1]["margin"] == 100.0


def test_probability_comes_from_the_win_curve(client):
    d = post(client, bidders=2).json()
    assert prob_at(d, 96000.0) == 60.0   # 0.96 of the typical bid, 2 bidders
    assert prob_at(d, 104000.0) == 10.0  # above the typical bid: the cliff


def test_price_above_typical_bid_wins_less_than_below(client):
    d = post(client, bidders=4).json()
    assert prob_at(d, 96000.0) > prob_at(d, 104000.0)


def test_more_bidders_lower_the_win_chance(client):
    assert prob_at(post(client, bidders=2).json(), 96000.0) > prob_at(post(client, bidders=4).json(), 96000.0)


def test_unknown_bidders_averages_over_typical_counts(client):
    # n_sample is [2, 4]: (60% + 30%) / 2
    assert prob_at(post(client).json(), 96000.0) == 45.0


def test_recommended_is_profitable_and_meets_target(client):
    d = post(client, bidders=2).json()
    rec = d["recommended"]
    assert d["target_reached"] is True
    assert rec["profit"] >= 0 and rec["win_probability"] >= 40
    meets = [s for s in d["simulations"] if s["profit"] >= 0 and s["win_probability"] >= 40]
    assert rec["profit"] == max(s["profit"] for s in meets)


def test_unreachable_target_recommends_best_expected_profit(client):
    d = post(client, target_probability=99).json()
    assert d["target_reached"] is False
    profitable = [s for s in d["simulations"] if s["profit"] >= 0]
    best_ev = max(s["win_probability"] * s["profit"] for s in profitable)
    rec = d["recommended"]
    assert rec["win_probability"] * rec["profit"] == best_ev
    assert rec["profit"] > 0  # not the zero-profit break-even bid
    assert d["conservative"]["win_probability"] == max(s["win_probability"] for s in profitable)


def test_never_recommends_loss_when_profit_possible(client):
    d = post(client).json()
    for key in ("recommended", "aggressive", "conservative"):
        assert d[key]["profit"] >= 0


def test_aggressive_is_most_profitable_option_with_half_the_target(client):
    # 4 bidders: prices under the typical bid win 30%, above only 5%; target 50% is unreachable
    d = post(client, bidders=4, target_probability=50).json()
    options = [s for s in d["simulations"] if s["profit"] >= 0 and s["win_probability"] >= 25]
    assert d["aggressive"]["profit"] == max(s["profit"] for s in options) > 0
    assert d["aggressive"]["win_probability"] == 30.0


def test_sensitivity_shows_cost_of_overestimating_the_typical_bid(client):
    d = post(client, bidders=2).json()
    s = d["recommended_sensitivity"]
    # the recommended price sits under the typical bid; if the true typical bid is 10% lower it falls off the cliff
    assert s["typical_bid_10pct_lower"] < d["recommended"]["win_probability"] <= s["typical_bid_10pct_higher"]


def test_probabilities_are_clamped(monkeypatch, client):
    class Flat:
        def __init__(self, p):
            self.p = p

        def predict_proba(self, X):
            return np.c_[1 - np.full(len(X), self.p), np.full(len(X), self.p)]

    use_curve(monkeypatch, {"model": Flat(0.0), "n_sample": np.array([3])})
    assert {s["win_probability"] for s in post(client).json()["simulations"]} == {1.0}
    use_curve(monkeypatch, {"model": Flat(1.0), "n_sample": np.array([3])})
    assert {s["win_probability"] for s in post(client).json()["simulations"]} == {99.0}


def test_untrained_model_is_400(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: object()
    monkeypatch.setattr(ml_module, "_load", lambda name: None)
    try:
        r = TestClient(app).post("/api/ml/predict-p2w", json=BODY)
        assert r.status_code == 400 and "not trained" in r.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("field,value", [("base_cost", 0), ("base_cost", -5), ("estimated_value", 0), ("bidders", 1)])
def test_rejects_invalid_inputs(client, field, value):
    assert post(client, **{field: value}).status_code == 400
