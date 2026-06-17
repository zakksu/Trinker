"""
TRINKER - Automatic replay/session detection after games.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..analytics.replay_store import save_replay_analysis
from ..analytics.session import save_session
from ..core.config import settings
from ..core.database import db_conn
from ..core.logger import logger
from ..replay.profile import extract_replay_profile
from ..replay.session_builder import profile_to_session


@dataclass
class AutoSessionResult:
    imported: bool = False
    replay_name: str = ""
    civ: str = ""
    message: str = ""
    replay_path: str = ""
    build_order_id: Optional[int] = None


def _already_imported(path: Path) -> bool:
    resolved = str(path.resolve())
    with db_conn() as conn:
        row = conn.execute("SELECT id FROM sessions WHERE replay_path = ?", (resolved,)).fetchone()
    return row is not None


def _display_civ(profile_civ: str, build_order_id: Optional[int]) -> str:
    if profile_civ and profile_civ != "Unknown":
        return profile_civ
    if build_order_id:
        from ..build_orders.manager import get_build_order

        bo = get_build_order(build_order_id)
        if bo and bo.civ != "Any":
            return bo.civ
    if settings.last_practice_bo_id:
        from ..build_orders.manager import get_build_order

        bo = get_build_order(settings.last_practice_bo_id)
        if bo:
            return bo.civ
    return "Unknown"


def try_auto_import_latest_replay(
    *,
    preferred_bo_id: Optional[int] = None,
) -> AutoSessionResult:
    """
    Silently import the newest replay as a session if it hasn't been seen.
    No popups — for background auto-detection.
    Also scans for any unimported replays on first poll after startup.
    """
    result = AutoSessionResult()
    if not settings.auto_detect_sessions:
        return result

    from ..replay.parser import find_replay_files, get_latest_replay

    latest = get_latest_replay()
    if not latest:
        return result

    try:
        mtime = latest.stat().st_mtime
    except OSError:
        return result

    # Startup catch-up: import any replay newer than last_seen we missed
    if settings.last_seen_replay_mtime <= 0:
        for path in sorted(find_replay_files(), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
            if _already_imported(path):
                continue
            profile = extract_replay_profile(path)
            bo_id = preferred_bo_id or settings.last_practice_bo_id
            session = profile_to_session(profile, path, preferred_bo_id=bo_id)
            if session:
                save_session(session)
                save_replay_analysis(profile, session_id=session.id)
            else:
                save_replay_analysis(profile)
            try:
                seen_mtime = path.stat().st_mtime
            except OSError:
                continue
            settings.last_seen_replay_mtime = seen_mtime
            settings.last_seen_replay_path = str(path.resolve())
            settings.save()
            civ = _display_civ(profile.civ, session.build_order_id if session else bo_id)
            result.imported = True
            result.replay_name = path.name
            result.civ = civ
            result.replay_path = str(path.resolve())
            result.build_order_id = session.build_order_id if session else bo_id
            result.message = (
                f"Game saved — {civ} ({profile.data_quality})"
                if session
                else f"Game detected — {civ} ({profile.data_quality})"
            )
            logger.info("Auto-session catch-up: %s", result.message)
            return result

    if mtime <= settings.last_seen_replay_mtime:
        return result

    profile = extract_replay_profile(latest)

    if _already_imported(latest):
        save_replay_analysis(profile)
        settings.last_seen_replay_mtime = mtime
        settings.last_seen_replay_path = str(latest)
        settings.save()
        return result

    bo_id = preferred_bo_id or settings.last_practice_bo_id
    session = profile_to_session(profile, latest, preferred_bo_id=bo_id)
    if not session:
        save_replay_analysis(profile)
        settings.last_seen_replay_mtime = mtime
        settings.last_seen_replay_path = str(latest.resolve())
        settings.save()
        civ = _display_civ(profile.civ, bo_id)
        result.imported = True
        result.replay_name = latest.name
        result.civ = civ
        result.replay_path = str(latest.resolve())
        result.build_order_id = bo_id
        result.message = f"Game detected — {civ} ({profile.data_quality})"
        return result

    save_session(session)
    save_replay_analysis(profile, session_id=session.id)
    settings.last_seen_replay_mtime = mtime
    settings.last_seen_replay_path = str(latest.resolve())
    settings.save()

    civ = _display_civ(profile.civ, session.build_order_id)
    result.imported = True
    result.replay_name = latest.name
    result.civ = civ
    result.replay_path = str(latest.resolve())
    result.build_order_id = session.build_order_id
    result.message = f"Game saved — {civ} ({profile.data_quality})"
    logger.info("Auto-session: %s", result.message)
    return result
