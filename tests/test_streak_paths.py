"""Tests for practice streaks, badges, and platform paths."""

from datetime import date, timedelta

from src.analytics.session import get_practice_streak, get_training_badges
from src.core.config import APP_DIRS, DATA_DIR, get_replay_search_dirs


def test_data_dir_is_path():
    assert DATA_DIR.exists()
    assert str(DATA_DIR)


def test_app_dirs_resolves():
    assert APP_DIRS.user_data_dir
    assert APP_DIRS.user_log_dir
    assert APP_DIRS.user_cache_dir


def test_replay_search_dirs_returns_list():
    dirs = get_replay_search_dirs()
    assert isinstance(dirs, list)


def test_streak_empty_db():
    streak = get_practice_streak()
    assert "current" in streak
    assert "best" in streak
    assert streak["current"] >= 0


def test_training_badges_is_list():
    badges = get_training_badges()
    assert isinstance(badges, list)


def test_streak_logic_with_dates(monkeypatch):
    """Unit-style check: streak counts consecutive days ending today."""
    from src.analytics import session as session_mod

    today = date.today()
    fake_days = [
        {"date": (today - timedelta(days=i)).isoformat()}
        for i in (0, 1, 2)
    ]

    class FakeConn:
        def execute(self, *args, **kwargs):
            return self

        def fetchall(self):
            return fake_days

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(session_mod, "db_conn", lambda: FakeConn())
    streak = session_mod.get_practice_streak()
    assert streak["current"] == 3
    assert streak["best"] >= 3
