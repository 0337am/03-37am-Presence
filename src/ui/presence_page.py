from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.discord.presence_modes import (
    MODE_NAMES,
    PresenceMode,
    remove_mode_image,
    save_mode_image,
)


class PresencePage(QWidget):
    def __init__(self, controller):
        super().__init__()

        self.controller = controller
        self.image_path = ""

        self.build_ui()
        self.load_active_mode()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(16)

        title = QLabel("Presence")
        title.setObjectName("presenceTitle")

        subtitle = QLabel(
            "Choose what your Discord Rich Presence displays"
        )
        subtitle.setObjectName("presenceSubtitle")

        root.addWidget(title)
        root.addWidget(subtitle)

        mode_card = QFrame()
        mode_card.setObjectName("presenceCard")

        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setContentsMargins(22, 18, 22, 20)
        mode_layout.setSpacing(10)

        mode_label = QLabel("Presence mode")
        mode_label.setObjectName("fieldTitle")

        self.mode_box = QComboBox()
        self.mode_box.setObjectName("modeBox")

        for mode, display_name in MODE_NAMES.items():
            self.mode_box.addItem(
                display_name,
                mode,
            )

        self.mode_box.currentIndexChanged.connect(
            self.on_mode_changed
        )

        self.mode_help = QLabel("")
        self.mode_help.setObjectName("modeHelp")
        self.mode_help.setWordWrap(True)

        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_box)
        mode_layout.addWidget(self.mode_help)

        editor_card = QFrame()
        editor_card.setObjectName("presenceCard")

        editor_layout = QHBoxLayout(editor_card)
        editor_layout.setContentsMargins(22, 20, 22, 22)
        editor_layout.setSpacing(24)

        fields_layout = QVBoxLayout()
        fields_layout.setSpacing(10)

        title_label = QLabel("Title")
        title_label.setObjectName("fieldTitle")

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(
            "Away right now"
        )

        message_label = QLabel("Message")
        message_label.setObjectName("fieldTitle")

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText(
            "Be back later ♡"
        )

        self.elapsed_box = QCheckBox(
            "Show elapsed time"
        )
        self.elapsed_box.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        fields_layout.addWidget(title_label)
        fields_layout.addWidget(self.title_input)
        fields_layout.addWidget(message_label)
        fields_layout.addWidget(self.message_input)
        fields_layout.addWidget(self.elapsed_box)
        fields_layout.addStretch()

        image_layout = QVBoxLayout()
        image_layout.setSpacing(8)

        image_title = QLabel("Custom image")
        image_title.setObjectName("fieldTitle")

        self.image_preview = QLabel(
            "No image selected"
        )
        self.image_preview.setObjectName(
            "imagePreview"
        )
        self.image_preview.setFixedSize(
            170,
            170,
        )
        self.image_preview.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_name = QLabel("")
        self.image_name.setObjectName(
            "imageName"
        )
        self.image_name.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.image_name.setWordWrap(True)

        image_buttons = QHBoxLayout()
        image_buttons.setSpacing(8)

        self.choose_image_button = QPushButton(
            "Choose image"
        )
        self.choose_image_button.setObjectName(
            "secondaryButton"
        )
        self.choose_image_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.choose_image_button.clicked.connect(
            self.choose_image
        )

        self.remove_image_button = QPushButton(
            "Remove"
        )
        self.remove_image_button.setObjectName(
            "secondaryButton"
        )
        self.remove_image_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.remove_image_button.clicked.connect(
            self.remove_image
        )

        image_buttons.addWidget(
            self.choose_image_button
        )
        image_buttons.addWidget(
            self.remove_image_button
        )

        image_layout.addWidget(
            image_title,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        image_layout.addWidget(
            self.image_preview,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        image_layout.addWidget(self.image_name)
        image_layout.addLayout(image_buttons)

        editor_layout.addLayout(
            fields_layout,
            stretch=1,
        )
        editor_layout.addLayout(image_layout)

        bottom_layout = QHBoxLayout()

        self.status_label = QLabel("")
        self.status_label.setObjectName(
            "presenceStatus"
        )

        self.apply_button = QPushButton(
            "Apply to Discord"
        )
        self.apply_button.setObjectName(
            "applyButton"
        )
        self.apply_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.apply_button.clicked.connect(
            self.apply_presence
        )

        bottom_layout.addWidget(
            self.status_label,
            stretch=1,
        )
        bottom_layout.addWidget(
            self.apply_button
        )

        root.addWidget(mode_card)
        root.addWidget(editor_card)
        root.addLayout(bottom_layout)
        root.addStretch()

        self.setStyleSheet(
            """
            QLabel#presenceTitle {
                color: #fff0f7;
                font-size: 28px;
                font-weight: bold;
            }

            QLabel#presenceSubtitle {
                color: #b96f94;
                font-size: 13px;
            }

            QFrame#presenceCard {
                background: #352747;
                border: 1px solid #5c4777;
                border-radius: 18px;
            }

            QLabel#fieldTitle {
                color: #fff5fb;
                font-size: 14px;
                font-weight: bold;
            }

            QLabel#modeHelp {
                color: #bca9ce;
                font-size: 12px;
            }

            QLabel#presenceStatus {
                color: #ff9dca;
                font-size: 12px;
            }

            QLabel#imageName {
                color: #bca9ce;
                font-size: 11px;
            }

            QLabel#imagePreview {
                color: #bca9ce;
                background: #1d1729;
                border: 1px solid #6f578a;
                border-radius: 14px;
            }

            QComboBox,
            QLineEdit {
                color: #fff5fb;
                background: #3e2e54;
                border: 1px solid #6f578a;
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 14px;
            }

            QComboBox:hover,
            QLineEdit:hover,
            QLineEdit:focus {
                border: 1px solid #ff79b9;
            }

            QComboBox QAbstractItemView {
                color: #fff5fb;
                background: #352747;
                selection-background-color: #6d234e;
                border: 1px solid #6f578a;
            }

            QCheckBox {
                color: #f8eaf2;
                spacing: 10px;
                padding-top: 6px;
            }

            QCheckBox::indicator {
                width: 19px;
                height: 19px;
                background: #1d1729;
                border: 2px solid #8f75aa;
                border-radius: 5px;
            }

            QCheckBox::indicator:checked {
                background: #ff79b9;
                border: 2px solid #ffb2d6;
            }
            """
        )

        self.setStyleSheet(
            self.styleSheet()
            + """
            QPushButton#secondaryButton {
                color: #ffeaf4;
                background: #49345f;
                border: 1px solid #7f619c;
                border-radius: 9px;
                padding: 8px 12px;
                font-weight: bold;
            }

            QPushButton#secondaryButton:hover {
                background: #5a3e72;
                border: 1px solid #ff79b9;
            }

            QPushButton#applyButton {
                color: white;
                background: #8a2e62;
                border: 1px solid #ff8fc5;
                border-radius: 11px;
                padding: 11px 20px;
                font-weight: bold;
            }

            QPushButton#applyButton:hover {
                background: #a53a76;
            }

            QPushButton:disabled,
            QLineEdit:disabled,
            QCheckBox:disabled {
                color: #796d82;
                background: #2a2235;
                border-color: #473b55;
            }
            """
        )

    @property
    def current_mode(self) -> str:
        return str(
            self.mode_box.currentData()
            or "music"
        )

    def load_active_mode(self):
        active_mode = self.controller.active_mode

        index = self.mode_box.findData(
            active_mode
        )

        if index < 0:
            index = 0

        self.mode_box.blockSignals(True)
        self.mode_box.setCurrentIndex(index)
        self.mode_box.blockSignals(False)

        self.load_mode(active_mode)
        self.update_editor_state()

    def on_mode_changed(self):
        self.load_mode(
            self.current_mode
        )
        self.update_editor_state()

    def load_mode(self, mode: str):
        presence_mode = self.controller.load_mode(
            mode
        )

        self.title_input.setText(
            presence_mode.title
        )

        self.message_input.setText(
            presence_mode.message
        )

        self.elapsed_box.setChecked(
            presence_mode.show_elapsed
        )

        self.image_path = (
            presence_mode.image_path
        )

        self.update_image_preview()

    def update_editor_state(self):
        mode = self.current_mode

        editable = mode not in {
            "music",
            "disabled",
        }

        self.title_input.setEnabled(editable)
        self.message_input.setEnabled(editable)
        self.elapsed_box.setEnabled(editable)
        self.choose_image_button.setEnabled(
            editable
        )
        self.remove_image_button.setEnabled(
            editable
        )

        if mode == "music":
            self.mode_help.setText(
                "Spotify controls the song text, "
                "timer, and album artwork automatically."
            )

        elif mode == "disabled":
            self.mode_help.setText(
                "Discord Rich Presence will be cleared."
            )

        else:
            self.mode_help.setText(
                "Your title, message, image, and timer "
                "will be shown on Discord."
            )

    def choose_image(self):
        source_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Rich Presence image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )

        if not source_path:
            return

        saved_path = save_mode_image(
            source_path,
            self.current_mode,
        )

        if not saved_path:
            self.status_label.setText(
                "The image could not be saved."
            )
            return

        self.image_path = saved_path
        self.update_image_preview()

        self.status_label.setText(
            "Image selected. Press Apply to update Discord."
        )

    def remove_image(self):
        remove_mode_image(
            self.image_path
        )

        self.image_path = ""
        self.update_image_preview()

        self.status_label.setText(
            "Image removed. Press Apply to update Discord."
        )

    def update_image_preview(self):
        path = Path(self.image_path)

        if not path.exists():
            self.image_preview.clear()
            self.image_preview.setText(
                "No image selected"
            )
            self.image_name.setText("")
            return

        pixmap = QPixmap(str(path))

        if pixmap.isNull():
            self.image_preview.clear()
            self.image_preview.setText(
                "Image could not be loaded"
            )
            self.image_name.setText(
                path.name
            )
            return

        self.image_preview.setPixmap(
            pixmap.scaled(
                160,
                160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        self.image_name.setText(
            path.name
        )

    def apply_presence(self):
        presence_mode = PresenceMode(
            mode=self.current_mode,
            title=self.title_input.text().strip(),
            message=self.message_input.text().strip(),
            image_path=self.image_path,
            show_elapsed=self.elapsed_box.isChecked(),
        )

        self.controller.apply_mode(
            presence_mode
        )

        if self.current_mode == "music":
            self.status_label.setText(
                "Music presence enabled."
            )

        elif self.current_mode == "disabled":
            self.status_label.setText(
                "Discord Rich Presence disabled."
            )

        else:
            mode_name = self.mode_box.currentText()

            self.status_label.setText(
                f"{mode_name} presence applied."
            )