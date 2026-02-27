import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_EXPERIENCE_DIR = "/workspace/dacomp-da/experience_cards"
DEFAULT_TOP_K = 3
MIN_RETRIEVAL_SCORE = 1.5


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r"[a-z0-9_]+", text.lower())


def _load_catalog_at(base: Path) -> List[Dict]:
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


def _discover_catalog(experience_dir: str) -> Tuple[Optional[Path], List[Dict], List[Path]]:
    candidates: List[Path] = []
    for raw in (
        experience_dir,
        "/workspace/experience_cards",
        "/workspace/dacomp-da/experience_cards",
        "/workspace",
    ):
        path = Path(raw)
        if path not in candidates:
            candidates.append(path)

    for base in candidates:
        cards = _load_catalog_at(base)
        if cards:
            return base, cards, candidates
    return None, [], candidates


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
        return []
    scored.sort(key=lambda x: (x[0], float(x[1].get("priority", 0))), reverse=True)
    best_score = scored[0][0]
    selected = []
    for score, card in scored:
        # Keep high-confidence hits only. This avoids injecting broad cards that
        # add noise and hurt accuracy on threshold-sensitive tasks.
        if score < MIN_RETRIEVAL_SCORE:
            continue
        if score < best_score - 1.5:
            continue
        selected.append(card)
        if len(selected) >= top_k:
            break
    return selected


def build_experience_snippet(
    task_instruction: str,
    experience_dir: str = DEFAULT_EXPERIENCE_DIR,
    top_k: int = DEFAULT_TOP_K,
) -> str:
    base_dir, cards, tried_paths = _discover_catalog(experience_dir)
    if not cards:
        tried = ", ".join(f"`{str(path / 'index.json')}`" for path in tried_paths)
        return (
            f"No experience catalog detected. Tried: {tried}.\n"
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
        full_path = str((base_dir / rel_path).resolve()) if base_dir else rel_path
        when_to_use = str(card.get("when_to_use", "")).strip()
        lines.append(
            f"{idx}. [{card.get('id')}] {card.get('title', '')}\n"
            f"   - when_to_use: {when_to_use}\n"
            f"   - file: `{full_path}`"
        )
    return "\n".join(lines)
