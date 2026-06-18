"""
TRINKER v5 — Personal feudal/castle benchmarks from replay-derived session history.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional

from ..build_orders.manager import get_build_order
from ..build_orders.timings import get_benchmarks_for
from .session import get_sessions


def _mmss(sec: Optional[float]) -> str:
    if sec is None:
        return "—"
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


@dataclass
class PersonalBenchmark:
    civ: str
    strategy: str
    build_order_id: Optional[int]
    sample_count: int
    median_feudal_sec: Optional[float]
    median_castle_sec: Optional[float]
    target_feudal_sec: Optional[int]
    delta_feudal_sec: Optional[float]

    def feudal_status(self) -> str:
        if self.median_feudal_sec is None or self.target_feudal_sec is None:
            return "neutral"
        delta = self.median_feudal_sec - self.target_feudal_sec
        if delta <= 15:
            return "green"
        if delta <= 45:
            return "yellow"
        return "red"


def get_personal_benchmark(
    civ: str,
    strategy: str = "",
    build_order_id: Optional[int] = None,
    last_n: int = 10,
) -> PersonalBenchmark:
    """Median feudal/castle from the player's last N sessions on this build/civ."""
    sessions = get_sessions(build_order_id=build_order_id, limit=last_n * 3)
    if build_order_id:
        filtered = sessions[:last_n]
    else:
        strat = (strategy or "").lower()
        filtered = []
        for s in sessions:
            bo = get_build_order(s.build_order_id)
            if not bo:
                continue
            if bo.civ.lower() not in (civ.lower(), "any"):
                continue
            if strat and strat not in (bo.strategy or "").lower():
                continue
            filtered.append(s)
            if len(filtered) >= last_n:
                break

    feudal_vals = [s.feudal_time_sec for s in filtered if s.feudal_time_sec]
    castle_vals = [s.castle_time_sec for s in filtered if s.castle_time_sec]
    median_feudal = statistics.median(feudal_vals) if feudal_vals else None
    median_castle = statistics.median(castle_vals) if castle_vals else None

    target_feudal = None
    benchmarks = get_benchmarks_for(civ, strategy or "Fast Castle")
    if not benchmarks:
        benchmarks = get_benchmarks_for("Any", strategy or "Fast Castle")
    if benchmarks and benchmarks[0].feudal_max_sec:
        target_feudal = benchmarks[0].feudal_max_sec

    delta = None
    if median_feudal is not None and target_feudal is not None:
        delta = median_feudal - target_feudal

    return PersonalBenchmark(
        civ=civ,
        strategy=strategy or "Fast Castle",
        build_order_id=build_order_id,
        sample_count=len(filtered),
        median_feudal_sec=median_feudal,
        median_castle_sec=median_castle,
        target_feudal_sec=target_feudal,
        delta_feudal_sec=delta,
    )


def format_personal_benchmark_line(
    civ: str,
    strategy: str = "",
    build_order_id: Optional[int] = None,
) -> str:
    """One-line overlay/dashboard summary."""
    pb = get_personal_benchmark(civ, strategy, build_order_id)
    if pb.sample_count == 0:
        return "Your benchmark: play more games to unlock"
    parts = [f"You median feudal {_mmss(pb.median_feudal_sec)} ({pb.sample_count} games)"]
    if pb.target_feudal_sec:
        parts.append(f"target {_mmss(pb.target_feudal_sec)}")
        if pb.delta_feudal_sec is not None:
            sign = "+" if pb.delta_feudal_sec >= 0 else ""
            parts.append(f"({sign}{int(pb.delta_feudal_sec)}s)")
    return " · ".join(parts)


def list_personal_benchmark_rows(limit: int = 8) -> list[dict]:
    """Dashboard rows: one per build order with enough history."""
    from ..build_orders.manager import get_all_build_orders

    rows: list[dict] = []
    for bo in get_all_build_orders():
        pb = get_personal_benchmark(bo.civ, bo.strategy or "", bo.id, last_n=10)
        if pb.sample_count < 2:
            continue
        rows.append(
            {
                "civ": bo.civ,
                "build": bo.name,
                "strategy": bo.strategy or "",
                "median_feudal": _mmss(pb.median_feudal_sec),
                "target_feudal": _mmss(pb.target_feudal_sec),
                "status": pb.feudal_status(),
                "samples": pb.sample_count,
            }
        )
        if len(rows) >= limit:
            break
    return rows
