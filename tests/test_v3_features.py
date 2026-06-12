"""TRINKER 3.0 feature tests."""

from src.ai_coach.rag import clear_cache, retrieve_context
from src.core.config import settings
from src.plugins.registry import emit, register
from src.training.drill_engine import pin_drill, suggest_drill


def test_rag_retrieves_feudal_content():
    clear_cache()
    ctx = retrieve_context("feudal timing dark age villager")
    assert ctx
    assert "Feudal" in ctx or "feudal" in ctx.lower()


def test_rag_disabled_returns_empty(monkeypatch):
    monkeypatch.setattr(settings, "rag_enabled", False)
    assert retrieve_context("feudal") == ""


def test_suggest_drill_late_feudal():
    drill = suggest_drill(feudal_sec=720)
    assert drill.id == "feudal_consistency"


def test_suggest_drill_from_alert():
    drill = suggest_drill(overlay_alert="Queue loom before boar lure")
    assert drill.id == "loom_discipline"


def test_pin_drill_persists(isolated_env):
    drill = suggest_drill(feudal_sec=650)
    pin_drill(drill)
    assert settings.overlay_coach_alert
    assert settings.active_drill_id == drill.id


def test_plugin_hook_emit():
    seen = []

    register("test_hook", lambda value: seen.append(value))
    emit("test_hook", value=42)
    assert 42 in seen


def test_parse_win_hotkey():
    import sys

    if sys.platform != "win32":
        return
    from src.core.global_hotkeys import _parse_win_hotkey

    parsed = _parse_win_hotkey("Ctrl+Right")
    assert parsed is not None
    mods, vk = parsed
    assert vk == 0x27
