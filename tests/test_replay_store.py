"""Tests for replay analysis storage."""

import json
from pathlib import Path

from src.analytics.replay_store import get_latest_replay_analysis, save_replay_analysis
from src.core.database import init_db
from src.replay.profile import ReplayProfile


def test_save_and_load_replay_analysis(tmp_path):
    init_db()
    profile = ReplayProfile(
        replay_path=str((tmp_path / "test.aoe2record").resolve()),
        file_name="test.aoe2record",
        civ="Britons",
        map_name="Arabia",
        game_mode="mp",
        data_quality="medium",
        feudal_time_sec=600,
    )
    rid = save_replay_analysis(profile, session_id=None)
    assert rid > 0

    latest = get_latest_replay_analysis()
    assert latest is not None
    assert latest.civ == "Britons"
    data = json.loads(latest.profile_json)
    assert data["feudal_time_sec"] == 600
