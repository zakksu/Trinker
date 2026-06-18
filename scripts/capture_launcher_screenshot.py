#!/usr/bin/env python3
"""Capture launcher hub screenshot for verification."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from launcher import TrinkerLauncher


def main() -> int:
    app = QApplication(sys.argv)
    win = TrinkerLauncher()
    out = ROOT / "assets" / "launcher_screenshot.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    def _snap() -> None:
        win.show()
        win.repaint()
        app.processEvents()
        win.grab().save(str(out))
        print(f"Saved {out}")
        app.quit()

    QTimer.singleShot(500, _snap)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
