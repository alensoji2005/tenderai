import datetime
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api.main  # noqa: F401  (must load before api.ml: avoids circular import via api.auth)
from api import ml as ml_module
from api import mybids
from api.auth import get_current_user
from api.main import app



class HalfModel:
    """Stand-in win curve: every price wins 50%."""

    def predict_proba(self, X):
        return np.full((len(X), 2), 0.5)


CURVE = {"model": HalfModel(), "n_sample": np.array([3])}
BID = {"tender_no": "T1", "title": "Poles", "our_price": 100000, "base_cost": 80000}


class FakeMyBid:
    """In-memory stand-in for prisma's db.mybid."""

    def __init__(self):
        self.rows, self.next_id = {}, 1

    async def create(self, data):
        row = SimpleNamespace(id=self.next_id, result="pending", winning_price=None,
                              created_at=datetime.datetime(2026, 1, 1), **data)
        self.rows[row.id] = row
        self.next_id += 1
        return row

    async def find_many(self, order=None):
        return list(self.rows.values())

    async def update(self, where, data):
        row = self.rows.get(where["id"])
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        return row

    async def delete(self, where):
        return self.rows.pop(where["id"], None)


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: object()
    monkeypatch.setattr(ml_module, "_load", lambda name: CURVE if name == "win_curve.pkl" else None)
    monkeypatch.setattr(mybids, "db", SimpleNamespace(mybid=FakeMyBid()))
    yield TestClient(app)
    app.dependency_overrides.clear()


def row(predicted, result, price=100, cost=80):
    return {"predicted_probability": predicted, "result": result, "our_price": price, "base_cost": cost}


def test_requires_auth():
    app.dependency_overrides.clear()
    assert TestClient(app).get("/api/my-bids/").status_code == 401


def test_predicted_probability_computed_from_model(client):
    d = client.post("/api/my-bids/", json={**BID, "typical_bid": 100000}).json()
    assert d["predicted_probability"] == 50.0


def test_prediction_uses_price_relative_to_typical_bid(client, monkeypatch):
    class Cliff:
        def predict_proba(self, X):
            p = np.where(np.exp(X[:, 0]) < 1.0, 0.8, 0.1)
            return np.c_[1 - p, p]

    monkeypatch.setattr(ml_module, "_load", lambda name: {"model": Cliff(), "n_sample": np.array([3])})
    under = client.post("/api/my-bids/", json={**BID, "our_price": 90000, "typical_bid": 100000}).json()
    over = client.post("/api/my-bids/", json={**BID, "our_price": 110000, "typical_bid": 100000}).json()
    assert (under["predicted_probability"], over["predicted_probability"]) == (80.0, 10.0)


def test_given_prediction_is_kept_and_missing_typical_bid_gives_none(client):
    d = client.post("/api/my-bids/", json={**BID, "predicted_probability": 72.5}).json()
    assert d["predicted_probability"] == 72.5
    d = client.post("/api/my-bids/", json=BID).json()
    assert d["predicted_probability"] is None


@pytest.mark.parametrize("extra", [
    {"our_price": 0}, {"base_cost": -1}, {"typical_bid": 0}, {"bidders": 1}, {"predicted_probability": 101},
])
def test_create_rejects_bad_input(client, extra):
    assert client.post("/api/my-bids/", json={**BID, **extra}).status_code == 400


def test_result_flow_and_validation(client):
    bid_id = client.post("/api/my-bids/", json=BID).json()["id"]
    r = client.patch(f"/api/my-bids/{bid_id}/result", json={"result": "lost", "winning_price": 90000})
    assert r.status_code == 200 and r.json()["result"] == "lost" and r.json()["winning_price"] == 90000
    assert client.patch(f"/api/my-bids/{bid_id}/result", json={"result": "maybe"}).status_code == 400
    assert client.patch(f"/api/my-bids/{bid_id}/result", json={"result": "lost", "winning_price": 0}).status_code == 400
    assert client.patch("/api/my-bids/999/result", json={"result": "won"}).status_code == 404


def test_delete(client):
    bid_id = client.post("/api/my-bids/", json=BID).json()["id"]
    assert client.delete(f"/api/my-bids/{bid_id}").status_code == 200
    assert client.get("/api/my-bids/").json()["count"] == 0
    assert client.delete(f"/api/my-bids/{bid_id}").status_code == 404


def test_calibration_endpoint(client):
    for result in ("won", "lost"):
        bid_id = client.post("/api/my-bids/", json={**BID, "predicted_probability": 60}).json()["id"]
        client.patch(f"/api/my-bids/{bid_id}/result", json={"result": result})
    d = client.get("/api/my-bids/calibration").json()
    assert d["won"] == 1 and d["lost"] == 1 and d["win_rate"] == 50.0


def test_calibration_empty():
    d = mybids.calibration([])
    assert d["total"] == 0 and d["win_rate"] is None and d["brier"] is None and d["buckets"] == []


def test_calibration_counts_and_profit_and_ignores_pending():
    d = mybids.calibration([row(80, "won", 100, 70), row(80, "lost"), row(30, "pending")])
    assert (d["total"], d["won"], d["lost"], d["pending"]) == (3, 1, 1, 1)
    assert d["win_rate"] == 50.0
    assert d["realised_profit"] == 30  # only the won bid counts
    assert d["scored"] == 2


def test_calibration_brier_and_buckets():
    # won at 80% -> (0.8-1)^2 = 0.04; lost at 80% -> 0.64; lost at 10% -> 0.01
    d = mybids.calibration([row(80, "won"), row(80, "lost"), row(10, "lost")])
    assert d["brier"] == pytest.approx((0.04 + 0.64 + 0.01) / 3, abs=1e-4)
    by_range = {b["range"]: b for b in d["buckets"]}
    assert by_range["75-100%"] == {"range": "75-100%", "n": 2, "predicted": 80.0, "actual": 50.0}
    assert by_range["0-25%"]["actual"] == 0.0


def test_calibration_skips_bids_without_prediction():
    d = mybids.calibration([row(None, "won"), row(None, "lost")])
    assert d["won"] == 1 and d["scored"] == 0 and d["brier"] is None


def test_calibration_bucket_edges_belong_to_upper_bucket():
    d = mybids.calibration([row(25, "won"), row(50, "won"), row(75, "won"), row(100, "won")])
    assert {b["range"]: b["n"] for b in d["buckets"]} == {"25-50%": 1, "50-75%": 1, "75-100%": 2}
