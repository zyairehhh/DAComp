"""Standalone experience card retrieval module.

Mirrors the scoring logic from methods/da-agent/da_agent/agent/experience.py
without the agent-runtime dependencies (no /workspace/ paths, no snippet rendering).

Public API:
  simulate_retrieval_map(cards, tasks, top_k) -> {case_id: [card_id, ...]}
  validate_new_cards(new_card_ids, test_case_ids, cards_dir, instructions) -> {card_id: [case_id, ...]}
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List


MIN_RETRIEVAL_SCORE = 3.0
DEFAULT_TOP_K = 4


# ---------------------------------------------------------------------------
# Tokenisation (identical to experience.py)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r"[a-z0-9_]+", text.lower())


def _contains_token_phrase(task_token_string: str, phrase: str) -> bool:
    phrase_tokens = _tokenize(phrase)
    if not phrase_tokens:
        return False
    return f" {' '.join(phrase_tokens)} " in task_token_string


# ---------------------------------------------------------------------------
# Scoring (identical to experience.py)
# ---------------------------------------------------------------------------

def _overlap_score(task_tokens: set, card: Dict) -> float:
    card_text = " ".join([
        str(card.get("when_to_use", "")),
        str(card.get("title", "")),
    ])
    card_tokens = set(_tokenize(card_text))
    if not card_tokens:
        return 0.0
    overlap = len(task_tokens & card_tokens) / len(card_tokens)
    return min(1.5, overlap * 3.0)


def _score_card(task_text: str, task_tokens: set, task_token_string: str, card: Dict) -> float:
    score = 0.0
    keyword_hits = 0
    for keyword in card.get("keywords", []):
        kw = str(keyword).strip().lower()
        if not kw:
            continue
        if _contains_token_phrase(task_token_string, kw):
            kw_tokens = _tokenize(kw)
            score += 2.0 if len(kw_tokens) >= 2 else 1.0
            keyword_hits += 1

    tag_hits = 0
    for tag in card.get("tags", []):
        tag_lower = str(tag).strip().lower()
        tag_tokens = tag_lower.replace("_", " ").split()
        for tt in tag_tokens:
            if tt and tt in task_tokens:
                score += 0.5
                tag_hits += 1
                break

    if keyword_hits >= 3 and tag_hits >= 1:
        score += 2.0

    score += _overlap_score(task_tokens, card)
    return score


def _select_cards(task_instruction: str, cards: List[Dict], top_k: int) -> List[Dict]:
    eligible = [c for c in cards if c.get("priority", 0) != 0]
    task_text = task_instruction or ""
    task_tokens_list = _tokenize(task_text)
    task_tokens = set(task_tokens_list)
    task_token_string = f" {' '.join(task_tokens_list)} " if task_tokens_list else " "

    scored = []
    for card in eligible:
        s = _score_card(task_text, task_tokens, task_token_string, card)
        if s > 0:
            scored.append((s, card))

    if not scored:
        return []

    scored.sort(key=lambda x: (x[0], float(x[1].get("priority", 0))), reverse=True)
    best_score = scored[0][0]

    selected = []
    for score, card in scored:
        if score < MIN_RETRIEVAL_SCORE:
            continue
        if score < best_score * 0.5:
            continue
        selected.append(card)
        if len(selected) >= top_k:
            break
    return selected


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def simulate_retrieval_map(
    cards: List[Dict],
    tasks: Dict[str, str],
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, List[str]]:
    """For every task, simulate which card IDs would be retrieved.

    Args:
        cards: List of card dicts from index.json (must have 'id', 'keywords', etc.)
        tasks: {instance_id: instruction_text}
        top_k: Max cards to retrieve per task.

    Returns:
        {instance_id: [retrieved_card_id, ...]}  (empty list if nothing qualifies)
    """
    result: Dict[str, List[str]] = {}
    for case_id, instruction in tasks.items():
        selected = _select_cards(instruction, cards, top_k=top_k)
        result[case_id] = [c["id"] for c in selected]
    return result


def validate_new_cards(
    new_card_ids: List[str],
    test_case_ids: List[str],
    cards_dir: Path,
    instructions: Dict[str, str],
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, List[str]]:
    """Check which test cases each new card would be retrieved for.

    Loads the full card catalog from cards_dir/index.json (which should already
    include the newly written cards), then simulates retrieval for each test case.

    Returns:
        {card_id: [case_ids where this card is retrieved]}
        Cards not retrieved for any case get an empty list (potential keyword issue).
    """
    index_path = cards_dir / "index.json"
    if not index_path.exists():
        return {cid: [] for cid in new_card_ids}

    data = json.loads(index_path.read_text(encoding="utf-8"))
    all_cards = data.get("cards", []) if isinstance(data, dict) else []

    test_tasks = {cid: instructions[cid] for cid in test_case_ids if cid in instructions}
    retrieval_map = simulate_retrieval_map(all_cards, test_tasks, top_k=top_k)

    # Invert: card_id → list of cases where it appears
    new_id_set = set(new_card_ids)
    hits: Dict[str, List[str]] = {cid: [] for cid in new_card_ids}
    for case_id, retrieved_ids in retrieval_map.items():
        for card_id in retrieved_ids:
            if card_id in new_id_set:
                hits[card_id].append(case_id)
    return hits
