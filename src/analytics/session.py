"""
TRINKER - Practice Session Recording
All logic for creating, updating, and querying practice sessions in the DB.
A "session" is one run-through of a build order (timed practice or casual).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..core.database import db_conn, json_dumps, json_loads, now_iso
from ..core.logger import logger

# ---------------------------------------------------------------------------
# Dataclass mirrors of the DB rows
# ---------------------------------------------------------------------------


@dataclass
class Milestone:
    """A user-logged event within a session (e.g. 'Clicked Feudal')."""

    label: str
    game_time_sec: Optional[int] = None
    wall_time: str = field(default_factory=now_iso)
    value: Optional[str] = None
    id: Optional[int] = None
    session_id: Optional[int] = None


@dataclass
class Session:
    """
    One practice session.
    Call save_session() to persist; all fields are optional except build_order_id.
    """

    build_order_id: int
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    duration_sec: int = 0
    feudal_time_sec: Optional[int] = None
    castle_time_sec: Optional[int] = None
    imperial_time_sec: Optional[int] = None
    final_pop: Optional[int] = None
    food_at_feudal: Optional[int] = None
    wood_at_feudal: Optional[int] = None
    gold_at_feudal: Optional[int] = None
    stone_at_feudal: Optional[int] = None
    result: str = "practice"  # win / loss / draw / practice
    accuracy_pct: Optional[float] = None
    notes: str = ""
    mistakes_json: list[str] = field(default_factory=list)
    replay_path: Optional[str] = None
    milestones: list[Milestone] = field(default_factory=list)
    id: Optional[int] = None
    created_at: str = field(default_factory=now_iso)
    # 2.0 replay profile fields
    civ: str = ""
    map_name: str = ""
    game_mode: str = "unknown"
    data_quality: str = "unknown"
    eapm: Optional[float] = None
    player_name: str = ""
    insights_json: str = "{}"


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------


def save_session(session: Session) -> Session:
    """
    Persist a Session (and its Milestones) to the database.
    Sets session.id on insert.
    """
    mistakes_json = json_dumps(session.mistakes_json)

    with db_conn() as conn:
        if session.id is None:
            cur = conn.execute(
                """INSERT INTO sessions
                   (build_order_id, date, duration_sec, feudal_time_sec, castle_time_sec,
                    imperial_time_sec, final_pop, food_at_feudal, wood_at_feudal,
                    gold_at_feudal, stone_at_feudal, result, accuracy_pct, notes,
                    mistakes_json, replay_path, created_at,
                    civ, map_name, game_mode, data_quality, eapm, player_name, insights_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    session.build_order_id,
                    session.date,
                    session.duration_sec,
                    session.feudal_time_sec,
                    session.castle_time_sec,
                    session.imperial_time_sec,
                    session.final_pop,
                    session.food_at_feudal,
                    session.wood_at_feudal,
                    session.gold_at_feudal,
                    session.stone_at_feudal,
                    session.result,
                    session.accuracy_pct,
                    session.notes,
                    mistakes_json,
                    session.replay_path,
                    session.created_at,
                    session.civ,
                    session.map_name,
                    session.game_mode,
                    session.data_quality,
                    session.eapm,
                    session.player_name,
                    session.insights_json,
                ),
            )
            session.id = cur.lastrowid
            logger.info("Session %d saved (BO id=%d)", session.id, session.build_order_id)

            # Insert milestones
            for ms in session.milestones:
                ms.session_id = session.id
                _insert_milestone(conn, ms)
        else:
            conn.execute(
                """UPDATE sessions SET
                   duration_sec=?, feudal_time_sec=?, castle_time_sec=?,
                   imperial_time_sec=?, final_pop=?, food_at_feudal=?,
                   wood_at_feudal=?, gold_at_feudal=?, stone_at_feudal=?,
                   result=?, accuracy_pct=?, notes=?, mistakes_json=?, replay_path=?
                   WHERE id=?""",
                (
                    session.duration_sec,
                    session.feudal_time_sec,
                    session.castle_time_sec,
                    session.imperial_time_sec,
                    session.final_pop,
                    session.food_at_feudal,
                    session.wood_at_feudal,
                    session.gold_at_feudal,
                    session.stone_at_feudal,
                    session.result,
                    session.accuracy_pct,
                    session.notes,
                    mistakes_json,
                    session.replay_path,
                    session.id,
                ),
            )
            logger.info("Session %d updated", session.id)
    return session


