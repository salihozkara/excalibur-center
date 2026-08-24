"""Command line interface.

Usage:
  excalibur-center                     GUI
  excalibur-center --restore           re-apply last state (systemd hook)
  excalibur-center --status            print current state
  excalibur-center --set-led ZONE HEX [BRIGHTNESS]
                                       apply color to a zone now
  excalibur-center --set-plan NAME     set power plan
  excalibur-center --lang en|tr        set UI language
"""

from __future__ import annotations

import argparse
import logging
import sys


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


def _restore() -> int:
    from .backend.led import LEDError, LEDBackend
    from .core.i18n import t
    from .core.profiles import ProfileManager

    log = logging.getLogger(__name__)
    pm = ProfileManager()
    snapshot, profile_name = pm.get_last_state()
    if snapshot is None:
        log.info(t("cli.nothing_to_restore"))
        return 0
    try:
        led = LEDBackend()
    except (FileNotFoundError, PermissionError) as exc:
        log.warning(t("cli.led_not_ready", error=str(exc)))
        return 0
    try:
        led.restore_snapshot(snapshot)
    except LEDError as exc:
        log.error("%s: %s", t("cli.restored"), exc)
        return 1
    if profile_name:
        log.info(t("cli.restored_profile", name=profile_name))
    else:
        log.info(t("cli.restored"))
    return 0


def _status() -> int:
    from .backend.power import PowerBackend
    from .core.config import Brightness, Zone
    from .core.i18n import t
    from .core.profiles import ProfileManager

    pm = ProfileManager()
    snapshot, last_name = pm.get_last_state()
    if snapshot is None:
        print(t("cli.no_state"))
    else:
        print(t("cli.lights"))
        zone_keys = {"left": "zone.left", "center": "zone.center", "right": "zone.right"}
        bri_keys = {int(Brightness.OFF): "bri.off", int(Brightness.MID): "bri.mid",
                    int(Brightness.MAX): "bri.max"}
        for key, values in snapshot.items():
            zone_label = t(zone_keys.get(key, key))
            bri_label = t(bri_keys.get(int(values["brightness"]), "?"))
            print(f"  {zone_label:<8} #{values['color']} ({bri_label})")
        if last_name:
            print(t("cli.last_profile", name=last_name))

    power = PowerBackend()
    plan = power.get_plan()
    if plan is None:
        print(t("cli.plan_unknown"))
    else:
        print(t("cli.plan", code=plan, name=t(f"plan.{plan}.name")))
    fans = power.fans()
    cpu = fans.get("cpu")
    gpu = fans.get("gpu")
    print(t("cli.fans", cpu=cpu if cpu is not None else "—", gpu=gpu if gpu is not None else "—"))
    return 0


def _set_led(zone_key: str, hex_color: str, brightness: int | None) -> int:
    from .backend.led import LEDBackend
    from .core.config import RGBColor, ZONE_LABELS
    from .core.i18n import t
    from .core.profiles import ProfileManager

    zone = ZONE_LABELS.get(zone_key.lower())
    if zone is None:
        print(t("cli.invalid_zone", zone=zone_key), file=sys.stderr)
        return 2
    try:
        color = RGBColor.from_hex(hex_color)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    led = LEDBackend()
    led.apply_zone(zone, color, brightness)
    ProfileManager().set_last_state(led.snapshot())
    print(t("cli.applied", zone=zone_key, color=color.to_hex()))
    return 0


def _slug(text: str) -> str:
    table = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    normalized = text.translate(table).lower()
    return "".join(ch for ch in normalized if ch.isalnum())


def _set_plan(plan_arg: str) -> int:
    from .backend.power import PowerBackend
    from .core.i18n import t

    mapping = {_slug(t(f"plan.{c}.name")): c for c in (1, 2, 3, 4)}
    mapping.update({"highpower": 1, "gaming": 2, "textmode": 3, "lowpower": 4})
    code = mapping.get(_slug(plan_arg)) or (
        int(plan_arg) if plan_arg.isdigit() and int(plan_arg) in (1, 2, 3, 4) else None
    )
    if code is None:
        print(t("cli.invalid_plan", plan=plan_arg), file=sys.stderr)
        return 2
    power = PowerBackend()
    power.set_plan(code)
    print(t("cli.plan_done", code=code))
    return 0


def _set_language(lang: str) -> int:
    from .core.i18n import set_language

    set_language(lang)
    print(f"Language / Dil: {lang}")
    return 0


def _set_effect(effect_arg: str) -> int:
    from .backend.led import EFFECT_CODES, LEDBackend

    code = EFFECT_CODES.get(effect_arg.lower()) or (
        int(effect_arg) if effect_arg.isdigit() and int(effect_arg) in EFFECT_CODES else None
    )
    if code is None:
        valid = "|".join(EFFECT_CODES.values())
        print(f"Geçersiz efekt: {effect_arg} ({valid})", file=sys.stderr)
        return 2
    led = LEDBackend()
    led.set_effect(code)
    from .backend.led import EFFECTS

    from .core.profiles import ProfileManager

    ProfileManager().set_last_state(led.snapshot(), effect=code)
    print(f"Efekt: {EFFECTS[code]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    from .core.i18n import SUPPORTED

    parser = argparse.ArgumentParser(
        prog="excalibur-center",
        description="Control Center for Casper Excalibur laptops (lighting + performance)",
    )
    parser.add_argument("--restore", action="store_true", help="re-apply last state")
    parser.add_argument("--status", action="store_true", help="print current state")
    parser.add_argument("--set-led", nargs="+", metavar=("ZONE", "HEX"),
                        help="e.g.: all FF8800 [2]")
    parser.add_argument("--brightness", type=int, choices=(0, 1, 2), default=None)
    parser.add_argument("--set-plan", metavar="PLAN",
                        help="highpower / gaming / textmode / lowpower or 1-4")
    parser.add_argument("--set-effect", metavar="EFFECT",
                        help="normal / blink / fade / heartbeat / repeat / random / ambilight")
    parser.add_argument("--lang", choices=SUPPORTED, help="set UI language")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    if args.lang:
        return _set_language(args.lang)
    if args.restore:
        return _restore()
    if args.status:
        return _status()
    if args.set_led:
        if len(args.set_led) < 2:
            parser.error("--set-led needs a zone and a color")
        return _set_led(args.set_led[0], args.set_led[1], args.brightness)
    if args.set_plan:
        return _set_plan(args.set_plan)
    if args.set_effect:
        return _set_effect(args.set_effect)

    from pathlib import Path

    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    from .gui.main_window import MainWindow

    app = QApplication(sys.argv[1:] or [])
    app.setApplicationName("Excalibur Center")
    app.setDesktopFileName("excalibur-center")

    theme_icon = QIcon.fromTheme("excalibur-center")
    if not theme_icon.isNull():
        app.setWindowIcon(theme_icon)

    qss_path = Path(__file__).parent / "gui" / "style.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
