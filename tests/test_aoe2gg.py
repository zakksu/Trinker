"""Tests for aoe2.gg / ladder match import."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.database import init_db
from src.integrations.aoe2gg import (
    MatchImportResult,
    OnlineMatch,
    fetch_recent_matches,
    profile_url_for,
    save_online_matches,
)


def test_profile_url():
    url = profile_url_for("76561198278846899")
    assert "aoe2.gg" in url
    assert "76561198278846899" in url


def test_fetch_no_steam_id():
    result = fetch_recent_matches("")
    assert result.error
    assert not result.matches


@patch("src.integrations.aoe2gg._requests")
def test_fetch_aoe2net_success(mock_requests):
    mock_requests.get.return_value.status_code = 200
    mock_requests.get.return_value.json.return_value = [{
        "matchId": "12345",
        "mapName": "Arabia",
        "started": 1700000000,
        "teams": [{
            "players": [
                {"profileId": "999", "name": "Opponent", "civ": "Franks"},
                {"profileId": "76561198000000001", "name": "Me", "civ": "Spanish", "winner": True, "rating": 1100},
            ],
        }],
    }]
    result = fetch_recent_matches("76561198000000001", count=5)
    assert len(result.matches) == 1
    assert result.matches[0].civ == "Spanish"
    assert result.source == "aoe2.net"


def test_save_online_matches(tmp_path, monkeypatch):
    from src.core import config as cfg
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "test.db")
    init_db()
    matches = [
        OnlineMatch(
            match_id="m1",
            played_at="2024-01-01T00:00:00",
            map_name="Arabia",
            civ="Spanish",
            result="win",
            rating=1100,
            opponent="Enemy",
            source="test",
            profile_url=profile_url_for("123"),
        ),
    ]
    n = save_online_matches(matches, "123")
    assert n == 1
