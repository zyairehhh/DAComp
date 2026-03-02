"""Main orchestrator for the experience card self-evolution pipeline.

Implements two modes:
  - interactive: proposes cards and waits for user approval before writing
  - auto:        fully automated, writes cards and runs the test pipeline

Iteration flow:
  1. Select N worst-performing cases from baseline
  2. Extract failure patterns for each case (LLM)
  3. Synthesize patterns into candidate cards (LLM)
  4. [interactive] Display proposals and get user approval
  5. Write approved cards to cards_dir / update index.json
  6. Run DA-agent on test sample with new cards
  7. Run llm_judge to score results
  8. Compare vs baseline scores → update confidence
  9. Rollback if regression; else keep and log

Usage:
    # Interactive with 10 worst cases, test on 5
    python evolve_pipeline.py \\
        --mode interactive --n-cases 10 --test-n 5 --iteration 1

    # Fully automated overnight
    python evolve_pipeline.py \\
        --mode auto --n-cases 20 --test-n 10 --max-iterations 3

    # Dry-run: extract + propose only (no agent run, no writes)
    python evolve_pipeline.py --mode dry-run --n-cases 5
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path defaults (relative to this script's location)
# DAComp/
# ├── experience_evolution/   ← _HERE
# ├── dacomp-da/
# │   ├── evaluation_suite/   ← _EVAL_DIR
# │   ├── experience_cards/
# │   └── tasks/
# └── methods/da-agent/       ← _AGENT_DIR
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent.resolve()
_REPO_ROOT = _HERE.parent                              # DAComp/
_DACOMP_DA = _REPO_ROOT / "dacomp-da"
_EVAL_DIR = _DACOMP_DA / "evaluation_suite"
_AGENT_DIR = _REPO_ROOT / "methods" / "da-agent"

DEFAULT_BASELINE_CSV = str(
    _EVAL_DIR / "model_scores" /
    "deepseek-v3.2-baseline__rubrics-deepseek-v3-2__textgsb-deepseek-v3-2__visgsb-deepseek-v3-2.csv"
)
DEFAULT_TASK_FILE = str(_DACOMP_DA / "tasks" / "dacomp-da.jsonl")
DEFAULT_TRAJ_DIR = str(_EVAL_DIR / "baseline_agent_results" / "deepseek-v3.2-baseline")
DEFAULT_CARDS_DIR = str(_DACOMP_DA / "experience_cards")
DEFAULT_PATTERNS_DIR = str(_HERE / "patterns")
DEFAULT_PYTHON = sys.executable


# ---------------------------------------------------------------------------
# Import local modules (make _HERE importable)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(_HERE))

from card_utils import (
    IMPROVEMENT_THRESHOLD,
    REGRESSION_THRESHOLD,
    load_index,
    rollback_cards,
    save_index,
    summarize_existing_cards,
    update_confidence,
)
from select_cases import load_case_file, select_worst_cases
from extract_patterns import extract_patterns_for_case, load_rubrics_scores, load_task_instructions
from synthesize_cards import load_all_patterns, synthesize_cards_with_llm, write_new_cards


# ---------------------------------------------------------------------------
# Agent invocation helpers
# ---------------------------------------------------------------------------

def _instance_id_to_0based_index(iid: str) -> int:
    """dacomp-001 → 0, dacomp-100 → 99."""
    try:
        return int(iid.split("-")[-1]) - 1
    except (ValueError, IndexError):
        raise ValueError(f"Cannot parse index from {iid!r}")


def run_agent_on_cases(
    case_ids: List[str],
    suffix: str,
    python: str = DEFAULT_PYTHON,
    model: str = "deepseek-v3.2",
    max_steps: int = 80,
    max_workers: int = 4,
) -> Path:
    """Invoke run_parallel.py on the given cases and return the agent output dir."""
    indices = ",".join(str(_instance_id_to_0based_index(iid)) for iid in case_ids)
    experiment_id = f"{model}-{suffix}"
    output_dir = _AGENT_DIR / "output"

    cmd = [
        python,
        str(_AGENT_DIR / "run_parallel.py"),
        "--model", model,
        "-s", suffix,
        "-t", DEFAULT_TASK_FILE,
        "--example_index", indices,
        "--use_experience",
        "--max_steps", str(max_steps),
        "-w", str(max_workers),
    ]
    print(f"\n[agent] Running: {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, cwd=str(_AGENT_DIR), check=True)

    # Export results to evaluation_suite/agent_results/
    get_results_cmd = [
        python,
        str(_AGENT_DIR / "get_results.py"),
        experiment_id,
        "--output_dir", str(_EVAL_DIR / "agent_results"),
    ]
    print(f"[agent] Exporting: {' '.join(get_results_cmd)}", file=sys.stderr)
    subprocess.run(get_results_cmd, cwd=str(_AGENT_DIR), check=True)

    return _EVAL_DIR / "agent_results" / experiment_id


def run_llm_judge(
    agent_results_dir: Path,
    python: str = DEFAULT_PYTHON,
    max_workers: int = 4,
) -> Path:
    """Run llm_judge.py and return the output CSV path."""
    cmd = [
        python,
        str(_EVAL_DIR / "llm_judge.py"),
        "--rubrics-model", "deepseek-v3.2",
        "--gsb-model-text", "deepseek-v3.2",
        "--gsb-model-vis", "deepseek-v3.2",
        "--inputs", str(agent_results_dir),
        "--max-workers", str(max_workers),
    ]
    print(f"[judge] Running: {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, cwd=str(_EVAL_DIR), check=True)

    # The judge writes to model_scores/<dir_name>__...csv
    # Find it by glob
    dir_name = agent_results_dir.name
    candidates = list((_EVAL_DIR / "model_scores").glob(f"{dir_name}*.csv"))
    if candidates:
        return max(candidates, key=lambda p: p.stat().st_mtime)
    raise FileNotFoundError(f"Could not find judge output CSV for {dir_name}")


# ---------------------------------------------------------------------------
# Score comparison
# ---------------------------------------------------------------------------

_SCORE_COLUMN = "weighted_total_score"


def _parse_total_score(row: dict) -> float:
    raw = (row.get(_SCORE_COLUMN) or "").strip()
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def load_scores_for_cases(csv_path: Path, case_ids: List[str]) -> Dict[str, float]:
    """Return {instance_id: weighted_total_score} for the given cases."""
    case_set = set(case_ids)
    scores: Dict[str, float] = {}
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            iid = (row.get("instance_id") or "").strip()
            if iid in case_set:
                scores[iid] = _parse_total_score(row)
    return scores


def compare_scores(
    baseline_csv: Path,
    new_csv: Path,
    case_ids: List[str],
) -> Tuple[float, Dict[str, float]]:
    """Return (avg_delta, {instance_id: delta}) where delta = new - baseline."""
    baseline = load_scores_for_cases(baseline_csv, case_ids)
    new = load_scores_for_cases(new_csv, case_ids)
    deltas: Dict[str, float] = {}
    for iid in case_ids:
        b = baseline.get(iid, 0.0)
        n = new.get(iid, 0.0)
        deltas[iid] = n - b
    avg = sum(deltas.values()) / len(deltas) if deltas else 0.0
    return avg, deltas


# ---------------------------------------------------------------------------
# Interactive review
# ---------------------------------------------------------------------------

def _display_card_proposal(card: Dict, idx: int, total: int) -> None:
    print(f"\n{'='*60}")
    print(f"Proposed card {idx}/{total}: {card.get('title', '?')}")
    print(f"{'='*60}")
    print(f"when_to_use:  {card.get('when_to_use', '')}")
    print(f"keywords:     {card.get('keywords', [])}")
    print(f"tags:         {card.get('tags', [])}")
    print(f"source_cases: {card.get('source_cases', [])}")
    print(f"\nExperience:\n{card.get('experience', '')}")
    print(f"\nCommon failure prevented:\n{card.get('common_failure_prevented', '')}")


def interactive_review(synthesized: List[Dict]) -> List[Dict]:
    """Prompt user to approve/skip each proposed card. Returns approved list."""
    approved: List[Dict] = []
    for idx, card in enumerate(synthesized, start=1):
        _display_card_proposal(card, idx, len(synthesized))
        while True:
            choice = input("\n[a]pprove / [s]kip / [q]uit? ").strip().lower()
            if choice in ("a", "approve", ""):
                approved.append(card)
                print("→ Approved")
                break
            elif choice in ("s", "skip"):
                print("→ Skipped")
                break
            elif choice in ("q", "quit"):
                print("Quitting interactive review. Approved so far will be used.")
                return approved
            else:
                print("Please enter 'a', 's', or 'q'.")
    return approved


# ---------------------------------------------------------------------------
# Iteration state logging
# ---------------------------------------------------------------------------

def _log_iteration(
    log_path: Path,
    iteration: int,
    added_ids: List[str],
    avg_delta: float,
    deltas: Dict[str, float],
    kept: bool,
) -> None:
    entry = {
        "iteration": iteration,
        "added_ids": added_ids,
        "avg_delta_rubrics_pct": round(avg_delta, 4),
        "per_case_deltas": {k: round(v, 4) for k, v in deltas.items()},
        "kept": kept,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    history: List[Dict] = []
    if log_path.exists():
        try:
            history = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    history.append(entry)
    log_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(args: argparse.Namespace) -> None:
    cards_dir = Path(args.cards_dir)
    baseline_csv = Path(args.baseline_csv)
    patterns_dir = Path(args.patterns_dir)
    patterns_dir.mkdir(parents=True, exist_ok=True)
    log_path = _HERE / "evolution_log.json"

    # ---- Step 1: Select cases ----
    print(f"\n[Step 1] Selecting {args.n_cases} worst-performing cases…")
    if args.case_file:
        case_ids = load_case_file(Path(args.case_file))[:args.n_cases]
    else:
        case_ids = select_worst_cases(baseline_csv, n=args.n_cases)
    print(f"  Selected: {case_ids}")

    # Use first --test-n cases as the test sample (already worst-scoring)
    test_case_ids = case_ids[:args.test_n]

    # ---- Step 2: Extract patterns ----
    print(f"\n[Step 2] Extracting patterns for {len(case_ids)} cases…")
    instructions = load_task_instructions(Path(args.task_file))
    scores_by_id = load_rubrics_scores(baseline_csv)
    index = load_index(cards_dir)
    existing_summary = summarize_existing_cards(index)
    traj_dir = Path(args.traj_dir)

    for iid in case_ids:
        out_path = patterns_dir / f"{iid}_patterns.json"
        if out_path.exists() and not args.force_extract:
            print(f"  [{iid}] patterns already exist, skipping extraction")
            continue
        instruction = instructions.get(iid, "")
        rubrics_row = scores_by_id.get(iid, {})
        traj_path = traj_dir / iid / f"{iid}-traj.txt"
        patterns = extract_patterns_for_case(
            instance_id=iid,
            instruction=instruction,
            traj_path=traj_path,
            rubrics_row=rubrics_row,
            existing_cards_summary=existing_summary,
        )
        out_path.write_text(json.dumps(patterns, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  [{iid}] extracted {len(patterns)} patterns")

    # ---- Step 3: Synthesize cards ----
    print(f"\n[Step 3] Synthesizing patterns into candidate cards…")
    all_patterns = load_all_patterns(patterns_dir)
    if not all_patterns:
        print("  No patterns available. Exiting.")
        return
    print(f"  Loaded {len(all_patterns)} total candidate patterns")

    synthesized = synthesize_cards_with_llm(all_patterns, existing_summary, model=args.model)
    print(f"  LLM proposed {len(synthesized)} consolidated cards")

    if not synthesized:
        print("  Nothing to add.")
        return

    # ---- Step 4 (interactive): Review proposals ----
    if args.mode == "interactive":
        print(f"\n[Step 4] Interactive review of {len(synthesized)} proposed cards…")
        synthesized = interactive_review(synthesized)
        if not synthesized:
            print("  All cards skipped. Exiting.")
            return

    if args.mode == "dry-run":
        print(f"\n[DRY RUN] {len(synthesized)} cards proposed. No files written.")
        for i, card in enumerate(synthesized, 1):
            _display_card_proposal(card, i, len(synthesized))
        return

    # ---- Step 5: Write cards ----
    print(f"\n[Step 5] Writing {len(synthesized)} cards to {cards_dir}…")
    added_ids, updated_index = write_new_cards(synthesized, cards_dir, dry_run=False)
    if not added_ids:
        print("  No valid cards written.")
        return
    print(f"  Added: {added_ids}")

    if args.skip_agent_run:
        print("\n[--skip-agent-run] Skipping agent execution and evaluation.")
        print("Cards written. Run agent manually and compare scores.")
        return

    # ---- Step 6: Run agent on test sample ----
    iteration_id = args.iteration
    suffix = f"evolve_iter{iteration_id}"
    print(f"\n[Step 6] Running DA-agent on {len(test_case_ids)} test cases (suffix={suffix})…")
    try:
        agent_results_dir = run_agent_on_cases(
            test_case_ids,
            suffix=suffix,
            python=args.python,
            max_workers=args.max_workers,
        )
    except subprocess.CalledProcessError as exc:
        print(f"  ERROR: agent run failed: {exc}", file=sys.stderr)
        print("  Rolling back cards…")
        rolled = rollback_cards(added_ids, updated_index, cards_dir)
        save_index(rolled, cards_dir)
        return

    # ---- Step 7: Run LLM judge ----
    print(f"\n[Step 7] Running LLM judge…")
    try:
        new_scores_csv = run_llm_judge(agent_results_dir, python=args.python,
                                        max_workers=args.max_workers)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"  ERROR: judge failed: {exc}", file=sys.stderr)
        print("  Rolling back cards…")
        rolled = rollback_cards(added_ids, updated_index, cards_dir)
        save_index(rolled, cards_dir)
        return

    # ---- Step 8: Compare scores + update confidence ----
    print(f"\n[Step 8] Comparing scores…")
    avg_delta, deltas = compare_scores(baseline_csv, new_scores_csv, test_case_ids)
    avg_delta_frac = avg_delta / 100.0  # convert from percentage points to fraction
    print(f"  Avg rubrics delta: {avg_delta:+.2f}pp ({avg_delta_frac:+.4f})")
    for iid, d in sorted(deltas.items()):
        print(f"  {iid}: {d:+.2f}pp")

    # Update confidence for each new card
    index_after = load_index(cards_dir)
    for card_id in added_ids:
        index_after = update_confidence(card_id, avg_delta_frac, index_after)
    save_index(index_after, cards_dir)

    # ---- Step 9: Keep or rollback ----
    # Rollback only if clear regression; ambiguous/no-change keeps cards
    if avg_delta_frac < REGRESSION_THRESHOLD:
        print(
            f"\n[Step 9] Regression detected ({avg_delta:+.2f}pp). Rolling back {added_ids}…"
        )
        final_index = rollback_cards(added_ids, index_after, cards_dir)
        save_index(final_index, cards_dir)
        kept = False
        print("  Rollback complete.")
    else:
        kept = True
        print(
            f"\n[Step 9] Keeping cards (delta={avg_delta:+.2f}pp ≥ threshold). "
            f"Confidence updated."
        )

    _log_iteration(log_path, iteration_id, added_ids, avg_delta_frac, deltas, kept)
    print(f"\nIteration {iteration_id} complete. Log: {log_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Self-evolving experience card pipeline"
    )
    parser.add_argument(
        "--mode",
        choices=["interactive", "auto", "dry-run"],
        default="interactive",
        help="interactive: human reviews proposals; auto: fully automated; dry-run: no writes",
    )
    parser.add_argument("--n-cases", type=int, default=10, help="Cases to extract patterns from")
    parser.add_argument("--test-n", type=int, default=5, help="Cases to use for score testing")
    parser.add_argument("--iteration", type=int, default=1, help="Iteration number (for naming)")
    parser.add_argument("--max-iterations", type=int, default=1,
                        help="Max auto iterations (auto mode only)")

    # Paths
    parser.add_argument("--baseline-csv", default=DEFAULT_BASELINE_CSV)
    parser.add_argument("--task-file", default=DEFAULT_TASK_FILE)
    parser.add_argument("--traj-dir", default=DEFAULT_TRAJ_DIR)
    parser.add_argument("--cards-dir", default=DEFAULT_CARDS_DIR)
    parser.add_argument("--patterns-dir", default=DEFAULT_PATTERNS_DIR)
    parser.add_argument("--case-file", default=None,
                        help="Use pre-existing case list instead of selecting from CSV")

    # Agent / eval
    parser.add_argument("--python", default=DEFAULT_PYTHON,
                        help="Python executable to use for agent + judge subprocesses")
    parser.add_argument("--max-workers", type=int, default=4,
                        help="Max parallel workers for agent and judge")
    parser.add_argument("--model", default="deepseek-v3.2", help="LLM model for extraction")
    parser.add_argument("--skip-agent-run", action="store_true",
                        help="Skip agent execution (write cards only, no scoring)")
    parser.add_argument("--force-extract", action="store_true",
                        help="Re-extract patterns even if *_patterns.json already exists")

    args = parser.parse_args()

    if args.mode == "auto" and args.max_iterations > 1:
        for i in range(1, args.max_iterations + 1):
            args.iteration = i
            print(f"\n{'#'*60}")
            print(f"# AUTO ITERATION {i}/{args.max_iterations}")
            print(f"{'#'*60}")
            run_pipeline(args)
            # Move processed patterns to avoid re-processing
            patterns_dir = Path(args.patterns_dir)
            archive = patterns_dir.parent / f"patterns_iter{i}"
            if patterns_dir.exists():
                patterns_dir.rename(archive)
            patterns_dir.mkdir(parents=True, exist_ok=True)
    else:
        run_pipeline(args)


if __name__ == "__main__":
    main()
