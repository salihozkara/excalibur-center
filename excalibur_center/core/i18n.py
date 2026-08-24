"""Lightweight i18n: English (default) and Turkish.

Language resolution order:
  1. settings.json  (~/.config/excalibur-center/settings.json)
  2. LANG environment variable (tr* -> "tr")
  3. fallback: "en"
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "excalibur-center"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

SUPPORTED = ("en", "tr")

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # shell / navigation
        "app.subtitle": "Unofficial Control Center for Casper Excalibur laptops",
        "nav.lighting": "Lighting",
        "nav.performance": "Performance",
        "nav.profiles": "Profiles",
        "lang.label": "Language (restart to apply)",
        # lighting page
        "lighting.title": "Lighting",
        "lighting.desc": "Pick a zone on the live keyboard preview and apply colour and brightness instantly.",
        "lighting.presets": "Presets",
        "lighting.custom": "Custom colour…",
        "lighting.hex": "Hex:",
        "lighting.brightness": "Brightness",
        "lighting.effects": "Effects",
        "lighting.turn_off": "Turn lights off",
        "lighting.turn_on": "Turn lights on",
        "effect.normal": "Normal",
        "effect.blink": "Blink",
        "effect.fade": "Fade",
        "effect.heartbeat": "Heartbeat",
        "effect.repeat": "Repeat",
        "effect.random": "Random",
        "effect.ambilight": "Ambilight",
        "zone.left": "Left",
        "zone.center": "Center",
        "zone.right": "Right",
        "zone.all": "All",
        "bri.off": "Off",
        "bri.mid": "Low",
        "bri.max": "High",
        # performance page
        "perf.title": "Performance",
        "perf.desc": "Choose a power plan and monitor fan speeds live.",
        "perf.plans": "Power plan",
        "perf.fans": "Fan speeds",
        "perf.refresh": "Refresh",
        "perf.unavailable": "casper_wmi hwmon interface not found — fans and power plan disabled.",
        "fan.cpu": "CPU Fan",
        "fan.gpu": "GPU Fan",
        "plan.1.name": "High Power",
        "plan.1.desc": "Maximum performance",
        "plan.2.name": "Gaming",
        "plan.2.desc": "Gaming profile",
        "plan.3.name": "Text Mode",
        "plan.3.desc": "Balanced office use",
        "plan.4.name": "Low Power",
        "plan.4.desc": "Quiet and efficient",
        # profiles page
        "profiles.title": "Profiles",
        "profiles.desc": "Save your favourite combinations; the last state is restored at boot.",
        "profiles.save_current": "Save current state…",
        "profiles.apply": "Apply",
        "profiles.delete": "Delete",
        "profiles.save_title": "Save profile",
        "profiles.save_label": "Profile name:",
        "profiles.default_name": "Gaming",
        "profiles.invalid_name_title": "Invalid name",
        "profiles.error_title": "Error",
        "profiles.confirm_title": "Delete profile",
        "profiles.confirm_text": "Delete profile '{name}'?",
        "profiles.last_suffix": "  •  last",
        # statuses
        "status.applied": "{zone} → #{color}",
        "status.brightness": "Brightness → {value}",
        "status.effect": "Effect → {name}",
        "status.effect_failed": "Could not set effect: {error}",
        "status.lights_off": "Lights turned off",
        "status.lights_on": "Lights turned on",
        "status.profile_saved": "Profile saved: {name}",
        "status.profile_applied": "Profile applied: {name}",
        "status.profile_deleted": "Profile deleted: {name}",
        "status.plan": "Power plan: {name}",
        "status.select_first": "Select a profile first.",
        "status.apply_failed": "Could not apply: {error}",
        "status.brightness_failed": "Could not set brightness: {error}",
        "status.toggle_failed": "Operation failed: {error}",
        "status.plan_failed": "Could not apply power plan: {error}",
        "status.invalid_color": "{error}",
        # unsupported dialog
        "unsupported.title": "<h2>No supported hardware found</h2>",
        "unsupported.body": (
            "<p>Neither LED interface (raw or multicolor) is present.</p>"
            "<p>Make sure a casper-wmi kernel module is installed and loaded:<br>"
            "<code>sudo modprobe casper_wmi</code></p>"
        ),
        # cli --status
        "cli.no_state": "No saved state.",
        "cli.lights": "Lights:",
        "cli.last_profile": "Last profile: {name}",
        "cli.plan": "Power plan: {code} ({name})",
        "cli.plan_unknown": "Power plan: unreadable",
        "cli.fans": "Fans: CPU={cpu} RPM  GPU={gpu} RPM",
        "cli.restored": "State restored",
        "cli.restored_profile": "State restored (profile: {name})",
        "cli.nothing_to_restore": "No state to restore",
        "cli.led_not_ready": "LED interface not ready: {error}",
        "cli.applied": "Applied: {zone} → #{color}",
        "cli.invalid_zone": "Invalid zone: {zone} (left/center/right/all)",
        "cli.invalid_plan": "Invalid plan: {plan} (highpower / gaming / textmode / lowpower or 1-4)",
        "cli.plan_done": "Power plan: {code}",
    },
    "tr": {
        "app.subtitle": "Casper Excalibur için resmi olmayan kontrol merkezi",
        "nav.lighting": "Aydınlatma",
        "nav.performance": "Performans",
        "nav.profiles": "Profiller",
        "lang.label": "Dil (uygulamak için yeniden başlat)",
        "lighting.title": "Aydınlatma",
        "lighting.desc": "Klavye önizlemesinden bölge seç, renk ve parlaklığı canlı uygula.",
        "lighting.presets": "Hazır renkler",
        "lighting.custom": "Özel renk…",
        "lighting.hex": "Hex:",
        "lighting.brightness": "Parlaklık",
        "lighting.effects": "Efektler",
        "lighting.turn_off": "Işıkları kapat",
        "lighting.turn_on": "Işıkları aç",
        "effect.normal": "Normal",
        "effect.blink": "Yanıp Sönme",
        "effect.fade": "Solma",
        "effect.heartbeat": "Kalp Atışı",
        "effect.repeat": "Tekrar",
        "effect.random": "Rastgele",
        "effect.ambilight": "Ambilight",
        "zone.left": "Sol",
        "zone.center": "Orta",
        "zone.right": "Sağ",
        "zone.all": "Tümü",
        "bri.off": "Kapalı",
        "bri.mid": "Düşük",
        "bri.max": "Yüksek",
        "perf.title": "Performans",
        "perf.desc": "Güç planını seç, fan hızlarını canlı izle.",
        "perf.plans": "Güç planı",
        "perf.fans": "Fan hızları",
        "perf.refresh": "Yenile",
        "perf.unavailable": "casper_wmi hwmon arayüzü bulunamadı — fan ve güç planı devre dışı.",
        "fan.cpu": "CPU Fan",
        "fan.gpu": "GPU Fan",
        "plan.1.name": "Yüksek Güç",
        "plan.1.desc": "Maksimum performans",
        "plan.2.name": "Oyun",
        "plan.2.desc": "Oyun modu profili",
        "plan.3.name": "Metin Modu",
        "plan.3.desc": "Dengeli ofis kullanımı",
        "plan.4.name": "Düşük Güç",
        "plan.4.desc": "Sessiz ve verimli",
        "profiles.title": "Profiller",
        "profiles.desc": "Kombinasyonlarını kaydet; açılışta son durum geri yüklenir.",
        "profiles.save_current": "Mevcut durumu kaydet…",
        "profiles.apply": "Uygula",
        "profiles.delete": "Sil",
        "profiles.save_title": "Profili kaydet",
        "profiles.save_label": "Profil adı:",
        "profiles.default_name": "Oyun",
        "profiles.invalid_name_title": "Geçersiz ad",
        "profiles.error_title": "Hata",
        "profiles.confirm_title": "Profili sil",
        "profiles.confirm_text": "'{name}' profili silinsin mi?",
        "profiles.last_suffix": "  •  son",
        "status.applied": "{zone} → #{color}",
        "status.brightness": "Parlaklık → {value}",
        "status.effect": "Efekt → {name}",
        "status.effect_failed": "Efekt ayarlanamadı: {error}",
        "status.lights_off": "Işıklar kapatıldı",
        "status.lights_on": "Işıklar açıldı",
        "status.profile_saved": "Profil kaydedildi: {name}",
        "status.profile_applied": "Profil uygulandı: {name}",
        "status.profile_deleted": "Profil silindi: {name}",
        "status.plan": "Güç planı: {name}",
        "status.select_first": "Önce bir profil seç.",
        "status.apply_failed": "Uygulanamadı: {error}",
        "status.brightness_failed": "Parlaklık ayarlanamadı: {error}",
        "status.toggle_failed": "İşlem başarısız: {error}",
        "status.plan_failed": "Güç planı uygulanamadı: {error}",
        "status.invalid_color": "{error}",
        "unsupported.title": "<h2>Desteklenen donanım bulunamadı</h2>",
        "unsupported.body": (
            "<p>Hiçbir LED arayüzü (raw veya multicolor) bulunamadı.</p>"
            "<p>Bir casper-wmi çekirdek modülünün kurulu ve yüklü olduğundan emin ol:<br>"
            "<code>sudo modprobe casper_wmi</code></p>"
        ),
        "cli.no_state": "Kayıtlı durum yok.",
        "cli.lights": "Işıklar:",
        "cli.last_profile": "Son profil: {name}",
        "cli.plan": "Güç planı: {code} ({name})",
        "cli.plan_unknown": "Güç planı: okunamadı",
        "cli.fans": "Fanlar: CPU={cpu} RPM  GPU={gpu} RPM",
        "cli.restored": "Durum geri yüklendi",
        "cli.restored_profile": "Durum geri yüklendi (profil: {name})",
        "cli.nothing_to_restore": "Geri yüklenecek durum yok",
        "cli.led_not_ready": "LED arayüzü hazır değil: {error}",
        "cli.applied": "Uygulandı: {zone} → #{color}",
        "cli.invalid_zone": "Geçersiz bölge: {zone} (left/center/right/all)",
        "cli.invalid_plan": "Geçersiz plan: {plan} (yuksekguc / oyun / textmode / dusukguc veya 1-4)",
        "cli.plan_done": "Güç planı: {code}",
    },
}

_LOCK = threading.Lock()
_LANGUAGE: str | None = None


def _detect() -> str:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        lang = str(data.get("language", "")).lower()
        if lang in SUPPORTED:
            return lang
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    env = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    if env.lower().startswith("tr"):
        return "tr"
    return "en"


def get_language() -> str:
    global _LANGUAGE
    with _LOCK:
        if _LANGUAGE is None:
            _LANGUAGE = _detect()
        return _LANGUAGE


def set_language(lang: str) -> None:
    """Persist the language choice; takes effect on next start."""
    if lang not in SUPPORTED:
        raise ValueError(f"Unsupported language: {lang!r}")
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps({"language": lang}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    global _LANGUAGE
    with _LOCK:
        _LANGUAGE = lang


def t(key: str, **kwargs) -> str:
    table = _STRINGS[get_language()]
    template = table.get(key) or _STRINGS["en"].get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
