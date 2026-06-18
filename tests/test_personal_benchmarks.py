"""Tests for personal feudal benchmarks (v5)."""

from __future__ import annotations

from src.analytics.personal_benchmarks import (
    format_personal_benchmark_line,
    get_personal_benchmark,
)


def test_personal_benchmark_empty():
    pb = get_personal_benchmark("Britons", "Scout Rush", build_order_id=999999)
    assert pb.sample_count == 0
    assert "play more" in format_personal_benchmark_line("Britons", "Scout Rush", 999999).lower()


def test_personal_benchmark_line_no_crash():
    line = format_personal_benchmark_line("Any", "Fast Castle")
    assert isinstance(line, str)
    assert len(line) > 5
