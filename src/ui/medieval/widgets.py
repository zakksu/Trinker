"""
Reusable medieval-styled widgets for Dashboard and tabs.
"""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .animations import pulse_once
from .palette import get_palette
from .styles import (
    panel_stylesheet,
    section_header_stylesheet,
    stat_card_stylesheet,
    timeline_item_stylesheet,
)


class StatCard(QFrame):
    """Metric card with icon, value, and label — AoE2Insights-style stat tile."""

    def __init__(
        self,
        icon: str,
        title: str,
        value: str = "—",
        accent: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._accent = accent or get_palette().gold
        self._pulse_target = None
        self.setObjectName("StatCard")
        self.setStyleSheet(stat_card_stylesheet(get_palette(), self._accent))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(4)

        top = QHBoxLayout()
        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet(f"color: {self._accent}; font-size: 18px;")
        top.addWidget(self.lbl_icon)
        top.addStretch()
        layout.addLayout(top)

        self.lbl_val = QLabel(value)
        self.lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_val.setStyleSheet(
            f"color: {self._accent}; font-size: 28px; font-weight: bold; font-family: 'Consolas', monospace;"
        )
        layout.addWidget(self.lbl_val)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p = get_palette()
        self.lbl_title.setStyleSheet(
            f"color: {p.ink_dim}; font-size: 10px; letter-spacing: 1.5px; font-weight: bold;"
        )
        layout.addWidget(self.lbl_title)
        self._pulse_target = self.lbl_val

    def set_value(self, value: str, *, animate: bool = True) -> None:
        if self.lbl_val.text() != value and animate and self._pulse_target:
            pulse_once(self._pulse_target)
        self.lbl_val.setText(value)


class SectionHeader(QWidget):
    """Page title block with icon and subtitle."""

    def __init__(self, title: str, subtitle: str = "", icon: str = "", parent=None):
        super().__init__(parent)
        p = get_palette()
        self.setStyleSheet(section_header_stylesheet(p))

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 8)
        row.setSpacing(12)

        if icon:
            self.lbl_icon = QLabel(icon)
            self.lbl_icon.setObjectName("SectionIcon")
            row.addWidget(self.lbl_icon)

        col = QVBoxLayout()
        col.setSpacing(2)
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("SectionTitle")
        col.addWidget(self.lbl_title)
        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setObjectName("SectionSub")
        self.lbl_sub.setWordWrap(True)
        col.addWidget(self.lbl_sub)
        row.addLayout(col, 1)


class MedievalPanel(QFrame):
    """Framed content panel with gold title bar — replaces plain QGroupBox."""

    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("MedievalPanel")
        self.setStyleSheet(panel_stylesheet(get_palette()))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        if icon:
            lbl_i = QLabel(icon)
            lbl_i.setObjectName("PanelIcon")
            header.addWidget(lbl_i)
        lbl_t = QLabel(title.upper())
        lbl_t.setObjectName("PanelTitle")
        header.addWidget(lbl_t)
        header.addStretch()
        outer.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        outer.addLayout(self.body)

    def add_widget(self, widget: QWidget) -> None:
        self.body.addWidget(widget)

    def add_layout(self, layout) -> None:
        self.body.addLayout(layout)


class TimelineItem(QFrame):
    """Single row in a vertical activity timeline."""

    def __init__(
        self,
        icon: str,
        title: str,
        subtitle: str = "",
        accent: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        accent = accent or get_palette().gold
        self.setObjectName("TimelineItem")
        self.setStyleSheet(timeline_item_stylesheet(get_palette(), accent))

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)

        lbl_i = QLabel(icon)
        lbl_i.setObjectName("TimelineIcon")
        lbl_i.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.addWidget(lbl_i)

        col = QVBoxLayout()
        col.setSpacing(2)
        lbl_t = QLabel(title)
        lbl_t.setObjectName("TimelineTitle")
        lbl_t.setWordWrap(True)
        col.addWidget(lbl_t)
        if subtitle:
            lbl_s = QLabel(subtitle)
            lbl_s.setObjectName("TimelineSub")
            lbl_s.setWordWrap(True)
            col.addWidget(lbl_s)
        row.addLayout(col, 1)


