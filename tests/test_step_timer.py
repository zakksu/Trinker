"""Tests for per-step ideal timing calculations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.build_orders.models import BuildOrder, BuildStep
from src.build_orders.step_timer import compute_step_timing


def _bo():
    return BuildOrder(
        name="Test",
        steps=[
            BuildStep(index=1, description="Sheep", time_str="0:00", time_sec=0),
            BuildStep(index=2, description="House", time_str="0:30", time_sec=30),
            BuildStep(index=3, description="Lumber camp", time_str="2:30", time_sec=150),
        ],
    )


def test_on_pace_is_green():
    state = compute_step_timing(_bo(), 1, elapsed_sec=10)
    assert state.status == "green"
    assert state.remaining_sec == 20


def test_overdue_is_red():
    state = compute_step_timing(_bo(), 1, elapsed_sec=40)
    assert state.status == "red"
    assert state.remaining_sec == -10


def test_progress_increases():
    early = compute_step_timing(_bo(), 2, elapsed_sec=60)
    late = compute_step_timing(_bo(), 2, elapsed_sec=120)
    assert late.progress_pct > early.progress_pct
