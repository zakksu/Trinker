"""Generate minimal synthetic .aoe2record bytes for parser regression tests."""

from __future__ import annotations

import struct
from pathlib import Path


def _embed_age_timing(data: bytearray, marker: bytes, seconds: float) -> None:
    """Place marker + nearby float timing within the analyzer window."""
    data.extend(b"\x00" * 32)
    data.extend(marker)
    data.extend(struct.pack("<f", seconds))


def build_synthetic_replay(
    *,
    feudal_sec: float = 480.0,
    castle_sec: float | None = 960.0,
    include_version: bool = True,
) -> bytes:
    data = bytearray()
    if include_version:
        data.extend(b"VER 9.4.0\x00")
    data.extend(b"\x00" * 128)
    _embed_age_timing(data, b"Feudal Age", feudal_sec)
    if castle_sec is not None:
        _embed_age_timing(data, b"Castle Age", castle_sec)
    # Plausible population int in tail for pop scanner
    data.extend(b"\x00" * 512)
    data.extend(struct.pack("<I", 75))
    return bytes(data)


def write_synthetic_mp_replay(
    path: Path,
    *,
    feudal_sec: float = 480.0,
    castle_sec: float | None = 960.0,
) -> Path:
    """Write a synthetic MP replay file with a standard DE filename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = "MP Replay v101.103.47452.0 @2026.06.08 213123 (1).aoe2record"
    target = path if path.is_dir() else path
    if target.is_dir():
        target = target / name
    target.write_bytes(build_synthetic_replay(feudal_sec=feudal_sec, castle_sec=castle_sec))
    return target
