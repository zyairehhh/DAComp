"""Test data factories — shared across all test modules."""

from pathlib import Path


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
