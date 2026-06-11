"""
TRINKER - Hotkey capture line edit for Settings.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QLineEdit

from ..core.hotkeys import is_valid_hotkey, normalize_key_sequence
from .theme import get_tokens


class HotkeyCaptureLineEdit(QLineEdit):
    """
    Click the field, then press the desired key combination.
    Escape clears capture; Backspace clears the hotkey.
    """

    capture_finished = Signal(str)

    def __init__(self, placeholder: str = "Click then press keys…", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setReadOnly(True)
        self._capturing = False
        t = get_tokens()
        self.setStyleSheet(f"""
            HotkeyCaptureLineEdit {{
                background: {t.bg_input};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 5px 8px;
                color: {t.text};
            }}
            HotkeyCaptureLineEdit[capturing="true"] {{
                border-color: {t.accent};
                background: {t.bg_elevated};
            }}
        """)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self._capturing = True
        self.setProperty("capturing", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setPlaceholderText("Press key combination…")

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self._capturing = False
        self.setProperty("capturing", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setPlaceholderText("Click then press keys…")

    def keyPressEvent(self, event) -> None:
        if not self._capturing:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.clearFocus()
            return
        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.clear()
            self.capture_finished.emit("")
            self.clearFocus()
            return

        # Ignore lone modifier keys
        if key in (
            Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt,
            Qt.Key.Key_Meta, Qt.Key.Key_AltGr,
        ):
            return

        combo = event.keyCombination()
        text = QKeySequence(combo).toString(QKeySequence.SequenceFormat.PortableText)
        if text and is_valid_hotkey(text):
            normalized = normalize_key_sequence(text)
            self.setText(normalized)
            self.capture_finished.emit(normalized)
            self.clearFocus()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.setFocus()

    def set_hotkey(self, text: str) -> None:
        self.setText(normalize_key_sequence(text))

    def hotkey(self) -> str:
        return normalize_key_sequence(self.text())
