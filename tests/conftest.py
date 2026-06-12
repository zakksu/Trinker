"""Shared pytest fixtures — isolated DB, Qt app, and service mocks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.build_orders.models import BuildOrder, BuildStep


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Point TRINKER data paths at a temp directory and init a fresh DB."""
    data = tmp_path / "trinker_data"
    data.mkdir()
    db = data / "trinker.db"
    settings_file = data / "settings.json"

    monkeypatch.setattr("src.core.config.DATA_DIR", data)
    monkeypatch.setattr("src.core.config.DB_PATH", db)
    monkeypatch.setattr("src.core.config.SETTINGS_FILE", settings_file)
    monkeypatch.setattr("src.core.database.DB_PATH", db)

    settings_file.write_text(
        json.dumps(
            {
                "theme": "dark",
                "ui_style": "medieval",
                "onboarding_complete": True,
                "auto_detect_sessions": False,
                "ai_coach_enabled": False,
            }
        )
    )

    from src.core.config import AppSettings
    from src.core.database import init_db

    monkeypatch.setattr("src.core.config.settings", AppSettings.load())
    init_db()
    yield data


@pytest.fixture
def sample_build_order() -> BuildOrder:
    return BuildOrder(
        id=1,
        name="18 Vills Scout Rush",
        civ="Britons",
        strategy="Scout Rush",
        steps=[
            BuildStep(
                index=1,
                description="Queue 2 vills to sheep",
                time_str="0:00",
                time_sec=0,
                population=6,
                food=200,
            ),
            BuildStep(
                index=2,
                description="Build house, lure boar",
                time_str="1:30",
                time_sec=90,
                population=10,
                food=180,
                wood=50,
            ),
            BuildStep(
                index=3,
                description="Click Feudal Age",
                time_str="8:00",
                time_sec=480,
                population=18,
                age="feudal",
            ),
        ],
    )


@pytest.fixture
def mock_ollama(monkeypatch):
    """Patch Ollama HTTP calls to return deterministic coach text."""

    class _Resp:
        def __init__(self, payload: dict, status: int = 200):
            self._payload = payload
            self.status_code = status

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    def _get(url, timeout=3, **kwargs):
        if url.endswith("/api/tags"):
            return _Resp({"models": [{"name": "llama3"}]})
        return _Resp({}, 404)

    def _post(url, json=None, timeout=60, **kwargs):
        if url.endswith("/api/chat"):
            return _Resp(
                {
                    "message": {
                        "content": (
                            "## Overlay Alert\nQueue loom before boar lure\n\n"
                            "Build: 18 Vills Scout Rush — tighten feudal timing"
                        )
                    }
                }
            )
        if url.endswith("/api/generate"):
            return _Resp({"response": "Practice feudal timing — stay on build order steps."})
        return _Resp({}, 404)

    monkeypatch.setattr("src.ai_coach.coach._REQUESTS_OK", True)
    monkeypatch.setattr("src.ai_coach.coach._requests.get", _get)
    monkeypatch.setattr("src.ai_coach.coach._requests.post", _post)

    from src.core.config import settings

    settings.ai_coach_enabled = True
    settings.ollama_url = "http://localhost:11434"
    settings.ollama_model = "llama3"
    return settings


@pytest.fixture
def replay_corpus_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "replays"
