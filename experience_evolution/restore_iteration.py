"""Restore experience cards to a previously snapshotted iteration state.

Snapshots are saved to <cards_dir>/snapshots/index_iter{N}.json at the end
of each successful pipeline iteration.

Usage:
    # List snapshots for a named run
    python restore_iteration.py --run exp_v1 --list

    # Preview what would change when restoring run exp_v1 to iteration 3
    python restore_iteration.py --run exp_v1 --to-iter 3 --dry-run

    # Restore
    python restore_iteration.py --run exp_v1 --to-iter 3

    # Without --run (legacy / explicit path)
    python restore_iteration.py --cards-dir /path/to/cards --list
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

_HERE = Path(__file__).parent.resolve()
DEFAULT_CARDS_DIR = str(_HERE / "cards")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_index(cards_dir: Path) -> Dict:
    path = cards_dir / "index.json"
    if not path.exists():
        return {"version": "2.0", "cards": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_index(index: Dict, cards_dir: Path) -> None:
    """Atomic write via .tmp file."""
    path = cards_dir / "index.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _load_evolution_log(log_path: Path) -> List[Dict]:
    if not log_path.exists():
        return []
    try:
        return json.loads(log_path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _list_snapshots(cards_dir: Path) -> List[Path]:
    snap_dir = cards_dir / "snapshots"
    if not snap_dir.exists():
        return []
    return sorted(snap_dir.glob("index_iter*.json"))


def _iter_num(snapshot_path: Path) -> int:
    """Extract iteration number from snapshot filename."""
    stem = snapshot_path.stem  # e.g. "index_iter3"
    return int(stem.replace("index_iter", ""))


def _log_entry_for_iter(log: List[Dict], n: int) -> Optional[Dict]:
    for entry in log:
        if entry.get("iteration") == n:
            return entry
    return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(cards_dir: Path, log_path: Path) -> None:
    current = _load_index(cards_dir)
    current_ids: Set[str] = {c["id"] for c in current.get("cards", [])}
    snapshots = _list_snapshots(cards_dir)
    log = _load_evolution_log(log_path)

    if not snapshots:
        print("No snapshots found. Run the pipeline at least once to create snapshots.")
        return

    print(f"\n{'Iter':<6} {'Cards':<7} {'ΔBaseline':>10} {'ΔPrevIter':>10}  Added IDs")
    print("-" * 70)
    for snap in snapshots:
        n = _iter_num(snap)
        snap_index = json.loads(snap.read_text(encoding="utf-8"))
        snap_ids = {c["id"] for c in snap_index.get("cards", [])}
        entry = _log_entry_for_iter(log, n)

        delta_base = "—"
        delta_prev = "—"
        added_ids_str = ""
        if entry:
            db = entry.get("avg_delta_rubrics_pct")
            dp = entry.get("avg_delta_vs_prev_iter")
            delta_base = f"{db*100:+.1f}pp" if db is not None else "—"
            delta_prev = f"{dp*100:+.1f}pp" if dp is not None else "—"
            added_ids_str = ", ".join(entry.get("added_ids", []))

        marker = " ← current" if snap_ids == current_ids else ""
        print(
            f"  {n:<4}  {len(snap_ids):<7} {delta_base:>10} {delta_prev:>10}  "
            f"{added_ids_str}{marker}"
        )

    print(f"\nCurrent index: {len(current_ids)} cards")
    print(f"Log: {log_path}")


def cmd_restore(cards_dir: Path, log_path: Path, target_iter: int, dry_run: bool) -> None:
    snapshots = _list_snapshots(cards_dir)
    available = {_iter_num(s): s for s in snapshots}

    if target_iter not in available:
        print(f"ERROR: No snapshot for iteration {target_iter}.")
        print(f"Available iterations: {sorted(available)}")
        sys.exit(1)

    snap_path = available[target_iter]
    target_index = json.loads(snap_path.read_text(encoding="utf-8"))
    target_ids: Set[str] = {c["id"] for c in target_index.get("cards", [])}

    current_index = _load_index(cards_dir)
    current_ids: Set[str] = {c["id"] for c in current_index.get("cards", [])}

    to_delete: Set[str] = current_ids - target_ids
    to_restore: Set[str] = target_ids - current_ids  # cards removed by a past rollback

    if not to_delete and not to_restore:
        print(f"Already at iteration {target_iter} state — nothing to do.")
        return

    print(f"\nRestoring to iteration {target_iter} snapshot: {snap_path.name}")
    print(f"  Cards to REMOVE ({len(to_delete)}): {sorted(to_delete) or '(none)'}")
    print(f"  Cards to RESTORE ({len(to_restore)}): {sorted(to_restore) or '(none)'}")

    if dry_run:
        print("\n[--dry-run] No files modified.")
        return

    # Delete .md files for cards being removed
    deleted_files: List[Path] = []
    for card in current_index.get("cards", []):
        if card["id"] in to_delete:
            rel_path = card.get("path", "")
            md_file = cards_dir / rel_path if rel_path else None
            if md_file and md_file.exists():
                md_file.unlink()
                deleted_files.append(md_file)

    # Replace index.json with snapshot
    _save_index(target_index, cards_dir)

    print(f"\n  Deleted {len(deleted_files)} .md files")
    print(f"  index.json replaced with iter {target_iter} snapshot")
    print(f"  Restored to {len(target_ids)} cards.")

    if to_restore:
        # Warn about any restored cards whose .md files were already deleted from disk
        missing = []
        for card in target_index.get("cards", []):
            if card["id"] in to_restore:
                rel_path = card.get("path", "")
                md_file = cards_dir / rel_path if rel_path else None
                if md_file and not md_file.exists():
                    missing.append(card["id"])
        if missing:
            print(
                f"\n  WARN: {len(missing)} restored card(s) have missing .md files "
                f"(index entry restored but content file was deleted): {missing}"
            )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore experience cards to a previous iteration snapshot"
    )

    # Run name (preferred) or explicit path
    parser.add_argument(
        "--run",
        default=None,
        metavar="NAME",
        help=(
            "Run name used with --run in evolve_pipeline.py. "
            "Resolves to experience_evolution/<NAME>/cards/ and evolution_log.json."
        ),
    )
    parser.add_argument(
        "--cards-dir",
        default=None,
        help="Explicit cards directory path (used when --run is not set)",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--list",
        action="store_true",
        help="List available snapshots with metrics",
    )
    group.add_argument(
        "--to-iter",
        type=int,
        metavar="N",
        help="Restore to iteration N's state",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying any files",
    )

    args = parser.parse_args()

    # Resolve cards_dir and log_path
    if args.run:
        run_dir = _HERE / args.run
        cards_dir = run_dir / "cards"
        log_path = run_dir / "evolution_log.json"
    elif args.cards_dir:
        cards_dir = Path(args.cards_dir)
        log_path = _HERE / "evolution_log.json"
    else:
        cards_dir = Path(DEFAULT_CARDS_DIR)
        log_path = _HERE / "evolution_log.json"

    if not cards_dir.exists():
        print(f"ERROR: cards_dir does not exist: {cards_dir}")
        sys.exit(1)

    if args.list:
        cmd_list(cards_dir, log_path)
    else:
        cmd_restore(cards_dir, log_path, args.to_iter, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
