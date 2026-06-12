"""
TRINKER 3.0 - Training Arena tab (drills + pinned coach goals).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..analytics.session import get_summary_stats
from ..core.config import settings
from ..training.drill_engine import list_drills, pin_drill, suggest_drill
from .medieval.icons import Icon
from .medieval.widgets import MedievalPanel, SectionHeader
from .notifications import show_toast
from .theme import apply_tab_panel, get_tokens


class TrainingTab(QWidget):
    """Practice drills — actionable goals between ranked games."""

    play_drill_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.apply_theme()
        self.refresh()

    def apply_theme(self, theme_name: str | None = None) -> None:
        apply_tab_panel(self)
        t = get_tokens(theme_name)
        if hasattr(self, "_header"):
            self._header.lbl_title.setStyleSheet(
                f"color: {t.text_title}; font-size: 26px; font-weight: bold;"
            )

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 24)
        root.setSpacing(16)

        self._header = SectionHeader(
            "Training Arena",
            "Structured drills — pin one goal and play three focused games.",
            Icon.OVERLAY,
        )
        root.addWidget(self._header)

        self.panel_suggested = MedievalPanel("Suggested Drill", Icon.COACH)
        self.lbl_suggested = QLabel("—")
        self.lbl_suggested.setWordWrap(True)
        self.panel_suggested.add_widget(self.lbl_suggested)
        btn_pin = QPushButton(f"{Icon.OVERLAY} Pin to Overlay")
        btn_pin.clicked.connect(self._pin_suggested)
        self.panel_suggested.add_widget(btn_pin)
        root.addWidget(self.panel_suggested)

        self.panel_pinned = MedievalPanel("Pinned for Next Game", Icon.ASK)
        self.lbl_pinned = QLabel("No drill pinned.")
        self.lbl_pinned.setWordWrap(True)
        self.panel_pinned.add_widget(self.lbl_pinned)
        root.addWidget(self.panel_pinned)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        self._drill_layout = QVBoxLayout(container)
        self._drill_layout.setSpacing(8)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        self.cb_drill = QComboBox()
        for d in list_drills():
            self.cb_drill.addItem(d.title, d.id)
        pick_row = QHBoxLayout()
        pick_row.addWidget(QLabel("Manual drill:"))
        pick_row.addWidget(self.cb_drill, 1)
        btn_manual = QPushButton("Pin Selected")
        btn_manual.clicked.connect(self._pin_selected)
        pick_row.addWidget(btn_manual)
        root.addLayout(pick_row)

        btn_play = QPushButton(f"{Icon.GAME} Go to Start Here & Play")
        btn_play.clicked.connect(self.play_drill_requested.emit)
        root.addWidget(btn_play)

    def refresh(self) -> None:
        stats = get_summary_stats()
        drill = suggest_drill(
            feudal_sec=stats.get("avg_feudal_sec"),
            overlay_alert=settings.overlay_coach_alert,
            win_rate=float(stats.get("win_rate") or 0),
        )
        self.lbl_suggested.setText(
            f"<b>{drill.title}</b> ({drill.focus})<br><br>{drill.instructions}"
        )
        self.lbl_suggested.setTextFormat(Qt.TextFormat.RichText)

        if settings.overlay_coach_alert:
            self.lbl_pinned.setText(f"{Icon.OVERLAY}  {settings.overlay_coach_alert}")
        else:
            self.lbl_pinned.setText("No drill pinned — use Pin to Overlay above.")

        while self._drill_layout.count():
            item = self._drill_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for d in list_drills():
            lbl = QLabel(f"• {d.title} — {d.instructions}")
            lbl.setWordWrap(True)
            self._drill_layout.addWidget(lbl)
        self._drill_layout.addStretch()

    def _pin_suggested(self) -> None:
        stats = get_summary_stats()
        drill = suggest_drill(
            feudal_sec=stats.get("avg_feudal_sec"),
            overlay_alert=settings.overlay_coach_alert,
            win_rate=float(stats.get("win_rate") or 0),
        )
        pin_drill(drill)
        self.refresh()
        show_toast(f"Pinned: {drill.title}", "success")

    def _pin_selected(self) -> None:
        from ..training.drill_engine import get_drill

        drill = get_drill(self.cb_drill.currentData())
        if drill:
            pin_drill(drill)
            self.refresh()
            show_toast(f"Pinned: {drill.title}", "success")
