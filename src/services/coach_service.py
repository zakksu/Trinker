"""
TRINKER 3.0 - Coach service layer (RAG + Ollama + offline fallbacks).
"""

from __future__ import annotations

from ..ai_coach import coach as coach_mod
from ..ai_coach.chat import ask_coach
from ..ai_coach.summary import ReplaySummary
from ..core.config import settings
from ..core.ollama import is_ollama_running


def get_session_coaching(build_order_name: str, civ: str, **kwargs) -> str:
    return coach_mod.get_session_coaching(build_order_name, civ, **kwargs)


def ask_with_context(question: str, summary: ReplaySummary, *, thread_key: str = "dashboard") -> str:
    return ask_coach(question, summary, thread_key=thread_key)


def ollama_setup_status() -> dict:
    return {
        "running": is_ollama_running(),
        "url": settings.ollama_url,
        "model": settings.ollama_model,
        "recommended": settings.recommended_ollama_model,
        "rag_enabled": settings.rag_enabled,
    }
