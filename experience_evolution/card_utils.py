"""Shared utilities for experience card management.

Conventions:
- All mutating functions return a NEW dict; originals are never modified.
- `cards_dir` always points to the directory containing index.json and the cards/ subdirectory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple  # noqa: F401 (Tuple used in rollback_specific_cards)


# ---------------------------------------------------------------------------
# Confidence constants
# ---------------------------------------------------------------------------
CONFIDENCE_HANDCRAFTED: float = 1.0
CONFIDENCE_GENERATED: float = 0.3

_CONFIDENCE_IMPROVE_DELTA: float = 0.2
_CONFIDENCE_REGRESS_DELTA: float = -0.3

# Rubric-percentage deltas (absolute, e.g. 0.02 = 2 percentage-points)
IMPROVEMENT_THRESHOLD: float = 0.02
REGRESSION_THRESHOLD: float = -0.02
# Max allowed drop vs previous iteration's score (relative safety net)
RELATIVE_REGRESSION_THRESHOLD: float = -0.05


def confidence_to_priority(confidence: float) -> int:
    """Map confidence score (0.0–1.0) to retrieval priority (0–5)."""
    if confidence >= 0.8:
        return 5
    if confidence >= 0.5:
        return 4
    if confidence >= 0.2:
        return 3
    return 0


# ---------------------------------------------------------------------------
# Index I/O
# ---------------------------------------------------------------------------

def load_index(cards_dir: Path) -> Dict:
    """Load index.json from cards_dir, migrating missing confidence fields."""
    index_path = cards_dir / "index.json"
    if not index_path.exists():
        return {"version": "2.0", "cards": []}
    raw = json.loads(index_path.read_text(encoding="utf-8"))
    cards = raw.get("cards", [])
    migrated = [
        {**card, "confidence": CONFIDENCE_HANDCRAFTED}
        if "confidence" not in card
        else card
        for card in cards
    ]
    return {**raw, "cards": migrated}


def save_index(index: Dict, cards_dir: Path) -> None:
    """Write index.json atomically (write then replace)."""
    index_path = cards_dir / "index.json"
    tmp_path = index_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(index_path)


# ---------------------------------------------------------------------------
# Card ID management
# ---------------------------------------------------------------------------

def next_card_id(index: Dict) -> str:
    """Return the next available exp-da-NNN id."""
    existing = {card["id"] for card in index.get("cards", [])}
    n = 1
    while True:
        candidate = f"exp-da-{n:03d}"
        if candidate not in existing:
            return candidate
        n += 1


# ---------------------------------------------------------------------------
# Card file I/O
# ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def card_filename(card_id: str, title: str) -> str:
    return f"{card_id}-{_slug(title)}.md"


def write_card_file(card_id: str, title: str, content: str, cards_dir: Path) -> Path:
    """Write a card markdown file; returns the written path."""
    filename = card_filename(card_id, title)
    card_path = cards_dir / "cards" / filename
    card_path.parent.mkdir(parents=True, exist_ok=True)
    card_path.write_text(content, encoding="utf-8")
    return card_path


def render_card_markdown(
    card_id: str,
    title: str,
    experience: str,
    checklist: List[str],
    common_failure_prevented: str,
) -> str:
    """Render experience card markdown from structured fields."""
    checklist_lines = "\n".join(f"- {item}" for item in checklist) if checklist else ""
    checklist_section = f"\n## Checklist\n{checklist_lines}\n" if checklist_lines else ""
    return (
        f"# {card_id} {title}\n\n"
        f"## Experience\n{experience}\n"
        f"{checklist_section}\n"
        f"## Common failure prevented\n{common_failure_prevented}\n"
    )


# ---------------------------------------------------------------------------
# Index manipulation (all return new dicts)
# ---------------------------------------------------------------------------

def add_card_to_index(
    index: Dict,
    card_id: str,
    title: str,
    path: str,
    when_to_use: str,
    tags: List[str],
    keywords: List[str],
    priority: int,
    confidence: float,
    source_cases: Optional[List[str]] = None,
) -> Dict:
    """Return a new index dict with the card appended."""
    new_entry: Dict = {
        "id": card_id,
        "title": title,
        "path": path,
        "when_to_use": when_to_use,
        "tags": tags,
        "keywords": keywords,
        "priority": priority,
        "confidence": round(confidence, 3),
    }
    if source_cases:
        new_entry["source_cases"] = source_cases
    return {**index, "cards": [*index.get("cards", []), new_entry]}


def rollback_cards(added_ids: List[str], index: Dict, cards_dir: Path) -> Dict:
    """Remove newly added cards from index and disk. Returns updated index."""
    remove_set = set(added_ids)
    kept = []
    for card in index.get("cards", []):
        if card["id"] in remove_set:
            card_path = cards_dir / card.get("path", "")
            if card_path.exists():
                card_path.unlink()
        else:
            kept.append(card)
    return {**index, "cards": kept}


def rollback_specific_cards(
    card_ids: List[str],
    index: Dict,
    cards_dir: Path,
) -> Tuple[Dict, List[str]]:
    """Remove only the specified card IDs from index and disk.

    Unlike rollback_cards (which removes all newly added cards), this function
    performs a surgical rollback — only the named cards are removed, leaving
    other newly added cards intact.

    Returns:
        (updated_index, actually_removed_ids)
    """
    remove_set = set(card_ids)
    kept = []
    removed: List[str] = []
    for card in index.get("cards", []):
        if card["id"] in remove_set:
            card_path = cards_dir / card.get("path", "")
            if card_path.exists():
                card_path.unlink()
            removed.append(card["id"])
        else:
            kept.append(card)
    return {**index, "cards": kept}, removed


def update_confidence(card_id: str, delta_rubrics_pct: float, index: Dict) -> Dict:
    """Update confidence for one card based on rubrics percentage delta.

    delta_rubrics_pct: difference in rubrics_percentage (e.g. +0.03 for +3%).
    Returns a new index dict.
    """
    updated_cards = []
    for card in index.get("cards", []):
        if card["id"] != card_id:
            updated_cards.append(card)
            continue
        current = float(card.get("confidence", CONFIDENCE_GENERATED))
        if delta_rubrics_pct > IMPROVEMENT_THRESHOLD:
            new_conf = min(1.0, current + _CONFIDENCE_IMPROVE_DELTA)
        elif delta_rubrics_pct < REGRESSION_THRESHOLD:
            new_conf = max(0.0, current + _CONFIDENCE_REGRESS_DELTA)
        else:
            new_conf = current
        new_priority = confidence_to_priority(new_conf)
        updated_cards.append({**card, "confidence": round(new_conf, 3), "priority": new_priority})
    return {**index, "cards": updated_cards}


# ---------------------------------------------------------------------------
# Summaries for LLM prompts
# ---------------------------------------------------------------------------

def summarize_existing_cards(index: Dict, include_disabled: bool = False) -> str:
    """Return a compact summary string for use in LLM deduplication prompts."""
    lines = []
    for card in index.get("cards", []):
        if not include_disabled and card.get("priority", 0) == 0:
            continue
        lines.append(
            f"- [{card['id']}] {card['title']}: {card.get('when_to_use', '').strip()}"
        )
    return "\n".join(lines) if lines else "(none)"


# ---------------------------------------------------------------------------
# Score helpers
# ---------------------------------------------------------------------------

def parse_rubrics_percentage(row: Dict) -> float:
    """Parse rubrics_percentage from a CSV row, returning 0.0 on failure."""
    raw = row.get("rubrics_percentage", "")
    try:
        return float(raw) if raw else 0.0
    except (ValueError, TypeError):
        return 0.0


def instance_id_to_index(instance_id: str) -> int:
    """Convert 'dacomp-NNN' to 0-based JSONL index (dacomp-001 → 0)."""
    try:
        return int(instance_id.split("-")[-1]) - 1
    except (ValueError, IndexError):
        raise ValueError(f"Cannot parse index from instance_id: {instance_id!r}")
