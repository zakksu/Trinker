"""
TRINKER - Replay business logic (import, analysis storage).
Thin service layer — UI should call this instead of raw replay modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..analytics.replay_store import save_replay_analysis
from ..analytics.session import save_session
from ..core.config import settings
from ..core.logger import logger
from ..replay.parser import get_latest_replay
from ..replay.profile import ReplayProfile, extract_replay_profile
from ..replay.session_builder import profile_to_session


@dataclass
class ImportResult:
    imported: bool = False
    replay_path: str = ""
    civ: str = ""
    message: str = ""
    session_id: Optional[int] = None
    build_order_id: Optional[int] = None


def detect_replay_folders() -> list[Path]:
    """Return configured + default AoE2 replay search roots that exist."""
    from ..core.config import get_replay_search_dirs
    return get_replay_search_dirs()


def import_replay_profile(
    path: str | Path,
    *,
    preferred_bo_id: Optional[int] = None,
    save: bool = True,
) -> ImportResult:
    """Parse replay, optionally save session + analysis snapshot."""
    result = ImportResult()
    path = Path(path)
    if not path.exists():
        result.message = "Replay file not found."
        return result

    profile = extract_replay_profile(path)
    result.replay_path = profile.replay_path
    result.civ = profile.civ

    if not save:
        save_replay_analysis(profile)
        result.imported = True
        result.message = f"Analyzed {profile.file_name}"
        return result

    bo_id = preferred_bo_id or settings.last_practice_bo_id
    session = profile_to_session(profile, path, preferred_bo_id=bo_id)
    if not session:
        save_replay_analysis(profile)
        result.message = f"No build match for {profile.civ}"
        return result

    save_session(session)
    result.session_id = session.id
    result.build_order_id = session.build_order_id
    save_replay_analysis(profile, session_id=session.id)

    civ_label = _display_civ(profile, session.build_order_id)
    result.imported = True
    result.civ = civ_label
    result.message = f"Game saved — {civ_label} ({profile.data_quality})"
    logger.info("ReplayService: %s", result.message)
    return result


def import_latest_replay(preferred_bo_id: Optional[int] = None) -> ImportResult:
    latest = get_latest_replay()
    if not latest:
        return ImportResult(message="No replays found.")
    return import_replay_profile(latest, preferred_bo_id=preferred_bo_id)


def _display_civ(profile: ReplayProfile, build_order_id: Optional[int]) -> str:
    if profile.civ and profile.civ != "Unknown":
        return profile.civ
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
