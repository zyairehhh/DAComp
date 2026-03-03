"""Shared pytest fixtures and path setup for experience_evolution tests."""

import json
import sys
from pathlib import Path

import pytest

# Make experience_evolution/ and tests/ importable
_TESTS_DIR = Path(__file__).parent.resolve()
_EVOLVE_DIR = _TESTS_DIR.parent
sys.path.insert(0, str(_EVOLVE_DIR))
sys.path.insert(0, str(_TESTS_DIR))   # so test files can do: from factories import ...


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cards_dir(tmp_path: Path) -> Path:
    """A temporary cards directory with index.json and cards/ subdirectory."""
    d = tmp_path / "cards"
    d.mkdir()
    (d / "cards").mkdir()
    (d / "index.json").write_text(
        json.dumps({"version": "2.0", "cards": []}), encoding="utf-8"
    )
    return d


def make_card(
    card_id: str = "exp-da-001",
    title: str = "Test Card",
    keywords: list = None,
    tags: list = None,
    priority: int = 3,
    confidence: float = 0.3,
    when_to_use: str = "When analysing data",
    source_cases: list = None,
    **extra,
) -> dict:
    """Build a minimal card dict for testing."""
    return {
        "id": card_id,
        "title": title,
        "path": f"cards/{card_id}-test-card.md",
        "when_to_use": when_to_use,
        "tags": tags or ["analysis"],
        "keywords": keywords or ["data", "analysis", "metric"],
        "priority": priority,
        "confidence": confidence,
        "source_cases": source_cases or [],
        **extra,
    }


def make_index(cards: list = None) -> dict:
    """Build a minimal index dict."""
    return {"version": "2.0", "cards": cards or []}
