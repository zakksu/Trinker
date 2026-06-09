"""
TRINKER - Main Application Window
Tabbed main window with: Library, Practice, Analytics, Settings, and Overlay control.
Wires all tabs and the overlay together with signals.
"""

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal

from ..core.config import get_app_version
from PySide6.QtGui import QFont, QIcon, QKeySequence, QShortcut, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QStatusBar, QFrame, QSizePolicy, QMenuBar, QMenu,
    QMessageBox, QFileDialog,
)

from .library_tab   import LibraryTab
from .practice_tab  import PracticeTab
from .analytics_tab import AnalyticsTab
from .settings_tab  import SettingsTab
from .overlay       import BuildOrderOverlay
from ..build_orders.models import BuildOrder
from ..core.config  import settings
from ..core.logger  import logger

DARK_STYLE = """
QMainWindow, QWidget {
    background: #0d0d0f;
    color: #ecf0f1;
    font-family: "Segoe UI", "SF Pro Display", "Inter", sans-serif;
}
QTabWidget::pane {
    border: none;
    background: #111113;
}
QTabBar {
    background: #0d0d0f;
}
QTabBar::tab {
    background: #111113;
    color: #7f8c8d;
    padding: 10px 20px;
    margin-right: 1px;
    border: none;
    font-size: 12px;
    letter-spacing: 0.5px;
}
QTabBar::tab:selected {
    color: #3498db;
    border-bottom: 2px solid #3498db;
    background: #111113;
}
QTabBar::tab:hover:!selected {
    color: #bdc3c7;
    background: #1a1a1f;
}
QStatusBar {
    background: #0a0a0c;
    color: #7f8c8d;
    font-size: 11px;
    border-top: 1px solid #1a1a1f;
}
QMenuBar {
    background: #0d0d0f;
    color: #ecf0f1;
    border-bottom: 1px solid #1a1a1f;
    padding: 2px 4px;
}
QMenuBar::item:selected { background: #1e1e22; border-radius: 4px; }
QMenu {
    background: #1e1e22;
    border: 1px solid #2c2c2e;
    border-radius: 6px;
    padding: 4px;
    color: #ecf0f1;
}
QMenu::item:selected { background: #2c2c3e; border-radius: 4px; }
QMenu::separator { height: 1px; background: #2c2c2e; margin: 4px 0; }
"""

LIGHT_STYLE = """
QMainWindow, QWidget { background: #f5f5f7; color: #1a1a1a; font-family: "Segoe UI", "SF Pro Display", "Inter", sans-serif; }
QTabBar::tab { background: #f0f0f2; color: #666; padding: 10px 20px; border: none; }
QTabBar::tab:selected { color: #007AFF; border-bottom: 2px solid #007AFF; background: #f5f5f7; }
QStatusBar { background: #e8e8ea; color: #666; border-top: 1px solid #d0d0d5; }
"""


class HeaderBar(QFrame):
    """Compact header strip above the tabs with branding and overlay toggle."""

    overlay_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet("QFrame { background: #0a0a0c; border-bottom: 1px solid #1a1a1f; }")
        self._overlay_visible = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Logo / title
        logo = QLabel("TRINKER")
        logo.setStyleSheet(
            "color: #3498db; font-size: 16px; font-weight: bold; letter-spacing: 4px;"
        )
        subtitle = QLabel("AoE2 Training Companion")
        subtitle.setStyleSheet("color: #3c3c4e; font-size: 11px; margin-left: 2px;")

        layout.addWidget(logo)
        layout.addWidget(subtitle)
        layout.addStretch()

        # Overlay toggle button
        self.btn_overlay = QPushButton("⊞ Show Overlay")
        self.btn_overlay.setCheckable(True)
        self.btn_overlay.setStyleSheet("""
            QPushButton {
                background: rgba(52, 152, 219, 0.12);
                color: #3498db;
                border: 1px solid rgba(52, 152, 219, 0.4);
                border-radius: 6px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:checked {
                background: rgba(52, 152, 219, 0.25);
                border-color: #3498db;
            }
            QPushButton:hover { background: rgba(52, 152, 219, 0.2); }
        """)
        self.btn_overlay.toggled.connect(self.overlay_toggled.emit)
        layout.addWidget(self.btn_overlay)

        # Version label
        version_lbl = QLabel("v1.0.0")
        version_lbl.setStyleSheet("color: #3c3c4e; font-size: 10px;")
        layout.addWidget(version_lbl)


