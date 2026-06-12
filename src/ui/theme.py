"""
TRINKER - Centralized theming (dark / light / medieval).
Single source for QSS tokens used across main window, tabs, and dialogs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core.config import settings
from .medieval.palette import get_palette, use_medieval_style
from .medieval.styles import parchment_bg, wood_frame_border

FONT_STACK = '"Segoe UI", "Cinzel", "Georgia", "Times New Roman", serif'
FONT_UI = '"Segoe UI", "SF Pro Display", "Inter", sans-serif'


@dataclass(frozen=True)
class ThemeTokens:
    """Color and surface tokens for one theme variant."""

    name: str
    accent: str
    accent_soft: str
    accent_muted: str
    bg_root: str
    bg_window: str
    bg_panel: str
    bg_input: str
    bg_elevated: str
    bg_header: str
    border: str
    border_subtle: str
    text: str
    text_dim: str
    text_muted: str
    text_title: str
    success: str
    warning: str
    error: str
    selection: str
    medieval: bool = False


def _accent_variants(hex_color: str) -> tuple[str, str, str]:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        hex_color = "#3498db"
        h = "3498db"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return hex_color, f"rgba({r},{g},{b},0.12)", f"rgba({r},{g},{b},0.4)"


def _medieval_tokens() -> ThemeTokens:
    p = get_palette()
    return ThemeTokens(
        name="medieval",
        accent=p.gold,
        accent_soft="rgba(201, 162, 39, 0.15)",
        accent_muted="rgba(201, 162, 39, 0.45)",
        bg_root=p.parchment_dark,
        bg_window=p.parchment,
        bg_panel=p.parchment_light,
        bg_input=p.parchment_dark,
        bg_elevated=p.parchment_light,
        bg_header=p.parchment_dark,
        border=p.wood_frame,
        border_subtle=p.wood_dark,
        text=p.ink,
        text_dim=p.ink_dim,
        text_muted=p.ink_muted,
        text_title=p.gold_bright,
        success=p.success,
        warning=p.warning,
        error=p.error,
        selection="rgba(201, 162, 39, 0.22)",
        medieval=True,
    )


def get_tokens(theme_name: Optional[str] = None, accent: Optional[str] = None) -> ThemeTokens:
    """Resolve tokens for the active or requested theme."""
    name = (theme_name or settings.theme or "dark").lower()
    if name != "light" and use_medieval_style():
        return _medieval_tokens()

    accent_hex = accent or getattr(settings, "accent_color", None) or "#3498db"
    accent_main, accent_soft, accent_muted = _accent_variants(accent_hex)

    if name == "light":
        return ThemeTokens(
            name="light",
            accent=accent_main if accent_main != "#3498db" else "#007AFF",
            accent_soft="rgba(0, 122, 255, 0.10)",
            accent_muted="rgba(0, 122, 255, 0.35)",
            bg_root="#f5f5f7",
            bg_window="#ffffff",
            bg_panel="#f0f0f2",
            bg_input="#ffffff",
            bg_elevated="#e8e8ea",
            bg_header="#e8e8ea",
            border="#d0d0d5",
            border_subtle="#e0e0e5",
            text="#1a1a1a",
            text_dim="#666666",
            text_muted="#888888",
            text_title="#007AFF",
            success="#28a745",
            warning="#d68910",
            error="#dc3545",
            selection="rgba(0, 122, 255, 0.15)",
        )

    return ThemeTokens(
        name="dark",
        accent=accent_main,
        accent_soft=accent_soft,
        accent_muted=accent_muted,
        bg_root="#0d0d0f",
        bg_window="#111113",
        bg_panel="#16161a",
        bg_input="#1e1e22",
        bg_elevated="#1a1a20",
        bg_header="#0a0a0c",
        border="#2c2c2e",
        border_subtle="#1a1a1f",
        text="#ecf0f1",
        text_dim="#7f8c8d",
        text_muted="#3c3c4e",
        text_title="#7ec8ff",
        success="#2ecc71",
        warning="#f1c40f",
        error="#e74c3c",
        selection="#1c3a5c",
    )


def _font_family(t: ThemeTokens) -> str:
    return FONT_STACK if t.medieval else FONT_UI


def stylesheet_main_window(t: ThemeTokens) -> str:
    ff = _font_family(t)
    bg = parchment_bg(get_palette()) if t.medieval else t.bg_root
    tab_bg = get_palette().parchment_dark if t.medieval else t.bg_window
    tab_sel = get_palette().parchment if t.medieval else t.bg_window
    return f"""
