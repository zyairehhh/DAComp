"""Tests for regression_guard.py — pre-write guard and surgical rollback."""

import pytest

from regression_guard import (
    HIGH_BASELINE_THRESHOLD,
    CASE_REGRESSION_THRESHOLD,
    _diff_retrieval_maps,
    find_culprit_cards,
    flag_at_risk_cases,
    run_pre_write_guard,
    tighten_keywords,
)
from factories import make_card


# ---------------------------------------------------------------------------
# _diff_retrieval_maps
# ---------------------------------------------------------------------------

def test_diff_detects_added_card():
    before = {"case-1": ["exp-da-001"]}
    after = {"case-1": ["exp-da-001", "exp-da-002"]}
    diff = _diff_retrieval_maps(before, after)
    assert "case-1" in diff
    assert diff["case-1"]["added"] == ["exp-da-002"]
    assert diff["case-1"]["removed"] == []


def test_diff_detects_removed_card():
    before = {"case-1": ["exp-da-001", "exp-da-002"]}
    after = {"case-1": ["exp-da-001"]}
    diff = _diff_retrieval_maps(before, after)
    assert diff["case-1"]["removed"] == ["exp-da-002"]


def test_diff_no_change_excluded():
    before = {"case-1": ["exp-da-001"]}
    after = {"case-1": ["exp-da-001"]}
    diff = _diff_retrieval_maps(before, after)
    assert "case-1" not in diff


def test_diff_new_case_in_after():
    before = {}
    after = {"case-1": ["exp-da-001"]}
    diff = _diff_retrieval_maps(before, after)
    assert diff["case-1"]["added"] == ["exp-da-001"]


# ---------------------------------------------------------------------------
# flag_at_risk_cases
# ---------------------------------------------------------------------------

def test_flag_at_risk_high_baseline():
    diff = {"case-1": {"added": ["exp-da-001"], "removed": []}}
    baseline = {"case-1": 75.0}
    at_risk = flag_at_risk_cases(diff, baseline, high_threshold=60.0)
    assert len(at_risk) == 1
    assert at_risk[0]["case_id"] == "case-1"
    assert at_risk[0]["added_card_ids"] == ["exp-da-001"]


def test_flag_at_risk_low_baseline_ignored():
    diff = {"case-1": {"added": ["exp-da-001"], "removed": []}}
    baseline = {"case-1": 40.0}
    at_risk = flag_at_risk_cases(diff, baseline, high_threshold=60.0)
    assert at_risk == []


def test_flag_at_risk_only_added_triggers():
    diff = {"case-1": {"added": [], "removed": ["exp-da-001"]}}
    baseline = {"case-1": 80.0}
    at_risk = flag_at_risk_cases(diff, baseline, high_threshold=60.0)
    assert at_risk == []


def test_flag_at_risk_sorted_by_baseline_desc():
    diff = {
        "case-1": {"added": ["exp-da-001"], "removed": []},
        "case-2": {"added": ["exp-da-002"], "removed": []},
    }
    baseline = {"case-1": 65.0, "case-2": 90.0}
    at_risk = flag_at_risk_cases(diff, baseline, high_threshold=60.0)
    assert at_risk[0]["case_id"] == "case-2"  # higher baseline first


# ---------------------------------------------------------------------------
# tighten_keywords
# ---------------------------------------------------------------------------

def test_tighten_keywords_removes_non_discriminating():
    """Keyword that hits at-risk but NOT source instructions → removed."""
    card = make_card(
        keywords=["revenue", "growth", "metric", "validate", "analysis"],
        priority=3,
    )
    at_risk_instrs = ["calculate revenue growth for all segments"]
    source_instrs = ["validate metric for cohort analysis"]  # no "revenue"

    tightened = tighten_keywords(card, at_risk_instrs, source_instrs)
    assert "revenue" not in tightened["keywords"]
    assert "growth" not in tightened["keywords"]
    assert tightened is not card  # new dict returned


def test_tighten_keywords_keeps_discriminating():
    """Keyword that hits source instructions is kept even if it also hits at-risk."""
    card = make_card(
        keywords=["validate", "metric", "cohort", "analysis", "data"],
        priority=3,
    )
    at_risk_instrs = ["validate data for segments"]
    source_instrs = ["validate metric for cohort analysis"]  # "validate" appears here too

    tightened = tighten_keywords(card, at_risk_instrs, source_instrs)
    assert "validate" in tightened["keywords"]


def test_tighten_keywords_minimum_guard():
    """If tightening would leave < 3 keywords, return original card unchanged."""
    card = make_card(
        keywords=["revenue", "growth"],   # only 2 keywords
        priority=3,
    )
    at_risk_instrs = ["revenue growth"]
    source_instrs = ["cohort metric"]

    result = tighten_keywords(card, at_risk_instrs, source_instrs)
    assert result is card  # unchanged


