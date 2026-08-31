from typing import Callable, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    Qt,
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
    def fade_in_start(cls, widget: QWidget) -> None:
        effect = cls._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        widget.show()
        cls.fade_in(widget).start()

    @classmethod
    def fade_out_and_hide(
        cls,
        widget: QWidget,
        duration: int = DURATION_FAST,
        on_finished: Optional[Callable] = None,
    ) -> QPropertyAnimation:
        def _hide():
            widget.hide()

        anim = cls.fade_out(widget, duration=duration, on_finished=on_finished or _hide)
        return anim

    @classmethod
    def slide_to(
        cls,
        widget: QWidget,
        target_pos: QPoint,
        duration: int = DURATION_NORMAL,
        easing: QEasingCurve = EASE_OUT,
        on_finished: Optional[Callable] = None,
    ) -> QPropertyAnimation:
        return cls._animation(
            widget, b"pos", widget.pos(), target_pos, duration, easing, on_finished
        )

    @classmethod
    def resize_to(
        cls,
        widget: QWidget,
        target_size,
        duration: int = DURATION_NORMAL,
        easing: QEasingCurve = EASE_OUT,
        on_finished: Optional[Callable] = None,
    ) -> QPropertyAnimation:
        return cls._animation(
            widget,
            b"size",
            widget.size(),
            target_size,
            duration,
            easing,
            on_finished,
        )

    @classmethod
    def slide_in_panel(
        cls,
        widget: QWidget,
        direction: str = "left",
        duration: int = DURATION_PANEL,
        on_finished: Optional[Callable] = None,
    ) -> QPropertyAnimation:
        if not widget.parent():
            raise ValueError("slide_in_panel requires widget with a parent")

        parent_rect = widget.parent().rect()
        if direction == "left":
            start_pos = QPoint(-widget.width(), widget.y())
            end_pos = QPoint(0, widget.y())
        elif direction == "right":
            start_pos = QPoint(parent_rect.width(), widget.y())
            end_pos = QPoint(parent_rect.width() - widget.width(), widget.y())
        elif direction == "top":
            start_pos = QPoint(widget.x(), -widget.height())
            end_pos = QPoint(widget.x(), 0)
        elif direction == "bottom":
            start_pos = QPoint(widget.x(), parent_rect.height())
            end_pos = QPoint(widget.x(), parent_rect.height() - widget.height())
        else:
            raise ValueError(f"Unknown direction: {direction}")

        widget.move(start_pos)
        widget.show()
        anim = cls._animation(
            widget, b"pos", start_pos, end_pos, duration, cls.EASE_OUT, on_finished
        )
        return anim

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

    @classmethod
    def parallel(cls, *anims: QPropertyAnimation) -> QParallelAnimationGroup:
        group = QParallelAnimationGroup()
        for a in anims:
            group.addAnimation(a)
        return group

    @classmethod
    def sequential(cls, *anims: QPropertyAnimation) -> QSequentialAnimationGroup:
        group = QSequentialAnimationGroup()
        for a in anims:
            group.addAnimation(a)
        return group
