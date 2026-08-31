from typing import Optional

from PySide6.QtCore import QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QStackedWidget,
    QToolButton,
    QWidget,
)

from src.app.theme.animations import Anim
from src.app.widgets.seek_slider import SeekSlider


class _IconButton(QToolButton):
    def __init__(self, text: str, tooltip: str, object_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setText(text)
        self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(38, 36)
        font = self.font()
        font.setPointSize(13)
        self.setFont(font)


class ControlBar(QWidget):
    """Bottom playback control bar.

    Exposes high-level signals (``play_clicked``, ``stop_clicked``, etc.) that
    the parent window maps to player actions, so the bar stays decoupled from
    the :class:`PlayerController`.
    """

    play_clicked = Signal()
    stop_clicked = Signal()
    seek_requested = Signal(float)
    volume_requested = Signal(int)
    quality_selected = Signal(object)
    fullscreen_toggle_requested = Signal()
    record_toggle_requested = Signal()
    debug_toggle_requested = Signal()
    previous_chapter_clicked = Signal()
    next_chapter_clicked = Signal()

    PLAY_GLYPH = "\u25B6"
    PAUSE_GLYPH = "\u23F8"
    STOP_GLYPH = "\u25A0"
    FULLSCREEN_GLYPH = "\u26F6"
    EXIT_FULLSCREEN_GLYPH = "\u2715"
    RECORD_GLYPH = "\u25CF"
    VOLUME_GLYPH = "\u266B"
    VOLUME_MID_GLYPH = "\u266C"
    MUTE_GLYPH = "\u2715"
    DEBUG_GLYPH = "\u25D0"
    PREV_GLYPH = "\u23EE"
    NEXT_GLYPH = "\u23ED"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("controlBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(56)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._is_playing = False
        self._is_fullscreen = False
        self._is_recording = False
        self._volume_visible = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        self._position_label = QLabel("00:00")
        self._position_label.setObjectName("timeLabel")
        self._position_label.setMinimumWidth(56)
        self._position_label.setAlignment(Qt.AlignCenter)
        font = QFont("Consolas", 9)
        self._position_label.setFont(font)
        layout.addWidget(self._position_label)

        self._seek_slider = SeekSlider(Qt.Horizontal)
        self._seek_slider.setObjectName("seekSlider")
        self._seek_slider.user_seek.connect(self.seek_requested)
        layout.addWidget(self._seek_slider, 1)

        self._duration_label = QLabel("00:00")
        self._duration_label.setObjectName("timeLabel")
        self._duration_label.setMinimumWidth(56)
        self._duration_label.setAlignment(Qt.AlignCenter)
        self._duration_label.setFont(font)
        layout.addWidget(self._duration_label)

        layout.addSpacing(8)

        self._prev_btn = _IconButton(self.PREV_GLYPH, "Seek back 10s", "controlButton#prevButton")
        self._prev_btn.clicked.connect(self.previous_chapter_clicked)
        layout.addWidget(self._prev_btn)

        self._play_btn = _IconButton(self.PLAY_GLYPH, "Play/Pause (Space)", "controlButton#playButton")
        self._play_btn.clicked.connect(self._on_play_clicked)
        layout.addWidget(self._play_btn)

        self._next_btn = _IconButton(self.NEXT_GLYPH, "Seek forward 10s", "controlButton#nextButton")
        self._next_btn.clicked.connect(self.next_chapter_clicked)
        layout.addWidget(self._next_btn)

        layout.addSpacing(8)

        self._volume_container = QWidget()
        self._volume_container.setObjectName("volumeContainer")
        self._volume_container.setFixedWidth(38)
        vol_layout = QHBoxLayout(self._volume_container)
        vol_layout.setContentsMargins(0, 0, 0, 0)
        vol_layout.setSpacing(0)
        self._volume_btn = _IconButton(self.VOLUME_MID_GLYPH, "Volume", "controlButton#volumeButton")
        self._volume_btn.clicked.connect(self._on_volume_btn_clicked)
        vol_layout.addWidget(self._volume_btn)
        self._volume_slider = QSlider(Qt.Horizontal)
        self._volume_slider.setObjectName("volumeSlider")
        self._volume_slider.setRange(0, 130)
        self._volume_slider.setValue(100)
        self._volume_slider.setFixedWidth(0)
        self._volume_slider.setVisible(False)
        self._volume_slider.valueChanged.connect(self._on_volume_slider_changed)
        vol_layout.addWidget(self._volume_slider)
        layout.addWidget(self._volume_container)

        self._quality_combo = QComboBox()
        self._quality_combo.setObjectName("qualityCombo")
        self._quality_combo.setMinimumWidth(100)
        self._quality_combo.setToolTip("Video quality / track")
        self._quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        self._quality_combo.addItem("Auto", None)
        layout.addWidget(self._quality_combo)

        self._fullscreen_btn = _IconButton(
            self.FULLSCREEN_GLYPH, "Fullscreen (F)", "controlButton#fullscreenButton"
        )
        self._fullscreen_btn.clicked.connect(self._on_fullscreen_clicked)
        layout.addWidget(self._fullscreen_btn)

        self._debug_btn = _IconButton(self.DEBUG_GLYPH, "Debug (F12)", "controlButton#debugButton")
        self._debug_btn.clicked.connect(self._on_debug_clicked)
        layout.addWidget(self._debug_btn)

    # ------------------------------------------------------------------ public
    def set_playing(self, is_playing: bool) -> None:
        self._is_playing = is_playing
        self._play_btn.setText(self.PAUSE_GLYPH if is_playing else self.PLAY_GLYPH)
        self._play_btn.setToolTip("Pause" if is_playing else "Play")

    def set_position(self, current: float, duration: float) -> None:
        self._position_label.setText(self._format_time(current))
        self._duration_label.setText(self._format_time(duration))
        if duration > 0 and not self._seek_slider.is_seeking():
            fraction = max(0.0, min(1.0, current / duration))
            self._seek_slider.setValue(int(fraction * self._seek_slider.maximum()))

    def set_buffered(self, buffered_seconds: float, duration: float) -> None:
        if duration <= 0:
            self._seek_slider.set_buffered(0.0)
            return
        self._seek_slider.set_buffered(max(0.0, min(1.0, buffered_seconds / duration)))

    def set_volume(self, volume: int) -> None:
        if self._volume_slider.value() != volume:
            self._volume_slider.blockSignals(True)
            self._volume_slider.setValue(volume)
            self._volume_slider.blockSignals(False)
        self._update_volume_icon(volume)

    def set_fullscreen(self, is_fullscreen: bool) -> None:
        self._is_fullscreen = is_fullscreen
        self._fullscreen_btn.setText(
            self.EXIT_FULLSCREEN_GLYPH if is_fullscreen else self.FULLSCREEN_GLYPH
        )
        self._fullscreen_btn.setToolTip(
            "Exit fullscreen" if is_fullscreen else "Fullscreen"
        )

    def set_debug(self, is_active: bool) -> None:
        self._debug_btn.setProperty("active", is_active)
        self._debug_btn.style().unpolish(self._debug_btn)
        self._debug_btn.style().polish(self._debug_btn)

    def set_recording(self, is_recording: bool) -> None:
        # Recording is not exposed in the modern control bar layout.
        pass

    def set_track_list(self, tracks: list) -> None:
        previous_data = self._quality_combo.currentData()
        self._quality_combo.blockSignals(True)
        self._quality_combo.clear()
        self._quality_combo.addItem("Auto", None)
        for track in tracks or []:
            if not isinstance(track, dict):
                continue
            if track.get("type") != "video":
                continue
            track_id = track.get("id")
            label = self._format_track_label(track)
            self._quality_combo.addItem(label, track_id)
        if previous_data is not None:
            idx = self._quality_combo.findData(previous_data)
            if idx >= 0:
                self._quality_combo.setCurrentIndex(idx)
        self._quality_combo.blockSignals(False)

    def set_enabled_controls(self, enabled: bool) -> None:
        self._play_btn.setEnabled(enabled)
        self._seek_slider.setEnabled(enabled)
        self._quality_combo.setEnabled(enabled)
        self._volume_btn.setEnabled(enabled)
        self._fullscreen_btn.setEnabled(enabled)

    # ------------------------------------------------------------------ slots
    def _on_play_clicked(self) -> None:
        self.play_clicked.emit()

    def _on_fullscreen_clicked(self) -> None:
        self.fullscreen_toggle_requested.emit()

    def _on_debug_clicked(self) -> None:
        self.debug_toggle_requested.emit()

    def _on_volume_btn_clicked(self) -> None:
        self._volume_visible = not self._volume_visible
        target_w = 90 if self._volume_visible else 0
        if self._volume_visible:
            self._volume_slider.setVisible(True)
        Anim.expand_horizontal(self._volume_container, target_w, duration=Anim.DURATION_NORMAL)
        if not self._volume_visible:
            def _hide():
                self._volume_slider.setVisible(False)
            QPropertyAnimation(
                self._volume_container, b"maximumWidth"
            )  # no-op to keep static analysis happy
            self._volume_slider.setVisible(False)

    def _on_volume_slider_changed(self, value: int) -> None:
        self._update_volume_icon(value)
        self.volume_requested.emit(value)

    def _on_quality_changed(self, index: int) -> None:
        data = self._quality_combo.itemData(index)
        self.quality_selected.emit(data)

    # ------------------------------------------------------------------ helpers
    def _update_volume_icon(self, value: int) -> None:
        if value <= 0:
            self._volume_btn.setText(self.MUTE_GLYPH)
        else:
            self._volume_btn.setText(self.VOLUME_GLYPH)

    @staticmethod
    def _format_track_label(track: dict) -> str:
        height = track.get("height")
        width = track.get("width")
        codec = track.get("codec") or ""
        title = track.get("title") or ""
        if height:
            res = f"{int(width or 0)}x{int(height)}" if width else f"{int(height)}p"
        else:
            res = title or f"Track {track.get('id', '?')}"
        if codec:
            return f"{res} ({codec})"
        return res

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds is None or seconds < 0:
            seconds = 0
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
