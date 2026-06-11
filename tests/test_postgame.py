"""Tests for post-game coach pipeline helpers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ai_coach.postgame import _parse_overlay_alert, _parse_suggested_build


def test_parse_overlay_alert():
    report = "## Overlay Alert\nQueue loom before boar lure"
    assert "loom" in _parse_overlay_alert(report)


def test_parse_suggested_build():
    report = "## Practice Next\nBuild: 18 Vills Scout Rush — fixes feudal timing"
    assert "Scout" in _parse_suggested_build(report)
