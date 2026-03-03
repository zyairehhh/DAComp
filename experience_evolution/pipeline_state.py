"""Checkpoint I/O for the experience card self-evolution pipeline.

All checkpoint files live under <run_dir>/iter{N}/:

  iter1/
    synthesis_cache.json   -- Step 3 LLM synthesis result
    guard_cache.json       -- Step 4.5 GuardResult (refined_cards with temp IDs stripped)
    cards_written.json     -- Step 5 written added_ids (idempotency sentinel)
    iter_complete.json     -- Full iteration done; contains agent_results_dir / new_scores_csv
    patterns/              -- Per-case pattern files (replaces top-level patterns/ rename)

All writes are atomic: write to .tmp then rename, same pattern as card_utils.save_index.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: Any) -> None:
    """Atomic JSON write: write to .tmp then rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> Optional[Any]:
    """Return parsed JSON or None if file is missing / corrupt."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# Iteration directory
# ---------------------------------------------------------------------------

def iter_dir(base_dir: Path, iteration: int) -> Path:
    """Return <base_dir>/iter{N}/, creating it (and iter{N}/patterns/) if needed."""
    d = base_dir / f"iter{iteration}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "patterns").mkdir(exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Step 3: synthesis cache
# ---------------------------------------------------------------------------

def load_synthesis_cache(idir: Path) -> Optional[List[Dict]]:
    """Return cached synthesized cards, or None if not cached."""
    data = _read_json(idir / "synthesis_cache.json")
    if data is None:
        return None
    return data.get("synthesized_cards")


def save_synthesis_cache(
    idir: Path,
    iteration: int,
    case_ids: List[str],
    synthesized: List[Dict],
) -> None:
    _write_json(idir / "synthesis_cache.json", {
        "schema_version": 1,
        "iteration": iteration,
        "case_ids": case_ids,
        "synthesized_cards": synthesized,
        "timestamp": _ts(),
    })


# ---------------------------------------------------------------------------
# Step 4.5: guard cache
# ---------------------------------------------------------------------------

def load_guard_cache(idir: Path) -> Optional[Dict]:
    """Return guard cache dict (with 'refined_cards' key), or None if not cached."""
    return _read_json(idir / "guard_cache.json")


def save_guard_cache(idir: Path, iteration: int, guard_result: Any) -> None:
    """Serialize a GuardResult dataclass to JSON.

    refined_cards must have temp IDs already stripped by the caller before this
    call, so that write_new_cards() can assign fresh real IDs on resume.
    """
    _write_json(idir / "guard_cache.json", {
        "schema_version": 1,
        "iteration": iteration,
        "refined_cards": guard_result.refined_cards,
        "tightened_card_ids": guard_result.tightened_card_ids,
        "blocked_card_ids": guard_result.blocked_card_ids,
        "at_risk_cases": guard_result.at_risk_cases,
        "timestamp": _ts(),
    })


# ---------------------------------------------------------------------------
# Step 5: cards written sentinel
# ---------------------------------------------------------------------------

def load_cards_written(idir: Path) -> Optional[List[str]]:
    """Return added_ids if cards were already written this iteration, else None."""
    data = _read_json(idir / "cards_written.json")
    if data is None:
        return None
    return data.get("added_ids")


def save_cards_written(idir: Path, iteration: int, added_ids: List[str]) -> None:
    _write_json(idir / "cards_written.json", {
        "schema_version": 1,
        "iteration": iteration,
        "added_ids": added_ids,
        "timestamp": _ts(),
    })


# ---------------------------------------------------------------------------
# Iteration complete sentinel
# ---------------------------------------------------------------------------

def mark_iter_complete(
    idir: Path,
    iteration: int,
    *,
    kept: bool,
    added_ids: List[str],
    avg_delta: float,
    agent_results_dir: Path,
    new_scores_csv: Path,
) -> None:
    """Write iter_complete.json. Called at the very end of run_pipeline().

    Written even when kept=False (rollback case) so the iteration is not
    re-run on restart.  agent_results_dir and new_scores_csv are stored as
    absolute path strings for cross-iteration chaining on resume.
    """
    _write_json(idir / "iter_complete.json", {
        "schema_version": 1,
        "iteration": iteration,
        "kept": kept,
        "added_ids": added_ids,
        "avg_delta": round(float(avg_delta), 4),
        "agent_results_dir": str(agent_results_dir.resolve()),
        "new_scores_csv": str(new_scores_csv.resolve()),
        "timestamp": _ts(),
    })


def load_iter_complete(idir: Path) -> Optional[Dict]:
    """Return the complete record for this iteration, or None."""
    return _read_json(idir / "iter_complete.json")


def is_iter_complete(base_dir: Path, iteration: int) -> bool:
    """Fast check: True if iter{N}/iter_complete.json exists."""
    return (base_dir / f"iter{iteration}" / "iter_complete.json").exists()
