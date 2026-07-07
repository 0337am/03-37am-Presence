from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.system.startup import StartupManager


class SettingsPage(QWidget):
    show_portrait_changed = pyqtSignal(bool)
    always_on_top_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()

        self.store = QSettings(
            "0337am",
            "Presence",
        )

        self.build_ui()

    @property
    def show_yuno_portrait(self) -> bool:
        return self.store.value(
            "show_yuno_portrait",
            True,
            type=bool,
        )

    @property
    def always_on_top(self) -> bool:
        return self.store.value(
            "always_on_top",
            False,
            type=bool,
        )

    @property
    def start_minimized(self) -> bool:
        return self.store.value(
            "start_minimized",
            True,
            type=bool,
        )

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(18)

        title = QLabel("Settings")
        title.setObjectName("title")

        subtitle = QLabel(
            "Changes are saved automatically"
        )
        subtitle.setObjectName("subtitle")

        root.addWidget(title)
        root.addWidget(subtitle)

        appearance = self.create_card(
            "Appearance",
            "Choose how the desktop app behaves.",
        )

        appearance_layout = appearance.layout()

        self.portrait_box = self.create_checkbox(
            "Show Yuno portrait",
            self.show_yuno_portrait,
        )

        self.top_box = self.create_checkbox(
            "Keep window on top",
            self.always_on_top,
        )

        self.portrait_box.toggled.connect(
            self.change_portrait
        )

        self.top_box.toggled.connect(
            self.change_always_on_top
        )

        appearance_layout.addWidget(
            self.portrait_box
        )

        appearance_layout.addWidget(
            self.top_box
        )

        startup = self.create_card(
            "Windows startup",
            "Control how the app starts with Windows.",
        )

        startup_layout = startup.layout()

        self.windows_box = self.create_checkbox(
            "Start with Windows",
            StartupManager.is_enabled(),
        )

        self.hidden_box = self.create_checkbox(
            "Start hidden in the tray",
            self.start_minimized,
        )

        self.windows_box.toggled.connect(
            self.change_windows_startup
        )

        self.hidden_box.toggled.connect(
            self.change_start_minimized
        )

        startup_layout.addWidget(
            self.windows_box
        )

        startup_layout.addWidget(
            self.hidden_box
        )

        self.status = QLabel("")
        self.status.setObjectName("status")

        reset = QPushButton("Reset settings")
        reset.setObjectName("reset")
        reset.clicked.connect(self.reset_settings)

        root.addWidget(appearance)
        root.addWidget(startup)
        root.addWidget(self.status)

        root.addWidget(
            reset,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )

        root.addStretch()

        self.setStyleSheet(
            """
            QLabel#title {
                color: #fff0f7;
                font-size: 28px;
                font-weight: bold;
            }

            QLabel#subtitle {
                color: #b96f94;
                font-size: 13px;
            }

            QFrame#card {
                background: #352747;
                border: 1px solid #5c4777;
                border-radius: 18px;
            }

            QLabel#cardTitle {
                color: #fff5fb;
                font-size: 18px;
                font-weight: bold;
            }

            QLabel#cardDescription {
                color: #bca9ce;
                font-size: 13px;
            }

            QLabel#status {
                color: #ff9dca;
                font-size: 12px;
            }

            QCheckBox {
                color: #f8eaf2;
                background: #3e2e54;
                border: 1px solid #5c4777;
                border-radius: 12px;
                padding: 13px;
                spacing: 12px;
                font-size: 14px;
            }

            QCheckBox:hover {
                background: #49345f;
                border: 1px solid #ff79b9;
            }

            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                background: #1d1729;
                border: 2px solid #8f75aa;
                border-radius: 6px;
            }

            QCheckBox::indicator:checked {
                background: #ff79b9;
                border: 2px solid #ffb2d6;
            }

            QPushButton#reset {
                color: #ffeaf4;
                background: #521b3d;
                border: 1px solid #ff79b9;
                border-radius: 10px;
                padding: 9px 16px;
                font-weight: bold;
            }

            QPushButton#reset:hover {
                background: #6d234e;
            }
            """
        )

    def create_card(
        self,
        title: str,
        description: str,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")

        description_label = QLabel(description)
        description_label.setObjectName(
            "cardDescription"
        )
        description_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(description_label)

        return card

    @staticmethod
    def create_checkbox(
        text: str,
        checked: bool,
    ) -> QCheckBox:
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        checkbox.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        return checkbox

    def change_portrait(self, checked: bool):
        self.store.setValue(
            "show_yuno_portrait",
            checked,
        )
        self.show_portrait_changed.emit(checked)

    def change_always_on_top(self, checked: bool):
        self.store.setValue(
            "always_on_top",
            checked,
        )
        self.always_on_top_changed.emit(checked)

    def change_windows_startup(self, checked: bool):
        success = StartupManager.set_enabled(
            checked,
            self.hidden_box.isChecked(),
        )

        if success:
            message = (
                "Windows startup enabled."
                if checked
                else "Windows startup disabled."
            )
            self.status.setText(message)
            return

        self.status.setText(
            "Windows startup could not be changed."
        )

        self.windows_box.blockSignals(True)
        self.windows_box.setChecked(not checked)
        self.windows_box.blockSignals(False)

    def change_start_minimized(self, checked: bool):
        self.store.setValue(
            "start_minimized",
            checked,
        )

        if self.windows_box.isChecked():
            StartupManager.set_enabled(
                True,
                checked,
            )

        self.status.setText(
            "Startup preference saved."
        )

    def reset_settings(self):
        self.portrait_box.setChecked(True)
        self.top_box.setChecked(False)
        self.hidden_box.setChecked(True)
        self.windows_box.setChecked(False)

        self.status.setText(
            "Settings reset."
        )