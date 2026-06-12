"""Tests for AoE2 replay folder discovery."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.replay_paths import (
    _expand_savegame_roots,
    count_replays_in,
    register_replay_folder,
)


def test_expand_steam_id_savegame(tmp_path):
    steam_dir = tmp_path / "76561198000000000" / "savegame"
    steam_dir.mkdir(parents=True)
    replay = steam_dir / "SP Replay test.aoe2record"
    replay.write_bytes(b"\x00" * 64)

    roots = _expand_savegame_roots(tmp_path)
    assert any(r.name == "savegame" for r in roots)
    count, newest = count_replays_in(roots)
    assert count == 1
    assert "SP Replay" in newest


def test_register_replay_folder(tmp_path, monkeypatch):
    from src.core import config

    steam_dir = tmp_path / "76561198000000000" / "savegame"
    steam_dir.mkdir(parents=True)
    monkeypatch.setattr(config, "settings", config.AppSettings())
    assert register_replay_folder(tmp_path, save=False)
    assert config.settings.replay_dirs
