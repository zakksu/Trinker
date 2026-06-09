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

from .parser import ReplayInfo, ReplayParser, parse_replay, CIV_MAP
from ..core.logger import logger

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
    confidence: str = "low"       # low | medium | high
    parse_errors: list[str] = field(default_factory=list)
    source_label: str = ""

    def has_timings(self) -> bool:
        return any([
            self.feudal_time_sec, self.castle_time_sec, self.imperial_time_sec,
        ])


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
    Looks for float game-time values near age-related string markers.
    """
    times: dict[str, int] = {}

    for marker, age_key in _AGE_RESEARCH_MARKERS.items():
        idx = 0
        while True:
            pos = data.find(marker, idx)
            if pos == -1:
                break
            # Search nearby bytes for plausible game-time floats (0–3600 sec)
            window_start = max(0, pos - 64)
            window_end = min(len(data), pos + 64)
            window = data[window_start:window_end]
            for off in range(0, len(window) - 4, 4):
                try:
                    val = struct.unpack_from("<f", window, off)[0]
                    if 30 <= val <= 3600:
                        sec = int(val)
                        if age_key not in times or sec < times[age_key]:
                            times[age_key] = sec
                except struct.error:
                    pass
            idx = pos + len(marker)

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
    """
    Full analysis pass on a replay file.
    Combines header parse + binary scans + filename metadata.
    """
    path = Path(path)
    info: ReplayInfo = parse_replay(path)
    meta = _parse_filename_metadata(path)

    analysis = ReplayAnalysis(
        replay_path=str(path),
        civ=info.primary_civ(),
        map_name=info.map_name,
        duration_sec=min(info.duration_sec, 7200),
        is_multiplayer=meta["is_mp"],
        is_ranked=meta["is_ranked"],
        recorded_at=meta["recorded_at"],
        parse_errors=list(info.parse_errors),
    )

    try:
        data = path.read_bytes()
    except OSError as exc:
        analysis.parse_errors.append(str(exc))
        return analysis

    age_times = _scan_age_times(data)
    if "feudal" in age_times:
        analysis.feudal_time_sec = age_times["feudal"]
        analysis.confidence = "medium"
    if "castle" in age_times:
        analysis.castle_time_sec = age_times["castle"]
        analysis.confidence = "medium"
    if "imperial" in age_times:
        analysis.imperial_time_sec = age_times["imperial"]

    pop = _scan_population_peaks(data)
    if pop:
        analysis.final_pop = pop

    # Tag pro/community replays from path hints
    path_l = str(path).lower()
    if any(k in path_l for k in ("hera", "viper", "lierrey", "tournament", "esports")):
        analysis.source_label = "Pro / tournament replay"
        analysis.confidence = "medium"

    logger.info(
        "Replay analysis: %s | feudal=%s castle=%s pop=%s conf=%s",
        path.name, analysis.feudal_time_sec, analysis.castle_time_sec,
        analysis.final_pop, analysis.confidence,
    )
    return analysis
