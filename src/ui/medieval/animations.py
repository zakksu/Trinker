"""
Lightweight micro-animations — short durations, no continuous timers.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


def fade_in(widget: QWidget, duration_ms: int = 220) -> None:
    """Fade widget in on show."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def pulse_once(widget: QWidget, duration_ms: int = 180) -> None:
    """Brief opacity pulse for value updates."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(1.0)
    anim.setKeyValueAt(0.5, 0.65)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def stagger_fade_in(widgets: list[QWidget], delay_ms: int = 40) -> None:
    """Stagger fade-in for dashboard cards."""
    for i, w in enumerate(widgets):
        QTimer.singleShot(i * delay_ms, lambda ww=w: fade_in(ww))
