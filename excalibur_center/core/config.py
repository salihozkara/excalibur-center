"""Constants and value types shared across the application.

Zone codes and brightness levels mirror the casper-wmi kernel module:
https://github.com/Mustafa-eksi/casper-wmi
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Final

LED_CONTROL_PATH: Final[str] = "/sys/class/leds/casper::kbd_backlight/led_control"

HELPER_SCRIPT_PATH: Final[str] = "/usr/lib/excalibur-center/priv-write-helper"

POLKIT_ACTION: Final[str] = "org.excalibur.center.priv-write"

APP_CONFIG_DIR: Final[Path] = Path.home() / ".config" / "excalibur-center"


class Zone(IntEnum):
    """Keyboard LED zones as defined in the casper-wmi kernel module."""

    LEFT = 0x03
    CENTER = 0x04
    RIGHT = 0x05
    ALL = 0x06


ZONE_LABELS: Final[dict[str, Zone]] = {
    "left": Zone.LEFT,
    "orta": Zone.CENTER,
    "center": Zone.CENTER,
    "right": Zone.RIGHT,
    "sag": Zone.RIGHT,
    "all": Zone.ALL,
    "tumu": Zone.ALL,
}

ZONE_NAMES: Final[dict[int, str]] = {
    Zone.LEFT: "Sol",
    Zone.CENTER: "Orta",
    Zone.RIGHT: "Sağ",
    Zone.ALL: "Tümü",
}

KEYBOARD_ZONES: Final[tuple[Zone, ...]] = (Zone.LEFT, Zone.CENTER, Zone.RIGHT)

# multicolor LED arayüzü (platform_profile kullanan sürücüler)
MCLED_BASE: Final[str] = "/sys/class/leds"
MCLED_ZONE_NAMES: Final[dict[int, str]] = {
    int(Zone.LEFT): "left",
    int(Zone.CENTER): "middle",
    int(Zone.RIGHT): "right",
}


class Brightness(IntEnum):
    """Brightness levels supported by the hardware (2-bit field)."""

    OFF = 0x00
    MID = 0x01
    MAX = 0x02


BRIGHTNESS_LABELS: Final[dict[int, str]] = {
    Brightness.OFF: "Kapalı",
    Brightness.MID: "Düşük",
    Brightness.MAX: "Yüksek",
}


HEX_COLOR_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9A-Fa-f]{6}$")

COMMAND_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9A-Fa-f]{9}$")


@dataclass(frozen=True, slots=True)
class RGBColor:
    """Immutable RGB color with validation."""

    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for channel, name in ((self.r, "R"), (self.g, "G"), (self.b, "B")):
            if not isinstance(channel, int) or not (0 <= channel <= 255):
                raise ValueError(f"{name} değeri 0-255 arası olmalı: {channel!r}")

    def to_hex(self) -> str:
        return f"{self.r:02X}{self.g:02X}{self.b:02X}"

    @classmethod
    def from_hex(cls, hex_str: str) -> "RGBColor":
        hex_str = hex_str.strip().lstrip("#")
        if not HEX_COLOR_RE.match(hex_str):
            raise ValueError(f"Geçersiz renk kodu: {hex_str!r}")
        return cls(
            r=int(hex_str[0:2], 16),
            g=int(hex_str[2:4], 16),
            b=int(hex_str[4:6], 16),
        )

    def as_qcolor_args(self) -> tuple[int, int, int]:
        return self.r, self.g, self.b


def validate_led_path(path: str) -> str:
    """Ensure *path* resolves inside sysfs and exists."""
    import os

    resolved = os.path.realpath(path)
    if not resolved.startswith("/sys/"):
        raise PermissionError(f"LED yolu /sys/ dışına işaret ediyor: {resolved}")
    if not os.path.exists(resolved):
        raise FileNotFoundError(f"LED kontrol dosyası bulunamadı: {resolved}")
    return resolved


def build_command(
    zone: Zone, brightness: int, color: RGBColor, mode: int = 0x00
) -> str:
    """Build the raw command written to led_control.

    Layout matches the driver's kstrtou64(base16) parsing:
    high byte = zone id, then u32 data = (led_mode | brightness) << 24 | RRGGBB.
    ``mode`` carries the effect nibble (0x10 normal .. 0x70 ambilight).
    """
    data_byte = (mode | brightness) & 0xFF
    cmd = f"{int(zone):X}{data_byte:02X}{color.to_hex()}"
    if not COMMAND_RE.match(cmd):
        raise ValueError(f"Komut doğrulanamadı: {cmd!r}")
    return cmd
