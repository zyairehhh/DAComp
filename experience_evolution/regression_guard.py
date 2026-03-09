"""Pre-write regression guard for experience card evolution.

Detects when candidate cards have over-broad keywords that would cause them to
be retrieved for high-baseline cases outside their source domain, and attempts
to tighten those keywords before the cards are written to index.json.

Also provides surgical per-case rollback: instead of rolling back ALL new cards,
only removes cards that caused regressions on specific high-performing cases.

Public API:
  run_pre_write_guard(candidate_cards, current_index, tasks, baseline_scores, ...) -> GuardResult
  find_culprit_cards(per_case_deltas, new_cards, tasks, baseline_scores, ...) -> set[str]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from retrieval import _tokenize, simulate_retrieval_map


# Weighted_total_score threshold: cases above this score are "high-baseline" (worth protecting)
HIGH_BASELINE_THRESHOLD = 60.0

# Per-case weighted delta trigger: if a high-baseline case falls by more than this → culprit search
CASE_REGRESSION_THRESHOLD = -15.0

# Coverage cap: new cards that would match more than this fraction of the task corpus are too broad
MAX_COVERAGE_FRACTION = 0.15


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GuardResult:
    refined_cards: List[Dict]               # Candidate cards after keyword tightening (may be same)
    at_risk_cases: Dict[str, List[str]]     # {case_id: [card_ids that would be newly injected]}
    tightened_card_ids: List[str]           # Cards whose keywords were narrowed
    blocked_card_ids: List[str]             # Cards blocked entirely (risk too high, tightening failed)


# ---------------------------------------------------------------------------
# Retrieval diff
# ---------------------------------------------------------------------------

def _diff_retrieval_maps(
    before: Dict[str, List[str]],
    after: Dict[str, List[str]],
) -> Dict[str, Dict[str, List[str]]]:
    """Return {case_id: {added: [...], removed: [...]}} for cases where retrieval changed."""
    all_cases = set(before) | set(after)
    diff: Dict[str, Dict[str, List[str]]] = {}
    for case_id in all_cases:
        b = set(before.get(case_id, []))
        a = set(after.get(case_id, []))
        added = sorted(a - b)
        removed = sorted(b - a)
        if added or removed:
            diff[case_id] = {"added": added, "removed": removed}
    return diff


# ---------------------------------------------------------------------------
# At-risk detection
# ---------------------------------------------------------------------------

def flag_at_risk_cases(
    diff: Dict[str, Dict[str, List[str]]],
    baseline_scores: Dict[str, float],
    high_threshold: float = HIGH_BASELINE_THRESHOLD,
) -> List[Dict]:
    """Find cases where new cards would be injected AND baseline score was high.

    Returns list of {case_id, baseline_score, added_card_ids}.
    """
    at_risk = []
    for case_id, changes in diff.items():
        added = changes.get("added", [])
        if not added:
            continue
        score = baseline_scores.get(case_id, 0.0)
        if score >= high_threshold:
            at_risk.append({
                "case_id": case_id,
                "baseline_score": score,
                "added_card_ids": added,
            })
    return sorted(at_risk, key=lambda x: -x["baseline_score"])


# ---------------------------------------------------------------------------
# Keyword tightening
# ---------------------------------------------------------------------------

def _keyword_hits_any(keyword: str, instructions: List[str]) -> bool:
    """True if keyword appears in any of the given instructions."""
    from retrieval import _tokenize, _contains_token_phrase
    for instr in instructions:
        tokens = _tokenize(instr)
        token_string = f" {' '.join(tokens)} "
        if _contains_token_phrase(token_string, keyword):
            return True
    return False


def _coverage_fraction(card: Dict, all_instructions: Dict[str, str]) -> float:
    """Return the fraction of tasks in the corpus that would retrieve this card."""
    rmap = simulate_retrieval_map([card], all_instructions)
    hit_count = sum(1 for hits in rmap.values() if card.get("id") in hits)
    return hit_count / len(all_instructions) if all_instructions else 0.0


def tighten_keywords(
    card: Dict,
    at_risk_instructions: List[str],
    source_instructions: List[str],
) -> Dict:
    """Remove keywords that hit at-risk cases but NOT source cases (non-discriminating).

    Returns a new card dict (immutable). Falls back to original if no keywords can be removed
    without losing all keywords.
    """
    original_keywords = list(card.get("keywords", []))
    if not original_keywords or not at_risk_instructions:
        return card

    to_remove = []
    for kw in original_keywords:
        hits_at_risk = _keyword_hits_any(kw, at_risk_instructions)
        hits_source = _keyword_hits_any(kw, source_instructions)
        if hits_at_risk and not hits_source:
            to_remove.append(kw)

    if not to_remove:
        return card

    refined = [kw for kw in original_keywords if kw not in to_remove]
    if len(refined) < 3:
        # Don't remove so many keywords that the card becomes unretrievable
        return card

    return {**card, "keywords": refined}


# ---------------------------------------------------------------------------
# Main guard
# ---------------------------------------------------------------------------

def run_pre_write_guard(
    candidate_cards: List[Dict],
    current_index: List[Dict],
    tasks: Dict[str, str],
    baseline_scores: Dict[str, float],
    high_threshold: float = HIGH_BASELINE_THRESHOLD,
    auto_tighten: bool = True,
    all_instructions: Optional[Dict[str, str]] = None,
    max_coverage_fraction: float = MAX_COVERAGE_FRACTION,
) -> GuardResult:
    """Run pre-write regression guard on candidate cards.

    Steps:
      1. Simulate retrieval before adding candidate cards.
      2. Simulate retrieval after adding candidate cards.
      3. Diff to find cases that would get new cards injected.
      4. Flag at-risk cases (high baseline, new injection).
      5. For each at-risk card, try keyword tightening.
      6. (Optional) If all_instructions provided: check corpus coverage cap.
         Cards matching > max_coverage_fraction of all tasks are flagged as
         over-broad.  Tightening is attempted; if still over-broad the card
         is blocked.

    Args:
        candidate_cards:       Proposed new cards (not yet in index).
        current_index:         Existing cards list from index.json.
        tasks:                 {instance_id: instruction} for all 100 cases.
        baseline_scores:       {instance_id: weighted_total_score} from baseline CSV.
        high_threshold:        Cases with score above this are "protected".
        auto_tighten:          If True, automatically tighten keywords on flagged cards.
        all_instructions:      Full {instance_id: instruction} corpus for coverage check.
                               If None, coverage check is skipped.
        max_coverage_fraction: Fraction of corpus a card may match before tightening.

    Returns:
        GuardResult with refined_cards ready for writing.
    """
    # Simulate retrieval before and after
    before_map = simulate_retrieval_map(current_index, tasks)
    combined_cards = current_index + candidate_cards
    after_map = simulate_retrieval_map(combined_cards, tasks)

    diff = _diff_retrieval_maps(before_map, after_map)
    at_risk_list = flag_at_risk_cases(diff, baseline_scores, high_threshold)

    # Build per-card mapping: which at-risk cases does each candidate card affect?
    candidate_ids = {c["id"] for c in candidate_cards if c.get("id")}
    card_to_at_risk: Dict[str, List[str]] = {cid: [] for cid in candidate_ids}
    at_risk_map: Dict[str, List[str]] = {}  # case_id → added card_ids

    for entry in at_risk_list:
        case_id = entry["case_id"]
        for card_id in entry["added_card_ids"]:
            if card_id in candidate_ids:
                card_to_at_risk[card_id].append(case_id)
        at_risk_map[case_id] = entry["added_card_ids"]

    if at_risk_list:
        print(
            f"\n[Guard] {len(at_risk_list)} at-risk cases detected "
            f"(baseline weighted > {high_threshold}):",
            file=sys.stderr,
        )
        for entry in at_risk_list:
            print(
                f"  {entry['case_id']} (baseline={entry['baseline_score']:.1f}) "
                f"← {entry['added_card_ids']}",
                file=sys.stderr,
            )

    refined_cards: List[Dict] = []
    tightened_ids: List[str] = []
    blocked_ids: List[str] = []

    for card in candidate_cards:
        card_id = card.get("id", "")
        at_risk_cases = card_to_at_risk.get(card_id, [])

        # --- Coverage cap check (Optimization 3) ---
        if all_instructions:
            cov = _coverage_fraction(card, all_instructions)
            if cov > max_coverage_fraction:
                print(
                    f"  [Guard] OVER-BROAD: {card_id} matches {cov:.0%} of corpus "
                    f"(limit {max_coverage_fraction:.0%}); attempting tighten…",
                    file=sys.stderr,
                )
                # Reuse tighten_keywords: at-risk = every non-source task, source = source tasks
                source_case_ids = card.get("source_cases", [])
                source_instructions = [all_instructions[c] for c in source_case_ids if c in all_instructions]
                non_source = [instr for iid, instr in all_instructions.items() if iid not in set(source_case_ids)]
                tightened = tighten_keywords(card, non_source, source_instructions)
                if tightened is card:
                    print(f"  [Guard] BLOCKED: {card_id} still over-broad after tighten; skipping.", file=sys.stderr)
                    blocked_ids.append(card_id)
                    continue
                post_cov = _coverage_fraction(tightened, all_instructions)
                if post_cov > max_coverage_fraction:
                    print(
                        f"  [Guard] BLOCKED: {card_id} still matches {post_cov:.0%} after tighten; skipping.",
                        file=sys.stderr,
                    )
                    blocked_ids.append(card_id)
                    continue
                removed_kw = set(card.get("keywords", [])) - set(tightened.get("keywords", []))
                print(
                    f"  [Guard] Coverage-tightened {card_id}: {cov:.0%} → {post_cov:.0%}, "
                    f"removed {sorted(removed_kw)}",
                    file=sys.stderr,
                )
                card = tightened
                tightened_ids.append(card_id)

        # --- At-risk (high-baseline regression) check ---
        if not at_risk_cases:
            refined_cards.append(card)
            continue

        if not auto_tighten:
            # Just warn and keep as-is
            print(f"  [Guard] WARN: card {card_id} would inject into {at_risk_cases}", file=sys.stderr)
            refined_cards.append(card)
            continue

        # Collect source and at-risk instructions for tightening
        source_case_ids = card.get("source_cases", [])
        source_instructions = [tasks[c] for c in source_case_ids if c in tasks]
        at_risk_instructions = [tasks[c] for c in at_risk_cases if c in tasks]

        tightened = tighten_keywords(card, at_risk_instructions, source_instructions)

        if tightened is card:
            # Tightening made no change — card stays but we warn
            print(
                f"  [Guard] WARN: could not tighten {card_id} "
                f"(no non-discriminating keywords found); keeping as-is",
                file=sys.stderr,
            )
            refined_cards.append(card)
        else:
            removed = set(card.get("keywords", [])) - set(tightened.get("keywords", []))
            print(
                f"  [Guard] Tightened {card_id}: removed keywords {sorted(removed)} "
                f"(was hitting {at_risk_cases})",
                file=sys.stderr,
            )
            refined_cards.append(tightened)
            tightened_ids.append(card_id)

    return GuardResult(
        refined_cards=refined_cards,
        at_risk_cases=at_risk_map,
        tightened_card_ids=tightened_ids,
        blocked_card_ids=blocked_ids,
    )


# ---------------------------------------------------------------------------
# Surgical per-case rollback helper
# ---------------------------------------------------------------------------

def find_culprit_cards(
    per_case_deltas: Dict[str, float],
    new_cards: List[Dict],
    tasks: Dict[str, str],
    baseline_scores: Dict[str, float],
    high_threshold: float = HIGH_BASELINE_THRESHOLD,
    case_regression_threshold: float = CASE_REGRESSION_THRESHOLD,
) -> Set[str]:
    """Find which new cards caused regressions on high-baseline cases.

    For each case that (a) had a high baseline score and (b) regressed severely,
    simulate which new cards were retrieved for it and collect them as culprits.

    Returns: set of card IDs to surgically roll back.
    """
    culprit_ids: Set[str] = set()

    for case_id, delta in per_case_deltas.items():
        if delta >= case_regression_threshold:
            continue
        if baseline_scores.get(case_id, 0.0) < high_threshold:
            continue
        if case_id not in tasks:
            continue

        # Simulate which new cards were retrieved for this case
        retrieved = simulate_retrieval_map(new_cards, {case_id: tasks[case_id]})
        culprits = retrieved.get(case_id, [])
        if culprits:
            print(
                f"  [Guard] Culprit cards for {case_id} (delta={delta:+.1f}): {culprits}",
                file=sys.stderr,
            )
            culprit_ids.update(culprits)

    return culprit_ids


# ---------------------------------------------------------------------------
# CLI (dry-run mode for replaying past regressions)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import csv
    import json as _json
    from pathlib import Path as _Path

    parser = argparse.ArgumentParser(description="Regression guard dry-run")
    parser.add_argument("--candidate-cards", nargs="+", required=True,
                        help="Card IDs to test (e.g. exp-da-033 exp-da-034)")
    parser.add_argument("--baseline-csv", default=None, help="Baseline scores CSV")
    parser.add_argument(
        "--cards-dir",
        default=str(_Path(__file__).parent.parent / "dacomp-da" / "experience_cards"),
    )
    parser.add_argument(
        "--task-file",
        default=str(_Path(__file__).parent.parent / "dacomp-da" / "tasks" / "dacomp-da.jsonl"),
    )
    cli = parser.parse_args()

    cards_dir = _Path(cli.cards_dir)
    index_data = _json.loads((cards_dir / "index.json").read_text())
    all_cards = index_data.get("cards", [])

    candidate_ids = set(cli.candidate_cards)
    current = [c for c in all_cards if c["id"] not in candidate_ids]
    candidates = [c for c in all_cards if c["id"] in candidate_ids]

    # Load tasks
    tasks: Dict[str, str] = {}
    with open(cli.task_file, encoding="utf-8") as f:
        for line in f:
            rec = _json.loads(line.strip())
            tasks[rec["instance_id"]] = rec.get("instruction", "")

    # Load baseline scores
    baseline_scores: Dict[str, float] = {}
    if cli.baseline_csv:
        with open(cli.baseline_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                iid = row.get("instance_id", "").strip()
                try:
                    baseline_scores[iid] = float(row.get("weighted_total_score", 0) or 0)
                except ValueError:
                    pass

    result = run_pre_write_guard(candidates, current, tasks, baseline_scores)
    print(f"\nTightened: {result.tightened_card_ids}")
    print(f"Blocked:   {result.blocked_card_ids}")
    print(f"At-risk cases: {list(result.at_risk_cases.keys())}")
