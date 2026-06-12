"""
TRINKER - Main Application Window
Tabbed main window with: Start Here, Library, Analytics, Settings, and Overlay control.
Wires all tabs and the overlay together with signals.
"""

from typing import Optional

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..analytics.session import get_practice_streak
from ..build_orders.models import BuildOrder
from ..core.config import get_app_version, is_sandbox_mode, settings
from ..core.global_hotkeys import GlobalHotkeyManager
from ..core.logger import logger
from .analytics_tab import AnalyticsTab
from .dashboard_tab import DashboardTab
from .library_tab import LibraryTab
from .medieval.icons import Icon
from .notifications import ToastHost, set_toast_host, show_toast
from .overlay import BuildOrderOverlay
from .quick_start_tab import QuickStartTab
from .settings_tab import SettingsTab
from .theme import (
    apply_main_window,
    get_tokens,
    stylesheet_header_bar,
    stylesheet_overlay_toggle,
)
from .training_tab import TrainingTab


class HeaderBar(QFrame):
    """Compact header strip above the tabs with branding and overlay toggle."""

    overlay_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self._logo: Optional[QLabel] = None
        self._subtitle: Optional[QLabel] = None
        self._version_lbl: Optional[QLabel] = None
        self._overlay_visible = False
        self._setup_ui()
        self.apply_theme()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        self._logo = QLabel(f"{Icon.TRINKER} TRINKER")
        self._subtitle = QLabel("AoE2 Training Companion")
        layout.addWidget(self._logo)
        layout.addWidget(self._subtitle)
        layout.addStretch()

        self.btn_overlay = QPushButton(f"{Icon.OVERLAY} Show Overlay")
        self.btn_overlay.setCheckable(True)
        self.btn_overlay.setToolTip("Toggle the in-game build order overlay (customize hotkey in Settings)")
        self.btn_overlay.toggled.connect(self.overlay_toggled.emit)
        layout.addWidget(self.btn_overlay)

        self.lbl_streak = QLabel("")
        self.lbl_streak.setToolTip("Consecutive days with at least one saved game")
        layout.addWidget(self.lbl_streak)

        self._version_lbl = QLabel(f"v{get_app_version()}")
        layout.addWidget(self._version_lbl)

    def apply_theme(self, theme_name: Optional[str] = None) -> None:
        t = get_tokens(theme_name)
        self.setStyleSheet(stylesheet_header_bar(t))
        if self._logo:
            self._logo.setStyleSheet(
                f"color: {t.accent}; font-size: 16px; font-weight: bold; letter-spacing: 4px;"
            )
        if self._subtitle:
            self._subtitle.setStyleSheet(
                f"color: {t.text_muted}; font-size: 11px; margin-left: 2px;"
            )
        if self._version_lbl:
            self._version_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px;")
        if self.lbl_streak:
            self.lbl_streak.setStyleSheet(
                f"color: {t.success if t.medieval else t.accent}; "
                f"font-size: 10px; font-weight: bold; padding: 0 8px;"
            )
        self.btn_overlay.setStyleSheet(stylesheet_overlay_toggle(t))
        self.refresh_streak()

    def refresh_streak(self) -> None:
        streak = get_practice_streak()
        current = streak.get("current", 0)
        if current > 0:
            self.lbl_streak.setText(f"🔥 {current}d streak")
        else:
            self.lbl_streak.setText("")


