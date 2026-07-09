from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src.artwork.cloudinary_preferences import (
    CloudinaryPreferences,
    CloudinaryPreferencesStore,
)


class ArtworkHostingCard(QFrame):
    """
    Optional Bring Your Own Cloudinary settings card.

    The card stores only a cloud name and unsigned
    upload preset. API keys and API secrets are not
    requested or supported.
    """

    message_changed = pyqtSignal(str)

    def __init__(
        self,
        preferences_store=None,
        parent=None,
    ):
        super().__init__(parent)

        self.preferences_store = (
            preferences_store
            or CloudinaryPreferencesStore()
        )

        self.setObjectName(
            "settingsCard"
        )

        self.build_ui()

        self.load_preferences()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            18,
            16,
            18,
            18,
        )
        layout.setSpacing(10)

        title = QLabel(
            "Artwork Hosting"
        )
        title.setObjectName(
            "cardTitle"
        )

        description = QLabel(
            (
                "Optionally connect your own "
                "Cloudinary account so locally sourced "
                "artwork can appear on Discord."
            )
        )
        description.setObjectName(
            "cardDescription"
        )
        description.setWordWrap(
            True
        )

        self.enabled_box = QCheckBox(
            "Enable personal artwork hosting"
        )
        self.enabled_box.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        fields = QGridLayout()
        fields.setHorizontalSpacing(12)
        fields.setVerticalSpacing(10)

        cloud_name_label = QLabel(
            "Cloud name"
        )
        cloud_name_label.setObjectName(
            "fieldLabel"
        )

        self.cloud_name_input = QLineEdit()
        self.cloud_name_input.setObjectName(
            "textField"
        )
        self.cloud_name_input.setPlaceholderText(
            "Your Cloudinary cloud name"
        )
        self.cloud_name_input.setClearButtonEnabled(
            True
        )
        self.cloud_name_input.setMaxLength(
            128
        )

        preset_label = QLabel(
            "Unsigned upload preset"
        )
        preset_label.setObjectName(
            "fieldLabel"
        )

        self.upload_preset_input = QLineEdit()
        self.upload_preset_input.setObjectName(
            "textField"
        )
        self.upload_preset_input.setPlaceholderText(
            "Dedicated unsigned preset"
        )
        self.upload_preset_input.setClearButtonEnabled(
            True
        )
        self.upload_preset_input.setMaxLength(
            255
        )

        fields.addWidget(
            cloud_name_label,
            0,
            0,
        )
        fields.addWidget(
            self.cloud_name_input,
            0,
            1,
        )
        fields.addWidget(
            preset_label,
            1,
            0,
        )
        fields.addWidget(
            self.upload_preset_input,
            1,
            1,
        )
        fields.setColumnStretch(
            1,
            1,
        )

        warning = QLabel(
            (
                "Use a dedicated unsigned preset from "
                "your own Cloudinary account. Never "
                "enter an API key or API secret."
            )
        )
        warning.setObjectName(
            "helpText"
        )
        warning.setWordWrap(
            True
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName(
            "helpText"
        )
        self.status_label.setWordWrap(
            True
        )

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        self.save_button = QPushButton(
            "Save artwork hosting"
        )
        self.save_button.setObjectName(
            "secondaryButton"
        )
        self.save_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.save_button.clicked.connect(
            self.save_preferences
        )

        self.disconnect_button = QPushButton(
            "Disconnect"
        )
        self.disconnect_button.setObjectName(
            "dangerButton"
        )
        self.disconnect_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.disconnect_button.clicked.connect(
            self.confirm_disconnect
        )

        buttons.addWidget(
            self.save_button
        )
        buttons.addWidget(
            self.disconnect_button
        )
        buttons.addStretch()

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(
            self.enabled_box
        )
        layout.addLayout(fields)
        layout.addWidget(warning)
        layout.addWidget(
            self.status_label
        )
        layout.addLayout(buttons)

    def load_preferences(self):
        preferences = (
            self.preferences_store.load()
        )

        self.cloud_name_input.setText(
            preferences.cloud_name
        )
        self.upload_preset_input.setText(
            preferences.upload_preset
        )

        self.refresh_status(
            preferences
        )

    def refresh_status(
        self,
        preferences: CloudinaryPreferences,
    ):
        self.enabled_box.blockSignals(
            True
        )
        self.enabled_box.setChecked(
            preferences.enabled
        )
        self.enabled_box.blockSignals(
            False
        )

        if preferences.enabled:
            message = (
                "Personal artwork hosting is enabled "
                "for this installation."
            )

        elif preferences.configured:
            message = (
                "Cloudinary is configured, but artwork "
                "hosting is currently disabled."
            )

        else:
            message = (
                "Not configured. Artwork remains on "
                "this device and Discord shows text only."
            )

        self.status_label.setText(
            message
        )

    def save_preferences(self):
        cloud_name = (
            self.cloud_name_input
            .text()
            .strip()
        )

        upload_preset = (
            self.upload_preset_input
            .text()
            .strip()
        )

        if not cloud_name or not upload_preset:
            message = (
                "Enter both a Cloudinary cloud name "
                "and unsigned upload preset."
            )

            self.status_label.setText(
                message
            )
            self.message_changed.emit(
                message
            )
            return

        preferences = (
            self.preferences_store.update(
                enabled=(
                    self.enabled_box.isChecked()
                ),
                cloud_name=cloud_name,
                upload_preset=upload_preset,
            )
        )

        if not preferences.configured:
            message = (
                "The Cloudinary settings were invalid."
            )

            self.status_label.setText(
                message
            )
            self.message_changed.emit(
                message
            )
            return

        self.cloud_name_input.setText(
            preferences.cloud_name
        )
        self.upload_preset_input.setText(
            preferences.upload_preset
        )

        self.refresh_status(
            preferences
        )

        if preferences.enabled:
            message = (
                "Personal artwork hosting saved "
                "and enabled."
            )
        else:
            message = (
                "Personal artwork hosting saved "
                "but disabled."
            )

        self.message_changed.emit(
            message
        )

    def confirm_disconnect(self):
        response = QMessageBox.question(
            self,
            "Disconnect Cloudinary",
            (
                "Remove the saved cloud name and upload "
                "preset from this computer?"
                "\n\n"
                "Existing uploads in your Cloudinary "
                "account will not be deleted."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if (
            response
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.disconnect_preferences()

    def disconnect_preferences(self):
        preferences = (
            self.preferences_store.disconnect()
        )

        self.cloud_name_input.clear()
        self.upload_preset_input.clear()

        self.refresh_status(
            preferences
        )

        message = (
            "Personal artwork hosting disconnected."
        )

        self.message_changed.emit(
            message
        )

    def reset_preferences(self):
        self.disconnect_preferences()
