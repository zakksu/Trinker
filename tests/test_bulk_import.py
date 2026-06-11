"""Tests for bulk replay import helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.replay.session_builder import match_build_for_civ
from src.replay.validate import validate_timings


def test_match_build_for_known_civ():
    bo = match_build_for_civ("Britons")
    assert bo is not None
    assert bo.civ == "Britons"


def test_match_build_fallback_for_unknown_civ():
    bo = match_build_for_civ("Vietnamese")
    assert bo is not None


def test_validate_rejects_garbage():
    v = validate_timings(feudal=23, source="scan")
    assert v.feudal_time_sec is None
