"""Tests for historical analysis."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analytics.history import build_historical_summary


def test_historical_summary_returns_text():
    text = build_historical_summary("Britons")
    assert "Historical" in text
    assert "sessions" in text.lower()