def test_tighten_keywords_no_at_risk_instrs():
    """No at-risk instructions → return original card unchanged."""
    card = make_card(keywords=["a", "b", "c", "d", "e"], priority=3)
    result = tighten_keywords(card, [], ["source instr"])
    assert result is card


def test_tighten_keywords_immutable():
    card = make_card(keywords=["revenue", "growth", "metric", "validate", "analysis"])
    original_keywords = list(card["keywords"])
    tighten_keywords(card, ["revenue growth metric"], ["validate analysis"])
    assert card["keywords"] == original_keywords  # original unchanged


# ---------------------------------------------------------------------------
# run_pre_write_guard
# ---------------------------------------------------------------------------

def _make_strong_candidate(card_id: str, keyword: str, source_cases: list = None) -> dict:
    return make_card(
        card_id=card_id,
        keywords=[keyword, f"{keyword}_rate", "analyse", "metric", "validate"],
        tags=["analysis"],
        priority=3,
        source_cases=source_cases or [],
    )


def test_run_pre_write_guard_no_risk():
    """Candidate card that doesn't affect any high-baseline case → unchanged."""
    candidate = _make_strong_candidate("exp-da-001", "cohort")
    baseline = {"case-1": 10.0}  # low baseline → not at risk
    tasks = {"case-1": "cohort metric analyse validate analysis"}

    result = run_pre_write_guard([candidate], [], tasks, baseline, high_threshold=60.0)
    assert result.blocked_card_ids == []
    assert result.tightened_card_ids == []
    assert len(result.refined_cards) == 1


def test_run_pre_write_guard_at_risk_detected():
    """Candidate affecting a high-baseline case is flagged in at_risk_cases."""
    candidate = _make_strong_candidate("exp-da-001", "revenue",
                                        source_cases=["dacomp-099"])
    baseline = {"case-1": 80.0}
    tasks = {
        "case-1": "revenue metric analyse validate analysis",   # high baseline, candidate hits
        "dacomp-099": "completely different unrelated task",   # source case
    }

    result = run_pre_write_guard([candidate], [], tasks, baseline, high_threshold=60.0)
    assert "case-1" in result.at_risk_cases


def test_run_pre_write_guard_no_auto_tighten():
    """With auto_tighten=False, at-risk cards are kept unchanged."""
    candidate = _make_strong_candidate("exp-da-001", "revenue")
    baseline = {"case-1": 80.0}
    tasks = {"case-1": "revenue metric analyse validate analysis"}

    result = run_pre_write_guard(
        [candidate], [], tasks, baseline, high_threshold=60.0, auto_tighten=False
    )
    assert result.tightened_card_ids == []
    assert len(result.refined_cards) == 1


# ---------------------------------------------------------------------------
# find_culprit_cards
# ---------------------------------------------------------------------------

def test_find_culprit_cards_identifies_regression():
    """Card retrieved for a regressed high-baseline case → culprit."""
    card = _make_strong_candidate("exp-da-001", "revenue")
    deltas = {"case-1": -20.0}        # severe regression
    baseline = {"case-1": 70.0}       # high baseline
    tasks = {"case-1": "revenue metric analyse validate analysis"}

    culprits = find_culprit_cards(deltas, [card], tasks, baseline,
                                   high_threshold=60.0, case_regression_threshold=-15.0)
    assert "exp-da-001" in culprits


def test_find_culprit_cards_low_regression_ignored():
    """Small regression (above threshold) → card not a culprit."""
    card = _make_strong_candidate("exp-da-001", "revenue")
    deltas = {"case-1": -5.0}         # minor regression (threshold is -15)
    baseline = {"case-1": 70.0}
    tasks = {"case-1": "revenue metric analyse validate analysis"}

    culprits = find_culprit_cards(deltas, [card], tasks, baseline,
                                   high_threshold=60.0, case_regression_threshold=-15.0)
    assert culprits == set()


def test_find_culprit_cards_low_baseline_ignored():
    """Severe regression but baseline was low → not a protected case."""
    card = _make_strong_candidate("exp-da-001", "revenue")
    deltas = {"case-1": -20.0}
    baseline = {"case-1": 30.0}       # low baseline → not protected
    tasks = {"case-1": "revenue metric analyse validate analysis"}

    culprits = find_culprit_cards(deltas, [card], tasks, baseline,
                                   high_threshold=60.0, case_regression_threshold=-15.0)
    assert culprits == set()


def test_find_culprit_cards_returns_set():
    result = find_culprit_cards({}, [], {}, {})
    assert isinstance(result, set)
