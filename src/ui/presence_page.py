from pathlib import Path

from PyQt6.QtCore import (
    Qt,
    pyqtSlot,
)
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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.discord.presence_modes import (
    MODE_NAMES,
    PresenceMode,
    remove_mode_image,
    save_mode_image,
)
from src.ui.theme import ThemeManager


class PresencePage(QWidget):
    def __init__(
        self,
        controller,
        theme_manager=None,
    ):
        super().__init__()

        self.setObjectName("presenceRoot")

        self.controller = controller
        self.theme_manager = (
            theme_manager
            or ThemeManager(self)
        )

        self.image_path = ""
        self._editor_image_size = 108
        self._preview_image_size = 62

        self.build_ui()
        self.connect_signals()

        self.theme_manager.theme_changed.connect(
            self.apply_theme
        )

        self.apply_theme(
            self.theme_manager.theme()
        )

        self.load_active_mode()

    def build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )
        self.root_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)

        heading_group = QVBoxLayout()
        heading_group.setSpacing(1)

        self.page_title = QLabel("Presence")
        self.page_title.setObjectName(
            "presenceTitle"
        )

        self.page_subtitle = QLabel(
            "Choose and preview your Discord activity"
        )
        self.page_subtitle.setObjectName(
            "presenceSubtitle"
        )

        heading_group.addWidget(
            self.page_title
        )
        heading_group.addWidget(
            self.page_subtitle
        )

        self.active_badge = QLabel(
            "MUSIC"
        )
        self.active_badge.setObjectName(
            "activeBadge"
        )
        self.active_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        header.addLayout(heading_group)
        header.addStretch()
        header.addWidget(
            self.active_badge,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )

        self.root_layout.addLayout(header)

        self.mode_card = QFrame()
        self.mode_card.setObjectName(
            "presenceCard"
        )

        mode_layout = QVBoxLayout(
            self.mode_card
        )
        mode_layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )
        mode_layout.setSpacing(7)

        mode_header = QHBoxLayout()
        mode_header.setSpacing(10)

        mode_label = QLabel(
            "Presence mode"
        )
        mode_label.setObjectName(
            "fieldTitle"
        )

        self.mode_box = QComboBox()
        self.mode_box.setObjectName(
            "modeBox"
        )
        self.mode_box.setMinimumWidth(190)

        for mode, display_name in MODE_NAMES.items():
            self.mode_box.addItem(
                display_name,
                mode,
            )

        mode_header.addWidget(mode_label)
        mode_header.addStretch()
        mode_header.addWidget(
            self.mode_box
        )

        self.mode_help = QLabel("")
        self.mode_help.setObjectName(
            "modeHelp"
        )
        self.mode_help.setWordWrap(True)

        mode_layout.addLayout(mode_header)
        mode_layout.addWidget(
            self.mode_help
        )

        self.root_layout.addWidget(
            self.mode_card
        )

        self.content_row = QHBoxLayout()
        self.content_row.setSpacing(12)

        self.editor_card = QFrame()
        self.editor_card.setObjectName(
            "presenceCard"
        )

        self.editor_layout = QVBoxLayout(
            self.editor_card
        )
        self.editor_layout.setContentsMargins(
            16,
            15,
            16,
            15,
        )
        self.editor_layout.setSpacing(10)

        editor_heading = QLabel(
            "Activity details"
        )
        editor_heading.setObjectName(
            "cardHeading"
        )

        title_label = QLabel("Title")
        title_label.setObjectName(
            "fieldTitle"
        )

        self.title_input = QLineEdit()
        self.title_input.setObjectName(
            "presenceInput"
        )
        self.title_input.setPlaceholderText(
            "Away right now"
        )
        self.title_input.setMaxLength(128)

        message_label = QLabel("Message")
        message_label.setObjectName(
            "fieldTitle"
        )

        self.message_input = QLineEdit()
        self.message_input.setObjectName(
            "presenceInput"
        )
        self.message_input.setPlaceholderText(
            "Be back later \u2661"
        )
        self.message_input.setMaxLength(128)

        self.elapsed_box = QCheckBox(
            "Show elapsed time"
        )
        self.elapsed_box.setObjectName(
            "elapsedBox"
        )
        self.elapsed_box.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.editor_layout.addWidget(
            editor_heading
        )
        self.editor_layout.addWidget(
            title_label
        )
        self.editor_layout.addWidget(
            self.title_input
        )
        self.editor_layout.addWidget(
            message_label
        )
        self.editor_layout.addWidget(
            self.message_input
        )
        self.editor_layout.addWidget(
            self.elapsed_box
        )

        self.editor_layout.addStretch()

        self.image_card = QFrame()
        self.image_card.setObjectName(
            "presenceCard"
        )

        image_layout = QVBoxLayout(
            self.image_card
        )
        image_layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )
        image_layout.setSpacing(8)

        image_heading = QLabel(
            "Custom image"
        )
        image_heading.setObjectName(
            "cardHeading"
        )

        self.image_preview = QLabel(
            "No image selected"
        )
        self.image_preview.setObjectName(
            "imagePreview"
        )
        self.image_preview.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.image_preview.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
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
        image_buttons.setSpacing(7)

        self.choose_image_button = QPushButton(
            "Choose"
        )
        self.choose_image_button.setObjectName(
            "secondaryButton"
        )
        self.choose_image_button.setCursor(
            Qt.CursorShape.PointingHandCursor
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

        image_buttons.addWidget(
            self.choose_image_button
        )
        image_buttons.addWidget(
            self.remove_image_button
        )

        image_layout.addWidget(
            image_heading
        )
        image_layout.addWidget(
            self.image_preview,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        image_layout.addWidget(
            self.image_name
        )
        image_layout.addLayout(
            image_buttons
        )

        self.preview_card = QFrame()
        self.preview_card.setObjectName(
            "previewCard"
        )

        preview_layout = QVBoxLayout(
            self.preview_card
        )
        preview_layout.setContentsMargins(
            14,
            13,
            14,
            13,
        )
        preview_layout.setSpacing(8)

        preview_header = QHBoxLayout()
        preview_header.setSpacing(8)

        preview_heading = QLabel(
            "DISCORD PREVIEW"
        )
        preview_heading.setObjectName(
            "previewHeading"
        )

        self.preview_mode = QLabel(
            "MUSIC"
        )
        self.preview_mode.setObjectName(
            "previewMode"
        )
        self.preview_mode.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        preview_header.addWidget(
            preview_heading
        )
        preview_header.addStretch()
        preview_header.addWidget(
            self.preview_mode
        )

        self.preview_app = QLabel(
            "03:37am Presence"
        )
        self.preview_app.setObjectName(
            "previewApp"
        )

        activity_row = QHBoxLayout()
        activity_row.setSpacing(10)

        self.preview_image = QLabel(
            "Image"
        )
        self.preview_image.setObjectName(
            "previewImage"
        )
        self.preview_image.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.preview_image.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        preview_text = QVBoxLayout()
        preview_text.setSpacing(2)

        self.preview_title = QLabel(
            "Waiting for activity"
        )
        self.preview_title.setObjectName(
            "previewTitle"
        )
        self.preview_title.setWordWrap(True)

        self.preview_message = QLabel(
            "Select a presence mode"
        )
        self.preview_message.setObjectName(
            "previewMessage"
        )
        self.preview_message.setWordWrap(True)

        self.preview_timer = QLabel("")
        self.preview_timer.setObjectName(
            "previewTimer"
        )

        preview_text.addWidget(
            self.preview_title
        )
        preview_text.addWidget(
            self.preview_message
        )
        preview_text.addStretch()
        preview_text.addWidget(
            self.preview_timer
        )

        activity_row.addWidget(
            self.preview_image,
            alignment=Qt.AlignmentFlag.AlignTop,
        )
        activity_row.addLayout(
            preview_text,
            stretch=1,
        )

        preview_layout.addLayout(
            preview_header
        )
        preview_layout.addWidget(
            self.preview_app
        )
        preview_layout.addLayout(
            activity_row
        )
        preview_layout.addStretch()

        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        right_column.addWidget(
            self.image_card
        )
        right_column.addWidget(
            self.preview_card,
            stretch=1,
        )

        self.content_row.addWidget(
            self.editor_card,
            stretch=3,
        )
        self.content_row.addLayout(
            right_column,
            stretch=2,
        )

        self.root_layout.addLayout(
            self.content_row
        )

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.status_label = QLabel("")
        self.status_label.setObjectName(
            "presenceStatus"
        )
        self.status_label.setWordWrap(True)

        self.apply_button = QPushButton(
            "Apply to Discord"
        )
        self.apply_button.setObjectName(
            "applyButton"
        )
        self.apply_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        bottom_layout.addWidget(
            self.status_label,
            stretch=1,
        )
        bottom_layout.addWidget(
            self.apply_button
        )

        self.root_layout.addLayout(
            bottom_layout
        )
        self.root_layout.addStretch()

    def connect_signals(self):
        self.mode_box.currentIndexChanged.connect(
            self.on_mode_changed
        )

        self.title_input.textChanged.connect(
            self.update_preview
        )
        self.message_input.textChanged.connect(
            self.update_preview
        )
        self.elapsed_box.toggled.connect(
            self.update_preview
        )

        self.choose_image_button.clicked.connect(
            self.choose_image
        )
        self.remove_image_button.clicked.connect(
            self.remove_image
        )
        self.apply_button.clicked.connect(
            self.apply_presence
        )

        self.theme_manager.branding_changed.connect(
            self.apply_branding
        )

        self.apply_branding(
            self.theme_manager.branding()
        )

    @pyqtSlot(dict)
    def apply_theme(self, theme: dict):
        compact = theme.get(
            "compact",
            True,
        )

        self._editor_image_size = (
            100 if compact else 120
        )

        self._preview_image_size = (
            56 if compact else 68
        )

        margin = 18 if compact else 24
        spacing = 10 if compact else 14
        title_size = 23 if compact else 27
        input_padding = 8 if compact else 10

        self.root_layout.setContentsMargins(
            margin,
            margin,
            margin,
            margin,
        )

        self.root_layout.setSpacing(
            spacing
        )

        self.image_preview.setFixedSize(
            self._editor_image_size,
            self._editor_image_size,
        )

        self.preview_image.setFixedSize(
            self._preview_image_size,
            self._preview_image_size,
        )

        self.setStyleSheet(
            f"""
            QWidget#presenceRoot {{
                background: {theme["background"]};
            }}

            QLabel#presenceTitle {{
                color: {theme["text"]};
                font-size: {title_size}px;
                font-weight: 700;
            }}

            QLabel#presenceSubtitle {{
                color: {theme["muted"]};
                font-size: 11px;
            }}

            QLabel#activeBadge {{
                color: {theme["accent"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 5px 10px;
                font-size: 10px;
                font-weight: 700;
            }}

            QFrame#presenceCard,
            QFrame#previewCard {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}

            QLabel#cardHeading {{
                color: {theme["accent"]};
                font-size: 11px;
                font-weight: 700;
            }}

            QLabel#fieldTitle {{
                color: {theme["text"]};
                font-size: 11px;
                font-weight: 650;
            }}

            QLabel#modeHelp,
            QLabel#imageName,
            QLabel#presenceStatus {{
                color: {theme["muted"]};
                font-size: 10px;
            }}

            QLabel#imagePreview,
            QLabel#previewImage {{
                color: {theme["muted"]};
                background: {theme["background"]};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
            }}

            QComboBox#modeBox,
            QLineEdit#presenceInput {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: {input_padding}px 10px;
                selection-background-color: {theme["accent"]};
            }}

            QComboBox#modeBox {{
                font-size: 9pt;
            }}

            QLineEdit#presenceInput {{
                font-size: 11px;
            }}

            QComboBox#modeBox:hover,
            QComboBox#modeBox:focus,
            QLineEdit#presenceInput:hover,
            QLineEdit#presenceInput:focus {{
                border: 1px solid {theme["accent"]};
            }}

            QComboBox#modeBox::drop-down {{
                border: none;
                width: 22px;
            }}

            QComboBox QAbstractItemView {{
                color: {theme["text"]};
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                selection-color: {theme["text"]};
                selection-background-color: {theme["accent"]};
                outline: none;
            }}

            QCheckBox#elapsedBox {{
                color: {theme["text"]};
                spacing: 8px;
                font-size: 11px;
                padding-top: 3px;
            }}

            QCheckBox#elapsedBox::indicator {{
                width: 16px;
                height: 16px;
                background: {theme["background"]};
                border: 1px solid {theme["border"]};
                border-radius: 4px;
            }}

            QCheckBox#elapsedBox::indicator:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QCheckBox#elapsedBox::indicator:checked {{
                background: {theme["accent"]};
                border: 1px solid {theme["accent"]};
            }}

            QPushButton#secondaryButton {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 10px;
                font-weight: 650;
            }}

            QPushButton#secondaryButton:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QPushButton#secondaryButton:pressed {{
                background: {theme["background"]};
            }}

            QPushButton#applyButton {{
                color: {theme["background"]};
                background: {theme["accent"]};
                border: 1px solid {theme["accent"]};
                border-radius: 9px;
                padding: 9px 17px;
                font-size: 11px;
                font-weight: 700;
            }}

            QPushButton#applyButton:hover {{
                color: {theme["text"]};
            }}

            QPushButton#applyButton:pressed {{
                padding-top: 10px;
                padding-bottom: 8px;
            }}

            QPushButton:disabled,
            QLineEdit:disabled {{
                color: {theme["muted"]};
                background: {theme["background"]};
                border-color: {theme["border"]};
            }}

            QCheckBox:disabled {{
                color: {theme["muted"]};
            }}

            QLabel#previewHeading {{
                color: {theme["accent"]};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#previewMode {{
                color: {theme["accent"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 7px;
                padding: 3px 7px;
                font-size: 9px;
                font-weight: 700;
            }}

            QLabel#previewApp {{
                color: {theme["text"]};
                font-size: 11px;
                font-weight: 650;
            }}

            QLabel#previewTitle {{
                color: {theme["text"]};
                font-size: 12px;
                font-weight: 700;
            }}

            QLabel#previewMessage,
            QLabel#previewTimer {{
                color: {theme["muted"]};
                font-size: 10px;
            }}
            """
        )

        self.update_image_preview()

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
        self.update_preview()

    def on_mode_changed(self, *_):
        self.load_mode(
            self.current_mode
        )
        self.update_editor_state()
        self.update_preview()

        self.status_label.setText(
            "Press Apply to update Discord."
        )

    def load_mode(self, mode: str):
        presence_mode = (
            self.controller.load_mode(mode)
        )

        self.title_input.blockSignals(True)
        self.message_input.blockSignals(True)
        self.elapsed_box.blockSignals(True)

        self.title_input.setText(
            presence_mode.title
        )
        self.message_input.setText(
            presence_mode.message
        )
        self.elapsed_box.setChecked(
            presence_mode.show_elapsed
        )

        self.title_input.blockSignals(False)
        self.message_input.blockSignals(False)
        self.elapsed_box.blockSignals(False)

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

        mode_name = self.mode_box.currentText()

        self.active_badge.setText(
            mode_name.upper()
        )
        self.preview_mode.setText(
            mode_name.upper()
        )

        if mode == "music":
            self.mode_help.setText(
                "Spotify controls the song title, "
                "artist, timer, and artwork automatically."
            )

        elif mode == "disabled":
            self.mode_help.setText(
                "Discord Rich Presence will be cleared."
            )

        else:
            self.mode_help.setText(
                "Your title, message, image, and timer "
                "will be displayed on Discord."
            )

    @pyqtSlot(dict)
    def apply_branding(self, branding: dict):
        title = (
            branding.get("title", "")
            or "03:37am Presence"
        )

        self.preview_app.setText(title)

    def update_preview(self, *_):
        mode = self.current_mode

        mode_name = self.mode_box.currentText()

        self.preview_mode.setText(
            mode_name.upper()
        )

        if mode == "music":
            self.preview_title.setText(
                "Current Spotify track"
            )
            self.preview_message.setText(
                "Artist and album update automatically"
            )
            self.preview_timer.setText(
                "Playback timer"
            )

            if not Path(self.image_path).exists():
                self.preview_image.clear()
                self.preview_image.setText(
                    "Music"
                )

            return

        if mode == "disabled":
            self.preview_title.setText(
                "Rich Presence disabled"
            )
            self.preview_message.setText(
                "Nothing will be displayed on Discord"
            )
            self.preview_timer.setText("")

            self.preview_image.clear()
            self.preview_image.setText(
                "Off"
            )
            return

        title = (
            self.title_input.text().strip()
            or mode_name
        )

        message = (
            self.message_input.text().strip()
            or "No message"
        )

        self.preview_title.setText(title)
        self.preview_message.setText(message)

        if self.elapsed_box.isChecked():
            self.preview_timer.setText(
                "00:00 elapsed"
            )
        else:
            self.preview_timer.setText("")

        if not Path(self.image_path).exists():
            self.preview_image.clear()
            self.preview_image.setText(
                mode_name[:5]
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
        self.update_preview()

        self.status_label.setText(
            "Image selected. Press Apply to update Discord."
        )

    def remove_image(self):
        remove_mode_image(
            self.image_path
        )

        self.image_path = ""

        self.update_image_preview()
        self.update_preview()

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

            self.preview_image.clear()

            if self.current_mode == "music":
                self.preview_image.setText(
                    "Music"
                )

            elif self.current_mode == "disabled":
                self.preview_image.setText(
                    "Off"
                )

            else:
                mode_name = (
                    self.mode_box.currentText()
                    or "Mode"
                )

                self.preview_image.setText(
                    mode_name[:5]
                )

            return

        pixmap = QPixmap(str(path))

        if pixmap.isNull():
            self.image_preview.clear()
            self.image_preview.setText(
                "Image could not be loaded"
            )

            self.preview_image.clear()
            self.preview_image.setText(
                "Invalid"
            )

            self.image_name.setText(
                path.name
            )
            return

        editor_pixmap = pixmap.scaled(
            self._editor_image_size,
            self._editor_image_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        preview_pixmap = pixmap.scaled(
            self._preview_image_size,
            self._preview_image_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.image_preview.setText("")
        self.image_preview.setPixmap(
            editor_pixmap
        )

        self.preview_image.setText("")
        self.preview_image.setPixmap(
            preview_pixmap
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
            show_elapsed=(
                self.elapsed_box.isChecked()
            ),
        )

        self.controller.apply_mode(
            presence_mode
        )

        mode_name = self.mode_box.currentText()

        self.active_badge.setText(
            mode_name.upper()
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
            self.status_label.setText(
                f"{mode_name} presence applied."
            )

        self.update_preview()