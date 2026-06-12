"""pytest-qt smoke tests for core widgets."""

import pytest

from src.ui.dashboard_tab import DashboardTab
from src.ui.overlay import BuildOrderOverlay


@pytest.fixture(autouse=True)
def _qt_test_guards(monkeypatch):
    """Keep UI tests deterministic — no stagger timers or background imports."""
    from src.core.config import settings

    settings.auto_detect_sessions = False
    settings.onboarding_complete = True
    monkeypatch.setattr(
        "src.ui.medieval.animations.stagger_fade_in",
        lambda widgets, delay_ms=40: None,
    )


def test_dashboard_tab_renders(qtbot, isolated_env):
    tab = DashboardTab()
    qtbot.addWidget(tab)
    tab.refresh()
    assert tab.card_sessions.lbl_val.text() is not None


def test_overlay_loads_build_order(qtbot, sample_build_order):
    overlay = BuildOrderOverlay()
    qtbot.addWidget(overlay)
    overlay.load_build_order(sample_build_order)
    assert overlay.lbl_bo_name.text().startswith("18 Vills")
    assert overlay.get_current_step() is not None
    assert overlay.get_current_step().description


def test_overlay_next_step_advances(qtbot, sample_build_order):
    overlay = BuildOrderOverlay()
    qtbot.addWidget(overlay)
    overlay.load_build_order(sample_build_order)
    overlay.next_step()
    assert overlay._current_index == 1
    step = overlay.get_current_step()
    assert step and "house" in step.description.lower()


def test_stat_card_pulse_on_change(qtbot):
    from src.ui.medieval.icons import Icon
    from src.ui.medieval.widgets import StatCard

    card = StatCard(Icon.GAME, "Games", "0")
    qtbot.addWidget(card)
    card.set_value("3", animate=True)
    assert card.lbl_val.text() == "3"
