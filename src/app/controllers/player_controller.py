from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from src.player_core import MpvPlayer


class PlayerState:
    IDLE = "idle"
    LOADING = "loading"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class PlayerController(QObject):
    """Qt-friendly wrapper around :class:`MpvPlayer`.

    Translates mpv events and property observations into Qt signals so the
    UI can react on the GUI thread. Also drives a periodic poll for
    position, duration, cache state and buffered time.
    """

    state_changed = Signal(str)
    position_changed = Signal(float)
    duration_changed = Signal(float)
    volume_changed = Signal(int)
    cache_state_changed = Signal(object)
    buffered_time_changed = Signal(float)
    network_speed_changed = Signal(float)
    track_list_changed = Signal(list)
    error_occurred = Signal(str)
    initialized = Signal()
    terminated = Signal()

    POLL_INTERVAL_MS = 250

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._player: Optional[MpvPlayer] = None
        self._state: str = PlayerState.IDLE
        self._duration: float = 0.0
        self._last_cache_bytes: int = 0
        self._poll_timer: Optional[QTimer] = None
        self._init_pending: bool = False
        self._surface_wid: Optional[int] = None

    # ------------------------------------------------------------------ init
    @property
    def is_initialized(self) -> bool:
        return self._player is not None and self._player.mpv is not None

    def initialize(self) -> None:
        if self._init_pending or self.is_initialized:
            return
        self._init_pending = True
        try:
            self._player = MpvPlayer(wid=self._surface_wid)
        except Exception as exc:
            self._init_pending = False
            self._set_state(PlayerState.ERROR)
            self.error_occurred.emit(str(exc))
            return

        self._wire_observers()
        self._start_polling()
        self._init_pending = False
        self.initialized.emit()

    def _wire_observers(self) -> None:
        if not self.is_initialized:
            return
        mpv_obj = self._player.mpv
        mpv_obj.event_callback(self._on_mpv_event)
        mpv_obj.observe_property("pause", self._on_property_pause)
        mpv_obj.observe_property("core-idle", self._on_property_core_idle)
        mpv_obj.observe_property("paused-for-cache", self._on_property_paused_for_cache)
        mpv_obj.observe_property("eof-reached", self._on_property_eof_reached)
        mpv_obj.observe_property("duration", self._on_property_duration)
        mpv_obj.observe_property("volume", self._on_property_volume)
        mpv_obj.observe_property("track-list", self._on_property_track_list)

    # ------------------------------------------------------------------ polling
    def _start_polling(self) -> None:
        if self._poll_timer is not None:
            return
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self.POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start()

    def _stop_polling(self) -> None:
        if self._poll_timer is None:
            return
        self._poll_timer.stop()
        self._poll_timer.deleteLater()
        self._poll_timer = None

    @Slot()
    def _poll(self) -> None:
        if not self.is_initialized:
            return

        pos = self._player.get_time_pos()
        if pos is not None:
            self.position_changed.emit(float(pos))

        cache_state = self._player.get_demuxer_cache_state() or {}
        if cache_state:
            self.cache_state_changed.emit(cache_state)
            speed = float(cache_state.get("input-bitrate") or 0.0)
            self.network_speed_changed.emit(speed)

        buffered = self._player.get_buffered_time()
        if buffered is not None:
            self.buffered_time_changed.emit(float(buffered))

    # ------------------------------------------------------------------ play api
    def attach_surface(self, wid: int) -> None:
        """Bind the mpv render target to a native window id from a VideoSurface."""
        if wid is None:
            return
        self._surface_wid = int(wid)
        if not self.is_initialized:
            return
        self._player.set_wid(wid)

    def play(self, url: str, headers: Optional[dict] = None, user_agent: Optional[str] = None) -> None:
        if not self.is_initialized:
            self.error_occurred.emit("Player not initialized")
            return
        self._player.play(url, headers=headers, user_agent=user_agent)
        self._set_state(PlayerState.LOADING)

    def toggle_pause(self) -> None:
        if not self.is_initialized:
            return
        new_state = self._player.pause()
        self._set_state(PlayerState.PAUSED if new_state else PlayerState.PLAYING)

    def stop(self) -> None:
        if not self.is_initialized:
            return
        self._player.stop()
        self._set_state(PlayerState.STOPPED)

    def seek(self, value: float, mode: str = "relative") -> None:
        if not self.is_initialized:
            return
        self._player.seek(value, mode)

    def set_volume(self, value: int) -> None:
        if not self.is_initialized:
            return
        self._player.set_volume(max(0, min(130, int(value))))

    def terminate(self) -> None:
        self._stop_polling()
        if self._player is not None:
            try:
                self._player.terminate()
            except Exception:
                pass
            self._player = None
        self.terminated.emit()

    # ------------------------------------------------------------------ helpers
    def get_track_list(self) -> list:
        if not self.is_initialized:
            return []
        return self._player.get_video_tracks() or []

    def select_video_track(self, track_id) -> None:
        if not self.is_initialized:
            return
        self._player.set_video_track(track_id)

    def apply_cache_settings(self, max_bytes_mb=None, max_back_bytes_mb=None) -> bool:
        if not self.is_initialized:
            return False
        return self._player.apply_cache_settings(max_bytes_mb, max_back_bytes_mb)

    def clear_cache(self) -> bool:
        if not self.is_initialized:
            return False
        return self._player.clear_cache()

    # ------------------------------------------------------------------ mpv event/observer callbacks
    def _on_mpv_event(self, event) -> None:
        event_id = event.get("event_id") if isinstance(event, dict) else None
        if event_id is None:
            return
        try:
            import mpv as _mpv

            end_file = _mpv.MpvEventID.END_FILE
            file_loaded = _mpv.MpvEventID.FILE_LOADED
            log_message = _mpv.MpvEventID.LOG_MESSAGE
        except Exception:
            return

        if event_id == end_file:
            reason = (event.get("reason") or "eof").lower()
            if reason == "error":
                self._set_state(PlayerState.ERROR)
            else:
                self._set_state(PlayerState.STOPPED)
        elif event_id == file_loaded:
            if self._state == PlayerState.LOADING:
                self._set_state(PlayerState.PLAYING)
        elif event_id == log_message:
            text = event.get("text") or ""
            if "error" in text.lower() or "failed" in text.lower():
                self.error_occurred.emit(text)

    def _on_property_pause(self, _name, value) -> None:
        if value is None:
            return
        self._set_state(PlayerState.PAUSED if value else PlayerState.PLAYING)

    def _on_property_core_idle(self, _name, value) -> None:
        if value and self._state not in (PlayerState.STOPPED, PlayerState.ERROR):
            self._set_state(PlayerState.LOADING)
        elif not value and self._state == PlayerState.LOADING:
            self._set_state(PlayerState.PLAYING)

    def _on_property_paused_for_cache(self, _name, value) -> None:
        if value and self._state not in (PlayerState.PAUSED, PlayerState.STOPPED):
            self._set_state(PlayerState.LOADING)

    def _on_property_eof_reached(self, _name, value) -> None:
        if value and self._state != PlayerState.ERROR:
            self._set_state(PlayerState.STOPPED)

    def _on_property_duration(self, _name, value) -> None:
        if value is None:
            return
        d = float(value)
        if abs(d - self._duration) > 0.05:
            self._duration = d
            self.duration_changed.emit(d)

    def _on_property_volume(self, _name, value) -> None:
        if value is None:
            return
        self.volume_changed.emit(int(value))

    def _on_property_track_list(self, _name, value) -> None:
        self.track_list_changed.emit(list(value or []))

    # ------------------------------------------------------------------ state
    def _set_state(self, new_state: str) -> None:
        if new_state == self._state:
            return
        self._state = new_state
        self.state_changed.emit(new_state)

    @property
    def state(self) -> str:
        return self._state