def add_milestone(session_id: int, ms: Milestone) -> Milestone:
    """Append a single milestone to an existing session."""
    ms.session_id = session_id
    with db_conn() as conn:
        _insert_milestone(conn, ms)
    return ms


def _insert_milestone(conn, ms: Milestone) -> None:
    cur = conn.execute(
        """INSERT INTO milestones (session_id, label, game_time_sec, wall_time, value)
           VALUES (?,?,?,?,?)""",
        (ms.session_id, ms.label, ms.game_time_sec, ms.wall_time, ms.value),
    )
    ms.id = cur.lastrowid


def delete_session(session_id: int) -> bool:
    """Delete a session and its milestones (cascade). Returns True on success."""
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------


def get_sessions(
    *,
    build_order_id: Optional[int] = None,
    result: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 200,
) -> list[Session]:
    """
    Query sessions with optional filters.

    Args:
        build_order_id: Filter to a specific build order.
        result:         Filter by result ('win', 'loss', 'draw', 'practice').
        date_from:      ISO date string lower bound (inclusive).
        date_to:        ISO date string upper bound (inclusive).
        limit:          Max rows to return.

    Returns:
        List of Session objects, newest first.
    """
    conditions = []
    params: list = []

    if build_order_id is not None:
        conditions.append("build_order_id = ?")
        params.append(build_order_id)
    if result:
        conditions.append("result = ?")
        params.append(result)
    if date_from:
        conditions.append("date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM sessions {where} ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with db_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_session(dict(r)) for r in rows]


def get_session(session_id: int) -> Optional[Session]:
    """Fetch one session with its milestones."""
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        session = _row_to_session(dict(row))
        ms_rows = conn.execute(
            "SELECT * FROM milestones WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
    session.milestones = [
        Milestone(
            id=m["id"],
            session_id=m["session_id"],
            label=m["label"],
            game_time_sec=m["game_time_sec"],
            wall_time=m["wall_time"] or "",
            value=m["value"],
        )
        for m in ms_rows
    ]
    return session


# ---------------------------------------------------------------------------
# Aggregated analytics queries
# ---------------------------------------------------------------------------

# Only average sessions with plausible data (2.0 quality gate)
_QUALITY_SQL = """
    AND (feudal_time_sec IS NULL OR feudal_time_sec >= 420)
    AND (castle_time_sec IS NULL OR castle_time_sec >= 660)
    AND (duration_sec IS NULL OR duration_sec = 0 OR (duration_sec >= 300 AND duration_sec <= 7200))
    AND (game_mode IS NULL OR game_mode != 'sp')
    AND (replay_path IS NULL OR replay_path NOT LIKE '%SP Replay%')
"""


def purge_low_quality_sessions() -> int:
    """Remove polluted bulk-import and impossible-timing sessions."""
    with db_conn() as conn:
        cur = conn.execute(
            """DELETE FROM sessions WHERE
               notes LIKE '%Bulk import%'
               OR (feudal_time_sec IS NOT NULL AND feudal_time_sec < 420)
               OR (castle_time_sec IS NOT NULL AND castle_time_sec < 660)
               OR duration_sec = 7200
               OR replay_path LIKE '%SP Replay%'
               OR game_mode = 'sp'"""
        )
        deleted = cur.rowcount
    logger.info("Purged %d low-quality sessions.", deleted)
    return deleted


def get_summary_stats(build_order_id: Optional[int] = None) -> dict:
    """
    Return aggregated stats for the analytics dashboard.

    Returns dict with:
      total_sessions, wins, losses, draws,
      avg_feudal_sec, avg_castle_sec,
      best_feudal_sec, best_castle_sec,
      avg_accuracy, practice_days
    """
    if build_order_id:
        where = f"WHERE build_order_id = ? {_QUALITY_SQL}"
        params: tuple = (build_order_id,)
    else:
        where = f"WHERE 1=1 {_QUALITY_SQL}"
        params = ()

    with db_conn() as conn:
        row = conn.execute(
            f"""SELECT
                COUNT(*)                              AS total_sessions,
                SUM(CASE WHEN result='win'  THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN result='loss' THEN 1 ELSE 0 END) AS losses,
                SUM(CASE WHEN result='draw' THEN 1 ELSE 0 END) AS draws,
                AVG(feudal_time_sec)                  AS avg_feudal_sec,
                AVG(castle_time_sec)                  AS avg_castle_sec,
                MIN(feudal_time_sec)                  AS best_feudal_sec,
                MIN(castle_time_sec)                  AS best_castle_sec,
                AVG(accuracy_pct)                     AS avg_accuracy,
                COUNT(DISTINCT date)                  AS practice_days
            FROM sessions {where}""",
            params,
        ).fetchone()

    d = dict(row) if row else {}
    d["win_rate"] = (
        round(d["wins"] / d["total_sessions"] * 100, 1) if d.get("total_sessions") else 0.0
    )
    return d


def get_accuracy_trend(build_order_id: Optional[int] = None, last_n: int = 30) -> list[dict]:
    """
    Return last N accuracy scores for trend charting.
    Each dict has: date, accuracy_pct, session_id.
    """
    bo_filter = "AND build_order_id = ?" if build_order_id else ""
    params: tuple = (build_order_id, last_n) if build_order_id else (last_n,)
    with db_conn() as conn:
        rows = conn.execute(
            f"""SELECT id AS session_id, date, accuracy_pct
                FROM sessions
                WHERE accuracy_pct IS NOT NULL {_QUALITY_SQL} {bo_filter}
                ORDER BY created_at DESC LIMIT ?""",
            params,
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def get_feudal_time_trend(build_order_id: Optional[int] = None, last_n: int = 30) -> list[dict]:
    """
    Return last N feudal times for trend charting.
    Each dict has: date, feudal_time_sec, session_id.
    """
    bo_filter = "AND build_order_id = ?" if build_order_id else ""
    params: tuple = (build_order_id, last_n) if build_order_id else (last_n,)
    with db_conn() as conn:
        rows = conn.execute(
            f"""SELECT id AS session_id, date, feudal_time_sec
                FROM sessions
                WHERE feudal_time_sec IS NOT NULL {_QUALITY_SQL} {bo_filter}
                ORDER BY created_at DESC LIMIT ?""",
            params,
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def get_most_practiced_builds(limit: int = 10) -> list[dict]:
    """Return top-N builds by number of practice sessions."""
    with db_conn() as conn:
        rows = conn.execute(
            """SELECT bo.name, bo.civ, bo.id AS build_order_id,
                      COUNT(s.id) AS session_count,
                      AVG(s.accuracy_pct) AS avg_accuracy,
                      MIN(s.feudal_time_sec) AS best_feudal
               FROM sessions s
               JOIN build_orders bo ON bo.id = s.build_order_id
               GROUP BY s.build_order_id
               ORDER BY session_count DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_activity_heatmap(year: Optional[int] = None) -> dict[str, int]:
    """
    Return a dict mapping ISO date strings to session counts for the heatmap.
    Defaults to current year.
    """
    from datetime import date

    yr = year or date.today().year
    with db_conn() as conn:
        rows = conn.execute(
            """SELECT date, COUNT(*) AS cnt FROM sessions
               WHERE date LIKE ? GROUP BY date""",
            (f"{yr}-%",),
        ).fetchall()
    return {r["date"]: r["cnt"] for r in rows}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_session(row: dict) -> Session:
    return Session(
        id=row["id"],
        build_order_id=row["build_order_id"],
        date=row.get("date", ""),
        duration_sec=row.get("duration_sec", 0) or 0,
        feudal_time_sec=row.get("feudal_time_sec"),
        castle_time_sec=row.get("castle_time_sec"),
        imperial_time_sec=row.get("imperial_time_sec"),
        final_pop=row.get("final_pop"),
        food_at_feudal=row.get("food_at_feudal"),
        wood_at_feudal=row.get("wood_at_feudal"),
        gold_at_feudal=row.get("gold_at_feudal"),
        stone_at_feudal=row.get("stone_at_feudal"),
        result=row.get("result", "practice"),
        accuracy_pct=row.get("accuracy_pct"),
        notes=row.get("notes", ""),
        mistakes_json=json_loads(row.get("mistakes_json", "[]")),
        replay_path=row.get("replay_path"),
        created_at=row.get("created_at", ""),
        civ=row.get("civ") or "",
        map_name=row.get("map_name") or "",
        game_mode=row.get("game_mode") or "unknown",
        data_quality=row.get("data_quality") or "unknown",
        eapm=row.get("eapm"),
        player_name=row.get("player_name") or "",
        insights_json=row.get("insights_json") or "{}",
    )
