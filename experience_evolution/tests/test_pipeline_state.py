"""Tests for pipeline_state.py — checkpoint I/O for the evolution pipeline."""

import json
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline_state import (
    iter_dir,
    load_synthesis_cache,
    save_synthesis_cache,
    load_guard_cache,
    save_guard_cache,
    load_cards_written,
    save_cards_written,
    mark_iter_complete,
    load_iter_complete,
    is_iter_complete,
)


# ---------------------------------------------------------------------------
# Minimal GuardResult stub (mirrors regression_guard.GuardResult dataclass)
# ---------------------------------------------------------------------------

class _GuardResult:
    def __init__(self, refined_cards, tightened_card_ids, blocked_card_ids, at_risk_cases):
        self.refined_cards = refined_cards
        self.tightened_card_ids = tightened_card_ids
        self.blocked_card_ids = blocked_card_ids
        self.at_risk_cases = at_risk_cases


def _make_guard_result(cards=None):
    return _GuardResult(
        refined_cards=cards or [{"title": "Test Card", "keywords": ["a", "b", "c"]}],
        tightened_card_ids=["exp-da-tmp-001"],
        blocked_card_ids=[],
        at_risk_cases={"dacomp-010": ["exp-da-tmp-001"]},
    )


def _make_synthesized():
    return [
        {"title": "Card One", "keywords": ["x", "y", "z"], "when_to_use": "When testing"},
        {"title": "Card Two", "keywords": ["a", "b", "c"], "when_to_use": "When analysing"},
    ]


# ---------------------------------------------------------------------------
# iter_dir
# ---------------------------------------------------------------------------

def test_iter_dir_creates_subdir(tmp_path):
    d = iter_dir(tmp_path, 1)
    assert d == tmp_path / "iter1"
    assert d.is_dir()


def test_iter_dir_creates_patterns_subdir(tmp_path):
    d = iter_dir(tmp_path, 2)
    assert (d / "patterns").is_dir()


def test_iter_dir_idempotent(tmp_path):
    """Calling iter_dir twice must not raise."""
    iter_dir(tmp_path, 1)
    d = iter_dir(tmp_path, 1)
    assert d.is_dir()


# ---------------------------------------------------------------------------
# synthesis cache
# ---------------------------------------------------------------------------

def test_synthesis_cache_none_initially(tmp_path):
    idir = iter_dir(tmp_path, 1)
    assert load_synthesis_cache(idir) is None


def test_synthesis_cache_roundtrip(tmp_path):
    idir = iter_dir(tmp_path, 1)
    cards = _make_synthesized()
    save_synthesis_cache(idir, 1, ["dacomp-022", "dacomp-034"], cards)
    loaded = load_synthesis_cache(idir)
    assert loaded == cards


def test_synthesis_cache_file_schema(tmp_path):
    idir = iter_dir(tmp_path, 1)
    save_synthesis_cache(idir, 1, ["dacomp-001"], _make_synthesized())
    data = json.loads((idir / "synthesis_cache.json").read_text())
    assert data["schema_version"] == 1
    assert data["iteration"] == 1
    assert data["case_ids"] == ["dacomp-001"]
    assert "timestamp" in data


def test_synthesis_cache_atomic_write(tmp_path):
    """No .tmp file should remain after a successful write."""
    idir = iter_dir(tmp_path, 1)
    save_synthesis_cache(idir, 1, [], _make_synthesized())
    assert not (idir / "synthesis_cache.json.tmp").exists()


# ---------------------------------------------------------------------------
# guard cache
# ---------------------------------------------------------------------------

def test_guard_cache_none_initially(tmp_path):
    idir = iter_dir(tmp_path, 1)
    assert load_guard_cache(idir) is None


def test_guard_cache_roundtrip(tmp_path):
    idir = iter_dir(tmp_path, 1)
    gr = _make_guard_result()
    save_guard_cache(idir, 1, gr)
    data = load_guard_cache(idir)
    assert data is not None
    assert data["refined_cards"] == gr.refined_cards
    assert data["tightened_card_ids"] == gr.tightened_card_ids
    assert data["blocked_card_ids"] == gr.blocked_card_ids
    assert data["at_risk_cases"] == gr.at_risk_cases


