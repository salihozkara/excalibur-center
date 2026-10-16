"""Lighting page: zone selection, colors and brightness."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..backend.led import EFFECTS
from ..core.config import Brightness, RGBColor, Zone
from ..core.i18n import t
from .widgets.keyboard_preview import KeyboardPreview

PRESETS: list[str] = [
    "FFFFFF", "FF2D2D", "FF7A00", "FFD500",
    "38D900", "00E5A0", "00C8FF", "2952FF",
    "7B00FF", "FF00C8", "FF6B9E", "C0C8D4",
]

ZONE_KEYS = {
    int(Zone.LEFT): "zone.left", int(Zone.CENTER): "zone.center",
    int(Zone.RIGHT): "zone.right", int(Zone.ALL): "zone.all",
}
BRI_KEYS = {0: "bri.off", 1: "bri.mid", 2: "bri.max"}
EFFECT_KEYS = {
    1: "effect.normal", 2: "effect.blink", 3: "effect.fade",
    4: "effect.heartbeat", 5: "effect.repeat", 6: "effect.random",
    7: "effect.ambilight",
}


class LightingPage(QWidget):
    def __init__(self, led_backend, profile_manager, set_status, parent=None):
        super().__init__(parent)
        self.led = led_backend
        self.pm = profile_manager
        self.set_status = set_status
        self.selected_zone: int = int(Zone.ALL)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel(t("lighting.title"))
        title.setObjectName("pageTitle")
        desc = QLabel(t("lighting.desc"))
        desc.setObjectName("pageDesc")
        root.addWidget(title)
        root.addWidget(desc)

        self.preview = KeyboardPreview()
        self.preview.zone_clicked.connect(self._on_preview_click)
        root.addWidget(self.preview)

        zone_row = QHBoxLayout()
        zone_row.setSpacing(8)
        self.zone_buttons: dict[int, QPushButton] = {}
        for code in (int(Zone.LEFT), int(Zone.CENTER), int(Zone.RIGHT), int(Zone.ALL)):
            btn = QPushButton(t(ZONE_KEYS[code]))
            btn.setCheckable(True)
            btn.setObjectName("brightnessChip")
            btn.clicked.connect(lambda _=False, z=code: self.select_zone(z))
            self.zone_buttons[code] = btn
            zone_row.addWidget(btn)
        zone_row.addStretch()
        root.addLayout(zone_row)

        grid_frame = QFrame()
        grid_frame.setObjectName("card")
        grid = QGridLayout(grid_frame)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(12)

        lbl = QLabel(t("lighting.presets"))
        lbl.setObjectName("cardTitle")
        grid.addWidget(lbl, 0, 0, 1, 3)

        for i, hex_color in enumerate(PRESETS):
            swatch = QPushButton()
            swatch.setFixedSize(34, 34)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            swatch.setToolTip(f"#{hex_color}")
            swatch.setStyleSheet(
                f"background-color: #{hex_color}; border: 1px solid #343a46;"
                "border-radius: 8px; min-width: 34px; max-width: 34px;"
                "min-height: 34px; max-height: 34px; padding: 0px;"
            )
            swatch.clicked.connect(lambda _=False, hx=hex_color: self.apply_color(hx))
            grid.addWidget(swatch, 1 + i // 6, i % 6)

        custom_btn = QPushButton(t("lighting.custom"))
        custom_btn.clicked.connect(self._pick_custom)
        grid.addWidget(custom_btn, 1, 6)

        grid.addWidget(QLabel(t("lighting.hex")), 1, 7)
        self.hex_edit = QLineEdit()
        self.hex_edit.setPlaceholderText("#FF8800")
        self.hex_edit.setFixedWidth(110)
        self.hex_edit.returnPressed.connect(self._apply_hex_field)
        grid.addWidget(self.hex_edit, 1, 8)
        root.addWidget(grid_frame)

        bri_row = QHBoxLayout()
        bri_label = QLabel(t("lighting.brightness"))
        bri_label.setObjectName("cardTitle")
        bri_row.addWidget(bri_label)
        bri_row.addSpacing(10)
        self.bri_buttons: dict[int, QPushButton] = {}
        for value in (0, 1, 2):
            btn = QPushButton(t(BRI_KEYS[value]))
            btn.setCheckable(True)
            btn.setObjectName("brightnessChip")
            btn.clicked.connect(lambda _=False, v=value: self.apply_brightness(v))
            self.bri_buttons[value] = btn
            bri_row.addWidget(btn)
        bri_row.addStretch()
        self.power_btn = QPushButton()
        self.power_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.power_btn.clicked.connect(self.toggle_lights)
        bri_row.addWidget(self.power_btn)
        root.addLayout(bri_row)

        # ── effects ──────────────────────────────────────────
        self.effect_buttons: dict[int, QPushButton] = {}
        eff_label = QLabel(t("lighting.effects"))
        eff_label.setObjectName("cardTitle")
        eff_row = QHBoxLayout()
        eff_row.addWidget(eff_label)
        eff_row.addSpacing(10)
        for code in sorted(EFFECTS):
            btn = QPushButton(t(EFFECT_KEYS[code]))
            btn.setCheckable(True)
            btn.setObjectName("brightnessChip")
            btn.clicked.connect(lambda _=False, c=code: self.apply_effect(c))
            self.effect_buttons[code] = btn
            eff_row.addWidget(btn)
        eff_row.addStretch()
        root.addLayout(eff_row)

        # ── corner leds ──────────────────────────────────────
        self.corner_frame: QFrame | None = None
        if self.led.has_corner:
            root.addWidget(self._build_corner_card())

        root.addStretch()

        self.sync_from_backend()

    def _build_corner_card(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        box = QVBoxLayout(frame)
        box.setContentsMargins(16, 16, 16, 16)
        box.setSpacing(12)

        title = QLabel(t("corner.title"))
        title.setObjectName("cardTitle")
        box.addWidget(title)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        for hex_color in PRESETS:
            swatch = QPushButton()
            swatch.setFixedSize(24, 24)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            swatch.setToolTip(f"#{hex_color}")
            swatch.setStyleSheet(
                f"background-color: #{hex_color}; border: 1px solid #343a46;"
                "border-radius: 6px; min-width: 24px; max-width: 24px;"
                "min-height: 24px; max-height: 24px; padding: 0px;"
            )
            swatch.clicked.connect(lambda _=False, hx=hex_color: self.apply_corner_color(hx))
            preset_row.addWidget(swatch)
        preset_row.addStretch()
        box.addLayout(preset_row)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)
        self.corner_swatch = QPushButton()
        self.corner_swatch.setFixedSize(34, 34)
        self.corner_swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.corner_swatch.setToolTip(t("lighting.custom"))
        self.corner_swatch.clicked.connect(self._pick_corner_custom)
        ctrl_row.addWidget(self.corner_swatch)

        ctrl_row.addWidget(QLabel(t("lighting.hex")))
        self.corner_hex = QLineEdit()
        self.corner_hex.setPlaceholderText("#FF8800")
        self.corner_hex.setFixedWidth(110)
        self.corner_hex.returnPressed.connect(self._apply_corner_hex_field)
        ctrl_row.addWidget(self.corner_hex)
        # corner leds are on/off only, so there is no brightness row here
        ctrl_row.addStretch()

        self.corner_power_btn = QPushButton()
        self.corner_power_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.corner_power_btn.clicked.connect(self.toggle_corner)
        ctrl_row.addWidget(self.corner_power_btn)
        box.addLayout(ctrl_row)

        self.corner_frame = frame
        return frame

    # ── helpers ──────────────────────────────────────────────
    def _current_color(self) -> RGBColor:
        if self.selected_zone == int(Zone.ALL):
            left = self.led.state[int(Zone.LEFT)]
            return RGBColor.from_hex(left[1])
        return RGBColor.from_hex(self.led.state[self.selected_zone][1])

    def _current_brightness(self) -> int:
        if self.selected_zone == int(Zone.ALL):
            return self.led.state[int(Zone.LEFT)][0]
        return self.led.state[self.selected_zone][0]

    def select_zone(self, zone_code: int) -> None:
        self.selected_zone = zone_code
        for code, btn in self.zone_buttons.items():
            btn.setChecked(code == zone_code)
        self.preview.set_selected(zone_code)
        self._sync_controls()

    def _on_preview_click(self, zone: Zone) -> None:
        zone_code = int(Zone.ALL) if self.selected_zone == int(zone) else int(zone)
        self.select_zone(zone_code)

    def _refresh_preview(self) -> None:
        colors = {
            code: (values[1], values[0])
            for code, values in self.led.state.items()
        }
        self.preview.set_state(colors)

    def _sync_controls(self) -> None:
        color = self._current_color()
        bri = self._current_brightness()
        self.hex_edit.setText(f"#{color.to_hex()}")
        for value, btn in self.bri_buttons.items():
            btn.setChecked(value == bri)
        self._sync_power_btn()
        self._sync_corner()

    def _sync_corner(self) -> None:
        if self.corner_frame is None:
            return
        hex_color = self.led.state[int(Zone.CORNER)][1]
        self.corner_hex.setText(f"#{hex_color}")
        self.corner_swatch.setStyleSheet(
            f"background-color: #{hex_color}; border: 1px solid #343a46;"
            "border-radius: 8px; padding: 0px;"
        )
        if self.led.corner_on:
            self.corner_power_btn.setText(t("corner.turn_off"))
            self.corner_power_btn.setObjectName("dangerButton")
        else:
            self.corner_power_btn.setText(t("corner.turn_on"))
            self.corner_power_btn.setObjectName("accentButton")
        self.corner_power_btn.style().unpolish(self.corner_power_btn)
        self.corner_power_btn.style().polish(self.corner_power_btn)

    def _sync_power_btn(self) -> None:
        if self.led.lights_on:
            self.power_btn.setText(t("lighting.turn_off"))
            self.power_btn.setObjectName("dangerButton")
        else:
            self.power_btn.setText(t("lighting.turn_on"))
            self.power_btn.setObjectName("accentButton")
        self.power_btn.style().unpolish(self.power_btn)
        self.power_btn.style().polish(self.power_btn)

    def _sync_effects(self) -> None:
        if not self.effect_buttons:
            return
        current = self.led.get_effect()
        for code, btn in self.effect_buttons.items():
            btn.setChecked(code == current)

    def sync_from_backend(self) -> None:
        self._refresh_preview()
        self.select_zone(self.selected_zone)
        self._sync_effects()

    # ── actions ──────────────────────────────────────────────
    def apply_color(self, hex_color: str) -> None:
        try:
            color = RGBColor.from_hex(hex_color)
        except ValueError as exc:
            self.set_status("✖ " + t("status.invalid_color", error=str(exc)), error=True)
            return
        try:
            if self.selected_zone == int(Zone.ALL):
                self.led.apply_all(color)
            else:
                self.led.apply_zone(Zone(self.selected_zone), color)
        except Exception as exc:  # noqa: BLE001
            self.set_status("✖ " + t("status.apply_failed", error=str(exc)), error=True)
            return
        self._after_apply(
            t("status.applied", zone=t(ZONE_KEYS[self.selected_zone]), color=color.to_hex())
        )

    def _apply_hex_field(self) -> None:
        text = self.hex_edit.text().strip().lstrip("#").upper()
        if len(text) == 3:
            text = "".join(c * 2 for c in text)
        self.apply_color(text)

    def _pick_custom(self) -> None:
        initial = QColor(f"#{self._current_color().to_hex()}")
        chosen = QColorDialog.getColor(initial, self, t("lighting.custom"))
        if chosen.isValid():
            self.apply_color(chosen.name()[1:].upper())

    def apply_brightness(self, value: int) -> None:
        try:
            self.led.set_brightness(value)
        except Exception as exc:  # noqa: BLE001
            self.set_status("✖ " + t("status.brightness_failed", error=str(exc)), error=True)
            return
        self._after_apply(t("status.brightness", value=t(BRI_KEYS[value])))

    def toggle_lights(self) -> None:
        try:
            if self.led.lights_on:
                self.led.turn_off()
                message = t("status.lights_off")
            else:
                self.led.turn_on()
                message = t("status.lights_on")
        except Exception as exc:  # noqa: BLE001
            self.set_status("✖ " + t("status.toggle_failed", error=str(exc)), error=True)
            return
        self._after_apply(message)

    def apply_effect(self, code: int) -> None:
        try:
            self.led.set_effect(code)
        except Exception as exc:  # noqa: BLE001
            self.set_status("✖ " + t("status.effect_failed", error=str(exc)), error=True)
            return
        self.pm.set_last_state(self.led.snapshot(), effect=code)
        self._sync_effects()
        self.set_status("✔ " + t("status.effect", name=t(EFFECT_KEYS[code])))

    def apply_corner_color(self, hex_color: str) -> None:
        try:
            color = RGBColor.from_hex(hex_color)
        except ValueError as exc:
            self.set_status("✖ " + t("status.invalid_color", error=str(exc)), error=True)
            return
        # picking a colour while the corner leds are off switches them on
        try:
            self.led.apply_zone(Zone.CORNER, color, int(Brightness.MAX))
        except Exception as exc:  # noqa: BLE001
            self.set_status("✖ " + t("status.apply_failed", error=str(exc)), error=True)
            return
        self._after_apply(t("status.applied", zone=t("zone.corner"), color=color.to_hex()))

    def _apply_corner_hex_field(self) -> None:
        text = self.corner_hex.text().strip().lstrip("#").upper()
        if len(text) == 3:
            text = "".join(c * 2 for c in text)
        self.apply_corner_color(text)

    def _pick_corner_custom(self) -> None:
        initial = QColor(f"#{self.led.state[int(Zone.CORNER)][1]}")
        chosen = QColorDialog.getColor(initial, self, t("corner.title"))
        if chosen.isValid():
            self.apply_corner_color(chosen.name()[1:].upper())

    def toggle_corner(self) -> None:
        turn_on = not self.led.corner_on
        try:
            self.led.set_corner(turn_on)
        except Exception as exc:  # noqa: BLE001
            self.set_status("✖ " + t("status.toggle_failed", error=str(exc)), error=True)
            return
        self._after_apply(t("status.corner_on" if turn_on else "status.corner_off"))

    def _after_apply(self, message: str) -> None:
        self._refresh_preview()
        self._sync_controls()
        snapshot = self.led.snapshot()
        self.pm.set_last_state(snapshot)
        self.set_status(f"✔ {message}")
