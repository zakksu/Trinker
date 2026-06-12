"""Regression: late feudal must not read as 'slightly early'."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.build_orders.timings import TimingBenchmark, evaluate_feudal_time


def _bench() -> TimingBenchmark:
    return TimingBenchmark(
        id=1,
        civ="Britons",
        strategy="Archer Rush",
        pop_count=21,
        feudal_min_sec=555,
        feudal_max_sec=585,
        castle_min_sec=None,
        castle_max_sec=None,
        imperial_min_sec=None,
        imperial_max_sec=None,
        source="test",
        notes="",
    )


def test_feudal_10min_vs_945_target_is_late_not_early():
    """Actual 10:00 vs target 9:15–9:45 should describe lateness."""
    status, msg = evaluate_feudal_time(600, _bench())
    assert status == "green"
    assert "early" not in msg.lower()
    assert "late" in msg.lower() or "behind" in msg.lower() or "pace" in msg.lower()


def test_feudal_on_pace_inside_window():
    status, msg = evaluate_feudal_time(570, _bench())
    assert status == "green"
    assert "on pace" in msg.lower()
