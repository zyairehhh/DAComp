import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_EXPERIENCE_DIR = "/workspace/_aux/experience_cards"
DEFAULT_TOP_K = 4
MIN_RETRIEVAL_SCORE = 3.0

# Hybrid scoring: weight for semantic score vs keyword score
SEMANTIC_ALPHA = 0.7
_EMBEDDING_MODEL = "text-embedding-v3"
_EMBEDDING_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
_EMBEDDING_DIM = 1024


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


def _overlap_score(task_tokens: set, card: Dict) -> float:
    """Semantic-style bonus: token overlap between task and card when_to_use + title (no embeddings)."""
    card_text = " ".join([
        str(card.get("when_to_use", "")),
        str(card.get("title", "")),
    ])
    card_tokens = set(_tokenize(card_text))
    if not card_tokens:
        return 0.0
    overlap = len(task_tokens & card_tokens) / len(card_tokens)
    return min(1.5, overlap * 3.0)  # cap bonus at 1.5


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

    score += _overlap_score(task_tokens, card)
    return score


def _get_task_embedding(task_text: str) -> List[float]:
    """Fetch embedding for a single task instruction via DashScope API.

    Returns an empty list on failure so the caller can fall back to
    keyword-only scoring without crashing.
    """
    api_key = os.environ.get("BAILIAN_API_KEY", "")
    if not api_key:
        return []
    try:
        import requests
        resp = requests.post(
            _EMBEDDING_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": _EMBEDDING_MODEL, "input": [task_text], "dimensions": _EMBEDDING_DIM},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    except Exception:
        return []


def _cosine_sim(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _hybrid_score(
    keyword_score: float,
    task_emb: List[float],
    card_emb: List[float],
    alpha: float = SEMANTIC_ALPHA,
    max_keyword_score: float = 10.0,
) -> float:
    """Blend keyword score with semantic cosine similarity.

    Falls back to pure keyword score when either embedding is absent.
    """
    if not card_emb or not task_emb:
        return keyword_score
    sem_sim = _cosine_sim(task_emb, card_emb)
    sem_score = max(0.0, sem_sim) * 5.0
    kw_score_norm = min(keyword_score, max_keyword_score) / max_keyword_score * 5.0
    return alpha * sem_score + (1.0 - alpha) * kw_score_norm


def _select_cards(task_instruction: str, cards: List[Dict], top_k: int) -> List[Dict]:
    # Skip disabled cards (priority 0 = do not retrieve)
    cards = [c for c in cards if c.get("priority", 0) != 0]
    task_text = task_instruction or ""
    task_tokens_list = _tokenize(task_text)
    task_tokens = set(task_tokens_list)
    task_token_string = f" {' '.join(task_tokens_list)} " if task_tokens_list else " "

    # Fetch task embedding once; used for all cards (falls back gracefully)
    task_emb = _get_task_embedding(task_text)

    scored = []
    for card in cards:
        kw_s = _score_card(task_text, task_tokens, task_token_string, card)
        card_emb = card.get("embedding") or []
        s = _hybrid_score(kw_s, task_emb, card_emb)
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
