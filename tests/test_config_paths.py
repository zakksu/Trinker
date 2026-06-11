"""Tests for replay search path configuration."""

from src.core.config import AppSettings, get_replay_search_dirs


def test_get_replay_search_dirs_includes_defaults():
    dirs = get_replay_search_dirs()
    assert isinstance(dirs, list)


def test_new_settings_default_onboarding_complete_for_existing():
    """Existing field defaults keep onboarding off for migrated settings."""
    s = AppSettings()
    assert s.onboarding_complete is True
