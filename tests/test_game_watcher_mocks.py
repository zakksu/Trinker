"""Game watcher / overlay pause detection mocks."""

import sys


def test_aoe2_foreground_mock_win32(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        "src.capture.game_watcher._foreground_window_title",
        lambda: "Age of Empires II: Definitive Edition",
    )
    from src.capture.game_watcher import is_aoe2_foreground

    assert is_aoe2_foreground() is True


def test_aoe2_foreground_false_on_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    from src.capture.game_watcher import is_aoe2_foreground

    assert is_aoe2_foreground() is False


def test_sample_clock_region_mock(monkeypatch):
    monkeypatch.setattr("src.capture.game_watcher.sample_clock_region", lambda: 12345)
    from src.capture.game_watcher import sample_clock_region

    assert sample_clock_region() == 12345


def test_overlay_pause_on_stalled_clock(qtbot, monkeypatch):
    """Overlay timer pauses when game clock hash stops changing."""
    from src.ui.overlay import BuildOrderOverlay

    monkeypatch.setattr(
        "src.capture.game_watcher.is_aoe2_foreground",
        lambda: True,
    )
    states = iter([100, 100, 100])
    monkeypatch.setattr(
        "src.capture.game_watcher.sample_clock_region",
        lambda: next(states, 100),
    )

    overlay = BuildOrderOverlay()
    qtbot.addWidget(overlay)
    overlay._is_session_active = True
    overlay._manual_pause = False
    overlay._last_screen_hash = 100
    overlay._stall_samples = 1

    overlay._check_game_pause()
    assert overlay._timer_paused is True
