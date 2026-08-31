from typing import Optional

from PySide6.QtCore import QPropertyAnimation, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

from src.app.theme.animations import Anim


class _Spinner(QWidget):
    """Lingkaran arc yang berputar — indikator loading/buffering standar."""

    SPIN_DURATION = 900  # ms per putaran
    ARC_SPAN = 270       # derajat busur yang digambar

    def __init__(self, size: int = 22, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0)
        self._anim.setEndValue(360)
        self._anim.setDuration(self.SPIN_DURATION)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._on_angle_changed)

    def start(self) -> None:
        self._anim.start()

    def stop(self) -> None:
        self._anim.stop()

    def _on_angle_changed(self, value) -> None:
        self._angle = float(value)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor("#3b82f6"), max(2, self.width() // 8), Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        margin = pen.widthF()
        rect = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)
        start = int(-self._angle * 16)  # negatif = searah jarum jam
        span = int(self.ARC_SPAN * 16)
        painter.drawArc(rect, start, span)


class BufferingIndicator(QWidget):
    """Overlay "Buffering…" yang muncul saat stream menunggu data.

    Ditampilkan saat player dalam state ``LOADING`` (load awal maupun buffer/
    stall di tengah playback): spinner berputar + fade in lalu berdenyut
    (pulse) halus, kemudian fade out saat playback berlanjut. Transparan
    terhadap mouse agar klik tetap sampai ke area video.
    """

    PULSE_MIN = 0.4
    PULSE_MAX = 1.0
    PULSE_DURATION = 700  # ms per setengah siklus

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("bufferingIndicator")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(10)

        self._spinner = _Spinner(size=22)
        layout.addWidget(self._spinner)

        self._text = QLabel("Buffering\u2026")
        self._text.setStyleSheet(
            "color: #fafafa; background: transparent; border: none;"
            " font-size: 10pt; font-weight: 600;"
        )
        layout.addWidget(self._text)

        self.setStyleSheet(
            """
            QWidget#bufferingIndicator {
                background-color: rgba(10, 10, 10, 190);
                border: 1px solid #1f1f1f;
                border-radius: 20px;
            }
            """
        )
        self.adjustSize()

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        self._fade_anim: Optional[QPropertyAnimation] = None
        self._pulse: Optional[QPropertyAnimation] = None

    # ------------------------------------------------------------------ public
    def set_message(self, text: str) -> None:
        """Ganti teks overlay (mis. 'Loading…' saat load awal, 'Buffering…' saat stall)."""
        if self._text.text() != text:
            self._text.setText(text)
            self._center()

    def show_indicator(self) -> None:
        """Tampilkan overlay: spinner berputar, fade in, lalu denyut (pulse)."""
        # Guard pakai isHidden() (flag eksplisit), bukan isVisible() — yang
        # terakhir bergantung status window system dan tidak andal di semua
        # platform (mis. platform offscreen).
        if not self.isHidden() and self._opacity.opacity() > 0.9:
            return
        if self._fade_anim is not None and self._fade_anim.state() == QPropertyAnimation.State.Running:
            self._fade_anim.stop()
        self._stop_pulse()
        self._opacity.setOpacity(0.0)
        self._spinner.start()
        self.setVisible(True)
        self._center()
        self.raise_()
        self._fade_anim = Anim.fade_in(
            self,
            duration=Anim.DURATION_FAST,
            on_finished=self._start_pulse,
        )
        self._fade_anim.start()

    def hide_indicator(self) -> None:
        """Sembunyikan overlay: hentikan spinner & denyut lalu fade out."""
        if self.isHidden():
            return
        self._spinner.stop()
        self._stop_pulse()
        if self._fade_anim is not None and self._fade_anim.state() == QPropertyAnimation.State.Running:
            self._fade_anim.stop()

        def _hide() -> None:
            self.setVisible(False)
            self._fade_anim = None

        self._fade_anim = Anim.fade_out(
            self,
            duration=Anim.DURATION_FAST,
            on_finished=_hide,
        )
        self._fade_anim.start()

    def _center(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        x = (parent.width() - self.width()) // 2
        y = (parent.height() - self.height()) // 2
        self.setGeometry(max(0, x), max(0, y), self.width(), self.height())

    # ------------------------------------------------------------------ anim
    def _start_pulse(self) -> None:
        self._stop_pulse()
        pulse = QPropertyAnimation(self._opacity, b"opacity")
        pulse.setDuration(self.PULSE_DURATION)
        pulse.setStartValue(self.PULSE_MIN)
        pulse.setEndValue(self.PULSE_MAX)
        pulse.setEasingCurve(Anim.EASE_IN_OUT)
        pulse.setLoopCount(-1)  # berdenyut terus selama buffering
        pulse.start()
        self._pulse = pulse

    def _stop_pulse(self) -> None:
        if self._pulse is not None:
            self._pulse.stop()
            self._pulse = None
