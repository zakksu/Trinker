"""
Upgrade premium build orders + pro benchmarks in the TRINKER database.
Run: python scripts/upgrade_builds.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.build_orders.detailed_builds import PREMIUM_BUILDS
from src.build_orders.manager import import_and_save
from src.core.database import db_conn, init_db

BENCHMARKS = [
    # civ, strategy, pop, f_min, f_max, c_min, c_max, source, notes
    (
        "Britons",
        "Archer Rush",
        22,
        555,
        585,
        780,
        900,
        "Hera/community",
        "22-pop Britons archer — Feudal ~9:15-9:45, Castle ~13:00-15:00",
    ),
    (
        "Any",
        "Fast Castle",
        25,
        570,
        630,
        870,
        990,
        "aoe2.gg",
        "21-25 pop Fast Castle — Feudal ~9:30-10:30, Castle ~15:00-16:30",
    ),
]


def _upsert_benchmarks() -> int:
    added = 0
    with db_conn() as conn:
        for row in BENCHMARKS:
            civ, strat, pop, fmin, fmax, cmin, cmax, src, notes = row
            existing = conn.execute(
                """SELECT id FROM ideal_timings
                   WHERE civ=? AND strategy=? AND pop_count=?""",
                (civ, strat, pop),
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE ideal_timings SET
                       feudal_min_sec=?, feudal_max_sec=?,
                       castle_min_sec=?, castle_max_sec=?,
                       source=?, notes=?
                       WHERE id=?""",
                    (fmin, fmax, cmin, cmax, src, notes, existing["id"]),
                )
            else:
                conn.execute(
                    """INSERT INTO ideal_timings
                       (civ, strategy, pop_count, feudal_min_sec, feudal_max_sec,
                        castle_min_sec, castle_max_sec, source, notes)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (civ, strat, pop, fmin, fmax, cmin, cmax, src, notes),
                )
                added += 1
    return added


def main() -> int:
    init_db()
    print("TRINKER 2.0 — Upgrading premium build orders...\n")

    for factory in PREMIUM_BUILDS:
        bo = factory()
        result = import_and_save(bo)
        print(f"  OK: {result.name} ({result.civ}) — {len(result.steps)} steps")

    n = _upsert_benchmarks()
    print(f"\n  Benchmarks updated ({n} new rows).")
    print("\nDone! Restart TRINKER and pick your build from Start Here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
