"""Tests for medieval UI kit."""

from src.ui.medieval.icons import Icon
from src.ui.medieval.palette import get_palette, use_medieval_style
from src.ui.medieval.styles import parchment_bg, stat_card_stylesheet
from src.ui.theme import get_tokens


def test_medieval_palette_colors():
    p = get_palette()
    assert p.gold.startswith("#")
    assert p.parchment
    assert p.ink


def test_medieval_tokens_when_enabled():
    t = get_tokens("dark")
    if use_medieval_style():
        assert t.medieval is True
        assert t.accent == get_palette().gold


def test_parchment_gradient_css():
    p = get_palette()
    css = parchment_bg(p)
    assert "qlineargradient" in css


def test_stat_card_stylesheet():
    p = get_palette()
    css = stat_card_stylesheet(p, p.gold)
    assert "QFrame" in css


def test_icon_vocabulary():
    assert Icon.FOOD
    assert Icon.status_glyph("green") == Icon.ON_PACE
