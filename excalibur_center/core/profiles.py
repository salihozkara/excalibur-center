"""Profile and last-state persistence."""

from __future__ import annotations

import json
import logging
import os
import pwd
import re
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

PROFILE_NAME_RE = re.compile(r"^[\wçğıöşüÇĞİÖŞÜ -]{1,32}$")

PROFILES_FILE = "profiles.json"
STATE_FILE = "state.json"


def find_config_dir() -> Path:
    """Config dir of the calling user; when running as root (systemd),
    locate the first human user that has a saved state."""
    if os.getuid() != 0:
        d = Path.home() / ".config" / "excalibur-center"
        d.mkdir(parents=True, exist_ok=True)
        return d
    for entry in sorted(pwd.getpwall(), key=lambda p: p.pw_uid):
        if entry.pw_uid < 1000:
            continue
        candidate = Path(entry.pw_dir) / ".config" / "excalibur-center" / STATE_FILE
        if candidate.exists():
            logger.info("Durum dosyası bulundu: %s", candidate)
            return candidate.parent
    fallback = Path("/root/.config/excalibur-center")
    # Do NOT mkdir here: under systemd ProtectHome=read-only the write would
    # fail; ProfileManager._write() creates directories on demand anyway.
    return fallback


class ProfileManager:
    def __init__(self, config_dir: Path | None = None) -> None:
        self.dir = config_dir or find_config_dir()
        self.profiles_path = self.dir / PROFILES_FILE
        self.state_path = self.dir / STATE_FILE
        self._lock = threading.Lock()

    # ── low level ────────────────────────────────────────────
    def _read(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Okunamadı (%s): %s", path.name, exc)
            return {}

    def _write(self, path: Path, data: dict) -> None:
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)

    # ── profiles ─────────────────────────────────────────────
    @staticmethod
    def validate_name(name: str) -> str:
        name = name.strip()
        if not PROFILE_NAME_RE.match(name):
            raise ValueError(f"Geçersiz profil adı: {name!r}")
        return name

    def save_profile(self, name: str, snapshot: dict) -> None:
        name = self.validate_name(name)
        data = self._read(self.profiles_path)
        data[name] = snapshot
        self._write(self.profiles_path, data)

    def list_profiles(self) -> list[str]:
        return sorted(self._read(self.profiles_path).keys())

    def load_profile(self, name: str) -> dict | None:
        name = self.validate_name(name)
        return self._read(self.profiles_path).get(name)

    def delete_profile(self, name: str) -> bool:
        name = self.validate_name(name)
        data = self._read(self.profiles_path)
        if name not in data:
            return False
        del data[name]
        self._write(self.profiles_path, data)
        return True

    # ── last applied state (for boot restore) ────────────────
    def get_last_state(self) -> tuple[dict | None, str | None]:
        data = self._read(self.state_path)
        snap = data.get("snapshot")
        if not isinstance(snap, dict):
            return None, None
        return snap, data.get("profile_name")

    def get_last_effect(self) -> int | None:
        data = self._read(self.state_path)
        effect = data.get("effect")
        return effect if isinstance(effect, int) else None

    def set_last_state(
        self,
        snapshot: dict,
        profile_name: str | None = None,
        effect: int | None = None,
    ) -> None:
        data: dict = {"snapshot": snapshot, "profile_name": profile_name}
        if effect is not None:
            data["effect"] = effect
        self._write(self.state_path, data)
