from typing import Callable, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPropertyAnimation,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


class Anim:
    DURATION_INSTANT = 80
    DURATION_FAST = 150
    DURATION_NORMAL = 250
    DURATION_SLOW = 350
    DURATION_PANEL = 400

    DEFAULT_EASING = QEasingCurve.InOutCubic
    EASE_OUT = QEasingCurve.OutCubic
    EASE_IN = QEasingCurve.InCubic
    EASE_IN_OUT = QEasingCurve.InOutCubic
    EASE_OUT_BACK = QEasingCurve.OutBack
    EASE_OUT_ELASTIC = QEasingCurve.OutElastic

    @staticmethod
    def _ensure_opacity_effect(widget: QWidget) -> QGraphicsOpacityEffect:
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        return effect

    @staticmethod
    def _animation(
        target: QObject,
        prop_name: bytes,
        start,
        end,
        duration: int,
        easing: QEasingCurve,
        on_finished: Optional[Callable] = None,
    ) -> QPropertyAnimation:
        anim = QPropertyAnimation(target, prop_name)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(easing)
        if on_finished is not None:
            anim.finished.connect(on_finished)
        return anim

    @classmethod
    def fade_in(
        cls,
        widget: QWidget,
        duration: int = DURATION_FAST,
        easing: QEasingCurve = EASE_IN_OUT,
        on_finished: Optional[Callable] = None,
    ) -> QPropertyAnimation:
        effect = cls._ensure_opacity_effect(widget)
        return cls._animation(
            effect, b"opacity", 0.0, 1.0, duration, easing, on_finished
        )

    @classmethod
    def fade_out(
        cls,
        widget: QWidget,
        duration: int = DURATION_FAST,
        easing: QEasingCurve = EASE_IN_OUT,
        on_finished: Optional[Callable] = None,
    ) -> QPropertyAnimation:
        effect = cls._ensure_opacity_effect(widget)
        return cls._animation(
            effect, b"opacity", 1.0, 0.0, duration, easing, on_finished
        )

    @classmethod
    def expand_horizontal(
        cls,
        widget: QWidget,
        target_width: int,
        duration: int = DURATION_NORMAL,
        easing: QEasingCurve = EASE_OUT,
        on_finished: Optional[Callable] = None,
    ) -> QPropertyAnimation:
        if widget.maximumWidth() < target_width:
            widget.setMaximumWidth(target_width)
        return cls._animation(
            widget,
            b"maximumWidth",
            widget.maximumWidth(),
            target_width,
            duration,
            easing,
            on_finished,
        )
