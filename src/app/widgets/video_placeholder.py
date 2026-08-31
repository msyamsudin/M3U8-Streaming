from typing import Optional

from PySide6.QtCore import QPointF, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.app.theme.animations import Anim


class VideoPlaceholder(QWidget):
    """Modern centered placeholder shown when no stream is loaded.

    The placeholder overlays the video surface and is automatically hidden
    once a video starts playing.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("videoPlaceholder")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setVisible(False)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        # Play icon + helper text
        container = QWidget()
        container.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignCenter)

        self._icon_label = QLabel("\u25B6")
        self._icon_label.setAlignment(Qt.AlignCenter)
        icon_font = QFont("Segoe UI Symbol", 64)
        icon_font.setBold(False)
        self._icon_label.setFont(icon_font)
        self._icon_label.setStyleSheet(
            "color: #3b82f6; background: transparent; border: none;"
        )
        # Subtle glow
        glow = QGraphicsDropShadowEffect(self._icon_label)
        glow.setBlurRadius(40)
        glow.setColor(QColor(59, 130, 246, 110))
        glow.setOffset(0, 0)
        self._icon_label.setGraphicsEffect(glow)
        layout.addWidget(self._icon_label, 0, Qt.AlignHCenter)

        self._title_label = QLabel("Ready to Play")
        title_font = QFont("Segoe UI", 18)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet(
            "color: #fafafa; background: transparent; border: none;"
        )
        layout.addWidget(self._title_label, 0, Qt.AlignHCenter)

        self._hint_label = QLabel("Enter a stream URL and click Load Stream")
        hint_font = QFont("Segoe UI", 10)
        self._hint_label.setFont(hint_font)
        self._hint_label.setAlignment(Qt.AlignCenter)
        self._hint_label.setStyleSheet(
            "color: #71717a; background: transparent; border: none;"
        )
        layout.addWidget(self._hint_label, 0, Qt.AlignHCenter)

        outer.addWidget(container, 0, Qt.AlignCenter)
        outer.addStretch(2)

        # Soft fade in
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        self._opacity_effect = effect
        self._animation: Optional[QPropertyAnimation] = None

    def show_animated(self) -> None:
        if self.isVisible() and self._opacity_effect.opacity() > 0.9:
            return
        self._stop_animation()
        self._opacity_effect.setOpacity(0.0)
        self.setVisible(True)
        self.raise_()
        self._animation = Anim.fade_in(
            self,
            duration=Anim.DURATION_NORMAL,
            on_finished=self._clear_animation,
        )
        self._animation.start()

    def hide_animated(self) -> None:
        if not self.isVisible():
            return
        self._stop_animation()

        def _hide() -> None:
            self.setVisible(False)
            self._clear_animation()

        self._animation = Anim.fade_out(
            self,
            duration=Anim.DURATION_FAST,
            on_finished=_hide,
        )
        self._animation.start()

    def hide_now(self) -> None:
        self._stop_animation()
        self._opacity_effect.setOpacity(0.0)
        self.setVisible(False)

    def set_message(self, title: str, hint: str) -> None:
        self._title_label.setText(title)
        self._hint_label.setText(hint)

    def _stop_animation(self) -> None:
        if self._animation is not None:
            self._animation.stop()
            self._animation = None

    def _clear_animation(self) -> None:
        self._animation = None
