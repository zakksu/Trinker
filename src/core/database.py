"""
TRINKER - Database Layer
SQLite schema setup, migrations, and helper query functions.
All tables are created here; no ORM is used — raw SQL keeps the dependency count low.
"""

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from .config import DB_PATH
from .logger import logger


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- ── Build Orders ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS build_orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT,                       -- e.g. buildorderguide.com slug
    name        TEXT    NOT NULL,
    civ         TEXT    NOT NULL DEFAULT 'Any',
    strategy    TEXT,                       -- e.g. "Fast Castle", "Scout Rush"
    difficulty  TEXT    DEFAULT 'Medium',   -- Easy / Medium / Hard
    tags        TEXT    DEFAULT '[]',       -- JSON array of strings
    author      TEXT,
    source_url  TEXT,
    steps_json  TEXT    NOT NULL DEFAULT '[]',  -- JSON array of step objects
    notes       TEXT,
    is_favorite INTEGER DEFAULT 0,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

-- ── Practice Sessions ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    build_order_id  INTEGER REFERENCES build_orders(id),
    date            TEXT    NOT NULL,
    duration_sec    INTEGER DEFAULT 0,
    feudal_time_sec INTEGER,
    castle_time_sec INTEGER,
    imperial_time_sec INTEGER,
    final_pop       INTEGER,
    food_at_feudal  INTEGER,
    wood_at_feudal  INTEGER,
    gold_at_feudal  INTEGER,
    stone_at_feudal INTEGER,
    result          TEXT    DEFAULT 'practice',  -- win / loss / draw / practice
    accuracy_pct    REAL,
    notes           TEXT,
    mistakes_json   TEXT    DEFAULT '[]',
    replay_path     TEXT,
    created_at      TEXT    NOT NULL
);

-- ── Milestones within a session ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS milestones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    label       TEXT    NOT NULL,   -- e.g. "Clicked Feudal", "Hit 100 pop"
    game_time_sec INTEGER,
    wall_time   TEXT,
    value       TEXT                -- optional numeric or string value
);

-- ── Ideal Timings Database ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ideal_timings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    civ             TEXT    NOT NULL,
    strategy        TEXT    NOT NULL,
    pop_count       INTEGER,
    feudal_min_sec  INTEGER,        -- lower bound (seconds)
    feudal_max_sec  INTEGER,        -- upper bound (seconds)
    castle_min_sec  INTEGER,
    castle_max_sec  INTEGER,
    imperial_min_sec INTEGER,
    imperial_max_sec INTEGER,
    source          TEXT,
    notes           TEXT
);

-- ── App-wide key-value settings store (supplement to JSON file) ─────────────
CREATE TABLE IF NOT EXISTS kv_store (
    key     TEXT PRIMARY KEY,
    value   TEXT
);
"""

# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """
    Return a configured SQLite connection.
    Row factory is set so results can be accessed by column name.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")   # write-ahead log for concurrency
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def db_conn() -> Generator[sqlite3.Connection, None, None]:
    """Context manager that auto-commits or rolls back."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("DB transaction rolled back: %s", exc, exc_info=True)
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema initialization & seeding
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables and seed reference data if first run."""
    logger.info("Initializing database at %s", DB_PATH)
    with db_conn() as conn:
        conn.executescript(SCHEMA_SQL)

    _seed_ideal_timings()
    logger.info("Database ready.")


def _seed_ideal_timings() -> None:
    """Insert pro-level benchmark timings if table is empty."""
    with db_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM ideal_timings").fetchone()[0]
        if count > 0:
            return

        benchmarks = [
            # (civ, strategy, pop, feudal_min, feudal_max, castle_min, castle_max, imp_min, imp_max, source, notes)
            ("Any",     "Fast Feudal (18 pop)",   18, 480, 540,  None, None, None, None, "Community",  "Standard 18-pop feudal"),
            ("Any",     "Fast Castle (21 pop)",   21, 540, 600,  840,  960,  None, None, "aoe2.gg",    "21-pop fast castle"),
            ("Spanish", "Scout Rush (18 pop)",    18, 510, 555,  930, 1005, None, None, "aoe2.gg",    "Hera / Viper benchmarks"),
            ("Spanish", "Fast Castle (21 pop)",   21, 555, 615,  870,  990, None, None, "aoe2.gg",    ""),
            ("Franks",  "Scout Rush (20 pop)",    20, 510, 570,  960, 1020, None, None, "Community",  "Franks knight rush transition"),
            ("Mongols", "Drush Fast Castle",      22, 570, 630,  900,  990, None, None, "aoe2.gg",    "Liereyy-style drush FC"),
            ("Britons", "MAA + Archers",          21, 495, 555,  None, None, None, None, "Community", "MAA into archers"),
            ("Any",     "Boom (23 pop)",          23, 570, 660, 1020, 1140, None, None, "Community",  "3-TC boom target"),
            ("Any",     "Fast Imperial",          25, 600, 660, 1020, 1080, 1500, 1680, "aoe2.gg",   "Pro-level fast imp"),
            ("Vikings", "Double Bit Axe Rush",    20, 510, 570,  None, None, None, None, "Community", "Early wood eco"),
            ("Aztecs",  "Eagle Warrior Rush",     20, 510, 555,  None, None, None, None, "aoe2.gg",    "Mbl / Hera-style"),
            ("Chinese", "Fast Castle (37 pop)",   37, 630, 720,  900, 1020, None, None, "aoe2.gg",    "Chinese opening no scouts"),
        ]

        conn.executemany(
            """INSERT INTO ideal_timings
               (civ, strategy, pop_count, feudal_min_sec, feudal_max_sec,
                castle_min_sec, castle_max_sec, imperial_min_sec, imperial_max_sec,
                source, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            benchmarks,
        )
        logger.info("Seeded %d ideal timing benchmarks.", len(benchmarks))


# ---------------------------------------------------------------------------
# Utility helpers used by other modules
# ---------------------------------------------------------------------------

def now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.utcnow().isoformat()


def json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def json_loads(s: str | None):
    if not s:
        return []
    try:
        return json.loads(s)
    except Exception:
        return []
