"""Tests for replay filename metadata parsing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.replay.analyzer import _parse_filename_metadata


def test_mp_replay_filename():
    meta = _parse_filename_metadata(Path(
        "MP Replay v101.103.47452.0 @2026.06.08 213123 (2).aoe2record"
    ))
    assert meta["is_mp"] is True
    assert "2026.06.08" in meta["recorded_at"]
