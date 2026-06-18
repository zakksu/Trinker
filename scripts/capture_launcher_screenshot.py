#!/usr/bin/env python3
"""Capture a PNG screenshot of the TRINKER launcher (headless-friendly)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from launcher import TrinkerLauncher


def main() -> int:
    app = QApplication(sys.argv)
    out = ROOT / "assets" / "launcher_screenshot.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    w = TrinkerLauncher()
    w.show()

    def _capture() -> None:
        pix = w.grab()
        pix.save(str(out))
        print(str(out))
        app.quit()

    QTimer.singleShot(600, _capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
