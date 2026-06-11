"""
TRINKER - Quick Start Tab
One-screen guided workflow so new users aren't overwhelmed.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QMessageBox,
)

from ..build_orders.manager import get_all_build_orders
from ..core.config import settings

STYLE = """
QWidget { background: #111113; color: #ecf0f1; }
QComboBox {
    background: #1e1e22; border: 1px solid #2c2c2e;
    border-radius: 8px; padding: 10px 12px; color: #ecf0f1; font-size: 13px;
}
QPushButton#primary {
    background: #1c3a5c; color: #7ec8ff; border: 2px solid #3498db;
    border-radius: 10px; padding: 16px 28px; font-size: 15px; font-weight: bold;
}
QPushButton#primary:hover { background: #254a70; }
QPushButton#secondary {
    background: #1e1e22; color: #ecf0f1; border: 1px solid #2c2c2e;
    border-radius: 10px; padding: 14px 24px; font-size: 13px;
}
QPushButton#secondary:hover { border-color: #3498db; }
"""


class _StepCard(QFrame):
    def __init__(self, number: str, title: str, hint: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background: #16161a; border: 1px solid #2c2c2e; border-radius: 12px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        num = QLabel(number)
        num.setStyleSheet(
            "color: #3498db; font-size: 22px; font-weight: bold; min-width: 36px;"
        )
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        header.addWidget(num)
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        hint_lbl = QLabel(hint)
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet("color: #7f8c8d; font-size: 12px; margin-left: 36px;")
        layout.addWidget(hint_lbl)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(36, 4, 0, 0)
        layout.addLayout(self.body)


class QuickStartTab(QWidget):
    """Guided 3-step loop: pick build → play with overlay → import replay."""

    play_requested = Signal(object)       # BuildOrder
    import_replay_requested = Signal()
    bulk_import_done = Signal()
    simple_mode_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLE)
        self._setup_ui()
        self._load_builds()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(20)

        title = QLabel("Start Here")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #7ec8ff;")
        root.addWidget(title)

        sub = QLabel(
            "Ignore everything else for now. Repeat this loop each game — "
            "TRINKER handles coaching, replay data, and progress tracking."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #7f8c8d; font-size: 13px; max-width: 720px;")
        root.addWidget(sub)

        root.addSpacing(8)

        # Step 1
        step1 = _StepCard(
            "1",
            "Pick what you're practicing today",
            "Choose one build order and stick with it for a few games.",
        )
        self.cb_bo = QComboBox()
        self.cb_bo.setMinimumWidth(360)
        step1.body.addWidget(self.cb_bo)
        root.addWidget(step1)

        # Step 2
        step2 = _StepCard(
            "2",
            "Play with the overlay on screen",
            "Alt-tab to AoE2. Follow the steps. Use Ctrl+Right / Ctrl+Left to advance.",
        )
        self.btn_play = QPushButton("▶  Show Overlay & Play")
        self.btn_play.setObjectName("primary")
        self.btn_play.clicked.connect(self._on_play)
        step2.body.addWidget(self.btn_play)
        root.addWidget(step2)

        # Step 3
        step3 = _StepCard(
            "3",
            "Play any game — TRINKER watches in the background",
            "Single-player, ranked, team games: when you finish, the replay is saved "
            "automatically. Check Analytics for history and AI coach tips.",
        )
        import_row = QHBoxLayout()
        self.btn_import = QPushButton("Check Latest Game")
        self.btn_import.setObjectName("secondary")
        self.btn_import.clicked.connect(self.import_replay_requested.emit)
        import_row.addWidget(self.btn_import)

        self.btn_import_all = QPushButton("Import All Past Games")
        self.btn_import_all.setObjectName("secondary")
        self.btn_import_all.clicked.connect(self._on_import_all)
        import_row.addWidget(self.btn_import_all)
        step3.body.addLayout(import_row)
        root.addWidget(step3)

        footer = QLabel(
            "You do not need to import manually. Buttons above are for catching up on old replays."
        )
        footer.setWordWrap(True)
        footer.setStyleSheet("color: #3a5a7a; font-size: 11px; margin-top: 8px;")
        root.addWidget(footer)

        root.addStretch()

    def _load_builds(self) -> None:
        self.cb_bo.clear()
        bos = get_all_build_orders()
        default_idx = 0
        for i, bo in enumerate(bos):
            self.cb_bo.addItem(f"{bo.name} ({bo.civ})", bo.id)
            if settings.last_practice_bo_id and bo.id == settings.last_practice_bo_id:
                default_idx = i
        if bos:
            self.cb_bo.setCurrentIndex(default_idx)

    def refresh(self) -> None:
        self._load_builds()

    def _on_play(self) -> None:
        bo_id = self.cb_bo.currentData()
        if bo_id is None:
            return
        from ..build_orders.manager import get_build_order
        bo = get_build_order(bo_id)
        if bo:
            settings.last_practice_bo_id = bo.id
            settings.save()
            self.play_requested.emit(bo)

    def selected_build_id(self):
        return self.cb_bo.currentData()

    def _on_import_all(self) -> None:
        from ..replay.bulk_import import import_all_replays
        from ..replay.parser import find_replay_files

        count = len(find_replay_files())
        if count == 0:
            QMessageBox.information(
                self, "No Replays",
                "No .aoe2record files found in your AoE2 save folder.",
            )
            return

        from ..replay.parser import find_replay_files as _find
        total = len(_find())

        reply = QMessageBox.question(
            self, "Import Past Games?",
            f"Import up to {total} replay(s) from your AoE2 folder?\n\n"
            "(Skips already-imported games. No popups — data goes to Analytics.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        result = import_all_replays(
            preferred_bo_id=self.cb_bo.currentData(),
            mp_only=False,
        )
        QMessageBox.information(
            self, "Import Complete",
            f"Imported: {result.imported}\n"
            f"Skipped (already had): {result.skipped}\n"
            f"Failed: {result.failed}\n\n"
            "v2.0 only stores validated data. Timings show — until mgz supports your DE patch.\n"
            "Check Analytics → Session History.",
        )
        self.bulk_import_done.emit()
