from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.app.theme.animations import Anim
from src.utils import (
    format_time,
    load_history,
    save_history,
    write_history,
)


class _HistoryItemDelegate(QStyledItemDelegate):
    """Paints each history row with title, URL, time and progress.

    Keeps the row compact yet readable with two lines of text and a subtle
    progress bar at the bottom that shows how far the user got into the
    stream last time.
    """

    PADDING_X = 12
    PADDING_Y = 8
    SPACING = 2
    PROGRESS_HEIGHT = 3

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(option.rect.width() or 280, 68)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = option.rect
        is_selected = bool(option.state & QStyle.State_Selected)
        is_hover = bool(option.state & QStyle.State_MouseOver)

        if is_selected:
            painter.fillRect(rect, QColor("#007ACC"))
        elif is_hover:
            painter.fillRect(rect, QColor("#1a1a1a"))
        else:
            painter.fillRect(rect, QColor("#0f0f0f"))

        title = index.data(Qt.UserRole) or ""
        url = index.data(Qt.UserRole + 1) or ""
        ts = index.data(Qt.UserRole + 2) or ""
        pos = index.data(Qt.UserRole + 3) or 0
        duration = index.data(Qt.UserRole + 4) or 0

        text_x = rect.x() + self.PADDING_X
        text_w = rect.width() - self.PADDING_X * 2

        # Title
        title_rect = rect.adjusted(self.PADDING_X, self.PADDING_Y, -self.PADDING_X, 0)
        title_rect.setHeight(20)
        title_font = QFont(option.font)
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize())
        painter.setFont(title_font)
        painter.setPen(QColor("#ffffff") if is_selected else QColor("#ffffff"))
        elided_title = painter.fontMetrics().elidedText(title, Qt.ElideRight, text_w)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_title)

        # URL (gray, smaller)
        url_rect = title_rect.adjusted(0, title_rect.height() + self.SPACING, 0, 0)
        url_rect.setHeight(16)
        url_font = QFont(option.font)
        url_font.setPointSize(url_font.pointSize() - 1)
        painter.setFont(url_font)
        painter.setPen(QColor("#dddddd") if is_selected else QColor("#aaaaaa"))
        elided_url = painter.fontMetrics().elidedText(url, Qt.ElideMiddle, text_w)
        painter.drawText(url_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_url)

        # Footer: timestamp | position
        footer_rect = url_rect.adjusted(0, url_rect.height() + self.SPACING, 0, 0)
        footer_rect.setHeight(14)
        footer_font = QFont(option.font)
        footer_font.setPointSize(footer_font.pointSize() - 1)
        painter.setFont(footer_font)
        painter.setPen(QColor("#dddddd") if is_selected else QColor("#666666"))
        pos_text = f"Pos {format_time(pos)}" if pos else ""
        if duration and duration > 0:
            pos_text = f"{pos_text} / {format_time(duration)}" if pos_text else f"Dur {format_time(duration)}"
        footer_text = ts
        if pos_text:
            footer_text = f"{footer_text}  -  {pos_text}"
        elided_footer = painter.fontMetrics().elidedText(footer_text, Qt.ElideRight, text_w)
        painter.drawText(footer_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_footer)

        # Progress bar
        if duration and duration > 0 and pos:
            progress = max(0.0, min(1.0, pos / duration))
            prog_y = rect.bottom() - self.PROGRESS_HEIGHT
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#005FA3"))
            painter.drawRect(rect.x(), prog_y, int(rect.width() * progress), self.PROGRESS_HEIGHT)
            if not is_selected:
                painter.setBrush(QColor("#1a1a1a"))
                painter.drawRect(
                    rect.x() + int(rect.width() * progress),
                    prog_y,
                    rect.width() - int(rect.width() * progress),
                    self.PROGRESS_HEIGHT,
                )

        painter.restore()


