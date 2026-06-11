"""
TRINKER - Replay Data Analyzer
Extracts actionable timing data from .aoe2record files for auto-fill.
Best-effort: scans binary for age-up markers and embedded metadata.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# AoE2 DE research IDs (approximate) — Feudal=101, Castle=102, Imperial=103 in some builds
_AGE_RESEARCH_MARKERS = {
    b"Feudal Age": "feudal",
    b"Castle Age": "castle",
    b"Imperial Age": "imperial",
}


@dataclass
class ReplayAnalysis:
    """Extracted metrics from a replay for session auto-fill."""

    replay_path: str
    civ: str = "Unknown"
    map_name: str = "Unknown"
    duration_sec: int = 0
    feudal_time_sec: Optional[int] = None
    castle_time_sec: Optional[int] = None
    imperial_time_sec: Optional[int] = None
    final_pop: Optional[int] = None
    is_multiplayer: bool = False
    is_ranked: bool = False
    recorded_at: str = ""
    confidence: str = "low"  # low | medium | high
    parse_errors: list[str] = field(default_factory=list)
    source_label: str = ""

    def has_timings(self) -> bool:
        return any(
            [
                self.feudal_time_sec,
                self.castle_time_sec,
                self.imperial_time_sec,
            ]
        )


def _parse_filename_metadata(path: Path) -> dict:
    """Extract date/time and MP info from standard DE replay filenames."""
    meta = {"recorded_at": "", "is_mp": False, "is_ranked": False}
    name = path.name
    if name.startswith("MP Replay"):
        meta["is_mp"] = True
    if "RM_" in name or "ranked" in name.lower():
        meta["is_ranked"] = True
    m = re.search(r"@(\d{4}\.\d{2}\.\d{2}\s+\d{6})", name)
    if m:
        meta["recorded_at"] = m.group(1)
    return meta


def _scan_age_times(data: bytes) -> dict[str, int]:
    """
    Scan replay binary for age-up timing hints.
    Uses strict realistic windows — rejects garbage like 0:23 feudal.
    """
    from .validate import (
        CASTLE_MAX,
        CASTLE_MIN,
        FEUDAL_MAX,
        FEUDAL_MIN,
        IMPERIAL_MAX,
        IMPERIAL_MIN,
    )

    ranges = {
        "feudal": (FEUDAL_MIN, FEUDAL_MAX),
        "castle": (CASTLE_MIN, CASTLE_MAX),
        "imperial": (IMPERIAL_MIN, IMPERIAL_MAX),
    }
    candidates: dict[str, list[int]] = {k: [] for k in ranges}

    for marker, age_key in _AGE_RESEARCH_MARKERS.items():
        idx = 0
        while True:
            pos = data.find(marker, idx)
            if pos == -1:
                break
            window_start = max(0, pos - 128)
            window_end = min(len(data), pos + 128)
            window = data[window_start:window_end]
            lo, hi = ranges[age_key]
            for off in range(0, len(window) - 4, 4):
                try:
                    val = struct.unpack_from("<f", window, off)[0]
                    if lo <= val <= hi:
                        candidates[age_key].append(int(val))
                except struct.error:
                    pass
            idx = pos + len(marker)

    times: dict[str, int] = {}
    for key, vals in candidates.items():
        if vals:
            # Prefer median candidate — more stable than min
            vals.sort()
            times[key] = vals[len(vals) // 2]
    return times


def _scan_population_peaks(data: bytes) -> Optional[int]:
    """Find plausible final population values in replay tail."""
    tail = data[-65536:] if len(data) > 65536 else data
    candidates: list[int] = []
    for off in range(0, len(tail) - 4, 4):
        val = struct.unpack_from("<I", tail, off)[0]
        if 25 <= val <= 200:
            candidates.append(val)
    return max(candidates) if candidates else None


def analyze_replay(path: str | Path) -> ReplayAnalysis:
    """Full analysis via 2.0 profile pipeline (backward-compatible ReplayAnalysis)."""
    from .profile import extract_replay_profile

    profile = extract_replay_profile(path)
    analysis = ReplayAnalysis(
        replay_path=profile.replay_path,
        civ=profile.civ,
        map_name=profile.map_name,
        duration_sec=profile.duration_sec or 0,
        feudal_time_sec=profile.feudal_time_sec,
        castle_time_sec=profile.castle_time_sec,
        imperial_time_sec=profile.imperial_time_sec,
        final_pop=profile.final_pop,
        is_multiplayer=profile.game_mode == "mp",
        is_ranked=profile.is_ranked,
        recorded_at=profile.recorded_at,
        confidence=profile.confidence,
        parse_errors=profile.parse_errors + profile.validation_issues,
        source_label=profile.parse_source,
    )
    return analysis
