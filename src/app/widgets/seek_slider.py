from typing import Optional

from PySide6.QtCore import Property, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPalette
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider, QWidget


class SeekSlider(QSlider):
    """A horizontal QSlider that paints a buffered-region highlight.

    ``buffered`` (0.0 - 1.0) draws a softer accent behind the played segment
    so users can see how much of the stream has been pre-fetched.
    """

    user_seek = Signal(float)

    def __init__(self, orientation=Qt.Horizontal, parent: Optional[QWidget] = None):
        super().__init__(orientation, parent)
        self.setObjectName("seekSlider")
        self.setRange(0, 1000)
        self.setSingleStep(1)
        self.setPageStep(10)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._buffered: float = 0.0
        self._seeking: bool = False

    # ------------------------------------------------------------------ props
    def set_buffered(self, value: float) -> None:
        clamped = max(0.0, min(1.0, value))
        if abs(clamped - self._buffered) < 0.001:
            return
        self._buffered = clamped
        self.update()

    def get_buffered(self) -> float:
        return self._buffered

    buffered_fraction = Property(float, get_buffered, set_buffered)

    def is_seeking(self) -> bool:
        return self._seeking

    # ------------------------------------------------------------------ events
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._seeking = True
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            handle_w = self.style().pixelMetric(
                QStyle.PM_SliderLength, opt, self
            )
            available = max(1, self.width() - handle_w)
            fraction = max(0.0, min(1.0, (event.x() - handle_w / 2) / available))
            new_value = int(fraction * (self.maximum() - self.minimum()) + self.minimum())
            self.setValue(new_value)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._seeking and (event.buttons() & Qt.LeftButton):
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            handle_w = self.style().pixelMetric(
                QStyle.PM_SliderLength, opt, self
            )
            available = max(1, self.width() - handle_w)
            fraction = max(0.0, min(1.0, (event.x() - handle_w / 2) / available))
            new_value = int(fraction * (self.maximum() - self.minimum()) + self.minimum())
            self.setValue(new_value)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._seeking:
            self._seeking = False
            fraction = (self.value() - self.minimum()) / max(
                1, (self.maximum() - self.minimum())
            )
            self.user_seek.emit(fraction)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        opt.subControls = QStyle.SC_None
        opt.activeSubControls = QStyle.SC_None

        style = self.style()
        handle_w = style.pixelMetric(QStyle.PM_SliderLength, opt, self)
        groove_h = style.pixelMetric(QStyle.PM_SliderThickness, opt, self)
        groove_h = max(4, groove_h)
        cy = self.height() // 2
        gx1 = handle_w // 2
        gx2 = self.width() - handle_w // 2
        gw = max(1, gx2 - gx1)

        # Background groove
        bg_rect = self._groove_rect(gx1, gx2, cy, groove_h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#3d3d3d"))
        painter.drawRoundedRect(bg_rect, groove_h / 2, groove_h / 2)

        # Buffered region
        if self._buffered > 0:
            buffered_w = int(gw * self._buffered)
            bx2 = gx1 + buffered_w
            buffered_rect = self._groove_rect(gx1, bx2, cy, groove_h)
            gradient = QLinearGradient(buffered_rect.topLeft(), buffered_rect.topRight())
            gradient.setColorAt(0.0, QColor("#005FA3"))
            gradient.setColorAt(1.0, QColor("#007ACC"))
            painter.setBrush(gradient)
            painter.drawRoundedRect(buffered_rect, groove_h / 2, groove_h / 2)

        # Played region (sub-page)
        if self.maximum() > self.minimum():
            fraction = (self.value() - self.minimum()) / (self.maximum() - self.minimum())
            played_w = int(gw * fraction)
            px2 = gx1 + played_w
            if played_w > 0:
                played_rect = self._groove_rect(gx1, px2, cy, groove_h)
                painter.setBrush(QColor("#0098FF"))
                painter.drawRoundedRect(played_rect, groove_h / 2, groove_h / 2)

        # Handle
        handle_x = gx1 + int(gw * (self.value() - self.minimum()) / max(1, self.maximum() - self.minimum()))
        handle_x = max(handle_w // 2, min(self.width() - handle_w // 2, handle_x))
        handle_color = QColor("#0098FF") if self.underMouse() else QColor("#ffffff")
        painter.setBrush(handle_color)
        painter.setPen(Qt.NoPen)
        handle_d = max(10, handle_w - 2)
        painter.drawEllipse(
            handle_x - handle_d // 2,
            cy - handle_d // 2,
            handle_d,
            handle_d,
        )

    @staticmethod
    def _groove_rect(x1: int, x2: int, cy: int, h: int):
        from PySide6.QtCore import QRect

        return QRect(x1, cy - h // 2, max(1, x2 - x1), h)
