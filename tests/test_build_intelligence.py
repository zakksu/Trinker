"""Tests for build intelligence (v6)."""

from __future__ import annotations

from src.build_orders.build_intelligence import (
    detect_top_mistakes,
    suggest_next_build,
    worst_timing_axis,
)
from src.analytics.compare import compare_to_build_order


def test_detect_top_mistakes_empty():
    cmp = compare_to_build_order()
    mistakes = detect_top_mistakes(cmp)
    assert isinstance(mistakes, list)


def test_suggest_next_build():
    name = suggest_next_build("feudal")
    assert isinstance(name, str)
    assert len(name) > 2


def test_worst_timing_axis():
    axis = worst_timing_axis("Britons", "Scout Rush", 620, 900)
    assert axis in ("feudal", "castle")
