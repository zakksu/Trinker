"""
TRINKER - Settings Tab
User-configurable preferences: theme, overlay, hotkeys, AI coaching, data management.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QGroupBox, QFormLayout, QSlider, QCheckBox, QSpinBox,
    QFrame, QScrollArea, QMessageBox, QDoubleSpinBox,
)

from ..core.config import settings, DATA_DIR, LOG_DIR, EXPORT_DIR
from ..core.logger import logger

STYLE = """
QWidget { background: #111113; color: #ecf0f1; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #1e1e22; border: 1px solid #2c2c2e;
    border-radius: 6px; padding: 5px 8px; color: #ecf0f1;
}
QGroupBox {
    border: 1px solid #2c2c2e; border-radius: 8px;
    margin-top: 10px; padding: 12px 10px 10px 10px;
}
QGroupBox::title { color: #7f8c8d; padding: 0 8px; font-size: 11px; letter-spacing: 1px; }
QPushButton {
    background: #1e1e22; border: 1px solid #2c2c2e;
    border-radius: 6px; padding: 6px 14px; color: #ecf0f1;
}
QPushButton:hover { background: #25252c; border-color: #3498db; }
QCheckBox { color: #ecf0f1; spacing: 8px; }
QSlider::groove:horizontal {
    background: #2c2c2e; height: 6px; border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #3498db; width: 16px; height: 16px; margin: -5px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal { background: #3498db; border-radius: 3px; }
"""


class SettingsTab(QWidget):
    """
    Settings tab.

    Signals:
        settings_changed: Emitted whenever settings are saved.
    """

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLE)
        self._setup_ui()
        self._populate()

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
        appear_form.addRow("Theme", self.cb_theme)

        self.sp_font = QSpinBox()
        self.sp_font.setRange(8, 22)
        self.sp_font.setSuffix(" px")
        appear_form.addRow("Font Size", self.sp_font)

        self.chk_simple_mode = QCheckBox("Simple mode — hide advanced Practice panels (recommended)")
        appear_form.addRow("", self.chk_simple_mode)
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
        self.slider_opacity.valueChanged.connect(
            lambda v: self.lbl_opacity_val.setText(f"{v}%")
        )
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

        self.chk_auto_replay = QCheckBox("Prompt to import last replay after a new game (manual mode)")
        overlay_form.addRow("", self.chk_auto_replay)

        self.chk_postgame_coach = QCheckBox("Auto-run post-game AI coach after replay import")
        overlay_form.addRow("", self.chk_postgame_coach)

        self.chk_ocr = QCheckBox("Enable OCR capture (experimental — requires mss + easyocr)")
        overlay_form.addRow("", self.chk_ocr)
        layout.addWidget(overlay_group)

        # ── Hotkeys ───────────────────────────────────────────────────────
        hotkey_group = QGroupBox("Hotkeys")
        hotkey_form = QFormLayout(hotkey_group)
        hotkey_form.setSpacing(10)

        self.ed_hotkey_next    = QLineEdit(); self.ed_hotkey_next.setPlaceholderText("e.g. Ctrl+Right")
        self.ed_hotkey_prev    = QLineEdit(); self.ed_hotkey_prev.setPlaceholderText("e.g. Ctrl+Left")
        self.ed_hotkey_overlay = QLineEdit(); self.ed_hotkey_overlay.setPlaceholderText("e.g. Ctrl+Shift+O")
        self.ed_hotkey_session = QLineEdit(); self.ed_hotkey_session.setPlaceholderText("e.g. Ctrl+Shift+S")

        hotkey_form.addRow("Next Step",       self.ed_hotkey_next)
        hotkey_form.addRow("Previous Step",   self.ed_hotkey_prev)
        hotkey_form.addRow("Toggle Overlay",  self.ed_hotkey_overlay)
        hotkey_form.addRow("Pause/Resume Overlay Timer", self.ed_hotkey_session)

        hotkey_hint = QLabel("Note: Hotkeys require the app window to be focused on most platforms.")
        hotkey_hint.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        hotkey_hint.setWordWrap(True)
        layout.addWidget(hotkey_group)
        layout.addWidget(hotkey_hint)

        # ── AI Coaching ───────────────────────────────────────────────────
        ai_group = QGroupBox("AI Coaching (requires Ollama)")
        ai_form  = QFormLayout(ai_group)
        ai_form.setSpacing(10)

        self.chk_ai_enabled = QCheckBox("Enable AI Coach (auto-enabled when Ollama is running)")
        ai_form.addRow("", self.chk_ai_enabled)

        self.ed_ollama_url = QLineEdit()
        self.ed_ollama_url.setPlaceholderText("http://localhost:11434")
        ai_form.addRow("Ollama URL", self.ed_ollama_url)

        self.ed_ollama_model = QLineEdit()
        self.ed_ollama_model.setPlaceholderText("llama3")
        ai_form.addRow("Model name", self.ed_ollama_model)

        btn_test_ai = QPushButton("Test Connection")
        btn_test_ai.clicked.connect(self._test_ollama)
        ai_form.addRow("", btn_test_ai)

        ai_hint = QLabel(
            "Download Ollama from https://ollama.ai and run: ollama pull llama3\n"
            "The AI coach analyzes your sessions and suggests improvements."
        )
        ai_hint.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        ai_hint.setWordWrap(True)
        layout.addWidget(ai_group)
        layout.addWidget(ai_hint)

        # ── Privacy ───────────────────────────────────────────────────────
        privacy_group = QGroupBox("Privacy")
        privacy_form  = QFormLayout(privacy_group)
        self.chk_telemetry = QCheckBox("Allow anonymous usage telemetry (opt-in)")
        self.chk_telemetry.setStyleSheet("color: #ecf0f1;")
        privacy_form.addRow("", self.chk_telemetry)
        telemetry_hint = QLabel(
            "If enabled, aggregate (non-identifiable) build order popularity data may be "
            "submitted to a future TRINKER server. No personal data is ever sent."
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
        data_layout.addLayout(_path_row("Logs",           LOG_DIR))
        data_layout.addLayout(_path_row("Exports",        EXPORT_DIR))
        layout.addWidget(data_group)

        # ── Save button ───────────────────────────────────────────────────
        save_row = QHBoxLayout()
        btn_save = QPushButton("💾 Save Settings")
        btn_save.setStyleSheet(
            "QPushButton { background: #1c3a5c; color: #3498db; border: 1px solid #2c5a8c; "
            "border-radius: 6px; padding: 8px 24px; font-weight: bold; font-size: 13px; }"
            "QPushButton:hover { background: #264d7a; }"
        )
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
        self.sp_font.setValue(settings.font_size)
        self.slider_opacity.setValue(int(settings.overlay_opacity * 100))
        self.chk_show_timings.setChecked(settings.show_timings)
        self.chk_auto_advance.setChecked(settings.auto_advance)
        self.chk_auto_detect.setChecked(settings.auto_detect_sessions)
        self.chk_sync_pause.setChecked(settings.overlay_sync_game_pause)
        self.chk_auto_replay.setChecked(settings.auto_prompt_new_replay)
        self.chk_postgame_coach.setChecked(settings.auto_postgame_coach)
        self.chk_ocr.setChecked(settings.ocr_capture_enabled)
        self.chk_simple_mode.setChecked(settings.simple_mode)
        self.ed_hotkey_next.setText(settings.hotkey_next_step)
        self.ed_hotkey_prev.setText(settings.hotkey_prev_step)
        self.ed_hotkey_overlay.setText(settings.hotkey_toggle_overlay)
        self.ed_hotkey_session.setText(settings.hotkey_start_session)
        self.chk_ai_enabled.setChecked(settings.ai_coach_enabled)
        self.ed_ollama_url.setText(settings.ollama_url)
        self.ed_ollama_model.setText(settings.ollama_model)
        self.chk_telemetry.setChecked(settings.telemetry_opt_in)

    def _save(self) -> None:
        settings.theme          = self.cb_theme.currentText()
        settings.font_size      = self.sp_font.value()
        settings.overlay_opacity = self.slider_opacity.value() / 100.0
        settings.show_timings   = self.chk_show_timings.isChecked()
        settings.auto_advance   = self.chk_auto_advance.isChecked()
        settings.auto_detect_sessions = self.chk_auto_detect.isChecked()
        settings.overlay_sync_game_pause = self.chk_sync_pause.isChecked()
        settings.auto_prompt_new_replay = self.chk_auto_replay.isChecked()
        settings.auto_postgame_coach = self.chk_postgame_coach.isChecked()
        settings.ocr_capture_enabled = self.chk_ocr.isChecked()
        settings.simple_mode = self.chk_simple_mode.isChecked()
        settings.hotkey_next_step      = self.ed_hotkey_next.text().strip()
        settings.hotkey_prev_step      = self.ed_hotkey_prev.text().strip()
        settings.hotkey_toggle_overlay = self.ed_hotkey_overlay.text().strip()
        settings.hotkey_start_session  = self.ed_hotkey_session.text().strip()
        settings.ai_coach_enabled = self.chk_ai_enabled.isChecked()
        settings.ollama_url   = self.ed_ollama_url.text().strip() or "http://localhost:11434"
        settings.ollama_model = self.ed_ollama_model.text().strip() or "llama3"
        settings.telemetry_opt_in = self.chk_telemetry.isChecked()
        settings.save()
        self.settings_changed.emit()
        logger.info("Settings saved.")
        QMessageBox.information(self, "Saved", "Settings saved successfully.")

    def _reset_defaults(self) -> None:
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from ..core.config import AppSettings, SETTINGS_FILE
            SETTINGS_FILE.unlink(missing_ok=True)
            import importlib, src.core.config as cfg_mod
            # Re-create defaults in place
            defaults = AppSettings()
            for field in defaults.__dataclass_fields__:
                setattr(settings, field, getattr(defaults, field))
            settings.save()
            self._populate()
            self.settings_changed.emit()

    def _test_ollama(self) -> None:
        url = self.ed_ollama_url.text().strip() or settings.ollama_url
        try:
            import requests
            resp = requests.get(f"{url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                msg = f"Connected!\nAvailable models: {', '.join(models) or 'none pulled yet'}"
                QMessageBox.information(self, "Ollama Connected", msg)
            else:
                QMessageBox.warning(self, "Ollama Error", f"HTTP {resp.status_code}")
        except Exception as exc:
            QMessageBox.warning(
                self, "Cannot connect to Ollama",
                f"{exc}\n\nMake sure Ollama is running: https://ollama.ai"
            )


def _open_dir(path: Path) -> None:
    """Open a directory in the system file manager."""
    import subprocess, sys
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
