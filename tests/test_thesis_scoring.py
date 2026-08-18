from app.thesis import SCORE_WEIGHTS, call_from_score, compute_score


def test_weights_sum_to_one():
    assert round(sum(SCORE_WEIGHTS.values()), 6) == 1.0


def test_compute_score_all_max():
    sub_scores = {"team": 100, "product": 100, "market": 100, "risk_adjustment": 100}
    assert compute_score(sub_scores) == 100.0


def test_compute_score_all_zero():
    sub_scores = {"team": 0, "product": 0, "market": 0, "risk_adjustment": 0}
    assert compute_score(sub_scores) == 0.0


def test_compute_score_weighted_correctly():
    # product is weighted 0.30 — a product-only score of 100 with everything
    # else 0 should contribute exactly 30 points, not equal weight (25).
    sub_scores = {"team": 0, "product": 100, "market": 0, "risk_adjustment": 0}
    assert compute_score(sub_scores) == 30.0


def test_call_thresholds():
    assert call_from_score(90) == "Take a meeting"
    assert call_from_score(75) == "Take a meeting"
    assert call_from_score(74.9) == "Watch"
    assert call_from_score(55) == "Watch"
    assert call_from_score(54.9) == "Pass"
    assert call_from_score(0) == "Pass"
