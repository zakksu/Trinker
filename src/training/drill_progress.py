"""
TRINKER - Drill completion tracking (kv_store backed).
"""

from __future__ import annotations

from typing import Optional

from ..core.config import settings
from ..core.kv_store import kv_get_json, kv_set_json
from ..core.telemetry import track
from .drill_engine import get_drill


def _progress_key(drill_id: str) -> str:
    return f"drill_progress:{drill_id}"


def get_drill_progress(drill_id: str) -> dict:
    drill = get_drill(drill_id)
    target = drill.target_games if drill else 3
    data = kv_get_json(_progress_key(drill_id), {})
    return {
        "games_done": int(data.get("games_done", 0)),
        "target_games": int(data.get("target_games", target)),
        "pinned_at": data.get("pinned_at", ""),
    }


def reset_drill_progress(drill_id: str) -> None:
    drill = get_drill(drill_id)
    if not drill:
        return
    from ..core.database import now_iso

    kv_set_json(
        _progress_key(drill_id),
        {"games_done": 0, "target_games": drill.target_games, "pinned_at": now_iso()},
    )


def record_drill_game(*, feudal_sec: Optional[int] = None) -> Optional[str]:
    """Increment progress for the active drill after a saved game. Returns completion message."""
    drill_id = (settings.active_drill_id or "").strip()
    if not drill_id:
        return None

    drill = get_drill(drill_id)
    if not drill:
        return None

    prog = get_drill_progress(drill_id)
    done = prog["games_done"] + 1
    target = prog["target_games"]
    kv_set_json(
        _progress_key(drill_id),
        {**prog, "games_done": done},
    )
    track("drill_game_recorded", drill_id=drill_id, games_done=done, feudal_sec=feudal_sec)

    if done >= target:
        settings.active_drill_id = ""
        settings.overlay_coach_alert = ""
        settings.save()
        track("drill_completed", drill_id=drill_id)
        return f"Drill complete: {drill.title} ({target}/{target} games)."

    remaining = target - done
    return f"Drill progress: {drill.title} ({done}/{target}) — {remaining} game(s) left."


def format_progress_label(drill_id: str) -> str:
    prog = get_drill_progress(drill_id)
    return f"{prog['games_done']}/{prog['target_games']} games"
