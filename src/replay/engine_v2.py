"""
TRINKER 3.2 - Replay extraction engine v2.
Multi-source pipeline: mgz -> scan -> header; picks best validated timings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..core.logger import logger
from .analyzer import _parse_filename_metadata, _scan_age_times
from .mgz_parser import parse_with_mgz
from .parser import parse_replay
from .validate import ValidatedTimings, validate_timings

_QUALITY_RANK = {"high": 3, "medium": 2, "low": 1, "rejected": 0}


@dataclass
class ExtractionCandidate:
    source: str
    validated: ValidatedTimings
    civ: str = "Unknown"
    player_name: str = ""
    eapm: Optional[float] = None
    villager_high: Optional[int] = None
    result: str = "practice"
    duration_sec: Optional[int] = None
    errors: list[str] = field(default_factory=list)


@dataclass
class EngineV2Result:
    """Best merged extraction from all sources."""

    feudal_time_sec: Optional[int] = None
    castle_time_sec: Optional[int] = None
    imperial_time_sec: Optional[int] = None
    duration_sec: Optional[int] = None
    civ: str = "Unknown"
    player_name: str = ""
    eapm: Optional[float] = None
    final_pop: Optional[int] = None
    result: str = "practice"
    data_quality: str = "rejected"
    parse_source: str = "none"
    confidence: str = "low"
    sources_used: list[str] = field(default_factory=list)
    validation_issues: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    def quality_score(self) -> int:
        return _QUALITY_RANK.get(self.data_quality, 0)


def _candidate_from_mgz(path: Path) -> Optional[ExtractionCandidate]:
    mgz = parse_with_mgz(path)
    if not mgz.success or not mgz.owner:
        return ExtractionCandidate(
            source="mgz",
            validated=ValidatedTimings(),
            errors=list(mgz.errors),
        )
    o = mgz.owner
    validated = validate_timings(
        feudal=o.feudal_time_sec,
        castle=o.castle_time_sec,
        imperial=o.imperial_time_sec,
        duration=mgz.duration_sec or None,
        source="mgz",
    )
    result = "practice"
    if o.winner is True:
        result = "win"
    elif o.winner is False:
        result = "loss"
    return ExtractionCandidate(
        source="mgz",
        validated=validated,
        civ=o.civ or "Unknown",
        player_name=o.name or "",
        eapm=o.eapm,
        villager_high=o.villager_high,
        result=result,
        duration_sec=mgz.duration_sec or None,
    )


def _candidate_from_scan(data: bytes) -> ExtractionCandidate:
    age_times = _scan_age_times(data)
    validated = validate_timings(
        feudal=age_times.get("feudal"),
        castle=age_times.get("castle"),
        imperial=age_times.get("imperial"),
        source="scan",
    )
    return ExtractionCandidate(source="scan", validated=validated)


def _pick_best(candidates: list[ExtractionCandidate]) -> ExtractionCandidate | None:
    usable = [c for c in candidates if c.validated.has_usable_timings()]
    if not usable:
        return candidates[0] if candidates else None

    def score(c: ExtractionCandidate) -> tuple:
        q = _QUALITY_RANK.get(c.validated.quality, 0)
        timing_count = sum(
            1
            for t in (
                c.validated.feudal_time_sec,
                c.validated.castle_time_sec,
                c.validated.imperial_time_sec,
            )
            if t
        )
        src_bonus = 1 if c.source == "mgz" else 0
        return (q, timing_count, src_bonus)

    return max(usable, key=score)


def _merge_timings(primary: ExtractionCandidate, others: list[ExtractionCandidate]) -> EngineV2Result:
    feudal = primary.validated.feudal_time_sec
    castle = primary.validated.castle_time_sec
    imperial = primary.validated.imperial_time_sec
    duration = primary.validated.duration_sec or primary.duration_sec
    issues = list(primary.validated.issues)
    sources = [primary.source]

    for c in others:
        if c.source == primary.source:
            continue
        v = c.validated
        if feudal is None and v.feudal_time_sec:
            feudal = v.feudal_time_sec
            sources.append(f"{c.source}:feudal")
        if castle is None and v.castle_time_sec:
            castle = v.castle_time_sec
            sources.append(f"{c.source}:castle")
        if imperial is None and v.imperial_time_sec:
            imperial = v.imperial_time_sec
            sources.append(f"{c.source}:imperial")
        if duration is None and v.duration_sec:
            duration = v.duration_sec

    quality = primary.validated.quality
    if quality == "rejected" and any(
        c.validated.has_usable_timings() for c in others if c.source != primary.source
    ):
        quality = "low"

    return EngineV2Result(
        feudal_time_sec=feudal,
        castle_time_sec=castle,
        imperial_time_sec=imperial,
        duration_sec=duration,
        civ=primary.civ,
        player_name=primary.player_name,
        eapm=primary.eapm,
        final_pop=primary.villager_high,
        result=primary.result,
        data_quality=quality if feudal or castle else "rejected",
        parse_source=primary.source,
        confidence=quality if quality != "rejected" else "low",
        sources_used=sources,
        validation_issues=issues,
    )


def extract_replay_v2(path: str | Path) -> EngineV2Result:
    """Run all extractors and return the best merged profile."""
    path = Path(path)
    candidates: list[ExtractionCandidate] = []
    errors: list[str] = []

    mgz_c = _candidate_from_mgz(path)
    if mgz_c:
        candidates.append(mgz_c)
        errors.extend(mgz_c.errors)

    try:
        data = path.read_bytes()
        candidates.append(_candidate_from_scan(data))
    except OSError as exc:
        errors.append(str(exc))

    info = parse_replay(path)
    if info.primary_civ() and info.primary_civ() != "Unknown":
        for c in candidates:
            if c.civ == "Unknown":
                c.civ = info.primary_civ()

    best = _pick_best(candidates)
    if not best:
        return EngineV2Result(parse_errors=errors, data_quality="rejected")

    result = _merge_timings(best, candidates)
    result.parse_errors = errors
    logger.info(
        "EngineV2 %s: quality=%s source=%s feudal=%s sources=%s",
        path.name,
        result.data_quality,
        result.parse_source,
        result.feudal_time_sec,
        result.sources_used,
    )
    return result
