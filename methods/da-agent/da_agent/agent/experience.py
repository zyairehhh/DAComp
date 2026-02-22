import json
import re
from pathlib import Path
from typing import Dict, List


DEFAULT_EXPERIENCE_DIR = "/workspace/dacomp-da/experience_cards"
DEFAULT_TOP_K = 5


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r"[a-z0-9_]+", text.lower())


def _load_catalog(experience_dir: str) -> List[Dict]:
    base = Path(experience_dir)
    index_path = base / "index.json"
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    cards = data.get("cards", []) if isinstance(data, dict) else []
    valid_cards = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        if not card.get("id") or not card.get("path"):
            continue
        valid_cards.append(card)
    return valid_cards


def _score_card(task_text: str, task_tokens: set, card: Dict) -> float:
    score = 0.0
    lowered = task_text.lower()
    for keyword in card.get("keywords", []):
        kw = str(keyword).strip().lower()
        if not kw:
            continue
        if kw in lowered:
            score += 3.0
        else:
            kw_tokens = _tokenize(kw)
            if kw_tokens and all(token in task_tokens for token in kw_tokens):
                score += 1.5
    for tag in card.get("tags", []):
        tag_token = str(tag).strip().lower()
        if tag_token and tag_token in task_tokens:
            score += 1.0
    # Small deterministic boost from author-set priority.
    score += float(card.get("priority", 0)) * 0.2
    return score


def _select_cards(task_instruction: str, cards: List[Dict], top_k: int) -> List[Dict]:
    task_text = task_instruction or ""
    task_tokens = set(_tokenize(task_text))
    scored = []
    for card in cards:
        card_score = _score_card(task_text, task_tokens, card)
        if card_score > 0:
            scored.append((card_score, card))
    if not scored:
        # Fallback to highest-priority generic cards when no lexical hit.
        ranked = sorted(cards, key=lambda x: float(x.get("priority", 0)), reverse=True)
        return ranked[:top_k]
    scored.sort(key=lambda x: (x[0], float(x[1].get("priority", 0))), reverse=True)
    return [card for _, card in scored[:top_k]]


def build_experience_snippet(
    task_instruction: str,
    experience_dir: str = DEFAULT_EXPERIENCE_DIR,
    top_k: int = DEFAULT_TOP_K,
) -> str:
    cards = _load_catalog(experience_dir)
    if not cards:
        return (
            "No experience catalog detected at `/workspace/dacomp-da/experience_cards/index.json`.\n"
            "Proceed without experience cards."
        )

    selected = _select_cards(task_instruction, cards, top_k=top_k)
    if not selected:
        return "No relevant experience cards retrieved for this task."

    lines = [
        "Retrieved experience cards (optional, on-demand):",
        "Do NOT load all cards. Read only cards that match your current sub-task.",
    ]
    for idx, card in enumerate(selected, start=1):
        rel_path = str(card.get("path", "")).lstrip("./")
        full_path = f"/workspace/dacomp-da/experience_cards/{rel_path}"
        when_to_use = str(card.get("when_to_use", "")).strip()
        lines.append(
            f"{idx}. [{card.get('id')}] {card.get('title', '')}\n"
            f"   - when_to_use: {when_to_use}\n"
            f"   - file: `{full_path}`"
        )
    return "\n".join(lines)
