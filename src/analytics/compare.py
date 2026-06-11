"""
TRINKER - Build Order Comparison
Compare replay/session timings against a practiced build order and pro benchmarks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..build_orders.manager import get_build_order
from ..build_orders.timings import (
    evaluate_castle_time,
    evaluate_feudal_time,
    get_benchmarks_for,
)
from ..core.config import settings


def _mmss(sec: Optional[int]) -> str:
    if sec is None:
        return "—"
    return f"{sec // 60}:{sec % 60:02d}"


@dataclass
class CompareRow:
    label: str
    target: str
    actual: str
    status: str  # green | yellow | red | neutral
    detail: str = ""


@dataclass
class BuildOrderComparison:
    build_name: str
    civ: str
    strategy: str
    rows: list[CompareRow]
    summary: str

    def has_data(self) -> bool:
        return bool(self.rows)


def compare_to_build_order(
    *,
    feudal_sec: Optional[int] = None,
    castle_sec: Optional[int] = None,
    imperial_sec: Optional[int] = None,
    build_order_id: Optional[int] = None,
) -> BuildOrderComparison:
    """
    Compare age-up timings to the build order's strategy benchmarks and step targets.
    """
    bo_id = build_order_id or settings.last_practice_bo_id
    if not bo_id:
        return BuildOrderComparison(
            build_name="—",
            civ="—",
            strategy="—",
            rows=[],
            summary="Pick a build on Start Here to enable comparison.",
        )

    bo = get_build_order(bo_id)
    if not bo:
        return BuildOrderComparison(
            build_name="—",
            civ="—",
            strategy="—",
            rows=[],
            summary="Build order not found — select one on Start Here.",
        )

    strategy = bo.strategy or "Fast Castle"
    benchmarks = get_benchmarks_for(bo.civ, strategy)
    if not benchmarks:
        benchmarks = get_benchmarks_for("Any", strategy)
    benchmark = benchmarks[0] if benchmarks else None

    rows: list[CompareRow] = []

    if benchmark:
        if feudal_sec is not None and benchmark.feudal_max_sec:
            status, msg = evaluate_feudal_time(feudal_sec, benchmark)
            rows.append(CompareRow(
                label="Feudal Age",
                target=benchmark.feudal_range_str(),
                actual=_mmss(feudal_sec),
                status=status,
                detail=msg,
            ))
        elif benchmark.feudal_max_sec:
            rows.append(CompareRow(
                label="Feudal Age",
                target=benchmark.feudal_range_str(),
                actual="—",
                status="neutral",
                detail="Timing not detected in replay.",
            ))

        if castle_sec is not None and benchmark.castle_max_sec:
            status, msg = evaluate_castle_time(castle_sec, benchmark)
            rows.append(CompareRow(
                label="Castle Age",
                target=benchmark.castle_range_str(),
                actual=_mmss(castle_sec),
                status=status,
                detail=msg,
            ))
        elif benchmark.castle_max_sec:
            rows.append(CompareRow(
                label="Castle Age",
                target=benchmark.castle_range_str(),
                actual="—",
                status="neutral",
                detail="Timing not detected in replay.",
            ))

    # Step timing targets from the build order itself
    feudal_step = next((s for s in bo.steps if s.age == "Feudal"), None)
    castle_step = next((s for s in bo.steps if s.age == "Castle"), None)

    if feudal_step and feudal_step.time_sec and feudal_sec is not None:
        delta = feudal_sec - feudal_step.time_sec
        status = "green" if abs(delta) <= 15 else ("yellow" if abs(delta) <= 45 else "red")
        rows.append(CompareRow(
            label=f"BO step {feudal_step.index}: Feudal",
            target=_mmss(feudal_step.time_sec),
            actual=_mmss(feudal_sec),
            status=status,
            detail=f"{'+' if delta >= 0 else ''}{delta}s vs build guide",
        ))

    if castle_step and castle_step.time_sec and castle_sec is not None:
        delta = castle_sec - castle_step.time_sec
        status = "green" if abs(delta) <= 20 else ("yellow" if abs(delta) <= 60 else "red")
        rows.append(CompareRow(
            label=f"BO step {castle_step.index}: Castle",
            target=_mmss(castle_step.time_sec),
            actual=_mmss(castle_sec),
            status=status,
            detail=f"{'+' if delta >= 0 else ''}{delta}s vs build guide",
        ))

    if imperial_sec is not None:
        rows.append(CompareRow(
            label="Imperial Age",
            target="—",
            actual=_mmss(imperial_sec),
            status="neutral",
            detail="Imperial timing recorded.",
        ))

    if not rows:
        summary = f"No comparable timings yet for '{bo.name}'."
    else:
        bad = sum(1 for r in rows if r.status == "red")
        ok = sum(1 for r in rows if r.status == "green")
        if bad:
            summary = f"{bad} timing(s) behind target — drill '{bo.name}' again."
        elif ok:
            summary = f"Solid execution on '{bo.name}' — keep the pace consistent."
        else:
            summary = f"Partial data for '{bo.name}' — play another game with overlay on."

    return BuildOrderComparison(
        build_name=bo.name,
        civ=bo.civ,
        strategy=strategy,
        rows=rows,
        summary=summary,
    )
