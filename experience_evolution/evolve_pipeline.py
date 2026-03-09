"""Main orchestrator for the experience card self-evolution pipeline.

Implements two modes:
  - interactive: proposes cards and waits for user approval before writing
  - auto:        fully automated, writes cards and runs the test pipeline

Iteration flow:
  1. Select N worst-performing cases from baseline (skip 'hard'/stagnant cases)
  2. [classify] Classify failure type; skip non-knowledge_gap cases
  3. Extract failure patterns for each case (LLM)
  4. Synthesize patterns into candidate cards (LLM, with dedup gate)
  4.5 [guard] Pre-write retrieval regression guard + keyword tightening
  5. [interactive] Display proposals and get user approval
  6. Write approved cards to cards_dir / update index.json
  6.5 [validate] Check each new card's retrieval coverage
  7. Run DA-agent on test sample with new cards
  8. Run llm_judge to score results
  9. Compare vs baseline scores → update confidence + case state
  10. Surgical per-case rollback; then avg-delta rollback if needed

Usage:
    # Interactive with 10 worst cases, test on 5
    python evolve_pipeline.py \\
        --mode interactive --n-cases 10 --test-n 5 --iteration 1

    # Fully automated overnight
    python evolve_pipeline.py \\
        --mode auto --n-cases 20 --test-n 10 --max-iterations 3

    # Dry-run: extract + propose only (no agent run, no writes)
    python evolve_pipeline.py --mode dry-run --n-cases 5

    # With contrast learning (attach successful reference cases to prompt)
    python evolve_pipeline.py --mode interactive --n-cases 10 --use-contrast
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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

from pipeline_state import (
    iter_dir as _iter_dir,
    is_iter_complete,
    load_iter_complete,
    load_synthesis_cache,
    save_synthesis_cache,
    load_guard_cache,
    save_guard_cache,
    load_cards_written,
    save_cards_written,
    mark_iter_complete,
)
from card_utils import (
    IMPROVEMENT_THRESHOLD,
    REGRESSION_THRESHOLD,
    RELATIVE_REGRESSION_THRESHOLD,
    load_index,
    prune_disabled_cards,
    prune_zero_hit_cards,
    rollback_cards,
    rollback_specific_cards,
    save_index,
    summarize_existing_cards,
    update_confidence,
)
from select_cases import load_case_file, select_worst_cases
from extract_patterns import (
    extract_patterns_for_case,
    find_similar_successful_cases,
    load_rubrics_scores,
    load_task_instructions,
)
from synthesize_cards import load_all_patterns, synthesize_cards_with_llm, write_new_cards
from retrieval import get_embeddings, simulate_retrieval_map, validate_new_cards
from regression_guard import (
    HIGH_BASELINE_THRESHOLD,
    CASE_REGRESSION_THRESHOLD,
    find_culprit_cards,
    run_pre_write_guard,
)
from classify_failures import classify_failure_type, load_failure_type, save_failure_type
from case_state import (
    get_hard_case_ids,
    load_case_state,
    mark_stagnant_cases,
    save_case_state,
    update_case_state,
)


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
    cards_dir: Optional[Path] = None,
    python: str = DEFAULT_PYTHON,
    model: str = "deepseek-v3.2",
    max_steps: int = 80,
    max_workers: int = 4,
    timeout_seconds: Optional[int] = None,
    compress_context: bool = False,
) -> Tuple[Path, List[str]]:
    """Invoke run_parallel.py on the given cases.

    Returns:
        (agent_results_dir, completed_case_ids)

    On timeout the process group is killed and only cases with output on disk
    are included in completed_case_ids.  On a hard (non-timeout) failure a
    CalledProcessError is raised as before.
    """
    indices = ",".join(str(_instance_id_to_0based_index(iid)) for iid in case_ids)
    experiment_id = f"{model}-{suffix}"

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
    if cards_dir is not None:
        cmd += ["--experience_dir", str(cards_dir.resolve())]
    if compress_context:
        cmd += ["--compress_context"]
    print(f"\n[agent] Running: {' '.join(cmd)}", file=sys.stderr)

    timed_out = False
    # start_new_session creates a new process group so os.killpg covers all workers
    proc = subprocess.Popen(cmd, cwd=str(_AGENT_DIR), start_new_session=True)
    try:
        proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        print(
            f"\n[agent] TIMEOUT after {timeout_seconds}s. Killing process group…",
            file=sys.stderr,
        )
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            proc.kill()
        proc.wait()
        timed_out = True

    if not timed_out and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)

    # Export results (idempotent — exports whatever output exists on disk)
    get_results_cmd = [
        python,
        str(_AGENT_DIR / "get_results.py"),
        experiment_id,
        "--output_dir", str(_EVAL_DIR / "agent_results"),
    ]
    print(f"[agent] Exporting: {' '.join(get_results_cmd)}", file=sys.stderr)
    subprocess.run(get_results_cmd, cwd=str(_AGENT_DIR), check=True, timeout=120)

    # Determine which cases actually produced output
    agent_dir = _EVAL_DIR / "agent_results" / experiment_id
    completed = [
        iid for iid in case_ids
        if (agent_dir / iid).exists() and any((agent_dir / iid).iterdir())
    ]
    if timed_out:
        missing = [iid for iid in case_ids if iid not in set(completed)]
        if missing:
            print(f"[agent] Timed-out cases (excluded from scoring): {missing}", file=sys.stderr)

    return agent_dir, completed


def run_llm_judge(
    agent_results_dir: Path,
    python: str = DEFAULT_PYTHON,
    max_workers: int = 4,
) -> Path:
    """Run llm_judge.py then get_score.py, return the enriched CSV path."""
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

    # get_score.py computes weighted_total_score / rubrics_percentage and writes
    # them back into the CSV in-place.  Without this step those columns are absent
    # and compare_scores() will read 0 for every case.
    get_score_cmd = [python, str(_EVAL_DIR / "get_score.py")]
    print(f"[judge] Post-processing scores: {' '.join(get_score_cmd)}", file=sys.stderr)
    subprocess.run(get_score_cmd, cwd=str(_EVAL_DIR), check=True)

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


def load_all_baseline_scores(csv_path: Path) -> Dict[str, float]:
    """Return {instance_id: weighted_total_score} for ALL cases in the CSV."""
    scores: Dict[str, float] = {}
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            iid = (row.get("instance_id") or "").strip()
            if iid:
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


def _write_averaged_csv(run_csvs: List[Path], case_ids: List[str], out_path: Path) -> Path:
    """Average weighted_total_score across multiple run CSVs; write to out_path.

    Cases missing from a run CSV are treated as score=0 for that run's count,
    but only counted if they appear in at least one run (avoids penalising
    cases that simply weren't scheduled in a given run).
    """
    import collections
    score_sums: Dict[str, float] = collections.defaultdict(float)
    score_counts: Dict[str, int] = collections.defaultdict(int)
    for csv_path in run_csvs:
        scores = load_scores_for_cases(csv_path, case_ids)
        for iid, score in scores.items():
            score_sums[iid] += score
            score_counts[iid] += 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["instance_id", _SCORE_COLUMN])
        writer.writeheader()
        for iid in case_ids:
            cnt = score_counts[iid]
            if cnt > 0:
                writer.writerow({
                    "instance_id": iid,
                    _SCORE_COLUMN: round(score_sums[iid] / cnt, 4),
                })
    return out_path


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
    note: str = "",
    prev_iter_avg_delta: Optional[float] = None,
) -> None:
    entry = {
        "iteration": iteration,
        "added_ids": added_ids,
        "avg_delta_rubrics_pct": round(avg_delta, 4),
        "per_case_deltas": {k: round(v, 4) for k, v in deltas.items()},
        "kept": kept,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if prev_iter_avg_delta is not None:
        entry["avg_delta_vs_prev_iter"] = round(prev_iter_avg_delta, 4)
    if note:
        entry["note"] = note
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

def run_pipeline(
    args: argparse.Namespace,
    override_traj_dir: Optional[Path] = None,
    override_extract_csv: Optional[Path] = None,
    best_kept_csv: Optional[Path] = None,
) -> Optional[Tuple[Path, Path]]:
    """Run one iteration of the evolution pipeline.

    Args:
        args:                 Parsed CLI arguments.
        override_traj_dir:    If set, use this trajectory dir instead of args.traj_dir
                              for pattern extraction (enables multi-iteration chaining).
        override_extract_csv: If set, use this CSV for rubric scores in pattern extraction
                              (iteration N+1 sees residual failures after iteration N's cards).
        best_kept_csv:        If set, use this CSV for relative (iter-over-iter) comparison
                              instead of override_extract_csv.  Should be the last *kept*
                              iteration's score CSV so rolled-back iterations don't pollute
                              the baseline for relative regression checks.

    Returns:
        (agent_results_dir, new_scores_csv) on success, None on early exit/rollback.
    """
    cards_dir = Path(args.cards_dir)
    baseline_csv = Path(args.baseline_csv)
    patterns_dir = Path(args.patterns_dir)
    patterns_dir.mkdir(parents=True, exist_ok=True)
    iteration_id = args.iteration

    # --run sets the root folder for all run-specific state
    if args.run:
        run_dir = _HERE / args.run
        run_dir.mkdir(parents=True, exist_ok=True)
        cards_dir = run_dir / "cards"
        # patterns live under iter{N}/patterns/ to avoid rename/archive issues
        idir = _iter_dir(run_dir, iteration_id)
        patterns_dir = idir / "patterns"
        log_path = run_dir / "evolution_log.json"
        state_file = run_dir / "case_state.json"
    else:
        idir = _iter_dir(_HERE, iteration_id)
        log_path = _HERE / "evolution_log.json"
        state_file = _HERE / "case_state.json"

    # Trajectory dir and extraction CSV (support override for multi-iteration chaining)
    traj_dir = override_traj_dir or Path(args.traj_dir)
    extract_csv = override_extract_csv or baseline_csv

    # ---- Load shared data ----
    instructions = load_task_instructions(Path(args.task_file))
    scores_by_id = load_rubrics_scores(extract_csv)          # for pattern extraction
    baseline_weighted = load_all_baseline_scores(baseline_csv)  # for guard + rollback
    index = load_index(cards_dir)
    existing_summary = summarize_existing_cards(index)

    # ---- Step 0.5: Prune disabled cards from previous iterations ----
    # Cards with priority=0 are no longer retrieved but still occupy the index.
    # Remove them at the start of each iteration to keep the index clean and
    # prevent accidental confidence recovery.
    index_before_prune = load_index(cards_dir)
    index_pruned, pruned_ids = prune_disabled_cards(index_before_prune, cards_dir)
    if pruned_ids:
        save_index(index_pruned, cards_dir)
        index = index_pruned
        existing_summary = summarize_existing_cards(index)
        print(
            f"[Step 0.5] Pruned {len(pruned_ids)} disabled cards "
            f"(confidence-decayed): {pruned_ids}"
        )
    else:
        print(f"[Step 0.5] No disabled cards to prune.")

    # Prune auto-generated cards with zero retrieval hits across the full task corpus.
    # These cards are never seen by any agent and are pure dead weight.
    index_before_zero = load_index(cards_dir)
    index_zero, zero_pruned_ids = prune_zero_hit_cards(index_before_zero, cards_dir, instructions)
    if zero_pruned_ids:
        save_index(index_zero, cards_dir)
        index = index_zero
        existing_summary = summarize_existing_cards(index)
        print(
            f"[Step 0.5] Pruned {len(zero_pruned_ids)} zero-hit cards "
            f"(never retrieved by any task): {zero_pruned_ids}"
        )
    else:
        print(f"[Step 0.5] No zero-hit cards to prune.")

    # ---- Load case state (stagnation tracking) ----
    case_state = load_case_state(state_file)
    hard_ids = get_hard_case_ids(case_state)
    if hard_ids:
        print(f"  [state] Excluding {len(hard_ids)} stagnant cases: {sorted(hard_ids)}")

    # ---- Step 1: Select cases ----
    print(f"\n[Step 1] Selecting {args.n_cases} worst-performing cases…")
    if args.case_file:
        case_ids = load_case_file(Path(args.case_file))[:args.n_cases]
    else:
        case_ids = select_worst_cases(extract_csv, n=args.n_cases + len(hard_ids))
        case_ids = [c for c in case_ids if c not in hard_ids][:args.n_cases]
    print(f"  Selected: {case_ids}")

    test_case_ids = case_ids[:args.test_n]

    # ---- Step 2: Classify failures + extract patterns ----
    print(f"\n[Step 2] Classifying failures and extracting patterns for {len(case_ids)} cases…")
    failure_types: Dict[str, str] = {}

    for iid in case_ids:
        out_path = patterns_dir / f"{iid}_patterns.json"

        # Load or compute failure type (cached)
        ft = load_failure_type(patterns_dir, iid)
        if ft is None:
            instruction = instructions.get(iid, "")
            rubrics_row = scores_by_id.get(iid, {})
            traj_path = traj_dir / iid / f"{iid}-traj.txt"
            traj_text = traj_path.read_text(encoding="utf-8", errors="replace") \
                if traj_path.exists() else ""
            ft = classify_failure_type(iid, instruction, traj_text, rubrics_row, model=args.model)
            save_failure_type(patterns_dir, iid, ft)
        failure_types[iid] = ft

        if ft != "knowledge_gap":
            print(f"  [{iid}] failure_type={ft} — skipping pattern extraction")
            continue

        if out_path.exists() and not args.force_extract:
            print(f"  [{iid}] patterns already exist, skipping extraction")
            continue

        instruction = instructions.get(iid, "")
        rubrics_row = scores_by_id.get(iid, {})
        traj_path = traj_dir / iid / f"{iid}-traj.txt"

        # Optional contrast learning
        similar_cases = None
        if args.use_contrast:
            similar_cases = find_similar_successful_cases(
                instruction, instructions, scores_by_id, top_k=3,
            )

        patterns = extract_patterns_for_case(
            instance_id=iid,
            instruction=instruction,
            traj_path=traj_path,
            rubrics_row=rubrics_row,
            existing_cards_summary=existing_summary,
            similar_success_cases=similar_cases,
        )
        out_path.write_text(json.dumps(patterns, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  [{iid}] extracted {len(patterns)} patterns")

    # ---- Step 3: Synthesize cards ----
    print(f"\n[Step 3] Synthesizing patterns into candidate cards…")
    all_patterns = load_all_patterns(patterns_dir)
    if not all_patterns:
        print("  No patterns available. Exiting.")
        return None
    print(f"  Loaded {len(all_patterns)} total candidate patterns")

    _cached_synth = load_synthesis_cache(idir)
    if _cached_synth is not None:
        synthesized = _cached_synth
        print(f"  [checkpoint] Loaded {len(synthesized)} cards from synthesis cache.")
    else:
        synthesized = synthesize_cards_with_llm(all_patterns, existing_summary, model=args.model)
        save_synthesis_cache(idir, iteration_id, case_ids, synthesized)
        print(f"  LLM proposed {len(synthesized)} consolidated cards")

    if not synthesized:
        print("  Nothing to add.")
        return None

    # ---- Step 4.5: Pre-write regression guard ----
    if args.mode != "dry-run":
        print(f"\n[Step 4.5] Running pre-write regression guard…")
        _cached_guard = load_guard_cache(idir)
        if _cached_guard is not None:
            # refined_cards already has temp IDs stripped; write_new_cards will assign real IDs
            synthesized = _cached_guard["refined_cards"]
            print(f"  [checkpoint] Guard result loaded from cache ({len(synthesized)} cards).")
        else:
            # Assign temporary IDs for guard simulation (will be reassigned on write)
            from card_utils import next_card_id
            _temp_index = load_index(cards_dir)
            for card in synthesized:
                if not card.get("id"):
                    card["id"] = next_card_id(_temp_index)
                    _temp_index = {**_temp_index, "cards": [*_temp_index.get("cards", []),
                                                             {"id": card["id"]}]}

            current_cards = load_index(cards_dir).get("cards", [])
            guard_result = run_pre_write_guard(
                candidate_cards=synthesized,
                current_index=current_cards,
                tasks=instructions,
                baseline_scores=baseline_weighted,
                all_instructions=instructions,  # enables corpus coverage cap check
            )
            synthesized = guard_result.refined_cards
            if guard_result.tightened_card_ids:
                print(f"  Keywords tightened on: {guard_result.tightened_card_ids}")
            if guard_result.blocked_card_ids:
                print(f"  Blocked (risk too high): {guard_result.blocked_card_ids}")
                synthesized = [c for c in synthesized
                               if c.get("id") not in guard_result.blocked_card_ids]
            # Strip temp IDs before caching so write_new_cards can assign real IDs on resume
            for card in synthesized:
                card.pop("id", None)
            save_guard_cache(idir, iteration_id, guard_result)

    # ---- Step 4 (interactive): Review proposals ----
    if args.mode == "interactive":
        print(f"\n[Step 4] Interactive review of {len(synthesized)} proposed cards…")
        synthesized = interactive_review(synthesized)
        if not synthesized:
            print("  All cards skipped. Exiting.")
            return None

    if args.mode == "dry-run":
        print(f"\n[DRY RUN] {len(synthesized)} cards proposed. No files written.")
        for i, card in enumerate(synthesized, 1):
            _display_card_proposal(card, i, len(synthesized))
        return None

    # ---- Step 5: Write cards ----
    print(f"\n[Step 5] Writing cards to {cards_dir}…")
    _cached_written = load_cards_written(idir)
    if _cached_written is not None:
        added_ids = _cached_written
        updated_index = load_index(cards_dir)
        print(f"  [checkpoint] Cards already written: {added_ids}")
    else:
        # Guard cache already stripped temp IDs; write_new_cards assigns real IDs
        added_ids, updated_index = write_new_cards(synthesized, cards_dir, dry_run=False)
        if not added_ids:
            print("  No valid cards written.")
            return None
        # Stamp added_in_iteration on each new card for version traceability
        idx_stamped = load_index(cards_dir)
        stamped_cards = [
            {**c, "added_in_iteration": iteration_id} if c["id"] in set(added_ids) else c
            for c in idx_stamped.get("cards", [])
        ]
        save_index({**idx_stamped, "cards": stamped_cards}, cards_dir)

        # Compute and store embeddings for hybrid retrieval at inference time.
        # Texts = when_to_use + title (matches what experience.py embeds at query time).
        _new_card_entries = [c for c in stamped_cards if c["id"] in set(added_ids)]
        _embed_texts = [
            f"{c.get('when_to_use', '')} {c.get('title', '')}".strip()
            for c in _new_card_entries
        ]
        _embed_vecs = get_embeddings(_embed_texts)
        _emb_map = {
            c["id"]: vec
            for c, vec in zip(_new_card_entries, _embed_vecs)
        }
        _all_cards_emb = [
            {**c, "embedding": _emb_map[c["id"]]} if (c["id"] in _emb_map and _emb_map[c["id"]]) else c
            for c in stamped_cards
        ]
        save_index({**idx_stamped, "cards": _all_cards_emb}, cards_dir)
        _embedded_count = sum(1 for v in _emb_map.values() if v)
        print(f"  Embedded {_embedded_count}/{len(_new_card_entries)} new cards for hybrid retrieval.")

        save_cards_written(idir, iteration_id, added_ids)
    print(f"  Added: {added_ids}")

    # ---- Step 5.5: Validate retrieval coverage ----
    print(f"\n[Step 5.5] Validating retrieval coverage for new cards…")
    hits = validate_new_cards(added_ids, test_case_ids, cards_dir, instructions)
    for card_id in sorted(hits):
        hit_cases = hits[card_id]
        status = "OK" if hit_cases else "WARN: 0 retrieval hits on test cases"
        print(f"  [{card_id}] {len(hit_cases)}/{len(test_case_ids)} test cases — {status}")

    if args.skip_agent_run:
        print("\n[--skip-agent-run] Skipping agent execution and evaluation.")
        print("Cards written. Run agent manually and compare scores.")
        return None

    # ---- Step 6+7: Run agent N times and judge each run ----
    run_tag = f"_{args.run}" if args.run else ""
    n_runs = getattr(args, "n_runs_per_case", 1)
    timeout_secs = (
        args.agent_timeout_minutes * len(test_case_ids) * 60
        if args.agent_timeout_minutes else None
    )

    all_run_results: List[Tuple[Path, List[str]]] = []  # (agent_results_dir, completed_ids)
    all_run_csvs: List[Path] = []

    for run_idx in range(n_runs):
        run_suffix = (
            f"evolve{run_tag}_iter{iteration_id}_r{run_idx}"
            if n_runs > 1
            else f"evolve{run_tag}_iter{iteration_id}"
        )
        print(
            f"\n[Step 6] Run {run_idx + 1}/{n_runs}: "
            f"suffix={run_suffix}, {len(test_case_ids)} cases…"
        )
        try:
            run_dir, run_completed = run_agent_on_cases(
                test_case_ids,
                suffix=run_suffix,
                cards_dir=cards_dir,
                python=args.python,
                max_workers=args.max_workers,
                timeout_seconds=timeout_secs,
                compress_context=getattr(args, "compress_context", False),
            )
        except subprocess.CalledProcessError as exc:
            print(f"  ERROR: agent run {run_idx} failed: {exc}", file=sys.stderr)
            print("  Rolling back cards…")
            rolled = rollback_cards(added_ids, updated_index, cards_dir)
            save_index(rolled, cards_dir)
            return None

        run_timed_out = [iid for iid in test_case_ids if iid not in set(run_completed)]
        if run_timed_out:
            print(f"  Run {run_idx}: {len(run_timed_out)} timed out: {run_timed_out}")
        if not run_completed:
            print(f"  ERROR: run {run_idx} — all cases timed out. Rolling back…")
            rolled = rollback_cards(added_ids, updated_index, cards_dir)
            save_index(rolled, cards_dir)
            return None

        all_run_results.append((run_dir, run_completed))

        # ---- Step 7: Judge this run ----
        print(f"\n[Step 7] Judging run {run_idx + 1}/{n_runs}…")
        try:
            run_csv = run_llm_judge(run_dir, python=args.python, max_workers=args.max_workers)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"  ERROR: judge failed on run {run_idx}: {exc}", file=sys.stderr)
            print("  Rolling back cards…")
            rolled = rollback_cards(added_ids, updated_index, cards_dir)
            save_index(rolled, cards_dir)
            return None
        all_run_csvs.append(run_csv)

    # Merge completed_case_ids across all runs (union, for completeness tracking)
    completed_case_ids: List[str] = sorted(
        set(iid for _, completed in all_run_results for iid in completed)
    )
    timed_out_ids = [iid for iid in test_case_ids if iid not in set(completed_case_ids)]
    if timed_out_ids:
        print(f"  [agent] {len(timed_out_ids)} cases timed out across all runs: {timed_out_ids}")

    # For checkpointing purposes, use the last run's directory
    agent_results_dir = all_run_results[-1][0]

    # Average scores across runs when N > 1
    if n_runs > 1 and len(all_run_csvs) > 1:
        avg_csv_path = idir / "averaged_scores.csv"
        new_scores_csv = _write_averaged_csv(all_run_csvs, completed_case_ids, avg_csv_path)
        print(f"  Averaged {len(all_run_csvs)} run CSVs → {avg_csv_path.name}")
    else:
        new_scores_csv = all_run_csvs[0]

    # ---- Step 8: Compare scores + update confidence ----
    print(f"\n[Step 8] Comparing scores…")
    # Use only completed cases — timed-out cases are excluded to avoid unfair rollback
    avg_delta, deltas = compare_scores(baseline_csv, new_scores_csv, completed_case_ids)
    avg_delta_frac = avg_delta / 100.0
    print(f"  Avg weighted delta vs baseline: {avg_delta:+.2f}pp ({avg_delta_frac:+.4f})")
    for iid, d in sorted(deltas.items()):
        print(f"  {iid}: {d:+.2f}pp")

    # Dual-criterion: also compare vs previous iteration's scores when available.
    # Use best_kept_csv if provided (last KEPT iteration), otherwise fall back to
    # override_extract_csv (last run, even if rolled back).  This prevents a rolled-
    # back iteration from artificially lowering the relative-regression bar.
    comparison_csv = best_kept_csv if best_kept_csv is not None else override_extract_csv
    prev_iter_avg_delta: Optional[float] = None
    prev_iter_avg_delta_frac: Optional[float] = None
    if comparison_csv is not None and comparison_csv != baseline_csv:
        prev_avg, _ = compare_scores(comparison_csv, new_scores_csv, completed_case_ids)
        prev_iter_avg_delta = prev_avg
        prev_iter_avg_delta_frac = prev_avg / 100.0
        label = "best-kept iter" if best_kept_csv is not None else "prev iter"
        print(
            f"  Avg weighted delta vs {label}: {prev_avg:+.2f}pp "
            f"({prev_iter_avg_delta_frac:+.4f}) "
            f"[threshold: {RELATIVE_REGRESSION_THRESHOLD*100:+.0f}pp]"
        )

    # Update confidence per card using per-card contribution analysis.
    # Instead of using the global avg_delta for all cards, we simulate which
    # cases each card was retrieved for and compute the avg delta for those
    # cases.  This catches cards that cause regressions even when the overall
    # avg barely passes the threshold.
    index_after = load_index(cards_dir)
    retrieval_map = simulate_retrieval_map(
        [c for c in index_after.get("cards", []) if c["id"] in set(added_ids)],
        {iid: instructions[iid] for iid in completed_case_ids if iid in instructions},
    )
    # Invert: card_id → [case_ids it was retrieved for]
    card_to_cases: Dict[str, List[str]] = {cid: [] for cid in added_ids}
    for case_id, retrieved_cards in retrieval_map.items():
        for cid in retrieved_cards:
            if cid in card_to_cases:
                card_to_cases[cid].append(case_id)

    for card_id in added_ids:
        hit_cases = card_to_cases.get(card_id, [])
        if hit_cases:
            card_delta_frac = (
                sum(deltas.get(c, 0.0) for c in hit_cases) / len(hit_cases) / 100.0
            )
        else:
            # Card not retrieved by any completed case → use global avg as fallback
            card_delta_frac = avg_delta_frac
        index_after = update_confidence(card_id, card_delta_frac, index_after)
        if hit_cases:
            print(
                f"  [confidence] {card_id}: hit {len(hit_cases)} cases, "
                f"per-card avg delta={card_delta_frac*100:+.2f}pp"
            )
    save_index(index_after, cards_dir)

    # Update case state (only completed cases; timed-out cases not penalised)
    updated_state = case_state
    new_scores_by_case = load_scores_for_cases(new_scores_csv, completed_case_ids)
    for iid in completed_case_ids:
        updated_state = update_case_state(
            updated_state, iid,
            new_scores_by_case.get(iid, 0.0),
            failure_type=failure_types.get(iid),
        )
    updated_state = mark_stagnant_cases(updated_state)
    save_case_state(updated_state, state_file)
    newly_hard = {
        cid for cid in updated_state
        if updated_state[cid].get("status") == "hard"
        and case_state.get(cid, {}).get("status") != "hard"
    }
    if newly_hard:
        print(f"  [state] Newly marked hard (stagnant): {sorted(newly_hard)}")

    # ---- Step 9: Surgical rollback + avg-delta rollback ----
    kept = True
    note = ""

    # 9a: Surgical per-case rollback for high-baseline regressions
    new_cards_only = [c for c in index_after.get("cards", []) if c["id"] in set(added_ids)]
    culprit_ids = find_culprit_cards(
        deltas, new_cards_only, instructions, baseline_weighted,
    )
    if culprit_ids:
        remaining_new = sorted(set(added_ids) - culprit_ids)
        print(
            f"\n[Step 9a] Surgical rollback: removing culprit cards {sorted(culprit_ids)} "
            f"(keeping {remaining_new})…"
        )
        index_after, actually_removed = rollback_specific_cards(
            sorted(culprit_ids), index_after, cards_dir
        )
        save_index(index_after, cards_dir)
        added_ids = [cid for cid in added_ids if cid not in culprit_ids]
        note = f"Surgical rollback of {sorted(actually_removed)}"
        print(f"  Removed: {actually_removed}")

    # 9b: Avg-delta rollback as final safety net (dual-criterion)
    # Criterion (a): must not regress below original baseline
    baseline_regression = avg_delta_frac < REGRESSION_THRESHOLD
    # Criterion (b): must not drop significantly vs previous iteration (catches slow drift)
    relative_regression = (
        prev_iter_avg_delta_frac is not None
        and prev_iter_avg_delta_frac < RELATIVE_REGRESSION_THRESHOLD
    )

    if baseline_regression or relative_regression:
        reasons: List[str] = []
        if baseline_regression:
            reasons.append(
                f"baseline regression ({avg_delta:+.2f}pp < {REGRESSION_THRESHOLD*100:+.0f}pp)"
            )
        if relative_regression:
            reasons.append(
                f"iter-over-iter regression "
                f"({prev_iter_avg_delta:+.2f}pp < {RELATIVE_REGRESSION_THRESHOLD*100:+.0f}pp)"
            )
        print(
            f"\n[Step 9b] Rollback triggered: {'; '.join(reasons)}. "
            f"Rolling back remaining {added_ids}…"
        )
        final_index = rollback_cards(added_ids, index_after, cards_dir)
        save_index(final_index, cards_dir)
        kept = False
        note = (note + " | avg-delta rollback: " + "; ".join(reasons)).lstrip(" | ")
        print("  Rollback complete.")
    else:
        print(
            f"\n[Step 9] Keeping cards (avg delta={avg_delta:+.2f}pp ≥ threshold). "
            f"Confidence updated."
        )

    _log_iteration(
        log_path, iteration_id, added_ids, avg_delta, deltas, kept, note,
        prev_iter_avg_delta=prev_iter_avg_delta,
    )
    print(f"\nIteration {iteration_id} complete. Log: {log_path}")

    # Save index snapshot for this iteration (only when cards were kept)
    if kept:
        snapshots_dir = cards_dir / "snapshots"
        snapshots_dir.mkdir(exist_ok=True)
        snapshot_path = snapshots_dir / f"index_iter{iteration_id}.json"
        final_snap = load_index(cards_dir)
        snapshot_path.write_text(
            json.dumps(final_snap, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  Snapshot saved: {snapshot_path.relative_to(_REPO_ROOT)}")

    # Write iteration-complete sentinel (enables cross-iteration resume)
    mark_iter_complete(
        idir, iteration_id,
        kept=kept,
        added_ids=added_ids if kept else [],
        avg_delta=avg_delta,
        agent_results_dir=agent_results_dir,
        new_scores_csv=new_scores_csv,
    )

    return (agent_results_dir, new_scores_csv)


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
    parser.add_argument(
        "--run",
        default=None,
        metavar="NAME",
        help=(
            "Run name. Creates experience_evolution/<NAME>/ containing cards/, "
            "patterns/, evolution_log.json, and case_state.json. "
            "Overrides --cards-dir and --patterns-dir when set."
        ),
    )
    parser.add_argument("--baseline-csv", default=DEFAULT_BASELINE_CSV)
    parser.add_argument("--task-file", default=DEFAULT_TASK_FILE)
    parser.add_argument("--traj-dir", default=DEFAULT_TRAJ_DIR)
    parser.add_argument("--cards-dir", default=DEFAULT_CARDS_DIR,
                        help="Ignored when --run is set")
    parser.add_argument("--patterns-dir", default=DEFAULT_PATTERNS_DIR,
                        help="Ignored when --run is set")
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
    parser.add_argument("--use-contrast", action="store_true",
                        help="Attach similar successful cases to extraction prompt for contrast")
    parser.add_argument(
        "--agent-timeout-minutes", type=int, default=8,
        help=(
            "Per-case timeout in minutes (0 = no limit). "
            "Total timeout = per_case_minutes × n_test_cases. "
            "Timed-out cases are excluded from scoring; pipeline continues with partial results. "
            "Default 8 min/case (e.g. 30 cases → 240 min total)."
        ),
    )
    parser.add_argument(
        "--n-runs-per-case", type=int, default=1,
        help=(
            "Number of independent agent runs per test case. "
            "Scores are averaged across runs to reduce evaluation noise. "
            "Default 1 (single run, original behaviour). "
            "Recommended: 3 for reliable signal (same total compute as 3× cases)."
        ),
    )
    parser.add_argument(
        "--compress-context", action="store_true",
        help=(
            "Enable context compression in agent runs: old observations are "
            "summarized and CreateFile/EditFile code blocks are stripped from "
            "history to reduce cumulative input tokens."
        ),
    )

    args = parser.parse_args()

    if args.mode == "auto" and args.max_iterations > 1:
        base_dir = _HERE / args.run if args.run else _HERE
        prev_result: Optional[Tuple[Path, Path]] = None
        best_kept_result: Optional[Tuple[Path, Path]] = None  # last KEPT iteration's result
        start = args.iteration
        end = start + args.max_iterations
        for i in range(start, end):
            # Skip iterations that completed in a previous run
            if is_iter_complete(base_dir, i):
                rec = load_iter_complete(_iter_dir(base_dir, i))
                if rec and rec.get("agent_results_dir") and rec.get("new_scores_csv"):
                    prev_result = (Path(rec["agent_results_dir"]), Path(rec["new_scores_csv"]))
                    if rec.get("kept"):
                        best_kept_result = prev_result
                print(f"\n[auto] Iteration {i} already complete — skipping.")
                continue

            args.iteration = i
            print(f"\n{'#'*60}")
            print(f"# AUTO ITERATION {i}  ({i - start + 1}/{args.max_iterations})")
            print(f"{'#'*60}")

            traj_override = prev_result[0] if prev_result else None
            csv_override = prev_result[1] if prev_result else None
            best_kept_csv = best_kept_result[1] if best_kept_result else None

            result = run_pipeline(args, traj_override, csv_override, best_kept_csv=best_kept_csv)
            if result:
                prev_result = result
                # Update best_kept only if this iteration was kept (read from log)
                log_path = base_dir / "evolution_log.json"
                if log_path.exists():
                    import json as _json
                    log_entries = _json.loads(log_path.read_text())
                    last = log_entries[-1] if log_entries else {}
                    if last.get("kept") and last.get("iteration") == i:
                        best_kept_result = result
        # Patterns now live under iter{N}/patterns/ — no rename needed
    else:
        run_pipeline(args)


if __name__ == "__main__":
    main()
