"""Consolidate extracted candidate patterns into new experience cards.

Reads all *_patterns.json files from the patterns directory, calls an LLM
to deduplicate and consolidate them against existing cards, then writes the
new card markdown files and updates index.json.

Usage:
    python synthesize_cards.py \\
        --patterns-dir patterns/ \\
        --cards-dir ../../../../dacomp-da/experience_cards \\
        [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from card_utils import (
    CONFIDENCE_GENERATED,
    confidence_to_priority,
    add_card_to_index,
    load_index,
    next_card_id,
    render_card_markdown,
    save_index,
    summarize_existing_cards,
    write_card_file,
)


# ---------------------------------------------------------------------------
# LLM client (same standalone approach as extract_patterns.py)
# ---------------------------------------------------------------------------

_DEEPSEEK_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
_DEFAULT_MODEL = "deepseek-v3.2"


def _call_llm(prompt: str, model: str = _DEFAULT_MODEL, max_retries: int = 5) -> str:
    api_key = os.environ.get("BAILIAN_API_KEY", "")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8192,
        "temperature": 0.0,
    }
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(_DEEPSEEK_URL, headers=headers, json=payload, timeout=300)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            print(
                f"[LLM] HTTP {resp.status_code} on attempt {attempt}: {resp.text[:200]}",
                file=sys.stderr,
            )
        except requests.RequestException as exc:
            print(f"[LLM] Request error on attempt {attempt}: {exc}", file=sys.stderr)
        if attempt < max_retries:
            time.sleep(5 * attempt)
    raise RuntimeError(f"LLM call failed after {max_retries} attempts")


# ---------------------------------------------------------------------------
# Load patterns
# ---------------------------------------------------------------------------

def load_all_patterns(patterns_dir: Path) -> List[Dict]:
    """Load all *_patterns.json files from patterns_dir."""
    patterns: List[Dict] = []
    for path in sorted(patterns_dir.glob("*_patterns.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                patterns.extend(data)
        except Exception as exc:
            print(f"WARNING: could not load {path}: {exc}", file=sys.stderr)
    return patterns


# ---------------------------------------------------------------------------
# Synthesis prompt
# ---------------------------------------------------------------------------

_SYNTHESIS_PROMPT = """\
You are a data analysis knowledge engineer. Your task is to consolidate a set of candidate experience card patterns into a final set of high-quality, non-redundant cards.

## Existing Experience Cards (do NOT duplicate these)
{existing_cards_summary}

## Candidate Patterns (extracted from {n_cases} failure cases across {n_patterns} raw patterns)
{candidate_patterns_json}

## Instructions
1. **Group** candidate patterns that address the SAME underlying principle (same root cause / same type of mistake).
2. For each group, produce ONE well-formed final card — use the best phrasing from the group.
3. **Skip** any pattern that is already covered by an existing card (listed above).
4. **Skip** patterns that are too vague, too specific to one dataset, or duplicates of each other.
5. Keep only patterns that are:
   - General across different data analysis tasks
   - Actionable (specific steps)
   - Non-trivial (not obvious advice)
   - Have clear keywords that appear in task descriptions

## Quality bar
Aim for 3-8 final cards total. Fewer high-quality cards are better than many mediocre ones.

## Output Format
Return ONLY a JSON array (no markdown fences, no extra text):
[
  {{
    "title": "Short action-oriented title (5-8 words)",
    "when_to_use": "One sentence: what task feature triggers this card",
    "experience": "Markdown: 3-6 bullet points with specific steps",
    "checklist": ["checklist item 1", "checklist item 2", "checklist item 3"],
    "common_failure_prevented": "One sentence describing the mistake this prevents",
    "keywords": ["kw1", "kw2", "kw3"],
    "tags": ["tag1", "tag2", "tag3"],
    "source_cases": ["dacomp-003", "dacomp-012"]
  }}
]

