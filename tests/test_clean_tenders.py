import pytest

from types import SimpleNamespace as NS

from ml.data_prep import clean_tenders, is_sane_amount


def bid(company, value, winner=False, offer="Main"):
    return NS(company_name=company, total_quoted_value=value, is_winner=winner, offer_type=offer)


def tender(bids, no="1/2025/MOH/X"):
    return NS(tender_no=no, tender_title="t", entity_name="e", category_grade="g", bids=bids)


def one(bids):
    rows = clean_tenders([tender(bids)])
    return rows[0] if rows else None


def test_keeps_clean_tender_and_computes_stats():
    r = one([bid("A", 80, True), bid("B", 100), bid("C", 120)])
    assert r["n_bidders"] == 3
    assert r["winning_bid"] == 80
    assert r["median_bid"] == 100
    assert r["mean_bid"] == 100


def test_ignores_alternate_offers():
    r = one([bid("A", 80, True), bid("B", 100), bid("A", 1, offer="Alternate1")])
    assert r["n_bidders"] == 2 and r["winning_bid"] == 80


def test_ignores_zero_negative_and_absurd_values():
    r = one([bid("A", 80, True), bid("B", 100), bid("C", 0), bid("D", -5), bid("E", 1e9)])
    assert r["n_bidders"] == 2


def test_one_row_per_company_keeps_lowest():
    r = one([bid("A", 90, True), bid("A", 70), bid("B", 100)])
    assert r["n_bidders"] == 2 and r["winning_bid"] == 70


def test_needs_two_distinct_bidders():
    assert one([bid("A", 80, True), bid("A", 90)]) is None
    assert one([bid("A", 80, True)]) is None


def test_drops_multi_lot_awards():
    assert one([bid("A", 80, True), bid("B", 90, True), bid("C", 100)]) is None


def test_drops_tender_without_priced_winner():
    assert one([bid("A", 80), bid("B", 90)]) is None
    assert one([bid("A", 0, True), bid("B", 90), bid("C", 95)]) is None


def test_handles_missing_bids():
    assert clean_tenders([tender(None), tender([])]) == []


def test_median_differs_from_mean_on_skewed_bids():
    r = one([bid("A", 80, True), bid("B", 100), bid("C", 300)])
    assert r["median_bid"] == 100
    assert r["mean_bid"] == pytest.approx(160)


@pytest.mark.parametrize("value,ok", [(1, True), (1e8, True), (0, False), (-5, False), (1e8 + 1, False), (None, False)])
def test_is_sane_amount(value, ok):
    assert is_sane_amount(value) is ok
