from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from src.discord.identity_preferences import (
    IDENTITY_MODE_CUSTOM,
    IDENTITY_MODE_DEFAULT,
    DiscordIdentityPreferences,
    DiscordIdentityPreferencesStore,
)


class DiscordIdentitySettingsCard(QFrame):
    message_changed = pyqtSignal(str)

    def __init__(
        self,
        *,
        preference_store=None,
        runtime=None,
        parent=None,
    ):
        super().__init__(parent)

        self.preference_store = (
            preference_store
            if preference_store is not None
            else DiscordIdentityPreferencesStore()
        )

        self.runtime = runtime
        self._preferences = (
            DiscordIdentityPreferences()
        )

        self.setObjectName(
            "settingsCard"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        layout.setSpacing(10)

        title = QLabel(
            "Presence Identity"
        )
        title.setObjectName(
            "cardTitle"
        )

        description = QLabel(
            (
                "Choose which Discord application "
                "owns your Rich Presence."
            )
        )
        description.setObjectName(
            "cardDescription"
        )
        description.setWordWrap(
            True
        )

        self.default_box = QCheckBox(
            "Use 03:37am Presence"
        )

        self.custom_box = QCheckBox(
            "Use a custom Discord application"
        )

        self.identity_group = QButtonGroup(
            self
        )
        self.identity_group.setExclusive(
            True
        )
        self.identity_group.addButton(
            self.default_box
        )
        self.identity_group.addButton(
            self.custom_box
        )

        field_label = QLabel(
            "Application ID"
        )
        field_label.setObjectName(
            "fieldLabel"
        )

        self.application_id_field = (
            QLineEdit()
        )
        self.application_id_field.setObjectName(
            "textField"
        )
        self.application_id_field.setMaxLength(
            22
        )
        self.application_id_field.setPlaceholderText(
            "e.g. 123456789012345678"
        )

        safety_help = QLabel(
            (
                "Your Discord Application ID is public "
                "and safe to store. Never enter a Client "
                "Secret, bot token, or user token here."
            )
        )
        safety_help.setObjectName(
            "helpText"
        )
        safety_help.setWordWrap(
            True
        )

        button_row = QHBoxLayout()
        button_row.setSpacing(
            10
        )

        self.apply_button = QPushButton(
            "Apply Identity"
        )
        self.apply_button.setObjectName(
            "primaryButton"
        )
        self.apply_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button_row.addWidget(
            self.apply_button
        )
        button_row.addStretch()

        layout.addWidget(
            title
        )
        layout.addWidget(
            description
        )
        layout.addSpacing(
            2
        )
        layout.addWidget(
            self.default_box
        )
        layout.addWidget(
            self.custom_box
        )
        layout.addSpacing(
            2
        )
        layout.addWidget(
            field_label
        )
        layout.addWidget(
            self.application_id_field
        )
        layout.addWidget(
            safety_help
        )
        layout.addLayout(
            button_row
        )

        self.custom_box.toggled.connect(
            self._sync_custom_controls
        )

        self.apply_button.clicked.connect(
            self.apply_preferences
        )

        self.refresh_from_store()

    def _sync_custom_controls(
        self,
        _checked=False,
    ):
        custom_enabled = (
            self.custom_box.isChecked()
        )

        self.application_id_field.setEnabled(
            custom_enabled
        )

    def _apply_preferences_to_ui(
        self,
        preferences: DiscordIdentityPreferences,
    ):
        self._preferences = preferences

        custom_mode = (
            preferences.normalized_mode
            == IDENTITY_MODE_CUSTOM
        )

        self.default_box.blockSignals(
            True
        )
        self.custom_box.blockSignals(
            True
        )

        self.default_box.setChecked(
            not custom_mode
        )
        self.custom_box.setChecked(
            custom_mode
        )

        self.default_box.blockSignals(
            False
        )
        self.custom_box.blockSignals(
            False
        )

        self.application_id_field.setText(
            preferences.custom_application_id
        )

        self._sync_custom_controls()

    def refresh_from_store(
        self,
    ) -> DiscordIdentityPreferences:
        preferences = (
            self.preference_store.load()
        )

        self._apply_preferences_to_ui(
            preferences
        )

        return preferences

    def apply_preferences(
        self,
    ) -> bool:
        custom_mode = (
            self.custom_box.isChecked()
        )

        mode = (
            IDENTITY_MODE_CUSTOM
            if custom_mode
            else IDENTITY_MODE_DEFAULT
        )

        custom_application_id = (
            self.application_id_field.text()
            .strip()
        )

        preferences = (
            DiscordIdentityPreferences(
                mode=mode,
                custom_application_id=(
                    custom_application_id
                ),
            )
        )

        try:
            saved = (
                self.preference_store.save(
                    preferences
                )
            )
        except ValueError as error:
            self.message_changed.emit(
                str(error)
            )
            return False
        except OSError:
            self.message_changed.emit(
                (
                    "Discord identity settings "
                    "could not be saved."
                )
            )
            return False

        self._apply_preferences_to_ui(
            saved
        )

        request_identity = getattr(
            self.runtime,
            "request_client_id",
            None,
        )

        if callable(
            request_identity
        ):
            request_identity(
                saved.resolved_application_id
            )

            if (
                saved.normalized_mode
                == IDENTITY_MODE_CUSTOM
            ):
                message = (
                    "Custom Discord identity saved. "
                    "Discord is reconnecting."
                )
            else:
                message = (
                    "Using the 03:37am Presence "
                    "Discord identity."
                )
        else:
            message = (
                "Discord identity saved. Restart "
                "03:37am Presence to apply it."
            )

        self.message_changed.emit(
            message
        )

        return True

    def reset_preferences(
        self,
    ) -> DiscordIdentityPreferences:
        preferences = (
            self.preference_store.reset()
        )

        self._apply_preferences_to_ui(
            preferences
        )

        request_identity = getattr(
            self.runtime,
            "request_client_id",
            None,
        )

        if callable(
            request_identity
        ):
            request_identity(
                preferences.resolved_application_id
            )

        self.message_changed.emit(
            (
                "Discord presence identity reset "
                "to 03:37am Presence."
            )
        )

        return preferences
