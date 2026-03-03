"""Tests for select_cases.py and classify_failures.py (I/O + mocked LLM)."""

import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from select_cases import load_case_file, select_worst_cases
from classify_failures import (
    classify_failure_type,
    load_failure_type,
    save_failure_type,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_fake_csv(path: Path, rows: list[dict]) -> None:
    """Write a minimal scores CSV for testing."""
    if not rows:
        path.write_text("instance_id,weighted_total_score\n", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# select_worst_cases
# ---------------------------------------------------------------------------

def test_select_worst_cases_basic(tmp_path: Path):
    csv_path = tmp_path / "scores.csv"
    _write_fake_csv(csv_path, [
        {"instance_id": "dacomp-001", "weighted_total_score": "80"},
        {"instance_id": "dacomp-002", "weighted_total_score": "30"},
        {"instance_id": "dacomp-003", "weighted_total_score": "50"},
    ])
    result = select_worst_cases(csv_path, n=2)
    assert result == ["dacomp-002", "dacomp-003"]


def test_select_worst_cases_n_larger_than_rows(tmp_path: Path):
    csv_path = tmp_path / "scores.csv"
    _write_fake_csv(csv_path, [
        {"instance_id": "dacomp-001", "weighted_total_score": "10"},
    ])
    result = select_worst_cases(csv_path, n=5)
    assert result == ["dacomp-001"]


def test_select_worst_cases_excludes_ids(tmp_path: Path):
    csv_path = tmp_path / "scores.csv"
    _write_fake_csv(csv_path, [
        {"instance_id": "dacomp-001", "weighted_total_score": "5"},
        {"instance_id": "dacomp-002", "weighted_total_score": "10"},
    ])
    result = select_worst_cases(csv_path, n=2, exclude_ids={"dacomp-001"})
    assert "dacomp-001" not in result
    assert "dacomp-002" in result


def test_select_worst_cases_missing_score_treated_as_zero(tmp_path: Path):
    csv_path = tmp_path / "scores.csv"
    _write_fake_csv(csv_path, [
        {"instance_id": "dacomp-001", "weighted_total_score": ""},
        {"instance_id": "dacomp-002", "weighted_total_score": "50"},
    ])
    result = select_worst_cases(csv_path, n=1)
    assert result == ["dacomp-001"]   # 0.0 < 50.0


# ---------------------------------------------------------------------------
# load_case_file
# ---------------------------------------------------------------------------

def test_load_case_file(tmp_path: Path):
    f = tmp_path / "cases.txt"
    f.write_text("dacomp-001\ndacomp-002\n\ndacomp-003\n")
    result = load_case_file(f)
    assert result == ["dacomp-001", "dacomp-002", "dacomp-003"]


# ---------------------------------------------------------------------------
# classify_failures — I/O helpers (no LLM)
# ---------------------------------------------------------------------------

def test_save_and_load_failure_type(tmp_path: Path):
    save_failure_type(tmp_path, "dacomp-001", "knowledge_gap")
    loaded = load_failure_type(tmp_path, "dacomp-001")
    assert loaded == "knowledge_gap"


def test_load_failure_type_missing(tmp_path: Path):
    assert load_failure_type(tmp_path, "dacomp-999") is None


def test_save_failure_type_creates_file(tmp_path: Path):
    save_failure_type(tmp_path, "dacomp-005", "execution_error")
    cache_file = tmp_path / "dacomp-005_failure_type.json"
    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    assert data["failure_type"] == "execution_error"


# ---------------------------------------------------------------------------
# classify_failure_type — mocked LLM
# ---------------------------------------------------------------------------

def test_classify_failure_type_returns_knowledge_gap(tmp_path: Path):
    with patch("classify_failures._call_llm", return_value="knowledge_gap"):
        result = classify_failure_type(
            "dacomp-001",
            instruction="Analyse the revenue data",
            traj_text="agent tried but missed validation step",
            rubrics_row={"completeness_percentage": "30"},
        )
    assert result == "knowledge_gap"


def test_classify_failure_type_returns_execution_error(tmp_path: Path):
    with patch("classify_failures._call_llm", return_value='{"failure_type": "execution_error", "reason": "test"}'):
        result = classify_failure_type(
            "dacomp-002",
            instruction="Run regression",
            traj_text="SyntaxError: unexpected token",
            rubrics_row={},
        )
    assert result == "execution_error"


def test_classify_failure_type_fallback_on_invalid_response():
    """If LLM returns an unrecognised label, fallback to 'knowledge_gap'."""
    with patch("classify_failures._call_llm", return_value="some_garbage_response"):
        result = classify_failure_type(
            "dacomp-003", instruction="x", traj_text="y", rubrics_row={}
        )
    assert result == "knowledge_gap"


def test_classify_failure_type_fallback_on_llm_error():
    """If LLM raises an exception, fallback to 'knowledge_gap'."""
    with patch("classify_failures._call_llm", side_effect=Exception("network error")):
        result = classify_failure_type(
            "dacomp-004", instruction="x", traj_text="y", rubrics_row={}
        )
    assert result == "knowledge_gap"
