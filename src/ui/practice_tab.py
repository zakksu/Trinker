"""
TRINKER - Practice Tab
Live practice session interface with real-time timer, resource tracker,
milestone logging, performance feedback, and post-session review.
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QTextEdit, QGroupBox, QFormLayout, QFrame, QSplitter,
    QListWidget, QListWidgetItem, QMessageBox, QSpinBox, QDoubleSpinBox,
    QFileDialog, QDialog, QDialogButtonBox,
)

from ..analytics.session import Session, Milestone, save_session, get_summary_stats
from ..build_orders.manager import get_all_build_orders
from ..build_orders.models import BuildOrder
from ..build_orders.timings import (
    get_benchmarks_for, evaluate_feudal_time, evaluate_castle_time,
    calculate_accuracy_score,
)
from ..core.config import settings
from ..core.database import now_iso
from ..core.logger import logger

STYLE = """
QWidget { background: #111113; color: #ecf0f1; }
QLineEdit, QComboBox, QTextEdit, QSpinBox, QDoubleSpinBox {
    background: #1e1e22; border: 1px solid #2c2c2e;
    border-radius: 6px; padding: 5px 8px; color: #ecf0f1;
}
QPushButton {
    background: #1e1e22; border: 1px solid #2c2c2e;
    border-radius: 6px; padding: 6px 14px; color: #ecf0f1;
}
QPushButton:hover { background: #25252c; border-color: #3498db; }
QPushButton:disabled { color: #3c3c3e; border-color: #2c2c2e; }
QGroupBox {
    border: 1px solid #2c2c2e; border-radius: 8px; margin-top: 10px;
    padding: 10px 8px 8px 8px;
}
QGroupBox::title { color: #7f8c8d; padding: 0 8px; font-size: 11px; letter-spacing: 1px; }
QListWidget { background: #1a1a20; border: 1px solid #2c2c2e; border-radius: 6px; }
QListWidget::item { padding: 4px 8px; border-bottom: 1px solid #1e1e22; }
QListWidget::item:selected { background: #1c3a5c; }
"""

STATUS_STYLES = {
    "green":   "color: #2ecc71; font-weight: bold;",
    "yellow":  "color: #f1c40f; font-weight: bold;",
    "red":     "color: #e74c3c; font-weight: bold;",
    "neutral": "color: #95a5a6;",
}


def _sec_to_mmss(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


class _CoachingDialog(QDialog):
    """Non-blocking coaching review window with a scrollable text area."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Coach — Session Review")
        self.setMinimumSize(520, 360)
        self.setStyleSheet("""
            QDialog { background: #111113; color: #ecf0f1; }
            QTextEdit {
                background: #1a1a20; border: 1px solid #2c2c2e;
                border-radius: 6px; color: #ecf0f1; padding: 8px;
            }
            QPushButton {
                background: #1e1e22; border: 1px solid #2c2c2e;
                border-radius: 6px; padding: 6px 16px; color: #ecf0f1;
            }
            QPushButton:hover { background: #25252c; border-color: #3498db; }
            QPushButton:disabled { color: #555; }
        """)

        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlainText("Analyzing your session…")
        layout.addWidget(self.text)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.btn_close = self.buttons.button(QDialogButtonBox.StandardButton.Close)
        self.btn_close.setEnabled(False)
        self.buttons.rejected.connect(self.accept)
        layout.addWidget(self.buttons)

    def set_result(self, text: str) -> None:
        self.text.setPlainText(text)
        self.btn_close.setEnabled(True)


class _PostGameCoachWorker(QObject):
    finished = Signal(object)
    error    = Signal(str)

    def __init__(self, replay_path: str, civ: str, strategy: str, bo_id, bo_name: str):
        super().__init__()
        self.replay_path = replay_path
        self.civ = civ
        self.strategy = strategy
        self.bo_id = bo_id
        self.bo_name = bo_name

    def run(self) -> None:
        try:
            from ..ai_coach.postgame import run_postgame_coach
            result = run_postgame_coach(
                self.replay_path, self.civ, self.strategy,
                self.bo_id, self.bo_name,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class _CoachingWorker(QObject):
    finished = Signal(str)
    error    = Signal(str)

    def __init__(self, session, build_order: BuildOrder):
        super().__init__()
        self.session = session
        self.build_order = build_order

    def run(self) -> None:
        try:
            from ..ai_coach.coach import get_session_coaching
            result = get_session_coaching(
                build_order_name=self.build_order.name,
                civ=self.build_order.civ,
                feudal_time_sec=self.session.feudal_time_sec,
                castle_time_sec=self.session.castle_time_sec,
                accuracy_pct=self.session.accuracy_pct,
                notes=self.session.notes,
                mistakes=self.session.mistakes_json,
                result=self.session.result,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class TimerWidget(QFrame):
    """Large game timer display with start/stop/lap controls."""

    lapped = Signal(str, int)          # (label, elapsed_sec)
    elapsed_changed = Signal(int)      # emitted every second while running

    def __init__(self, parent=None):
        super().__init__(parent)
        self._start_time: Optional[float] = None
        self._elapsed: int = 0
        self._running = False

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        self.lbl_time = QLabel("0:00")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_time.setStyleSheet(
            "color: #ecf0f1; font-size: 56px; font-weight: bold; letter-spacing: 4px; font-family: monospace;"
        )
        layout.addWidget(self.lbl_time)

        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("▶ Start")
        self.btn_start.setStyleSheet("QPushButton { background: #1a4a2a; color: #2ecc71; border: 1px solid #2ecc71; border-radius: 6px; padding: 8px 20px; font-weight: bold; font-size: 13px; } QPushButton:hover { background: #2ecc71; color: #111; }")
        self.btn_start.clicked.connect(self.toggle)

        self.btn_reset = QPushButton("↺ Reset")
        self.btn_reset.setStyleSheet("QPushButton { background: #1e1e22; color: #7f8c8d; border: 1px solid #2c2c2e; border-radius: 6px; padding: 8px 16px; }")
        self.btn_reset.clicked.connect(self.reset)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_reset)
        layout.addLayout(btn_row)

    def toggle(self) -> None:
        if self._running:
            self.stop()
        else:
            self.start()

    def start(self) -> None:
        self._start_time = time.time() - self._elapsed
        self._running = True
        self._timer.start()
        self.btn_start.setText("⏸ Pause")
        self.btn_start.setStyleSheet("QPushButton { background: #4a3a1a; color: #f1c40f; border: 1px solid #f1c40f; border-radius: 6px; padding: 8px 20px; font-weight: bold; font-size: 13px; }")

    def stop(self) -> None:
        self._running = False
        self._timer.stop()
        if self._start_time:
            self._elapsed = int(time.time() - self._start_time)
        self.btn_start.setText("▶ Resume")
        self.btn_start.setStyleSheet("QPushButton { background: #1a4a2a; color: #2ecc71; border: 1px solid #2ecc71; border-radius: 6px; padding: 8px 20px; font-weight: bold; font-size: 13px; }")

    def reset(self) -> None:
        self._running = False
        self._timer.stop()
        self._elapsed = 0
        self._start_time = None
        self.lbl_time.setText("0:00")
        self.btn_start.setText("▶ Start")
        self.btn_start.setStyleSheet("QPushButton { background: #1a4a2a; color: #2ecc71; border: 1px solid #2ecc71; border-radius: 6px; padding: 8px 20px; font-weight: bold; font-size: 13px; } QPushButton:hover { background: #2ecc71; color: #111; }")

    def elapsed_sec(self) -> int:
        if self._running and self._start_time:
            return int(time.time() - self._start_time)
        return self._elapsed

    def _tick(self) -> None:
        if self._start_time:
            self._elapsed = int(time.time() - self._start_time)
        self.lbl_time.setText(_sec_to_mmss(self._elapsed))
        self.elapsed_changed.emit(self._elapsed)


class ResourceTracker(QGroupBox):
    """Manual resource input widget with performance feedback."""

    def __init__(self, parent=None):
        super().__init__("Resource Tracker", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setSpacing(6)

        self.sp_pop  = QSpinBox(); self.sp_pop.setRange(0, 500); self.sp_pop.setSuffix(" pop")
        self.sp_food = QSpinBox(); self.sp_food.setRange(0, 9999); self.sp_food.setSuffix(" 🌾")
        self.sp_wood = QSpinBox(); self.sp_wood.setRange(0, 9999); self.sp_wood.setSuffix(" 🪵")
        self.sp_gold = QSpinBox(); self.sp_gold.setRange(0, 9999); self.sp_gold.setSuffix(" 🪙")
        self.sp_stone= QSpinBox(); self.sp_stone.setRange(0, 9999); self.sp_stone.setSuffix(" 🪨")

        self.cb_age = QComboBox()
        self.cb_age.addItems(["Dark Age", "Feudal Age", "Castle Age", "Imperial Age"])

        layout.addRow("Population", self.sp_pop)
        layout.addRow("Current Age", self.cb_age)
        layout.addRow("Food", self.sp_food)
        layout.addRow("Wood", self.sp_wood)
        layout.addRow("Gold", self.sp_gold)
        layout.addRow("Stone", self.sp_stone)

    def snapshot(self) -> dict:
        return {
            "pop":   self.sp_pop.value(),
            "food":  self.sp_food.value(),
            "wood":  self.sp_wood.value(),
            "gold":  self.sp_gold.value(),
            "stone": self.sp_stone.value(),
            "age":   self.cb_age.currentText(),
        }


class PracticeTab(QWidget):
    """
    Full practice session interface.

    Features:
      - Build order selector
      - Game timer with start/pause/reset
      - Resource tracker with manual inputs
      - Milestone logger (Feudal click, Castle click, etc.)
      - Real-time performance feedback vs. benchmarks
      - Post-session notes and save
    """

    session_saved = Signal(object)   # emits the saved Session

    def __init__(self, overlay=None, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.setStyleSheet(STYLE)
        self._current_session: Optional[Session] = None
        self._session_start_wall: Optional[datetime] = None
        self._milestones: list[Milestone] = []
        self._steps_completed = 0
        self._selected_bo: Optional[BuildOrder] = None
        self._replay_path: Optional[str] = None
        self._replay_info = None
        self._replay_analysis = None
        self._coaching_thread = None
        self._coaching_worker = None
        self._postgame_thread = None
        self._postgame_worker = None
        self._setup_ui()
        self._load_build_orders()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        self.lbl_guidance = QLabel("")
        self.lbl_guidance.setWordWrap(True)
        self.lbl_guidance.setStyleSheet(
            "background: #1c3a5c; color: #a8d4ff; border: 1px solid #2c5a8c; "
            "border-radius: 8px; padding: 10px 14px; font-size: 12px;"
        )
        outer.addWidget(self.lbl_guidance)
        self._update_guidance()

        self.btn_toggle_advanced = QPushButton("Show all options ▾")
        self.btn_toggle_advanced.setStyleSheet(
            "QPushButton { color: #7f8c8d; border: none; text-align: left; padding: 4px 0; }"
            "QPushButton:hover { color: #3498db; }"
        )
        self.btn_toggle_advanced.clicked.connect(self._toggle_advanced)
        outer.addWidget(self.btn_toggle_advanced)

        content = QWidget()
        root = QHBoxLayout(content)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        outer.addWidget(content, stretch=1)

        # ── Left panel ────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(12)

        # Build order selector
        bo_group = QGroupBox("Build Order")
        bo_layout = QFormLayout(bo_group)
        self.cb_bo = QComboBox()
        self.cb_bo.setMinimumWidth(280)
        self.cb_bo.currentIndexChanged.connect(self._on_bo_changed)
        self.lbl_bo_info = QLabel("")
        self.lbl_bo_info.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        bo_layout.addRow("Select", self.cb_bo)
        bo_layout.addRow("", self.lbl_bo_info)
        left.addWidget(bo_group)

        # Timer
        timer_group = QGroupBox("Game Timer")
        timer_layout = QVBoxLayout(timer_group)
        self.timer_widget = TimerWidget()
        self.timer_widget.elapsed_changed.connect(self._on_timer_tick)
        timer_layout.addWidget(self.timer_widget)

        # Quick milestone buttons (advanced)
        self.quick_milestone_row = QWidget()
        quick_row = QHBoxLayout(self.quick_milestone_row)
        quick_row.setContentsMargins(0, 0, 0, 0)
        quick_row.setSpacing(6)
        for label in ["Clicked Feudal", "Clicked Castle", "Clicked Imperial", "Hit 100 Pop"]:
            btn = QPushButton(label)
            btn.setStyleSheet("QPushButton { font-size: 10px; padding: 4px 8px; }")
            btn.clicked.connect(lambda checked, l=label: self._log_milestone(l))
            quick_row.addWidget(btn)
        timer_layout.addWidget(self.quick_milestone_row)
        left.addWidget(timer_group)

        # Resource tracker (advanced)
        self.resource_tracker = ResourceTracker()
        left.addWidget(self.resource_tracker)

        # Replay sync
        self.replay_group = QGroupBox("Replay Sync")
        replay_group = self.replay_group
        replay_layout = QVBoxLayout(replay_group)
        replay_layout.setSpacing(6)

        self.lbl_replay_info = QLabel("No replay loaded")
        self.lbl_replay_info.setWordWrap(True)
        self.lbl_replay_info.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        replay_layout.addWidget(self.lbl_replay_info)

        replay_btn_row = QHBoxLayout()
        self.btn_import_last = QPushButton("Import Last Game")
        self.btn_import_last.setStyleSheet(
            "QPushButton { background: #1c3a5c; color: #3498db; border: 1px solid #2c5a8c; }"
        )
        self.btn_import_last.clicked.connect(self.import_last_replay)
        btn_browse_replay = QPushButton("Browse…")
        btn_browse_replay.clicked.connect(self._on_browse_replay)
        btn_clear_replay = QPushButton("Clear")
        btn_clear_replay.clicked.connect(self._on_clear_replay)
        replay_btn_row.addWidget(self.btn_import_last)
        replay_btn_row.addWidget(btn_browse_replay)
        replay_btn_row.addWidget(btn_clear_replay)
        replay_layout.addLayout(replay_btn_row)
        left.addWidget(replay_group)

        # Session control
        ctrl_group = QGroupBox("Session Control")
        ctrl_layout = QVBoxLayout(ctrl_group)
        ctrl_layout.setSpacing(8)

        result_row = QHBoxLayout()
        result_row.addWidget(QLabel("Result:"))
        self.cb_result = QComboBox()
        self.cb_result.addItems(["practice", "win", "loss", "draw"])
        result_row.addWidget(self.cb_result)
        result_row.addStretch()
        ctrl_layout.addLayout(result_row)

        self.ed_session_notes = QTextEdit()
        self.ed_session_notes.setPlaceholderText("Notes, mistakes, what went well…")
        self.ed_session_notes.setMaximumHeight(80)
        ctrl_layout.addWidget(self.ed_session_notes)

        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("💾 Save Session")
        self.btn_save.setStyleSheet("QPushButton { background: #1c3a5c; color: #3498db; border: 1px solid #2c5a8c; border-radius: 6px; padding: 8px 16px; font-weight: bold; }")
        self.btn_save.clicked.connect(self._on_save_session)
        btn_row.addWidget(self.btn_save)
        ctrl_layout.addLayout(btn_row)
        left.addWidget(ctrl_group)

        left.addStretch()
        root.addLayout(left, stretch=2)

        # ── Right panel (mostly advanced) ───────────────────────────────
        self.right_panel = QWidget()
        right = QVBoxLayout(self.right_panel)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(12)

        # Performance feedback
        self.feedback_group = QGroupBox("Performance Feedback")
        feedback_group = self.feedback_group
        feedback_layout = QVBoxLayout(feedback_group)

        self.lbl_feudal_status = QLabel("Feudal: —")
        self.lbl_feudal_status.setStyleSheet(STATUS_STYLES["neutral"])
        self.lbl_castle_status = QLabel("Castle: —")
        self.lbl_castle_status.setStyleSheet(STATUS_STYLES["neutral"])
        self.lbl_accuracy = QLabel("Accuracy: —")
        self.lbl_accuracy.setStyleSheet(STATUS_STYLES["neutral"])

        feedback_layout.addWidget(self.lbl_feudal_status)
        feedback_layout.addWidget(self.lbl_castle_status)
        feedback_layout.addWidget(self.lbl_accuracy)

        btn_eval = QPushButton("📊 Evaluate Now")
        btn_eval.clicked.connect(self._evaluate_performance)
        feedback_layout.addWidget(btn_eval)
        right.addWidget(feedback_group)

        # Milestone log
        self.milestone_group = QGroupBox("Milestone Log")
        milestone_group = self.milestone_group
        milestone_layout = QVBoxLayout(milestone_group)

        self.milestone_list = QListWidget()
        milestone_layout.addWidget(self.milestone_list)

        custom_row = QHBoxLayout()
        self.ed_milestone = QLineEdit()
        self.ed_milestone.setPlaceholderText("Custom milestone…")
        self.ed_milestone.returnPressed.connect(self._log_custom_milestone)
        btn_log = QPushButton("Log")
        btn_log.clicked.connect(self._log_custom_milestone)
        custom_row.addWidget(self.ed_milestone)
        custom_row.addWidget(btn_log)
        milestone_layout.addLayout(custom_row)
        right.addWidget(milestone_group)

        # Step counter
        self.steps_group = QGroupBox("Steps Completed")
        steps_group = self.steps_group
        steps_layout = QHBoxLayout(steps_group)
        self.sp_steps_done = QSpinBox()
        self.sp_steps_done.setRange(0, 200)
        self.lbl_total_steps = QLabel("/ 0 total")
        self.lbl_total_steps.setStyleSheet("color: #7f8c8d;")
        steps_layout.addWidget(self.sp_steps_done)
        steps_layout.addWidget(self.lbl_total_steps)
        steps_layout.addStretch()
        right.addWidget(steps_group)

        # Personal best
        self.pb_group = QGroupBox("Personal Bests")
        pb_group = self.pb_group
        pb_layout = QFormLayout(pb_group)
        self.lbl_pb_feudal = QLabel("—")
        self.lbl_pb_castle = QLabel("—")
        self.lbl_pb_accuracy = QLabel("—")
        pb_layout.addRow("Best Feudal:", self.lbl_pb_feudal)
        pb_layout.addRow("Best Castle:", self.lbl_pb_castle)
        pb_layout.addRow("Best Accuracy:", self.lbl_pb_accuracy)
        right.addWidget(pb_group)

        right.addStretch()
        root.addWidget(self.right_panel, stretch=1)

        self._advanced_visible = not settings.simple_mode
        self._apply_simple_mode()

    def _update_guidance(self) -> None:
        if settings.simple_mode:
            self.lbl_guidance.setText(
                "Simple mode — just pick a build, use the overlay, then Import Last Game. "
                "Everything else is optional."
            )
        else:
            self.lbl_guidance.setText(
                "Full mode — all trackers and logs are visible. "
                "Switch back in Settings if this feels like too much."
            )

    def _toggle_advanced(self) -> None:
        self._advanced_visible = not self._advanced_visible
        self._apply_simple_mode()

    def apply_simple_mode(self) -> None:
        """Called when settings change."""
        if settings.simple_mode:
            self._advanced_visible = False
        self._update_guidance()
        self._apply_simple_mode()

    def _apply_simple_mode(self) -> None:
        if settings.simple_mode:
            show_adv = self._advanced_visible
            self.btn_toggle_advanced.setVisible(True)
            self.btn_toggle_advanced.setText(
                "Hide extra options ▴" if show_adv else "Show all options ▾"
            )
        else:
            show_adv = True
            self.btn_toggle_advanced.setVisible(False)

        for w in (
            self.resource_tracker, self.quick_milestone_row,
            self.feedback_group, self.milestone_group, self.steps_group,
            self.pb_group, self.right_panel,
        ):
            w.setVisible(show_adv)
        self.replay_group.setVisible(True)

        # Session notes + save always visible in left column
        self.ed_session_notes.setVisible(True)
        self.btn_save.setVisible(True)

    # ── Data ──────────────────────────────────────────────────────────────

    def _load_build_orders(self) -> None:
        self.cb_bo.clear()
        self.cb_bo.addItem("— Select a build order —", None)
        for bo in get_all_build_orders():
            self.cb_bo.addItem(f"{bo.name} ({bo.civ})", bo.id)

    def refresh_build_orders(self) -> None:
        """Reload build order list (call after library changes)."""
        current_id = self.cb_bo.currentData()
        self._load_build_orders()
        if current_id:
            for i in range(self.cb_bo.count()):
                if self.cb_bo.itemData(i) == current_id:
                    self.cb_bo.setCurrentIndex(i)
                    break

    def set_overlay(self, overlay) -> None:
        """Attach the floating overlay so practice can sync steps."""
        self.overlay = overlay

    def load_build_order(self, bo: BuildOrder) -> None:
        """Pre-select a build order (called from overlay or library)."""
        self._selected_bo = bo
        for i in range(self.cb_bo.count()):
            if self.cb_bo.itemData(i) == bo.id:
                self.cb_bo.setCurrentIndex(i)
                break
        self.lbl_total_steps.setText(f"/ {bo.step_count} total")
        self._update_personal_bests()
        if bo.id:
            settings.last_practice_bo_id = bo.id
            settings.save()

    def load_build_order_by_id(self, bo_id) -> None:
        if bo_id is None:
            return
        from ..build_orders.manager import get_build_order
        bo = get_build_order(bo_id)
        if bo:
            self.load_build_order(bo)

    def _on_bo_changed(self) -> None:
        bo_id = self.cb_bo.currentData()
        if bo_id is None:
            self._selected_bo = None
            self.lbl_bo_info.setText("")
            self.lbl_total_steps.setText("/ 0 total")
            return
        bos = get_all_build_orders()
        self._selected_bo = next((b for b in bos if b.id == bo_id), None)
        if self._selected_bo:
            self.lbl_bo_info.setText(
                f"{self._selected_bo.civ} · {self._selected_bo.strategy} · {self._selected_bo.step_count} steps"
            )
            self.lbl_total_steps.setText(f"/ {self._selected_bo.step_count} total")
            self._update_personal_bests()

    # ── Replay ────────────────────────────────────────────────────────────

    def _on_browse_replay(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select AoE2 Replay",
            str(Path.home() / "Documents" / "My Games" / "Age of Empires 2 DE"),
            "AoE2 Replays (*.aoe2record);;All Files (*)",
        )
        if path:
            self._load_replay(path)

    def import_last_replay(self, *, silent: bool = False) -> bool:
        """Load the newest .aoe2record from the AoE2 replays folder."""
        from ..replay.parser import get_latest_replay
        latest = get_latest_replay()
        if not latest:
            if not silent:
                QMessageBox.information(
                    self, "No Replays Found",
                    "No .aoe2record files found in your AoE2 replays folder.\n\n"
                    f"Expected location:\n{Path.home() / 'Documents' / 'My Games' / 'Age of Empires 2 DE'}"
                )
            return False
        self._load_replay(str(latest), mark_seen=True)
        return True

    def check_for_new_replay(self) -> None:
        """
        Prompt to import when a newer replay appears (e.g. after a finished game).
        Called on app startup and when switching to the Practice tab.
        """
        if settings.auto_detect_sessions or not settings.auto_prompt_new_replay:
            return

        from ..replay.parser import get_latest_replay
        latest = get_latest_replay()
        if not latest:
            return

        mtime = latest.stat().st_mtime
        if mtime <= settings.last_seen_replay_mtime:
            return
        if str(latest) == settings.last_seen_replay_path and self._replay_path:
            return

        reply = QMessageBox.question(
            self, "New Game Detected",
            f"A new replay was found from your last game:\n\n"
            f"{latest.name}\n\n"
            "Import it into this practice session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._load_replay(str(latest), mark_seen=True)
            self._suggest_build_for_civ()
        else:
            settings.last_seen_replay_mtime = mtime
            settings.last_seen_replay_path = str(latest)
            settings.save()

    def _suggest_build_for_civ(self) -> None:
        """If replay civ matches a library build, offer to select it."""
        if not self._replay_info:
            return
        civ = self._replay_info.primary_civ()
        if not civ or civ == "Unknown":
            return

        bos = get_all_build_orders()
        matches = [b for b in bos if b.civ.lower() == civ.lower() or b.civ == "Any"]
        if not matches:
            return

        best = next((b for b in matches if b.civ.lower() == civ.lower()), matches[0])
        if self._selected_bo and self._selected_bo.id == best.id:
            return

        reply = QMessageBox.question(
            self, "Match Build Order?",
            f"Replay civ: {civ}\n\nLoad '{best.name}' for this review?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.load_build_order(best)

    def _load_replay(self, path: str, *, mark_seen: bool = True) -> None:
        from ..replay.parser import parse_replay, format_replay_duration
        from ..replay.analyzer import analyze_replay
        info = parse_replay(path)
        analysis = analyze_replay(path)
        self._replay_path = path
        self._replay_info = info
        self._replay_analysis = analysis

        if mark_seen:
            try:
                settings.last_seen_replay_mtime = Path(path).stat().st_mtime
                settings.last_seen_replay_path = path
                settings.save()
            except OSError:
                pass

        civ = info.primary_civ()
        duration = format_replay_duration(info.duration_sec)
        timing_bits = []
        if analysis.feudal_time_sec:
            timing_bits.append(f"Feudal {_sec_to_mmss(analysis.feudal_time_sec)}")
        if analysis.castle_time_sec:
            timing_bits.append(f"Castle {_sec_to_mmss(analysis.castle_time_sec)}")
        timing_str = " | ".join(timing_bits) if timing_bits else "timings not detected"
        conf = f" [{analysis.confidence} confidence]" if analysis.has_timings() else ""

        self.lbl_replay_info.setText(
            f"{Path(path).name}\n"
            f"Map: {info.map_name} | Civ: {civ} | ~{duration}\n"
            f"{timing_str}{conf}"
        )
        self._auto_fill_from_replay(analysis)
        if settings.auto_postgame_coach:
            self._run_postgame_coach(path)
        logger.info("Replay loaded for practice: %s", path)

    def _run_postgame_coach(self, replay_path: str) -> None:
        """Background post-game coach pipeline after replay import."""
        civ = self._replay_analysis.civ if self._replay_analysis else "Any"
        strategy = self._selected_bo.strategy if self._selected_bo else ""
        bo_id = self._selected_bo.id if self._selected_bo else None
        bo_name = self._selected_bo.name if self._selected_bo else ""

        self._postgame_thread = QThread(self)
        self._postgame_worker = _PostGameCoachWorker(
            replay_path, civ, strategy, bo_id, bo_name,
        )
        self._postgame_worker.moveToThread(self._postgame_thread)
        self._postgame_thread.started.connect(self._postgame_worker.run)
        self._postgame_worker.finished.connect(self._on_postgame_coach_done)
        self._postgame_worker.error.connect(
            lambda e: logger.warning("Post-game coach error: %s", e)
        )
        self._postgame_worker.finished.connect(self._postgame_thread.quit)
        self._postgame_worker.error.connect(self._postgame_thread.quit)
        self._postgame_thread.start()

    def _on_postgame_coach_done(self, result) -> None:
        """Show post-game coach report and offer to pin overlay alert."""
        from ..ai_coach.postgame import pin_overlay_alert

        dlg = _CoachingDialog(self)
        dlg.setWindowTitle("Post-Game Coach — Hera Analysis")
        dlg.set_result(result.report)
        dlg.show()

        if result.overlay_alert:
            reply = QMessageBox.question(
                self, "Pin to Overlay?",
                f"Show this reminder on your overlay next match?\n\n"
                f"\"{result.overlay_alert}\"",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                bo_id = self._selected_bo.id if self._selected_bo else None
                pin_overlay_alert(result.overlay_alert, bo_id)
                if self.overlay and self._selected_bo:
                    self.overlay._show_coach_alert(self._selected_bo)

    def _auto_fill_from_replay(self, analysis) -> None:
        """Pre-fill session fields from replay analysis data."""
        filled: list[str] = []

        if analysis.feudal_time_sec:
            self._log_milestone_silent("Clicked Feudal", analysis.feudal_time_sec)
            self._evaluate_feudal(analysis.feudal_time_sec)
            filled.append(f"Feudal {_sec_to_mmss(analysis.feudal_time_sec)}")
        if analysis.castle_time_sec:
            self._log_milestone_silent("Clicked Castle", analysis.castle_time_sec)
            self._evaluate_castle(analysis.castle_time_sec)
            filled.append(f"Castle {_sec_to_mmss(analysis.castle_time_sec)}")
        if analysis.imperial_time_sec:
            self._log_milestone_silent("Clicked Imperial", analysis.imperial_time_sec)
            filled.append(f"Imperial {_sec_to_mmss(analysis.imperial_time_sec)}")
        if analysis.final_pop:
            self.resource_tracker.sp_pop.setValue(analysis.final_pop)
            filled.append(f"Pop {analysis.final_pop}")

        if analysis.is_multiplayer:
            self.cb_result.setCurrentText("practice")

        if filled:
            note = f"Auto-filled from replay ({analysis.confidence} confidence): {', '.join(filled)}"
            existing = self.ed_session_notes.toPlainText().strip()
            self.ed_session_notes.setPlainText(f"{existing}\n{note}".strip() if existing else note)

    def _log_milestone_silent(self, label: str, elapsed_sec: int) -> None:
        """Log a milestone without re-triggering evaluation loops."""
        if any(m.label == label and m.game_time_sec == elapsed_sec for m in self._milestones):
            return
        ms = Milestone(label=label, game_time_sec=elapsed_sec, wall_time=now_iso())
        self._milestones.append(ms)
        item = QListWidgetItem(f"[{_sec_to_mmss(elapsed_sec)}] {label} (replay)")
        item.setForeground(Qt.GlobalColor.green)
        self.milestone_list.addItem(item)

    def _on_clear_replay(self) -> None:
        self._replay_path = None
        self._replay_info = None
        self.lbl_replay_info.setText("No replay loaded")

    def _on_timer_tick(self, elapsed_sec: int) -> None:
        """Sync overlay step timing + progress bars when auto-advance is on."""
        if not self.overlay or not self.overlay.isVisible():
            return
        if settings.auto_advance:
            self.overlay.sync_to_elapsed(elapsed_sec)
        elif self._selected_bo:
            self.overlay.sync_to_elapsed(elapsed_sec)

    # ── Milestones ────────────────────────────────────────────────────────

    def _log_milestone(self, label: str) -> None:
        elapsed = self.timer_widget.elapsed_sec()
        ms = Milestone(
            label=label,
            game_time_sec=elapsed,
            wall_time=now_iso(),
        )
        self._milestones.append(ms)

        item = QListWidgetItem(f"[{_sec_to_mmss(elapsed)}] {label}")
        if "feudal" in label.lower():
            item.setForeground(Qt.GlobalColor.yellow)
            # Auto-evaluate feudal time
            self._evaluate_feudal(elapsed)
        elif "castle" in label.lower():
            item.setForeground(Qt.GlobalColor.cyan)
            self._evaluate_castle(elapsed)
        self.milestone_list.addItem(item)
        self.milestone_list.scrollToBottom()
        logger.debug("Milestone logged: %s @ %ds", label, elapsed)

    def _log_custom_milestone(self) -> None:
        text = self.ed_milestone.text().strip()
        if text:
            self._log_milestone(text)
            self.ed_milestone.clear()

    # ── Performance evaluation ────────────────────────────────────────────

    def _evaluate_feudal(self, elapsed_sec: int) -> None:
        if not self._selected_bo:
            return
        benchmarks = get_benchmarks_for(self._selected_bo.civ, self._selected_bo.strategy)
        if not benchmarks:
            self.lbl_feudal_status.setText(f"Feudal: {_sec_to_mmss(elapsed_sec)} (no benchmark)")
            return
        status, msg = evaluate_feudal_time(elapsed_sec, benchmarks[0])
        self.lbl_feudal_status.setText(f"Feudal: {msg}")
        self.lbl_feudal_status.setStyleSheet(STATUS_STYLES.get(status, STATUS_STYLES["neutral"]))

    def _evaluate_castle(self, elapsed_sec: int) -> None:
        if not self._selected_bo:
            return
        benchmarks = get_benchmarks_for(self._selected_bo.civ, self._selected_bo.strategy)
        if not benchmarks:
            self.lbl_castle_status.setText(f"Castle: {_sec_to_mmss(elapsed_sec)} (no benchmark)")
            return
        status, msg = evaluate_castle_time(elapsed_sec, benchmarks[0])
        self.lbl_castle_status.setText(f"Castle: {msg}")
        self.lbl_castle_status.setStyleSheet(STATUS_STYLES.get(status, STATUS_STYLES["neutral"]))

    def _evaluate_performance(self) -> None:
        steps_done  = self.sp_steps_done.value()
        total_steps = self._selected_bo.step_count if self._selected_bo else 0

        feudal_ms = next((ms for ms in self._milestones if "feudal" in ms.label.lower()), None)
        castle_ms = next((ms for ms in self._milestones if "castle" in ms.label.lower()), None)

        if feudal_ms:
            self._evaluate_feudal(feudal_ms.game_time_sec)
        if castle_ms:
            self._evaluate_castle(castle_ms.game_time_sec)

        score = calculate_accuracy_score(
            steps_done, total_steps,
            feudal_ms.game_time_sec if feudal_ms else None,
            castle_ms.game_time_sec if castle_ms else None,
        )
        self.lbl_accuracy.setText(f"Accuracy Score: {score:.1f}%")
        style = "green" if score >= 75 else ("yellow" if score >= 50 else "red")
        self.lbl_accuracy.setStyleSheet(STATUS_STYLES[style])

    def _update_personal_bests(self) -> None:
        if not self._selected_bo:
            return
        stats = get_summary_stats(self._selected_bo.id)
        bf = stats.get("best_feudal_sec")
        bc = stats.get("best_castle_sec")
        ba = stats.get("avg_accuracy")
        self.lbl_pb_feudal.setText(_sec_to_mmss(bf) if bf else "—")
        self.lbl_pb_castle.setText(_sec_to_mmss(bc) if bc else "—")
        self.lbl_pb_accuracy.setText(f"{ba:.1f}%" if ba else "—")

    # ── Save session ──────────────────────────────────────────────────────

    def _on_save_session(self) -> None:
        if not self._selected_bo or self._selected_bo.id is None:
            QMessageBox.warning(self, "No Build Order", "Select a build order before saving.")
            return

        elapsed = self.timer_widget.elapsed_sec()
        if elapsed < 10:
            reply = QMessageBox.question(
                self, "Short Session",
                "The timer shows less than 10 seconds. Save anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        resources = self.resource_tracker.snapshot()
        feudal_ms = next((ms for ms in self._milestones if "feudal" in ms.label.lower()), None)
        castle_ms = next((ms for ms in self._milestones if "castle" in ms.label.lower()), None)
        imp_ms    = next((ms for ms in self._milestones if "imperial" in ms.label.lower()), None)

        steps_done  = self.sp_steps_done.value()
        total_steps = self._selected_bo.step_count

        score = calculate_accuracy_score(
            steps_done, total_steps,
            feudal_ms.game_time_sec if feudal_ms else None,
            castle_ms.game_time_sec if castle_ms else None,
        )

        session = Session(
            build_order_id=self._selected_bo.id,
            duration_sec=elapsed,
            replay_path=self._replay_path,
            feudal_time_sec=feudal_ms.game_time_sec if feudal_ms else None,
            castle_time_sec=castle_ms.game_time_sec if castle_ms else None,
            imperial_time_sec=imp_ms.game_time_sec if imp_ms else None,
            final_pop=resources["pop"],
            food_at_feudal=resources["food"] if feudal_ms else None,
            wood_at_feudal=resources["wood"] if feudal_ms else None,
            gold_at_feudal=resources["gold"] if feudal_ms else None,
            stone_at_feudal=resources["stone"] if feudal_ms else None,
            result=self.cb_result.currentText(),
            accuracy_pct=score,
            notes=self.ed_session_notes.toPlainText().strip(),
            milestones=self._milestones.copy(),
        )

        saved = save_session(session)
        self.session_saved.emit(saved)

        # Reset for next session
        self._milestones.clear()
        self.milestone_list.clear()
        self.ed_session_notes.clear()
        self.sp_steps_done.setValue(0)
        self.timer_widget.reset()
        self._update_personal_bests()

        QMessageBox.information(
            self, "Session Saved",
            f"Session saved!\nAccuracy: {score:.1f}%\n"
            f"Feudal: {_sec_to_mmss(feudal_ms.game_time_sec) if feudal_ms else 'N/A'}\n"
            f"Castle: {_sec_to_mmss(castle_ms.game_time_sec) if castle_ms else 'N/A'}"
        )
        logger.info("Session saved: id=%d score=%.1f", saved.id, score)
        self._offer_ai_coaching(saved)

    def _offer_ai_coaching(self, session: Session) -> None:
        """Show post-session coaching tips (AI or offline fallback)."""
        reply = QMessageBox.question(
            self, "AI Coach",
            "Session saved. View coaching tips for this run?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes or not self._selected_bo:
            return

        dlg = _CoachingDialog(self)
        dlg.show()

        self._coaching_thread = QThread(self)
        self._coaching_worker = _CoachingWorker(session, self._selected_bo)
        self._coaching_worker.moveToThread(self._coaching_thread)
        self._coaching_thread.started.connect(self._coaching_worker.run)

        self._coaching_worker.finished.connect(dlg.set_result)
        self._coaching_worker.error.connect(
            lambda e: dlg.set_result(f"Coach error: {e}")
        )
        self._coaching_worker.finished.connect(self._coaching_thread.quit)
        self._coaching_worker.error.connect(self._coaching_thread.quit)
        self._coaching_thread.finished.connect(self._coaching_thread.deleteLater)
        self._coaching_thread.start()
