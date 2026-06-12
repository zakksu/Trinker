"""Mocked Ollama coach HTTP integration tests."""

from src.ai_coach.chat import ask_coach
from src.ai_coach.coach import get_build_recommendations, get_session_coaching
from src.ai_coach.summary import ReplaySummary


def test_ollama_available_mock(mock_ollama):
    from src.ai_coach.coach import _is_ollama_available

    assert _is_ollama_available() is True


def test_session_coaching_with_mock(mock_ollama):
    text = get_session_coaching(
        build_order_name="18 Vills Scout Rush",
        civ="Britons",
        feudal_time_sec=540,
        accuracy_pct=70,
    )
    assert text
    assert "feudal" in text.lower() or "Practice" in text or "loom" in text.lower()


def test_build_recommendations_with_mock(mock_ollama):
    text = get_build_recommendations({"total_sessions": 5, "win_rate": 40.0})
    assert text
    assert len(text) > 20


def test_ask_coach_persists_messages(mock_ollama, isolated_env):
    summary = ReplaySummary(civ="Britons", build_name="Scout Rush", feudal_sec=600)
    reply = ask_coach("Why was my feudal late?", summary, thread_key="test-thread")
    assert reply

    from src.ai_coach.chat import get_coach_messages

    msgs = get_coach_messages("test-thread")
    assert len(msgs) >= 2
    assert msgs[0].role == "user"
    assert msgs[-1].role == "assistant"


def test_ask_coach_offline_fallback(isolated_env, monkeypatch):
    monkeypatch.setattr("src.ai_coach.coach._is_ollama_available", lambda: False)
    summary = ReplaySummary(civ="Britons", feudal_sec=700)
    reply = ask_coach("Tips?", summary, thread_key="offline-thread")
    assert "Offline" in reply or "feudal" in reply.lower() or "Enable" in reply
