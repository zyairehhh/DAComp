"""Tests for card_utils.py — card index management and confidence system."""

import json
from pathlib import Path

import pytest

from card_utils import (
    CONFIDENCE_GENERATED,
    CONFIDENCE_HANDCRAFTED,
    IMPROVEMENT_THRESHOLD,
    REGRESSION_THRESHOLD,
    RELATIVE_REGRESSION_THRESHOLD,
    add_card_to_index,
    card_filename,
    confidence_to_priority,
    load_index,
    next_card_id,
    render_card_markdown,
    rollback_cards,
    rollback_specific_cards,
    save_index,
    summarize_existing_cards,
    update_confidence,
)

from factories import make_card, make_index


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_relative_regression_threshold_stricter_than_regression():
    """RELATIVE_REGRESSION_THRESHOLD must be more lenient (less negative) than
    REGRESSION_THRESHOLD, because it governs a softer guard, not the hard floor."""
    assert RELATIVE_REGRESSION_THRESHOLD < 0
    assert RELATIVE_REGRESSION_THRESHOLD < REGRESSION_THRESHOLD  # e.g. -0.05 < -0.02


# ---------------------------------------------------------------------------
# confidence_to_priority
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("conf, expected", [
    (1.0, 5),
    (0.8, 5),
    (0.79, 4),
    (0.5, 4),
    (0.49, 3),
    (0.2, 3),
    (0.19, 0),
    (0.0, 0),
])
def test_confidence_to_priority_boundaries(conf, expected):
    assert confidence_to_priority(conf) == expected


# ---------------------------------------------------------------------------
# next_card_id
# ---------------------------------------------------------------------------

def test_next_card_id_empty_index():
    assert next_card_id(make_index()) == "exp-da-001"


def test_next_card_id_skips_used_ids():
    idx = make_index([make_card("exp-da-001"), make_card("exp-da-002")])
    assert next_card_id(idx) == "exp-da-003"


def test_next_card_id_fills_gap():
    idx = make_index([make_card("exp-da-001"), make_card("exp-da-003")])
    assert next_card_id(idx) == "exp-da-002"


# ---------------------------------------------------------------------------
# card_filename / render_card_markdown
# ---------------------------------------------------------------------------

def test_card_filename_slug():
    fn = card_filename("exp-da-007", "Verify Data Completeness Before Filtering")
    assert fn == "exp-da-007-verify-data-completeness-before-filtering.md"


def test_card_filename_special_chars():
    fn = card_filename("exp-da-001", "A/B Test & Validation!")
    assert fn.startswith("exp-da-001-")
    assert "/" not in fn
    assert "&" not in fn


def test_render_card_markdown_contains_sections():
    md = render_card_markdown(
        "exp-da-001", "My Card",
        experience="Always validate.",
        checklist=["Step 1", "Step 2"],
        common_failure_prevented="Skipping validation.",
    )
    assert "# exp-da-001 My Card" in md
    assert "## Experience" in md
    assert "Always validate." in md
    assert "## Checklist" in md
    assert "- Step 1" in md
    assert "## Common failure prevented" in md


def test_render_card_markdown_no_checklist():
    md = render_card_markdown("exp-da-001", "T", "E", [], "F")
    assert "## Checklist" not in md


# ---------------------------------------------------------------------------
# add_card_to_index (immutability)
# ---------------------------------------------------------------------------

def test_add_card_to_index_immutable():
    original = make_index()
    updated = add_card_to_index(
        original, "exp-da-001", "T", "cards/t.md", "When X", ["tag"], ["kw"], 3, 0.3
    )
    assert original["cards"] == []          # original unchanged
    assert len(updated["cards"]) == 1
    assert updated["cards"][0]["id"] == "exp-da-001"


def test_add_card_to_index_source_cases_optional():
    idx = add_card_to_index(make_index(), "exp-da-001", "T", "p", "W", [], [], 3, 0.3)
    assert "source_cases" not in idx["cards"][0]

    idx2 = add_card_to_index(make_index(), "exp-da-001", "T", "p", "W", [], [], 3, 0.3,
                              source_cases=["dacomp-001"])
    assert idx2["cards"][0]["source_cases"] == ["dacomp-001"]


# ---------------------------------------------------------------------------
# load_index / save_index
# ---------------------------------------------------------------------------

def test_load_index_empty_dir(cards_dir: Path):
    idx = load_index(cards_dir)
    assert idx["cards"] == []


def test_load_index_migrates_missing_confidence(cards_dir: Path):
    """Cards without 'confidence' field get confidence=1.0 (handcrafted default)."""
    raw = {"version": "2.0", "cards": [{"id": "exp-da-001", "title": "T"}]}
    (cards_dir / "index.json").write_text(json.dumps(raw), encoding="utf-8")

    idx = load_index(cards_dir)
    assert idx["cards"][0]["confidence"] == CONFIDENCE_HANDCRAFTED


def test_save_index_atomic(cards_dir: Path):
    """save_index must not leave a .tmp file behind."""
    idx = make_index([make_card()])
    save_index(idx, cards_dir)

    assert not list(cards_dir.glob("*.tmp"))
    reloaded = json.loads((cards_dir / "index.json").read_text())
    assert reloaded["cards"][0]["id"] == "exp-da-001"


