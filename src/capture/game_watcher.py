"""
TRINKER - AoE2 window / pause detection for overlay timer sync.

Uses Win32 foreground window checks (always available on Windows).
Optional mss screen sampling detects when the in-game clock stops (game paused).
"""

from __future__ import annotations

import sys
from typing import Optional

from ..core.logger import logger

_AOE2_TITLE_PARTS = (
    "age of empires ii",
    "aoe2",
    "age of empires 2",
)


def is_aoe2_foreground() -> bool:
    """True when an AoE2 DE window is the active foreground window."""
    if sys.platform != "win32":
        return False
    title = _foreground_window_title()
    if not title:
        return False
    lower = title.lower()
    return any(part in lower for part in _AOE2_TITLE_PARTS)


def _foreground_window_title() -> str:
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buf = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buf, length)
        return buf.value or ""
    except Exception:
        return ""


def sample_clock_region() -> Optional[int]:
    """
    Hash of the top-right screen region where AoE2 shows game time.
    Returns None if mss is not installed.
    """
    try:
        import mss
    except ImportError:
        return None

    try:
        with mss.mss() as sct:
            mon = sct.monitors[1]
            w, h = mon["width"], mon["height"]
            region = {
                "left": mon["left"] + int(w * 0.80),
                "top": mon["top"] + int(h * 0.005),
                "width": max(40, int(w * 0.18)),
                "height": max(20, int(h * 0.045)),
            }
            shot = sct.grab(region)
            return hash(shot.rgb)
    except Exception as exc:
        logger.debug("Clock region sample failed: %s", exc)
        return None
