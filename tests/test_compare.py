"""Tests for build order comparison."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analytics.compare import compare_to_build_order
from src.core.config import settings


def test_compare_without_build_order():
    old = settings.last_practice_bo_id
    settings.last_practice_bo_id = None
    try:
        cmp = compare_to_build_order(feudal_sec=600)
        assert not cmp.has_data()
        assert "Start Here" in cmp.summary
    finally:
        settings.last_practice_bo_id = old


def test_compare_with_timings_no_build():
    cmp = compare_to_build_order(
        feudal_sec=555,
        castle_sec=900,
        build_order_id=999999,
    )
    assert not cmp.has_data() or "not found" in cmp.summary.lower()
