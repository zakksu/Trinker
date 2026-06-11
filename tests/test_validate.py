"""Tests for replay timing validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.replay.validate import validate_timings


def test_rejects_impossible_feudal():
    v = validate_timings(feudal=23, castle=40, source="scan")
    assert v.feudal_time_sec is None
    assert v.castle_time_sec is None
    assert v.quality == "rejected"


def test_accepts_realistic_feudal():
    v = validate_timings(feudal=540, castle=900, source="mgz")
    assert v.feudal_time_sec == 540
    assert v.castle_time_sec == 900
    assert v.quality == "high"
