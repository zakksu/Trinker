"""Tests for automatic replay import on startup."""

from unittest.mock import MagicMock

import pytest


def test_auto_import_skipped_when_disabled(isolated_env):
    from src.core.config import settings
    from src.core.auto_session import try_auto_import_latest_replay

    settings.auto_detect_sessions = False
    settings.save()

    result = try_auto_import_latest_replay()
    assert result.imported is False


def test_auto_import_catch_up_on_first_run(isolated_env, monkeypatch, tmp_path):
    from src.core.config import settings
    from src.core.auto_session import try_auto_import_latest_replay

    settings.auto_detect_sessions = True
    settings.last_seen_replay_mtime = 0.0
    settings.save()
    monkeypatch.setattr("src.core.auto_session.settings", settings)

    fake_replay = tmp_path / "game.aoe2record"
    fake_replay.write_bytes(b"fake")

    profile = MagicMock()
    profile.civ = "Britons"
    profile.data_quality = "medium"

    monkeypatch.setattr("src.replay.parser.get_latest_replay", lambda: fake_replay)
    monkeypatch.setattr("src.replay.parser.find_replay_files", lambda: [fake_replay])
    monkeypatch.setattr("src.core.auto_session.extract_replay_profile", lambda _p: profile)
    monkeypatch.setattr("src.core.auto_session.profile_to_session", lambda *_a, **_k: None)
    monkeypatch.setattr("src.core.auto_session.save_replay_analysis", lambda *_a, **_k: None)

    result = try_auto_import_latest_replay()
    assert result.imported is True
    assert "Britons" in result.message
