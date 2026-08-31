from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class _StatRow(QWidget):
    """A label/value row that shares a consistent style."""

    def __init__(self, label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        self._name = QLabel(label)
        self._name.setStyleSheet("color: #888888;")
        self._value = QLabel("-")
        self._value.setStyleSheet("color: #ffffff;")
        self._value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        font = QFont("Consolas", 9)
        self._name.setFont(font)
        self._value.setFont(font)
        layout.addWidget(self._name, 0, 0)
        layout.addWidget(self._value, 0, 1)
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class DebugOverlay(QWidget):
    """A semi-transparent stats panel that sits on top of the video area.

    The widget is ``WA_TransparentForMouseEvents`` so clicks reach the
    video surface beneath. Position the overlay in the desired corner via
    :meth:`attach_to` (parent video container) and call
    :meth:`update_stats` whenever new metrics arrive.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("debugOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(Qt.SubWindow)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMinimumWidth(220)
        self.setStyleSheet(
            """
            QWidget#debugOverlay {
                background-color: rgba(10, 10, 10, 200);
                border: 1px solid #1a1a1a;
                border-radius: 6px;
            }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(2)

        title = QLabel("Debug Stats")
        title.setStyleSheet(
            "color: #007ACC; font-weight: bold; font-size: 9pt; padding-bottom: 4px;"
        )
        outer.addWidget(title)

        self._row_state = _StatRow("State")
        self._row_pos = _StatRow("Position")
        self._row_dur = _StatRow("Duration")
        self._row_speed = _StatRow("Speed")
        self._row_buffered = _StatRow("Buffered")
        self._row_cache = _StatRow("Cache")
        self._row_refresh = _StatRow("Refresh In")
        self._row_url = _StatRow("Active URL")
        self._row_resolution = _StatRow("Resolution")
        self._row_codec = _StatRow("Codec")
        self._row_volume = _StatRow("Volume")
        self._row_tracks = _StatRow("Tracks")
        for row in (
            self._row_state,
            self._row_pos,
            self._row_dur,
            self._row_speed,
            self._row_buffered,
            self._row_cache,
            self._row_refresh,
            self._row_url,
            self._row_resolution,
            self._row_codec,
            self._row_volume,
            self._row_tracks,
        ):
            outer.addWidget(row)

    # ------------------------------------------------------------------ public
    def attach_to(self, parent: QWidget, margin: int = 12) -> None:
        """Re-parent to ``parent`` (typically the video container) and place
        in the top-right corner. Call after the parent is laid out."""
        if self.parentWidget() is not parent:
            self.setParent(parent)
        self._margin = margin
        self._reposition()
        self.raise_()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        margin = getattr(self, "_margin", 12)
        self.adjustSize()
        pw = parent.width()
        ph = parent.height()
        w = self.width()
        h = self.height()
        x = pw - w - margin
        y = margin
        self.setGeometry(max(0, x), max(0, y), w, h)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self.raise_()

    # ------------------------------------------------------------------ updates
    def update_stats(self, stats: dict) -> None:
        for key, row in (
            ("state", self._row_state),
            ("position", self._row_pos),
            ("duration", self._row_dur),
            ("speed", self._row_speed),
            ("buffered", self._row_buffered),
            ("cache", self._row_cache),
            ("refresh", self._row_refresh),
            ("url", self._row_url),
            ("resolution", self._row_resolution),
            ("codec", self._row_codec),
            ("volume", self._row_volume),
            ("tracks", self._row_tracks),
        ):
            value = stats.get(key)
            if value is not None:
                row.set_value(str(value))
