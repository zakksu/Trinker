"""TRINKER 3.1 feature tests."""

import json
from pathlib import Path

from src.core.config import settings
from src.core.telemetry import track
from src.training.drill_engine import suggest_drill
from src.training.drill_progress import get_drill_progress, record_drill_game, reset_drill_progress
from src.training.simulation import evaluate_tick, get_scenario, list_scenarios
from src.ui.skins.registry import SKIN_NAMES, get_skin_palette


def test_civ_skin_palette_differs():
    default = get_skin_palette("default")
    franks = get_skin_palette("franks")
    assert default.gold != franks.gold
    assert "franks" in SKIN_NAMES


def test_drill_progress_increments(isolated_env):
    drill = suggest_drill(feudal_sec=700)
    reset_drill_progress(drill.id)
    settings.active_drill_id = drill.id
    settings.save()
    msg = record_drill_game(feudal_sec=650)
    prog = get_drill_progress(drill.id)
    assert prog["games_done"] == 1
    assert msg and "1/3" in msg


def test_simulation_evaluate_tick():
    sc = get_scenario("dark_age_eco")
    assert sc is not None
    assert "pace" in evaluate_tick(sc, 120).lower()
    assert len(list_scenarios()) >= 3


def test_telemetry_respects_opt_in(isolated_env, monkeypatch):
    from src.core import telemetry as telemetry_mod

    telem_path = isolated_env / "telemetry.jsonl"
    monkeypatch.setattr(telemetry_mod, "_TELEMETRY_FILE", telem_path)
    monkeypatch.setattr(settings, "telemetry_opt_in", False)
    track("test_event", foo="bar")
    assert not telem_path.exists()

    monkeypatch.setattr(settings, "telemetry_opt_in", True)
    track("test_event", foo="bar")
    assert telem_path.exists()
    payload = json.loads(telem_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert payload["event"] == "test_event"


def test_ensure_remote_files_skips_without_urls(tmp_path):
    from tests.fixtures.corpus_runner import ensure_remote_files, load_manifest

    manifest = {"remote": [], "replays": []}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    ensure_remote_files(tmp_path)  # no-op
    assert load_manifest(tmp_path)["remote"] == []
