"""Main window: sidebar navigation and shared services."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, __version__
from ..backend.led import LEDBackend
from ..backend.power import PowerBackend
from ..core.config import LED_CONTROL_PATH
from ..core.i18n import SUPPORTED, get_language, set_language, t
from ..core.profiles import ProfileManager
from .lighting_tab import LightingPage
from .performance_tab import PerformancePage
from .profiles_tab import ProfilesPage

NAV_ITEMS = [
    ("lighting", "🎨", "nav.lighting"),
    ("performance", "⚡", "nav.performance"),
    ("profiles", "💾", "nav.profiles"),
]

LANG_LABELS = {"en": "English", "tr": "Türkçe"}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(860, 600)

        self.pm = ProfileManager()
        try:
            self.led = LEDBackend()
        except (FileNotFoundError, PermissionError):
            self._show_unsupported()
            return
        self.power = PowerBackend()

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 0, 12, 16)
        side_layout.setSpacing(4)

        app_title = QLabel(APP_NAME)
        app_title.setObjectName("appTitle")
        subtitle = QLabel(t("app.subtitle"))
        subtitle.setObjectName("appSubtitle")
        subtitle.setWordWrap(True)
        side_layout.addWidget(app_title)
        side_layout.addWidget(subtitle)

        self.nav_buttons: dict[str, QPushButton] = {}
        for key, icon, label_key in NAV_ITEMS:
            btn = QPushButton(f"{icon}  {t(label_key)}")
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=key: self.switch_page(k))
            self.nav_buttons[key] = btn
            side_layout.addWidget(btn)

        side_layout.addStretch()

        lang_label = QLabel(t("lang.label"))
        lang_label.setObjectName("appSubtitle")
        lang_label.setWordWrap(True)
        side_layout.addWidget(lang_label)
        self.lang_combo = QComboBox()
        for code in SUPPORTED:
            self.lang_combo.addItem(LANG_LABELS.get(code, code), code)
        self.lang_combo.setCurrentIndex(SUPPORTED.index(get_language()))
        self.lang_combo.currentIndexChanged.connect(self._on_language_change)
        side_layout.addWidget(self.lang_combo)

        version = QLabel("v" + __version__)
        version.setObjectName("appSubtitle")
        side_layout.addWidget(version)
        layout.addWidget(sidebar)

        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background-color: #23262e;")
        layout.addWidget(divider)

        self.stack = QStackedWidget()
        self.lighting_page = LightingPage(self.led, self.pm, self.set_status)
        self.performance_page = PerformancePage(self.power, self.set_status)
        self.profiles_page = ProfilesPage(
            self.led, self.pm, self.lighting_page, self.set_status
        )
        for page in (self.lighting_page, self.performance_page, self.profiles_page):
            self.stack.addWidget(page)
        layout.addWidget(self.stack, stretch=1)

        self.setCentralWidget(central)
        self.statusBar().showMessage("")
        self.statusBar().setStyleSheet("color: #8b93a4; font-size: 12px;")
        self.switch_page("lighting")

    # ── helpers ──────────────────────────────────────────────
    def switch_page(self, key: str) -> None:
        index = {k: i for i, (k, _, _) in enumerate(NAV_ITEMS)}[key]
        self.stack.setCurrentIndex(index)
        for name, btn in self.nav_buttons.items():
            btn.setChecked(name == key)

    def set_status(self, message: str, error: bool = False) -> None:
        self.statusBar().showMessage(message)
        color = "#f87171" if error else "#34d399" if message.startswith("✔") else "#8b93a4"
        self.statusBar().setStyleSheet(f"color: {color}; font-size: 12px;")

    def _on_language_change(self, index: int) -> None:
        code = self.lang_combo.itemData(index)
        if code and code != get_language():
            set_language(code)
            self.set_status(
                "✔ " + ("Restart the app to apply the language."
                        if code == "en" else
                        "Dili uygulamak için uygulamayı yeniden başlat.")
            )

    def closeEvent(self, event) -> None:  # noqa: N802
        self.performance_page.shutdown()
        super().closeEvent(event)

    def _show_unsupported(self) -> None:
        label = QLabel(
            t("unsupported.title")
            + t("unsupported.body", path=LED_CONTROL_PATH)
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #d7dbe4;")
        self.setCentralWidget(label)
