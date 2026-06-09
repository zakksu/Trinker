"""
TRINKER — Retro Game Launcher (early-2000s vibe)
Auto-updates, installs dependencies, then launches the main app.

Usage:
    python launcher.py
    Double-click: LAUNCHER.bat
"""

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtCore import Qt, QThread, QObject, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton,
)

from src.core.config import get_app_version

LAUNCHER_STYLE = """
QWidget {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1a2a4a, stop:0.5 #0d1528, stop:1 #060a14);
    color: #c8d8f0;
    font-family: "Trebuchet MS", "Segoe UI", sans-serif;
}
QLabel#title {
    color: #7ec8ff;
    font-size: 28px;
    font-weight: bold;
    letter-spacing: 6px;
}
QLabel#subtitle {
    color: #5a7a9a;
    font-size: 11px;
    letter-spacing: 2px;
}
QLabel#status {
    color: #8ab4d4;
    font-size: 12px;
}
QProgressBar {
    background: #0a1020;
    border: 2px solid #2a4a6a;
    border-radius: 4px;
    height: 18px;
    text-align: center;
    color: #fff;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2060a0, stop:1 #40a0e0);
    border-radius: 2px;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3a6a9a, stop:1 #1a3a5a);
    color: #e0f0ff;
    border: 2px solid #5a9aca;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton:hover { background: #4a8aba; }
QPushButton:disabled { color: #556; border-color: #334; }
"""


class _LaunchWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def run(self) -> None:
        steps = [
            (10, "Initializing TRINKER systems…"),
            (25, "Checking for updates…"),
            (45, "Verifying dependencies…"),
            (65, "Preparing training modules…"),
            (85, "Launching application…"),
        ]
        try:
            for pct, msg in steps:
                self.progress.emit(pct, msg)
                if pct == 25:
                    self._git_pull()
                if pct == 45:
                    self._pip_install()

            self.progress.emit(100, "Ready — starting TRINKER!")
            self.finished.emit(True, "")
        except Exception as exc:
            self.finished.emit(False, str(exc))

    def _git_pull(self) -> None:
        if not (_ROOT / ".git").exists():
            return
        subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=_ROOT, capture_output=True, text=True, timeout=120,
        )

    def _pip_install(self) -> None:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            cwd=_ROOT, capture_output=True, text=True, timeout=300,
        )


class TrinkerLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TRINKER Launcher")
        self.setFixedSize(480, 340)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(LAUNCHER_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(12)

        icon_path = _ROOT / "assets" / "trinker_icon.png"
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation)
            icon_lbl = QLabel()
            icon_lbl.setPixmap(pix)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon_lbl)

        title = QLabel("TRINKER")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel(f"AoE2 TRAINING COMPANION  ·  v{get_app_version()}")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        layout.addSpacing(16)

        self.lbl_status = QLabel("Click START to begin…")
        self.lbl_status.setObjectName("status")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        layout.addWidget(self.bar)

        layout.addStretch()

        self.btn_start = QPushButton("▶  START")
        self.btn_start.clicked.connect(self._on_start)
        layout.addWidget(self.btn_start, alignment=Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("Updates + dependencies handled automatically")
        hint.setStyleSheet("color: #3a5a7a; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self._thread = None
        self._worker = None

    def _on_start(self) -> None:
        self.btn_start.setEnabled(False)
        self.bar.setValue(0)
        self._thread = QThread(self)
        self._worker = _LaunchWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_progress(self, pct: int, msg: str) -> None:
        self.bar.setValue(pct)
        self.lbl_status.setText(msg)

    def _on_finished(self, ok: bool, err: str) -> None:
        if not ok:
            self.lbl_status.setText(f"Error: {err}")
            self.btn_start.setEnabled(True)
            return
        QTimer.singleShot(400, self._launch_app)

    def _launch_app(self) -> None:
        subprocess.Popen([sys.executable, str(_ROOT / "main.py")], cwd=_ROOT)
        self.close()


def main() -> int:
    app = QApplication(sys.argv)
    icon = _ROOT / "assets" / "trinker.ico"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    w = TrinkerLauncher()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