def test_save_load_roundtrip(cards_dir: Path):
    idx = make_index([make_card("exp-da-005", confidence=0.7)])
    save_index(idx, cards_dir)
    loaded = load_index(cards_dir)
    assert loaded["cards"][0]["id"] == "exp-da-005"
    assert loaded["cards"][0]["confidence"] == 0.7


# ---------------------------------------------------------------------------
# rollback_cards
# ---------------------------------------------------------------------------

def test_rollback_cards_removes_from_index(cards_dir: Path):
    card = make_card("exp-da-001")
    idx = make_index([card])
    result = rollback_cards(["exp-da-001"], idx, cards_dir)
    assert result["cards"] == []


def test_rollback_cards_deletes_md_file(cards_dir: Path):
    md_file = cards_dir / "cards" / "exp-da-001-test-card.md"
    md_file.write_text("content")
    card = make_card("exp-da-001", path="cards/exp-da-001-test-card.md")
    idx = make_index([card])

    rollback_cards(["exp-da-001"], idx, cards_dir)
    assert not md_file.exists()


def test_rollback_cards_keeps_other_cards(cards_dir: Path):
    c1 = make_card("exp-da-001")
    c2 = make_card("exp-da-002", title="Keep Me")
    idx = make_index([c1, c2])
    result = rollback_cards(["exp-da-001"], idx, cards_dir)
    assert len(result["cards"]) == 1
    assert result["cards"][0]["id"] == "exp-da-002"


def test_rollback_cards_immutable(cards_dir: Path):
    original_cards = [make_card("exp-da-001")]
    idx = make_index(original_cards)
    rollback_cards(["exp-da-001"], idx, cards_dir)
    assert len(idx["cards"]) == 1  # original not mutated


# ---------------------------------------------------------------------------
# rollback_specific_cards
# ---------------------------------------------------------------------------

def test_rollback_specific_cards_surgical(cards_dir: Path):
    c1 = make_card("exp-da-001")
    c2 = make_card("exp-da-002", title="Keep Me")
    idx = make_index([c1, c2])
    new_idx, removed = rollback_specific_cards(["exp-da-001"], idx, cards_dir)

    assert removed == ["exp-da-001"]
    assert len(new_idx["cards"]) == 1
    assert new_idx["cards"][0]["id"] == "exp-da-002"
    assert len(idx["cards"]) == 2  # original unchanged


def test_rollback_specific_cards_returns_actually_removed(cards_dir: Path):
    idx = make_index([make_card("exp-da-001")])
    _, removed = rollback_specific_cards(["exp-da-001", "exp-da-099"], idx, cards_dir)
    # exp-da-099 not in index, so only exp-da-001 actually removed
    assert removed == ["exp-da-001"]


# ---------------------------------------------------------------------------
# update_confidence
# ---------------------------------------------------------------------------

def test_update_confidence_improvement(cards_dir: Path):
    card = make_card(confidence=0.3)
    idx = make_index([card])
    updated = update_confidence("exp-da-001", IMPROVEMENT_THRESHOLD + 0.01, idx)
    new_conf = updated["cards"][0]["confidence"]
    assert new_conf == pytest.approx(0.5, abs=0.001)


def test_update_confidence_regression(cards_dir: Path):
    card = make_card(confidence=0.5)
    idx = make_index([card])
    updated = update_confidence("exp-da-001", REGRESSION_THRESHOLD - 0.01, idx)
    new_conf = updated["cards"][0]["confidence"]
    assert new_conf == pytest.approx(0.2, abs=0.001)


def test_update_confidence_neutral():
    card = make_card(confidence=0.4)
    idx = make_index([card])
    updated = update_confidence("exp-da-001", 0.0, idx)
    assert updated["cards"][0]["confidence"] == pytest.approx(0.4)


def test_update_confidence_clamped_at_1():
    card = make_card(confidence=0.9)
    idx = make_index([card])
    updated = update_confidence("exp-da-001", 0.1, idx)
    assert updated["cards"][0]["confidence"] <= 1.0


def test_update_confidence_clamped_at_0():
    card = make_card(confidence=0.1)
    idx = make_index([card])
    updated = update_confidence("exp-da-001", -0.5, idx)
    assert updated["cards"][0]["confidence"] >= 0.0


def test_update_confidence_immutable():
    card = make_card(confidence=0.3)
    idx = make_index([card])
    update_confidence("exp-da-001", 0.1, idx)
    assert idx["cards"][0]["confidence"] == 0.3  # original unchanged


# ---------------------------------------------------------------------------
# summarize_existing_cards
# ---------------------------------------------------------------------------

def test_summarize_existing_cards_includes_active():
    c = make_card("exp-da-001", title="My Card", priority=3)
    idx = make_index([c])
    summary = summarize_existing_cards(idx)
    assert "exp-da-001" in summary
    assert "My Card" in summary


def test_summarize_existing_cards_excludes_disabled():
    c = make_card("exp-da-001", priority=0)
    idx = make_index([c])
    summary = summarize_existing_cards(idx)
    assert "exp-da-001" not in summary


def test_summarize_existing_cards_empty():
    assert summarize_existing_cards(make_index()) == "(none)"
