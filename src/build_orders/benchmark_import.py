"""
TRINKER - Pro benchmark JSON import for ideal_timings table.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..core.database import db_conn
from ..core.logger import logger

_BENCHMARKS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "pro_benchmarks.json"


def import_pro_benchmarks(force: bool = False) -> int:
    """
    Load benchmarks from data/pro_benchmarks.json.
    Skips if table already has rows unless force=True.
    Returns count inserted.
    """
    if not _BENCHMARKS_FILE.exists():
        logger.warning("Missing pro benchmarks file: %s", _BENCHMARKS_FILE)
        return 0

    payload = json.loads(_BENCHMARKS_FILE.read_text(encoding="utf-8"))
    entries = payload.get("benchmarks", [])

    with db_conn() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM ideal_timings").fetchone()[0]
        if existing > 0 and not force:
            # Merge: insert only (civ, strategy) pairs not present
            return _merge_new(conn, entries)

        if force and existing > 0:
            conn.execute("DELETE FROM ideal_timings WHERE source LIKE 'Pro DB%'")

        inserted = 0
        for e in entries:
            conn.execute(
                """INSERT INTO ideal_timings
                   (civ, strategy, pop_count, feudal_min_sec, feudal_max_sec,
                    castle_min_sec, castle_max_sec, imperial_min_sec, imperial_max_sec,
                    source, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    e.get("civ", "Any"),
                    e.get("strategy", ""),
                    e.get("pop_count"),
                    e.get("feudal_min_sec"),
                    e.get("feudal_max_sec"),
                    e.get("castle_min_sec"),
                    e.get("castle_max_sec"),
                    e.get("imperial_min_sec"),
                    e.get("imperial_max_sec"),
                    e.get("source", "Pro DB"),
                    e.get("notes", ""),
                ),
            )
            inserted += 1
        logger.info("Imported %d pro benchmarks.", inserted)
        return inserted


def _merge_new(conn, entries: list[dict]) -> int:
    inserted = 0
    for e in entries:
        civ = e.get("civ", "Any")
        strategy = e.get("strategy", "")
        row = conn.execute(
            "SELECT id FROM ideal_timings WHERE civ=? AND strategy=? LIMIT 1",
            (civ, strategy),
        ).fetchone()
        if row:
            continue
        conn.execute(
            """INSERT INTO ideal_timings
               (civ, strategy, pop_count, feudal_min_sec, feudal_max_sec,
                castle_min_sec, castle_max_sec, imperial_min_sec, imperial_max_sec,
                source, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                civ,
                strategy,
                e.get("pop_count"),
                e.get("feudal_min_sec"),
                e.get("feudal_max_sec"),
                e.get("castle_min_sec"),
                e.get("castle_max_sec"),
                e.get("imperial_min_sec"),
                e.get("imperial_max_sec"),
                e.get("source", "Pro DB"),
                e.get("notes", ""),
            ),
        )
        inserted += 1
    if inserted:
        logger.info("Merged %d new pro benchmarks.", inserted)
    return inserted