If no patterns meet the quality bar, return an empty array: []
"""


def _tokenize_text(text: str) -> set:
    """Lowercase alphanumeric token set for Jaccard overlap."""
    import re
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _is_duplicate_pattern(pattern: Dict, existing_summary: str, threshold: float = 0.85) -> bool:
    """Return True if pattern.when_to_use has Jaccard overlap > threshold with existing_summary."""
    when_to_use = str(pattern.get("when_to_use", ""))
    if not when_to_use:
        return False
    pat_tokens = _tokenize_text(when_to_use)
    sum_tokens = _tokenize_text(existing_summary)
    if not pat_tokens or not sum_tokens:
        return False
    intersection = len(pat_tokens & sum_tokens)
    union = len(pat_tokens | sum_tokens)
    return (intersection / union) > threshold if union > 0 else False


def filter_duplicate_patterns(
    patterns: List[Dict],
    existing_summary: str,
    threshold: float = 0.85,
) -> tuple:
    """Filter out patterns that are highly similar to existing cards.

    Returns (kept, filtered) tuple.
    """
    kept: List[Dict] = []
    filtered: List[Dict] = []
    for p in patterns:
        if _is_duplicate_pattern(p, existing_summary, threshold):
            filtered.append(p)
        else:
            kept.append(p)
    return kept, filtered


def synthesize_cards_with_llm(
    patterns: List[Dict],
    existing_cards_summary: str,
    model: str = _DEFAULT_MODEL,
) -> List[Dict]:
    """Call LLM to consolidate patterns into final cards."""
    # Pre-filter patterns that duplicate existing cards (fast Jaccard check)
    kept, filtered = filter_duplicate_patterns(patterns, existing_cards_summary)
    if filtered:
        titles = [p.get("title", "?") for p in filtered]
        print(f"  [dedup] Filtered {len(filtered)} near-duplicate patterns: {titles}",
              file=sys.stderr)
    patterns = kept
    if not patterns:
        print("  [dedup] All patterns filtered as duplicates.", file=sys.stderr)
        return []

    source_cases = sorted({p.get("source_case", "") for p in patterns if p.get("source_case")})
    patterns_json = json.dumps(patterns, indent=2, ensure_ascii=False)
    # Truncate if very large
    if len(patterns_json) > 40000:
        patterns_json = patterns_json[:40000] + "\n... [truncated]"

    prompt = _SYNTHESIS_PROMPT.format(
        existing_cards_summary=existing_cards_summary,
        n_cases=len(source_cases),
        n_patterns=len(patterns),
        candidate_patterns_json=patterns_json,
    )

    print(f"Calling LLM to synthesize {len(patterns)} patterns…", file=sys.stderr)
    raw = _call_llm(prompt, model=model)

    json_match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not json_match:
        print("WARNING: LLM returned no JSON array in synthesis response", file=sys.stderr)
        return []

    try:
        result = json.loads(json_match.group())
        return result if isinstance(result, list) else []
    except json.JSONDecodeError as exc:
        print(f"WARNING: JSON parse error in synthesis: {exc}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Card writing
# ---------------------------------------------------------------------------

def _validate_card_dict(card: Dict) -> Optional[str]:
    """Return error string if card is invalid, else None."""
    for field in ("title", "when_to_use", "experience", "common_failure_prevented"):
        if not card.get(field):
            return f"Missing required field: {field!r}"
    keywords = card.get("keywords", [])
    if not isinstance(keywords, list) or len(keywords) < 3:
        return "Must have at least 3 keywords"
    return None


def write_new_cards(
    synthesized: List[Dict],
    cards_dir: Path,
    dry_run: bool = False,
) -> tuple[List[str], Dict]:
    """Write new card files and update index. Returns (added_ids, updated_index)."""
    index = load_index(cards_dir)
    added_ids: List[str] = []

    for card_dict in synthesized:
        error = _validate_card_dict(card_dict)
        if error:
            print(f"SKIP invalid card '{card_dict.get('title', '?')}': {error}", file=sys.stderr)
            continue

        card_id = next_card_id(index)
        title = card_dict["title"].strip()
        experience = card_dict.get("experience", "")
        checklist = card_dict.get("checklist", [])
        common_failure = card_dict.get("common_failure_prevented", "")
        when_to_use = card_dict.get("when_to_use", "")
        tags = card_dict.get("tags", [])
        keywords = card_dict.get("keywords", [])
        source_cases = card_dict.get("source_cases", [])

        content = render_card_markdown(
            card_id=card_id,
            title=title,
            experience=experience,
            checklist=checklist,
            common_failure_prevented=common_failure,
        )
        priority = confidence_to_priority(CONFIDENCE_GENERATED)
        rel_path = f"cards/{card_id}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}.md"

        if dry_run:
            print(f"[DRY RUN] Would create card {card_id}: {title}")
            print(f"  when_to_use: {when_to_use}")
            print(f"  keywords: {keywords}")
            print(f"  tags: {tags}")
            print(f"  source_cases: {source_cases}")
            print()
        else:
            write_card_file(card_id, title, content, cards_dir)
            index = add_card_to_index(
                index=index,
                card_id=card_id,
                title=title,
                path=rel_path,
                when_to_use=when_to_use,
                tags=tags,
                keywords=keywords,
                priority=priority,
                confidence=CONFIDENCE_GENERATED,
                source_cases=source_cases,
            )
            added_ids.append(card_id)
            print(f"Created card {card_id}: {title}", file=sys.stderr)

    if not dry_run and added_ids:
        save_index(index, cards_dir)
        print(f"Updated index.json with {len(added_ids)} new cards", file=sys.stderr)

    return added_ids, index


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synthesize candidate patterns into new experience cards"
    )
    parser.add_argument(
        "--patterns-dir",
        default="patterns",
        help="Directory containing *_patterns.json files",
    )
    parser.add_argument(
        "--cards-dir",
        default="../../../../dacomp-da/experience_cards",
        help="Experience cards directory (contains index.json)",
    )
    parser.add_argument(
        "--out-report",
        default="synthesis_report.json",
        help="Path to write synthesis report JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print proposed cards without writing files",
    )
    parser.add_argument(
        "--model",
        default=_DEFAULT_MODEL,
        help="LLM model name to use",
    )
    args = parser.parse_args()

    patterns_dir = Path(args.patterns_dir)
    cards_dir = Path(args.cards_dir)

    patterns = load_all_patterns(patterns_dir)
    if not patterns:
        print("No patterns found. Run extract_patterns.py first.", file=sys.stderr)
        sys.exit(1)
    print(f"Loaded {len(patterns)} candidate patterns from {patterns_dir}", file=sys.stderr)

    index = load_index(cards_dir)
    existing_summary = summarize_existing_cards(index)

    synthesized = synthesize_cards_with_llm(patterns, existing_summary, model=args.model)
    print(f"LLM proposed {len(synthesized)} consolidated cards", file=sys.stderr)

    if not synthesized:
        print("No cards to create.", file=sys.stderr)
        sys.exit(0)

    added_ids, final_index = write_new_cards(synthesized, cards_dir, dry_run=args.dry_run)

    # Write report
    report = {
        "added_ids": added_ids,
        "dry_run": args.dry_run,
        "total_patterns_in": len(patterns),
        "total_cards_proposed": len(synthesized),
        "total_cards_added": len(added_ids),
        "cards": synthesized,
    }
    report_path = Path(args.out_report)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Synthesis report written to {report_path}", file=sys.stderr)

    if not args.dry_run:
        print(f"\nAdded {len(added_ids)} new cards: {added_ids}")


if __name__ == "__main__":
    main()
