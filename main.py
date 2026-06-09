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

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtCore import Qt

from src.core.logger import logger
from src.core.database import init_db
from src.core.config import settings


def _configure_app(app: QApplication) -> None:
    """Apply global Qt application settings before any window opens."""
    app.setApplicationName("TRINKER")
    app.setApplicationDisplayName("TRINKER — AoE2 Training Companion")
    app.setApplicationVersion("1.0.0")
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
    Redirect unhandled exceptions to both the logger and a user-visible dialog.
    Without this, crashes in PySide6 slots are silently swallowed on Windows.
    """
    original_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        # Show a message box if a QApplication exists
        app = QApplication.instance()
        if app:
            box = QMessageBox()
            box.setWindowTitle("TRINKER — Unexpected Error")
            box.setIcon(QMessageBox.Icon.Critical)
            box.setText(
                "<b>An unexpected error occurred.</b><br><br>"
                "Please check the log file for details, then restart TRINKER."
            )
            box.setDetailedText(msg)
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

    # Step 2: Create the Qt application
    app = QApplication(sys.argv)
    _configure_app(app)
    _install_exception_handler()

    # Step 3: Import and show the main window
    # Import here (after QApplication creation) to avoid Qt init errors
    from src.ui.main_window import TrinkerMainWindow

    window = TrinkerMainWindow()
    window.show()
    window.raise_()

    _maybe_enable_ollama_coach()

    logger.info("Main window shown. Entering Qt event loop.")


def _maybe_enable_ollama_coach() -> None:
    """If Ollama is running and AI coach is off, enable it once automatically."""
    if settings.ai_coach_enabled:
        return
    try:
        import requests
        resp = requests.get(f"{settings.ollama_url}/api/tags", timeout=2)
        if resp.status_code == 200:
            settings.ai_coach_enabled = True
            settings.save()
            logger.info("Ollama detected — AI Coach enabled automatically.")
    except Exception:
        pass

    # Step 4: Run the Qt event loop
    exit_code = app.exec()
    logger.info("TRINKER exited with code %d.", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
