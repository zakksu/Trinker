"""
TRINKER 2.0 - Unified replay profile extraction.
Single pipeline: parse -> validate -> label -> session-ready insights.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..core.logger import logger
from .analyzer import _parse_filename_metadata, _scan_age_times
from .mgz_parser import parse_with_mgz
from .parser import parse_replay
from .validate import ValidatedTimings, validate_timings

# User's Steam ID folder under AoE2 DE (detect owner replay path)
_STEAM_RE = re.compile(r"(\d{17})")


@dataclass
class ReplayProfile:
    """Rich, validated replay profile for storage and AI coaching."""

    replay_path: str
    file_name: str = ""

    # Identity
    player_name: str = ""
    civ: str = "Unknown"
    map_name: str = "Unknown"
    owner_steam_hint: str = ""

    # Game context
    game_mode: str = "unknown"  # mp | sp | unknown
    is_ranked: bool = False
    recorded_at: str = ""
    player_count: int = 0
    result: str = "practice"  # win | loss | practice

    # Timings (validated only)
    feudal_time_sec: Optional[int] = None
    castle_time_sec: Optional[int] = None
    imperial_time_sec: Optional[int] = None
    duration_sec: Optional[int] = None
    final_pop: Optional[int] = None
    eapm: Optional[float] = None

    # Quality & parsing
    data_quality: str = "rejected"
    parse_source: str = "none"
    confidence: str = "low"
    parse_errors: list[str] = field(default_factory=list)
    validation_issues: list[str] = field(default_factory=list)

    # AI-ready sections
    labels: list[str] = field(default_factory=list)
    coach_sections: dict = field(default_factory=dict)

    def has_timings(self) -> bool:
        return bool(self.feudal_time_sec or self.castle_time_sec)

    def insights_json(self) -> str:
        return json.dumps(
            {
                "labels": self.labels,
                "sections": self.coach_sections,
                "parse_source": self.parse_source,
                "validation_issues": self.validation_issues,
            },
            ensure_ascii=False,
        )

    def coach_context(self) -> str:
        """Structured text block for LLM prompts."""
        lines = [
            f"=== Replay Profile: {self.file_name} ===",
            f"Mode: {self.game_mode.upper()} | Civ: {self.civ} | Map: {self.map_name}",
            f"Quality: {self.data_quality} ({self.parse_source}) | Result: {self.result}",
        ]
        if self.recorded_at:
            lines.append(f"Played: {self.recorded_at}")
        if self.feudal_time_sec:
            lines.append(f"Feudal: {self._mmss(self.feudal_time_sec)}")
        if self.castle_time_sec:
            lines.append(f"Castle: {self._mmss(self.castle_time_sec)}")
        if self.imperial_time_sec:
            lines.append(f"Imperial: {self._mmss(self.imperial_time_sec)}")
        if self.eapm:
            lines.append(f"eAPM: {self.eapm:.1f}")
        if self.final_pop:
            lines.append(f"Peak villagers: {self.final_pop}")
        if self.labels:
            lines.append("Labels: " + ", ".join(self.labels))
        if self.validation_issues:
            lines.append("Parse notes: " + "; ".join(self.validation_issues[:3]))
        return "\n".join(lines)

    @staticmethod
    def _mmss(sec: int) -> str:
        return f"{sec // 60}:{sec % 60:02d}"


def _detect_steam_from_path(path: Path) -> str:
    for part in path.parts:
        m = _STEAM_RE.fullmatch(part)
        if m:
            return m.group(1)
    return ""


def _apply_mgz(profile: ReplayProfile, path: Path) -> bool:
    mgz = parse_with_mgz(path)
    if not mgz.success or not mgz.owner:
        profile.parse_errors.extend(mgz.errors)
        return False

    o = mgz.owner
    profile.parse_source = "mgz"
    profile.civ = o.civ
    profile.player_name = o.name
    profile.eapm = o.eapm
    if o.winner is True:
        profile.result = "win"
    elif o.winner is False:
        profile.result = "loss"
    if o.villager_high:
        profile.final_pop = o.villager_high

    validated = validate_timings(
        feudal=o.feudal_time_sec,
        castle=o.castle_time_sec,
        imperial=o.imperial_time_sec,
        duration=mgz.duration_sec if mgz.duration_sec else None,
        source="mgz",
    )
    _apply_validated(profile, validated)
    return True


def _apply_scan(profile: ReplayProfile, data: bytes) -> None:
    """Strict binary scan — only accepts realistic age-up windows."""
    age_times = _scan_age_times(data)
    validated = validate_timings(
        feudal=age_times.get("feudal"),
        castle=age_times.get("castle"),
        imperial=age_times.get("imperial"),
        source="scan",
    )
    if validated.has_usable_timings():
        profile.parse_source = "scan"
        _apply_validated(profile, validated)


def _apply_validated(profile: ReplayProfile, v: ValidatedTimings) -> None:
    profile.feudal_time_sec = v.feudal_time_sec
    profile.castle_time_sec = v.castle_time_sec
    profile.imperial_time_sec = v.imperial_time_sec
    if v.duration_sec:
        profile.duration_sec = v.duration_sec
    profile.data_quality = v.quality
    profile.validation_issues = v.issues
    profile.confidence = v.quality if v.quality != "rejected" else "low"


def _build_labels(profile: ReplayProfile, info) -> None:
    labels: list[str] = []
    if profile.game_mode == "mp":
        labels.append("multiplayer")
    if profile.is_ranked:
        labels.append("ranked")
    if profile.civ != "Unknown":
        labels.append(profile.civ.lower())
    if profile.feudal_time_sec:
        if profile.feudal_time_sec <= 540:
            labels.append("fast-feudal")
        elif profile.feudal_time_sec >= 660:
            labels.append("slow-feudal")
    if profile.result == "win":
        labels.append("victory")
    elif profile.result == "loss":
        labels.append("defeat")
    if profile.data_quality == "rejected":
        labels.append("timings-unavailable")
    profile.labels = labels

    profile.coach_sections = {
        "identity": {
            "civ": profile.civ,
            "map": profile.map_name,
            "mode": profile.game_mode,
            "result": profile.result,
        },
        "timings": {
            "feudal_sec": profile.feudal_time_sec,
            "castle_sec": profile.castle_time_sec,
            "imperial_sec": profile.imperial_time_sec,
            "quality": profile.data_quality,
        },
        "economy": {
            "eapm": profile.eapm,
            "villager_high": profile.final_pop,
        },
    }


def extract_replay_profile(path: str | Path) -> ReplayProfile:
    """Full 2.0 extraction pipeline for one replay file."""
    path = Path(path)
    meta = _parse_filename_metadata(path)
    info = parse_replay(path)

    profile = ReplayProfile(
        replay_path=str(path.resolve()),
        file_name=path.name,
        map_name=info.map_name,
        recorded_at=meta["recorded_at"],
        is_ranked=meta["is_ranked"],
        player_count=len(info.players),
        owner_steam_hint=_detect_steam_from_path(path),
        parse_errors=list(info.parse_errors),
    )

    if meta["is_mp"] or path.name.startswith("MP Replay"):
        profile.game_mode = "mp"
    elif path.name.startswith("SP Replay"):
        profile.game_mode = "sp"

    civ = info.primary_civ()
    if civ and civ != "Unknown":
        profile.civ = civ

    # 1) Try mgz (best when game version supported)
    if not _apply_mgz(profile, path):
        # 2) Strict binary scan fallback
        try:
            data = path.read_bytes()
            _apply_scan(profile, data)
        except OSError as exc:
            profile.parse_errors.append(str(exc))

    # Never use file-size duration heuristic
    if profile.duration_sec is None and profile.parse_source == "none":
        profile.data_quality = "low"
        profile.confidence = "low"

    _build_labels(profile, info)

    logger.info(
        "Profile %s | civ=%s quality=%s feudal=%s source=%s",
        path.name,
        profile.civ,
        profile.data_quality,
        profile.feudal_time_sec,
        profile.parse_source,
    )
    return profile
