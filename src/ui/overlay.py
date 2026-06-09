"""
TRINKER - Transparent Build Order Overlay
A frameless, always-on-top, draggable transparent window that displays
the current build order step during practice.

Design goals:
  - Minimal screen footprint — shows only the current step + next step.
  - Draggable anywhere on screen without a title bar.
  - Opacity adjustable (default 0.88).
  - Keyboard hotkeys advance/retreat steps (registered in main window).
  - Traffic-light color status for resource/timing feedback.
"""

from typing import Optional

from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPalette, QKeySequence
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizeGrip, QFrame, QGraphicsOpacityEffect,
)

from ..build_orders.models import BuildOrder, BuildStep
from ..core.config import settings
from ..core.logger import logger


# ---------------------------------------------------------------------------
# Status colors (traffic-light system)
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "green":  "#2ecc71",
    "yellow": "#f1c40f",
    "red":    "#e74c3c",
    "neutral": "#95a5a6",
}

DARK_BG    = "rgba(18, 18, 20, {alpha})"
STEP_BG    = "#1e1e22"
TEXT_COLOR = "#ecf0f1"
DIM_COLOR  = "#7f8c8d"
ACCENT     = "#3498db"


def _rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert #RRGGBB to rgba(...) CSS string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


class StepCard(QFrame):
    """Displays one build step with index, timing, population, and description."""

    def __init__(self, is_current: bool = False, parent=None):
        super().__init__(parent)
        self.is_current = is_current
        self._setup_ui()

    def _setup_ui(self) -> None:
        border_color = ACCENT if self.is_current else "#2c2c2e"
        bg           = STEP_BG if self.is_current else "#16161a"
        self.setStyleSheet(f"""
            StepCard {{
                background: {bg};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Row 1: step number + time
        header_row = QHBoxLayout()
        self.lbl_index = QLabel("─")
        self.lbl_index.setStyleSheet(f"color: {ACCENT if self.is_current else DIM_COLOR}; font-weight: bold; font-size: 11px;")

        self.lbl_time = QLabel("")
        self.lbl_time.setStyleSheet(f"color: {DIM_COLOR}; font-size: 10px;")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.lbl_pop = QLabel("")
        self.lbl_pop.setStyleSheet(f"color: #e67e22; font-size: 10px; font-weight: bold;")

        header_row.addWidget(self.lbl_index)
        header_row.addStretch()
        header_row.addWidget(self.lbl_pop)
        header_row.addWidget(self.lbl_time)
        layout.addLayout(header_row)

        # Row 2: description
        self.lbl_desc = QLabel("")
        self.lbl_desc.setWordWrap(True)
        font_size = 13 if self.is_current else 11
        weight = "bold" if self.is_current else "normal"
        self.lbl_desc.setStyleSheet(f"color: {TEXT_COLOR}; font-size: {font_size}px; font-weight: {weight};")
        layout.addWidget(self.lbl_desc)

        # Row 3: resources (optional)
        self.lbl_resources = QLabel("")
        self.lbl_resources.setStyleSheet(f"color: {DIM_COLOR}; font-size: 10px;")
        layout.addWidget(self.lbl_resources)

        # Row 4: notes (optional)
        self.lbl_notes = QLabel("")
        self.lbl_notes.setWordWrap(True)
        self.lbl_notes.setStyleSheet(f"color: {DIM_COLOR}; font-size: 10px; font-style: italic;")
        layout.addWidget(self.lbl_notes)

    def set_step(self, step: Optional[BuildStep], label: str = "") -> None:
        if step is None:
            self.lbl_index.setText(label or "—")
            self.lbl_desc.setText("No more steps")
            self.lbl_time.setText("")
            self.lbl_pop.setText("")
            self.lbl_resources.setText("")
            self.lbl_notes.setText("")
            return

        self.lbl_index.setText(f"#{step.index}" if not label else label)
        self.lbl_desc.setText(step.description)
        self.lbl_time.setText(step.time_str if step.time_str else "")
        self.lbl_pop.setText(f"👥 {step.population}" if step.population else "")

        res_parts = []
        if step.food  is not None: res_parts.append(f"🌾{step.food}")
        if step.wood  is not None: res_parts.append(f"🪵{step.wood}")
        if step.gold  is not None: res_parts.append(f"🪙{step.gold}")
        if step.stone is not None: res_parts.append(f"🪨{step.stone}")
        self.lbl_resources.setText("  ".join(res_parts))
        self.lbl_resources.setVisible(bool(res_parts))

        self.lbl_notes.setText(step.notes)
        self.lbl_notes.setVisible(bool(step.notes))

        if step.age:
            age_colors = {
                "feudal": "#e67e22", "castle": "#9b59b6",
                "imperial": "#e74c3c", "dark": "#7f8c8d",
            }
            color = age_colors.get(step.age.lower(), ACCENT)
            self.lbl_index.setText(f"▶ {step.age.upper()} AGE")
            self.lbl_index.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")

    def set_status(self, status: str = "neutral") -> None:
        """Update left border color based on timing status."""
        color = STATUS_COLORS.get(status, STATUS_COLORS["neutral"])
        self.setStyleSheet(self.styleSheet().replace(
            f"border: 1px solid {ACCENT}",
            f"border-left: 3px solid {color}",
        ))


class BuildOrderOverlay(QWidget):
    """
    The always-on-top transparent overlay window.

    Signals:
        step_changed(int): Emitted when step index changes (0-based).
        session_started:   User clicked Start Session.
        session_stopped:   User clicked Stop Session.
        closed:            Window was closed.
    """

    step_changed    = Signal(int)
    session_started = Signal()
    session_stopped = Signal()
    closed          = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_order: Optional[BuildOrder] = None
        self._current_index = 0          # 0-based index into steps list
        self._is_session_active = False
        self._drag_start: Optional[QPoint] = None

        self._setup_window()
        self._setup_ui()
        self._apply_opacity()
        self._restore_position()

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(340)
        self.setMinimumHeight(200)
        w, h = settings.overlay_size
        self.resize(w, h)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Container frame (gets background color) ────────────────────────
        self.container = QFrame(self)
        self.container.setStyleSheet(f"""
            QFrame {{
                background: rgba(14, 14, 16, 0.92);
                border: 1px solid #2c2c2e;
                border-radius: 12px;
            }}
        """)
        root.addWidget(self.container)

        inner = QVBoxLayout(self.container)
        inner.setContentsMargins(12, 10, 12, 10)
        inner.setSpacing(8)

        # ── Title bar row ─────────────────────────────────────────────────
        title_row = QHBoxLayout()
        self.lbl_title = QLabel("TRINKER")
        self.lbl_title.setStyleSheet(f"color: {ACCENT}; font-size: 12px; font-weight: bold; letter-spacing: 2px;")

        self.lbl_bo_name = QLabel("No build order")
        self.lbl_bo_name.setStyleSheet(f"color: {DIM_COLOR}; font-size: 11px;")

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {DIM_COLOR}; border: none; font-size: 13px; }}
            QPushButton:hover {{ color: #e74c3c; }}
        """)
        self.btn_close.clicked.connect(self.close)

        title_row.addWidget(self.lbl_title)
        title_row.addWidget(self.lbl_bo_name)
        title_row.addStretch()
        title_row.addWidget(self.btn_close)
        inner.addLayout(title_row)

        # ── Separator ─────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2c2c2e;")
        inner.addWidget(sep)

        # ── Current step card ─────────────────────────────────────────────
        self.current_card = StepCard(is_current=True, parent=self)
        inner.addWidget(self.current_card)

        # ── Next step card ────────────────────────────────────────────────
        self.next_card = StepCard(is_current=False, parent=self)
        inner.addWidget(self.next_card)

        # ── Status bar ────────────────────────────────────────────────────
        status_row = QHBoxLayout()
        self.lbl_status = QLabel("No active session")
        self.lbl_status.setStyleSheet(f"color: {DIM_COLOR}; font-size: 10px;")
        self.lbl_progress = QLabel("")
        self.lbl_progress.setStyleSheet(f"color: {DIM_COLOR}; font-size: 10px;")
        self.lbl_progress.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_row.addWidget(self.lbl_status)
        status_row.addStretch()
        status_row.addWidget(self.lbl_progress)
        inner.addLayout(status_row)

        # ── Navigation buttons ────────────────────────────────────────────
        nav_row = QHBoxLayout()
        nav_row.setSpacing(6)

        self.btn_prev = self._nav_button("◀ Prev")
        self.btn_prev.clicked.connect(self.prev_step)

        self.btn_session = self._nav_button("▶ Start Session", color="#2ecc71")
        self.btn_session.clicked.connect(self._toggle_session)

        self.btn_next = self._nav_button("Next ▶")
        self.btn_next.clicked.connect(self.next_step)

        nav_row.addWidget(self.btn_prev)
        nav_row.addWidget(self.btn_session)
        nav_row.addWidget(self.btn_next)
        inner.addLayout(nav_row)

        # ── Resize grip ───────────────────────────────────────────────────
        grip_row = QHBoxLayout()
        grip_row.addStretch()
        grip = QSizeGrip(self)
        grip.setStyleSheet("color: #3c3c3e;")
        grip_row.addWidget(grip)
        inner.addLayout(grip_row)

    def _nav_button(self, text: str, color: str = ACCENT) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {_rgba(color, 0.15)};
                color: {color};
                border: 1px solid {_rgba(color, 0.4)};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {_rgba(color, 0.25)};
            }}
            QPushButton:pressed {{
                background: {_rgba(color, 0.4)};
            }}
        """)
        return btn

    # ── Public API ────────────────────────────────────────────────────────────

    def load_build_order(self, bo: BuildOrder) -> None:
        """Load a build order into the overlay and reset to step 0."""
        self._build_order = bo
        self._current_index = 0
        self.lbl_bo_name.setText(f"{bo.name} ({bo.civ})")
        self._refresh_steps()
        logger.info("Overlay loaded: '%s'", bo.name)

    def next_step(self) -> None:
        """Advance to the next build step."""
        if self._build_order and self._current_index < len(self._build_order.steps) - 1:
            self._current_index += 1
            self._refresh_steps()
            self.step_changed.emit(self._current_index)

    def prev_step(self) -> None:
        """Go back to the previous build step."""
        if self._build_order and self._current_index > 0:
            self._current_index -= 1
            self._refresh_steps()
            self.step_changed.emit(self._current_index)

    def set_status(self, status: str, message: str = "") -> None:
        """Update the status indicator (green/yellow/red/neutral)."""
        color = STATUS_COLORS.get(status, STATUS_COLORS["neutral"])
        self.lbl_status.setText(message)
        self.lbl_status.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
        self.current_card.set_status(status)

    def set_opacity(self, opacity: float) -> None:
        """Update window opacity (0.0 – 1.0)."""
        self.setWindowOpacity(opacity)
        settings.overlay_opacity = opacity

    def sync_to_elapsed(self, elapsed_sec: int) -> None:
        """Advance to the build step that matches elapsed game time."""
        if not self._build_order or not self._build_order.steps:
            return

        best_idx = 0
        for i, step in enumerate(self._build_order.steps):
            if step.time_sec and step.time_sec <= elapsed_sec:
                best_idx = i

        if best_idx != self._current_index:
            self._current_index = best_idx
            self._refresh_steps()
            self.step_changed.emit(self._current_index)

    def get_current_step(self) -> Optional[BuildStep]:
        """Return the currently displayed step, or None."""
        if not self._build_order or not self._build_order.steps:
            return None
        if self._current_index < len(self._build_order.steps):
            return self._build_order.steps[self._current_index]
        return None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _refresh_steps(self) -> None:
        if not self._build_order or not self._build_order.steps:
            self.current_card.set_step(None)
            self.next_card.set_step(None)
            self.lbl_progress.setText("")
            return

        steps = self._build_order.steps
        total = len(steps)

        current = steps[self._current_index] if self._current_index < total else None
        nxt     = steps[self._current_index + 1] if self._current_index + 1 < total else None

        self.current_card.set_step(current, label="CURRENT")
        self.next_card.set_step(nxt, label="NEXT")
        self.lbl_progress.setText(f"{self._current_index + 1} / {total}")

    def _toggle_session(self) -> None:
        if self._is_session_active:
            self._is_session_active = False
            self.btn_session.setText("▶ Start Session")
            self.lbl_status.setText("Session stopped")
            self.session_stopped.emit()
        else:
            self._is_session_active = True
            self.btn_session.setText("⏹ Stop Session")
            self.lbl_status.setText("Session in progress…")
            self.session_started.emit()

    def _apply_opacity(self) -> None:
        self.setWindowOpacity(settings.overlay_opacity)

    def _restore_position(self) -> None:
        x, y = settings.overlay_position
        self.move(x, y)

    # ── Drag support (frameless window) ───────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_start
            self.move(new_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_start = None
        # Persist position
        pos = self.pos()
        settings.overlay_position = [pos.x(), pos.y()]
        settings.save()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        settings.overlay_size = [self.width(), self.height()]

    def closeEvent(self, event) -> None:
        settings.save()
        self.closed.emit()
        super().closeEvent(event)
