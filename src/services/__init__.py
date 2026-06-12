"""Simplify coach service — re-export key helpers."""

from .coach_service import ask_with_context, get_session_coaching, ollama_setup_status

__all__ = ["ask_with_context", "get_session_coaching", "ollama_setup_status"]
