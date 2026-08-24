"""Performance backend: fan speeds and power plan.

Power plan is written through whichever interface the active driver provides:
- ``pwm1`` in the casper_wmi hwmon device (casper-wmi 1.1.0 fork)
- ``/sys/firmware/acpi/platform_profile`` (kernel platform_profile API)
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from ..core.config import HELPER_SCRIPT_PATH

logger = logging.getLogger(__name__)

PLATFORM_PROFILE_PATH = Path("/sys/firmware/acpi/platform_profile")

POWER_PLANS: dict[int, dict[str, str]] = {
    1: {"name": "Yüksek Güç", "desc": "Maksimum performans"},
    2: {"name": "Oyun", "desc": "Oyun modu profili"},
    3: {"name": "Metin Modu", "desc": "Dengeli ofis kullanımı"},
    4: {"name": "Düşük Güç", "desc": "Sessiz ve verimli"},
}

# plan kodu -> platform_profile değeri
PROFILE_NAMES: dict[int, str] = {
    1: "performance",
    2: "balanced-performance",
    3: "balanced",
    4: "low-power",
}
PROFILE_CODES: dict[str, int] = {v: k for k, v in PROFILE_NAMES.items()}


class PowerError(RuntimeError):
    pass


def _find_hwmon() -> Path | None:
    base = Path("/sys/class/hwmon")
    for candidate in base.iterdir():
        try:
            if (candidate / "name").read_text().strip() == "casper_wmi":
                return candidate
        except OSError:
            continue
    return None


class PowerBackend:
    """Fan speed monitoring and power plan switching."""

    def __init__(self) -> None:
        self.hwmon: Path | None = _find_hwmon()

    @property
    def available(self) -> bool:
        return self.hwmon is not None and (self.hwmon / "fan1_input").exists()

    @property
    def plan_mode(self) -> str | None:
        if self.hwmon is not None and (self.hwmon / "pwm1").exists():
            return "pwm"
        if PLATFORM_PROFILE_PATH.exists():
            return "profile"
        return None

    # ── fans ─────────────────────────────────────────────────
    def fans(self) -> dict[str, int | None]:
        """Return {'cpu': rpm|None, 'gpu': rpm|None}."""
        out = {"cpu": None, "gpu": None}
        if not self.available:
            return out
        for key, fname in (("cpu", "fan1_input"), ("gpu", "fan2_input")):
            try:
                out[key] = int((self.hwmon / fname).read_text().strip())
            except (OSError, ValueError):
                out[key] = None
        return out

    # ── power plan ───────────────────────────────────────────
    def get_plan(self) -> int | None:
        if self.plan_mode == "pwm":
            try:
                value = int((self.hwmon / "pwm1").read_text().strip())
            except (OSError, ValueError):
                return None
            return value if value in POWER_PLANS else None
        if self.plan_mode == "profile":
            try:
                name = PLATFORM_PROFILE_PATH.read_text().strip()
            except OSError:
                return None
            return PROFILE_CODES.get(name)
        return None

    def set_plan(self, plan: int) -> None:
        if plan not in POWER_PLANS:
            raise PowerError(f"Geçersiz güç planı: {plan}")
        if self.plan_mode == "pwm":
            self._set_pwm(plan)
        elif self.plan_mode == "profile":
            self._set_profile(PROFILE_NAMES[plan])
        else:
            raise PowerError("Güç planı arayüzü bulunamadı")

    def _set_pwm(self, plan: int) -> None:
        try:
            (self.hwmon / "pwm1").write_text(str(plan))
        except PermissionError:
            logger.info("Doğrudan yazma reddedildi, polkit kullanılıyor")
            self._helper_run("pwm", str(plan))
        except OSError as exc:
            raise PowerError(f"Güç planı yazılamadı: {exc}") from exc

    def _set_profile(self, profile: str) -> None:
        try:
            PLATFORM_PROFILE_PATH.write_text(profile)
        except PermissionError:
            logger.info("Doğrudan yazma reddedildi, polkit kullanılıyor")
            self._helper_run("profile", profile)
        except OSError as exc:
            raise PowerError(f"Güç planı yazılamadı: {exc}") from exc

    def _helper_run(self, kind: str, value: str) -> None:
        import os

        if not os.path.exists(HELPER_SCRIPT_PATH):
            raise PowerError(
                f"Yazma izni yok ve yardımcı betik bulunamadı: {HELPER_SCRIPT_PATH}"
            )
        pkexec = shutil.which("pkexec")
        if pkexec is None:
            raise PowerError("pkexec bulunamadı")
        result = subprocess.run(
            [pkexec, HELPER_SCRIPT_PATH, kind, value],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise PowerError(f"Yardımcı betik başarısız: {result.stderr.strip()}")
