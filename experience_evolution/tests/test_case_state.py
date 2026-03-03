"""Tests for case_state.py — stagnation tracking."""

import json
from pathlib import Path

import pytest

from case_state import (
    get_active_case_ids,
    get_hard_case_ids,
    load_case_state,
    mark_stagnant_cases,
    save_case_state,
    update_case_state,
)


# ---------------------------------------------------------------------------
# update_case_state
# ---------------------------------------------------------------------------

def test_update_case_state_first_score():
    state = update_case_state({}, "dacomp-001", 50.0)
    entry = state["dacomp-001"]
    assert entry["scores"] == [50.0]
    # First score: prev=0.0, new=50.0 → 50-0=50 ≥ 1.0 → improved → count=0
    assert entry["stagnation_count"] == 0
    assert entry["status"] == "active"


def test_update_case_state_improvement_resets_stagnation():
    state = {"dacomp-001": {"scores": [30.0], "stagnation_count": 2, "status": "active"}}
    state = update_case_state(state, "dacomp-001", 35.0, improvement_threshold=1.0)
    assert state["dacomp-001"]["stagnation_count"] == 0


def test_update_case_state_no_improvement_increments():
    state = {"dacomp-001": {"scores": [30.0], "stagnation_count": 1, "status": "active"}}
    state = update_case_state(state, "dacomp-001", 30.5, improvement_threshold=1.0)
    assert state["dacomp-001"]["stagnation_count"] == 2


def test_update_case_state_records_failure_type():
    state = update_case_state({}, "dacomp-001", 0.0, failure_type="execution_error")
    assert state["dacomp-001"]["failure_type"] == "execution_error"


def test_update_case_state_failure_type_none_not_stored():
    state = update_case_state({}, "dacomp-001", 0.0, failure_type=None)
    assert "failure_type" not in state["dacomp-001"]


def test_update_case_state_score_appended():
    state = update_case_state({}, "dacomp-001", 10.0)
    state = update_case_state(state, "dacomp-001", 20.0, improvement_threshold=1.0)
    assert state["dacomp-001"]["scores"] == [10.0, 20.0]


def test_update_case_state_immutable():
    original = {}
    update_case_state(original, "dacomp-001", 0.0)
    assert original == {}


# ---------------------------------------------------------------------------
# mark_stagnant_cases
# ---------------------------------------------------------------------------

def test_mark_stagnant_at_threshold():
    state = {"dacomp-001": {"stagnation_count": 3, "status": "active"}}
    result = mark_stagnant_cases(state, stagnation_threshold=3)
    assert result["dacomp-001"]["status"] == "hard"


def test_mark_stagnant_below_threshold():
    state = {"dacomp-001": {"stagnation_count": 2, "status": "active"}}
    result = mark_stagnant_cases(state, stagnation_threshold=3)
    assert result["dacomp-001"]["status"] == "active"


def test_mark_stagnant_already_hard_stays_hard():
    state = {"dacomp-001": {"stagnation_count": 0, "status": "hard"}}
    result = mark_stagnant_cases(state, stagnation_threshold=3)
    assert result["dacomp-001"]["status"] == "hard"


def test_mark_stagnant_immutable():
    state = {"dacomp-001": {"stagnation_count": 5, "status": "active"}}
    mark_stagnant_cases(state)
    assert state["dacomp-001"]["status"] == "active"


def test_mark_stagnant_mixed():
    state = {
        "dacomp-001": {"stagnation_count": 3, "status": "active"},
        "dacomp-002": {"stagnation_count": 1, "status": "active"},
    }
    result = mark_stagnant_cases(state, stagnation_threshold=3)
    assert result["dacomp-001"]["status"] == "hard"
    assert result["dacomp-002"]["status"] == "active"


# ---------------------------------------------------------------------------
# get_active_case_ids / get_hard_case_ids
# ---------------------------------------------------------------------------

def test_get_hard_case_ids():
    state = {
        "dacomp-001": {"status": "hard"},
        "dacomp-002": {"status": "active"},
        "dacomp-003": {"status": "hard"},
    }
    assert get_hard_case_ids(state) == {"dacomp-001", "dacomp-003"}


def test_get_active_case_ids():
    state = {
        "dacomp-001": {"status": "hard"},
        "dacomp-002": {"status": "active"},
    }
    assert get_active_case_ids(state) == {"dacomp-002"}


def test_get_hard_case_ids_empty():
    assert get_hard_case_ids({}) == set()


# ---------------------------------------------------------------------------
# Stagnation pipeline simulation
# ---------------------------------------------------------------------------

def test_stagnation_marks_hard_after_three_no_improvement():
    """Simulate 3 iterations with no improvement → status becomes 'hard'."""
    state = {}
    for _ in range(3):
        state = update_case_state(state, "dacomp-022", 0.0, improvement_threshold=1.0)
    state = mark_stagnant_cases(state, stagnation_threshold=3)
    assert state["dacomp-022"]["status"] == "hard"


def test_stagnation_reset_by_improvement():
    state = {}
    for _ in range(2):
        state = update_case_state(state, "dacomp-022", 0.0, improvement_threshold=1.0)
    state = update_case_state(state, "dacomp-022", 10.0, improvement_threshold=1.0)
    state = mark_stagnant_cases(state, stagnation_threshold=3)
    assert state["dacomp-022"]["status"] == "active"
    assert state["dacomp-022"]["stagnation_count"] == 0


# ---------------------------------------------------------------------------
# save_case_state / load_case_state
# ---------------------------------------------------------------------------

def test_save_load_roundtrip(tmp_path: Path):
    state_file = tmp_path / "case_state.json"
    state = {"dacomp-001": {"scores": [1.0], "stagnation_count": 0, "status": "active"}}
    save_case_state(state, state_file)
    loaded = load_case_state(state_file)
    assert loaded == state


def test_save_case_state_atomic(tmp_path: Path):
    state_file = tmp_path / "case_state.json"
    save_case_state({"a": 1}, state_file)
    assert not list(tmp_path.glob("*.tmp"))


def test_load_case_state_missing_file(tmp_path: Path):
    result = load_case_state(tmp_path / "nonexistent.json")
    assert result == {}
