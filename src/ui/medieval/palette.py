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


SKINS: dict[str, MedievalPalette] = {
    "default": MedievalPalette(),
    "britons": MedievalPalette(
        gold="#c9a227",
        gold_bright="#e8c547",
        wood_frame="#5a4a38",
        parchment="#2a2418",
    ),
    "franks": MedievalPalette(
        gold="#3b6ea8",
        gold_bright="#5a8fc4",
        wood_frame="#4a5560",
        parchment="#1e2430",
        feudal="#4a7ab8",
    ),
    "chinese": MedievalPalette(
        gold="#c0392b",
        gold_bright="#e74c3c",
        wood_frame="#6b3030",
        parchment="#281818",
        feudal="#d35400",
    ),
    "byzantines": MedievalPalette(
        gold="#9b59b6",
        gold_bright="#bb77d4",
        wood_frame="#4a3a5c",
        parchment="#221a2e",
        castle="#8e44ad",
    ),
    "mayans": MedievalPalette(
        gold="#27ae60",
        gold_bright="#2ecc71",
        wood_frame="#3d5c40",
        parchment="#1a2820",
        feudal="#1e8449",
    ),
}

SKIN_NAMES: list[str] = list(SKINS.keys())


def get_skin_palette(skin_id: str | None) -> MedievalPalette:
    key = (skin_id or "default").lower()
    return SKINS.get(key, SKINS["default"])


def get_palette() -> MedievalPalette:
    """Return palette for the active civ skin (Settings → Civ Theme)."""
    skin = getattr(settings, "civ_skin", "default") or "default"
    return get_skin_palette(skin)


def use_medieval_style() -> bool:
    """Medieval UI is default for dark theme unless explicitly disabled."""
    style = getattr(settings, "ui_style", "medieval")
    theme = (settings.theme or "dark").lower()
    if style == "classic":
        return False
    return theme != "light"
