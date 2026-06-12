"""
TRINKER 3.0 - Build order card widgets for Library grid view.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ..build_orders.models import BuildOrder
from .medieval.palette import get_palette


class BuildOrderCard(QFrame):
    """Compact card for one build order in grid view."""

    clicked = Signal(object)
    load_requested = Signal(object)

    def __init__(self, bo: BuildOrder, parent=None):
        super().__init__(parent)
        self._bo = bo
        p = get_palette()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"BuildOrderCard {{ background: {p.parchment_light}; "
            f"border: 2px solid {p.wood_frame}; border-radius: 10px; }}"
            f"BuildOrderCard:hover {{ border-color: {p.gold}; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        top = QHBoxLayout()
        star = "⭐" if bo.is_favorite else "📖"
        lbl_star = QLabel(star)
        lbl_name = QLabel(bo.name)
        lbl_name.setWordWrap(True)
        lbl_name.setStyleSheet(
            f"color: {p.gold_bright}; font-size: 13px; font-weight: bold;"
        )
        top.addWidget(lbl_star)
        top.addWidget(lbl_name, 1)
        layout.addLayout(top)

        meta = QLabel(f"{bo.civ}  ·  {bo.strategy or 'General'}")
        meta.setStyleSheet(f"color: {p.ink_dim}; font-size: 11px;")
        layout.addWidget(meta)

        steps = len(bo.steps)
        footer = QLabel(f"{steps} steps  ·  {bo.difficulty}")
        footer.setStyleSheet(f"color: {p.ink_muted}; font-size: 10px;")
        layout.addWidget(footer)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._bo)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.load_requested.emit(self._bo)
        super().mouseDoubleClickEvent(event)
