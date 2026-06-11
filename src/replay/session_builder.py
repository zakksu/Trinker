"""
TRINKER 2.0 - Build practice sessions from validated replay profiles.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..analytics.session import Milestone, Session
from ..build_orders.manager import get_all_build_orders, get_build_order
from ..build_orders.timings import calculate_accuracy_score, get_benchmarks_for
from .profile import ReplayProfile


def _date_from_profile(path: Path, profile: ReplayProfile) -> str:
    if profile.recorded_at:
        m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", profile.recorded_at)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).date().isoformat()
    except OSError:
        return datetime.now(timezone.utc).date().isoformat()


def match_build_for_civ(civ: str, preferred_bo_id: Optional[int] = None):
    """Pick the best library build for a civ — never assign unrelated 'Any' builds."""
    bos = get_all_build_orders()
    if not bos:
        return None

    if preferred_bo_id:
        bo = get_build_order(preferred_bo_id)
        if bo and (bo.civ.lower() == civ.lower() or bo.civ == "Any"):
            return bo

    civ_matches = [b for b in bos if b.civ.lower() == civ.lower()]
    if civ_matches:
        for keyword in ("Archer", "Scout", "Castle", "Rush"):
            for b in civ_matches:
                if (
                    keyword.lower() in b.name.lower()
                    or keyword.lower() in (b.strategy or "").lower()
                ):
                    return b
        return civ_matches[0]

    # No dedicated BO — attach generic macro track; true civ stored on session
    for b in bos:
        if b.civ == "Any" and "Feudal" in (b.name + b.strategy):
            return b
    any_b = next((b for b in bos if b.civ == "Any"), None)
    return any_b or bos[0]


def profile_to_session(
    profile: ReplayProfile,
    path: Path,
    *,
    preferred_bo_id: Optional[int] = None,
) -> Optional[Session]:
    """Convert a ReplayProfile into a DB-ready Session."""
    bo = match_build_for_civ(profile.civ, preferred_bo_id)
    if not bo:
        return None

    milestones: list[Milestone] = []
    if profile.feudal_time_sec:
        milestones.append(Milestone(label="Clicked Feudal", game_time_sec=profile.feudal_time_sec))
    if profile.castle_time_sec:
        milestones.append(Milestone(label="Clicked Castle", game_time_sec=profile.castle_time_sec))
    if profile.imperial_time_sec:
        milestones.append(
            Milestone(label="Clicked Imperial", game_time_sec=profile.imperial_time_sec)
        )

    feudal_delta = castle_delta = None
    benchmarks = get_benchmarks_for(bo.civ, bo.strategy)
    if benchmarks:
        b = benchmarks[0]
        if profile.feudal_time_sec and b.feudal_max_sec:
            feudal_delta = max(0, profile.feudal_time_sec - b.feudal_max_sec)
        if profile.castle_time_sec and b.castle_max_sec:
            castle_delta = max(0, profile.castle_time_sec - b.castle_max_sec)

    accuracy = None
    if profile.has_timings():
        accuracy = calculate_accuracy_score(0, bo.step_count, feudal_delta, castle_delta)

    timing_note = []
    if profile.feudal_time_sec:
        timing_note.append(
            f"Feudal {profile.feudal_time_sec // 60}:{profile.feudal_time_sec % 60:02d}"
        )
    if profile.castle_time_sec:
        timing_note.append(
            f"Castle {profile.castle_time_sec // 60}:{profile.castle_time_sec % 60:02d}"
        )
    timing_str = (
        ", ".join(timing_note) if timing_note else "timings unavailable (DE v101 parser pending)"
    )

    return Session(
        build_order_id=bo.id,
        date=_date_from_profile(path, profile),
        duration_sec=profile.duration_sec or 0,
        feudal_time_sec=profile.feudal_time_sec,
        castle_time_sec=profile.castle_time_sec,
        imperial_time_sec=profile.imperial_time_sec,
        final_pop=profile.final_pop,
        result=profile.result,
        accuracy_pct=accuracy,
        notes=f"[{profile.data_quality}] {profile.civ} {profile.game_mode}: {timing_str}",
        replay_path=profile.replay_path,
        milestones=milestones,
        civ=profile.civ,
        map_name=profile.map_name,
        game_mode=profile.game_mode,
        data_quality=profile.data_quality,
        eapm=profile.eapm,
        player_name=profile.player_name,
        insights_json=profile.insights_json(),
    )
