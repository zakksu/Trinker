"""
TRINKER 3.0 - Training drills (actionable next-step practice goals).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core.config import settings


@dataclass(frozen=True)
class Drill:
    id: str
    title: str
    instructions: str
    focus: str  # feudal | eco | military | general
    target_games: int = 3


_DRILLS: dict[str, Drill] = {
    "feudal_consistency": Drill(
        id="feudal_consistency",
        title="Feudal Consistency",
        instructions="Play 3 games with the same build. Hit Feudal within 30s of your target each time.",
        focus="feudal",
    ),
    "no_idle_tc": Drill(
        id="no_idle_tc",
        title="Zero Idle TC",
        instructions="Dark Age only: never let TC idle >2s. Queue vills or research immediately.",
        focus="eco",
    ),
    "scout_timing": Drill(
        id="scout_timing",
        title="Scout Production Window",
        instructions="Feudal → first 2 scouts within 60s. No extra houses before stable.",
        focus="military",
    ),
    "loom_discipline": Drill(
        id="loom_discipline",
        title="Loom Before Lure",
        instructions="Research loom before second boar lure. Repeat until automatic.",
        focus="eco",
    ),
}


def list_drills() -> list[Drill]:
    return list(_DRILLS.values())


def get_drill(drill_id: str) -> Optional[Drill]:
    return _DRILLS.get(drill_id)


def suggest_drill(
    *,
    feudal_sec: Optional[int] = None,
    overlay_alert: str = "",
    win_rate: float = 0.0,
) -> Drill:
    """Pick the best drill from stats and coach alerts."""
    alert = (overlay_alert or settings.overlay_coach_alert or "").lower()

    if feudal_sec and feudal_sec > 600:
        return _DRILLS["feudal_consistency"]
    if "loom" in alert or "boar" in alert:
        return _DRILLS["loom_discipline"]
    if "scout" in alert or "stable" in alert:
        return _DRILLS["scout_timing"]
    if "idle" in alert or "vill" in alert or "tc" in alert:
        return _DRILLS["no_idle_tc"]
    if win_rate < 45 and feudal_sec and feudal_sec > 540:
        return _DRILLS["feudal_consistency"]
    return _DRILLS["no_idle_tc"]


def pin_drill(drill: Drill) -> None:
    """Save drill as overlay alert for next session."""
    from ..core.telemetry import track
    from ..plugins.registry import emit
    from .drill_progress import reset_drill_progress

    settings.overlay_coach_alert = drill.instructions[:120]
    settings.active_drill_id = drill.id
    settings.save()
    reset_drill_progress(drill.id)
    track("drill_pinned", drill_id=drill.id, focus=drill.focus)
    emit("drill_pinned", drill=drill)
