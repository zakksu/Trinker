"""
TRINKER - Ollama auto-detection and connection health.
"""

from __future__ import annotations

from ..core.config import settings
from ..core.logger import logger

try:
    import requests as _requests
except ImportError:
    _requests = None


def is_ollama_running() -> bool:
    if not _requests:
        return False
    try:
        resp = _requests.get(f"{settings.ollama_url}/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def ensure_ollama_enabled(*, force_coach: bool = True) -> bool:
    """
    Detect Ollama and enable AI coach + post-game coach automatically.
    Returns True if Ollama responded OK.
    """
    if not is_ollama_running():
        return False

    changed = False
    if not settings.ai_coach_enabled:
        settings.ai_coach_enabled = True
        changed = True
    if force_coach and not settings.auto_postgame_coach:
        settings.auto_postgame_coach = True
        changed = True
    if changed:
        settings.save()
        logger.info("Ollama connected — AI Coach + post-game coach enabled.")
    return True
