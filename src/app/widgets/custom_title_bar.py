from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QEnterEvent, QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class TitleBarButton(QPushButton):
    """A QPushButton tuned for the custom title bar.

    Provides a flat look with hover-only background and a cursor hint.
    Subclassing keeps per-button styling simple via ``objectName``.
    """

    def __init__(self, text: str, object_name: str, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setObjectName(object_name)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedHeight(32)


class CustomTitleBar(QWidget):
    """A frameless title bar with drag support and min/max/close buttons.

    Emits high-level signals that the parent window maps to ``showMinimized``,
    ``showMaximized``/``showNormal`` and ``close``. The bar itself does not
    touch the parent window directly so it stays decoupled.
    """

    minimize_requested = Signal()
    maximize_toggle_requested = Signal()
    close_requested = Signal()
    settings_toggle_requested = Signal()
    history_toggle_requested = Signal()

    DRAG_THRESHOLD = 4

    def __init__(self, title: str = "M3U8 Player", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("customTitleBar")
        self.setFixedHeight(32)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._parent_window: Optional[QWidget] = parent
        self._drag_start_global: Optional[QPoint] = None
        self._drag_active: bool = False
        self._is_drag: bool = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(0)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("titleBarLabel")
        layout.addWidget(self._title_label)

        layout.addStretch(1)

        self._history_btn = TitleBarButton("\u23F3", "titleBarButton#historyButton", self)
        self._history_btn.setToolTip("History")
        self._history_btn.setFixedWidth(40)
        self._history_btn.clicked.connect(self.history_toggle_requested)
        layout.addWidget(self._history_btn)

        self._settings_btn = TitleBarButton("\u2699", "titleBarButton#settingsButton", self)
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.setFixedWidth(40)
        self._settings_btn.clicked.connect(self.settings_toggle_requested)
        layout.addWidget(self._settings_btn)

        self._min_btn = TitleBarButton("\u2013", "titleBarButton#minButton", self)
        self._min_btn.setToolTip("Minimize")
        self._min_btn.setFixedWidth(46)
        self._min_btn.clicked.connect(self.minimize_requested)
        layout.addWidget(self._min_btn)

        self._max_btn = TitleBarButton("\u25A1", "titleBarButton#maxButton", self)
        self._max_btn.setToolTip("Maximize")
        self._max_btn.setFixedWidth(46)
        self._max_btn.clicked.connect(self.maximize_toggle_requested)
        layout.addWidget(self._max_btn)

        self._close_btn = TitleBarButton("\u2715", "titleBarButton#closeButton", self)
        self._close_btn.setToolTip("Close")
        self._close_btn.setFixedWidth(46)
        self._close_btn.clicked.connect(self.close_requested)
        layout.addWidget(self._close_btn)

    # ------------------------------------------------------------------ public
    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def set_maximized(self, maximized: bool) -> None:
        self._max_btn.setText("\u2750" if maximized else "\u25A1")
        self._max_btn.setToolTip("Restore" if maximized else "Maximize")

    # ------------------------------------------------------------------ events
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._is_on_draggable_area(event.pos()):
            self._drag_start_global = event.globalPos()
            self._is_drag = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start_global is not None and (event.buttons() & Qt.LeftButton):
            delta = event.globalPos() - self._drag_start_global
            if not self._is_drag and delta.manhattanLength() < self.DRAG_THRESHOLD:
                return
            self._is_drag = True
            window = self._resolve_window()
            if window is not None and not window.isMaximized():
                window.move(window.pos() + delta)
                self._drag_start_global = event.globalPos()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._drag_start_global is not None:
            self._drag_start_global = None
            self._is_drag = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._is_on_draggable_area(event.pos()):
            self.maximize_toggle_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    # ------------------------------------------------------------------ helpers
    def _is_on_draggable_area(self, pos: QPoint) -> bool:
        widget_at = self.childAt(pos)
        if widget_at is None:
            return True
        return not isinstance(widget_at, TitleBarButton)

    def _resolve_window(self) -> Optional[QWidget]:
        if self._parent_window is not None:
            return self._parent_window.window()
        return self.window()
