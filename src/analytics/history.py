"""
TRINKER - Historical Session Analysis
Compares practice history per civ/build and surfaces recurring patterns.
"""

from __future__ import annotations

from collections import Counter
from typing import Optional

from ..build_orders.manager import get_all_build_orders, get_build_order
from .session import get_sessions, get_summary_stats


def _mmss(sec: Optional[float]) -> str:
    if sec is None:
        return "—"
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def get_civ_history(civ: str, limit: int = 50) -> list[dict]:
    """Sessions for builds matching a civilization."""
    bos = {
        b.id: b for b in get_all_build_orders() if b.civ.lower() == civ.lower() or b.civ == "Any"
    }
    sessions = get_sessions(limit=limit)
    rows = []
    for s in sessions:
        if s.build_order_id not in bos:
            continue
        bo = bos[s.build_order_id]
        rows.append(
            {
                "date": s.date,
                "build": bo.name,
                "feudal": s.feudal_time_sec,
                "castle": s.castle_time_sec,
                "accuracy": s.accuracy_pct,
                "result": s.result,
                "notes": s.notes,
            }
        )
    return rows


_AUTO_NOTE_MARKERS = ("bulk import", "auto-filled", "[rejected]", "[low]")
_STOPWORDS = frozenset(
    {
        "import",
        "replay",
        "timing",
        "timings",
        "detected",
        "confidence",
        "bulk",
        "from",
        "auto",
        "filled",
        "practice",
        "unavailable",
        "parser",
        "pending",
        "unknown",
        "medium",
        "high",
        "rejected",
    }
)


def get_recurring_themes(limit: int = 100) -> list[tuple[str, int]]:
    """
    Extract recurring keywords from user-written session notes only.
    Ignores auto-import boilerplate.
    """
    sessions = get_sessions(limit=limit)
    keywords = Counter()
    themes = [
        "idle",
        "late feudal",
        "late castle",
        "forgot",
        "house",
        "boar",
        "scouts",
        "military",
        "gold",
        "wood",
        "food",
        "wall",
        "loom",
        "idle tc",
        "barracks",
        "behind",
        "slow",
        "lure",
        "feudal",
    ]
    for s in sessions:
        text = (s.notes or "").lower()
        if any(m in text for m in _AUTO_NOTE_MARKERS):
            continue
        if not text.strip():
            continue
        for t in themes:
            if t in text:
                keywords[t] += 1
        for word in text.split():
            w = word.strip(".,;:!?[]()")
            if len(w) > 4 and w.isalpha() and w not in _STOPWORDS:
                keywords[w] += 1

    return keywords.most_common(10)


def build_historical_summary(
    civ: str,
    build_order_id: Optional[int] = None,
) -> str:
    """
    Text block summarizing player history for LLM context.
    """
    stats = get_summary_stats(build_order_id)
    themes = get_recurring_themes()
    lines = [
        f"=== Historical Practice Data ({civ}) ===",
        f"Quality-filtered sessions: {stats.get('total_sessions', 0)}",
        f"Win rate: {stats.get('win_rate', 0):.1f}%",
        f"Avg Feudal: {_mmss(stats.get('avg_feudal_sec'))}",
        f"Best Feudal: {_mmss(stats.get('best_feudal_sec'))}",
        f"Avg Castle: {_mmss(stats.get('avg_castle_sec'))}",
        f"Avg Accuracy: {stats.get('avg_accuracy', 0) or 0:.1f}%",
        "(Stats exclude SP games and impossible timings.)",
    ]

    if themes:
        lines.append("Recurring themes in notes:")
        for theme, cnt in themes[:5]:
            lines.append(f"  - {theme} ({cnt}x)")

    if build_order_id:
        bo = get_build_order(build_order_id)
        if bo:
            recent = [s for s in get_sessions(build_order_id=build_order_id, limit=5)]
            if recent:
                lines.append(f"Last 5 runs on '{bo.name}':")
                for s in recent:
                    lines.append(
                        f"  {s.date}: feudal={_mmss(s.feudal_time_sec)} "
                        f"acc={s.accuracy_pct or 0:.0f}% {s.result}"
                    )

    return "\n".join(lines)


def compare_to_pro_benchmark(
    civ: str,
    strategy: str,
    feudal_sec: Optional[int],
    castle_sec: Optional[int],
) -> str:
    """Compare player timings to ideal_timings DB."""
    from ..build_orders.timings import (
        evaluate_castle_time,
        evaluate_feudal_time,
        get_benchmarks_for,
    )

    benchmarks = get_benchmarks_for(civ, strategy)
    if not benchmarks:
        return "No pro benchmark on file for this civ/strategy."

    b = benchmarks[0]
    lines = [f"Pro benchmark ({b.source}): {b.strategy}"]
    lines.append(f"  Feudal target: {b.feudal_range_str()}")
    lines.append(f"  Castle target: {b.castle_range_str()}")

    if feudal_sec:
        status, msg = evaluate_feudal_time(feudal_sec, b)
        lines.append(f"  Your Feudal: {msg} [{status}]")
    if castle_sec:
        status, msg = evaluate_castle_time(castle_sec, b)
        lines.append(f"  Your Castle: {msg} [{status}]")

    return "\n".join(lines)
