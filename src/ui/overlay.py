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
    QSizeGrip, QFrame, QProgressBar, QTabWidget, QGridLayout,
)

from ..build_orders.models import BuildOrder, BuildStep
from ..build_orders.step_timer import compute_step_timing
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
NEXT_ACCENT = "#2ecc71"


def _rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert #RRGGBB to rgba(...) CSS string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


class StepTimingBar(QFrame):
    """Progress bar showing time remaining to hit the ideal step deadline."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.lbl_timing = QLabel("Step timer")
        self.lbl_timing.setStyleSheet(f"color: {DIM_COLOR}; font-size: 10px;")
        layout.addWidget(self.lbl_timing)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        self.bar.setStyleSheet("""
            QProgressBar { background: #1a1a20; border: 1px solid #2c2c2e; border-radius: 4px; }
            QProgressBar::chunk { background: #3498db; border-radius: 3px; }
        """)
        layout.addWidget(self.bar)

    def update_timing(self, progress: float, status: str, message: str) -> None:
        color = STATUS_COLORS.get(status, STATUS_COLORS["neutral"])
        self.bar.setValue(int(progress))
        self.bar.setStyleSheet(f"""
            QProgressBar {{ background: #1a1a20; border: 1px solid #2c2c2e; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}
        """)
        self.lbl_timing.setText(message)
        self.lbl_timing.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")


class ResourcePanel(QFrame):
    """Large resource target display for the current step."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            ResourcePanel {{
                background: #16161a;
                border: 1px solid #2c2c2e;
                border-radius: 8px;
            }}
        """)
        grid = QGridLayout(self)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(8)

        self._cells: dict[str, QLabel] = {}
        specs = [
            ("pop", "POP", "#e67e22", 0, 0),
            ("food", "FOOD", "#2ecc71", 0, 1),
            ("wood", "WOOD", "#d4a574", 1, 0),
            ("gold", "GOLD", "#f1c40f", 1, 1),
            ("stone", "STONE", "#95a5a6", 2, 0),
        ]
        for key, title, color, row, col in specs:
            box = QVBoxLayout()
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet(f"color: {DIM_COLOR}; font-size: 9px; font-weight: bold;")
            lbl_v = QLabel("—")
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
            box.addWidget(lbl_t)
            box.addWidget(lbl_v)
            w = QFrame()
            w.setLayout(box)
            w.setStyleSheet(f"background: #1a1a20; border-radius: 6px; padding: 4px;")
            grid.addWidget(w, row, col)
            self._cells[key] = lbl_v

        self.lbl_hint = QLabel("Targets for the current step")
        self.lbl_hint.setStyleSheet(f"color: {DIM_COLOR}; font-size: 10px;")
        self.lbl_hint.setWordWrap(True)
        grid.addWidget(self.lbl_hint, 2, 1)

    def set_step(self, step: Optional[BuildStep]) -> None:
        if not step:
            for lbl in self._cells.values():
                lbl.setText("—")
            self.lbl_hint.setText("Load a build order to see targets.")
            return

        self._cells["pop"].setText(str(step.population) if step.population else "—")
        self._cells["food"].setText(str(step.food) if step.food is not None else "—")
        self._cells["wood"].setText(str(step.wood) if step.wood is not None else "—")
        self._cells["gold"].setText(str(step.gold) if step.gold is not None else "—")
        self._cells["stone"].setText(str(step.stone) if step.stone is not None else "—")
        self.lbl_hint.setText(step.notes or step.description)


class NextStepBanner(QFrame):
    """Eye-catching preview of the upcoming step."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            NextStepBanner {{
                background: rgba(46, 204, 113, 0.12);
                border: 2px solid {NEXT_ACCENT};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        row = QHBoxLayout()
        self.lbl_tag = QLabel("NEXT")
        self.lbl_tag.setStyleSheet(
            f"color: {NEXT_ACCENT}; font-size: 11px; font-weight: bold; letter-spacing: 2px;"
        )
        self.lbl_time = QLabel("")
        self.lbl_time.setStyleSheet(f"color: {NEXT_ACCENT}; font-size: 10px;")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.lbl_tag)
        row.addStretch()
        row.addWidget(self.lbl_time)
        layout.addLayout(row)

        self.lbl_desc = QLabel("—")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet(
            f"color: #ecf0f1; font-size: 12px; font-weight: bold;"
        )
        layout.addWidget(self.lbl_desc)

    def set_step(self, step: Optional[BuildStep]) -> None:
        if not step:
            self.lbl_desc.setText("Final step — you're done!")
            self.lbl_time.setText("")
            return
        self.lbl_desc.setText(step.description)
        self.lbl_time.setText(step.time_str or "")


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
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        self.lbl_index = QLabel("NOW")
        self.lbl_index.setStyleSheet(
            f"color: {ACCENT}; font-weight: bold; font-size: 11px; letter-spacing: 2px;"
        )
        self.lbl_time = QLabel("")
        self.lbl_time.setStyleSheet(f"color: {ACCENT}; font-size: 11px; font-weight: bold;")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_pop = QLabel("")
        self.lbl_pop.setStyleSheet(f"color: #e67e22; font-size: 11px; font-weight: bold;")
        header_row.addWidget(self.lbl_index)
        header_row.addWidget(self.lbl_pop)
        header_row.addStretch()
        header_row.addWidget(self.lbl_time)
        layout.addLayout(header_row)

        self.lbl_desc = QLabel("")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet(
            f"color: {TEXT_COLOR}; font-size: 15px; font-weight: bold; line-height: 1.3;"
        )
        layout.addWidget(self.lbl_desc)

        self.lbl_resources = QLabel("")
        self.lbl_resources.setStyleSheet(f"color: {DIM_COLOR}; font-size: 10px;")
        layout.addWidget(self.lbl_resources)

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
        session_started:   Overlay step timer started.
        session_stopped:   Overlay closed or timer stopped.
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
        self._timer_paused = False
        self._manual_pause = False
        self._stall_samples = 0
        self._last_screen_hash: Optional[int] = None
        self._elapsed_sec = 0
        self._drag_start: Optional[QPoint] = None

        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)

        self._game_sync = QTimer(self)
        self._game_sync.setInterval(1000)
        self._game_sync.timeout.connect(self._check_game_pause)

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
        self.setMinimumWidth(260)
        self.setMinimumHeight(180)
        w, h = settings.overlay_size
        self.resize(min(w, 320), min(h, 400))

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
        inner.setContentsMargins(8, 6, 8, 6)
        inner.setSpacing(4)

        title_row = QHBoxLayout()
        self.lbl_title = QLabel("TRINKER")
        self.lbl_title.setStyleSheet(
            f"color: {ACCENT}; font-size: 10px; font-weight: bold; letter-spacing: 2px;"
        )
        self.lbl_bo_name = QLabel("No build")
        self.lbl_bo_name.setStyleSheet(f"color: {DIM_COLOR}; font-size: 10px;")
        self.lbl_paused = QLabel("")
        self.lbl_paused.setStyleSheet(
            "color: #f1c40f; font-size: 9px; font-weight: bold; letter-spacing: 1px;"
        )
        self.lbl_progress = QLabel("")
        self.lbl_progress.setStyleSheet(f"color: {DIM_COLOR}; font-size: 10px;")
        self.btn_close = QPushButton("x")
        self.btn_close.setFixedSize(18, 18)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {DIM_COLOR}; border: none; font-size: 12px; }}
            QPushButton:hover {{ color: #e74c3c; }}
        """)
        self.btn_close.clicked.connect(self.close)
        title_row.addWidget(self.lbl_title)
        title_row.addWidget(self.lbl_bo_name)
        title_row.addStretch()
        title_row.addWidget(self.lbl_paused)
        title_row.addWidget(self.lbl_progress)
        title_row.addWidget(self.btn_close)
        inner.addLayout(title_row)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab {
                background: #1a1a20; color: #7f8c8d; padding: 4px 10px;
                margin-right: 2px; border-radius: 4px; font-size: 10px;
            }
            QTabBar::tab:selected { color: #3498db; background: #25252c; }
        """)

        # Tab: Steps (default view)
        tab_steps = QWidget()
        steps_layout = QVBoxLayout(tab_steps)
        steps_layout.setContentsMargins(4, 6, 4, 4)
        steps_layout.setSpacing(6)
        self.current_card = StepCard(is_current=True, parent=self)
        steps_layout.addWidget(self.current_card)
        self.step_timing_bar = StepTimingBar(parent=self)
        steps_layout.addWidget(self.step_timing_bar)
        self.next_banner = NextStepBanner(parent=self)
        steps_layout.addWidget(self.next_banner)
        nav_row = QHBoxLayout()
        nav_row.setSpacing(4)
        self.btn_prev = self._nav_button("Prev", small=True)
        self.btn_prev.clicked.connect(self.prev_step)
        self.btn_next = self._nav_button("Next", small=True)
        self.btn_next.clicked.connect(self.next_step)
        nav_row.addWidget(self.btn_prev)
        nav_row.addWidget(self.btn_next)
        steps_layout.addLayout(nav_row)
        self.tabs.addTab(tab_steps, "Steps")

        # Tab: Resources
        tab_res = QWidget()
        res_layout = QVBoxLayout(tab_res)
        res_layout.setContentsMargins(4, 6, 4, 4)
        self.resource_panel = ResourcePanel(parent=self)
        res_layout.addWidget(self.resource_panel)
        self.tabs.addTab(tab_res, "Resources")

        # Tab: Coach / tips
        tab_tip = QWidget()
        tip_layout = QVBoxLayout(tab_tip)
        tip_layout.setContentsMargins(4, 6, 4, 4)
        self.lbl_coach_alert = QLabel("")
        self.lbl_coach_alert.setWordWrap(True)
        self.lbl_coach_alert.setStyleSheet(
            "color: #f1c40f; font-size: 11px; font-weight: bold; "
            "background: rgba(241,196,15,0.12); border-radius: 6px; padding: 8px;"
        )
        self.lbl_coach_alert.setVisible(False)
        tip_layout.addWidget(self.lbl_coach_alert)
        self.lbl_tip = QLabel("Step tips appear here while you play.")
        self.lbl_tip.setWordWrap(True)
        self.lbl_tip.setStyleSheet(f"color: {DIM_COLOR}; font-size: 11px; padding: 4px;")
        tip_layout.addWidget(self.lbl_tip)
        tip_layout.addStretch()
        self.tabs.addTab(tab_tip, "Tips")

        inner.addWidget(self.tabs)

        grip_row = QHBoxLayout()
        grip_row.addStretch()
        grip = QSizeGrip(self)
        grip.setStyleSheet("color: #3c3c3e;")
        grip_row.addWidget(grip)
        inner.addLayout(grip_row)

        self.lbl_status = QLabel("")
        self.lbl_status.setVisible(False)

    def _nav_button(self, text: str, color: str = ACCENT, *, small: bool = False) -> QPushButton:
        btn = QPushButton(text)
        pad = "4px 8px" if small else "5px 10px"
        fs = "10px" if small else "11px"
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {_rgba(color, 0.15)};
                color: {color};
                border: 1px solid {_rgba(color, 0.4)};
                border-radius: 6px;
                padding: {pad};
                font-size: {fs};
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {_rgba(color, 0.25)}; }}
        """)
        return btn

    # ── Public API ────────────────────────────────────────────────────────────

    def load_build_order(self, bo: BuildOrder) -> None:
        """Load a build order into the overlay and reset to step 0."""
        self._build_order = bo
        self._current_index = 0
        self.lbl_bo_name.setText(f"{bo.name} ({bo.civ})")
        self._refresh_steps()
        self._show_coach_alert(bo)
        self._auto_start_timer()
        logger.info("Overlay loaded: '%s'", bo.name)

    def _auto_start_timer(self) -> None:
        """Timer starts automatically — no manual session button."""
        if self._is_session_active:
            return
        self._is_session_active = True
        self._timer_paused = False
        self._manual_pause = False
        self._stall_samples = 0
        self._last_screen_hash = None
        self._elapsed_sec = 0
        self._tick.start()
        if settings.overlay_sync_game_pause:
            self._game_sync.start()
        self._update_pause_label()
        self.session_started.emit()

    def toggle_timer_pause(self) -> bool:
        """Toggle manual pause. Returns True if timer is now paused."""
        self._manual_pause = not self._manual_pause
        self._set_timer_paused(self._manual_pause, manual=True)
        return self._timer_paused

    def _set_timer_paused(self, paused: bool, *, manual: bool = False) -> None:
        if manual:
            self._timer_paused = paused
        elif not self._manual_pause:
            self._timer_paused = paused
        self._update_pause_label()

    def _update_pause_label(self) -> None:
        if self._timer_paused:
            hint = "PAUSED"
            if self._manual_pause:
                hint += " (manual)"
            self.lbl_paused.setText(hint)
        else:
            self.lbl_paused.setText("")

    def _check_game_pause(self) -> None:
        if not self._is_session_active or self._manual_pause:
            return
        from ..capture.game_watcher import is_aoe2_foreground, sample_clock_region

        if not is_aoe2_foreground():
            self._set_timer_paused(True)
            return

        screen_hash = sample_clock_region()
        if screen_hash is None:
            return

        if screen_hash == self._last_screen_hash:
            self._stall_samples += 1
            if self._stall_samples >= 2:
                self._set_timer_paused(True)
        else:
            self._stall_samples = 0
            self._last_screen_hash = screen_hash
            self._set_timer_paused(False)

    def _show_coach_alert(self, bo: BuildOrder) -> None:
        """Display pinned post-game coaching alert if it matches this build."""
        alert = settings.overlay_coach_alert.strip()
        bo_id = settings.overlay_coach_alert_bo_id
        if not alert:
            self.lbl_coach_alert.setVisible(False)
            return
        if bo_id and bo.id and bo_id != bo.id:
            self.lbl_coach_alert.setVisible(False)
            return
        self.lbl_coach_alert.setText(f"⚠ NEXT GAME: {alert}")
        self.lbl_coach_alert.setVisible(True)

    def clear_coach_alert(self) -> None:
        settings.overlay_coach_alert = ""
        settings.overlay_coach_alert_bo_id = None
        settings.save()
        self.lbl_coach_alert.setVisible(False)

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
        self._elapsed_sec = elapsed_sec
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

        self._update_step_timing_bar()

    def _update_step_timing_bar(self) -> None:
        if not self._build_order:
            return
        state = compute_step_timing(self._build_order, self._current_index, self._elapsed_sec)
        self.step_timing_bar.update_timing(state.progress_pct, state.status, state.message)
        if self._is_session_active:
            self.set_status(state.status, state.message)

    def _on_tick(self) -> None:
        if self._is_session_active and not self._timer_paused:
            self._elapsed_sec += 1
            self.sync_to_elapsed(self._elapsed_sec)

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
            self.next_banner.set_step(None)
            self.resource_panel.set_step(None)
            self.lbl_progress.setText("")
            return

        steps = self._build_order.steps
        total = len(steps)
        current = steps[self._current_index] if self._current_index < total else None
        nxt = steps[self._current_index + 1] if self._current_index + 1 < total else None

        self.current_card.set_step(current, label="NOW")
        self.next_banner.set_step(nxt)
        self.resource_panel.set_step(current)
        if current and current.notes:
            self.lbl_tip.setText(current.notes)
        self.lbl_progress.setText(f"{self._current_index + 1}/{total}")
        self._update_step_timing_bar()

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
        if self._is_session_active:
            self._is_session_active = False
            self._tick.stop()
            self._game_sync.stop()
            self.session_stopped.emit()
        settings.save()
        self.closed.emit()
        super().closeEvent(event)
