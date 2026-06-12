"""
TRINKER - First-run onboarding wizard.
Collects replay folder, Steam ID, Ollama settings, and first build order.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from ..build_orders.manager import get_all_build_orders
from ..core.config import DATA_DIR, get_replay_search_dirs, settings
from ..core.logger import logger
from ..core.ollama import ensure_ollama_enabled, is_ollama_running
from ..replay.parser import find_replay_files
from .medieval.icons import Icon
from .theme import apply_tab_panel, get_tokens


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to TRINKER")
        self.setSubTitle("Your AoE2 training companion — overlay, auto-save, and AI coaching.")

        layout = QVBoxLayout(self)
        intro = QLabel(
            f"{Icon.TRINKER} This quick setup takes about a minute.\n\n"
            "TRINKER will:\n"
            "• Show build order steps on a game overlay\n"
            "• Auto-detect finished games and save them to Analytics\n"
            "• Connect to Ollama for post-game coaching (optional)"
        )
        intro.setWordWrap(True)
        intro.setToolTip("You can re-run setup anytime from Settings.")
        layout.addWidget(intro)


class ReplayFolderPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Find Your Replays")
        self.setSubTitle("TRINKER watches this folder for new games.")

        layout = QVBoxLayout(self)
        self.lbl_hint = QLabel(
            "We look for .aoe2record files under your AoE2 DE save folder."
        )
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setToolTip("Default: Documents/My Games/Age of Empires 2 DE on Windows")
        layout.addWidget(self.lbl_hint)

        self.list_dirs = QListWidget()
        self.list_dirs.setToolTip("Folders TRINKER scans for new replays after each game")
        layout.addWidget(self.list_dirs)

        row = QHBoxLayout()
        self.ed_folder = QLineEdit()
        self.ed_folder.setPlaceholderText("Optional extra replay folder…")
        self.ed_folder.setToolTip("Add a custom folder if your replays live elsewhere")
        btn_browse = QPushButton("Browse…")
        btn_browse.setToolTip("Pick any folder containing .aoe2record files")
        btn_browse.clicked.connect(self._browse)
        row.addWidget(self.ed_folder)
        row.addWidget(btn_browse)
        layout.addLayout(row)

        self.lbl_count = QLabel("")
        layout.addWidget(self.lbl_count)

        self.registerField("replay_folder", self.ed_folder)

    def initializePage(self) -> None:
        self.list_dirs.clear()
        for p in get_replay_search_dirs():
            self.list_dirs.addItem(str(p))
        count = len(find_replay_files())
        self.lbl_count.setText(f"Found {count} replay(s) in search paths.")

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select AoE2 Replay Folder")
        if path:
            self.ed_folder.setText(path)


class SteamIdPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Steam ID (Optional)")
        self.setSubTitle("For future ladder stats and match imports from aoe2.gg.")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Your Steam ID is the 17-digit number in your replay folder path, e.g.\n"
            "…\\Age of Empires 2 DE\\76561198278846899\\savegame\\\n\n"
            "Leave blank to skip — you can add it later in Settings."
        ))
        self.ed_steam = QLineEdit()
        self.ed_steam.setPlaceholderText("76561198000000000")
        self.ed_steam.setToolTip(
            "17-digit Steam ID from your replay path — used for aoe2.gg ladder import"
        )
        layout.addWidget(self.ed_steam)
        self.registerField("steam_id", self.ed_steam)


class OllamaPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("AI Coach (Ollama)")
        self.setSubTitle("Local AI coaching — nothing leaves your PC.")

        layout = QVBoxLayout(self)
        self.lbl_status = QLabel("Checking Ollama…")
        layout.addWidget(self.lbl_status)

        self.ed_url = QLineEdit(settings.ollama_url)
        self.ed_url.setToolTip("Default local Ollama server — usually http://localhost:11434")
        layout.addWidget(QLabel("Ollama URL"))
        layout.addWidget(self.ed_url)

        self.ed_model = QLineEdit(settings.ollama_model)
        self.ed_model.setToolTip("Model you pulled with `ollama pull`, e.g. llama3 or llama3.2")
        layout.addWidget(QLabel("Model name"))
        layout.addWidget(self.ed_model)

        btn_test = QPushButton("Test Connection")
        btn_test.setToolTip("Verify Ollama is running before you finish setup")
        btn_test.clicked.connect(self._test)
        layout.addWidget(btn_test)

        self.registerField("ollama_url", self.ed_url)
        self.registerField("ollama_model", self.ed_model)

    def initializePage(self) -> None:
        if is_ollama_running():
            self.lbl_status.setText("Ollama detected — AI coach will auto-enable.")
        else:
            self.lbl_status.setText(
                "Ollama not running. Install from ollama.ai and run: ollama pull llama3"
            )

    def _test(self) -> None:
        settings.ollama_url = self.ed_url.text().strip()
        if ensure_ollama_enabled():
            QMessageBox.information(self, "Connected", "Ollama is ready.")
        else:
            QMessageBox.warning(self, "Not Connected", "Could not reach Ollama at that URL.")


class FirstBuildPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Pick Your First Build")
        self.setSubTitle("Choose one build order to practice — you can change anytime.")

        layout = QVBoxLayout(self)
        self.cb_bo = QComboBox()
        self.cb_bo.setToolTip("Starter build orders — change anytime on Start Here")
        for bo in get_all_build_orders():
            self.cb_bo.addItem(f"{bo.name} ({bo.civ})", bo.id)
        layout.addWidget(self.cb_bo)


class DonePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Ready to Play")
        self.setSubTitle("Open Start Here, pick your build, and show the overlay.")

        layout = QVBoxLayout(self)
        done = QLabel(
            f"{Icon.OVERLAY} After each game TRINKER auto-saves your replay to Analytics.\n"
            f"{Icon.DASHBOARD} Check the Dashboard tab for stats, badges, and coach tips.\n\n"
            f"Your data folder:\n{DATA_DIR}"
        )
        done.setWordWrap(True)
        layout.addWidget(done)


class OnboardingWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TRINKER Setup")
        self.setMinimumSize(560, 420)
        apply_tab_panel(self)
        t = get_tokens()
        self.setStyleSheet(self.styleSheet() + f"""
            QWizard {{ background: {t.bg_window}; color: {t.text}; }}
            QWizardPage {{ background: {t.bg_window}; }}
        """)

        self.addPage(WelcomePage())
        self.addPage(ReplayFolderPage())
        self.addPage(SteamIdPage())
        self.addPage(OllamaPage())
        self._build_page = FirstBuildPage()
        self.addPage(self._build_page)
        self.addPage(DonePage())

        self.setButtonText(QWizard.WizardButton.FinishButton, "Start TRINKER")
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)

    def accept(self) -> None:
        extra = self.field("replay_folder").strip()
        if extra:
            from ..core.replay_paths import register_replay_folder

            register_replay_folder(extra, save=False)

        settings.steam_id = self.field("steam_id").strip()
        settings.ollama_url = self.field("ollama_url").strip() or settings.ollama_url
        settings.ollama_model = self.field("ollama_model").strip() or settings.ollama_model
        bo_id = self._build_page.cb_bo.currentData()
        if bo_id:
            settings.last_practice_bo_id = int(bo_id)
        settings.onboarding_complete = True
        settings.save()
        ensure_ollama_enabled()
        logger.info("Onboarding complete.")
        super().accept()


def run_onboarding(parent=None) -> bool:
    """Show wizard; returns True if user finished setup."""
    wizard = OnboardingWizard(parent)
    return wizard.exec() == QWizard.DialogCode.Accepted
