"""Track per-case improvement history across evolution iterations.

Marks cases as 'hard' (stagnant) when they show no improvement over multiple
consecutive iterations, so the pipeline can stop wasting effort on them.

State schema (case_state.json):
{
  "dacomp-022": {
    "scores": [0.0, 2.0, 2.0],
    "stagnation_count": 2,
    "failure_type": "data_limitation",
    "status": "active"   // or "hard"
  }
}

All functions are pure / immutable — they return new dicts without mutating inputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Set


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def load_case_state(state_file: Path) -> Dict:
    """Load case_state.json; return empty dict if file does not exist."""
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_case_state(state: Dict, state_file: Path) -> None:
    """Write case_state.json atomically via a .tmp file."""
    tmp = state_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(state_file)


# ---------------------------------------------------------------------------
# State updates (all return new dicts)
# ---------------------------------------------------------------------------

def update_case_state(
    state: Dict,
    case_id: str,
    new_score: float,
    failure_type: Optional[str] = None,
    improvement_threshold: float = 1.0,
) -> Dict:
    """Update state for one case after an iteration.

    Increments stagnation_count if improvement < improvement_threshold pp;
    resets to 0 if improvement is meaningful.

    Args:
        state:                 Current state dict.
        case_id:               Instance ID to update.
        new_score:             weighted_total_score from the latest agent run.
        failure_type:          Optional FailureType string to record.
        improvement_threshold: Minimum score gain (pp) to count as "improved".

    Returns:
        New state dict with updated entry for case_id.
    """
    existing = state.get(case_id, {})
    scores = list(existing.get("scores", []))
    prev_score = scores[-1] if scores else 0.0
    scores = scores + [new_score]

    improved = (new_score - prev_score) >= improvement_threshold
    stagnation_count = 0 if improved else existing.get("stagnation_count", 0) + 1

    new_entry = {
        **existing,
        "scores": scores,
        "stagnation_count": stagnation_count,
    }
    if failure_type is not None:
        new_entry["failure_type"] = failure_type
    if "status" not in new_entry:
        new_entry["status"] = "active"

    return {**state, case_id: new_entry}


def mark_stagnant_cases(
    state: Dict,
    stagnation_threshold: int = 3,
) -> Dict:
    """Set status='hard' for cases whose stagnation_count >= stagnation_threshold.

    Cases already 'hard' remain 'hard' regardless of stagnation_count.

    Returns a new state dict.
    """
    updated: Dict = {}
    for case_id, entry in state.items():
        if entry.get("stagnation_count", 0) >= stagnation_threshold:
            updated[case_id] = {**entry, "status": "hard"}
        else:
            updated[case_id] = entry
    return updated


def get_active_case_ids(state: Dict) -> Set[str]:
    """Return the set of case IDs that are not marked 'hard'."""
    return {cid for cid, entry in state.items() if entry.get("status") != "hard"}


def get_hard_case_ids(state: Dict) -> Set[str]:
    """Return the set of case IDs marked as 'hard' (stagnant)."""
    return {cid for cid, entry in state.items() if entry.get("status") == "hard"}
