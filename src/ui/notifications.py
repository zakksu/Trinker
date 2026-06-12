"""
TRINKER - Non-blocking toast notifications.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

from .medieval.palette import get_palette
from .theme import get_tokens


class ToastWidget(QWidget):
    """Single auto-dismissing notification bubble."""

    def __init__(self, message: str, level: str = "info", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        t = get_tokens()
        p = get_palette()
        if t.medieval:
            colors = {
                "info": (p.gold, "rgba(201, 162, 39, 0.18)"),
                "success": (p.success, "rgba(106, 171, 85, 0.18)"),
                "warning": (p.warning, "rgba(212, 160, 23, 0.18)"),
                "error": (p.error, "rgba(181, 74, 74, 0.18)"),
            }
            border_radius = "10px"
            text_color = p.ink
        else:
            colors = {
                "info": (t.accent, t.accent_soft),
                "success": (t.success, "rgba(46, 204, 113, 0.15)"),
                "warning": (t.warning, "rgba(241, 196, 15, 0.15)"),
                "error": (t.error, "rgba(231, 76, 60, 0.15)"),
            }
            border_radius = "8px"
            text_color = t.text
        border, bg = colors.get(level, colors["info"])

        self.setStyleSheet(f"""
            ToastWidget {{
                background: {bg};
                border: 2px solid {border};
                border-radius: {border_radius};
                padding: 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lbl.setMaximumWidth(360)
        lbl.setStyleSheet(f"color: {text_color}; font-size: 12px;")
        layout.addWidget(lbl)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity = 1.0

    def get_opacity(self) -> float:
        return self._opacity

    def set_opacity(self, value: float) -> None:
        self._opacity = value
        self._opacity_effect.setOpacity(value)

    opacity = Property(float, get_opacity, set_opacity)

    def fade_out_and_close(self) -> None:
        anim = QPropertyAnimation(self, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.finished.connect(self.deleteLater)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


class ToastHost(QWidget):
    """Anchors toasts to the bottom-right of a parent window."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._toasts: list[ToastWidget] = []
        self._margin = 16
        self._spacing = 8

    def show_toast(self, message: str, level: str = "info", duration_ms: int = 4500) -> None:
        toast = ToastWidget(message, level, self)
        toast.show()
        self._toasts.append(toast)
        self._reposition()
        QTimer.singleShot(duration_ms, toast.fade_out_and_close)
        QTimer.singleShot(duration_ms + 350, self._prune_toasts)

    def _prune_toasts(self) -> None:
        self._toasts = [t for t in self._toasts if t.isVisible()]
        self._reposition()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        self.setGeometry(parent.rect())
        y = parent.height() - self._margin
        for toast in reversed(self._toasts):
            if not toast.isVisible():
                continue
            toast.adjustSize()
            w, h = toast.width(), toast.height()
            x = parent.width() - w - self._margin
            y -= h
            toast.move(x, y)
            y -= self._spacing

    def reposition(self) -> None:
        """Call when parent resizes."""
        self._reposition()


# Module-level host set by main window at startup
_toast_host: Optional[ToastHost] = None


def set_toast_host(host: ToastHost) -> None:
    global _toast_host
    _toast_host = host


def show_toast(message: str, level: str = "info", duration_ms: int = 4500) -> None:
    """Show a toast if a host is registered; otherwise no-op."""
    if _toast_host:
        _toast_host.show_toast(message, level, duration_ms)
