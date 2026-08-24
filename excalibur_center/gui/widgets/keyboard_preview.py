"""Interactive keyboard preview widget with three clickable LED zones."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from ...core.config import Brightness, RGBColor, Zone

BRIGHTNESS_FACTOR = {
    int(Brightness.OFF): 0.16,
    int(Brightness.MID): 0.55,
    int(Brightness.MAX): 1.00,
}

_ROWS = [
    ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "⌫"],
    ["Tab", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "\\"],
    ["Caps", "A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'", "Enter"],
    ["Shift", "\\", "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Shift"],
    ["Ctrl", "Fn", "Win", "Alt", "", "", "", "", "", "Alt", "Ctrl", "←", "↑", "↓", "→"],
]

_WIDE = {"Tab": 1.6, "Caps": 1.8, "Shift": 2.0, "Enter": 1.9, "⌫": 1.8}


class KeyboardPreview(QWidget):
    """Draws a stylized keyboard whose colors mirror the live LED state."""

    zone_clicked = pyqtSignal(object)  # Zone

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(560, 190)
        self._colors: dict[int, tuple[str, int]] = {
            int(Zone.LEFT): ("FFFFFF", int(Brightness.MAX)),
            int(Zone.CENTER): ("FFFFFF", int(Brightness.MAX)),
            int(Zone.RIGHT): ("FFFFFF", int(Brightness.MAX)),
        }
        self._selected: int = int(Zone.ALL)
        self.setMouseTracking(False)

    # ── public ───────────────────────────────────────────────
    def set_state(self, colors_by_zone: dict[int, tuple[str, int]]) -> None:
        """colors_by_zone: zone code -> ('RRGGBB', brightness)."""
        self._colors.update(colors_by_zone)
        self.update()

    def set_selected(self, zone: int) -> None:
        self._selected = zone
        self.update()

    # ── painting ─────────────────────────────────────────────
    def _zone_for_x(self, x_ratio: float) -> Zone:
        if x_ratio < 1 / 3:
            return Zone.LEFT
        if x_ratio < 2 / 3:
            return Zone.CENTER
        return Zone.RIGHT

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        pad = 10
        area = QRectF(pad, pad, w - 2 * pad, h - 2 * pad)

        # deck plate
        plate = QPainterPath()
        plate.addRoundedRect(area, 12, 12)
        painter.fillPath(plate, QColor("#101218"))
        painter.setPen(QPen(QColor("#23262e"), 1))
        painter.drawPath(plate)

        rows = len(_ROWS)
        unit_w = area.width() / 16.2
        row_h = area.height() / rows
        key_font = QFont(self.font())
        key_font.setPixelSize(max(8, int(row_h * 0.28)))

        zone_rects: dict[int, list[QRectF]] = {3: [], 4: [], 5: []}

        for r, row in enumerate(_ROWS):
            total_units = sum(_WIDE.get(k, 1.0) for k in row)
            scale = (area.width() - 8) / (total_units * unit_w)
            x = area.left() + 4
            y = area.top() + r * row_h + 3
            kh = row_h - 7
            for label in row:
                kw = unit_w * _WIDE.get(label, 1.0) * scale
                rect = QRectF(x, y, kw - 3, kh)
                cx_ratio = (x + kw / 2 - area.left()) / area.width()
                zone = self._zone_for_x(cx_ratio)
                code = int(zone)
                zone_rects[code].append(rect)
                hex_color, bri = self._colors.get(code, ("FFFFFF", 2))
                base = QColor(f"#{hex_color}")
                factor = BRIGHTNESS_FACTOR.get(bri, 1.0)
                lit = QColor(int(base.red() * factor),
                             int(base.green() * factor),
                             int(base.blue() * factor))
                lit.setAlpha(255 if factor > 0.2 else 120)
                key_path = QPainterPath()
                key_path.addRoundedRect(rect, 4, 4)
                painter.fillPath(key_path, lit)
                if code == self._selected:
                    painter.setPen(QPen(QColor("#4d80ff"), 1))
                else:
                    painter.setPen(QPen(QColor(0, 0, 0, 96), 1))
                painter.drawPath(key_path)
                if label and factor > 0.2:
                    painter.setPen(QColor("#0c0d10"))
                    painter.setFont(key_font)
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
                x += kw

        # zone outlines hugging each key cluster (replaces dashed lines)
        for code, rects in zone_rects.items():
            if not rects:
                continue
            left = min(rc.left() for rc in rects)
            right = max(rc.right() for rc in rects)
            top = min(rc.top() for rc in rects)
            bottom = max(rc.bottom() for rc in rects)
            outline = QRectF(left - 5, top - 5,
                             (right - left) + 10, (bottom - top) + 10)
            path = QPainterPath()
            path.addRoundedRect(outline, 9, 9)
            if code == self._selected:
                painter.setPen(QPen(QColor("#4d80ff"), 2))
            else:
                painter.setPen(QPen(QColor(255, 255, 255, 28), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    # ── interaction ──────────────────────────────────────────
    def mousePressEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        w = self.width()
        inner_left = 10
        inner_width = w - 20
        ratio = (pos.x() - inner_left) / max(inner_width, 1)
        ratio = min(max(ratio, 0.0), 0.999)
        self.zone_clicked.emit(self._zone_for_x(ratio))
