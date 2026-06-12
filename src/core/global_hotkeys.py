"""
TRINKER 3.0 - System-wide hotkeys (Windows RegisterHotKey).
Falls back gracefully on macOS/Linux — local QShortcut still works when focused.
"""

from __future__ import annotations

import sys
from typing import Callable, Optional

from PySide6.QtCore import QAbstractNativeEventFilter
from PySide6.QtWidgets import QWidget

from .config import settings
from .hotkeys import normalize_key_sequence
from .logger import logger

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    WM_HOTKEY = 0x0312
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004

    _VK = {
        "Left": 0x25,
        "Right": 0x27,
        "Up": 0x26,
        "Down": 0x28,
        "O": 0x4F,
        "S": 0x53,
        "N": 0x4E,
        "P": 0x50,
        "Space": 0x20,
        "Return": 0x0D,
        "Enter": 0x0D,
    }


def _parse_win_hotkey(seq: str) -> tuple[int, int] | None:
    """Map portable QKeySequence string to (modifiers, vk)."""
    if sys.platform != "win32":
        return None
    parts = [p.strip() for p in normalize_key_sequence(seq).split("+") if p.strip()]
    if not parts:
        return None
    mods = 0
    key = parts[-1]
    for p in parts[:-1]:
        low = p.lower()
        if low in ("ctrl", "control"):
            mods |= MOD_CONTROL
        elif low in ("shift",):
            mods |= MOD_SHIFT
        elif low in ("alt",):
            mods |= MOD_ALT
    vk = _VK.get(key) or _VK.get(key.title())
    if vk is None and len(key) == 1:
        vk = ord(key.upper())
    if vk is None:
        return None
    return mods, vk


class _WinHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callbacks: dict[int, Callable[[], None]]):
        super().__init__()
        self._callbacks = callbacks

    def nativeEventFilter(self, eventType, message):
        if sys.platform != "win32":
            return False, 0
        if eventType != b"windows_generic_MSG":
            return False, 0
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY:
            cb = self._callbacks.get(int(msg.wParam))
            if cb:
                cb()
            return True, 0
        return False, 0


class GlobalHotkeyManager:
    """Register global hotkeys on Windows; no-op elsewhere."""

    _HOTKEY_IDS = {
        "toggle_overlay": 1,
        "next_step": 2,
        "prev_step": 3,
        "pause_timer": 4,
    }

    def __init__(self, parent: QWidget):
        self._parent = parent
        self._filter: Optional[_WinHotkeyFilter] = None
        self._callbacks: dict[str, Callable[[], None]] = {}

    def set_callback(self, action: str, fn: Callable[[], None]) -> None:
        self._callbacks[action] = fn

    def register(self) -> None:
        self.unregister()
        if sys.platform != "win32" or not settings.global_hotkeys_enabled:
            return

        user32 = ctypes.windll.user32
        hwnd = int(self._parent.winId())
        mapping = {
            "toggle_overlay": settings.hotkey_toggle_overlay,
            "next_step": settings.hotkey_next_step,
            "prev_step": settings.hotkey_prev_step,
            "pause_timer": settings.hotkey_start_session,
        }
        id_callbacks: dict[int, Callable[[], None]] = {}

        for action, seq in mapping.items():
            parsed = _parse_win_hotkey(seq)
            cb = self._callbacks.get(action)
            if not parsed or not cb:
                continue
            mods, vk = parsed
            hid = self._HOTKEY_IDS[action]
            if not user32.RegisterHotKey(hwnd, hid, mods, vk):
                logger.warning("Global hotkey failed for %s (%s)", action, seq)
                continue
            id_callbacks[hid] = cb
            logger.info("Global hotkey registered: %s → %s", action, seq)

        if id_callbacks:
            self._filter = _WinHotkeyFilter(id_callbacks)
            from PySide6.QtWidgets import QApplication

            QApplication.instance().installNativeEventFilter(self._filter)

    def unregister(self) -> None:
        if sys.platform != "win32":
            return
        if self._filter:
            from PySide6.QtWidgets import QApplication

            QApplication.instance().removeNativeEventFilter(self._filter)
            self._filter = None
        user32 = ctypes.windll.user32
        hwnd = int(self._parent.winId())
        for hid in self._HOTKEY_IDS.values():
            user32.UnregisterHotKey(hwnd, hid)
