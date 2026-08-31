#!/usr/bin/env python3
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QApplication

from src.app.main_window import MainWindow
from src.app.theme.colors import Colors


def _apply_dark_palette(app: QApplication) -> None:
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(Colors.BG))
    palette.setColor(QPalette.WindowText, QColor(Colors.TEXT))
    palette.setColor(QPalette.Base, QColor(Colors.INPUT))
    palette.setColor(QPalette.AlternateBase, QColor(Colors.BG))
    palette.setColor(QPalette.ToolTipBase, QColor(Colors.CARD))
    palette.setColor(QPalette.ToolTipText, QColor(Colors.TEXT))
    palette.setColor(QPalette.Text, QColor(Colors.TEXT))
    palette.setColor(QPalette.Button, QColor(Colors.INPUT))
    palette.setColor(QPalette.ButtonText, QColor(Colors.TEXT))
    palette.setColor(QPalette.BrightText, QColor(Colors.DANGER))
    palette.setColor(QPalette.Link, QColor(Colors.ACCENT))
    palette.setColor(QPalette.Highlight, QColor(Colors.ACCENT_DARK))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(Colors.TEXT_DISABLED))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(Colors.TEXT_DISABLED))
    app.setPalette(palette)


def _load_stylesheet(app: QApplication) -> None:
    qss_path = Path(MainWindow.stylesheet_path())
    if not qss_path.exists():
        print(f"[warn] stylesheet not found: {qss_path}", file=sys.stderr)
        return
    app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def _build_app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)

        gradient = QLinearGradient(0, 0, 0, size)
        gradient.setColorAt(0.0, QColor("#0098FF"))
        gradient.setColorAt(1.0, QColor("#005FA3"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        radius = max(2, int(size * 0.18))
        painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

        painter.setBrush(QColor("#ffffff"))
        cx = size * 0.42
        cy = size * 0.5
        w = size * 0.36
        h = size * 0.42
        from PySide6.QtGui import QPolygonF

        poly = QPolygonF([
            QPointF(cx, cy - h / 2),
            QPointF(cx + w, cy),
            QPointF(cx, cy + h / 2),
        ])
        painter.drawPolygon(poly)
        painter.end()
        icon.addPixmap(pix)
    return icon


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("M3U8 Player")
    app.setOrganizationName("M3U8-Streaming")
    app.setApplicationDisplayName("M3U8 Player")
    app.setWindowIcon(_build_app_icon())

    _apply_dark_palette(app)
    _load_stylesheet(app)

    window = MainWindow()
    window.setWindowIcon(app.windowIcon())
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
