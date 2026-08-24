"""LED backend with dual driver-interface support.

Two casper-wmi driver generations are supported:

- ``raw``   : classic interface, single ``led_control`` sysfs file taking
              hex commands (our casper-wmi 1.1.0 fork, upstream 1.0).
- ``mcled`` : multicolor LED class per zone
              (``casper:rgb:kbd_zoned_backlight-*``, multicolor interface).

The backend auto-detects whichever interface is present.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from ..core.config import (
    Brightness,
    KEYBOARD_ZONES,
    LED_CONTROL_PATH,
    MCLED_ZONE_NAMES,
    MCLED_BASE,
    RGBColor,
    Zone,
    build_command,
    validate_led_path,
)

logger = logging.getLogger(__name__)


class LEDError(RuntimeError):
    pass


# effect attribute values of the multicolor interface
EFFECTS: dict[int, str] = {
    1: "normal",
    2: "blink",
    3: "fade",
    4: "heartbeat",
    5: "repeat",
    6: "random",
    7: "ambilight",
}
EFFECT_CODES: dict[str, int] = {v: k for k, v in EFFECTS.items()}

# raw arayüzde efekt nibble'ları (veri byte'ının üst 4 biti)
EFFECT_MODES: dict[int, int] = {
    1: 0x10,  # normal
    2: 0x20,  # blink
    3: 0x30,  # fade
    4: 0x40,  # heartbeat
    5: 0x50,  # repeat
    6: 0x60,  # random
    7: 0x70,  # ambilight
}


def _mcled_zone_path(zone: Zone) -> Path:
    return Path(MCLED_BASE) / f"casper:rgb:kbd_zoned_backlight-{MCLED_ZONE_NAMES[int(zone)]}"


class LEDBackend:
    """Keeps an in-memory snapshot of zone states and applies changes."""

    def __init__(self, load_state: bool = True) -> None:
        self._lock = threading.Lock()
        # zone code -> [brightness, "RRGGBB"]
        self.state: dict[int, list] = {
            int(z): [int(Brightness.MAX), "FFFFFF"] for z in KEYBOARD_ZONES
        }
        self._last_on_brightness: int = int(Brightness.MAX)
        self.effect: int = 1

        if Path(LED_CONTROL_PATH).exists():
            self.mode = "raw"
            self.path = validate_led_path(LED_CONTROL_PATH)
        elif Path(MCLED_BASE).is_dir() and _mcled_zone_path(Zone.LEFT).exists():
            self.mode = "mcled"
        else:
            raise FileNotFoundError(
                "Desteklenen LED arayüzü bulunamadı (led_control veya multicolor LED)"
            )

        if load_state:
            self._load_persisted_state()

    def _load_persisted_state(self) -> None:
        """Seed in-memory zone colors from the last saved state so that a
        single-zone write never resets the other zones to defaults."""
        mapping = {"left": Zone.LEFT, "center": Zone.CENTER, "right": Zone.RIGHT}
        try:
            from ..core.profiles import ProfileManager

            snap, _ = ProfileManager().get_last_state()
        except Exception:  # noqa: BLE001
            return
        if not isinstance(snap, dict):
            return
        for key, values in snap.items():
            zone = mapping.get(key)
            if zone is None or int(zone) not in self.state:
                continue
            try:
                bri = int(values["brightness"])
                hex_color = str(values["color"])
                RGBColor.from_hex(hex_color)
            except (KeyError, ValueError, TypeError):
                continue
            if bri in (int(Brightness.OFF), int(Brightness.MID), int(Brightness.MAX)):
                self.state[int(zone)] = [bri, hex_color.upper()]
        try:
            effect = pm.get_last_effect()
        except Exception:  # noqa: BLE001
            effect = None
        if effect in EFFECTS:
            self.effect = effect

    @property
    def lights_on(self) -> bool:
        return any(
            self.state[int(z)][0] != int(Brightness.OFF) for z in KEYBOARD_ZONES
        )

    # ── low level: raw interface ─────────────────────────────
    def _direct_write(self, command: str) -> None:
        with open(self.path, "w", encoding="ascii") as fp:
            fp.write(command)

    def _helper_write(self, command: str) -> None:
        import os
        import shutil

        from ..core.config import HELPER_SCRIPT_PATH

        if not os.path.exists(HELPER_SCRIPT_PATH):
            raise LEDError(
                f"Yazma izni yok ve yardımcı betik bulunamadı: {HELPER_SCRIPT_PATH}"
            )
        pkexec = shutil.which("pkexec")
        if pkexec is None:
            raise LEDError("pkexec bulunamadı")
        result = subprocess.run(
            [pkexec, HELPER_SCRIPT_PATH, "led", command],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise LEDError(f"Yardımcı betik başarısız: {result.stderr.strip()}")

    def _write_raw(self, command: str) -> None:
        with self._lock:
            try:
                self._direct_write(command)
            except PermissionError:
                logger.info("Doğrudan yazma reddedildi, polkit kullanılıyor")
                self._helper_write(command)

    # ── low level: multicolor interface ──────────────────────
    def _write_mcled(self, zone: Zone, color: RGBColor, bri: int) -> None:
        base = _mcled_zone_path(zone)
        try:
            (base / "multi_intensity").write_text(f"{color.r} {color.g} {color.b}")
            (base / "brightness").write_text(str(bri))
        except PermissionError:
            logger.info("Doğrudan yazma reddedildi, polkit kullanılıyor")
            self._helper_write_mcled(MCLED_ZONE_NAMES[int(zone)], color, bri)

    def _helper_write_mcled(self, zone_name: str, color: RGBColor, bri: int) -> None:
        import os
        import shutil

        from ..core.config import HELPER_SCRIPT_PATH

        if not os.path.exists(HELPER_SCRIPT_PATH):
            raise LEDError(
                f"Yazma izni yok ve yardımcı betik bulunamadı: {HELPER_SCRIPT_PATH}"
            )
        pkexec = shutil.which("pkexec")
        if pkexec is None:
            raise LEDError("pkexec bulunamadı")
        result = subprocess.run(
            [pkexec, HELPER_SCRIPT_PATH, "ledmc", f"{zone_name}:{color.to_hex()}:{bri}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise LEDError(f"Yardımcı betik başarısız: {result.stderr.strip()}")

    # ── public API ───────────────────────────────────────────
    def _effective_brightness(self, zone: Zone, brightness: int | None) -> int:
        if brightness is not None:
            return int(brightness)
        entry = self.state.get(int(zone))
        if entry is not None:
            return entry[0]
        return self.state[int(Zone.LEFT)][0]

    def apply_zone(
        self, zone: Zone, color: RGBColor, brightness: int | None = None
    ) -> None:
        if self.mode == "mcled" and zone == Zone.ALL:
            for z in KEYBOARD_ZONES:
                self.apply_zone(z, color, brightness)
            return
        bri = self._effective_brightness(zone, brightness)
        if bri not in (Brightness.OFF, Brightness.MID, Brightness.MAX):
            raise LEDError(f"Geçersiz parlaklık: {bri}")
        if self.mode == "raw":
            cmd = build_command(
                zone, bri, color, EFFECT_MODES.get(self.effect, 0x00)
            )
            self._write_raw(cmd)
        else:
            self._write_mcled(zone, color, bri)
        if zone == Zone.ALL:
            for z in KEYBOARD_ZONES:
                self.state[int(z)] = [bri, color.to_hex()]
        else:
            self.state[int(zone)] = [bri, color.to_hex()]
        if bri != int(Brightness.OFF):
            self._last_on_brightness = bri

    def apply_all(self, color: RGBColor, brightness: int | None = None) -> None:
        if self.mode == "raw":
            self.apply_zone(Zone.ALL, color, brightness)
            return
        for zone in KEYBOARD_ZONES:
            self.apply_zone(zone, color, brightness)

    def set_brightness(self, brightness: int, zones: tuple[Zone, ...] = KEYBOARD_ZONES) -> None:
        """Change brightness while keeping the current per-zone colors."""
        for zone in zones:
            hex_color = self.state[int(zone)][1]
            self.apply_zone(zone, RGBColor.from_hex(hex_color), brightness)

    def turn_off(self) -> None:
        """Turn every zone off while remembering its colour for turn_on()."""
        for zone in KEYBOARD_ZONES:
            hex_color = self.state[int(zone)][1]
            if self.mode == "raw":
                cmd = build_command(zone, Brightness.OFF, RGBColor.from_hex(hex_color))
                self._write_raw(cmd)
            else:
                self._write_mcled(zone, RGBColor.from_hex(hex_color), int(Brightness.OFF))
            self.state[int(zone)] = [int(Brightness.OFF), hex_color]

    def turn_on(self, brightness: int | None = None) -> None:
        """Restore the remembered colours with the last used brightness."""
        bri = (
            int(brightness)
            if brightness is not None
            else self._last_on_brightness
        )
        for zone in KEYBOARD_ZONES:
            hex_color = self.state[int(zone)][1]
            self.apply_zone(zone, RGBColor.from_hex(hex_color), bri)

    # ── effects ──────────────────────────────────────────────
    def get_effect(self) -> int | None:
        if self.mode == "mcled":
            try:
                value = int(
                    (_mcled_zone_path(Zone.LEFT) / "effect").read_text().strip()
                )
            except (OSError, ValueError):
                return None
            return value if value in EFFECTS else None
        # raw arayüzde okuma yok; bellek içi durumu döndür
        return self.effect

    def set_effect(self, code: int) -> None:
        if code not in EFFECTS:
            raise LEDError(f"Geçersiz efekt: {code}")
        if self.mode == "mcled":
            for zone in KEYBOARD_ZONES:
                try:
                    (_mcled_zone_path(zone) / "effect").write_text(str(code))
                except PermissionError as exc:
                    raise LEDError(
                        "Efekt yazma izni yok; 'excalibur' grubuna üye olmalısın."
                    ) from exc
        else:
            # raw: mevcut renk/parlaklıkla, mod nibble'ını taşıyan komut yaz
            for zone in KEYBOARD_ZONES:
                bri, hex_color = self.state[int(zone)]
                cmd = build_command(
                    zone, bri, RGBColor.from_hex(hex_color), EFFECT_MODES[code]
                )
                self._write_raw(cmd)
        self.effect = code

    # ── state helpers ────────────────────────────────────────
    def snapshot(self) -> dict[str, dict[str, int | str]]:
        return {
            name: {"brightness": self.state[int(code)][0], "color": self.state[int(code)][1]}
            for code, name in (
                (Zone.LEFT, "left"),
                (Zone.CENTER, "center"),
                (Zone.RIGHT, "right"),
            )
        }

    def restore_snapshot(self, snap: dict[str, dict[str, int | str]]) -> None:
        mapping = {"left": Zone.LEFT, "center": Zone.CENTER, "right": Zone.RIGHT}
        for key, values in snap.items():
            zone = mapping.get(key)
            if zone is None:
                continue
            try:
                color = RGBColor.from_hex(str(values["color"]))
                bri = int(values["brightness"])
            except (KeyError, ValueError) as exc:
                raise LEDError(f"Bozuk durum verisi ({key}): {exc}") from exc
            self.apply_zone(zone, color, bri)
