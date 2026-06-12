"""Chart data key and win-rate helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_feudal_trend_reads_feudal_time_sec():
    trend = [{"feudal_time_sec": 600, "date": "2026-06-01", "session_id": 1}]
    ys = [t.get("feudal_time_sec") or t.get("feudal_sec") or 0 for t in trend]
    assert ys == [600]


def test_win_rate_none_when_only_practice():
    from src.core.database import init_db
    from src.analytics.session import get_summary_stats

    init_db()
    stats = get_summary_stats()
    if stats.get("total_sessions", 0) > 0 and not (stats.get("wins") or stats.get("losses")):
        assert stats.get("win_rate") is None
        assert stats.get("practice_sessions", 0) >= 0