class HistoryPanel(QWidget):
    """Side panel showing recent playback history with click-to-load."""

    item_selected = Signal(dict)
    item_removed = Signal(str)
    history_cleared = Signal()
    panel_close_requested = Signal()

    PANEL_WIDTH = 320
    FLUSH_DEBOUNCE_MS = 30_000  # tulis disk maks. 1x/30 detik saat streaming

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("historyPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(self.PANEL_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._history: List[dict] = []
        self._items: dict = {}  # url -> QListWidgetItem, untuk update baris tunggal
        self._flush_timer: Optional[QTimer] = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("History")
        title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #007ACC;")
        header.addWidget(title)
        header.addStretch(1)
        close_btn = QToolButton()
        close_btn.setText("\u2715")
        close_btn.setObjectName("controlButton")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("Close panel")
        close_btn.clicked.connect(self.panel_close_requested)
        header.addWidget(close_btn)
        outer.addLayout(header)

        self._list = QListWidget()
        self._list.setObjectName("historyList")
        self._list.setItemDelegate(_HistoryItemDelegate(self._list))
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.itemClicked.connect(self._on_item_clicked)
        outer.addWidget(self._list, 1)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("controlButton")
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)
        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("dangerButton")
        clear_btn.clicked.connect(self._on_clear_all)
        btn_row.addWidget(clear_btn)
        outer.addLayout(btn_row)

        self.refresh()

    # ------------------------------------------------------------------ public
    def refresh(self) -> None:
        self.flush_pending()  # pastikan perubahan yang belum ter-flush tidak hilang
        self._history = load_history() or []
        self._populate()

    def add_entry(self, url: str, name: Optional[str] = None, meta: Optional[dict] = None) -> None:
        save_history(url, name, meta=meta)
        self.refresh()

    def update_progress(self, url: str, position: float, duration: float = 0) -> None:
        """Update posisi terakhir tanpa menulis disk / rebuild list setiap kali.

        Hanya baris item yang bersangkutan yang di-update; penulisan ke disk
        di-debounce dan dilakukan oleh :meth:`flush_pending`.
        """
        if not url:
            return
        entry = self._find_entry(url)
        if entry is None:
            save_history(url)
            self._history = load_history() or []
            self._populate()
            entry = self._find_entry(url)
        if entry is None:
            return
        entry["last_position"] = position
        if duration > 0:
            entry["duration"] = duration
        entry["timestamp"] = datetime.now().isoformat()

        item = self._items.get(url)
        if item is not None:
            item.setData(Qt.UserRole + 3, entry.get("last_position", 0) or 0)
            item.setData(Qt.UserRole + 4, entry.get("duration", 0) or 0)
            # repaint hanya baris item tersebut (bukan seluruh list)
            self._list.viewport().update(self._list.visualItemRect(item))
        self._schedule_disk_flush()

    def _find_entry(self, url: str) -> Optional[dict]:
        for candidate in self._history:
            if candidate.get("url") == url:
                return candidate
        return None

    def _schedule_disk_flush(self) -> None:
        if self._flush_timer is None:
            self._flush_timer = QTimer(self)
            self._flush_timer.setSingleShot(True)
            self._flush_timer.timeout.connect(self.flush_pending)
        self._flush_timer.start(self.FLUSH_DEBOUNCE_MS)

    def flush_pending(self) -> None:
        """Tulis riwayat ke disk bila ada perubahan yang belum ter-flush."""
        if self._flush_timer is not None:
            self._flush_timer.stop()
        if self._history:
            write_history(self._history)

    def get_history(self) -> List[dict]:
        return list(self._history)

    # ------------------------------------------------------------------ internal
    def _populate(self) -> None:
        self._list.clear()
        self._items.clear()
        for entry in self._history:
            item = QListWidgetItem()
            ts = entry.get("timestamp", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    ts = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    ts = ""
            title = entry.get("name") or entry.get("url", "")
            item.setData(Qt.UserRole, title)
            item.setData(Qt.UserRole + 1, entry.get("url", ""))
            item.setData(Qt.UserRole + 2, ts)
            item.setData(Qt.UserRole + 3, entry.get("last_position", 0) or 0)
            item.setData(Qt.UserRole + 4, entry.get("duration", 0) or 0)
            item.setData(Qt.UserRole + 5, entry)
            self._items[entry.get("url", "")] = item
            self._list.addItem(item)

        if self._list.count() == 0:
            empty = QListWidgetItem("No history yet. Play a stream to start.")
            empty.setFlags(Qt.NoItemFlags)
            empty.setForeground(QColor("#666666"))
            font = QFont()
            font.setItalic(True)
            empty.setFont(font)
            self._list.addItem(empty)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        entry = item.data(Qt.UserRole + 5)
        if isinstance(entry, dict):
            self.item_selected.emit(entry)

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        entry = item.data(Qt.UserRole + 5)
        if not isinstance(entry, dict):
            return

        menu = QMenu(self)
        load_action = QAction("Load", self)
        load_action.triggered.connect(lambda: self.item_selected.emit(entry))
        menu.addAction(load_action)
        menu.addSeparator()
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self._on_remove_entry(entry))
        menu.addAction(remove_action)
        menu.exec(self._list.mapToGlobal(pos))

    def _on_remove_entry(self, entry: dict) -> None:
        url = entry.get("url")
        if not url:
            return
        self._history = [h for h in self._history if h.get("url") != url]
        write_history(self._history)
        self._populate()
        self.item_removed.emit(url)

    def _on_clear_all(self) -> None:
        self._history = []
        write_history(self._history)
        self._populate()
        self.history_cleared.emit()
