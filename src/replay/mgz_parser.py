"""
TRINKER - Rich replay parsing via mgz (aoc-mgz / AoE2Insights).
Falls back gracefully if mgz is unavailable or parse fails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..core.logger import logger

_MGZ_OK = False
try:
    from mgz.summary import Summary

    _MGZ_OK = True
except ImportError:
    Summary = None  # type: ignore

CIV_NAMES = {
    1: "Britons",
    2: "Franks",
    3: "Goths",
    4: "Teutons",
    5: "Japanese",
    6: "Chinese",
    7: "Byzantines",
    8: "Persians",
    9: "Saracens",
    10: "Turks",
    11: "Vikings",
    12: "Mongols",
    13: "Celts",
    14: "Spanish",
    15: "Aztecs",
    16: "Mayans",
    17: "Huns",
    18: "Koreans",
    19: "Italians",
    20: "Hindustanis",
    21: "Incas",
    22: "Magyars",
    23: "Slavs",
    24: "Portuguese",
    25: "Ethiopians",
    26: "Malians",
    27: "Berbers",
    28: "Khmer",
    29: "Malay",
    30: "Burmese",
    31: "Vietnamese",
    32: "Bulgarians",
    33: "Tatars",
    34: "Cumans",
    35: "Lithuanians",
    38: "Poles",
    39: "Bohemians",
    40: "Dravidians",
    41: "Gurjaras",
    42: "Romans",
    43: "Bengalis",
    44: "Sicilians",
}


@dataclass
class MgzPlayerStats:
    name: str = ""
    civ: str = "Unknown"
    number: int = 0
    eapm: Optional[float] = None
    feudal_time_sec: Optional[int] = None
    castle_time_sec: Optional[int] = None
    imperial_time_sec: Optional[int] = None
    villager_high: Optional[int] = None
    food_collected: Optional[int] = None
    wood_collected: Optional[int] = None
    gold_collected: Optional[int] = None
    military_score: Optional[int] = None
    economy_score: Optional[int] = None
    winner: Optional[bool] = None


@dataclass
class MgzParseResult:
    """Structured data extracted from mgz Summary."""

    success: bool = False
    parser: str = "none"
    duration_sec: int = 0
    map_name: str = "Unknown"
    owner_number: int = 1
    players: list[MgzPlayerStats] = field(default_factory=list)
    owner: Optional[MgzPlayerStats] = None
    errors: list[str] = field(default_factory=list)

    def timeline_lines(self) -> list[str]:
        """Human-readable timeline for LLM coaching."""
        lines: list[str] = []
        if not self.owner:
            return lines
        p = self.owner
        lines.append(f"Player: {p.name} ({p.civ})")
        if p.feudal_time_sec:
            lines.append(f"  Feudal Age: {_mmss(p.feudal_time_sec)}")
        if p.castle_time_sec:
            lines.append(f"  Castle Age: {_mmss(p.castle_time_sec)}")
        if p.imperial_time_sec:
            lines.append(f"  Imperial Age: {_mmss(p.imperial_time_sec)}")
        if p.villager_high:
            lines.append(f"  Peak villagers: {p.villager_high}")
        if p.eapm:
            lines.append(f"  eAPM: {p.eapm:.1f}")
        if p.food_collected:
            lines.append(f"  Food collected: {p.food_collected}")
        if p.wood_collected:
            lines.append(f"  Wood collected: {p.wood_collected}")
        if p.gold_collected:
            lines.append(f"  Gold collected: {p.gold_collected}")
        return lines


def _mmss(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def _civ_name(civ_id) -> str:
    try:
        return CIV_NAMES.get(int(civ_id), f"Unknown({civ_id})")
    except (TypeError, ValueError):
        return "Unknown"


def _ms_to_sec(val) -> Optional[int]:
    if val is None or val <= 0:
        return None
    # mgz may return ms or seconds depending on parser path
    if val > 10000:
        return int(val / 1000)
    return int(val)


def parse_with_mgz(path: str | Path) -> MgzParseResult:
    """Parse replay with mgz Summary; returns empty result on failure."""
    result = MgzParseResult()
    if not _MGZ_OK:
        result.errors.append("mgz not installed")
        return result

    path = Path(path)
    name = path.name
    if "v101." in name or " v101 " in name:
        result.errors.append("de_v101: mgz may lack age timings — scan fallback active")

    try:
        with path.open("rb") as handle:
            summary = Summary(handle, fallback=True)
            result.parser = type(summary).__name__

            try:
                result.duration_sec = int(summary.get_duration() / 1000)
            except Exception:
                pass

            try:
                owner_num = summary.get_owner()
                result.owner_number = owner_num or 1
            except Exception:
                owner_num = 1

            players_raw = summary.get_players()
            for pr in players_raw:
                ach = pr.get("achievements") or {}
                tech = ach.get("technology") or {}
                eco = ach.get("economy") or {}
                mil = ach.get("military") or {}
                soc = ach.get("society") or {}

                ps = MgzPlayerStats(
                    name=pr.get("name", ""),
                    civ=_civ_name(pr.get("civilization")),
                    number=pr.get("number", 0),
                    eapm=pr.get("eapm"),
                    feudal_time_sec=_ms_to_sec(tech.get("feudal_time")),
                    castle_time_sec=_ms_to_sec(tech.get("castle_time")),
                    imperial_time_sec=_ms_to_sec(tech.get("imperial_time")),
                    villager_high=soc.get("villager_high"),
                    food_collected=eco.get("food_collected"),
                    wood_collected=eco.get("wood_collected"),
                    gold_collected=eco.get("gold_collected"),
                    military_score=mil.get("score"),
                    economy_score=eco.get("score"),
                    winner=pr.get("winner"),
                )
                result.players.append(ps)
                if ps.number == owner_num or (result.owner is None and pr.get("human")):
                    if ps.number == owner_num:
                        result.owner = ps

            if result.owner is None and result.players:
                result.owner = result.players[0]

            try:
                objects = summary.get_objects()
                if objects:
                    result.map_name = "parsed"
            except Exception:
                pass

            result.success = result.owner is not None
            if result.success:
                result.errors.append("mgz:high")
                logger.info(
                    "mgz parse OK: %s feudal=%s castle=%s eapm=%s",
                    path.name,
                    result.owner.feudal_time_sec if result.owner else None,
                    result.owner.castle_time_sec if result.owner else None,
                    result.owner.eapm if result.owner else None,
                )
    except Exception as exc:
        result.errors.append(f"mgz: {exc}")
        logger.warning("mgz parse failed for %s: %s", path, exc)

    return result
