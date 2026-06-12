"""
TRINKER — Retro Game Launcher
One click: check updates (popup if available) → pull → launch latest TRINKER.

Usage:
    Double-click LAUNCHER.bat  (recommended — only entry point you need)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.config import DATA_DIR, get_app_version
from src.core.update_service import UpdateStatus, apply_git_pull, apply_pip_install, check_updates

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

    def __init__(self, do_git_pull: bool):
        super().__init__()
        self._do_git_pull = do_git_pull

    def run(self) -> None:
        try:
            self.progress.emit(15, "Checking training modules…")
            if self._do_git_pull:
                self.progress.emit(35, "Downloading latest version from GitHub…")
                ok, msg = apply_git_pull(_ROOT)
                if not ok:
                    self.finished.emit(False, f"Update failed: {msg}")
                    return

            self.progress.emit(60, "Verifying dependencies…")
            apply_pip_install(_ROOT)

            self.progress.emit(90, "Starting TRINKER…")
            self.progress.emit(100, "Ready!")
            self.finished.emit(True, "")
        except Exception as exc:
            self.finished.emit(False, str(exc))


class TrinkerLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TRINKER Launcher")
        self.setFixedSize(480, 340)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(LAUNCHER_STYLE)
        self._update_status: UpdateStatus | None = None
        self._do_git_pull = False
        self._thread = None
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(12)

        icon_path = _ROOT / "assets" / "trinker_icon.png"
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(
                72, 72,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_lbl = QLabel()
            icon_lbl.setPixmap(pix)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon_lbl)

        title = QLabel("TRINKER")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.lbl_version = QLabel(f"AoE2 TRAINING COMPANION  ·  v{get_app_version()}")
        self.lbl_version.setObjectName("subtitle")
        self.lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_version)

        layout.addSpacing(16)

        self.lbl_status = QLabel("Checking for updates…")
        self.lbl_status.setObjectName("status")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        layout.addWidget(self.bar)

        layout.addStretch()

        self.btn_start = QPushButton("▶  START")
        self.btn_start.setVisible(False)
        self.btn_start.clicked.connect(self._begin_launch)
        layout.addWidget(self.btn_start, alignment=Qt.AlignmentFlag.AlignCenter)

        hint = QLabel(f"Data: {DATA_DIR}")
        hint.setStyleSheet("color: #3a5a7a; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        sub_hint = QLabel("Always launches the latest version from GitHub")
        sub_hint.setStyleSheet("color: #3a5a7a; font-size: 10px;")
        sub_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_hint)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(200, self._check_and_start)

    def _check_and_start(self) -> None:
        self.lbl_status.setText("Checking GitHub for updates…")
        self.bar.setValue(5)
        QApplication.processEvents()

        self._update_status = check_updates(_ROOT)
        self._do_git_pull = False

        if self._update_status.has_git_update:
            remote_v = self._update_status.remote_version or "latest"
            msg = (
                f"A newer TRINKER is available on GitHub.\n\n"
                f"{self._update_status.summary()}\n\n"
                f"Update now and launch v{remote_v}?"
            )
            box = QMessageBox(self)
            box.setWindowTitle("TRINKER Update")
            box.setText(msg)
            box.setStandardButtons(
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel
            )
            box.setDefaultButton(QMessageBox.StandardButton.Yes)
            choice = box.exec()

            if choice == QMessageBox.StandardButton.Cancel:
                self.close()
                return
            if choice == QMessageBox.StandardButton.Yes:
                self._do_git_pull = True
            # No = launch current version without pull

        elif self._update_status.exe_update_available:
            QMessageBox.information(
                self,
                "TRINKER Update",
                f"GitHub Release v{self._update_status.remote_version} includes TRINKER.exe.\n\n"
                "Run UPDATE_EXE.bat for the standalone app, or use git pull via this launcher.",
            )

        self._begin_launch()

    def _begin_launch(self) -> None:
        self.btn_start.setEnabled(False)
        self.bar.setValue(10)
        self._thread = QThread(self)
        self._worker = _LaunchWorker(self._do_git_pull)
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
            self.btn_start.setVisible(True)
            self.btn_start.setEnabled(True)
            return
        # Reload version label after pull
        from src.core.config import get_app_version

        self.lbl_version.setText(f"AoE2 TRAINING COMPANION  ·  v{get_app_version()}")
        QTimer.singleShot(300, self._launch_app)

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
