"""Tests for hotkey validation."""

import pytest

from src.core.errors import HotkeyError
from src.core.hotkeys import (
    assert_valid_hotkeys,
    is_valid_hotkey,
    normalize_key_sequence,
    validate_hotkey_set,
)


def test_normalize_key_sequence():
    assert normalize_key_sequence("Ctrl+Right")
    assert is_valid_hotkey("Ctrl+Right")


def test_empty_hotkey_invalid():
    assert not is_valid_hotkey("")
    assert not is_valid_hotkey("   ")


def test_duplicate_hotkeys_rejected():
    errors = validate_hotkey_set({
        "next": "Ctrl+Right",
        "prev": "Ctrl+Right",
    })
    assert errors
    assert "conflict" in errors[0].lower()


def test_valid_hotkey_set_passes():
    errors = validate_hotkey_set({
        "next": "Ctrl+Right",
        "prev": "Ctrl+Left",
        "overlay": "Ctrl+Shift+O",
        "pause": "Ctrl+Shift+S",
    })
    assert errors == []


def test_assert_valid_hotkeys_raises():
    with pytest.raises(HotkeyError):
        assert_valid_hotkeys({"a": "Ctrl+A", "b": "Ctrl+A"})
