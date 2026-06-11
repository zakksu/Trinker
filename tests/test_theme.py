"""Tests for centralized theming."""

from src.ui.theme import (
    get_tokens,
    stylesheet_main_window,
    stylesheet_tab_panel,
    stylesheet_table,
)


def test_dark_tokens_have_required_fields():
    t = get_tokens("dark")
    assert t.name == "dark"
    assert t.accent.startswith("#")
    assert t.bg_root
    assert t.text


def test_light_tokens_differ_from_dark():
    dark = get_tokens("dark")
    light = get_tokens("light")
    assert dark.bg_root != light.bg_root
    assert dark.text != light.text


def test_stylesheets_non_empty():
    t = get_tokens("dark")
    assert "QMainWindow" in stylesheet_main_window(t)
    assert "QWidget" in stylesheet_tab_panel(t)
    assert "QTableWidget" in stylesheet_table(t)


def test_accent_color_override():
    t = get_tokens("dark", accent="#ff0000")
    assert t.accent == "#ff0000"
