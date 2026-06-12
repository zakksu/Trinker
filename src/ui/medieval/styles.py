"""
QSS builders for medieval surfaces — gradients simulate parchment/wood textures.
"""

from __future__ import annotations

from .palette import MedievalPalette


def parchment_bg(p: MedievalPalette) -> str:
    return (
        f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 {p.parchment_light}, stop:0.4 {p.parchment}, stop:1 {p.parchment_dark})"
    )


def wood_frame_border(p: MedievalPalette) -> str:
    return (
        f"qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        f"stop:0 {p.wood_dark}, stop:0.5 {p.wood_frame}, stop:1 {p.wood_dark})"
    )


def stat_card_stylesheet(p: MedievalPalette, accent: str) -> str:
    bg = parchment_bg(p)
    return f"""
        QFrame {{
            background: {bg};
            border: 2px solid {p.wood_frame};
            border-top: 3px solid {accent};
            border-radius: 10px;
        }}
    """


def panel_stylesheet(p: MedievalPalette) -> str:
    bg = parchment_bg(p)
    return f"""
        QFrame#MedievalPanel {{
            background: {bg};
            border: 2px solid {p.wood_frame};
            border-radius: 12px;
        }}
        QLabel#PanelTitle {{
            color: {p.gold_bright};
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 2px;
        }}
        QLabel#PanelIcon {{
            color: {p.gold};
            font-size: 16px;
        }}
    """


def timeline_item_stylesheet(p: MedievalPalette, accent: str) -> str:
    return f"""
        QFrame#TimelineItem {{
            background: rgba(30, 24, 18, 0.6);
            border-left: 3px solid {accent};
            border-radius: 6px;
            padding: 2px;
        }}
        QLabel#TimelineTitle {{
            color: {p.ink};
            font-size: 12px;
            font-weight: bold;
        }}
        QLabel#TimelineSub {{
            color: {p.ink_dim};
            font-size: 11px;
        }}
        QLabel#TimelineIcon {{
            color: {accent};
            font-size: 14px;
            min-width: 20px;
        }}
    """


def section_header_stylesheet(p: MedievalPalette) -> str:
    """Steam artwork-inspired banner strip behind section titles."""
    return f"""
        QWidget#SectionHeader {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {p.parchment_dark}, stop:0.35 {p.wood_dark},
                stop:0.65 {p.parchment}, stop:1 {p.parchment_dark});
            border: 1px solid {p.wood_frame};
            border-left: 4px solid {p.gold};
            border-radius: 8px;
            padding: 4px;
        }}
        QLabel#SectionTitle {{
            color: {p.gold_bright};
            font-size: 26px;
            font-weight: bold;
            letter-spacing: 1px;
        }}
        QLabel#SectionSub {{
            color: {p.ink_dim};
            font-size: 12px;
        }}
        QLabel#SectionIcon {{
            color: {p.gold};
            font-size: 28px;
        }}
    """


def dialog_stylesheet(p: MedievalPalette) -> str:
    return f"""
        QDialog {{
            background: {p.wood_dark};
            border: 2px solid {p.wood_frame};
        }}
        QLabel {{
            color: {p.ink};
            font-size: 12px;
        }}
        QCheckBox {{
            color: {p.gold_bright};
            font-size: 12px;
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {p.gold};
            border-radius: 3px;
            background: {p.parchment_dark};
        }}
        QCheckBox::indicator:checked {{
            background: {p.gold};
        }}
        QDialogButtonBox QPushButton {{
            background: {p.parchment_dark};
            color: {p.gold_bright};
            border: 1px solid {p.wood_frame};
            border-radius: 6px;
            padding: 6px 16px;
            font-weight: bold;
        }}
        QDialogButtonBox QPushButton:hover {{
            background: {p.wood_frame};
        }}
    """


def overlay_container_stylesheet(p: MedievalPalette, alpha: float = 0.94) -> str:
    a = max(0.75, min(1.0, alpha))
    bg = f"rgba(22, 18, 14, {a:.2f})"
    return f"""
        QFrame#OverlayContainer {{
            background: {bg};
            border: 2px solid {p.wood_frame};
            border-top: 3px solid {p.gold};
            border-radius: 10px;
        }}
    """


def overlay_tab_stylesheet(p: MedievalPalette) -> str:
    return f"""
        QTabWidget::pane {{ border: none; background: transparent; }}
        QTabBar::tab {{
            background: {p.parchment_dark};
            color: {p.ink_muted};
            padding: 5px 12px;
            margin-right: 2px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        }}
        QTabBar::tab:selected {{
            color: {p.gold_bright};
            background: {p.parchment};
            border-bottom: 2px solid {p.gold};
        }}
        QTabBar::tab:hover:!selected {{
            color: {p.ink_dim};
        }}
    """
