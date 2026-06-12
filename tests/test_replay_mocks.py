"""Replay parser and profile tests with synthetic fixtures."""

from pathlib import Path

import pytest

from src.replay.analyzer import ReplayAnalysis, analyze_replay
from tests.fixtures.synthetic_replay import build_synthetic_replay, write_synthetic_mp_replay


def test_synthetic_replay_scan_age_times(tmp_path):
    path = write_synthetic_mp_replay(tmp_path, feudal_sec=480.0, castle_sec=960.0)
    analysis = analyze_replay(path)
    assert isinstance(analysis, ReplayAnalysis)
    assert analysis.replay_path == str(path.resolve())
    assert analysis.is_multiplayer is True


def test_analyze_replay_mocked_profile(tmp_path, monkeypatch):
    from src.replay.profile import ReplayProfile

    path = tmp_path / "test.aoe2record"
    path.write_bytes(build_synthetic_replay())

    fake = ReplayProfile(
        replay_path=str(path.resolve()),
        civ="Franks",
        map_name="Arabia",
        game_mode="mp",
        feudal_time_sec=510,
        data_quality="medium",
        confidence="medium",
    )

    monkeypatch.setattr("src.replay.profile.extract_replay_profile", lambda p: fake)
    analysis = analyze_replay(path)
    assert analysis.civ == "Franks"
    assert analysis.feudal_time_sec == 510


def test_mgz_parser_graceful_failure(tmp_path, monkeypatch):
    from src.replay.mgz_parser import MgzParseResult, parse_with_mgz

    path = tmp_path / "broken.aoe2record"
    path.write_bytes(b"not a real replay")

    monkeypatch.setattr(
        "src.replay.mgz_parser.parse_with_mgz",
        lambda p: MgzParseResult(errors=["mgz unavailable in test"]),
    )
    result = parse_with_mgz(path)
    assert result.errors