class Timeline(QWidget):
    """Vertical list of timeline items."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def add_item(
        self,
        icon: str,
        title: str,
        subtitle: str = "",
        accent: str | None = None,
    ) -> TimelineItem:
        item = TimelineItem(icon, title, subtitle, accent, self)
        self._layout.addWidget(item)
        return item


class BadgeChip(QLabel):
    """Small achievement pill for header / dashboard."""

    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        p = get_palette()
        self.setStyleSheet(
            f"color: {p.gold_bright}; background: rgba(201,162,39,0.14); "
            f"border: 1px solid {p.gold_dim}; border-radius: 10px; "
            f"padding: 4px 10px; font-size: 10px; font-weight: bold; letter-spacing: 0.5px;"
        )


class ActivityHeatmap(QWidget):
    """GitHub-style text heatmap of practice days."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lbl = QLabel("No practice data yet.")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._lbl)

    def set_data(self, data: dict[str, int], accent: str | None = None) -> None:
        p = get_palette()
        color = accent or p.gold
        if not data:
            self._lbl.setText("No practice data yet — play with the overlay on.")
            self._lbl.setStyleSheet(f"color: {p.ink_dim}; font-size: 12px;")
            return

        today = date.today()
        lines = []
        for week_offset in range(16, -1, -1):
            week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=week_offset)
            week_str = ""
            for d in range(7):
                day = week_start + timedelta(days=d)
                cnt = data.get(day.isoformat(), 0)
                if cnt == 0:
                    char = "░"
                elif cnt == 1:
                    char = "▒"
                elif cnt <= 3:
                    char = "▓"
                else:
                    char = "█"
                week_str += char
            lines.append(week_str)

        heatmap_text = "  ".join(lines)
        self._lbl.setText(
            f"<pre style='color: {color}; font-size: 13px; letter-spacing: 2px;'>{heatmap_text}</pre>"
        )
        self._lbl.setTextFormat(Qt.TextFormat.RichText)


class CompareDiffTable(QFrame):
    """Side-by-side target vs actual timing comparison."""

    _STATUS_COLORS = {
        "green": "#6aab55",
        "yellow": "#d4a017",
        "red": "#b54a4a",
        "neutral": "#7a6f5c",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        p = get_palette()
        self.setStyleSheet(
            "QFrame { background: rgba(30,24,18,0.45); border-radius: 8px; padding: 4px; }"
        )
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(8, 8, 8, 8)
        self._grid.setSpacing(6)
        for col, title in enumerate(["Milestone", "Target", "Actual", "Status"]):
            hdr = QLabel(title.upper())
            hdr.setStyleSheet(
                f"color: {p.ink_muted}; font-size: 9px; font-weight: bold; letter-spacing: 1px;"
            )
            self._grid.addWidget(hdr, 0, col)

    def clear_rows(self) -> None:
        while self._grid.count() > 4:
            item = self._grid.takeAt(4)
            w = item.widget()
            if w:
                w.deleteLater()

    def set_rows(self, rows: list) -> None:
        """Populate from analytics.compare.CompareRow objects."""
        from .icons import Icon

        self.clear_rows()
        p = get_palette()
        if not rows:
            empty = QLabel("No timing data to compare yet.")
            empty.setStyleSheet(f"color: {p.ink_dim}; font-size: 11px;")
            self._grid.addWidget(empty, 1, 0, 1, 4)
            return

        for r_idx, row in enumerate(rows, start=1):
            accent = self._STATUS_COLORS.get(row.status, self._STATUS_COLORS["neutral"])
            cells = [
                row.label,
                row.target,
                row.actual,
                f"{Icon.status_glyph(row.status)} {row.detail or row.status}",
            ]
            for c_idx, text in enumerate(cells):
                lbl = QLabel(text)
                lbl.setWordWrap(True)
                style = f"color: {p.ink if c_idx < 3 else accent}; font-size: 11px;"
                if c_idx == 0:
                    style += " font-weight: bold;"
                lbl.setStyleSheet(style)
                self._grid.addWidget(lbl, r_idx, c_idx)
