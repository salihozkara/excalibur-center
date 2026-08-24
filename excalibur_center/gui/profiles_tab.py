"""Profiles page: save, apply and delete lighting profiles."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.i18n import t


class ProfilesPage(QWidget):
    def __init__(self, led_backend, profile_manager, lighting_page, set_status, parent=None):
        super().__init__(parent)
        self.led = led_backend
        self.pm = profile_manager
        self.lighting_page = lighting_page
        self.set_status = set_status

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel(t("profiles.title"))
        title.setObjectName("pageTitle")
        desc = QLabel(t("profiles.desc"))
        desc.setObjectName("pageDesc")
        root.addWidget(title)
        root.addWidget(desc)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.apply_selected)
        root.addWidget(self.list_widget, stretch=1)

        buttons = QHBoxLayout()
        save_btn = QPushButton(t("profiles.save_current"))
        save_btn.setObjectName("accentButton")
        save_btn.clicked.connect(self.save_current)
        apply_btn = QPushButton(t("profiles.apply"))
        apply_btn.clicked.connect(self.apply_selected)
        delete_btn = QPushButton(t("profiles.delete"))
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self.delete_selected)
        buttons.addWidget(save_btn)
        buttons.addWidget(apply_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        root.addLayout(buttons)

        self.refresh_list()

    def _selected_name(self):
        item = self.list_widget.currentItem()
        if not item:
            return None
        return item.text().replace(t("profiles.last_suffix"), "")

    def refresh_list(self) -> None:
        self.list_widget.clear()
        _, last_name = self.pm.get_last_state()
        suffix = t("profiles.last_suffix")
        for name in self.pm.list_profiles():
            self.list_widget.addItem(name + (suffix if name == last_name else ""))

    def save_current(self) -> None:
        name, ok = QInputDialog.getText(
            self, t("profiles.save_title"), t("profiles.save_label"),
            text=t("profiles.default_name"),
        )
        if not ok or not name.strip():
            return
        try:
            self.pm.save_profile(name.strip(), self.led.snapshot())
        except ValueError as exc:
            QMessageBox.warning(self, t("profiles.invalid_name_title"), str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, t("profiles.error_title"), str(exc))
            return
        self.pm.set_last_state(self.led.snapshot(), profile_name=name.strip())
        self.refresh_list()
        self.set_status("✔ " + t("status.profile_saved", name=name.strip()))

    def apply_selected(self, *_args) -> None:
        name = self._selected_name()
        if not name:
            self.set_status(t("status.select_first"), error=True)
            return
        snapshot = self.pm.load_profile(name)
        if snapshot is None:
            self.set_status(name, error=True)
            return
        try:
            self.led.restore_snapshot(snapshot)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, t("profiles.error_title"), str(exc))
            return
        self.pm.set_last_state(snapshot, profile_name=name)
        self.lighting_page.sync_from_backend()
        self.refresh_list()
        self.set_status("✔ " + t("status.profile_applied", name=name))

    def delete_selected(self) -> None:
        name = self._selected_name()
        if not name:
            self.set_status(t("status.select_first"), error=True)
            return
        confirm = QMessageBox.question(
            self, t("profiles.confirm_title"), t("profiles.confirm_text", name=name)
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.pm.delete_profile(name)
        self.refresh_list()
        self.set_status("✔ " + t("status.profile_deleted", name=name))
