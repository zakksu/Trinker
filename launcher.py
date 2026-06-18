"""
TRINKER — Master Your Age (hub launcher)
One click: auto-pull latest → verify deps → LAUNCH TRINKER.

Usage:
    Double-click LAUNCHER.bat
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.config import DATA_DIR, get_app_version, settings
from src.core.update_service import UpdateStatus, apply_git_pull, apply_pip_install, check_updates
from src.ui.medieval.icons import Icon
from src.ui.medieval.palette import get_palette
from src.ui.medieval.styles import parchment_bg


def _display_name() -> str:
    try:
        import json
        from src.analytics.replay_store import get_replay_analyses

        for row in get_replay_analyses(3):
            data = json.loads(row.profile_json or "{}")
            name = (data.get("player_name") or "").strip()
            if name:
                return name.split()[0]
    except Exception:
        pass
    sid = (settings.steam_id or "").strip()
    if sid:
        return f"Player {sid[-4:]}"
    return os.environ.get("USERNAME") or os.environ.get("USER") or "Commander"


def _hub_stylesheet() -> str:
    p = get_palette()
    return f"""
QWidget#LauncherRoot {{
    background: #1a1814;
    color: #e8dcc8;
    font-family: "Segoe UI", "Georgia", serif;
}}
QFrame#Sidebar {{
    background: #12100e;
    border-right: 1px solid {p.wood_frame};
}}
QFrame#Banner {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2a2418, stop:0.5 #3d3424, stop:1 #2a2418);
    border-bottom: 2px solid {p.gold_dim};
    min-height: 72px;
}}
QFrame#Card {{
    background: #252018;
    border: 1px solid {p.wood_frame};
    border-radius: 6px;
}}
QPushButton#NavBtn {{
    background: transparent;
    color: #c8b898;
    border: none;
    border-left: 3px solid transparent;
    text-align: left;
    padding: 12px 16px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton#NavBtn:hover {{
    background: #2a2418;
    color: {p.gold_bright};
}}
QPushButton#NavBtn[active="true"] {{
    background: #3d3424;
    color: {p.gold_bright};
    border-left: 3px solid {p.gold};
}}
QPushButton#LaunchBtn {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3d8b4a, stop:1 #2a6b35);
    color: white;
    border: 2px solid #5cb86a;
    border-radius: 8px;
    padding: 16px 40px;
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 2px;
}}
QPushButton#LaunchBtn:hover {{
    background: #4aa858;
}}
QPushButton#LaunchBtn:disabled {{
    background: #444;
    border-color: #555;
    color: #888;
}}
QPushButton#QuickLink {{
    background: transparent;
    color: {p.gold};
    border: 1px solid {p.wood_frame};
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 10px;
}}
QProgressBar {{
    background: #12100e;
    border: 1px solid {p.wood_frame};
    height: 14px;
    border-radius: 3px;
}}
QProgressBar::chunk {{
    background: {p.gold};
}}
QLabel#Welcome {{
    font-size: 28px;
    font-weight: bold;
    color: {p.gold_bright};
}}
QLabel#Muted {{
    color: #8a8070;
    font-size: 11px;
}}
"""


class _LaunchWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, do_git_pull: bool):
        super().__init__()
        self._do_git_pull = do_git_pull

    def run(self) -> None:
        try:
            self.progress.emit(10, "Checking GitHub…")
            if self._do_git_pull:
                self.progress.emit(35, "Pulling latest TRINKER…")
                ok, msg = apply_git_pull(_ROOT)
                if not ok:
                    self.finished.emit(False, f"Update failed: {msg}")
                    return
            self.progress.emit(55, "Verifying dependencies…")
            apply_pip_install(_ROOT)
            self.progress.emit(80, "Background tests…")
            try:
                from src.core.resource_profile import get_resource_profile

                if get_resource_profile().background_tests:
                    subprocess.Popen(
                        [sys.executable, str(_ROOT / "scripts" / "test_worker.py"), "--once"],
                        cwd=_ROOT,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
            except Exception:
                pass
            self.progress.emit(100, "ALL SYSTEMS READY")
            self.finished.emit(True, "")
        except Exception as exc:
            self.finished.emit(False, str(exc))


class TrinkerLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("LauncherRoot")
        self.setWindowTitle("TRINKER")
        self.setFixedSize(980, 580)
        self.setStyleSheet(_hub_stylesheet())
        self._update_status: UpdateStatus | None = None
        self._do_git_pull = False
        self._ready = False
        self._thread = None
        self._worker = None
        self._nav_buttons: dict[str, QPushButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(0, 16, 0, 12)
        sb.setSpacing(4)

        logo = QLabel(f"{Icon.TRINKER} TRINKER")
        logo.setStyleSheet("color: #d4af37; font-size: 14px; font-weight: bold; padding: 8px 16px;")
        sb.addWidget(logo)

        for key, label, icon in (
            ("play", "PLAY", Icon.GAME),
            ("library", "LIBRARY", Icon.LIBRARY),
            ("replays", "REPLAYS", Icon.ANALYTICS),
            ("coach", "COACH", Icon.COACH),
        ):
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("NavBtn")
            btn.setProperty("active", key == "play")
            btn.setStyleSheet(btn.styleSheet())
            btn.clicked.connect(lambda checked=False, k=key: self._on_nav(k))
            self._nav_buttons[key] = btn
            sb.addWidget(btn)

        sb.addStretch()
        profile = QLabel(f"👤 {_display_name()}")
        profile.setStyleSheet("padding: 8px 16px; font-size: 11px; color: #a89878;")
        sb.addWidget(profile)
        settings_btn = QPushButton(f"  {Icon.SETTINGS}  Settings")
        settings_btn.setObjectName("NavBtn")
        settings_btn.clicked.connect(lambda: self._open_app_tab("settings"))
        sb.addWidget(settings_btn)
        root.addWidget(sidebar)

        # ── Main column ──
        main_col = QVBoxLayout()
        main_col.setContentsMargins(0, 0, 0, 0)
        main_col.setSpacing(0)

        banner = QFrame()
        banner.setObjectName("Banner")
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(24, 12, 24, 12)
        bl.addWidget(QLabel("TRINKER"))
        bl.addStretch()
        self.lbl_version = QLabel(f"v{get_app_version()}")
        self.lbl_version.setStyleSheet("color: #d4af37; font-weight: bold;")
        bl.addWidget(self.lbl_version)
        main_col.addWidget(banner)

        body = QHBoxLayout()
        body.setContentsMargins(24, 24, 24, 24)
        body.setSpacing(24)

        # Center welcome
        center = QVBoxLayout()
        center.setSpacing(12)
        welcome = QLabel(f"WELCOME BACK, {_display_name().upper()}")
        welcome.setObjectName("Welcome")
        center.addWidget(welcome)
        sub = QLabel("Your AoE2 DE training companion")
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #b8a888; font-size: 13px;")
        center.addWidget(sub)
        center.addSpacing(16)

        self.lbl_status = QLabel("Preparing…")
        self.lbl_status.setStyleSheet("color: #8fdc9a; font-size: 12px;")
        center.addWidget(self.lbl_status)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        center.addWidget(self.bar)

        self.btn_launch = QPushButton("LAUNCH TRINKER")
        self.btn_launch.setObjectName("LaunchBtn")
        self.btn_launch.setEnabled(False)
        self.btn_launch.clicked.connect(self._launch_app)
        center.addWidget(self.btn_launch, alignment=Qt.AlignmentFlag.AlignLeft)

        ql_row = QHBoxLayout()
        for key, title in (
            ("training", "PRACTICE"),
            ("library", "LEARN"),
            ("analytics", "IMPROVE"),
            ("dashboard", "COMPETE"),
        ):
            b = QPushButton(title)
            b.setObjectName("QuickLink")
            b.setToolTip(f"Open {title.title()} in TRINKER")
            b.clicked.connect(lambda checked=False, k=key: self._open_app_tab(k))
            ql_row.addWidget(b)
        center.addLayout(ql_row)
        center.addStretch()
        body.addLayout(center, stretch=3)

        # Right panel
        right = QVBoxLayout()
        right.setSpacing(12)
        feat = QFrame()
        feat.setObjectName("Card")
        fl = QVBoxLayout(feat)
        fl.setContentsMargins(14, 14, 14, 14)
        fl.addWidget(QLabel("FEATURED BUILD"))
        self.lbl_featured = QLabel("Loading build library…")
        self.lbl_featured.setWordWrap(True)
        self.lbl_featured.setStyleSheet("font-size: 12px; color: #e8dcc8;")
        fl.addWidget(self.lbl_featured)
        right.addWidget(feat)

        rec = QFrame()
        rec.setObjectName("Card")
        rl = QVBoxLayout(rec)
        rl.setContentsMargins(14, 14, 14, 14)
        rl.addWidget(QLabel("RECENT REPLAYS"))
        self.lbl_replays = QLabel("—")
        self.lbl_replays.setWordWrap(True)
        self.lbl_replays.setStyleSheet("font-size: 11px; color: #a89878;")
        rl.addWidget(self.lbl_replays)
        right.addWidget(rec)
        right.addStretch()
        body.addLayout(right, stretch=2)

        main_col.addLayout(body)
        root.addLayout(main_col, stretch=1)
        QTimer.singleShot(100, self._load_sidebar_data)

    def _on_nav(self, key: str) -> None:
        for k, btn in self._nav_buttons.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if key != "play":
            self._open_app_tab(key)

    def _load_sidebar_data(self) -> None:
        try:
            from src.build_orders.manager import get_all_build_orders, get_build_order

            bos = get_all_build_orders()
            bo = None
            if settings.last_practice_bo_id:
                bo = get_build_order(settings.last_practice_bo_id)
            if bo is None and bos:
                bo = bos[0]
            if bo:
                feudal = "—"
                for s in bo.steps:
                    if s.age and "feudal" in (s.age or "").lower():
                        feudal = s.time_str or f"{s.time_sec // 60}:{s.time_sec % 60:02d}"
                        break
                steps = "\n".join(
                    f"  • {s.description[:60]}" for s in bo.steps[:3]
                )
                self.lbl_featured.setText(
                    f"<b>{bo.name}</b><br>{bo.civ} · {bo.strategy}<br>"
                    f"Feudal target: {feudal}<br>{steps}"
                )
            else:
                self.lbl_featured.setText("Import builds from Library after first launch.")
        except Exception:
            self.lbl_featured.setText("Build library loads on first launch.")

        try:
            from src.analytics.replay_store import get_replay_analyses

            rows = get_replay_analyses(3)
            if rows:
                lines = []
                for r in rows:
                    name = Path(r.replay_path).name if r.replay_path else "Replay"
                    lines.append(f"• {name[:40]}")
                self.lbl_replays.setText("\n".join(lines))
            else:
                from src.analytics.session import get_sessions

                sessions = get_sessions(limit=3)
                if sessions:
                    self.lbl_replays.setText(
                        "\n".join(f"• {s.civ or 'Game'} — {s.date}" for s in sessions)
                    )
                else:
                    self.lbl_replays.setText("No replays yet — play a game!")
        except Exception:
            self.lbl_replays.setText("Replay history loads after first game.")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(200, self._auto_prepare)

    def _auto_prepare(self) -> None:
        self.lbl_status.setText("Checking GitHub for updates…")
        self.bar.setValue(5)
        QApplication.processEvents()
        self._update_status = check_updates(_ROOT)
        self._do_git_pull = bool(self._update_status.has_git_update)
        if self._do_git_pull:
            rv = self._update_status.remote_version or "latest"
            self.lbl_status.setText(f"Update available — pulling v{rv}…")
        else:
            self.lbl_status.setText("Checking dependencies…")
        self._begin_prepare()

    def _begin_prepare(self) -> None:
        self.btn_launch.setEnabled(False)
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
            self.btn_launch.setEnabled(True)
            self.btn_launch.setText("RETRY")
            self.btn_launch.clicked.disconnect()
            self.btn_launch.clicked.connect(self._begin_prepare)
            return
        self.lbl_version.setText(f"v{get_app_version()}")
        self._ready = True
        self.btn_launch.setEnabled(True)
        self.lbl_status.setText("● ALL SYSTEMS READY")
        self._load_sidebar_data()
        QTimer.singleShot(400, self._prompt_ollama_then_enable)

    def _prompt_ollama_then_enable(self) -> None:
        try:
            from src.core.config import settings as cfg

            if cfg.ollama_setup_dismissed or not cfg.ai_coach_enabled:
                return
            from src.ai_coach.coach import _is_ollama_available

            if _is_ollama_available():
                return
        except Exception:
            return

        from PySide6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setWindowTitle("TRINKER AI Coach")
        box.setText(
            "Optional: set up Ollama for smarter post-game tips.\n\n"
            "TRINKER works fully without it.\n\nRun SETUP_AI.bat now?"
        )
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if box.exec() == QMessageBox.StandardButton.Yes:
            setup_bat = _ROOT / "SETUP_AI.bat"
            if setup_bat.exists():
                subprocess.Popen(["cmd", "/c", str(setup_bat)], cwd=_ROOT)
            else:
                subprocess.Popen(
                    [sys.executable, str(_ROOT / "scripts" / "setup_ollama.py"), "--open-installer"],
                    cwd=_ROOT,
                )
        else:
            from src.core.config import settings as cfg

            cfg.ollama_setup_dismissed = True
            cfg.save()

    def _open_app_tab(self, tab_key: str) -> None:
        if not self._ready:
            self._begin_prepare()
            return
        env = os.environ.copy()
        env["TRINKER_START_TAB"] = tab_key
        subprocess.Popen([sys.executable, str(_ROOT / "main.py")], cwd=_ROOT, env=env)
        self.close()

    def _launch_app(self) -> None:
        if not self._ready:
            self._begin_prepare()
            return
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
