"""
TRINKER - Settings Tab
User-configurable preferences: theme, overlay, hotkeys, AI coaching, data management.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.config import DATA_DIR, EXPORT_DIR, LOG_DIR, settings
from ..core.hotkeys import normalize_key_sequence, validate_hotkey_set
from ..core.logger import logger
from .hotkey_editor import HotkeyCaptureLineEdit
from .notifications import show_toast
from .theme import apply_tab_panel, get_tokens


class SettingsTab(QWidget):
    """
    Settings tab.

    Signals:
        settings_changed: Emitted whenever settings are saved.
    """

    settings_changed = Signal()
    theme_preview_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.apply_theme()
        self._populate()

    def apply_theme(self, theme_name: str | None = None) -> None:
        apply_tab_panel(self)
        t = get_tokens(theme_name)
        if hasattr(self, "btn_save"):
            self.btn_save.setStyleSheet(
                f"QPushButton {{ background: {t.selection}; color: {t.text_title}; "
                f"border: 1px solid {t.accent}; border-radius: 6px; padding: 8px 24px; "
                f"font-weight: bold; font-size: 13px; }}"
                f"QPushButton:hover {{ background: {t.accent_soft}; }}"
            )

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # ── Appearance ────────────────────────────────────────────────────
        appear_group = QGroupBox("Appearance")
        appear_form = QFormLayout(appear_group)
        appear_form.setSpacing(10)

        self.cb_theme = QComboBox()
        self.cb_theme.addItems(["dark", "light"])
        self.cb_theme.currentTextChanged.connect(self.theme_preview_changed.emit)
        appear_form.addRow("Theme", self.cb_theme)

        self.cb_ui_style = QComboBox()
        self.cb_ui_style.addItems(["medieval", "classic"])
        self.cb_ui_style.setToolTip("Medieval = parchment, gold, wood frames (dark theme only)")
        appear_form.addRow("UI Style", self.cb_ui_style)

        self.cb_civ_skin = QComboBox()
        from .medieval.palette import SKIN_NAMES

        self.cb_civ_skin.addItems(SKIN_NAMES)
        self.cb_civ_skin.setToolTip("Civ-themed color accents (medieval dark theme)")
        appear_form.addRow("Civ Theme", self.cb_civ_skin)

        self.sp_font = QSpinBox()
        self.sp_font.setRange(8, 22)
        self.sp_font.setSuffix(" px")
        appear_form.addRow("Font Size", self.sp_font)

        self.chk_simple_mode = QCheckBox(
            "Simple mode — hide advanced Practice panels (recommended)"
        )
        appear_form.addRow("", self.chk_simple_mode)

        self.ed_steam_id = QLineEdit()
        self.ed_steam_id.setPlaceholderText("Optional — for future ladder imports")
        appear_form.addRow("Steam ID", self.ed_steam_id)

        self.ed_replay_dir = QLineEdit()
        self.ed_replay_dir.setPlaceholderText("Extra replay folder (optional)")
        replay_row = QHBoxLayout()
        replay_row.addWidget(self.ed_replay_dir, 1)
        btn_browse_replay = QPushButton("Browse…")
        btn_browse_replay.setToolTip("Pick your AoE2 savegame or Age of Empires 2 DE folder")
        btn_browse_replay.clicked.connect(self._browse_replay_folder)
        replay_row.addWidget(btn_browse_replay)
        btn_scan_replays = QPushButton("Scan for Replays")
        btn_scan_replays.setToolTip("Find Documents, OneDrive, and Steam savegame folders automatically")
        btn_scan_replays.clicked.connect(self._scan_replay_folders)
        replay_row.addWidget(btn_scan_replays)
        appear_form.addRow("Replay folder", replay_row)

        self.lbl_replay_access = QLabel("")
        self.lbl_replay_access.setWordWrap(True)
        self.lbl_replay_access.setStyleSheet("color: #b8a88a; font-size: 11px;")
        appear_form.addRow("Replay access", self.lbl_replay_access)

        layout.addWidget(appear_group)

        # ── Overlay ───────────────────────────────────────────────────────
        overlay_group = QGroupBox("Overlay")
        overlay_form = QFormLayout(overlay_group)
        overlay_form.setSpacing(10)

        opacity_row = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(20, 100)
        self.slider_opacity.setTickInterval(5)
        self.lbl_opacity_val = QLabel("88%")
        self.slider_opacity.valueChanged.connect(lambda v: self.lbl_opacity_val.setText(f"{v}%"))
        opacity_row.addWidget(self.slider_opacity)
        opacity_row.addWidget(self.lbl_opacity_val)
        overlay_form.addRow("Opacity", opacity_row)

        self.chk_show_timings = QCheckBox("Show step timings")
        overlay_form.addRow("", self.chk_show_timings)

        self.chk_auto_advance = QCheckBox("Auto-advance steps (replay sync)")
        overlay_form.addRow("", self.chk_auto_advance)

        self.chk_auto_detect = QCheckBox(
            "Auto-detect games — import replays in the background (recommended)"
        )
        overlay_form.addRow("", self.chk_auto_detect)

        self.chk_sync_pause = QCheckBox("Pause overlay timer when AoE2 is paused")
        overlay_form.addRow("", self.chk_sync_pause)

        self.chk_auto_replay = QCheckBox(
            "Prompt to import last replay after a new game (manual mode)"
        )
        overlay_form.addRow("", self.chk_auto_replay)

        self.chk_postgame_coach = QCheckBox("Auto-run post-game AI coach after replay import")
        overlay_form.addRow("", self.chk_postgame_coach)

        self.chk_ocr = QCheckBox("Enable OCR capture (experimental — requires mss + easyocr)")
        overlay_form.addRow("", self.chk_ocr)

        self.chk_overlay_profile = QCheckBox("Log slow overlay ticks (performance profiling)")
        overlay_form.addRow("", self.chk_overlay_profile)
        layout.addWidget(overlay_group)

        # ── Hotkeys ───────────────────────────────────────────────────────
        hotkey_group = QGroupBox("Hotkeys")
        hotkey_form = QFormLayout(hotkey_group)
        hotkey_form.setSpacing(10)

        self.ed_hotkey_next = HotkeyCaptureLineEdit("e.g. Ctrl+Right")
        self.ed_hotkey_prev = HotkeyCaptureLineEdit("e.g. Ctrl+Left")
        self.ed_hotkey_overlay = HotkeyCaptureLineEdit("e.g. Ctrl+Shift+O")
        self.ed_hotkey_session = HotkeyCaptureLineEdit("e.g. Ctrl+Shift+S")

        hotkey_form.addRow("Next Step", self.ed_hotkey_next)
        hotkey_form.addRow("Previous Step", self.ed_hotkey_prev)
        hotkey_form.addRow("Toggle Overlay", self.ed_hotkey_overlay)
        hotkey_form.addRow("Pause/Resume Overlay Timer", self.ed_hotkey_session)

        self.chk_global_hotkeys = QCheckBox("Global hotkeys while playing (Windows)")
        hotkey_form.addRow("", self.chk_global_hotkeys)

        hotkey_hint = QLabel(
            "Click a field, then press the key combination. "
            "Global hotkeys (Windows) work while AoE2 is focused."
        )
        hotkey_hint.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        hotkey_hint.setWordWrap(True)
        layout.addWidget(hotkey_group)
        layout.addWidget(hotkey_hint)

        # ── AI Coaching ───────────────────────────────────────────────────
        ai_group = QGroupBox("AI Coaching (optional — offline tips always available)")
        ai_form = QFormLayout(ai_group)
        ai_form.setSpacing(10)

        self.lbl_ollama_status = QLabel("Checking Ollama…")
        self.lbl_ollama_status.setWordWrap(True)
        ai_form.addRow("Status", self.lbl_ollama_status)

        self.chk_ai_enabled = QCheckBox("Enable AI Coach (auto-enabled when Ollama is running)")
        ai_form.addRow("", self.chk_ai_enabled)

        self.chk_rag = QCheckBox("Use local AoE2 knowledge base (RAG)")
        self.chk_rag.setToolTip("Injects guides from data/knowledge/ into coach prompts")
        ai_form.addRow("", self.chk_rag)

        self.ed_ollama_url = QLineEdit()
        self.ed_ollama_url.setPlaceholderText("http://localhost:11434")
        ai_form.addRow("Ollama URL", self.ed_ollama_url)

        self.ed_ollama_model = QLineEdit()
        self.ed_ollama_model.setPlaceholderText("llama3")
        ai_form.addRow("Model name", self.ed_ollama_model)

        btn_test_ai = QPushButton("Test Connection")
        btn_test_ai.clicked.connect(self._test_ollama)
        ai_form.addRow("", btn_test_ai)

        btn_setup = QPushButton("Run Ollama Setup Script")
        btn_setup.clicked.connect(self._run_ollama_setup)
        ai_form.addRow("", btn_setup)

        ai_hint = QLabel(
            "Download Ollama from https://ollama.ai — or use Setup Script to pull llama3.2.\n"
            "RAG adds local AoE2 guides to coach prompts automatically."
        )
        ai_hint.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        ai_hint.setWordWrap(True)
        layout.addWidget(ai_group)
        layout.addWidget(ai_hint)

        # ── Privacy ───────────────────────────────────────────────────────
        privacy_group = QGroupBox("Privacy")
        privacy_form = QFormLayout(privacy_group)
        self.chk_telemetry = QCheckBox("Allow anonymous usage telemetry (opt-in)")
        self.chk_telemetry.setStyleSheet("color: #ecf0f1;")
        privacy_form.addRow("", self.chk_telemetry)
        telemetry_hint = QLabel(
            "If enabled, anonymous events are written locally to telemetry.jsonl in your TRINKER "
            "data folder. No personal data is sent until a future sync server exists."
        )
        telemetry_hint.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        telemetry_hint.setWordWrap(True)
        layout.addWidget(privacy_group)
        layout.addWidget(telemetry_hint)

        # ── Data management ───────────────────────────────────────────────
        data_group = QGroupBox("Data & Storage")
        data_layout = QVBoxLayout(data_group)
        data_layout.setSpacing(8)

        def _path_row(label: str, path: Path) -> QHBoxLayout:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{label}:"))
            lbl = QLabel(str(path))
            lbl.setStyleSheet("color: #7f8c8d; font-size: 10px;")
            lbl.setWordWrap(True)
            row.addWidget(lbl, stretch=1)
            btn = QPushButton("Open")
            btn.setFixedWidth(60)
            btn.clicked.connect(lambda checked, p=path: _open_dir(p))
            row.addWidget(btn)
            return row

        data_layout.addLayout(_path_row("Data directory", DATA_DIR))
        data_layout.addLayout(_path_row("Logs", LOG_DIR))
        data_layout.addLayout(_path_row("Exports", EXPORT_DIR))
        layout.addWidget(data_group)

        # ── Save button ───────────────────────────────────────────────────
        save_row = QHBoxLayout()
        btn_save = QPushButton("💾 Save Settings")
        self.btn_save = btn_save
        btn_save.clicked.connect(self._save)
        btn_reset = QPushButton("↺ Reset to Defaults")
        btn_reset.clicked.connect(self._reset_defaults)
        save_row.addWidget(btn_save)
        save_row.addWidget(btn_reset)
        save_row.addStretch()
        layout.addLayout(save_row)

        layout.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll)

    def _populate(self) -> None:
        """Load current settings into widgets."""
        idx = self.cb_theme.findText(settings.theme)
        self.cb_theme.setCurrentIndex(max(0, idx))
        ui_idx = self.cb_ui_style.findText(getattr(settings, "ui_style", "medieval"))
        self.cb_ui_style.setCurrentIndex(max(0, ui_idx))
        skin_idx = self.cb_civ_skin.findText(getattr(settings, "civ_skin", "default"))
        self.cb_civ_skin.setCurrentIndex(max(0, skin_idx))
        self.sp_font.setValue(settings.font_size)
        self.slider_opacity.setValue(int(settings.overlay_opacity * 100))
        self.chk_show_timings.setChecked(settings.show_timings)
        self.chk_auto_advance.setChecked(settings.auto_advance)
        self.chk_auto_detect.setChecked(settings.auto_detect_sessions)
        self.chk_sync_pause.setChecked(settings.overlay_sync_game_pause)
        self.chk_auto_replay.setChecked(settings.auto_prompt_new_replay)
        self.chk_postgame_coach.setChecked(settings.auto_postgame_coach)
        self.chk_ocr.setChecked(settings.ocr_capture_enabled)
        self.chk_overlay_profile.setChecked(settings.overlay_profile_enabled)
        self.chk_simple_mode.setChecked(settings.simple_mode)
        self.ed_steam_id.setText(settings.steam_id)
        if settings.replay_dirs:
            self.ed_replay_dir.setText(settings.replay_dirs[0])
        self._refresh_replay_access()
        self.ed_hotkey_next.set_hotkey(settings.hotkey_next_step)
        self.ed_hotkey_prev.set_hotkey(settings.hotkey_prev_step)
        self.ed_hotkey_overlay.set_hotkey(settings.hotkey_toggle_overlay)
        self.ed_hotkey_session.set_hotkey(settings.hotkey_start_session)
        self.chk_ai_enabled.setChecked(settings.ai_coach_enabled)
        self.chk_rag.setChecked(settings.rag_enabled)
        self.chk_global_hotkeys.setChecked(settings.global_hotkeys_enabled)
        self.ed_ollama_url.setText(settings.ollama_url)
        self.ed_ollama_model.setText(settings.ollama_model)
        self.chk_telemetry.setChecked(settings.telemetry_opt_in)
        self._refresh_ollama_status()

    def _refresh_ollama_status(self) -> None:
        from ..services.coach_service import ollama_setup_status

        st = ollama_setup_status()
        if st["running"]:
            self.lbl_ollama_status.setText(
                f"● Online — {st['url']} · model: {st['model']}"
            )
            self.lbl_ollama_status.setStyleSheet("color: #6aab55; font-weight: bold;")
        else:
            self.lbl_ollama_status.setText(
                "○ Offline — rule-based tips and RAG guides still work without Ollama."
            )
            self.lbl_ollama_status.setStyleSheet("color: #b8a88a;")

    def _save(self) -> None:
        hotkeys = {
            "next_step": self.ed_hotkey_next.hotkey(),
            "prev_step": self.ed_hotkey_prev.hotkey(),
            "toggle_overlay": self.ed_hotkey_overlay.hotkey(),
            "pause_timer": self.ed_hotkey_session.hotkey(),
        }
        errors = validate_hotkey_set(hotkeys)
        if errors:
            show_toast(errors[0], "error", 6000)
            QMessageBox.warning(self, "Invalid Hotkeys", "\n".join(errors))
            return

        settings.theme = self.cb_theme.currentText()
        settings.ui_style = self.cb_ui_style.currentText()
        settings.civ_skin = self.cb_civ_skin.currentText()
        settings.font_size = self.sp_font.value()
        settings.overlay_opacity = self.slider_opacity.value() / 100.0
        settings.show_timings = self.chk_show_timings.isChecked()
        settings.auto_advance = self.chk_auto_advance.isChecked()
        settings.auto_detect_sessions = self.chk_auto_detect.isChecked()
        settings.overlay_sync_game_pause = self.chk_sync_pause.isChecked()
        settings.auto_prompt_new_replay = self.chk_auto_replay.isChecked()
        settings.auto_postgame_coach = self.chk_postgame_coach.isChecked()
        settings.ocr_capture_enabled = self.chk_ocr.isChecked()
        settings.overlay_profile_enabled = self.chk_overlay_profile.isChecked()
        settings.simple_mode = self.chk_simple_mode.isChecked()
        settings.steam_id = self.ed_steam_id.text().strip()
        extra = self.ed_replay_dir.text().strip()
        if extra:
            from ..core.replay_paths import register_replay_folder

            register_replay_folder(extra, save=False)
        settings.hotkey_next_step = normalize_key_sequence(hotkeys["next_step"])
        settings.hotkey_prev_step = normalize_key_sequence(hotkeys["prev_step"])
        settings.hotkey_toggle_overlay = normalize_key_sequence(hotkeys["toggle_overlay"])
        settings.hotkey_start_session = normalize_key_sequence(hotkeys["pause_timer"])
        settings.ai_coach_enabled = self.chk_ai_enabled.isChecked()
        settings.rag_enabled = self.chk_rag.isChecked()
        settings.global_hotkeys_enabled = self.chk_global_hotkeys.isChecked()
        settings.ollama_url = self.ed_ollama_url.text().strip() or "http://localhost:11434"
        settings.ollama_model = self.ed_ollama_model.text().strip() or "llama3"
        settings.telemetry_opt_in = self.chk_telemetry.isChecked()
        settings.save()
        self._refresh_replay_access()
        self.settings_changed.emit()
        logger.info("Settings saved.")

    def _reset_defaults(self) -> None:
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from ..core.config import SETTINGS_FILE, AppSettings

            SETTINGS_FILE.unlink(missing_ok=True)
            # Re-create defaults in place
            defaults = AppSettings()
            for field in defaults.__dataclass_fields__:
                setattr(settings, field, getattr(defaults, field))
            settings.save()
            self._populate()
            self.settings_changed.emit()
            show_toast("Settings reset to defaults.", "info")

    def _test_ollama(self) -> None:
        url = self.ed_ollama_url.text().strip() or settings.ollama_url
        try:
            import requests

            resp = requests.get(f"{url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                msg = f"Connected! Models: {', '.join(models) or 'none pulled yet'}"
                show_toast("Ollama connected.", "success")
                QMessageBox.information(self, "Ollama Connected", msg)
            else:
                show_toast(f"Ollama HTTP {resp.status_code}", "error")
                QMessageBox.warning(self, "Ollama Error", f"HTTP {resp.status_code}")
        except Exception as exc:
            show_toast("Cannot connect to Ollama.", "error")
            QMessageBox.warning(
                self,
                "Cannot connect to Ollama",
                f"{exc}\n\nMake sure Ollama is running: https://ollama.ai",
            )
        self._refresh_ollama_status()


    def _run_ollama_setup(self) -> None:
        import subprocess
        import sys
        from pathlib import Path

        script = Path(__file__).resolve().parent.parent.parent / "scripts" / "setup_ollama.py"
        if not script.exists():
            QMessageBox.warning(self, "Setup", f"Script not found:\n{script}")
            return
        try:
            subprocess.Popen([sys.executable, str(script)], cwd=str(script.parent.parent))
            show_toast("Ollama setup started in a new console window.", "info")
        except Exception as exc:
            QMessageBox.warning(self, "Setup", str(exc))

    def _refresh_replay_access(self) -> None:
        from ..core.replay_paths import probe_replay_access

        report = probe_replay_access()
        if report.readable:
            self.lbl_replay_access.setText(
                f"✓ {report.replay_count} replay(s) readable — newest: {report.newest_replay or '—'}"
            )
            self.lbl_replay_access.setStyleSheet("color: #6aab55; font-size: 11px;")
        else:
            hint = report.messages[0] if report.messages else "No replays found yet."
            self.lbl_replay_access.setText(f"○ {hint}")
            self.lbl_replay_access.setStyleSheet("color: #b8a88a; font-size: 11px;")

    def _browse_replay_folder(self) -> None:
        start = self.ed_replay_dir.text().strip()
        path = QFileDialog.getExistingDirectory(
            self,
            "Select AoE2 Replay Folder",
            start or str(Path.home() / "Documents"),
        )
        if not path:
            return
        self.ed_replay_dir.setText(path)
        from ..core.replay_paths import register_replay_folder

        if register_replay_folder(path):
            show_toast("Replay folder registered.", "success")
        self._refresh_replay_access()

    def _scan_replay_folders(self) -> None:
        from ..core.replay_paths import ensure_replay_folders

        report = ensure_replay_folders(save=True)
        if settings.replay_dirs:
            self.ed_replay_dir.setText(settings.replay_dirs[0])
        self._refresh_replay_access()
        if report.readable:
            show_toast(
                f"Found {report.replay_count} replay(s) in {len(report.search_roots)} folder(s).",
                "success",
            )
            QMessageBox.information(
                self,
                "Replay Access",
                f"TRINKER can read your game files.\n\n"
                f"Replays found: {report.replay_count}\n"
                f"Newest: {report.newest_replay or '—'}\n\n"
                f"Folders scanned: {len(report.search_roots)}",
            )
        else:
            QMessageBox.warning(
                self,
                "Replay Access",
                "No .aoe2record files found yet.\n\n"
                "1. Play a game in AoE2 DE, then click Scan again.\n"
                "2. Or use Browse to pick your savegame folder manually.\n\n"
                "Typical path:\n"
                "Documents\\My Games\\Age of Empires 2 DE\\<SteamID>\\savegame",
            )


def _open_dir(path: Path) -> None:
    """Open a directory in the system file manager."""
    import subprocess
    import sys

    path.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:
        logger.warning("Could not open directory: %s", exc)
