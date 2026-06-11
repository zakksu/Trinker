"""
TRINKER - Replay Parser
Partial parsing of .aoe2record files for basic game metadata and timing extraction.

The .aoe2record format is proprietary and not fully documented. This module
extracts what's reliably readable from the header:
  - Game start timestamp
  - Player civilization
  - Map type and size
  - Duration estimate

Full event-level parsing (age-ups, key actions) is flagged as a TODO:
it requires the community-maintained mgx2/aoe2record spec which evolves
with each game patch.

Reference: https://github.com/happyleavesaoc/aoc-mgx-format
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..core.logger import logger

# ---------------------------------------------------------------------------
# Known civilization IDs in AoE2 DE (as of patch 78087)
# Incomplete — covers the most common civs
# ---------------------------------------------------------------------------

CIV_MAP: dict[int, str] = {
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
    20: "Indians",
    21: "Incas",
    22: "Magyars",
    23: "Slavs",
    24: "Portuguese",
    25: "Ethiopian",
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
    36: "Teutons",
    38: "Poles",
    39: "Bohemians",
    40: "Dravidians",
    41: "Gurjaras",
    42: "Romans",
    43: "Bengalis",
    44: "Sicilians",
}

MAP_NAMES: dict[int, str] = {
    9: "Arabia",
    10: "Archipelago",
    11: "Baltic",
    12: "Black Forest",
    13: "Coastal",
    14: "Continental",
    19: "Gold Rush",
    29: "Highland",
    33: "Islands",
    72: "Arena",
    74: "Ghost Lake",
    75: "Migration",
    78: "Nomad",
    121: "Four Lakes",
    140: "Hideout",
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ReplayInfo:
    """
    Data extracted from a .aoe2record file.

    Attributes:
        file_path:       Source file path.
        game_version:    Decoded version string (e.g. "VER 9.4").
        duration_sec:    Estimated game duration in seconds.
        map_name:        Map name string.
        players:         List of player info dicts.
        parse_errors:    Non-fatal warnings encountered during parsing.
    """

    file_path: str
    game_version: str = ""
    duration_sec: int = 0
    map_name: str = "Unknown"
    players: list[dict] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    def primary_player(self) -> Optional[dict]:
        """Return the first human player entry, or None."""
        return next((p for p in self.players if p.get("human")), None)

    def primary_civ(self) -> str:
        """Convenience: civ name of the primary player."""
        p = self.primary_player()
        return p.get("civ", "Unknown") if p else "Unknown"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class ReplayParser:
    """
    Stateful parser for .aoe2record binary files.
    Only reads the file header — stops before the body of game events.
    """

    # Byte offsets are approximate and may shift between game versions
    _HEADER_MAGIC = b"VER "
    _MIN_FILE_SIZE = 4096  # sanity check

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data: bytes = b""

    def parse(self) -> ReplayInfo:
        """
        Parse the replay file and return a ReplayInfo.
        Never raises — errors are captured in ReplayInfo.parse_errors.
        """
        info = ReplayInfo(file_path=str(self.path))

        if not self.path.exists():
            info.parse_errors.append(f"File not found: {self.path}")
            return info

        try:
            self._data = self.path.read_bytes()
        except PermissionError:
            info.parse_errors.append(f"Permission denied: {self.path}")
            return info

        if len(self._data) < self._MIN_FILE_SIZE:
            info.parse_errors.append("File too small — may not be a valid .aoe2record")
            return info

        try:
            self._parse_version(info)
            self._parse_duration(info)
            self._parse_map(info)
            self._parse_players(info)
        except Exception as exc:
            msg = f"Parse error: {exc}"
            info.parse_errors.append(msg)
            logger.warning("Replay parse non-fatal: %s | file=%s", exc, self.path)

        logger.info(
            "Parsed replay: %s | %s | %ds | %d players | errors=%d",
            self.path.name,
            info.game_version,
            info.duration_sec,
            len(info.players),
            len(info.parse_errors),
        )
        return info

    def _parse_version(self, info: ReplayInfo) -> None:
        """Extract game version string from header magic bytes."""
        idx = self._data.find(self._HEADER_MAGIC)
        if idx == -1:
            info.parse_errors.append("VER magic not found — format unknown")
            return
        end = self._data.find(b"\x00", idx)
        if end == -1:
            end = idx + 12
        info.game_version = self._data[idx:end].decode("ascii", errors="replace").strip()

    def _parse_duration(self, info: ReplayInfo) -> None:
        """Duration requires mgz/event parse — do not guess from file size."""
        info.duration_sec = 0

    def _parse_map(self, info: ReplayInfo) -> None:
        """Try to read the map type ID from a known offset region."""
        # Map ID typically appears as a 4-byte little-endian int around offset 0x1C4
        # This is version-dependent; treat as best-effort
        for offset in (0x1C4, 0x1D0, 0x1E0):
            if offset + 4 <= len(self._data):
                map_id = struct.unpack_from("<I", self._data, offset)[0]
                if map_id in MAP_NAMES:
                    info.map_name = MAP_NAMES[map_id]
                    return
        info.parse_errors.append("Map ID not identified (best-effort parsing)")

    def _parse_players(self, info: ReplayInfo) -> None:
        """
        Extract player civ IDs from the player info block.
        The block typically starts around offset 0x20C and repeats per player.
        """
        # Scan for civilization IDs by looking for known civ ID values
        # in the expected player data region (first 8192 bytes)
        scan_region = self._data[:8192]
        found_civs: list[int] = []

        # Civ IDs appear as 4-byte little-endian ints in the range 1–50
        for i in range(0, len(scan_region) - 4, 4):
            val = struct.unpack_from("<I", scan_region, i)[0]
            if val in CIV_MAP and val not in found_civs:
                found_civs.append(val)
                if len(found_civs) >= 8:
                    break

        for idx, civ_id in enumerate(found_civs):
            info.players.append(
                {
                    "index": idx,
                    "civ_id": civ_id,
                    "civ": CIV_MAP.get(civ_id, f"Unknown({civ_id})"),
                    "human": idx == 0,  # assume first detected player is the human
                }
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_replay(path: str | Path) -> ReplayInfo:
    """
    Parse a .aoe2record replay file.

    Args:
        path: Path to the .aoe2record file.

    Returns:
        ReplayInfo with whatever data was extractable.
        Check parse_errors for any warnings.
    """
    return ReplayParser(path).parse()


def format_replay_duration(sec: int) -> str:
    """
    Human-readable duration for UI display.
    File-size estimates are unreliable for multiplayer replays — cap sanity.
    """
    if sec <= 0:
        return "unknown"
    if sec > 7200:
        return "long game (watch in AoE2)"
    m, s = divmod(sec, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}h {m}m"
    return f"{m}:{s:02d}"


def get_latest_replay() -> Optional[Path]:
    """Return the newest .aoe2record file, or None."""
    replays = find_replay_files()
    return replays[0] if replays else None


def find_replay_files() -> list[Path]:
    """
    Search AoE2 DE replay directories for .aoe2record files.
    Returns all found files, sorted newest first.
    """
    from ..core.config import get_replay_search_dirs

    found: list[Path] = []
    for base in get_replay_search_dirs():
        found.extend(base.rglob("*.aoe2record"))

    # Sort by modification time descending (newest first)
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if found:
        logger.debug("Found %d replay files (newest: %s)", len(found), found[0].name)
    return found
