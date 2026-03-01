import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_EXPERIENCE_DIR = "/workspace/_aux/experience_cards"
DEFAULT_TOP_K = 5
MIN_RETRIEVAL_SCORE = 3.0


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r"[a-z0-9_]+", text.lower())


def _normalized_token_string(text: str) -> str:
    tokens = _tokenize(text)
    return f" {' '.join(tokens)} " if tokens else " "


def _contains_token_phrase(task_token_string: str, phrase: str) -> bool:
    phrase_tokens = _tokenize(phrase)
    if not phrase_tokens:
        return False
    return f" {' '.join(phrase_tokens)} " in task_token_string


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
        "/workspace/_aux/experience_cards",
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


def _score_card(task_text: str, task_tokens: set, task_token_string: str, card: Dict) -> float:
    score = 0.0
    keyword_hits = 0
    for keyword in card.get("keywords", []):
        kw = str(keyword).strip().lower()
        if not kw:
            continue
        if _contains_token_phrase(task_token_string, kw):
            kw_tokens = _tokenize(kw)
            if len(kw_tokens) >= 2:
                score += 2.0
            else:
                score += 1.0
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

    return score


def _select_cards(task_instruction: str, cards: List[Dict], top_k: int) -> List[Dict]:
    task_text = task_instruction or ""
    task_tokens_list = _tokenize(task_text)
    task_tokens = set(task_tokens_list)
    task_token_string = f" {' '.join(task_tokens_list)} " if task_tokens_list else " "
    scored = []
    for card in cards:
        card_score = _score_card(task_text, task_tokens, task_token_string, card)
        if card_score > 0:
            scored.append((card_score, card))
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


def build_experience_snippet(
    task_instruction: str,
    experience_dir: str = DEFAULT_EXPERIENCE_DIR,
    top_k: int = DEFAULT_TOP_K,
) -> str:
    base_dir, cards, tried_paths = _discover_catalog(experience_dir)
    if not cards:
        return ""

    selected = _select_cards(task_instruction, cards, top_k=top_k)
    if not selected:
        return ""

    lines = [
        "[Optional reference — skip entirely if the task is straightforward]",
        "Experience cards below may help if you encounter difficulties.",
        "Do NOT read all cards. Only open a card file if you are stuck on that specific sub-problem.",
        "",
    ]
    for idx, card in enumerate(selected, start=1):
        rel_path = str(card.get("path", "")).lstrip("./")
        full_path = str((base_dir / rel_path).resolve()) if base_dir else rel_path
        when_to_use = str(card.get("when_to_use", "")).strip()
        lines.append(
            f"{idx}. **[{card.get('id')}] {card.get('title', '')}**\n"
            f"   - When to use: {when_to_use}\n"
            f"   - File: `{full_path}`"
        )
    return "\n".join(lines)
