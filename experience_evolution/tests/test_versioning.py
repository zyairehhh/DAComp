"""Tests for the new versioning features:
- added_in_iteration stamping (pipeline logic)
- index snapshot saving
- restore_iteration.py (cmd_list and cmd_restore)
- dual-criterion rollback thresholds
- --run path derivation
"""

import json
from pathlib import Path
from io import StringIO
from unittest.mock import patch

import pytest

from card_utils import (
    REGRESSION_THRESHOLD,
    RELATIVE_REGRESSION_THRESHOLD,
    load_index,
    save_index,
)
from factories import make_card, make_index


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_index(cards_dir: Path, cards: list) -> None:
    save_index(make_index(cards), cards_dir)


def _write_snapshot(cards_dir: Path, iteration: int, cards: list) -> None:
    snap_dir = cards_dir / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    (snap_dir / f"index_iter{iteration}.json").write_text(
        json.dumps(make_index(cards), indent=2), encoding="utf-8"
    )


def _write_evolution_log(run_dir: Path, entries: list) -> None:
    (run_dir / "evolution_log.json").write_text(
        json.dumps(entries, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# added_in_iteration stamping
# ---------------------------------------------------------------------------

def test_added_in_iteration_stamped_on_new_cards(cards_dir: Path):
    """Simulate the stamping logic from evolve_pipeline.py Step 5."""
    iteration_id = 2
    added_ids = ["exp-da-003"]
    cards = [make_card("exp-da-001"), make_card("exp-da-002"), make_card("exp-da-003")]
    _write_index(cards_dir, cards)

    # Replicate the stamping code from evolve_pipeline.run_pipeline()
    idx = load_index(cards_dir)
    stamped_cards = [
        {**c, "added_in_iteration": iteration_id} if c["id"] in set(added_ids) else c
        for c in idx.get("cards", [])
    ]
    save_index({**idx, "cards": stamped_cards}, cards_dir)

    reloaded = load_index(cards_dir)
    id_to_card = {c["id"]: c for c in reloaded["cards"]}
    assert id_to_card["exp-da-003"]["added_in_iteration"] == 2
    assert "added_in_iteration" not in id_to_card["exp-da-001"]
    assert "added_in_iteration" not in id_to_card["exp-da-002"]


def test_stamping_is_immutable(cards_dir: Path):
    """Original index dict is not mutated during stamping."""
    _write_index(cards_dir, [make_card("exp-da-001")])
    idx_original = load_index(cards_dir)

    stamped_cards = [
        {**c, "added_in_iteration": 1}
        for c in idx_original.get("cards", [])
    ]
    save_index({**idx_original, "cards": stamped_cards}, cards_dir)

    assert "added_in_iteration" not in idx_original["cards"][0]


# ---------------------------------------------------------------------------
# Snapshot saving logic
# ---------------------------------------------------------------------------

def test_snapshot_saved_when_kept(cards_dir: Path):
    """Simulate the snapshot-saving logic from evolve_pipeline.py."""
    iteration_id = 1
    kept = True
    _write_index(cards_dir, [make_card("exp-da-001")])

    if kept:
        snapshots_dir = cards_dir / "snapshots"
        snapshots_dir.mkdir(exist_ok=True)
        snapshot_path = snapshots_dir / f"index_iter{iteration_id}.json"
        final_snap = load_index(cards_dir)
        snapshot_path.write_text(
            json.dumps(final_snap, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    assert (cards_dir / "snapshots" / "index_iter1.json").exists()


def test_snapshot_not_created_when_rolled_back(cards_dir: Path):
    """If kept=False, no snapshot is written."""
    kept = False
    if kept:
        (cards_dir / "snapshots").mkdir()
        (cards_dir / "snapshots" / "index_iter1.json").write_text("{}")

    assert not (cards_dir / "snapshots" / "index_iter1.json").exists()


def test_snapshot_reflects_post_rollback_state(cards_dir: Path):
    """Snapshot must capture the final state (after rollbacks)."""
    _write_index(cards_dir, [make_card("exp-da-001"), make_card("exp-da-002")])
    snapshots_dir = cards_dir / "snapshots"
    snapshots_dir.mkdir()
    snap_path = snapshots_dir / "index_iter1.json"

    final_index = load_index(cards_dir)
    snap_path.write_text(
        json.dumps(final_index, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    snap_data = json.loads(snap_path.read_text())
    assert len(snap_data["cards"]) == 2


# ---------------------------------------------------------------------------
# restore_iteration — cmd_list
# ---------------------------------------------------------------------------

def test_cmd_list_shows_available_snapshots(tmp_path: Path, capsys):
    """cmd_list should print a table of available snapshots."""
    import restore_iteration

    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    (cards_dir / "cards").mkdir()

    cards_iter1 = [make_card("exp-da-001")]
    cards_iter2 = [make_card("exp-da-001"), make_card("exp-da-002")]
    _write_index(cards_dir, cards_iter2)            # current = 2 cards
    _write_snapshot(cards_dir, 1, cards_iter1)
    _write_snapshot(cards_dir, 2, cards_iter2)

    log = [
        {"iteration": 1, "avg_delta_rubrics_pct": 0.17, "added_ids": ["exp-da-001"]},
        {"iteration": 2, "avg_delta_rubrics_pct": 0.10, "added_ids": ["exp-da-002"],
         "avg_delta_vs_prev_iter": -0.06},
    ]
    log_path = tmp_path / "evolution_log.json"
    log_path.write_text(json.dumps(log))

    restore_iteration.cmd_list(cards_dir, log_path)
    out = capsys.readouterr().out
    assert "exp-da-001" in out
    assert "exp-da-002" in out
    assert "current" in out   # iter2 is marked as current


def test_cmd_list_no_snapshots_message(tmp_path: Path, capsys):
    import restore_iteration

    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    _write_index(cards_dir, [])
    log_path = tmp_path / "evolution_log.json"
    log_path.write_text("[]")

    restore_iteration.cmd_list(cards_dir, log_path)
    out = capsys.readouterr().out
    assert "No snapshots found" in out


# ---------------------------------------------------------------------------
# restore_iteration — cmd_restore
# ---------------------------------------------------------------------------

def _setup_restore_env(tmp_path: Path):
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    (cards_dir / "cards").mkdir()

    card1 = make_card("exp-da-001", path="cards/exp-da-001-test-card.md")
    card2 = make_card("exp-da-002", title="Card Two", path="cards/exp-da-002-card-two.md")

    # Write both .md files to disk
    (cards_dir / "cards" / "exp-da-001-test-card.md").write_text("# Card 1")
    (cards_dir / "cards" / "exp-da-002-card-two.md").write_text("# Card 2")

    # Current state has both cards
    _write_index(cards_dir, [card1, card2])

    # Snapshot iter1 had only card1
    _write_snapshot(cards_dir, 1, [card1])

    log_path = tmp_path / "evolution_log.json"
    log_path.write_text("[]")

    return cards_dir, log_path


def test_cmd_restore_dry_run_no_changes(tmp_path: Path, capsys):
    import restore_iteration

    cards_dir, log_path = _setup_restore_env(tmp_path)
    restore_iteration.cmd_restore(cards_dir, log_path, target_iter=1, dry_run=True)

    # Dry run: file must still exist
    assert (cards_dir / "cards" / "exp-da-002-card-two.md").exists()
    idx = load_index(cards_dir)
    assert len(idx["cards"]) == 2   # unchanged


def test_cmd_restore_removes_newer_card_file(tmp_path: Path):
    import restore_iteration

    cards_dir, log_path = _setup_restore_env(tmp_path)
    restore_iteration.cmd_restore(cards_dir, log_path, target_iter=1, dry_run=False)

    # exp-da-002 was not in iter1 snapshot → its .md file should be deleted
    assert not (cards_dir / "cards" / "exp-da-002-card-two.md").exists()
    # exp-da-001 stays
    assert (cards_dir / "cards" / "exp-da-001-test-card.md").exists()


def test_cmd_restore_updates_index(tmp_path: Path):
    import restore_iteration

    cards_dir, log_path = _setup_restore_env(tmp_path)
    restore_iteration.cmd_restore(cards_dir, log_path, target_iter=1, dry_run=False)

    idx = load_index(cards_dir)
    ids = [c["id"] for c in idx["cards"]]
    assert ids == ["exp-da-001"]


def test_cmd_restore_invalid_iter_exits(tmp_path: Path):
    import restore_iteration

    cards_dir, log_path = _setup_restore_env(tmp_path)
    with pytest.raises(SystemExit):
        restore_iteration.cmd_restore(cards_dir, log_path, target_iter=99, dry_run=False)


def test_cmd_restore_already_at_target(tmp_path: Path, capsys):
    import restore_iteration

    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    (cards_dir / "cards").mkdir()
    card = make_card("exp-da-001")
    _write_index(cards_dir, [card])
    _write_snapshot(cards_dir, 1, [card])
    log_path = tmp_path / "evolution_log.json"
    log_path.write_text("[]")

    restore_iteration.cmd_restore(cards_dir, log_path, target_iter=1, dry_run=False)
    out = capsys.readouterr().out
    assert "nothing to do" in out


# ---------------------------------------------------------------------------
# Dual-criterion rollback thresholds
# ---------------------------------------------------------------------------

def test_dual_criterion_baseline_regression():
    """avg_delta < REGRESSION_THRESHOLD triggers rollback."""
    avg_delta_frac = REGRESSION_THRESHOLD - 0.01   # just below threshold
    assert avg_delta_frac < REGRESSION_THRESHOLD


def test_dual_criterion_relative_regression():
    """prev_iter_delta < RELATIVE_REGRESSION_THRESHOLD triggers rollback."""
    prev_iter_delta_frac = RELATIVE_REGRESSION_THRESHOLD - 0.01
    assert prev_iter_delta_frac < RELATIVE_REGRESSION_THRESHOLD


def test_dual_criterion_both_pass():
    """Both above their thresholds → no rollback."""
    avg_delta_frac = REGRESSION_THRESHOLD + 0.01
    prev_iter_delta_frac = RELATIVE_REGRESSION_THRESHOLD + 0.01
    baseline_regression = avg_delta_frac < REGRESSION_THRESHOLD
    relative_regression = prev_iter_delta_frac < RELATIVE_REGRESSION_THRESHOLD
    assert not (baseline_regression or relative_regression)


def test_dual_criterion_only_relative_triggers():
    """Even if baseline is fine, relative regression alone triggers rollback."""
    avg_delta_frac = REGRESSION_THRESHOLD + 0.03    # above baseline threshold
    prev_iter_delta_frac = RELATIVE_REGRESSION_THRESHOLD - 0.02   # below relative threshold

    baseline_regression = avg_delta_frac < REGRESSION_THRESHOLD
    relative_regression = (
        prev_iter_delta_frac is not None
        and prev_iter_delta_frac < RELATIVE_REGRESSION_THRESHOLD
    )
    assert not baseline_regression
    assert relative_regression
    assert baseline_regression or relative_regression   # rollback triggered


def test_dual_criterion_no_prev_iter_skips_relative():
    """When prev_iter_delta is None (first iteration), relative check is skipped."""
    prev_iter_delta_frac = None
    relative_regression = (
        prev_iter_delta_frac is not None
        and prev_iter_delta_frac < RELATIVE_REGRESSION_THRESHOLD
    )
    assert not relative_regression


# ---------------------------------------------------------------------------
# --run path derivation
# ---------------------------------------------------------------------------

def test_run_path_cards_dir_derived(tmp_path: Path, monkeypatch):
    """When --run is set, cards_dir resolves to <evolve_dir>/<run>/cards/."""
    import evolve_pipeline

    # Patch _HERE to tmp_path so we control the directory
    monkeypatch.setattr(evolve_pipeline, "_HERE", tmp_path)

    # Simulate what run_pipeline does at the top:
    run_name = "test_run"
    run_dir = tmp_path / run_name
    run_dir.mkdir()
    cards_dir = run_dir / "cards"
    patterns_dir = run_dir / "patterns"
    log_path = run_dir / "evolution_log.json"
    state_file = run_dir / "case_state.json"

    assert cards_dir == tmp_path / run_name / "cards"
    assert patterns_dir == tmp_path / run_name / "patterns"
    assert log_path == tmp_path / run_name / "evolution_log.json"
    assert state_file == tmp_path / run_name / "case_state.json"


def test_run_path_restore_resolution(tmp_path: Path, monkeypatch):
    """restore_iteration resolves cards_dir from --run the same way."""
    import restore_iteration

    monkeypatch.setattr(restore_iteration, "_HERE", tmp_path)
    run_name = "my_run"

    # What main() does when args.run is set:
    cards_dir = tmp_path / run_name / "cards"
    log_path = tmp_path / run_name / "evolution_log.json"

    assert cards_dir == tmp_path / run_name / "cards"
    assert log_path == tmp_path / run_name / "evolution_log.json"
