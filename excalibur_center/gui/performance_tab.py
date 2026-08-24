"""Performance page: power plans and live fan monitoring."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.i18n import t


class PerformancePage(QWidget):
    FAN_REFRESH_MS = 2000

    def __init__(self, power_backend, set_status, parent=None):
        super().__init__(parent)
        self.power = power_backend
        self.set_status = set_status

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel(t("perf.title"))
        title.setObjectName("pageTitle")
        desc = QLabel(t("perf.desc"))
        desc.setObjectName("pageDesc")
        root.addWidget(title)
        root.addWidget(desc)

        plans_label = QLabel(t("perf.plans"))
        plans_label.setObjectName("cardTitle")
        root.addWidget(plans_label)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.plan_buttons: dict[int, QPushButton] = {}
        icons = {1: "🚀", 2: "🎮", 3: "📄", 4: "🌿"}
        for i, code in enumerate((1, 2, 3, 4)):
            btn = QPushButton(
                f"{icons[code]}  {t(f'plan.{code}.name')}\n{t(f'plan.{code}.desc')}"
            )
            btn.setObjectName("planCard")
            btn.setCheckable(True)
            btn.setMinimumHeight(74)
            btn.clicked.connect(lambda _=False, c=code: self.apply_plan(c))
            self.plan_buttons[code] = btn
            grid.addWidget(btn, i // 2, i % 2)
        root.addLayout(grid)

        fans_label = QLabel(t("perf.fans"))
        fans_label.setObjectName("cardTitle")
        root.addWidget(fans_label)

        fan_row = QHBoxLayout()
        fan_row.setSpacing(10)
        self.fan_labels: dict[str, QLabel] = {}
        for key, name_key in (("cpu", "fan.cpu"), ("gpu", "fan.gpu")):
            frame = QFrame()
            frame.setObjectName("card")
            layout = QVBoxLayout(frame)
            name_lbl = QLabel(t(name_key))
            name_lbl.setObjectName("cardHint")
            value_lbl = QLabel("— RPM")
            value_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #e8ebf0;")
            layout.addWidget(name_lbl)
            layout.addWidget(value_lbl)
            self.fan_labels[key] = value_lbl
            fan_row.addWidget(frame)
        refresh_btn = QPushButton(t("perf.refresh"))
        refresh_btn.clicked.connect(self.refresh_fans)
        fan_row.addWidget(refresh_btn)
        fan_row.addStretch()
        root.addLayout(fan_row)

        root.addStretch()

        if not self.power.available:
            note = QLabel("⚠ " + t("perf.unavailable"))
            note.setObjectName("pageDesc")
            note.setWordWrap(True)
            root.insertWidget(3, note)
            for btn in self.plan_buttons.values():
                btn.setEnabled(False)
        else:
            self.sync_plans()

        self._timer = QTimer(self)
        self._timer.setInterval(self.FAN_REFRESH_MS)
        self._timer.timeout.connect(self.refresh_fans)
        self._timer.start()
        self.refresh_fans()

    # ── actions ──────────────────────────────────────────────
    def sync_plans(self) -> None:
        current = self.power.get_plan()
        for code, btn in self.plan_buttons.items():
            btn.setChecked(code == current)

    def apply_plan(self, code: int) -> None:
        try:
            self.power.set_plan(code)
        except Exception as exc:  # noqa: BLE001
            self.set_status("✖ " + t("status.plan_failed", error=str(exc)), error=True)
            self.sync_plans()
            return
        self.sync_plans()
        self.set_status("✔ " + t("status.plan", name=t(f"plan.{code}.name")))

    def refresh_fans(self) -> None:
        speeds = self.power.fans()
        for key, label in self.fan_labels.items():
            value = speeds.get(key)
            label.setText("—" if value is None else f"{value:,} RPM".replace(",", "."))

    def shutdown(self) -> None:
        self._timer.stop()
