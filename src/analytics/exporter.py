"""
TRINKER - Data Exporter
Export practice sessions and build orders to CSV and JSON for external analysis.
"""

import csv
import json
from datetime import date
from pathlib import Path
from typing import Optional

from ..build_orders.manager import get_all_build_orders
from ..core.config import EXPORT_DIR
from ..core.logger import logger
from .session import get_sessions


def _auto_path(prefix: str, ext: str) -> Path:
    """Generate an export path with today's date embedded."""
    return EXPORT_DIR / f"{prefix}_{date.today().isoformat()}.{ext}"


# ---------------------------------------------------------------------------
# Session exports
# ---------------------------------------------------------------------------


def export_sessions_csv(
    path: Optional[str] = None,
    build_order_id: Optional[int] = None,
) -> str:
    """
    Write all (or filtered) practice sessions to a CSV file.

    Args:
        path:           Override output path. Auto-generated if None.
        build_order_id: Only export sessions for this build order.

    Returns:
        Absolute path of the written file as a string.
    """
    sessions = get_sessions(build_order_id=build_order_id, limit=10_000)
    out = Path(path) if path else _auto_path("sessions", "csv")

    fieldnames = [
        "id",
        "build_order_id",
        "date",
        "duration_sec",
        "result",
        "feudal_time_sec",
        "castle_time_sec",
        "imperial_time_sec",
        "final_pop",
        "food_at_feudal",
        "wood_at_feudal",
        "gold_at_feudal",
        "stone_at_feudal",
        "accuracy_pct",
        "notes",
        "replay_path",
        "created_at",
    ]

    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for s in sessions:
            writer.writerow(
                {
                    "id": s.id,
                    "build_order_id": s.build_order_id,
                    "date": s.date,
                    "duration_sec": s.duration_sec,
                    "result": s.result,
                    "feudal_time_sec": s.feudal_time_sec,
                    "castle_time_sec": s.castle_time_sec,
                    "imperial_time_sec": s.imperial_time_sec,
                    "final_pop": s.final_pop,
                    "food_at_feudal": s.food_at_feudal,
                    "wood_at_feudal": s.wood_at_feudal,
                    "gold_at_feudal": s.gold_at_feudal,
                    "stone_at_feudal": s.stone_at_feudal,
                    "accuracy_pct": s.accuracy_pct,
                    "notes": s.notes,
                    "replay_path": s.replay_path,
                    "created_at": s.created_at,
                }
            )

    logger.info("Exported %d sessions → %s", len(sessions), out)
    return str(out)


def export_sessions_json(
    path: Optional[str] = None,
    build_order_id: Optional[int] = None,
) -> str:
    """Serialize all sessions to JSON. Returns path written."""
    sessions = get_sessions(build_order_id=build_order_id, limit=10_000)
    out = Path(path) if path else _auto_path("sessions", "json")
    data = []
    for s in sessions:
        d = s.__dict__.copy()
        d.pop("milestones", None)
        data.append(d)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Exported %d sessions (JSON) → %s", len(sessions), out)
    return str(out)


# ---------------------------------------------------------------------------
# Build order exports
# ---------------------------------------------------------------------------


def export_build_orders_json(path: Optional[str] = None) -> str:
    """Export all build orders to a JSON file. Returns path written."""
    bos = get_all_build_orders()
    out = Path(path) if path else _auto_path("build_orders", "json")
    out.write_text(
        json.dumps([bo.to_dict() for bo in bos], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Exported %d build orders (JSON) → %s", len(bos), out)
    return str(out)


def export_build_orders_csv(path: Optional[str] = None) -> str:
    """Export build order metadata (no steps) to CSV. Returns path written."""
    bos = get_all_build_orders()
    out = Path(path) if path else _auto_path("build_orders", "csv")
    fieldnames = [
        "id",
        "name",
        "civ",
        "strategy",
        "difficulty",
        "author",
        "source_url",
        "step_count",
        "is_favorite",
        "created_at",
    ]
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for bo in bos:
            w.writerow(
                {
                    "id": bo.id,
                    "name": bo.name,
                    "civ": bo.civ,
                    "strategy": bo.strategy,
                    "difficulty": bo.difficulty,
                    "author": bo.author,
                    "source_url": bo.source_url,
                    "step_count": bo.step_count,
                    "is_favorite": bo.is_favorite,
                    "created_at": bo.created_at,
                }
            )
    logger.info("Exported %d build orders (CSV) → %s", len(bos), out)
    return str(out)