def test_guard_cache_file_schema(tmp_path):
    idir = iter_dir(tmp_path, 1)
    save_guard_cache(idir, 1, _make_guard_result())
    data = json.loads((idir / "guard_cache.json").read_text())
    assert data["schema_version"] == 1
    assert "timestamp" in data


def test_guard_cache_atomic_write(tmp_path):
    idir = iter_dir(tmp_path, 1)
    save_guard_cache(idir, 1, _make_guard_result())
    assert not (idir / "guard_cache.json.tmp").exists()


# ---------------------------------------------------------------------------
# cards written sentinel
# ---------------------------------------------------------------------------

def test_cards_written_none_initially(tmp_path):
    idir = iter_dir(tmp_path, 1)
    assert load_cards_written(idir) is None


def test_cards_written_roundtrip(tmp_path):
    idir = iter_dir(tmp_path, 1)
    ids = ["exp-da-045", "exp-da-046"]
    save_cards_written(idir, 1, ids)
    assert load_cards_written(idir) == ids


def test_cards_written_empty_list(tmp_path):
    idir = iter_dir(tmp_path, 1)
    save_cards_written(idir, 1, [])
    assert load_cards_written(idir) == []


def test_cards_written_atomic_write(tmp_path):
    idir = iter_dir(tmp_path, 1)
    save_cards_written(idir, 1, ["exp-da-001"])
    assert not (idir / "cards_written.json.tmp").exists()


# ---------------------------------------------------------------------------
# iter_complete
# ---------------------------------------------------------------------------

def test_is_iter_complete_false_before_write(tmp_path):
    assert not is_iter_complete(tmp_path, 1)


def test_is_iter_complete_true_after_write(tmp_path):
    idir = iter_dir(tmp_path, 1)
    mark_iter_complete(
        idir, 1, kept=True, added_ids=["exp-da-045"],
        avg_delta=3.4,
        agent_results_dir=tmp_path / "agent_results",
        new_scores_csv=tmp_path / "scores.csv",
    )
    assert is_iter_complete(tmp_path, 1)


def test_iter_complete_roundtrip(tmp_path):
    idir = iter_dir(tmp_path, 1)
    agent_dir = tmp_path / "agent_results" / "deepseek-v3.2-evolve_iter1"
    scores_csv = tmp_path / "model_scores" / "scores.csv"
    mark_iter_complete(
        idir, 1, kept=True, added_ids=["exp-da-045"],
        avg_delta=3.4,
        agent_results_dir=agent_dir,
        new_scores_csv=scores_csv,
    )
    data = load_iter_complete(idir)
    assert data is not None
    assert data["kept"] is True
    assert data["added_ids"] == ["exp-da-045"]
    assert data["avg_delta"] == 3.4
    assert data["agent_results_dir"] == str(agent_dir.resolve())
    assert data["new_scores_csv"] == str(scores_csv.resolve())


def test_iter_complete_rollback_case(tmp_path):
    """kept=False and empty added_ids should be stored without error."""
    idir = iter_dir(tmp_path, 1)
    mark_iter_complete(
        idir, 1, kept=False, added_ids=[],
        avg_delta=-5.0,
        agent_results_dir=tmp_path / "agent",
        new_scores_csv=tmp_path / "scores.csv",
    )
    data = load_iter_complete(idir)
    assert data["kept"] is False
    assert data["added_ids"] == []


def test_iter_complete_file_schema(tmp_path):
    idir = iter_dir(tmp_path, 1)
    mark_iter_complete(
        idir, 1, kept=True, added_ids=[],
        avg_delta=0.0,
        agent_results_dir=tmp_path / "a",
        new_scores_csv=tmp_path / "b",
    )
    data = json.loads((idir / "iter_complete.json").read_text())
    assert data["schema_version"] == 1
    assert "timestamp" in data


def test_load_iter_complete_none_before_write(tmp_path):
    idir = iter_dir(tmp_path, 1)
    assert load_iter_complete(idir) is None


def test_is_iter_complete_only_checks_correct_iter(tmp_path):
    """Completing iter1 must not affect is_iter_complete check for iter2."""
    idir = iter_dir(tmp_path, 1)
    mark_iter_complete(
        idir, 1, kept=True, added_ids=[],
        avg_delta=0.0,
        agent_results_dir=tmp_path / "a",
        new_scores_csv=tmp_path / "b",
    )
    assert is_iter_complete(tmp_path, 1)
    assert not is_iter_complete(tmp_path, 2)
