"""
TRINKER v6 — Build-specific timing intelligence: pro band compare + rule-based mistakes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..analytics.compare import BuildOrderComparison, compare_to_build_order
from ..build_orders.manager import get_all_build_orders, get_build_order
from ..build_orders.timings import get_benchmarks_for


@dataclass
class StepBandRow:
    label: str
    pro_target: str
    your_actual: str
    status: str
    detail: str


@dataclass
class BuildMistake:
    step_label: str
    message: str
    severity: str  # high | medium | low


def compare_steps_to_pro_band(
    *,
    feudal_sec: Optional[int] = None,
    castle_sec: Optional[int] = None,
    build_order_id: Optional[int] = None,
) -> list[StepBandRow]:
    """Per-step you vs pro band from ideal_timings + build order step targets."""
    cmp = compare_to_build_order(
        feudal_sec=feudal_sec,
        castle_sec=castle_sec,
        build_order_id=build_order_id,
    )
    rows: list[StepBandRow] = []
    for r in cmp.rows:
        rows.append(
            StepBandRow(
                label=r.label,
                pro_target=r.target,
                your_actual=r.actual,
                status=r.status,
                detail=r.detail,
            )
        )
    return rows


def detect_top_mistakes(
    cmp: BuildOrderComparison,
    *,
    feudal_sec: Optional[int] = None,
    castle_sec: Optional[int] = None,
    limit: int = 3,
) -> list[BuildMistake]:
    """Rule-based top mistakes tied to build steps (no LLM required)."""
    mistakes: list[BuildMistake] = []

    for row in cmp.rows:
        if row.status == "red":
            mistakes.append(
                BuildMistake(
                    step_label=row.label,
                    message=f"{row.label}: {row.detail or 'behind pro band'}",
                    severity="high",
                )
            )
        elif row.status == "yellow":
            mistakes.append(
                BuildMistake(
                    step_label=row.label,
                    message=f"{row.label}: slightly late — tighten Dark Age flow",
                    severity="medium",
                )
            )

    if feudal_sec and feudal_sec > 630 and not any(m.step_label.startswith("Feudal") for m in mistakes):
        mistakes.append(
            BuildMistake(
                step_label="Feudal Age",
                message="Feudal after 10:30 — add one more farm or skip a delay",
                severity="high",
            )
        )

    if castle_sec and feudal_sec and castle_sec - feudal_sec > 360:
        mistakes.append(
            BuildMistake(
                step_label="Castle Age",
                message="Long feudal — spend fewer resources before clicking Castle",
                severity="medium",
            )
        )

    order = {"high": 0, "medium": 1, "low": 2}
    mistakes.sort(key=lambda m: order.get(m.severity, 9))
    return mistakes[:limit]


def suggest_next_build(worst_axis: str = "feudal") -> str:
    """Pick a library build targeting the player's weakest timing axis."""
    candidates = get_all_build_orders()
    if not candidates:
        return "18 Vills Scout Rush"

    if worst_axis == "castle":
        for bo in candidates:
            if "fast castle" in (bo.strategy or "").lower() or "fc" in bo.name.lower():
                return bo.name
    for bo in candidates:
        if "scout" in bo.name.lower() or "flush" in (bo.strategy or "").lower():
            return bo.name
    return candidates[0].name


def worst_timing_axis(
    civ: str,
    strategy: str,
    feudal_sec: Optional[int],
    castle_sec: Optional[int],
) -> str:
    """Return 'feudal' or 'castle' as the axis most behind pro band."""
    benchmarks = get_benchmarks_for(civ, strategy)
    if not benchmarks:
        return "feudal"
    b = benchmarks[0]
    feudal_gap = (feudal_sec or 0) - (b.feudal_max_sec or 0) if feudal_sec and b.feudal_max_sec else 0
    castle_gap = (castle_sec or 0) - (b.castle_max_sec or 0) if castle_sec and b.castle_max_sec else 0
    return "castle" if castle_gap > feudal_gap else "feudal"
