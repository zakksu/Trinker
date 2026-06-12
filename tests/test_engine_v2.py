"""Tests for replay extraction engine v2."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.replay.engine_v2 import EngineV2Result, extract_replay_v2, _pick_best, _QUALITY_RANK
from src.replay.engine_v2 import ExtractionCandidate
from src.replay.validate import ValidatedTimings


def test_pick_best_prefers_high_quality_mgz():
    low = ExtractionCandidate(
        source="scan",
        validated=ValidatedTimings(feudal_time_sec=600, quality="low"),
    )
    high = ExtractionCandidate(
        source="mgz",
        validated=ValidatedTimings(feudal_time_sec=555, quality="high"),
    )
    best = _pick_best([low, high])
    assert best is not None
    assert best.source == "mgz"
    assert best.validated.feudal_time_sec == 555


def test_extract_missing_file_returns_rejected():
    missing = Path(__file__).parent / "nonexistent_replay_xyz.mgz"
    result = extract_replay_v2(missing)
    assert isinstance(result, EngineV2Result)
    assert result.data_quality == "rejected"


def test_quality_score_ranking():
    r = EngineV2Result(data_quality="high")
    assert r.quality_score() == _QUALITY_RANK["high"]
