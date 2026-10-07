import numpy as np
import pytest

from ml.data_prep import clean_bids
from ml.train_model import fit_win_curve, WIN_CURVE_RATIO_RANGE
from tests.test_clean_tenders import bid, tender


def test_clean_bids_gives_one_row_per_bid_with_ratio_to_median():
    rows = clean_bids([tender([bid("A", 80, True), bid("B", 100), bid("C", 125)])])
    assert [(r["n_bidders"], r["ratio"], r["is_winner"]) for r in rows] == [
        (3, 0.8, True), (3, 1.0, False), (3, 1.25, False)]
    assert {r["tender_no"] for r in rows} == {"1/2025/MOH/X"}


def test_clean_bids_applies_the_same_rules_as_clean_tenders():
    assert clean_bids([tender([bid("A", 80, True)])]) == []                                  # single bidder
    assert clean_bids([tender([bid("A", 80, True), bid("B", 90, True), bid("C", 100)])]) == []  # multi-lot award
    rows = clean_bids([tender([bid("A", 80, True), bid("B", 100), bid("A", 1, offer="Alternate1"), bid("C", 0)])])
    assert len(rows) == 2


def synthetic_bids(n_tenders=400, seed=0):
    """Tenders where only a bid below the median can win (a cliff at ratio 1), 4 bidders each."""
    rng = np.random.default_rng(seed)
    rows = []
    for t in range(n_tenders):
        ratios = rng.uniform(0.5, 1.5, 4)
        winner = int(np.argmin(ratios))
        for i, r in enumerate(ratios):
            rows.append({"tender_no": f"{t}/2025/X", "n_bidders": 4, "ratio": float(r), "is_winner": i == winner})
    return rows


def test_fit_win_curve_learns_that_lower_prices_win_more():
    curve = fit_win_curve(synthetic_bids())
    X = np.array([[np.log(0.6), 4], [np.log(1.4), 4]])
    low, high = curve["model"].predict_proba(X)[:, 1]
    assert low > 0.3 > high


def test_fit_win_curve_drops_out_of_range_ratios_and_records_bidder_counts():
    lo, hi = WIN_CURVE_RATIO_RANGE
    bad = [{"tender_no": f"bad{i}/2025/X", "n_bidders": 9, "ratio": hi * 2, "is_winner": True} for i in range(60)]
    curve = fit_win_curve(synthetic_bids(100) + bad)
    assert set(curve["n_sample"]) == {4}  # the out-of-range tenders (9 bidders) are excluded


def test_bidder_counts_are_sampled_per_tender_not_per_bid():
    def tender_bids(name, n):
        return [{"tender_no": name, "n_bidders": n, "ratio": 0.8 + 0.05 * i, "is_winner": i == 0} for i in range(n)]

    bids = [b for t in range(100) for b in tender_bids(f"s{t}", 2)] + tender_bids("big", 30)
    # 100 small tenders vs 1 large one: per bid the large tender would be ~13% of rows and show up
    assert set(fit_win_curve(bids)["n_sample"]) == {2}
