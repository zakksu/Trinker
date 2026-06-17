"""
TRINKER - AI Coach
Post-session coaching via a local Ollama LLM.
The coach receives session data and returns actionable text suggestions.

Requires Ollama running locally: https://ollama.ai
Default model: llama3 (configurable in Settings).

This module is entirely optional — if Ollama is unavailable, all functions
return graceful fallback messages rather than raising exceptions.
"""

from typing import Optional

try:
    import requests as _requests

    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

from ..core.config import OLLAMA_ENABLED, OLLAMA_PROBE_TIMEOUT_SECONDS, OLLAMA_TIMEOUT_SECONDS, settings
from ..core.resource_profile import ollama_request_options
from ..core.logger import logger
from .prompt_builder import PromptBuilder
from .summary import ReplaySummary

# ---------------------------------------------------------------------------
# Ollama client
# ---------------------------------------------------------------------------


def _is_ollama_available() -> bool:
    """Quick check whether Ollama is reachable."""
    if not _REQUESTS_OK or not settings.ai_coach_enabled or not OLLAMA_ENABLED:
        return False
    try:
        resp = _requests.get(
            f"{settings.ollama_url}/api/tags",
            timeout=OLLAMA_PROBE_TIMEOUT_SECONDS,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _query_ollama(prompt: str) -> str:
    """
    Send a prompt to Ollama and return the response text.
    Uses the streaming=False endpoint for simplicity.
    Raises requests.RequestException on network errors.
    """
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 512,
            **ollama_request_options(),
        },
    }
    resp = _requests.post(
        f"{settings.ollama_url}/api/generate",
        json=payload,
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "").strip()


def _query_ollama_chat(system: str, user: str) -> str:
    """Chat-style Ollama call; falls back to /api/generate on older Ollama builds."""
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.25, "num_predict": 800, **ollama_request_options()},
    }
    resp = _requests.post(
        f"{settings.ollama_url}/api/chat",
        json=payload,
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )
    if resp.status_code == 404:
        logger.debug("Ollama /api/chat not found — falling back to /api/generate")
        return _query_ollama(f"{system}\n\n{user}")
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "").strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_session_coaching(
    build_order_name: str,
    civ: str,
    feudal_time_sec: Optional[int] = None,
    castle_time_sec: Optional[int] = None,
    accuracy_pct: Optional[float] = None,
    notes: str = "",
    mistakes: Optional[list[str]] = None,
    result: str = "practice",
) -> str:
    """
    Return AI coaching text for a completed session.

    Args:
        build_order_name: Name of the build order practiced.
        civ:              Civilization played.
        feudal_time_sec:  Time to Feudal age in seconds (None if not tracked).
        castle_time_sec:  Time to Castle age in seconds.
        accuracy_pct:     Session accuracy score 0-100.
        notes:            Player's own session notes.
        mistakes:         List of mistake strings the player logged.
        result:           'win' | 'loss' | 'draw' | 'practice'.

    Returns:
        Multi-line string with coaching advice, or a fallback message if
        Ollama is unavailable.
    """
    if not _is_ollama_available():
        return _offline_coaching_tips(feudal_time_sec, castle_time_sec, accuracy_pct)

    summary = ReplaySummary(
        civ=civ,
        build_name=build_order_name,
        result=result,
        feudal_sec=feudal_time_sec,
        castle_sec=castle_time_sec,
        accuracy_pct=accuracy_pct,
        notes=notes,
        mistakes=mistakes or [],
    )
    system, user = PromptBuilder.session_coaching(summary)
    try:
        response = _query_ollama_chat(system, user)
        logger.info("AI coach response received (%d chars)", len(response))
        return response
    except Exception as exc:
        logger.warning("AI coach request failed: %s", exc)
        return _offline_coaching_tips(feudal_time_sec, castle_time_sec, accuracy_pct)


def get_build_recommendations(stats: dict, top_mistakes: Optional[list[str]] = None) -> str:
    """
    Return AI-generated build order recommendations based on aggregate stats.

    Args:
        stats:        Dict from analytics.session.get_summary_stats().
        top_mistakes: Optional list of frequently logged mistake strings.

    Returns:
        Recommendation text, or a generic suggestion if Ollama is unavailable.
    """
    if not _is_ollama_available():
        return (
            "AI Coach is not available. Enable it in Settings and ensure Ollama is running.\n\n"
            "Manual tip: Focus on the build order you've practiced least — "
            "repetition is the fastest path to consistent execution."
        )

    prompt = PromptBuilder.build_recommendations(stats, top_mistakes or [])
    try:
        return _query_ollama(prompt)
    except Exception as exc:
        logger.warning("AI recommendation request failed: %s", exc)
        return (
            "Could not reach AI Coach. Check Ollama is running and the URL is correct in Settings."
        )


# ---------------------------------------------------------------------------
# Offline fallback advice (rule-based, no LLM required)
# ---------------------------------------------------------------------------


def _offline_coaching_tips(
    feudal_sec: Optional[int],
    castle_sec: Optional[int],
    accuracy_pct: Optional[float],
) -> str:
    """
    Rule-based tips shown when Ollama is unavailable.
    Better than showing nothing — derived from common coaching advice.
    """
    tips: list[str] = []

    if feudal_sec is not None:
        if feudal_sec > 600:  # >10:00
            tips.append(
                "1. Your feudal time is slow. Focus on idle villager time — every idle second costs resources. Spam villagers non-stop in Dark Age."
            )
        elif feudal_sec > 540:  # >9:00
            tips.append(
                "1. Feudal time is slightly slow. Check that you're queuing the next build step while your current action resolves."
            )
        else:
            tips.append(
                "1. Good feudal time! Maintain this consistency and focus on transitioning efficiently into your Feudal strategy."
            )

    if castle_sec is not None:
        if castle_sec > 1080:  # >18:00
            tips.append(
                "2. Castle time is very late. Make sure you're collecting enough food/gold for the research — track resources at Feudal click."
            )
        elif castle_sec > 960:  # >16:00
            tips.append(
                "2. Castle time is a bit slow. Consider if your Feudal strategy is economical enough to support a fast Castle Age."
            )

    if accuracy_pct is not None:
        if accuracy_pct < 50:
            tips.append(
                "3. Accuracy is low — slow down and focus on step completion. Speed comes with muscle memory; precision comes first."
            )
        elif accuracy_pct < 75:
            tips.append(
                "3. Accuracy is improving. Identify the 2-3 steps where you hesitate most and drill them in isolation."
            )

    if not tips:
        tips = [
            "Enable AI Coach in Settings (requires Ollama) for personalized advice.",
            "General tip: Focus on one build order at a time until your feudal time is consistent within 30 seconds.",
            "Track your feudal and castle times every session — the trend matters more than any single run.",
        ]

    header = "── Offline Coaching Tips (AI Coach not available) ──\n\n"
    footer = "\n\n💡 Enable AI Coach in Settings → AI Coaching for personalized analysis."
    return header + "\n".join(tips) + footer