QMainWindow, QWidget {{
    background: {bg};
    color: {t.text};
    font-family: {ff};
}}
QTabWidget::pane {{
    border: none;
    background: {t.bg_window};
}}
QTabBar {{
    background: {t.bg_root};
}}
QTabBar::tab {{
    background: {tab_bg};
    color: {t.text_dim};
    padding: 10px 20px;
    margin-right: 1px;
    border: none;
    font-size: 12px;
    letter-spacing: 0.5px;
    font-weight: {"bold" if t.medieval else "normal"};
}}
QTabBar::tab:selected {{
    color: {t.accent};
    border-bottom: 3px solid {t.accent};
    background: {tab_sel};
}}
QTabBar::tab:hover:!selected {{
    color: {t.text};
    background: {t.border_subtle};
}}
QStatusBar {{
    background: {t.bg_header};
    color: {t.text_dim};
    font-size: 11px;
    border-top: 1px solid {t.border_subtle};
}}
QMenuBar {{
    background: {t.bg_root};
    color: {t.text};
    border-bottom: 1px solid {t.border_subtle};
    padding: 2px 4px;
}}
QMenuBar::item:selected {{ background: {t.bg_input}; border-radius: 4px; }}
QMenu {{
    background: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 4px;
    color: {t.text};
}}
QMenu::item:selected {{ background: {t.selection}; border-radius: 4px; }}
QMenu::separator {{ height: 1px; background: {t.border}; margin: 4px 0; }}
"""


def stylesheet_tab_panel(t: ThemeTokens) -> str:
    ff = _font_family(t)
    input_border = t.border
    btn_hover = t.bg_elevated
    if t.medieval:
        p = get_palette()
        input_border = p.wood_frame
        btn_hover = p.parchment_light

    return f"""
QWidget {{
    background: {t.bg_window};
    color: {t.text};
    font-family: {ff};
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background: {t.bg_input};
    border: 1px solid {input_border};
    border-radius: 6px;
    padding: 6px 10px;
    color: {t.text};
}}
QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {t.accent};
}}
QTextEdit {{
    background: {t.bg_elevated};
    border: 1px solid {input_border};
    border-radius: 8px;
    color: {t.text};
    padding: 4px;
}}
QGroupBox {{
    border: 1px solid {input_border};
    border-radius: 8px;
    margin-top: 10px;
    padding: 12px 10px 10px 10px;
}}
QGroupBox::title {{
    color: {t.text_title};
    padding: 0 8px;
    font-size: 11px;
    letter-spacing: 1px;
    font-weight: bold;
}}
QPushButton {{
    background: {t.bg_input};
    border: 1px solid {input_border};
    border-radius: 6px;
    padding: 7px 16px;
    color: {t.text};
    font-weight: {"bold" if t.medieval else "normal"};
}}
QPushButton:hover {{
    background: {btn_hover};
    border-color: {t.accent};
    color: {t.text_title if t.medieval else t.text};
}}
QCheckBox {{ color: {t.text}; spacing: 8px; }}
QSlider::groove:horizontal {{
    background: {t.border};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {t.accent};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{ background: {t.accent}; border-radius: 3px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {t.bg_input};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {t.border};
    border-radius: 5px;
    min-height: 24px;
}}
"""


def stylesheet_table(t: ThemeTokens) -> str:
    return f"""
QTableWidget {{
    background: {t.bg_elevated};
    border: 1px solid {t.border};
    gridline-color: {t.bg_input};
    border-radius: 6px;
}}
QTableWidget::item {{ padding: 6px 8px; }}
QTableWidget::item:selected {{ background: {t.selection}; }}
QTableWidget::item:alternate {{ background: {t.bg_elevated}; }}
QHeaderView::section {{
    background: {t.bg_input};
    color: {t.text_dim};
    border: none;
    padding: 6px 8px;
    font-size: 11px;
    letter-spacing: 1px;
}}
"""


def stylesheet_header_bar(t: ThemeTokens) -> str:
    border = wood_frame_border(get_palette()) if t.medieval else t.border_subtle
    bg = get_palette().parchment_dark if t.medieval else t.bg_header
    return f"""
QFrame {{
    background: {bg};
    border-bottom: 2px solid {border if t.medieval else t.border_subtle};
}}
"""


def stylesheet_overlay_toggle(t: ThemeTokens) -> str:
    return f"""
QPushButton {{
    background: {t.accent_soft};
    color: {t.accent};
    border: 1px solid {t.accent_muted};
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}}
QPushButton:checked {{
    background: {t.selection};
    border-color: {t.accent};
    color: {t.text_title};
}}
QPushButton:hover {{ background: {t.selection}; }}
"""


def stylesheet_primary_button(t: ThemeTokens) -> str:
    return f"""
QPushButton {{
    background: {t.selection};
    color: {t.text_title};
    border: 2px solid {t.accent};
    border-radius: 10px;
    padding: 14px 24px;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 0.5px;
}}
QPushButton:hover {{ background: {t.accent_soft}; border-color: {t.accent}; }}
"""


def stylesheet_quick_start_primary(t: ThemeTokens) -> str:
    return f"""
QPushButton#primary {{
    background: {t.selection};
    color: {t.text_title};
    border: 2px solid {t.accent};
    border-radius: 10px;
    padding: 16px 28px;
    font-size: 15px;
    font-weight: bold;
}}
QPushButton#primary:hover {{ background: {t.accent_soft}; }}
QPushButton#secondary {{
    background: {t.bg_input};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 10px;
    padding: 14px 24px;
    font-size: 13px;
}}
QPushButton#secondary:hover {{ border-color: {t.accent}; }}
QComboBox {{
    background: {t.bg_input};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 10px 12px;
    color: {t.text};
    font-size: 13px;
}}
"""


def apply_main_window(widget) -> ThemeTokens:
    t = get_tokens()
    widget.setStyleSheet(stylesheet_main_window(t))
    return t


def apply_tab_panel(widget) -> ThemeTokens:
    t = get_tokens()
    widget.setStyleSheet(stylesheet_tab_panel(t))
    return t


def apply_tab_with_table(widget) -> ThemeTokens:
    t = get_tokens()
    widget.setStyleSheet(stylesheet_tab_panel(t) + stylesheet_table(t))
    return t
