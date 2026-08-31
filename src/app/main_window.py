from pathlib import Path
import time
from typing import Optional

from PySide6.QtCore import QEvent, QPropertyAnimation, QTimer, Qt
from PySide6.QtGui import QCursor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.app.controllers.player_controller import PlayerController, PlayerState
from src.app.theme.animations import Anim
from src.app.widgets.control_bar import ControlBar
from src.app.widgets.custom_title_bar import CustomTitleBar
from src.app.widgets.debug_overlay import DebugOverlay
from src.app.widgets.history_panel import HistoryPanel
from src.app.widgets.toast import ToastManager
from src.app.widgets.video_placeholder import VideoPlaceholder
from src.app.widgets.video_surface import VideoSurface
from src.utils import (
    format_time,
    get_history_item,
    load_history,
    save_history,
    load_settings,
    save_settings,
)
from src.config import USER_AGENTS


DEFAULT_REFERER = "https://www.patreon.com"
CACHE_DEFAULTS = {"forward": 100, "back": 100, "pause_refresh": 60}

# Legacy lowercase tokens written by older versions of settings.json / history.json.
# Map them to the full User-Agent strings so persisted values keep working.
UA_ALIASES = {
    "chrome": USER_AGENTS["Chrome"],
    "firefox": USER_AGENTS["Firefox"],
    "safari": USER_AGENTS["Safari"],
    "edge": USER_AGENTS["Edge"],
}
KNOWN_UA_VALUES = set(USER_AGENTS.values())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("M3U8 Player")
        self.setObjectName("mainWindow")
        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinMaxButtonsHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # State
        self._player = PlayerController(self)
        self._video_surface: VideoSurface | None = None
        self._video_container: QWidget | None = None
        self._video_placeholder: Optional[VideoPlaceholder] = None
        self._debug_overlay: DebugOverlay | None = None
        self._info_bar: QWidget | None = None
        self._control_bar: ControlBar | None = None
        self._debug_visible: bool = False
        self._toast_manager: ToastManager | None = None
        self._maximized_state: bool = False
        self._normal_geometry = None
        self._body_left_layout: Optional[QVBoxLayout] = None
        self._control_bar_in_overlay: bool = False
        self._pre_fullscreen_config_visible: bool = True
        self._pre_fullscreen_history_visible: bool = False
        self._history_panel_visible: bool = False
        self._panel_anim = None
        self._current_side_panel: Optional[QWidget] = None
        self._pending_user_agent: str = ""
        self._pending_headers: dict = {}
        self._pending_referer: str = ""
        self._pending_cache: dict = dict(CACHE_DEFAULTS)
        self._current_url: str = ""
        self._current_headers: dict = {}
        self._current_user_agent: str = ""
        self._last_cache_state: dict = {}
        self._pause_started_at: Optional[float] = None
        self._last_progress_save_second: int = -1
        self._resume_prompted_for_url: str = ""
        self._auto_hide_timer: Optional[QTimer] = None
        self._auto_hide_armed: bool = False
        self._cursor_hidden: bool = False
        self._title_anim: Optional[QPropertyAnimation] = None
        self._control_anim: Optional[QPropertyAnimation] = None
        self._config_bar_visible: bool = True
        self._config_anim: Optional[QPropertyAnimation] = None

        # Build UI
        self._setup_window_geometry()
        self._setup_default_font()
        self._build_title_bar()
        self._build_history_panel()
        self._load_persisted_settings()
        self._setup_central_widget()
        self._setup_status_bar()
        self._setup_shortcuts()
        self._setup_toast_manager()
        self._wire_title_bar()
        self._wire_control_bar()
        self._wire_history_panel()
        self._wire_config_form()
        self._wire_player_signals()
        self._connect_surface_signals()
        # Player initialization is deferred to showEvent (see below) so the
        # heavy libmpv load does not block the first paint.

    # ---------------------------------------------------------------- setup
    def _setup_window_geometry(self) -> None:
        width, height = 1100, 720
        screen = self.screen()
        if screen is None:
            self.resize(width, height)
            return
        screen_rect = screen.availableGeometry()
        x = screen_rect.x() + (screen_rect.width() - width) // 2
        y = screen_rect.y() + (screen_rect.height() - height) // 2
        self.setGeometry(x, y, width, height)
        self.setMouseTracking(True)
        self.installEventFilter(self)

    def _setup_default_font(self) -> None:
        font = QFont("Segoe UI", 10)
        self.setFont(font)

    def _build_title_bar(self) -> None:
        self._title_bar = CustomTitleBar("M3U8 Player", self)
        # Replace the built-in settings button with a collapse toggle for the
        # new top config bar. We keep history as a slide-out.
        self._title_bar._settings_btn.setText("\u2303")
        self._title_bar._settings_btn.setObjectName("titleBarButton#collapseConfigButton")
        self._title_bar._settings_btn.setToolTip("Toggle config bar")

    def _build_history_panel(self) -> None:
        self._history_panel = HistoryPanel(self)
        self._history_panel.setObjectName("sidePanel")
        self._history_panel.setVisible(False)
        self._history_panel.setMaximumWidth(0)

    def _load_persisted_settings(self) -> None:
        data = load_settings() or {}
        ua = data.get("user_agent", "")
        self._pending_user_agent = UA_ALIASES.get(ua, ua)  # migrasi token lama -> string penuh
        self._pending_referer = data.get("referer", DEFAULT_REFERER)
        self._pending_headers = dict(data.get("headers", {}))
        # Make sure the default referer is reflected in the headers dict so
        # the very first play() call already includes a Referer header.
        if self._pending_referer:
            self._pending_headers.pop("referer", None)
            self._pending_headers["Referer"] = self._pending_referer
        cache = data.get("cache", {}) or {}
        self._pending_cache = {
            "forward": int(cache.get("forward", CACHE_DEFAULTS["forward"])),
            "back": int(cache.get("back", CACHE_DEFAULTS["back"])),
            "pause_refresh": int(cache.get("pause_refresh", CACHE_DEFAULTS["pause_refresh"])),
        }

    def _persist_settings(self) -> None:
        data = {
            "user_agent": self._pending_user_agent,
            "referer": self._pending_referer,
            "headers": self._pending_headers,
            "cache": {
                "forward": self._cache_forward.value(),
                "back": self._cache_back.value(),
                "pause_refresh": self._pause_refresh.value(),
            },
        }
        try:
            save_settings(data)
        except Exception:
            pass

    # ---------------------------------------------------------------- shortcuts
    def _setup_shortcuts(self) -> None:
        from PySide6.QtGui import QShortcut, QKeySequence

        self._shortcuts: list = []

        def _make_shortcut(key: str, slot):
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(lambda: self._safe_shortcut(slot))
            self._shortcuts.append(sc)
            return sc

        self._sc_play = _make_shortcut("Space", self._on_shortcut_play_pause)
        self._sc_stop = _make_shortcut("S", self._player.stop)
        self._sc_seek_back = _make_shortcut("Left", lambda: self._on_shortcut_seek(-10.0))
        self._sc_seek_fwd = _make_shortcut("Right", lambda: self._on_shortcut_seek(10.0))
        self._sc_seek_back_alt = _make_shortcut("Shift+Left", lambda: self._on_shortcut_seek(-30.0))
        self._sc_seek_fwd_alt = _make_shortcut("Shift+Right", lambda: self._on_shortcut_seek(30.0))
        self._sc_vol_down = _make_shortcut("Down", lambda: self._on_shortcut_volume(-5))
        self._sc_vol_up = _make_shortcut("Up", lambda: self._on_shortcut_volume(5))
        self._sc_fullscreen = _make_shortcut("F", self._on_toggle_fullscreen)
        self._sc_exit_fullscreen = _make_shortcut("Esc", self._exit_fullscreen)
        self._sc_mute = _make_shortcut("M", self._on_shortcut_mute)
        self._sc_history = _make_shortcut("H", self._on_toggle_history_panel)
        self._sc_open_url = _make_shortcut("Ctrl+L", self._focus_url_input)
        self._sc_open_url_alias = _make_shortcut("Ctrl+O", self._focus_url_input)
        self._sc_debug = _make_shortcut("F12", self._toggle_debug_overlay)
        self._sc_debug_alias = _make_shortcut("Ctrl+D", self._toggle_debug_overlay)
        self._sc_shortcuts_help = _make_shortcut("F1", self._show_shortcuts_dialog)
        self._sc_toggle_config = _make_shortcut("Ctrl+,", self._toggle_config_bar)

    def _is_text_input_focused(self) -> bool:
        from PySide6.QtWidgets import (
            QAbstractSpinBox, QComboBox, QLineEdit, QPlainTextEdit, QTextEdit,
        )
        from PySide6.QtWidgets import QApplication as QApp

        fw = QApp.focusWidget()
        if fw is None:
            return False
        if isinstance(fw, (QLineEdit, QPlainTextEdit, QTextEdit, QAbstractSpinBox)):
            return True
        if isinstance(fw, QComboBox):
            view = fw.view()
            if view is not None and view.isVisible():
                return True
        return False

    def _safe_shortcut(self, slot) -> None:
        if self._is_text_input_focused():
            return
        slot()

    def _on_shortcut_play_pause(self) -> None:
        self._on_play_pause()

    def _on_shortcut_seek(self, delta: float) -> None:
        self._player.seek(delta, mode="relative")

    def _on_shortcut_volume(self, delta: int) -> None:
        if not self._player.is_initialized:
            return
        current = self._player._player.mpv.volume or 0
        self._player.set_volume(int(max(0, min(130, current + delta))))

    def _on_shortcut_mute(self) -> None:
        if not self._player.is_initialized:
            return
        current = self._player._player.mpv.volume or 0
        if current > 0:
            self._saved_volume = int(current)
            self._player.set_volume(0)
            self._show_toast("Muted", "info")
        else:
            restore = getattr(self, "_saved_volume", 100) or 100
            self._player.set_volume(restore)
            self._show_toast(f"Volume: {restore}", "info")

    def _focus_url_input(self) -> None:
        if self.isFullScreen():
            return
        if self._config_bar is not None and not self._config_bar_visible:
            self._toggle_config_bar()
        if self._url_input is not None:
            self._url_input.setFocus()
            self._url_input.selectAll()

    def _setup_toast_manager(self) -> None:
        self._toast_manager = ToastManager(self)

    # ---------------------------------------------------------------- wiring
    def _wire_title_bar(self) -> None:
        self._title_bar.minimize_requested.connect(self._on_minimize)
        self._title_bar.maximize_toggle_requested.connect(self._on_toggle_fullscreen)
        self._title_bar.close_requested.connect(self.close)
        self._title_bar.settings_toggle_requested.connect(self._toggle_config_bar)
        self._title_bar.history_toggle_requested.connect(self._on_toggle_history_panel)

    def _wire_control_bar(self) -> None:
        self._control_bar.play_clicked.connect(self._on_play_pause)
        self._control_bar.stop_clicked.connect(self._player.stop)
        self._control_bar.seek_requested.connect(self._on_seek_requested)
        self._control_bar.volume_requested.connect(self._player.set_volume)
        self._control_bar.quality_selected.connect(self._player.select_video_track)
        self._control_bar.fullscreen_toggle_requested.connect(self._on_toggle_fullscreen)
        self._control_bar.debug_toggle_requested.connect(self._toggle_debug_overlay)
        self._control_bar.previous_chapter_clicked.connect(lambda: self._on_shortcut_seek(-10.0))
        self._control_bar.next_chapter_clicked.connect(lambda: self._on_shortcut_seek(10.0))

    def _wire_history_panel(self) -> None:
        self._history_panel.panel_close_requested.connect(lambda: self._show_side_panel(None))
        self._history_panel.item_selected.connect(self._on_history_selected)
        self._history_panel.item_removed.connect(self._on_history_removed)
        self._history_panel.history_cleared.connect(self._on_history_cleared)

    def _wire_config_form(self) -> None:
        self._load_btn.clicked.connect(self._on_load_url)
        self._referer_input.editingFinished.connect(self._on_referer_changed)
        self._ua_combo.currentIndexChanged.connect(self._on_ua_combo_changed)
        self._ua_custom_input.editingFinished.connect(self._on_ua_custom_changed)
        self._cache_forward.valueChanged.connect(lambda _v: self._update_cache_labels())
        self._cache_back.valueChanged.connect(lambda _v: self._update_cache_labels())
        self._pause_refresh.valueChanged.connect(lambda _v: None)
        self._apply_btn.clicked.connect(self._on_cache_apply)
        self._delete_btn.clicked.connect(self._on_cache_clear)
        self._reset_btn.clicked.connect(self._on_reset_defaults)

    def _on_referer_changed(self) -> None:
        ref = self._referer_input.text().strip()
        self._pending_referer = ref
        headers = dict(self._pending_headers or {})
        if ref:
            headers["Referer"] = ref
            headers.pop("referer", None)
        else:
            headers.pop("Referer", None)
            headers.pop("referer", None)
        self._pending_headers = headers
        self._persist_settings()

    def _on_ua_combo_changed(self, index: int) -> None:
        data = self._ua_combo.itemData(index)
        if data == "__custom__":
            self._ua_custom_input.setVisible(True)
            self._ua_custom_input.setFocus()
            return
        self._ua_custom_input.setVisible(False)
        self._pending_user_agent = data or ""
        self._persist_settings()

    def _on_ua_custom_changed(self) -> None:
        text = self._ua_custom_input.text().strip()
        if text:
            self._pending_user_agent = text
            self._persist_settings()

    def _on_cache_apply(self) -> None:
        forward = self._cache_forward.value()
        back = self._cache_back.value()
        self._pending_referer = self._referer_input.text().strip()
        self._persist_settings()
        ok = self._player.apply_cache_settings(forward, back)
        if ok:
            self._show_toast(f"Cache: fwd {forward}MB / back {back}MB", "success")
        else:
            self._show_toast("Failed to apply cache", "error")

    def _on_cache_clear(self) -> None:
        forward = self._cache_forward.value()
        back = self._cache_back.value()
        ok = self._player.clear_cache()
        if ok:
            self._show_toast("Flushing buffer...", "info")
            QTimer.singleShot(200, lambda: self._restore_cache_after_clear(forward, back))
        else:
            self._show_toast("Failed to clear cache", "error")

    def _restore_cache_after_clear(self, forward: int, back: int) -> None:
        if self._player.apply_cache_settings(forward, back):
            self._show_toast("Buffer cleared", "success")
        else:
            self._show_toast("Buffer cleared; restore failed", "warning")

    def _on_reset_defaults(self) -> None:
        self._cache_forward.setValue(CACHE_DEFAULTS["forward"])
        self._cache_back.setValue(CACHE_DEFAULTS["back"])
        self._pause_refresh.setValue(CACHE_DEFAULTS["pause_refresh"])
        self._update_cache_labels()
        self._persist_settings()
        self._on_cache_apply()
        self._show_toast("Defaults restored", "info")

    def _update_cache_labels(self) -> None:
        if hasattr(self, "_cache_forward") and self._cache_forward is not None:
            self._cache_forward_label.setText(f"{self._cache_forward.value()} MB")
            self._cache_back_label.setText(f"{self._cache_back.value()} MB")
            self._pause_refresh_label.setText(f"{self._pause_refresh.value()} s")

    # ---------------------------------------------------------------- events
    def _on_minimize(self) -> None:
        self.showMinimized()

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.MouseMove and obj in (
            self,
            self._video_container,
            self._video_surface,
            self._control_bar,
        ):
            self._on_mouse_activity()
        if obj is self._video_container and event.type() in (QEvent.Resize,):
            self._resize_video_overlays()
            self._position_fullscreen_controls()
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event) -> None:
        self._on_mouse_activity()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        if self._maximized_state and self._auto_hide_armed and self._auto_hide_timer is not None:
            self._auto_hide_timer.start()
        super().leaveEvent(event)

    def _on_toggle_fullscreen(self) -> None:
        if self.isFullScreen() or self._maximized_state:
            self._exit_fullscreen()
        else:
            self._normal_geometry = self.geometry()
            self._enter_fullscreen()

    def _enter_fullscreen(self) -> None:
        self._pre_fullscreen_config_visible = self._config_bar_visible
        self._pre_fullscreen_history_visible = self._history_panel_visible
        if self._history_panel_visible:
            if self._panel_anim is not None and self._panel_anim.state() == QPropertyAnimation.State.Running:
                self._panel_anim.stop()
            self._history_panel_visible = False
            self._history_panel.setMaximumWidth(0)
            self._history_panel.setVisible(False)
            self._title_bar._history_btn.setProperty("active", False)
            self._title_bar._history_btn.style().unpolish(self._title_bar._history_btn)
            self._title_bar._history_btn.style().polish(self._title_bar._history_btn)

        self._config_bar_visible = False
        self._config_bar.setVisible(False)
        self._config_bar.setMaximumHeight(0)
        self._title_bar.setVisible(False)
        if self._info_bar is not None:
            self._info_bar.setVisible(False)
        if self.statusBar() is not None:
            self.statusBar().setVisible(False)

        self._move_control_bar_to_overlay()
        self.showFullScreen()
        self._maximized_state = True
        self._title_bar.set_maximized(True)
        self._control_bar.set_fullscreen(True)
        self._control_bar.setVisible(True)
        self._position_fullscreen_controls()
        self._start_auto_hide()
        self._focus_video_surface()

    def _move_control_bar_to_overlay(self) -> None:
        if self._control_bar_in_overlay or self._video_container is None or self._body_left_layout is None:
            return
        self._body_left_layout.removeWidget(self._control_bar)
        self._control_bar.setParent(self._video_container)
        self._control_bar.setWindowFlags(Qt.Widget)
        self._control_bar_in_overlay = True

    def _restore_control_bar_to_layout(self) -> None:
        if not self._control_bar_in_overlay or self._body_left_layout is None:
            return
        self._control_bar.setParent(self.centralWidget())
        self._body_left_layout.addWidget(self._control_bar)
        self._control_bar_in_overlay = False

    def _position_fullscreen_controls(self) -> None:
        if not self._control_bar_in_overlay or self._video_container is None:
            return
        margin = 18
        width = max(320, self._video_container.width() - (margin * 2))
        height = self._control_bar.height()
        x = margin
        y = self._video_container.height() - height - margin
        self._control_bar.setGeometry(x, max(0, y), width, height)
        self._control_bar.raise_()

    def _exit_fullscreen(self) -> None:
        if not self.isFullScreen() and not self._maximized_state:
            return
        self.showNormal()
        if self._normal_geometry is not None:
            self.setGeometry(self._normal_geometry)
        self._restore_control_bar_to_layout()
        self._title_bar.setVisible(True)
        self._config_bar_visible = self._pre_fullscreen_config_visible
        self._config_bar.setVisible(self._config_bar_visible)
        self._config_bar.setMaximumHeight(
            self._config_bar.preferredHeight() if self._config_bar_visible else 0
        )
        if self._info_bar is not None:
            self._info_bar.setVisible(True)
        if self.statusBar() is not None:
            self.statusBar().setVisible(True)
        if self._pre_fullscreen_history_visible:
            self._show_side_panel(self._history_panel)
        self._maximized_state = False
        self._title_bar.set_maximized(False)
        self._control_bar.set_fullscreen(False)
        self._stop_auto_hide()
        self._control_bar.setVisible(True)
        self._control_bar.setMaximumHeight(16777215)

    def _start_auto_hide(self) -> None:
        if self._auto_hide_timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(3000)
            timer.timeout.connect(self._on_auto_hide_timeout)
            self._auto_hide_timer = timer
        self._auto_hide_armed = True
        self._auto_hide_timer.start()
        self._show_chrome(animate=False)

    def _stop_auto_hide(self) -> None:
        if self._auto_hide_timer is not None:
            self._auto_hide_timer.stop()
        self._auto_hide_armed = False
        if self._cursor_hidden:
            from PySide6.QtWidgets import QApplication
            QApplication.restoreOverrideCursor()
            self._cursor_hidden = False

    def _on_auto_hide_timeout(self) -> None:
        if not self._maximized_state or not self._auto_hide_armed:
            return
        self._hide_chrome()
        self._hide_cursor()

    def _show_chrome(self, animate: bool = True) -> None:
        if self._control_bar_in_overlay:
            self._control_bar.setVisible(True)
            self._control_bar.setMaximumHeight(16777215)
            self._position_fullscreen_controls()
            return
        if not animate:
            self._title_bar.setVisible(True)
            self._title_bar.setMaximumHeight(16777215)
            self._title_bar.raise_()
            self._control_bar.setVisible(True)
            self._control_bar.setMaximumHeight(16777215)
            self._control_bar.raise_()
            return
        self._animate_chrome(show=True)

    def _hide_chrome(self) -> None:
        if self._control_bar_in_overlay:
            self._control_bar.setVisible(False)
            return
        self._animate_chrome(show=False)

    def _animate_chrome(self, show: bool) -> None:
        if self._title_bar.isVisible() != show:
            self._title_bar.setVisible(True)
        title_h = self._title_bar.height() if show else 0
        anim = QPropertyAnimation(self._title_bar, b"maximumHeight")
        anim.setDuration(Anim.DURATION_NORMAL)
        anim.setStartValue(self._title_bar.maximumHeight() if show else title_h)
        anim.setEndValue(title_h if show else 0)
        anim.setEasingCurve(Anim.EASE_OUT if show else Anim.EASE_IN)
        anim.start()
        self._title_anim = anim

        if self._control_bar.isVisible() != show:
            self._control_bar.setVisible(True)
        ctrl_h = self._control_bar.height() if show else 0
        ctrl_anim = QPropertyAnimation(self._control_bar, b"maximumHeight")
        ctrl_anim.setDuration(Anim.DURATION_NORMAL)
        ctrl_anim.setStartValue(self._control_bar.maximumHeight() if show else ctrl_h)
        ctrl_anim.setEndValue(ctrl_h if show else 0)
        ctrl_anim.setEasingCurve(Anim.EASE_OUT if show else Anim.EASE_IN)
        ctrl_anim.start()
        self._control_anim = ctrl_anim

        if not show:
            QTimer.singleShot(Anim.DURATION_NORMAL, lambda: (
                self._title_bar.setVisible(False),
                self._control_bar.setVisible(False),
            ))

    def _hide_cursor(self) -> None:
        if not self._cursor_hidden:
            from PySide6.QtWidgets import QApplication
            QApplication.setOverrideCursor(QCursor(Qt.BlankCursor))
            self._cursor_hidden = True

    def _show_cursor(self) -> None:
        if self._cursor_hidden:
            from PySide6.QtWidgets import QApplication
            QApplication.restoreOverrideCursor()
            self._cursor_hidden = False

    def _on_mouse_activity(self) -> None:
        if not self._maximized_state or not self._auto_hide_armed:
            return
        if self._cursor_hidden:
            self._show_cursor()
        if self._control_bar_in_overlay:
            if not self._control_bar.isVisible():
                self._show_chrome(animate=False)
        elif not self._title_bar.isVisible() or not self._control_bar.isVisible():
            self._show_chrome(animate=True)
        if self._auto_hide_timer is not None:
            self._auto_hide_timer.start()

    # ---------------------------------------------------------------- config bar
    def _toggle_config_bar(self) -> None:
        if self.isFullScreen():
            return
        self._config_bar_visible = not self._config_bar_visible
        if self._config_anim is not None and self._config_anim.state() == QPropertyAnimation.State.Running:
            self._config_anim.stop()
        target_h = self._config_bar.preferredHeight() if self._config_bar_visible else 0
        if self._config_bar_visible:
            self._config_bar.setVisible(True)
        anim = QPropertyAnimation(self._config_bar, b"maximumHeight")
        anim.setDuration(Anim.DURATION_NORMAL)
        anim.setStartValue(self._config_bar.maximumHeight() if self._config_bar_visible else self._config_bar.preferredHeight())
        anim.setEndValue(target_h)
        anim.setEasingCurve(Anim.EASE_OUT if self._config_bar_visible else Anim.EASE_IN)
        anim.start()
        self._config_anim = anim
        if not self._config_bar_visible:
            QTimer.singleShot(Anim.DURATION_NORMAL, lambda: self._config_bar.setVisible(False))
        # update title bar collapse icon
        self._title_bar._settings_btn.setProperty("active", not self._config_bar_visible)
        self._title_bar._settings_btn.style().unpolish(self._title_bar._settings_btn)
        self._title_bar._settings_btn.style().polish(self._title_bar._settings_btn)

    # ---------------------------------------------------------------- side panel
    def _on_toggle_history_panel(self) -> None:
        if self.isFullScreen():
            return
        self._show_side_panel(None if self._history_panel_visible else self._history_panel)

    def _show_side_panel(self, panel: Optional[QWidget]) -> None:
        if panel is None:
            target_history = False
        elif panel is self._history_panel:
            target_history = True
        else:
            return

        if target_history == self._history_panel_visible:
            return

        self._history_panel_visible = target_history
        self._title_bar._history_btn.setProperty("active", target_history)
        self._title_bar._history_btn.style().unpolish(self._title_bar._history_btn)
        self._title_bar._history_btn.style().polish(self._title_bar._history_btn)

        if self._panel_anim is not None and self._panel_anim.state() == QPropertyAnimation.State.Running:
            self._panel_anim.stop()

        width = HistoryPanel.PANEL_WIDTH

        if panel is None:
            anim_target = self._history_panel
            self._panel_anim = Anim.expand_horizontal(
                anim_target,
                0,
                duration=Anim.DURATION_PANEL,
                easing=Anim.EASE_OUT,
                on_finished=lambda: self._finalize_side_panel_anim(False),
            )
        else:
            self._history_panel.setVisible(True)
            self._history_panel.setMaximumWidth(0)
            self._current_side_panel = panel
            self._panel_anim = Anim.expand_horizontal(
                panel,
                width,
                duration=Anim.DURATION_PANEL,
                easing=Anim.EASE_OUT,
            )
        self._panel_anim.start()

    def _finalize_side_panel_anim(self, target_history: bool) -> None:
        if not target_history:
            self._history_panel.setMaximumWidth(0)
            self._history_panel.setVisible(False)

    def _on_user_agent_changed(self, ua: str) -> None:
        self._pending_user_agent = ua
        self._persist_settings()
        self._show_toast(f"User-Agent: {ua or 'Default'}", "info")

    def _on_history_selected(self, entry: dict) -> None:
        url = entry.get("url", "")
        if not url:
            return
        self._url_input.setText(url)
        ref = entry.get("referer", "")
        if ref:
            self._referer_input.setText(ref)
            self._pending_referer = ref
        ua = entry.get("user_agent", "") or self._pending_user_agent or ""
        ua = UA_ALIASES.get(ua, ua)  # migrasi token lama -> string penuh
        headers = entry.get("headers", {}) or self._pending_headers or {}
        if ua and ua in KNOWN_UA_VALUES:
            idx = self._ua_combo.findData(ua)
            if idx >= 0:
                self._ua_combo.setCurrentIndex(idx)
        elif ua:
            self._ua_combo.setCurrentIndex(self._ua_combo.findData("__custom__"))
            self._ua_custom_input.setText(ua)
            self._ua_custom_input.setVisible(True)
        self._show_toast(f"Loading: {entry.get('name', url)[:40]}", "info")
        self._start_playback(url, headers=dict(headers or {}), user_agent=ua, add_history=False)

    def _on_history_removed(self, url: str) -> None:
        self._show_toast("History entry removed", "info")

    def _on_history_cleared(self) -> None:
        self._show_toast("History cleared", "success")

    def _show_toast(self, message: str, kind: str = "info") -> None:
        if self._toast_manager is None:
            return
        self._toast_manager.show(message, kind)

    def _refresh_debug_state(self) -> None:
        if self._debug_overlay is None:
            return
        vol = "100"
        if self._player.is_initialized and self._player._player is not None:
            try:
                vol = str(int(self._player._player.mpv.volume))
            except Exception:
                pass
        refresh = "N/A"
        if self._pause_started_at is not None:
            elapsed = time.monotonic() - self._pause_started_at
            refresh = f"{max(0, self._pause_refresh.value() - int(elapsed))}s"
        self._debug_overlay.update_stats(
            {
                "state": self._player.state,
                "volume": vol,
                "refresh": refresh,
                "url": self._current_url[:48] + "..." if len(self._current_url) > 51 else self._current_url,
            }
        )

    def changeEvent(self, event) -> None:
        if event.type() == event.Type.WindowStateChange:
            if not self.isFullScreen() and self._control_bar_in_overlay:
                self._exit_fullscreen()
        super().changeEvent(event)

    # ---------------------------------------------------------------- ui tree
    def _setup_central_widget(self) -> None:
        central = QWidget()
        central.setObjectName("rootWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._title_bar)
        root.addWidget(self._build_config_bar())
        self._config_bar.setMaximumHeight(self._config_bar.preferredHeight())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        body_left = QWidget()
        body_left_layout = QVBoxLayout(body_left)
        self._body_left_layout = body_left_layout
        body_left_layout.setContentsMargins(0, 0, 0, 0)
        body_left_layout.setSpacing(0)
        body_left_layout.addWidget(self._build_video_area(), 1)
        body_left_layout.addWidget(self._build_info_bar())
        body_left_layout.addWidget(self._build_control_bar())
        body.addWidget(body_left, 1)

        body.addWidget(self._history_panel, 0)

        body_container = QWidget()
        body_container.setLayout(body)
        root.addWidget(body_container, 1)

    def _build_config_bar(self) -> "ConfigBar":
        self._config_bar = ConfigBar(self)
        # expose the child widgets
        self._load_btn = self._config_bar.load_btn
        self._url_input = self._config_bar.url_input
        self._referer_input = self._config_bar.referer_input
        self._ua_combo = self._config_bar.ua_combo
        self._ua_custom_input = self._config_bar.ua_custom_input
        self._cache_forward = self._config_bar.cache_forward
        self._cache_back = self._config_bar.cache_back
        self._pause_refresh = self._config_bar.pause_refresh
        self._cache_forward_label = self._config_bar.cache_forward_label
        self._cache_back_label = self._config_bar.cache_back_label
        self._pause_refresh_label = self._config_bar.pause_refresh_label
        self._apply_btn = self._config_bar.apply_btn
        self._delete_btn = self._config_bar.delete_btn
        self._reset_btn = self._config_bar.reset_btn
        # Pre-fill from persisted state
        if self._pending_user_agent:
            idx = self._ua_combo.findData(self._pending_user_agent)
            if idx >= 0:
                self._ua_combo.setCurrentIndex(idx)
        if self._pending_referer:
            self._referer_input.setText(self._pending_referer)
        cache = getattr(self, "_pending_cache", CACHE_DEFAULTS)
        self._config_bar.set_cache_values(cache["forward"], cache["back"], cache["pause_refresh"])
        return self._config_bar

    def _build_video_area(self) -> QWidget:
        container = QWidget()
        container.setObjectName("videoContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._video_surface = VideoSurface(container)
        self._video_surface.setMinimumSize(640, 360)
        self._video_surface.installEventFilter(self)
        layout.addWidget(self._video_surface)

        self._video_container = container
        self._video_placeholder = VideoPlaceholder(container)
        self._video_placeholder.setGeometry(container.rect())
        container.installEventFilter(self)
        self._debug_overlay = DebugOverlay(container)
        self._debug_overlay.setVisible(False)
        return container

    def _resize_video_overlays(self) -> None:
        if self._video_container is None:
            return
        rect = self._video_container.rect()
        if self._video_placeholder is not None:
            self._video_placeholder.setGeometry(rect)
        if self._debug_overlay is not None:
            self._debug_overlay._reposition()
        self._position_fullscreen_controls()

    def _build_info_bar(self) -> QWidget:
        bar = QWidget()
        self._info_bar = bar
        bar.setObjectName("infoBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        self._state_label = QLabel("Ready")
        self._state_label.setObjectName("statusReady")
        layout.addWidget(self._state_label)

        layout.addStretch(1)

        self._wid_label = QLabel("wid: -")
        self._wid_label.setStyleSheet("color: #71717a; font-family: Consolas, monospace; font-size: 8pt; background: transparent;")
        layout.addWidget(self._wid_label)

        self._position_label = QLabel("00:00 / 00:00")
        self._position_label.setStyleSheet("color: #a1a1aa; font-family: Consolas, monospace; font-size: 8pt; background: transparent;")
        layout.addWidget(self._position_label)
        return bar

    def _build_control_bar(self) -> ControlBar:
        self._control_bar = ControlBar(self)
        self._control_bar.setMouseTracking(True)
        self._control_bar.installEventFilter(self)
        return self._control_bar

    def _setup_status_bar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Ready")

    # ---------------------------------------------------------------- wiring signals
    def _connect_surface_signals(self) -> None:
        if self._video_surface is None:
            return
        self._video_surface.surface_ready.connect(self._on_surface_ready)
        self._video_surface.double_clicked.connect(self._on_toggle_fullscreen)

    def _on_surface_ready(self) -> None:
        if self._video_surface is None:
            return
        wid = self._video_surface.surface_wid
        if wid is None:
            return
        self._wid_label.setText(f"wid: {wid}")
        self._player.attach_surface(wid)
        if self._debug_overlay is not None and self._video_container is not None:
            self._debug_overlay.attach_to(self._video_container)
            self._debug_overlay.setVisible(self._debug_visible)
        if self._video_placeholder is not None and self._video_placeholder.isVisible():
            self._video_placeholder.raise_()

    def _wire_player_signals(self) -> None:
        self._player.initialized.connect(self._on_player_initialized)
        self._player.error_occurred.connect(self._on_player_error)
        self._player.state_changed.connect(self._on_player_state_changed)
        self._player.position_changed.connect(self._on_player_position)
        self._player.duration_changed.connect(self._on_player_duration)
        self._player.buffered_time_changed.connect(self._on_player_buffered)
        self._player.volume_changed.connect(self._on_player_volume)
        self._player.track_list_changed.connect(self._on_player_track_list)
        self._player.network_speed_changed.connect(self._on_player_network_speed)
        self._player.cache_state_changed.connect(self._on_player_cache_state)

    def _on_play_pause(self) -> None:
        if self._player.state == PlayerState.PAUSED and self._pause_started_at is not None:
            elapsed = time.monotonic() - self._pause_started_at
            if elapsed >= self._pause_refresh.value():
                self._refresh_stream()
                return
        self._player.toggle_pause()

    def _on_seek_requested(self, fraction: float) -> None:
        duration = self._player._duration if self._player else 0.0
        if duration > 0:
            target_seconds = fraction * duration
            self._player.seek(target_seconds, mode="absolute")

    def _on_player_volume(self, volume: int) -> None:
        self._control_bar.set_volume(volume)
        if self._debug_overlay is not None:
            self._debug_overlay.update_stats({"volume": f"{volume}"})

    def _on_player_network_speed(self, bps: float) -> None:
        if self._debug_overlay is None or not self._debug_visible:
            return
        if bps >= 1024 * 1024:
            text = f"{bps / (1024 * 1024):.2f} MB/s"
        elif bps >= 1024:
            text = f"{bps / 1024:.1f} KB/s"
        else:
            text = f"{bps:.0f} B/s"
        self._debug_overlay.update_stats({"speed": text})

    def _on_player_cache_state(self, cache_state: object) -> None:
        if not isinstance(cache_state, dict) or not self._debug_visible:
            return
        self._last_cache_state = dict(cache_state)
        self._update_debug_cache()

    def _update_debug_cache(self) -> None:
        if self._debug_overlay is None:
            return
        state = self._last_cache_state
        if not state:
            self._debug_overlay.update_stats({"cache": "-"})
            return
        used = state.get("cache-used")
        total = state.get("cache-size")
        if used is not None and total is not None:
            used_mb = int(used) / (1024 * 1024)
            total_mb = int(total) / (1024 * 1024)
            self._debug_overlay.update_stats({"cache": f"{used_mb:.1f} / {total_mb:.1f} MB"})
        else:
            self._debug_overlay.update_stats({"cache": "-"})

    def _on_player_buffered(self, buffered: float) -> None:
        duration = self._player._duration if self._player else 0.0
        self._control_bar.set_buffered(buffered, duration)
        if self._debug_overlay is not None:
            self._debug_overlay.update_stats({"buffered": self._format_time(buffered)})

    def _on_player_track_list(self, tracks: list) -> None:
        self._control_bar.set_track_list(tracks)
        if self._debug_overlay is not None:
            video_tracks = [t for t in (tracks or []) if isinstance(t, dict) and t.get("type") == "video"]
            audio_tracks = [t for t in (tracks or []) if isinstance(t, dict) and t.get("type") == "audio"]
            self._debug_overlay.update_stats(
                {
                    "tracks": f"{len(video_tracks)}V / {len(audio_tracks)}A",
                    "resolution": self._format_resolution(video_tracks[0]) if video_tracks else "-",
                    "codec": (video_tracks[0].get("codec") if video_tracks else "-") or "-",
                }
            )

    @staticmethod
    def _format_resolution(track: dict) -> str:
        w = track.get("width")
        h = track.get("height")
        if w and h:
            return f"{int(w)}x{int(h)}"
        if h:
            return f"{int(h)}p"
        return "-"

    def _on_player_initialized(self) -> None:
        self._log_status("Player initialized")

    def _on_player_error(self, message: str) -> None:
        self._log_status(f"Error: {message}")
        self._show_toast(f"Player error: {message[:80]}", "error")

    def _on_player_state_changed(self, state: str) -> None:
        object_name = {
            PlayerState.PLAYING: "statusPlaying",
            PlayerState.PAUSED: "statusPaused",
            PlayerState.LOADING: "statusLoading",
            PlayerState.STOPPED: "statusStopped",
            PlayerState.ERROR: "statusStopped",
        }.get(state, "statusReady")
        self._state_label.setObjectName(object_name)
        self._state_label.setText(state.capitalize())
        self._state_label.style().unpolish(self._state_label)
        self._state_label.style().polish(self._state_label)
        self._control_bar.set_playing(state == PlayerState.PLAYING)
        if state == PlayerState.PAUSED:
            if self._pause_started_at is None:
                self._pause_started_at = time.monotonic()
        elif state == PlayerState.PLAYING:
            self._pause_started_at = None
            QTimer.singleShot(500, self._maybe_prompt_resume)
        elif state in (PlayerState.STOPPED, PlayerState.ERROR, PlayerState.IDLE):
            self._pause_started_at = None
        if self._debug_overlay is not None:
            self._debug_overlay.update_stats({"state": state})
        # Show / hide placeholder based on player state
        if self._video_placeholder is not None:
            if state in (PlayerState.PLAYING, PlayerState.PAUSED, PlayerState.LOADING):
                self._video_placeholder.hide_animated()
            elif state in (PlayerState.STOPPED, PlayerState.ERROR, PlayerState.IDLE):
                self._video_placeholder.show_animated()

    def _on_player_position(self, pos: float) -> None:
        duration = self._player._duration if self._player else 0.0
        self._position_label.setText(f"{self._format_time(pos)} / {self._format_time(duration)}")
        self._control_bar.set_position(pos, duration)
        self._save_progress_periodically(pos, duration)
        if self._debug_overlay is not None:
            self._debug_overlay.update_stats({"position": self._format_time(pos)})

    def _on_player_duration(self, duration: float) -> None:
        pos = 0.0
        self._position_label.setText(f"{self._format_time(pos)} / {self._format_time(duration)}")
        self._control_bar.set_position(pos, duration)
        if self._debug_overlay is not None:
            self._debug_overlay.update_stats({"duration": self._format_time(duration)})

    def _toggle_debug_overlay(self) -> None:
        if self._debug_overlay is None or self._video_container is None:
            return
        self._debug_visible = not self._debug_visible
        self._debug_overlay.setVisible(self._debug_visible)
        self._control_bar.set_debug(self._debug_visible)
        if self._debug_visible:
            self._debug_overlay.attach_to(self._video_container)
            self._refresh_debug_state()

    def _on_load_url(self) -> None:
        url = self._url_input.text().strip()
        if not url:
            self._show_toast("Please enter a stream URL", "warning")
            return
        self._show_toast(f"Loading: {url[:60]}", "info")
        self._on_referer_changed()
        ua = self._pending_user_agent or ""
        headers = dict(self._pending_headers or {})
        self._start_playback(url, headers=headers, user_agent=ua, add_history=True)

    def _start_playback(
        self,
        url: str,
        headers: Optional[dict] = None,
        user_agent: str = "",
        add_history: bool = True,
    ) -> None:
        if self._video_placeholder is not None:
            self._video_placeholder.hide_now()
        self._current_url = url
        self._current_headers = dict(headers or {})
        self._current_user_agent = user_agent or ""
        self._last_progress_save_second = -1
        self._pause_started_at = None
        self._player.play(url, headers=headers, user_agent=user_agent)
        if add_history:
            self._history_panel.add_entry(
                url,
                name=url,
                meta={
                    "referer": self._pending_referer,
                    "user_agent": self._pending_user_agent,
                    "headers": self._pending_headers,
                },
            )

    def _save_progress_periodically(self, pos: float, duration: float) -> None:
        if not self._current_url or pos is None or pos < 0:
            return
        second = int(pos)
        if second <= 0 or second == self._last_progress_save_second or second % 5 != 0:
            return
        self._last_progress_save_second = second
        try:
            self._history_panel.update_progress(self._current_url, pos, duration)
        except Exception:
            pass

    def _maybe_prompt_resume(self) -> None:
        if not self._current_url or self._resume_prompted_for_url == self._current_url:
            return
        item = get_history_item(self._current_url)
        pos = float((item or {}).get("last_position") or 0)
        if pos <= 5:
            return
        self._resume_prompted_for_url = self._current_url
        self._player.toggle_pause()
        answer = QMessageBox.question(
            self,
            "Resume Playback",
            f"Resume from {format_time(pos)}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._retry_seek(pos)
        self._player.toggle_pause()

    def _retry_seek(self, pos: float, attempt: int = 1) -> None:
        if not self._player.is_initialized:
            return
        try:
            self._player.seek(pos, mode="absolute")
            return
        except Exception:
            if attempt < 10:
                QTimer.singleShot(500, lambda: self._retry_seek(pos, attempt + 1))
            else:
                self._show_toast("Failed to resume: stream is not seekable", "error")

    def _refresh_stream(self) -> None:
        if not self._current_url or not self._player.is_initialized:
            return
        pos = self._player._player.get_time_pos() if self._player._player is not None else 0
        pos = float(pos or 0)
        self._show_toast("Refreshing stream...", "info")
        self._player.stop()
        self._player.apply_cache_settings(self._cache_forward.value(), self._cache_back.value())
        self._player.play(
            self._current_url,
            headers=self._current_headers,
            user_agent=self._current_user_agent,
        )
        self._pause_started_at = None
        QTimer.singleShot(500, lambda: self._retry_seek(pos))

    def _show_shortcuts_dialog(self) -> None:
        message = "\n".join(
            [
                "Playback",
                "Space - Play / Pause",
                "Left / Right - Seek -10s / +10s",
                "Shift+Left / Shift+Right - Seek -30s / +30s",
                "S - Stop",
                "Up / Down - Volume +5 / -5",
                "M - Mute / Unmute",
                "",
                "View",
                "F - Toggle fullscreen",
                "Esc - Exit fullscreen",
                "H - Toggle history",
                "Ctrl+, - Toggle config bar",
                "",
                "Other",
                "Ctrl+L or Ctrl+O - Focus stream URL",
                "F12 or Ctrl+D - Toggle debug overlay",
                "F1 - Show this dialog",
            ]
        )
        QMessageBox.information(self, "Keyboard Shortcuts", message)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._toast_manager is not None:
            self._toast_manager._reposition()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if getattr(self, "_startup_fade_done", False):
            return
        self._startup_fade_done = True

        # The whole window is shown instantly. Only the video placeholder has
        # a brief fade-in for visual polish — the rest of the UI does not
        # fade in, so the user sees one smooth, unified appearance.
        if self._video_placeholder is not None:
            self._video_placeholder.show_animated()

        QTimer.singleShot(0, self._focus_video_surface)

        # Kick off the heavy mpv initialization on the next event-loop tick.
        # The libmpv DLL load happens AFTER the first paint, so the window
        # never appears half-built.
        QTimer.singleShot(0, self._initialize_player_deferred)

    def _focus_video_surface(self) -> None:
        if self._video_surface is not None:
            self._video_surface.setFocus(Qt.OtherFocusReason)

    def _initialize_player_deferred(self) -> None:
        """Called after the first paint to avoid blocking the event loop."""
        if not self._player.is_initialized:
            self._player.initialize()

    def closeEvent(self, event) -> None:
        self._persist_settings()
        self._history_panel.flush_pending()  # simpan posisi terakhir yang masih di-debounce
        self._player.terminate()
        super().closeEvent(event)

    @staticmethod
    def stylesheet_path() -> str:
        return str(Path(__file__).parent / "theme" / "styles.qss")

    def _log_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 5000)

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds is None or seconds < 0:
            seconds = 0
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


# ---------------------------------------------------------------- Config bar
class ConfigBar(QWidget):
    """Top config card with URL, referer, user-agent, cache tuning."""

    PREFERRED_HEIGHT = 168

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("configBar")
        self.setAttribute(Qt.WA_StyledBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(10)

        card = QWidget()
        card.setObjectName("configBarCard")
        outer.addWidget(card)

        grid = QGridLayout(card)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 2)
        grid.setColumnStretch(4, 0)
        grid.setColumnStretch(5, 0)
        grid.setColumnStretch(6, 0)
        grid.setColumnStretch(7, 0)
        grid.setColumnStretch(8, 0)
        grid.setColumnStretch(9, 0)

        # Row 1 — URL
        url_label = QLabel("Stream URL")
        url_label.setObjectName("fieldLabel")
        grid.addWidget(url_label, 0, 0, 1, 1, Qt.AlignVCenter)

        self.url_input = QLineEdit()
        self.url_input.setObjectName("urlInput")
        self.url_input.setPlaceholderText("https://example.com/stream.m3u8")
        grid.addWidget(self.url_input, 0, 1, 1, 8)

        self.load_btn = QPushButton("Load Stream")
        self.load_btn.setObjectName("primaryButton")
        grid.addWidget(self.load_btn, 0, 9, 1, 1)

        # Row 2 — Referer + User Agent
        ref_label = QLabel("Referer")
        ref_label.setObjectName("fieldLabel")
        grid.addWidget(ref_label, 1, 0, 1, 1, Qt.AlignVCenter)

        self.referer_input = QLineEdit()
        self.referer_input.setPlaceholderText("https://example.com (optional)")
        grid.addWidget(self.referer_input, 1, 1, 1, 5)

        ua_label = QLabel("User Agent")
        ua_label.setObjectName("fieldLabel")
        ua_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(ua_label, 1, 6, 1, 1)

        self.ua_combo = QComboBox()
        self.ua_combo.setObjectName("userAgentCombo")
        self.ua_combo.addItem("Default", "")
        self.ua_combo.addItem("Chrome (Windows)", USER_AGENTS["Chrome"])
        self.ua_combo.addItem("Firefox (Windows)", USER_AGENTS["Firefox"])
        self.ua_combo.addItem("Safari (macOS)", USER_AGENTS["Safari"])
        self.ua_combo.addItem("Edge (Windows)", USER_AGENTS["Edge"])
        self.ua_combo.addItem("Custom...", "__custom__")
        grid.addWidget(self.ua_combo, 1, 7, 1, 3)

        # Hidden custom UA input
        self.ua_custom_input = QLineEdit()
        self.ua_custom_input.setObjectName("userAgentCustom")
        self.ua_custom_input.setPlaceholderText("Custom User-Agent string")
        self.ua_custom_input.setVisible(False)
        grid.addWidget(self.ua_custom_input, 2, 7, 1, 3)

        # Row 3 — Cache settings
        cache_label = QLabel("Cache")
        cache_label.setObjectName("fieldLabel")
        grid.addWidget(cache_label, 2, 0, 1, 1, Qt.AlignVCenter)

        self.cache_forward, self.cache_forward_label = self._build_field(
            "Forward", 0, 500, 100, "MB", row=2, col=1,
        )
        self.cache_back, self.cache_back_label = self._build_field(
            "Back", 0, 500, 100, "MB", row=2, col=2,
        )
        self.pause_refresh, self.pause_refresh_label = self._build_field(
            "Refresh", 5, 600, 60, "s", row=2, col=3,
        )

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("primaryButton")
        grid.addWidget(self.apply_btn, 2, 4, 1, 1)

        self.delete_btn = QPushButton("Delete Buffer")
        self.delete_btn.setObjectName("dangerButton")
        grid.addWidget(self.delete_btn, 2, 5, 1, 1)

        self.reset_btn = QPushButton("Reset Defaults")
        self.reset_btn.setObjectName("ghostButton")
        grid.addWidget(self.reset_btn, 2, 6, 1, 1)

        # Stretch the remaining columns (8, 9) to push the load button
        grid.setColumnStretch(8, 1)
        grid.setColumnStretch(9, 0)

    def preferredHeight(self) -> int:
        return self.PREFERRED_HEIGHT

    def set_cache_values(self, forward: int, back: int, pause_refresh: int) -> None:
        self.cache_forward.setValue(int(forward))
        self.cache_back.setValue(int(back))
        self.pause_refresh.setValue(int(pause_refresh))
        self._update_labels()

    def _build_field(
        self,
        name: str,
        min_v: int,
        max_v: int,
        default: int,
        suffix: str,
        row: int,
        col: int,
    ):
        wrapper = QWidget()
        wrapper.setObjectName("spinRow")
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        field = QLabel(name)
        field.setObjectName("fieldLabel")
        field.setAlignment(Qt.AlignVCenter)
        layout.addWidget(field)

        spin = QSpinBox()
        spin.setObjectName("cacheSpin")
        spin.setRange(min_v, max_v)
        spin.setValue(default)
        spin.setSuffix(f" {suffix}")
        spin.setMinimumWidth(96)
        spin.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(spin)

        # Add into the card grid
        card = self.findChild(QWidget, "configBarCard")
        if card is not None and card.layout() is not None:
            card.layout().addWidget(wrapper, row, col, 1, 1)

        label = QLabel(f"{default} {suffix}")
        label.setObjectName("formLabel")
        label.setStyleSheet("color: #71717a; font-size: 8pt;")
        label.setVisible(False)
        return spin, label

    def _update_labels(self) -> None:
        if hasattr(self, "cache_forward_label"):
            self.cache_forward_label.setText(f"{self.cache_forward.value()} MB")
            self.cache_back_label.setText(f"{self.cache_back.value()} MB")
            self.pause_refresh_label.setText(f"{self.pause_refresh.value()} s")
