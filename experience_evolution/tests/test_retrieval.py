"""Tests for retrieval.py — card scoring and retrieval simulation."""

import json
from pathlib import Path

import pytest

from retrieval import (
    DEFAULT_TOP_K,
    MIN_RETRIEVAL_SCORE,
    _contains_token_phrase,
    _score_card,
    _tokenize,
    simulate_retrieval_map,
    validate_new_cards,
)
from factories import make_card


# ---------------------------------------------------------------------------
# _tokenize
# ---------------------------------------------------------------------------

def test_tokenize_basic():
    assert _tokenize("Hello World") == ["hello", "world"]


def test_tokenize_numbers_and_underscores():
    tokens = _tokenize("rubric_score 2024")
    assert "rubric_score" in tokens
    assert "2024" in tokens


def test_tokenize_empty():
    assert _tokenize("") == []


def test_tokenize_special_chars_stripped():
    tokens = _tokenize("validate! data? metric.")
    assert tokens == ["validate", "data", "metric"]


# ---------------------------------------------------------------------------
# _contains_token_phrase
# ---------------------------------------------------------------------------

def test_contains_token_phrase_single_word_match():
    token_string = " validate data metric "
    assert _contains_token_phrase(token_string, "validate") is True


def test_contains_token_phrase_multi_word_match():
    token_string = " validate data before filtering "
    assert _contains_token_phrase(token_string, "validate data") is True


def test_contains_token_phrase_no_match():
    token_string = " analyse revenue growth "
    assert _contains_token_phrase(token_string, "rubric alignment") is False


def test_contains_token_phrase_empty_phrase():
    assert _contains_token_phrase(" tokens here ", "") is False


# ---------------------------------------------------------------------------
# _score_card
# ---------------------------------------------------------------------------

def _score(instruction: str, card: dict) -> float:
    tokens = _tokenize(instruction)
    token_set = set(tokens)
    token_string = f" {' '.join(tokens)} "
    return _score_card(instruction, token_set, token_string, card)


def test_score_card_keyword_match_single():
    card = make_card(keywords=["metric"], tags=[])
    s = _score("calculate the metric for each group", card)
    assert s > 0


def test_score_card_keyword_multi_word_gives_more():
    card_multi = make_card(keywords=["validate data"], tags=[])
    card_single = make_card(keywords=["validate"], tags=[])
    instr = "validate data before any filtering"
    assert _score(instr, card_multi) > _score(instr, card_single)


def test_score_card_tag_contributes():
    card_no_tag = make_card(keywords=["metric"], tags=[])
    card_with_tag = make_card(keywords=["metric"], tags=["analysis"])
    instr = "perform analysis of the metric"
    assert _score(instr, card_with_tag) >= _score(instr, card_no_tag)


def test_score_card_zero_for_no_match():
    card = make_card(keywords=["visualization", "chart", "graph"], tags=["plot"])
    s = _score("calculate statistical summary of revenues", card)
    # Should score very low or zero since no overlap
    assert s < MIN_RETRIEVAL_SCORE


def test_score_card_priority_zero_not_selected():
    """Cards with priority=0 are disabled and must never be returned."""
    card = make_card(
        keywords=["analysis", "metric", "data", "validate"],
        tags=["analysis"],
        priority=0,
    )
    result = simulate_retrieval_map([card], {"case-1": "perform analysis metric data validate"})
    assert result["case-1"] == []


# ---------------------------------------------------------------------------
# simulate_retrieval_map
# ---------------------------------------------------------------------------

def _make_strong_card(card_id: str, keyword: str) -> dict:
    """Card with 5 matching keywords to ensure score > MIN_RETRIEVAL_SCORE."""
    return make_card(
        card_id=card_id,
        keywords=[keyword, f"{keyword}_detail", "analysis", "metric", "validate"],
        tags=["analysis"],
        priority=3,
        when_to_use=f"When you need to {keyword}",
    )


def test_simulate_retrieval_map_returns_top_matching():
    card_a = _make_strong_card("exp-da-001", "revenue")
    card_b = _make_strong_card("exp-da-002", "cohort")
    instr = "analyse revenue metric validate analysis"
    result = simulate_retrieval_map([card_a, card_b], {"case-1": instr}, top_k=4)
    assert "exp-da-001" in result["case-1"]


def test_simulate_retrieval_map_empty_instruction():
    card = _make_strong_card("exp-da-001", "revenue")
    result = simulate_retrieval_map([card], {"case-1": ""})
    assert result["case-1"] == []


def test_simulate_retrieval_map_empty_cards():
    result = simulate_retrieval_map([], {"case-1": "analyse revenue"})
    assert result["case-1"] == []


def test_simulate_retrieval_map_respects_top_k():
    cards = [_make_strong_card(f"exp-da-{i:03d}", "data") for i in range(1, 10)]
    result = simulate_retrieval_map(cards, {"case-1": "data analysis metric validate analysis"}, top_k=3)
    assert len(result["case-1"]) <= 3


def test_simulate_retrieval_map_below_threshold_excluded():
    """Cards with score < MIN_RETRIEVAL_SCORE must be excluded even if > 0."""
    card = make_card(
        keywords=["rubric"],   # only one keyword match → score = 1.0 < MIN_RETRIEVAL_SCORE=3.0
        tags=[],
        priority=3,
    )
    result = simulate_retrieval_map([card], {"case-1": "rubric score"})
    assert result["case-1"] == []


# ---------------------------------------------------------------------------
# validate_new_cards
# ---------------------------------------------------------------------------

def test_validate_new_cards_no_index(tmp_path: Path):
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    # No index.json
    result = validate_new_cards(["exp-da-001"], ["case-1"], cards_dir, {"case-1": "test"})
    assert result == {"exp-da-001": []}


def test_validate_new_cards_hit(tmp_path: Path):
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    card = _make_strong_card("exp-da-001", "revenue")
    (cards_dir / "index.json").write_text(
        json.dumps({"cards": [card]}), encoding="utf-8"
    )
    instr = "analyse revenue metric validate analysis"
    result = validate_new_cards(["exp-da-001"], ["case-1"], cards_dir, {"case-1": instr})
    assert "case-1" in result["exp-da-001"]


def test_validate_new_cards_miss(tmp_path: Path):
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    card = make_card("exp-da-001", keywords=["unrelated", "topic", "here"], priority=3)
    (cards_dir / "index.json").write_text(
        json.dumps({"cards": [card]}), encoding="utf-8"
    )
    result = validate_new_cards(
        ["exp-da-001"], ["case-1"], cards_dir,
        {"case-1": "totally different instruction content"}
    )
    assert result["exp-da-001"] == []
