"""Platform stats and adaptive drill tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analytics.training_stats import format_win_rate_label, get_platform_stats
from src.training.drill_engine import suggest_drill_from_postgame


def test_format_win_rate_none():
    assert format_win_rate_label({}) == "—"
    assert format_win_rate_label({"ranked_win_rate": 55.5}) == "55.5%"


def test_platform_stats_has_all_games():
    from src.core.database import init_db

    init_db()
    stats = get_platform_stats()
    assert "all_games" in stats
    assert "ranked_win_rate" in stats
    assert "replay_win_rate" in stats


def test_suggest_drill_from_late_feudal_postgame():
    drill = suggest_drill_from_postgame(
        overlay_alert="Click Feudal earlier",
        feudal_sec=650,
        coach_report="Your feudal was late again.",
    )
    assert drill.id == "feudal_consistency"
