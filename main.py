"""
TRINKER - Application Entry Point
Initializes the database, sets up PySide6 application styling,
and launches the main window.

Usage:
    python main.py

Packaging:
    pyinstaller --onefile --windowed --name TRINKER main.py
"""

import sys
import traceback
from pathlib import Path

# Ensure the project root is on sys.path when run directly
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from src.core.config import get_app_version, settings
from src.core.database import init_db
from src.core.logger import logger


def _configure_app(app: QApplication) -> None:
    """Apply global Qt application settings before any window opens."""
    app.setApplicationName("TRINKER")
    app.setApplicationDisplayName("TRINKER — AoE2 Training Companion")
    app.setApplicationVersion(get_app_version())
    app.setOrganizationName("TRINKER")
    app.setOrganizationDomain("trinker.app")

    # Set a clean base font
    from src.core.config import settings

    font = QFont("Segoe UI", settings.font_size)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)

    # Force Fusion style for consistent cross-platform rendering
    app.setStyle("Fusion")


def _install_exception_handler() -> None:
    """
    Redirect unhandled exceptions to both the logger and a user-visible toast.
    Without this, crashes in PySide6 slots are silently swallowed on Windows.
    """
    from src.core.config import LOG_DIR
    from src.core.errors import user_friendly_message

    original_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        msg = user_friendly_message(exc_value)
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        app = QApplication.instance()
        if app:
            try:
                from src.ui.notifications import show_toast

                show_toast(msg, "error", 8000)
            except Exception:
                pass
            box = QMessageBox()
            box.setWindowTitle("TRINKER — Unexpected Error")
            box.setIcon(QMessageBox.Icon.Critical)
            box.setText(f"<b>{msg}</b><br><br>Log file: {LOG_DIR / 'trinker.log'}")
            box.setDetailedText(detail)
            box.exec()
        original_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def main() -> int:
    """
    Application main function.

    Returns:
        Exit code (0 = success, non-zero = error).
    """
    logger.info("=" * 60)
    logger.info("TRINKER starting — Python %s", sys.version.split()[0])

    # Step 1: Initialize the database (creates tables + seeds reference data)
    try:
        init_db()
    except Exception as exc:
        logger.critical("Failed to initialize database: %s", exc, exc_info=True)
        print(f"[FATAL] Database init failed: {exc}", file=sys.stderr)
        return 1

    try:
        from scripts.sync_buildorderguide import maybe_background_sync

        maybe_background_sync()
    except Exception as exc:
        logger.debug("Buildorderguide background sync skipped: %s", exc)

    # Step 1b: Auto-discover AoE2 replay folders (Documents / OneDrive / savegame)
    try:
        from src.core.replay_paths import ensure_replay_folders

        ensure_replay_folders(save=True)
    except Exception as exc:
        logger.warning("Replay folder discovery skipped: %s", exc)

    # Step 2: Create the Qt application
    app = QApplication(sys.argv)
    _configure_app(app)
    _install_exception_handler()

    # Step 3: Optional onboarding wizard, then main window
    if not settings.onboarding_complete:
        from src.ui.onboarding_wizard import run_onboarding

        if not run_onboarding():
            logger.info("Onboarding cancelled.")
            return 0

    from src.ui.main_window import TrinkerMainWindow

    window = TrinkerMainWindow()
    window.show()
    window.raise_()

    from src.core.ollama import ensure_ollama_enabled

    ensure_ollama_enabled()

    logger.info("Main window shown. Entering Qt event loop.")
    exit_code = app.exec()
    logger.info("TRINKER exited with code %d.", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