class TrinkerMainWindow(QMainWindow):
    """
    Root application window.

    Layout:
      HeaderBar (branding + overlay toggle)
      QTabWidget:
        0: Start Here  — pick build, show overlay
        1: Library     — browse / import build orders
        2: Analytics   — history, charts, coach reports
        3: Settings    — preferences
      QStatusBar
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TRINKER — AoE2 Training Companion")
        self.setMinimumSize(1000, 680)
        self.resize(1280, 800)
        self._apply_theme()

        self._overlay: Optional[BuildOrderOverlay] = None
        self._pending_bo: Optional[BuildOrder] = None
        self._shortcuts: list[QShortcut] = []
        self._toast_host: Optional[ToastHost] = None
        self._global_hotkeys: Optional[GlobalHotkeyManager] = None
        self.practice_tab: Optional[QWidget] = None
        self._setup_menu()
        self._setup_ui()
        self._setup_hotkeys()
        self._setup_background_services()
        from ..plugins.loader import load_plugins

        load_plugins()

        self._global_hotkeys = GlobalHotkeyManager(self)
        self._global_hotkeys.set_callback("toggle_overlay", self._toggle_overlay)
        self._global_hotkeys.set_callback("next_step", self._overlay_next_step)
        self._global_hotkeys.set_callback("prev_step", self._overlay_prev_step)
        self._global_hotkeys.set_callback("pause_timer", self._overlay_toggle_pause)

        logger.info("TRINKER main window initialized (v%s).", get_app_version())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._global_hotkeys:
            self._global_hotkeys.register()

    def _apply_theme(self, theme_name: Optional[str] = None) -> None:
        name = theme_name or settings.theme
        apply_main_window(self)
        if hasattr(self, "header"):
            self.header.apply_theme(name)
        if getattr(self, "_sandbox_banner", None):
            t = get_tokens(name)
            self._sandbox_banner.setStyleSheet(
                f"background: {t.warning}; color: {t.text}; font-size: 11px; "
                f"font-weight: bold; padding: 6px 12px; border-bottom: 1px solid {t.border};"
            )
        for tab in (
            getattr(self, "quick_start_tab", None),
            getattr(self, "dashboard_tab", None),
            getattr(self, "training_tab", None),
            getattr(self, "library_tab", None),
            getattr(self, "analytics_tab", None),
            getattr(self, "settings_tab", None),
            getattr(self, "practice_tab", None),
        ):
            if tab and hasattr(tab, "apply_theme"):
                tab.apply_theme(name)

    def _preview_theme(self, theme_name: str) -> None:
        """Live preview from Settings without saving."""
        self._apply_theme(theme_name)

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        act_import_url = QAction("Import from buildorderguide.com URL…", self)
        act_import_url.triggered.connect(self._on_menu_import_url)
        act_import_file = QAction("Import from file (JSON/TXT)…", self)
        act_import_file.triggered.connect(self._on_menu_import_file)
        act_export = QAction("Export all build orders…", self)
        act_export.triggered.connect(self._on_menu_export)
        act_quit = QAction("Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_import_url)
        file_menu.addAction(act_import_file)
        file_menu.addSeparator()
        file_menu.addAction(act_export)
        file_menu.addSeparator()
        file_menu.addAction(act_quit)

        view_menu = menubar.addMenu("View")
        act_overlay = QAction("Toggle Overlay", self)
        act_overlay.setShortcut(settings.hotkey_toggle_overlay)
        act_overlay.triggered.connect(self._toggle_overlay)
        view_menu.addAction(act_overlay)

        act_start = QAction("Start Here", self)
        act_start.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        act_dashboard = QAction("Dashboard", self)
        act_dashboard.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        act_training = QAction("Training", self)
        act_training.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        act_library = QAction("Library", self)
        act_library.triggered.connect(lambda: self.tabs.setCurrentIndex(3))
        act_analytics = QAction("Analytics", self)
        act_analytics.triggered.connect(lambda: self.tabs.setCurrentIndex(4))
        view_menu.addAction(act_start)
        view_menu.addSeparator()
        view_menu.addAction(act_dashboard)
        view_menu.addAction(act_training)
        view_menu.addAction(act_library)
        view_menu.addAction(act_analytics)

        help_menu = menubar.addMenu("Help")
        act_about = QAction("About TRINKER", self)
        act_about.triggered.connect(self._show_about)
        act_logs = QAction("Open Log File", self)
        act_logs.triggered.connect(self._open_logs)
        help_menu.addAction(act_about)
        help_menu.addAction(act_logs)
        act_setup = QAction("Run Setup Wizard Again…", self)
        act_setup.triggered.connect(self._run_setup_wizard)
        help_menu.addAction(act_setup)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = HeaderBar()
        self.header.overlay_toggled.connect(self._on_overlay_toggled)
        root.addWidget(self.header)

        if is_sandbox_mode():
            self._sandbox_banner = QLabel(
                "SANDBOX — fake training data only. Your real games are not used."
            )
            self._sandbox_banner.setObjectName("sandboxBanner")
            self._sandbox_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.addWidget(self._sandbox_banner)
            self.setWindowTitle("TRINKER [SANDBOX] — AoE2 Training Companion")
        else:
            self._sandbox_banner = None

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.quick_start_tab = QuickStartTab()
        self.dashboard_tab = DashboardTab()
        self.training_tab = TrainingTab()
        self.library_tab = LibraryTab()
        self.analytics_tab = AnalyticsTab()
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.quick_start_tab, "▶  Start Here")
        self.tabs.addTab(self.dashboard_tab, "📈  Dashboard")
        self.tabs.addTab(self.training_tab, "🎯  Training")
        self.tabs.addTab(self.library_tab, "📚  Library")
        self.tabs.addTab(self.analytics_tab, "📊  Analytics")
        self.tabs.addTab(self.settings_tab, "⚙  Settings")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            "Start Here → pick a build → Show Overlay & Play. Games auto-save to Analytics."
        )

        self.quick_start_tab.play_requested.connect(self._on_quick_start_play)
        self.quick_start_tab.import_replay_requested.connect(self._on_quick_start_import)
        self.quick_start_tab.bulk_import_done.connect(self.analytics_tab.refresh)
        self.training_tab.play_drill_requested.connect(lambda: self.tabs.setCurrentIndex(0))
        self.library_tab.build_order_selected.connect(self._on_bo_selected)
        self.settings_tab.settings_changed.connect(self._on_settings_changed)
        self.settings_tab.theme_preview_changed.connect(self._preview_theme)

        self._practice_tab_index: Optional[int] = None
        self._sync_practice_tab()

        self._toast_host = ToastHost(central)
        set_toast_host(self._toast_host)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._toast_host:
            self._toast_host.reposition()

    def _setup_hotkeys(self) -> None:
        self._reload_hotkeys()

    def _reload_hotkeys(self) -> None:
        for shortcut in self._shortcuts:
            shortcut.deleteLater()
        self._shortcuts.clear()

        self._shortcuts.append(QShortcut(QKeySequence(settings.hotkey_toggle_overlay), self))
        self._shortcuts[-1].activated.connect(self._toggle_overlay)

        self._shortcuts.append(QShortcut(QKeySequence(settings.hotkey_next_step), self))
        self._shortcuts[-1].activated.connect(self._overlay_next_step)

        self._shortcuts.append(QShortcut(QKeySequence(settings.hotkey_prev_step), self))
        self._shortcuts[-1].activated.connect(self._overlay_prev_step)

        self._shortcuts.append(QShortcut(QKeySequence(settings.hotkey_start_session), self))
        self._shortcuts[-1].activated.connect(self._overlay_toggle_pause)

    def _create_overlay(self) -> BuildOrderOverlay:
        overlay = BuildOrderOverlay()
        overlay.session_started.connect(
            lambda: self.status_bar.showMessage("Overlay timer running — pauses with the game.")
        )
        overlay.session_stopped.connect(
            lambda: self.status_bar.showMessage(
                "Overlay closed. Finished games auto-save to Analytics."
            )
        )
        overlay.closed.connect(self._on_overlay_closed)
        if self._pending_bo:
            overlay.load_build_order(self._pending_bo)
            self._pending_bo = None
        if hasattr(self, "practice_tab") and self.practice_tab:
            self.practice_tab.overlay = overlay
        return overlay

    def _sync_practice_tab(self) -> None:
        """Show advanced Practice tab when simple_mode is off."""
        from .practice_tab import PracticeTab

        want = not settings.simple_mode
        has = hasattr(self, "practice_tab") and self.practice_tab is not None

        if want and not has:
            self.practice_tab = PracticeTab(overlay=self._overlay)
            self.practice_tab.session_saved.connect(self.analytics_tab.refresh)
            self._practice_tab_index = self.tabs.insertTab(3, self.practice_tab, "⏱  Practice")
        elif not want and has:
            idx = self.tabs.indexOf(self.practice_tab)
            if idx >= 0:
                self.tabs.removeTab(idx)
            self.practice_tab.deleteLater()
            self.practice_tab = None
            self._practice_tab_index = None
        elif want and has and self._overlay:
            self.practice_tab.overlay = self._overlay

    def _toggle_overlay(self) -> None:
        self.header.btn_overlay.setChecked(not self.header.btn_overlay.isChecked())

    def _on_overlay_toggled(self, visible: bool) -> None:
        if visible:
            if self._overlay is None:
                self._overlay = self._create_overlay()
            self._overlay.show()
            self._overlay.raise_()
            self.header.btn_overlay.setText("⊟ Hide Overlay")
            self.status_bar.showMessage("Overlay shown. Timer syncs when you pause AoE2.")
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

    def _overlay_toggle_pause(self) -> None:
        if self._overlay and self._overlay.isVisible():
            paused = self._overlay.toggle_timer_pause()
            msg = "Overlay timer paused." if paused else "Overlay timer resumed."
            self.status_bar.showMessage(msg)

    def _setup_background_services(self) -> None:
        """Ollama health check + automatic replay import."""
        from ..core.ollama import ensure_ollama_enabled

        self._auto_import_timer = QTimer(self)
        self._auto_import_timer.setInterval(45_000)
        self._auto_import_timer.timeout.connect(self._poll_auto_import)
        if settings.auto_detect_sessions:
            self._auto_import_timer.start()
            QTimer.singleShot(5_000, self._poll_auto_import)

        self._ollama_timer = QTimer(self)
        self._ollama_timer.setInterval(60_000)
        self._ollama_timer.timeout.connect(ensure_ollama_enabled)
        self._ollama_timer.start()
        ensure_ollama_enabled()

    def _poll_auto_import(self) -> None:
        from ..core.auto_session import try_auto_import_latest_replay

        if not settings.auto_detect_sessions:
            return
        bo_id = settings.last_practice_bo_id
        result = try_auto_import_latest_replay(preferred_bo_id=bo_id)
        if not result.imported:
            return
        self.analytics_tab.refresh()
        self.dashboard_tab.refresh()
        self.header.refresh_streak()
        show_toast(result.message, "success")
        self.status_bar.showMessage(result.message)
        if settings.auto_postgame_coach and settings.ai_coach_enabled:
            self._run_silent_postgame_coach(result)

    def _run_silent_postgame_coach(self, auto_result) -> None:
        from ..ai_coach.postgame import create_postgame_worker
        from ..build_orders.manager import get_build_order

        bo = get_build_order(auto_result.build_order_id) if auto_result.build_order_id else None
        strategy = bo.strategy if bo else ""
        bo_name = bo.name if bo else ""

        thread = QThread(self)
        worker = create_postgame_worker(
            auto_result.replay_path,
            auto_result.civ,
            strategy,
            auto_result.build_order_id,
            bo_name,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(
            lambda r: self._on_silent_postgame_done(r, auto_result.build_order_id)
        )
        worker.error.connect(lambda e: logger.warning("Silent post-game coach: %s", e))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _on_silent_postgame_done(self, result, build_order_id: Optional[int]) -> None:
        from ..ai_coach.postgame import pin_overlay_alert

        if not result.overlay_alert:
            return
        pin_overlay_alert(result.overlay_alert, build_order_id)
        if self._overlay and self._overlay._build_order:
            self._overlay._show_coach_alert(self._overlay._build_order)
            self._overlay.tabs.setCurrentIndex(2)
        self.status_bar.showMessage(f"Coach tip for next game: {result.overlay_alert}")

    def _on_bo_selected(self, bo: BuildOrder) -> None:
        logger.info("Build order selected: '%s'", bo.name)

        if self._overlay:
            self._overlay.load_build_order(bo)
        else:
            self._pending_bo = bo

        settings.last_practice_bo_id = bo.id
        settings.save()
        self.tabs.setCurrentIndex(0)
        self.quick_start_tab.refresh()
        self.status_bar.showMessage(f"Loaded: {bo.name} ({bo.civ}) — open overlay and play")

    def _on_tab_changed(self, index: int) -> None:
        # Revert unsaved theme preview when switching tabs
        self._apply_theme()
        if index == 0:
            self.quick_start_tab.refresh()
        elif index == 1:
            self.dashboard_tab.refresh()
            self.header.refresh_streak()
        elif index == 2:
            self.training_tab.refresh()
        elif index == 3:
            self.library_tab.refresh()
        elif index == 4:
            self.analytics_tab.refresh()

    def _on_settings_changed(self) -> None:
        self._apply_theme()
        self._sync_practice_tab()
        if self._overlay:
            self._overlay.set_opacity(settings.overlay_opacity)
            if hasattr(self._overlay, "apply_theme"):
                self._overlay.apply_theme()
        self._reload_hotkeys()
        if self._global_hotkeys:
            self._global_hotkeys.register()
        if settings.auto_detect_sessions:
            if not self._auto_import_timer.isActive():
                self._auto_import_timer.start()
        else:
            self._auto_import_timer.stop()
        show_toast("Settings saved.", "success")
        logger.info("Settings applied to main window.")

    def _on_quick_start_play(self, bo: BuildOrder) -> None:
        if self._overlay:
            self._overlay.load_build_order(bo)
        else:
            self._pending_bo = bo
        if not self.header.btn_overlay.isChecked():
            self.header.btn_overlay.setChecked(True)
        self._on_overlay_toggled(True)
        self.status_bar.showMessage(
            f"Playing: {bo.name} — follow the overlay. TRINKER saves the game when you finish."
        )

    def _on_quick_start_import(self) -> None:
        from ..core.auto_session import try_auto_import_latest_replay
        from ..replay.parser import get_latest_replay

        result = try_auto_import_latest_replay(
            preferred_bo_id=self.quick_start_tab.selected_build_id(),
        )
        if result.imported:
            self.analytics_tab.refresh()
            self.dashboard_tab.refresh()
            self.header.refresh_streak()
            self.tabs.setCurrentIndex(1)
            self.status_bar.showMessage(result.message)
        elif get_latest_replay():
            self.tabs.setCurrentIndex(1)
            self.dashboard_tab.refresh()
            self.header.refresh_streak()
            self.status_bar.showMessage(
                "Latest game already saved — check Analytics for history and coach tips."
            )
        else:
            self.status_bar.showMessage(
                "No replays found yet. Play a game — TRINKER will detect it automatically."
            )

    def _on_menu_import_url(self) -> None:
        self.tabs.setCurrentIndex(2)
        self.library_tab._on_import_url()

    def _on_menu_import_file(self) -> None:
        self.tabs.setCurrentIndex(2)
        self.library_tab._on_import_file()

    def _on_menu_export(self) -> None:
        from ..analytics.exporter import export_build_orders_json

        path = export_build_orders_json()
        QMessageBox.information(self, "Exported", f"Build orders exported to:\n{path}")

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About TRINKER",
            "<h2>TRINKER</h2>"
            "<p><b>The Ultimate AoE2 Training Companion</b></p>"
            f"<p>Version {get_app_version()}</p>"
            "<p>Practice smarter. Improve faster.</p>"
            "<hr>"
            "<p>Built with Python + PySide6<br>"
            "Data sources: buildorderguide.com, aoe2.gg community benchmarks</p>",
        )

    def _run_setup_wizard(self) -> None:
        from .onboarding_wizard import run_onboarding

        if run_onboarding(self):
            show_toast("Setup updated.", "success")
            self._apply_theme()

    def _open_logs(self) -> None:
        import subprocess
        import sys

        from ..core.config import LOG_DIR

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

    def closeEvent(self, event) -> None:
        if self._global_hotkeys:
            self._global_hotkeys.unregister()
        settings.save()
        if self._overlay:
            self._overlay.close()
        logger.info("TRINKER closing.")
        super().closeEvent(event)
