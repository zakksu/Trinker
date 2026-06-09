"""
TRINKER - AI Coach
Post-session coaching via a local Ollama LLM.
The coach receives session data and returns actionable text suggestions.

Requires Ollama running locally: https://ollama.ai
Default model: llama3 (configurable in Settings).

This module is entirely optional — if Ollama is unavailable, all functions
return graceful fallback messages rather than raising exceptions.
"""

import json
from typing import Optional

try:
    import requests as _requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

from ..core.config import settings
from ..core.logger import logger


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _sec_to_mmss(sec: Optional[int]) -> str:
    if sec is None:
        return "N/A"
    return f"{sec // 60}:{sec % 60:02d}"


def _build_session_prompt(
    build_order_name: str,
    civ: str,
    feudal_time_sec: Optional[int],
    castle_time_sec: Optional[int],
    accuracy_pct: Optional[float],
    notes: str,
    mistakes: list[str],
    result: str,
) -> str:
    """
    Construct the user message sent to the LLM.
    Keeps the prompt concise to minimize latency on local models.
    """
    mistakes_str = "\n".join(f"  - {m}" for m in mistakes) if mistakes else "  None logged"
    accuracy_str = f"{accuracy_pct:.1f}%" if accuracy_pct is not None else "N/A"

    return f"""You are an expert Age of Empires II coach. Analyze this practice session and give 3-5 specific, actionable improvement tips. Be direct and concise.

Build Order: {build_order_name} ({civ})
Result: {result}
Feudal Age Time: {_sec_to_mmss(feudal_time_sec)}
Castle Age Time: {_sec_to_mmss(castle_time_sec)}
Accuracy Score: {accuracy_str}
Mistakes logged: 
{mistakes_str}
Player notes: {notes or 'None'}

Provide your coaching response in this format:
1. [Specific tip about the biggest issue]
2. [Next most important improvement]
3. [Timing or eco optimization]
(add up to 2 more if clearly relevant)

Keep each tip under 2 sentences. Focus on what to DO, not just what went wrong."""


def _build_recommendation_prompt(stats: dict, top_mistakes: list[str]) -> str:
    """Prompt for build-order recommendations based on aggregate stats."""
    mistakes_str = "\n".join(f"  - {m}" for m in top_mistakes[:5]) if top_mistakes else "  None identified"
    return f"""You are an AoE2 coaching AI. Based on this player's stats, recommend 2-3 build orders or strategies they should practice to improve.

Stats summary:
- Total sessions: {stats.get('total_sessions', 0)}
- Win rate: {stats.get('win_rate', 0):.1f}%
- Average feudal time: {_sec_to_mmss(stats.get('avg_feudal_sec'))}
- Average castle time: {_sec_to_mmss(stats.get('avg_castle_sec'))}
- Best feudal time: {_sec_to_mmss(stats.get('best_feudal_sec'))}

Recurring patterns/mistakes:
{mistakes_str}

Respond with 2-3 specific recommendations. Each should name a concrete build order or strategy and explain in 1 sentence why it targets this player's weakness. Be direct."""


# ---------------------------------------------------------------------------
# Ollama client
# ---------------------------------------------------------------------------

def _is_ollama_available() -> bool:
    """Quick check whether Ollama is reachable."""
    if not _REQUESTS_OK or not settings.ai_coach_enabled:
        return False
    try:
        resp = _requests.get(
            f"{settings.ollama_url}/api/tags",
            timeout=3,
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
            "temperature": 0.3,     # low temp for factual coaching advice
            "num_predict": 512,     # keep responses concise
        },
    }
    resp = _requests.post(
        f"{settings.ollama_url}/api/generate",
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "").strip()


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

    prompt = _build_session_prompt(
        build_order_name, civ, feudal_time_sec, castle_time_sec,
        accuracy_pct, notes, mistakes or [], result,
    )
    try:
        response = _query_ollama(prompt)
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

    prompt = _build_recommendation_prompt(stats, top_mistakes or [])
    try:
        return _query_ollama(prompt)
    except Exception as exc:
        logger.warning("AI recommendation request failed: %s", exc)
        return "Could not reach AI Coach. Check Ollama is running and the URL is correct in Settings."


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
        if feudal_sec > 600:   # >10:00
            tips.append("1. Your feudal time is slow. Focus on idle villager time — every idle second costs resources. Spam villagers non-stop in Dark Age.")
        elif feudal_sec > 540: # >9:00
            tips.append("1. Feudal time is slightly slow. Check that you're queuing the next build step while your current action resolves.")
        else:
            tips.append("1. Good feudal time! Maintain this consistency and focus on transitioning efficiently into your Feudal strategy.")

    if castle_sec is not None:
        if castle_sec > 1080:  # >18:00
            tips.append("2. Castle time is very late. Make sure you're collecting enough food/gold for the research — track resources at Feudal click.")
        elif castle_sec > 960: # >16:00
            tips.append("2. Castle time is a bit slow. Consider if your Feudal strategy is economical enough to support a fast Castle Age.")

    if accuracy_pct is not None:
        if accuracy_pct < 50:
            tips.append("3. Accuracy is low — slow down and focus on step completion. Speed comes with muscle memory; precision comes first.")
        elif accuracy_pct < 75:
            tips.append("3. Accuracy is improving. Identify the 2-3 steps where you hesitate most and drill them in isolation.")

    if not tips:
        tips = [
            "Enable AI Coach in Settings (requires Ollama) for personalized advice.",
            "General tip: Focus on one build order at a time until your feudal time is consistent within 30 seconds.",
            "Track your feudal and castle times every session — the trend matters more than any single run.",
        ]

    header = "── Offline Coaching Tips (AI Coach not available) ──\n\n"
    footer = "\n\n💡 Enable AI Coach in Settings → AI Coaching for personalized analysis."
    return header + "\n".join(tips) + footer
