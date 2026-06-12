"""
Medieval strategy palette — parchment, wood, gold, iron.
Pure color tokens (no image assets) for high performance.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...core.config import settings


@dataclass(frozen=True)
class MedievalPalette:
    """AoE2-inspired surface and accent colors."""

    parchment: str = "#2e261c"
    parchment_light: str = "#3a3226"
    parchment_dark: str = "#1e1812"
    wood: str = "#5c4033"
    wood_dark: str = "#3e2a1f"
    wood_frame: str = "#6b4c3b"
    gold: str = "#c9a227"
    gold_bright: str = "#e8c547"
    gold_dim: str = "#8a7020"
    iron: str = "#4a4f55"
    iron_light: str = "#6b7280"
    ink: str = "#f4ead5"
    ink_dim: str = "#b8a88a"
    ink_muted: str = "#7a6f5c"
    success: str = "#6aab55"
    warning: str = "#d4a017"
    error: str = "#b54a4a"
    feudal: str = "#d4843a"
    castle: str = "#9b7bb8"
    imperial: str = "#c45c5c"
    overlay_bg: str = "rgba(22, 18, 14, 0.94)"
    overlay_border: str = "#6b4c3b"


def get_palette() -> MedievalPalette:
    """Return palette; gold accent can follow user accent in future."""
    return MedievalPalette()


def use_medieval_style() -> bool:
    """Medieval UI is default for dark theme unless explicitly disabled."""
    style = getattr(settings, "ui_style", "medieval")
    theme = (settings.theme or "dark").lower()
    if style == "classic":
        return False
    return theme != "light"
