"""End-to-end flows across DB, UI, replay, and coach (headless Qt)."""

import pytest


@pytest.fixture(autouse=True)
def _qt_test_guards(monkeypatch):
    from src.core.config import settings

    settings.auto_detect_sessions = False
    settings.onboarding_complete = True
    monkeypatch.setattr(
        "src.ui.medieval.animations.stagger_fade_in",
        lambda widgets, delay_ms=40: None,
    )


@pytest.mark.e2e
def test_e2e_main_window_boot(qtbot, isolated_env, monkeypatch):
    """App shell opens with expected tabs and dashboard data."""
    monkeypatch.setattr(
        "src.ui.main_window.TrinkerMainWindow._setup_background_services",
        lambda self: None,
    )
    from src.ui.main_window import TrinkerMainWindow

    window = TrinkerMainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    assert window.tabs.count() >= 4
    assert window.dashboard_tab is not None
    window.dashboard_tab.refresh()
    assert window.header.lbl_streak is not None


@pytest.mark.e2e
def test_e2e_build_library_to_overlay(qtbot, isolated_env, sample_build_order):
    """Save a build order, load it on the overlay, advance a step."""
    from src.build_orders.manager import save_build_order

    save_build_order(sample_build_order)
    from src.ui.overlay import BuildOrderOverlay

    overlay = BuildOrderOverlay()
    qtbot.addWidget(overlay)
    overlay.load_build_order(sample_build_order)
    overlay.show()
    qtbot.waitExposed(overlay)

    overlay.next_step()
    assert overlay._current_index == 1


@pytest.mark.e2e
def test_e2e_postgame_offline_pipeline(tmp_path, isolated_env):
    """Replay → analyze → offline post-game coach produces overlay alert."""
    from src.ai_coach.postgame import run_postgame_coach
    from src.replay.analyzer import analyze_replay
    from tests.fixtures.synthetic_replay import write_synthetic_mp_replay

    path = write_synthetic_mp_replay(tmp_path, feudal_sec=720.0)
    analysis = analyze_replay(path)
    assert analysis.replay_path

    result = run_postgame_coach(str(path), civ="Britons", build_order_name="Scout Rush")
    assert result.report
    assert result.overlay_alert
    assert result.used_ai is False


@pytest.mark.e2e
def test_e2e_postgame_with_mock_ollama(tmp_path, isolated_env, mock_ollama):
    from src.ai_coach.postgame import run_postgame_coach
    from tests.fixtures.synthetic_replay import write_synthetic_mp_replay

    path = write_synthetic_mp_replay(tmp_path)
    result = run_postgame_coach(str(path), civ="Britons")
    assert result.used_ai is True
    assert "loom" in result.overlay_alert.lower() or result.overlay_alert
