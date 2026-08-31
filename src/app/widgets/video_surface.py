from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPaintEvent, QResizeEvent
from PySide6.QtWidgets import QWidget


class VideoSurface(QWidget):
    """A QWidget that hosts a native window handle for libmpv embedding.

    On Windows, ``int(self.winId())`` returns the HWND. On X11 it returns
    the X11 window ID, and on macOS it returns the NSView pointer. mpv
    accepts the same value for its ``wid`` property.

    The widget itself stays transparent and never paints anything. Rendering
    is performed by the mpv process into the native window.
    """

    surface_ready = Signal()
    clicked = Signal()
    double_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("videoSurface")
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("background-color: #000000;")
        self._surface_wid: Optional[int] = None

    @property
    def surface_wid(self) -> Optional[int]:
        """Return the native window id once the widget has been shown."""
        return self._surface_wid

    def showEvent(self, event: QShowEvent) -> None:  # noqa: F821 - forward ref
        super().showEvent(event)
        if self._surface_wid is None:
            try:
                self._surface_wid = int(self.winId())
                self.surface_ready.emit()
            except Exception:
                self._surface_wid = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