class TrinkerMainWindow(QMainWindow):
    """
    Root application window.

    Layout:
      HeaderBar (branding + overlay toggle)
      QTabWidget:
        0: Library    — browse / import build orders
        1: Practice   — live session with timer and tracker
        2: Analytics  — dashboard, charts, history
        3: Settings   — preferences
      QStatusBar     — status messages

    The floating overlay (BuildOrderOverlay) is a separate top-level widget.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TRINKER — AoE2 Training Companion")
        self.setMinimumSize(1000, 680)
        self.resize(1280, 800)
        self._apply_theme()

        self._overlay: Optional[BuildOrderOverlay] = None
        self._pending_bo: Optional[BuildOrder] = None
        self._setup_menu()
        self._setup_ui()
        self._setup_hotkeys()

        # After startup, check if a new replay appeared from a recent game
        QTimer.singleShot(2000, self.practice_tab.check_for_new_replay)

        logger.info("TRINKER main window initialized (v%s).", get_app_version())

    # ── Theme ─────────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        self.setStyleSheet(DARK_STYLE if settings.theme == "dark" else LIGHT_STYLE)

    # ── Menu bar ──────────────────────────────────────────────────────────

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        act_import_url  = QAction("Import from buildorderguide.com URL…", self)
        act_import_url.triggered.connect(self._on_menu_import_url)
        act_import_file = QAction("Import from file (JSON/TXT)…", self)
        act_import_file.triggered.connect(self._on_menu_import_file)
        act_export      = QAction("Export all build orders…", self)
        act_export.triggered.connect(self._on_menu_export)
        act_quit        = QAction("Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_import_url)
        file_menu.addAction(act_import_file)
        file_menu.addSeparator()
        file_menu.addAction(act_export)
        file_menu.addSeparator()
        file_menu.addAction(act_quit)

        # View menu
        view_menu = menubar.addMenu("View")
        act_overlay = QAction("Toggle Overlay", self)
        act_overlay.setShortcut(settings.hotkey_toggle_overlay)
        act_overlay.triggered.connect(self._toggle_overlay)
        view_menu.addAction(act_overlay)

        act_library   = QAction("Library",   self); act_library.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        act_practice  = QAction("Practice",  self); act_practice.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        act_analytics = QAction("Analytics", self); act_analytics.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        view_menu.addSeparator()
        view_menu.addAction(act_library)
        view_menu.addAction(act_practice)
        view_menu.addAction(act_analytics)

        # Help menu
        help_menu = menubar.addMenu("Help")
        act_about = QAction("About TRINKER", self)
        act_about.triggered.connect(self._show_about)
        act_logs = QAction("Open Log File", self)
        act_logs.triggered.connect(self._open_logs)
        help_menu.addAction(act_about)
        help_menu.addAction(act_logs)

    # ── UI ────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        self.header = HeaderBar()
        self.header.overlay_toggled.connect(self._on_overlay_toggled)
        root.addWidget(self.header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.library_tab   = LibraryTab()
        self.practice_tab  = PracticeTab()
        self.analytics_tab = AnalyticsTab()
        self.settings_tab  = SettingsTab()

        self.tabs.addTab(self.library_tab,   "📚  Library")
        self.tabs.addTab(self.practice_tab,  "⏱  Practice")
        self.tabs.addTab(self.analytics_tab, "📊  Analytics")
        self.tabs.addTab(self.settings_tab,  "⚙  Settings")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self.tabs)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("TRINKER ready. Select a build order from the Library to begin.")

        # Wire signals
        self.library_tab.build_order_selected.connect(self._on_bo_selected)
        self.practice_tab.session_saved.connect(self._on_session_saved)
        self.settings_tab.settings_changed.connect(self._on_settings_changed)

    # ── Hotkeys ───────────────────────────────────────────────────────────

    def _setup_hotkeys(self) -> None:
        self._hk_overlay = QShortcut(QKeySequence(settings.hotkey_toggle_overlay), self)
        self._hk_overlay.activated.connect(self._toggle_overlay)

        self._hk_next = QShortcut(QKeySequence(settings.hotkey_next_step), self)
        self._hk_next.activated.connect(self._overlay_next_step)

        self._hk_prev = QShortcut(QKeySequence(settings.hotkey_prev_step), self)
        self._hk_prev.activated.connect(self._overlay_prev_step)

    # ── Overlay ───────────────────────────────────────────────────────────

    def _create_overlay(self) -> BuildOrderOverlay:
        overlay = BuildOrderOverlay()
        overlay.session_started.connect(
            lambda: self.status_bar.showMessage("Session started — good luck!")
        )
        overlay.session_stopped.connect(
            lambda: self.status_bar.showMessage("Session stopped. Don't forget to save!")
        )
        overlay.closed.connect(self._on_overlay_closed)
        self.practice_tab.set_overlay(overlay)
        if self._pending_bo:
            overlay.load_build_order(self._pending_bo)
            self._pending_bo = None
        return overlay

    def _toggle_overlay(self) -> None:
        self.header.btn_overlay.setChecked(not self.header.btn_overlay.isChecked())

    def _on_overlay_toggled(self, visible: bool) -> None:
        if visible:
            if self._overlay is None:
                self._overlay = self._create_overlay()
            self._overlay.show()
            self._overlay.raise_()
            self.header.btn_overlay.setText("⊟ Hide Overlay")
            self.status_bar.showMessage("Overlay shown. Drag it anywhere on screen.")
        else:
            if self._overlay:
                self._overlay.hide()
            self.header.btn_overlay.setText("⊞ Show Overlay")

    def _on_overlay_closed(self) -> None:
        self.header.btn_overlay.setChecked(False)
        self._overlay = None

    def _overlay_next_step(self) -> None:
        if self._overlay and self._overlay.isVisible():
            self._overlay.next_step()

    def _overlay_prev_step(self) -> None:
        if self._overlay and self._overlay.isVisible():
            self._overlay.prev_step()

    # ── Signal handlers ───────────────────────────────────────────────────

    def _on_bo_selected(self, bo: BuildOrder) -> None:
        """User selected a build order in the Library — load it everywhere."""
        logger.info("Build order selected: '%s'", bo.name)

        # Load into overlay (or queue for when overlay opens)
        if self._overlay:
            self._overlay.load_build_order(bo)
        else:
            self._pending_bo = bo

        # Pre-select in practice tab
        self.practice_tab.load_build_order(bo)

        # Switch to practice tab
        self.tabs.setCurrentIndex(1)
        self.status_bar.showMessage(f"Loaded: {bo.name} ({bo.civ}) — {bo.step_count} steps")

    def _on_session_saved(self, session) -> None:
        self.analytics_tab.refresh()
        self.status_bar.showMessage(
            f"Session saved! Accuracy: {session.accuracy_pct:.1f}%" if session.accuracy_pct else "Session saved."
        )

    def _on_tab_changed(self, index: int) -> None:
        if index == 0:   # Library
            self.library_tab.refresh()
        elif index == 1: # Practice
            self.practice_tab.refresh_build_orders()
            self.practice_tab.check_for_new_replay()
        elif index == 2: # Analytics
            self.analytics_tab.refresh()

    def _on_settings_changed(self) -> None:
        self._apply_theme()
        if self._overlay:
            self._overlay.set_opacity(settings.overlay_opacity)
        logger.info("Settings applied to main window.")

    # ── Menu actions ──────────────────────────────────────────────────────

    def _on_menu_import_url(self) -> None:
        self.tabs.setCurrentIndex(0)
        self.library_tab._on_import_url()

    def _on_menu_import_file(self) -> None:
        self.tabs.setCurrentIndex(0)
        self.library_tab._on_import_file()

    def _on_menu_export(self) -> None:
        from ..analytics.exporter import export_build_orders_json
        path = export_build_orders_json()
        QMessageBox.information(self, "Exported", f"Build orders exported to:\n{path}")

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "About TRINKER",
            "<h2>TRINKER</h2>"
            "<p><b>The Ultimate AoE2 Training Companion</b></p>"
            "<p>Version 1.0.0</p>"
            "<p>Practice smarter. Improve faster.</p>"
            "<hr>"
            "<p>Built with Python + PySide6<br>"
            "Data sources: buildorderguide.com, aoe2.gg community benchmarks</p>"
        )

    def _open_logs(self) -> None:
        from ..core.config import LOG_DIR
        import subprocess, sys
        log_file = LOG_DIR / "trinker.log"
        if not log_file.exists():
            QMessageBox.information(self, "No logs", f"Log file not found at:\n{log_file}")
            return
        try:
            if sys.platform == "win32":
                subprocess.Popen(["notepad", str(log_file)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(log_file)])
            else:
                subprocess.Popen(["xdg-open", str(log_file)])
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not open log file:\n{exc}")

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        """Save state and clean up on close."""
        settings.save()
        if self._overlay:
            self._overlay.close()
        logger.info("TRINKER closing.")
        super().closeEvent(event)
