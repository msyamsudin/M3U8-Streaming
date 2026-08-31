from typing import List, Optional

from PySide6.QtCore import (
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import QEnterEvent, QFont, QMouseEvent
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from src.app.theme.animations import Anim


class Toast(QWidget):
    """A transient notification that slides in, auto-dismisses, and
    supports hover-to-pause and click-to-dismiss.

    The toast is parented to the application's main window and positioned
    along its bottom edge. Multiple toasts stack vertically.
    """

    ICONS = {
        "info": "\u2139",
        "success": "\u2714",
        "warning": "!",
        "error": "\u2716",
    }

    COLORS = {
        "info": "#007ACC",
        "success": "#4CAF50",
        "warning": "#FFA500",
        "error": "#ff4444",
    }

    DEFAULT_TIMEOUT = 3000
    FADE_DURATION = 200
    SLIDE_OFFSET = 30

    dismissed = Signal()

    def __init__(
        self,
        message: str,
        kind: str = "info",
        timeout_ms: int = DEFAULT_TIMEOUT,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("toastWidget")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(Qt.SubWindow)
        self.setMouseTracking(True)

        self._kind = kind
        self._timeout = int(timeout_ms)
        self._remaining_ms = int(timeout_ms)

        # Animation refs MUST be held to keep Python wrappers alive
        self._slide_in_anim: Optional[QPropertyAnimation] = None
        self._fade_in_anim: Optional[QPropertyAnimation] = None
        self._dismiss_group: Optional[QParallelAnimationGroup] = None
        self._timer: Optional[QTimer] = None
        self._hovered: bool = False
        self._dismissing: bool = False

        # Content
        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 10, 16, 10)
        outer.setSpacing(10)

        icon_label = QLabel(self.ICONS.get(kind, self.ICONS["info"]))
        icon_font = QFont("Segoe UI Symbol", 12)
        icon_font.setBold(True)
        icon_label.setFont(icon_font)
        icon_label.setStyleSheet(f"color: {self.COLORS.get(kind, '#007ACC')};")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedWidth(18)
        outer.addWidget(icon_label, 0, Qt.AlignVCenter)

        self._text_label = QLabel(message)
        self._text_label.setObjectName("toastMessage")
        self._text_label.setStyleSheet("color: #fafafa;")
        self._text_label.setWordWrap(False)
        self._text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self._text_label, 1, Qt.AlignVCenter)

        close_btn = QLabel("\u2715")
        close_btn.setStyleSheet("color: #71717a; padding: 0 4px;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.mousePressEvent = lambda _e: self.dismiss()
        outer.addWidget(close_btn, 0, Qt.AlignVCenter)

        self.setStyleSheet(
            f"""
            QWidget#toastWidget {{
                background-color: rgba(20, 20, 20, 235);
                border-left: 3px solid {self.COLORS.get(kind, '#007ACC')};
                border-top: 1px solid #1a1a1a;
                border-right: 1px solid #1a1a1a;
                border-bottom: 1px solid #1a1a1a;
                border-radius: 6px;
            }}
            QWidget#toastWidget:hover {{
                background-color: rgba(30, 30, 30, 240);
            }}
            """
        )

        self.setMaximumWidth(380)
        self.setMinimumWidth(220)
        self.adjustSize()

        # Opacity effect (reused by Anim helper)
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

    # ------------------------------------------------------------------ public
    def show_toast(self) -> None:
        """Show the toast, play entry animation, and start the auto-dismiss timer."""
        self.show()
        self.raise_()
        self._animate_in()
        self._start_timer()

    def dismiss(self) -> None:
        """Play exit animation and remove the widget."""
        if self._dismissing:
            return
        self._dismissing = True
        self._stop_timer()

        # Cancel any running entry animations
        if self._slide_in_anim is not None and self._slide_in_anim.state() == QPropertyAnimation.State.Running:
            self._slide_in_anim.stop()
        if self._fade_in_anim is not None and self._fade_in_anim.state() == QPropertyAnimation.State.Running:
            self._fade_in_anim.stop()

        start_pos = self.pos()
        end_pos = QPoint(start_pos.x(), start_pos.y() + self.SLIDE_OFFSET)
        slide = QPropertyAnimation(self, b"pos")
        slide.setDuration(self.FADE_DURATION)
        slide.setStartValue(start_pos)
        slide.setEndValue(end_pos)
        slide.setEasingCurve(Anim.EASE_IN)

        fade = QPropertyAnimation(self._opacity, b"opacity")
        fade.setDuration(self.FADE_DURATION)
        fade.setStartValue(self._opacity.opacity())
        fade.setEndValue(0.0)
        fade.setEasingCurve(Anim.EASE_IN)

        group = QParallelAnimationGroup(self)
        group.addAnimation(slide)
        group.addAnimation(fade)
        group.finished.connect(self._finish_dismiss)
        group.start()
        self._dismiss_group = group

    # ------------------------------------------------------------------ internal
    def _animate_in(self) -> None:
        end_pos = self.pos()
        start_pos = QPoint(end_pos.x(), end_pos.y() + self.SLIDE_OFFSET)
        self.move(start_pos)

        slide = QPropertyAnimation(self, b"pos")
        slide.setDuration(self.FADE_DURATION)
        slide.setStartValue(start_pos)
        slide.setEndValue(end_pos)
        slide.setEasingCurve(Anim.EASE_OUT)
        slide.start()
        self._slide_in_anim = slide

        fade = QPropertyAnimation(self._opacity, b"opacity")
        fade.setDuration(self.FADE_DURATION)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(Anim.EASE_OUT)
        fade.start()
        self._fade_in_anim = fade

    def _start_timer(self) -> None:
        if self._timeout <= 0:
            return
        self._stop_timer()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer_fired)
        self._timer.start(self._remaining_ms)

    def _stop_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    def _on_timer_fired(self) -> None:
        if not self._hovered:
            self.dismiss()
        # If hovered, _pause_for_hover already restarted the timer with the
        # remaining time, so we don't need to do anything here.

    def _pause_for_hover(self) -> None:
        if self._timer is None or not self._timer.isActive():
            return
        elapsed = self._timeout - self._timer.remainingTime()
        self._remaining_ms = max(500, self._timeout - elapsed)
        self._stop_timer()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer_fired)
        self._timer.start(self._remaining_ms + 1500)  # add 1.5s grace on hover

    def _finish_dismiss(self) -> None:
        self.dismissed.emit()
        self.deleteLater()

    # ------------------------------------------------------------------ events
    def enterEvent(self, event: QEnterEvent) -> None:
        self._hovered = True
        self._pause_for_hover()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.dismiss()
        super().mousePressEvent(event)


class ToastManager:
    """Lightweight manager that stacks toasts inside a parent widget."""

    def __init__(self, parent: QWidget):
        self._parent = parent
        self._toasts: List[Toast] = []
        self._spacing = 8
        self._margin = 12

    def show(
        self,
        message: str,
        kind: str = "info",
        timeout_ms: int = Toast.DEFAULT_TIMEOUT,
    ) -> Toast:
        toast = Toast(message, kind, timeout_ms, self._parent)
        toast.dismissed.connect(lambda t=toast: self._on_dismissed(t))
        toast.adjustSize()
        self._toasts.append(toast)
        self._reposition()
        toast.show_toast()
        return toast

    def _on_dismissed(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._reposition()

    def _reposition(self) -> None:
        if self._parent is None:
            return
        bottom = self._parent.height() - self._margin
        for toast in reversed(self._toasts):
            toast.adjustSize()
            h = toast.height()
            x = (self._parent.width() - toast.width()) // 2
            y = bottom - h
            toast.move(max(0, x), max(0, y))
            bottom = y - self._spacing
