"""
TRINKER - Hotkey validation and normalization.
"""

from __future__ import annotations

from PySide6.QtGui import QKeySequence

from .errors import HotkeyError


def normalize_key_sequence(text: str) -> str:
    """Convert user text to portable QKeySequence string."""
    text = (text or "").strip()
    if not text:
        return ""
    seq = QKeySequence(text)
    portable = seq.toString(QKeySequence.SequenceFormat.PortableText)
    return portable if portable else text


def is_valid_hotkey(text: str) -> bool:
    """True if the string maps to at least one key (with optional modifiers)."""
    text = normalize_key_sequence(text)
    if not text:
        return False
    seq = QKeySequence(text)
    return not seq.isEmpty()


def validate_hotkey_set(mapping: dict[str, str]) -> list[str]:
    """
    Validate a set of named hotkeys.
    Returns a list of human-readable error strings (empty if OK).
    """
    errors: list[str] = []
    seen: dict[str, str] = {}

    for name, raw in mapping.items():
        label = name.replace("_", " ").title()
        key = normalize_key_sequence(raw)
        if not key:
            errors.append(f"{label}: hotkey cannot be empty.")
            continue
        if not is_valid_hotkey(key):
            errors.append(f"{label}: '{raw}' is not a valid key combination.")
            continue
        if key in seen:
            errors.append(f"{label} conflicts with {seen[key]} (both use {key}).")
        else:
            seen[key] = label

    return errors


def assert_valid_hotkeys(mapping: dict[str, str]) -> None:
    """Raise HotkeyError if any hotkey is invalid or duplicated."""
    errors = validate_hotkey_set(mapping)
    if errors:
        raise HotkeyError("; ".join(errors))
