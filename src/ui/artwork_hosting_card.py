from __future__ import annotations

import binascii
import struct
import threading
import uuid
import zlib

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
from src.artwork.uploader import (
    ArtworkUploader,
)


class _ConnectionTestPreferencesStore:
    """
    Supplies temporary, enabled preferences to one
    connection-test uploader without saving them.
    """

    def __init__(
        self,
        cloud_name: str,
        upload_preset: str,
    ):
        self._preferences = CloudinaryPreferences(
            enabled=True,
            cloud_name=cloud_name,
            upload_preset=upload_preset,
        )

    def load(self) -> CloudinaryPreferences:
        return self._preferences


class ArtworkHostingCard(QFrame):
    """
    Optional Bring Your Own Cloudinary settings card.

    The card stores only a cloud name and unsigned
    upload preset. API keys and API secrets are not
    requested or supported.
    """

    message_changed = pyqtSignal(str)
    connection_test_finished = pyqtSignal(
        bool,
        str,
    )

    def __init__(
        self,
        preferences_store=None,
        uploader_factory=None,
        parent=None,
    ):
        super().__init__(parent)

        self.preferences_store = (
            preferences_store
            or CloudinaryPreferencesStore()
        )

        self.uploader_factory = (
            uploader_factory
            or ArtworkUploader
        )

        self._test_in_progress = False
        self._test_thread = None

        self.connection_test_finished.connect(
            self._handle_connection_test_result
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

        test_note = QLabel(
            (
                "Testing uploads one tiny transparent "
                "pixel to your Cloudinary account. "
                "The test image is not deleted "
                "automatically."
            )
        )
        test_note.setObjectName(
            "helpText"
        )
        test_note.setWordWrap(
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

        self.test_button = QPushButton(
            "Test connection"
        )
        self.test_button.setObjectName(
            "secondaryButton"
        )
        self.test_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.test_button.clicked.connect(
            self.test_connection
        )

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
            self.test_button
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
        layout.addWidget(test_note)
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

    def test_connection(self):
        if self._test_in_progress:
            return

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
                "and unsigned upload preset before "
                "testing."
            )

            self.status_label.setText(
                message
            )
            self.message_changed.emit(
                message
            )
            return

        try:
            test_store = (
                _ConnectionTestPreferencesStore(
                    cloud_name=cloud_name,
                    upload_preset=upload_preset,
                )
            )

            uploader = self.uploader_factory(
                preferences_store=test_store
            )

            test_image = (
                self._make_connection_test_png()
            )

        except Exception as error:
            message = (
                "The connection test could not start: "
                f"{error}"
            )

            self.status_label.setText(
                message
            )
            self.message_changed.emit(
                message
            )
            return

        self._test_in_progress = True
        self._set_test_controls_enabled(
            False
        )

        message = (
            "Testing Cloudinary connection... "
            "Uploading one tiny transparent pixel."
        )

        self.status_label.setText(
            message
        )
        self.message_changed.emit(
            message
        )

        thread = threading.Thread(
            target=self._run_connection_test,
            args=(
                uploader,
                test_image,
            ),
            name=(
                "ArtworkHostingConnectionTest"
            ),
            daemon=True,
        )

        self._test_thread = thread
        thread.start()

    def _run_connection_test(
        self,
        uploader,
        test_image: bytes,
    ):
        try:
            artwork_url = (
                uploader.get_or_upload(
                    test_image
                )
            )

            if artwork_url:
                success = True
                message = (
                    "Connection successful. "
                    "Cloudinary accepted the tiny test "
                    "image. Click Save artwork hosting "
                    "to keep these settings."
                )

            else:
                success = False
                message = (
                    getattr(
                        uploader,
                        "last_error",
                        "",
                    )
                    or (
                        "Cloudinary did not accept the "
                        "test image. Check the cloud "
                        "name and unsigned preset."
                    )
                )

        except Exception as error:
            success = False
            message = (
                "Cloudinary connection test failed: "
                f"{error}"
            )

        try:
            self.connection_test_finished.emit(
                success,
                message,
            )
        except RuntimeError:
            pass

    def _handle_connection_test_result(
        self,
        success: bool,
        message: str,
    ):
        self._test_in_progress = False
        self._test_thread = None

        self._set_test_controls_enabled(
            True
        )

        self.status_label.setText(
            message
        )
        self.message_changed.emit(
            message
        )

    def _set_test_controls_enabled(
        self,
        enabled: bool,
    ):
        for control in (
            self.enabled_box,
            self.cloud_name_input,
            self.upload_preset_input,
            self.test_button,
            self.save_button,
            self.disconnect_button,
        ):
            control.setEnabled(
                enabled
            )

    @classmethod
    def _make_connection_test_png(
        cls,
    ) -> bytes:
        signature = (
            b"\x89PNG\r\n\x1a\n"
        )

        header = struct.pack(
            ">IIBBBBB",
            1,
            1,
            8,
            6,
            0,
            0,
            0,
        )

        comment = (
            b"Comment\x00"
            + (
                "0337am Presence connection test "
                + uuid.uuid4().hex
            ).encode("ascii")
        )

        pixel_data = (
            b"\x00\xff\xff\xff\x00"
        )

        return b"".join(
            (
                signature,
                cls._png_chunk(
                    b"IHDR",
                    header,
                ),
                cls._png_chunk(
                    b"tEXt",
                    comment,
                ),
                cls._png_chunk(
                    b"IDAT",
                    zlib.compress(
                        pixel_data
                    ),
                ),
                cls._png_chunk(
                    b"IEND",
                    b"",
                ),
            )
        )

    @staticmethod
    def _png_chunk(
        chunk_type: bytes,
        data: bytes,
    ) -> bytes:
        checksum = (
            binascii.crc32(
                chunk_type + data
            )
            & 0xFFFFFFFF
        )

        return b"".join(
            (
                struct.pack(
                    ">I",
                    len(data),
                ),
                chunk_type,
                data,
                struct.pack(
                    ">I",
                    checksum,
                ),
            )
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
