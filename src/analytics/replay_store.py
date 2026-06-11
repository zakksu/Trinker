"""
TRINKER - Replay analysis persistence for dashboard and trends.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from ..core.database import db_conn, now_iso
from ..core.logger import logger
from ..replay.profile import ReplayProfile


@dataclass
class StoredReplayAnalysis:
    id: int
    session_id: Optional[int]
    replay_path: str
    civ: str
    map_name: str
    game_mode: str
    data_quality: str
    profile_json: str
    analyzed_at: str


def save_replay_analysis(
    profile: ReplayProfile,
    *,
    session_id: Optional[int] = None,
) -> int:
    """Upsert parsed replay profile for dashboard/history."""
    payload = json.dumps({
        "file_name": profile.file_name,
        "player_name": profile.player_name,
        "feudal_time_sec": profile.feudal_time_sec,
        "castle_time_sec": profile.castle_time_sec,
        "imperial_time_sec": profile.imperial_time_sec,
        "duration_sec": profile.duration_sec,
        "final_pop": profile.final_pop,
        "eapm": profile.eapm,
        "labels": profile.labels,
        "parse_source": profile.parse_source,
        "validation_issues": profile.validation_issues,
        "coach_context": profile.coach_context(),
    }, ensure_ascii=False)

    if session_id is not None:
        with db_conn() as conn:
            row = conn.execute(
                "SELECT id FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if not row:
                session_id = None

    with db_conn() as conn:
        conn.execute(
            """INSERT INTO replay_analyses
               (session_id, replay_path, civ, map_name, game_mode, data_quality,
                profile_json, analyzed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(replay_path) DO UPDATE SET
                 session_id=excluded.session_id,
                 civ=excluded.civ,
                 map_name=excluded.map_name,
                 game_mode=excluded.game_mode,
                 data_quality=excluded.data_quality,
                 profile_json=excluded.profile_json,
                 analyzed_at=excluded.analyzed_at""",
            (
                session_id,
                profile.replay_path,
                profile.civ,
                profile.map_name,
                profile.game_mode,
                profile.data_quality,
                payload,
                now_iso(),
            ),
        )
        row = conn.execute(
            "SELECT id FROM replay_analyses WHERE replay_path = ?",
            (profile.replay_path,),
        ).fetchone()
    rid = int(row["id"])
    logger.debug("Saved replay analysis id=%d for %s", rid, profile.file_name)
    return rid


def get_latest_replay_analysis() -> Optional[StoredReplayAnalysis]:
    with db_conn() as conn:
        row = conn.execute(
            """SELECT * FROM replay_analyses
               ORDER BY analyzed_at DESC LIMIT 1"""
        ).fetchone()
    return _row_to_analysis(row) if row else None


def get_replay_analyses(limit: int = 20) -> list[StoredReplayAnalysis]:
    with db_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM replay_analyses
               ORDER BY analyzed_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [_row_to_analysis(r) for r in rows]


def _row_to_analysis(row) -> StoredReplayAnalysis:
    return StoredReplayAnalysis(
        id=row["id"],
        session_id=row["session_id"],
        replay_path=row["replay_path"],
        civ=row["civ"] or "Unknown",
        map_name=row["map_name"] or "",
        game_mode=row["game_mode"] or "",
        data_quality=row["data_quality"] or "",
        profile_json=row["profile_json"] or "{}",
        analyzed_at=row["analyzed_at"] or "",
    )
