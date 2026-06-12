"""
TRINKER - Database Layer
SQLite schema setup, migrations, and helper query functions.
All tables are created here; no ORM is used — raw SQL keeps the dependency count low.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
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

-- ── Parsed replay snapshots (dashboard / trends) ────────────────────────────
CREATE TABLE IF NOT EXISTS replay_analyses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER REFERENCES sessions(id),
    replay_path     TEXT NOT NULL UNIQUE,
    civ             TEXT DEFAULT '',
    map_name        TEXT DEFAULT '',
    game_mode       TEXT DEFAULT '',
    data_quality    TEXT DEFAULT '',
    profile_json    TEXT NOT NULL DEFAULT '{}',
    analyzed_at     TEXT NOT NULL
);

-- ── Ask Coach chat history ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS coach_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_key  TEXT NOT NULL DEFAULT 'dashboard',
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

-- ── Imported online ladder matches (aoe2.gg / APIs) ─────────────────────────
CREATE TABLE IF NOT EXISTS online_matches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id    TEXT NOT NULL UNIQUE,
    steam_id    TEXT NOT NULL,
    played_at   TEXT NOT NULL,
    map_name    TEXT DEFAULT '',
    civ         TEXT DEFAULT '',
    result      TEXT DEFAULT 'unknown',
    rating      INTEGER,
    opponent    TEXT DEFAULT '',
    source      TEXT DEFAULT '',
    profile_url TEXT DEFAULT '',
    imported_at TEXT NOT NULL
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
    conn.execute("PRAGMA journal_mode=WAL;")  # write-ahead log for concurrency
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

V2_SESSION_COLUMNS = [
    ("civ", "TEXT DEFAULT ''"),
    ("map_name", "TEXT DEFAULT ''"),
    ("game_mode", "TEXT DEFAULT 'unknown'"),
    ("data_quality", "TEXT DEFAULT 'unknown'"),
    ("eapm", "REAL"),
    ("player_name", "TEXT DEFAULT ''"),
    ("insights_json", "TEXT DEFAULT '{}'"),
]


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """Add 2.0 session columns if missing (non-destructive)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
    added = 0
    for col, typedef in V2_SESSION_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE sessions ADD COLUMN {col} {typedef}")
            added += 1
    if added:
        logger.info("DB migrated to v2: added %d session column(s).", added)


def init_db() -> None:
    """Create all tables and seed reference data if first run."""
    logger.info("Initializing database at %s", DB_PATH)
    with db_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        _migrate_v2(conn)
        _ensure_replay_analyses(conn)
        _ensure_coach_messages(conn)
        _ensure_online_matches(conn)

    _seed_ideal_timings()
    try:
        from ..build_orders.benchmark_import import import_pro_benchmarks

        import_pro_benchmarks()
    except Exception as exc:
        logger.debug("Pro benchmark import skipped: %s", exc)
    logger.info("Database ready.")


def _ensure_replay_analyses(conn: sqlite3.Connection) -> None:
    """Create replay_analyses on existing DBs that predate the table."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='replay_analyses'"
    ).fetchone()
    if row:
        return
    conn.executescript("""
        CREATE TABLE replay_analyses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER REFERENCES sessions(id),
            replay_path     TEXT NOT NULL UNIQUE,
            civ             TEXT DEFAULT '',
            map_name        TEXT DEFAULT '',
            game_mode       TEXT DEFAULT '',
            data_quality    TEXT DEFAULT '',
            profile_json    TEXT NOT NULL DEFAULT '{}',
            analyzed_at     TEXT NOT NULL
        );
    """)
    logger.info("DB migrated: added replay_analyses table.")


def _ensure_coach_messages(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='coach_messages'"
    ).fetchone()
    if row:
        return
    conn.executescript("""
        CREATE TABLE coach_messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_key  TEXT NOT NULL DEFAULT 'dashboard',
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );
    """)
    logger.info("DB migrated: added coach_messages table.")


def _ensure_online_matches(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='online_matches'"
    ).fetchone()
    if row:
        return
    conn.executescript("""
        CREATE TABLE online_matches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id    TEXT NOT NULL UNIQUE,
            steam_id    TEXT NOT NULL,
            played_at   TEXT NOT NULL,
            map_name    TEXT DEFAULT '',
            civ         TEXT DEFAULT '',
            result      TEXT DEFAULT 'unknown',
            rating      INTEGER,
            opponent    TEXT DEFAULT '',
            source      TEXT DEFAULT '',
            profile_url TEXT DEFAULT '',
            imported_at TEXT NOT NULL
        );
    """)
    logger.info("DB migrated: added online_matches table.")


def _seed_ideal_timings() -> None:
    """Insert pro-level benchmark timings if table is empty."""
    with db_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM ideal_timings").fetchone()[0]
        if count > 0:
            return

        benchmarks = [
            # (civ, strategy, pop, feudal_min, feudal_max, castle_min, castle_max, imp_min, imp_max, source, notes)
            (
                "Any",
                "Fast Feudal (18 pop)",
                18,
                480,
                540,
                None,
                None,
                None,
                None,
                "Community",
                "Standard 18-pop feudal",
            ),
            (
                "Any",
                "Fast Castle (21 pop)",
                21,
                540,
                600,
                840,
                960,
                None,
                None,
                "aoe2.gg",
                "21-pop fast castle",
            ),
            (
                "Spanish",
                "Scout Rush (18 pop)",
                18,
                510,
                555,
                930,
                1005,
                None,
                None,
                "aoe2.gg",
                "Hera / Viper benchmarks",
            ),
            (
                "Spanish",
                "Fast Castle (21 pop)",
                21,
                555,
                615,
                870,
                990,
                None,
                None,
                "aoe2.gg",
                "",
            ),
            (
                "Franks",
                "Scout Rush (20 pop)",
                20,
                510,
                570,
                960,
                1020,
                None,
                None,
                "Community",
                "Franks knight rush transition",
            ),
            (
                "Mongols",
                "Drush Fast Castle",
                22,
                570,
                630,
                900,
                990,
                None,
                None,
                "aoe2.gg",
                "Liereyy-style drush FC",
            ),
            (
                "Britons",
                "MAA + Archers",
                21,
                495,
                555,
                None,
                None,
                None,
                None,
                "Community",
                "MAA into archers",
            ),
            (
                "Any",
                "Boom (23 pop)",
                23,
                570,
                660,
                1020,
                1140,
                None,
                None,
                "Community",
                "3-TC boom target",
            ),
            (
                "Any",
                "Fast Imperial",
                25,
                600,
                660,
                1020,
                1080,
                1500,
                1680,
                "aoe2.gg",
                "Pro-level fast imp",
            ),
            (
                "Vikings",
                "Double Bit Axe Rush",
                20,
                510,
                570,
                None,
                None,
                None,
                None,
                "Community",
                "Early wood eco",
            ),
            (
                "Aztecs",
                "Eagle Warrior Rush",
                20,
                510,
                555,
                None,
                None,
                None,
                None,
                "aoe2.gg",
                "Mbl / Hera-style",
            ),
            (
                "Chinese",
                "Fast Castle (37 pop)",
                37,
                630,
                720,
                900,
                1020,
                None,
                None,
                "aoe2.gg",
                "Chinese opening no scouts",
            ),
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
