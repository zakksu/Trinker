"""
TRINKER - Domain errors with user-friendly messages.
"""

from __future__ import annotations


class TrinkerError(Exception):
    """Base error for recoverable TRINKER failures."""

    user_message: str = "Something went wrong. Check the log for details."

    def __init__(self, message: str = "", *, user_message: str = ""):
        super().__init__(message or user_message or self.user_message)
        if user_message:
            self.user_message = user_message


class ReplayError(TrinkerError):
    user_message = "Could not read that replay. Make sure the file is a valid .aoe2record."


class BuildOrderError(TrinkerError):
    user_message = "Build order operation failed. Check the Library tab."


class CoachError(TrinkerError):
    user_message = "AI coach is unavailable. Check Settings → Ollama connection."


class ConfigError(TrinkerError):
    user_message = "Invalid setting. Please review your preferences."


class HotkeyError(ConfigError):
    user_message = "Invalid or conflicting hotkey. Choose a different combination."


def user_friendly_message(exc: BaseException) -> str:
    """Return a safe message suitable for toast / dialog display."""
    if isinstance(exc, TrinkerError):
        return exc.user_message
    text = str(exc).strip()
    if not text or len(text) > 200:
        return "An unexpected error occurred. See the log file for details."
    return text
