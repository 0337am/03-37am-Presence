from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
)
from PyQt6.QtGui import (
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QKeySequenceEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from src.system.media_hotkey_preferences import (
    MediaHotkeyPreferences,
    MediaHotkeyPreferencesStore,
)
from src.system.media_hotkeys import (
    ACTION_NEXT,
    ACTION_PLAY_PAUSE,
    ACTION_PREVIOUS,
    ACTION_REPEAT,
    ACTION_SEEK_BACKWARD,
    ACTION_SEEK_FORWARD,
    ACTION_SHUFFLE,
)
from src.ui.hotkey_sequence import (
    SUPPORTED_KEY_HELP,
    binding_from_sequence,
    sequence_from_binding,
)


ACTION_LABELS = (
    (
        ACTION_PLAY_PAUSE,
        "Play / Pause",
    ),
    (
        ACTION_NEXT,
        "Next track",
    ),
    (
        ACTION_PREVIOUS,
        "Previous track",
    ),
    (
        ACTION_SHUFFLE,
        "Toggle shuffle",
    ),
    (
        ACTION_REPEAT,
        "Cycle repeat",
    ),
    (
        ACTION_SEEK_FORWARD,
        "Seek forward",
    ),
    (
        ACTION_SEEK_BACKWARD,
        "Seek backward",
    ),
)


class MediaHotkeySettingsCard(
    QFrame
):
    def __init__(
        self,
        *,
        preference_store=None,
        status_callback=None,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.setObjectName(
            "settingsCard"
        )

        self.preference_store = (
            preference_store
            if preference_store is not None
            else MediaHotkeyPreferencesStore()
        )

        self.status_callback = (
            status_callback
        )

        self.reload_callback = None

        self.editors = {}
        self.clear_buttons = {}

        self._build_ui()
        self.refresh_from_store()

    def _build_ui(
        self,
    ):
        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            18,
            16,
            18,
            18,
        )

        layout.setSpacing(
            10
        )

        title = QLabel(
            "Global Media Hotkeys"
        )

        title.setObjectName(
            "cardTitle"
        )

        description = QLabel(
            (
                "Control the active Windows media session "
                "from anywhere, including while 03:37am "
                "Presence is hidden in the system tray."
            )
        )

        description.setObjectName(
            "cardDescription"
        )

        description.setWordWrap(
            True
        )

        self.enabled_box = (
            QCheckBox(
                "Enable global media hotkeys"
            )
        )

        help_label = QLabel(
            SUPPORTED_KEY_HELP
        )

        help_label.setObjectName(
            "helpText"
        )

        help_label.setWordWrap(
            True
        )

        seek_row = QHBoxLayout()

        seek_row.setSpacing(
            10
        )

        seek_label = QLabel(
            "Seek distance"
        )

        seek_label.setObjectName(
            "fieldLabel"
        )

        self.seek_seconds_box = (
            QSpinBox()
        )

        self.seek_seconds_box.setRange(
            1,
            300,
        )

        self.seek_seconds_box.setSuffix(
            " seconds"
        )

        self.seek_seconds_box.setMinimumWidth(
            130
        )

        seek_row.addWidget(
            seek_label
        )

        seek_row.addStretch()

        seek_row.addWidget(
            self.seek_seconds_box
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            description
        )

        layout.addWidget(
            self.enabled_box
        )

        layout.addWidget(
            help_label
        )

        layout.addLayout(
            seek_row
        )

        for (
            action,
            label_text,
        ) in ACTION_LABELS:
            row = QHBoxLayout()

            row.setSpacing(
                10
            )

            label = QLabel(
                label_text
            )

            label.setObjectName(
                "fieldLabel"
            )

            label.setMinimumWidth(
                120
            )

            editor = (
                QKeySequenceEdit()
            )

            editor.setMaximumSequenceLength(
                1
            )

            editor.setMinimumWidth(
                210
            )

            clear_button = (
                QPushButton(
                    "Clear"
                )
            )

            clear_button.setObjectName(
                "secondaryButton"
            )

            clear_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            clear_button.clicked.connect(
                lambda checked=False,
                selected_action=action:
                self.clear_action_field(
                    selected_action
                )
            )

            self.editors[
                action
            ] = editor

            self.clear_buttons[
                action
            ] = clear_button

            row.addWidget(
                label
            )

            row.addStretch()

            row.addWidget(
                editor
            )

            row.addWidget(
                clear_button
            )

            layout.addLayout(
                row
            )

        button_row = (
            QHBoxLayout()
        )

        button_row.setSpacing(
            8
        )

        self.apply_button = (
            QPushButton(
                "Apply hotkeys"
            )
        )

        self.apply_button.setObjectName(
            "secondaryButton"
        )

        self.apply_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.apply_button.clicked.connect(
            self.apply_changes
        )

        self.clear_all_button = (
            QPushButton(
                "Clear all fields"
            )
        )

        self.clear_all_button.setObjectName(
            "secondaryButton"
        )

        self.clear_all_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.clear_all_button.clicked.connect(
            self.clear_all_fields
        )

        button_row.addWidget(
            self.apply_button
        )

        button_row.addWidget(
            self.clear_all_button
        )

        button_row.addStretch()

        layout.addLayout(
            button_row
        )

        self.feedback_label = QLabel(
            ""
        )

        self.feedback_label.setObjectName(
            "helpText"
        )

        self.feedback_label.setWordWrap(
            True
        )

        layout.addWidget(
            self.feedback_label
        )

    def set_reload_callback(
        self,
        callback,
    ):
        if (
            callback is not None
            and not callable(
                callback
            )
        ):
            raise TypeError(
                "Media hotkey reload callback "
                "must be callable or None."
            )

        self.reload_callback = (
            callback
        )

    def _set_feedback(
        self,
        message,
    ):
        message = str(
            message or ""
        ).strip()

        self.feedback_label.setText(
            message
        )

        if callable(
            self.status_callback
        ):
            self.status_callback(
                message
            )

    def refresh_from_store(
        self,
    ):
        preferences = (
            self.preference_store.load()
        )

        self.enabled_box.setChecked(
            preferences.enabled
        )

        self.seek_seconds_box.setValue(
            max(
                1,
                int(
                    round(
                        preferences.seek_seconds
                    )
                ),
            )
        )

        for (
            action,
            editor,
        ) in self.editors.items():
            binding = (
                preferences.bindings.get(
                    action
                )
            )

            if binding is None:
                editor.clear()
            else:
                editor.setKeySequence(
                    sequence_from_binding(
                        binding
                    )
                )

        return preferences

    def preferences_from_ui(
        self,
    ) -> MediaHotkeyPreferences:
        bindings = {}

        for (
            action,
            editor,
        ) in self.editors.items():
            binding = (
                binding_from_sequence(
                    editor.keySequence()
                )
            )

            if binding is not None:
                bindings[
                    action
                ] = binding

        return MediaHotkeyPreferences(
            enabled=(
                self.enabled_box.isChecked()
            ),
            seek_seconds=float(
                self.seek_seconds_box.value()
            ),
            bindings=bindings,
        )

    def reload_runtime(
        self,
    ) -> bool:
        return self._reload_runtime()

    def _reload_runtime(
        self,
    ) -> bool:
        callback = (
            self.reload_callback
        )

        if callback is None:
            return True

        try:
            result = callback()

        except Exception as error:
            print(
                "Media hotkey Settings "
                "reload error:",
                error,
            )

            return False

        return result is not False

    def _commit_preferences(
        self,
        preferences,
        *,
        success_message,
    ) -> bool:
        previous = (
            self.preference_store.load()
        )

        try:
            self.preference_store.save(
                preferences
            )

        except Exception as error:
            self._set_feedback(
                "Could not save media hotkeys: "
                + str(
                    error
                )
            )

            return False

        if not self._reload_runtime():
            try:
                self.preference_store.save(
                    previous
                )

                self._reload_runtime()

            except Exception as error:
                print(
                    "Media hotkey Settings "
                    "rollback error:",
                    error,
                )

            self.refresh_from_store()

            self._set_feedback(
                (
                    "Those shortcuts could not be "
                    "registered by Windows. Your "
                    "previous hotkey configuration "
                    "was restored."
                )
            )

            return False

        self.refresh_from_store()

        self._set_feedback(
            success_message
        )

        return True

    def apply_changes(
        self,
        checked=False,
    ) -> bool:
        try:
            preferences = (
                self.preferences_from_ui()
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            self._set_feedback(
                str(
                    error
                )
            )

            return False

        if (
            preferences.enabled
            and not preferences.bindings
        ):
            message = (
                "Global media hotkeys are enabled, "
                "but no shortcuts are assigned."
            )
        elif preferences.enabled:
            message = (
                "Global media hotkeys applied."
            )
        else:
            message = (
                "Global media hotkeys disabled."
            )

        return self._commit_preferences(
            preferences,
            success_message=message,
        )

    def clear_action_field(
        self,
        action,
    ):
        editor = (
            self.editors.get(
                action
            )
        )

        if editor is None:
            return False

        editor.clear()

        self._set_feedback(
            "Shortcut field cleared. "
            "Click Apply hotkeys to save."
        )

        return True

    def clear_all_fields(
        self,
        checked=False,
    ):
        for editor in (
            self.editors.values()
        ):
            editor.clear()

        self._set_feedback(
            "All shortcut fields cleared. "
            "Click Apply hotkeys to save."
        )

    def reset_preferences(
        self,
    ) -> bool:
        return self._commit_preferences(
            MediaHotkeyPreferences(),
            success_message=(
                "Global media hotkeys reset "
                "to default."
            ),
        )
