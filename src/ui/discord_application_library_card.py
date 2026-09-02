from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.discord.application_library import (
    MAX_APPLICATION_NAME_LENGTH,
    BUILTIN_APPLICATION_ENTRY_ID,
    DiscordApplicationEntry,
    DiscordApplicationLibraryError,
    DiscordApplicationLibraryStore,
    validate_application_name,
)
from src.discord.identity_preferences import (
    APPLICATION_ID_MAX_LENGTH,
    validate_discord_application_id,
)


class DiscordApplicationEditorDialog(QDialog):
    def __init__(
        self,
        *,
        entry: DiscordApplicationEntry | None = None,
        parent=None,
    ):
        super().__init__(parent)

        if (
            entry is not None
            and not isinstance(
                entry,
                DiscordApplicationEntry,
            )
        ):
            raise TypeError(
                "entry must be a "
                "DiscordApplicationEntry or None."
            )

        if (
            entry is not None
            and entry.builtin
        ):
            raise DiscordApplicationLibraryError(
                "The built-in 03:37am application "
                "cannot be edited."
            )

        self.entry = entry

        self.setWindowTitle(
            "Edit Discord application"
            if entry is not None
            else "Add Discord application"
        )

        self.setModal(True)
        self.setMinimumWidth(440)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            18,
            18,
            18,
            18,
        )
        root.setSpacing(12)

        intro = QLabel(
            (
                "Give this Discord application a friendly "
                "name so it can be reused by Presences."
            )
        )
        intro.setObjectName(
            "cardDescription"
        )
        intro.setWordWrap(True)

        root.addWidget(intro)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setObjectName(
            "textField"
        )
        self.name_edit.setMaxLength(
            MAX_APPLICATION_NAME_LENGTH
        )
        self.name_edit.setClearButtonEnabled(
            True
        )
        self.name_edit.setPlaceholderText(
            "e.g. Sword Art Online"
        )

        self.application_id_edit = QLineEdit()
        self.application_id_edit.setObjectName(
            "textField"
        )
        self.application_id_edit.setMaxLength(
            APPLICATION_ID_MAX_LENGTH
        )
        self.application_id_edit.setClearButtonEnabled(
            True
        )
        self.application_id_edit.setPlaceholderText(
            "e.g. 123456789012345678"
        )

        form.addRow(
            "Name",
            self.name_edit,
        )

        form.addRow(
            "Application ID",
            self.application_id_edit,
        )

        root.addLayout(form)

        safety_help = QLabel(
            (
                "Discord Application IDs are public and "
                "safe to store. Never enter a Client Secret, "
                "bot token, or user token."
            )
        )
        safety_help.setObjectName(
            "helpText"
        )
        safety_help.setWordWrap(
            True
        )

        root.addWidget(
            safety_help
        )

        self.error_label = QLabel("")
        self.error_label.setObjectName(
            "fieldError"
        )
        self.error_label.setWordWrap(
            True
        )
        self.error_label.hide()

        root.addWidget(
            self.error_label
        )

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        self.save_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )

        self.save_button.setText(
            "Save changes"
            if entry is not None
            else "Add application"
        )

        self.buttons.accepted.connect(
            self._validate_and_accept
        )

        self.buttons.rejected.connect(
            self.reject
        )

        root.addWidget(
            self.buttons
        )

        if entry is not None:
            self.name_edit.setText(
                entry.name
            )

            self.application_id_edit.setText(
                entry.application_id
            )

        self.name_edit.setFocus()

    def validated_values(
        self,
    ) -> tuple[str, str]:
        name = validate_application_name(
            self.name_edit.text()
        )

        application_id = str(
            self.application_id_edit.text()
            or ""
        ).strip()

        validate_discord_application_id(
            application_id
        )

        return (
            name,
            application_id,
        )

    def _validate_and_accept(
        self,
    ):
        try:
            self.validated_values()
        except (
            DiscordApplicationLibraryError,
            ValueError,
        ) as error:
            self.error_label.setText(
                str(error)
            )
            self.error_label.show()
            return

        self.error_label.clear()
        self.error_label.hide()

        self.accept()


class DiscordApplicationRow(QFrame):
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(
        self,
        entry: DiscordApplicationEntry,
        parent=None,
    ):
        super().__init__(parent)

        if not isinstance(
            entry,
            DiscordApplicationEntry,
        ):
            raise TypeError(
                "entry must be a "
                "DiscordApplicationEntry."
            )

        self.entry = entry

        self.setObjectName(
            "settingsSubCard"
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(
            12,
            10,
            12,
            10,
        )
        root.setSpacing(12)

        text_column = QVBoxLayout()
        text_column.setSpacing(3)

        self.name_label = QLabel(
            entry.name
        )
        self.name_label.setObjectName(
            "fieldLabel"
        )

        self.application_id_label = QLabel(
            entry.application_id
        )
        self.application_id_label.setObjectName(
            "helpText"
        )
        self.application_id_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        text_column.addWidget(
            self.name_label
        )

        text_column.addWidget(
            self.application_id_label
        )

        root.addLayout(
            text_column,
            1,
        )

        self.builtin_label = None
        self.edit_button = None
        self.delete_button = None

        if entry.builtin:
            self.builtin_label = QLabel(
                "Built-in"
            )
            self.builtin_label.setObjectName(
                "helpText"
            )

            root.addWidget(
                self.builtin_label
            )

        else:
            self.edit_button = QPushButton(
                "Edit"
            )
            self.edit_button.setObjectName(
                "secondaryButton"
            )
            self.edit_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            self.delete_button = QPushButton(
                "Delete"
            )
            self.delete_button.setObjectName(
                "secondaryButton"
            )
            self.delete_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            self.edit_button.clicked.connect(
                lambda checked=False, value=entry.entry_id:
                self.edit_requested.emit(
                    value
                )
            )

            self.delete_button.clicked.connect(
                lambda checked=False, value=entry.entry_id:
                self.delete_requested.emit(
                    value
                )
            )

            root.addWidget(
                self.edit_button
            )

            root.addWidget(
                self.delete_button
            )


class DiscordApplicationLibrarySettingsCard(QFrame):
    message_changed = pyqtSignal(str)
    entries_changed = pyqtSignal()

    def __init__(
        self,
        *,
        application_store=None,
        parent=None,
    ):
        super().__init__(parent)

        self.application_store = (
            application_store
            if application_store is not None
            else DiscordApplicationLibraryStore()
        )

        self.entry_rows = {}

        self.setObjectName(
            "settingsCard"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        root.setSpacing(10)

        title = QLabel(
            "Discord Applications"
        )
        title.setObjectName(
            "cardTitle"
        )

        description = QLabel(
            (
                "Save Discord applications once, then reuse "
                "them across custom Presences. The built-in "
                "03:37am Music application is always available."
            )
        )
        description.setObjectName(
            "cardDescription"
        )
        description.setWordWrap(
            True
        )

        root.addWidget(
            title
        )

        root.addWidget(
            description
        )

        self.entries_container = QWidget()
        self.entries_layout = QVBoxLayout(
            self.entries_container
        )
        self.entries_layout.setContentsMargins(
            0,
            2,
            0,
            2,
        )
        self.entries_layout.setSpacing(
            8
        )

        root.addWidget(
            self.entries_container
        )

        button_row = QHBoxLayout()
        button_row.setSpacing(
            10
        )

        self.add_button = QPushButton(
            "Add Discord Application"
        )
        self.add_button.setObjectName(
            "primaryButton"
        )
        self.add_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button_row.addWidget(
            self.add_button
        )
        button_row.addStretch()

        root.addLayout(
            button_row
        )

        safety_help = QLabel(
            (
                "Only public Discord Application IDs belong "
                "here. Never enter a Client Secret, bot token, "
                "or user token."
            )
        )
        safety_help.setObjectName(
            "helpText"
        )
        safety_help.setWordWrap(
            True
        )

        root.addWidget(
            safety_help
        )

        self.add_button.clicked.connect(
            self.open_add_dialog
        )

        self.refresh_from_store()

    def _clear_rows(
        self,
    ):
        while (
            self.entries_layout.count()
            > 0
        ):
            item = (
                self.entries_layout.takeAt(
                    0
                )
            )

            widget = item.widget()

            if widget is not None:
                widget.hide()
                widget.deleteLater()

        self.entry_rows = {}

    def refresh_from_store(
        self,
    ) -> list[
        DiscordApplicationEntry
    ]:
        try:
            entries = list(
                self.application_store
                .list_entries()
            )
        except (
            DiscordApplicationLibraryError,
            OSError,
        ):
            entries = []

            self.message_changed.emit(
                "Discord applications could not be loaded."
            )

        self._clear_rows()

        for entry in entries:
            row = DiscordApplicationRow(
                entry,
                self.entries_container,
            )

            row.edit_requested.connect(
                self.open_edit_dialog
            )

            row.delete_requested.connect(
                self.confirm_delete_entry
            )

            self.entries_layout.addWidget(
                row
            )

            self.entry_rows[
                entry.entry_id
            ] = row

        return entries

    def create_entry(
        self,
        *,
        name: str,
        application_id: str,
    ) -> DiscordApplicationEntry | None:
        try:
            entry = (
                self.application_store.create(
                    name=name,
                    application_id=(
                        application_id
                    ),
                )
            )
        except (
            DiscordApplicationLibraryError,
            OSError,
        ) as error:
            self.message_changed.emit(
                str(error)
                or (
                    "Discord application "
                    "could not be added."
                )
            )
            return None

        self.refresh_from_store()

        self.entries_changed.emit()

        self.message_changed.emit(
            (
                f'Discord application "{entry.name}" '
                "added."
            )
        )

        return entry

    def update_entry(
        self,
        entry_id: str,
        *,
        name: str,
        application_id: str,
    ) -> DiscordApplicationEntry | None:
        try:
            entry = (
                self.application_store.update(
                    entry_id,
                    name=name,
                    application_id=(
                        application_id
                    ),
                )
            )
        except (
            DiscordApplicationLibraryError,
            OSError,
        ) as error:
            self.message_changed.emit(
                str(error)
                or (
                    "Discord application "
                    "could not be updated."
                )
            )
            return None

        self.refresh_from_store()

        self.entries_changed.emit()

        self.message_changed.emit(
            (
                f'Discord application "{entry.name}" '
                "updated."
            )
        )

        return entry

    def delete_entry(
        self,
        entry_id: str,
    ) -> bool:
        if (
            str(entry_id or "").strip()
            == BUILTIN_APPLICATION_ENTRY_ID
        ):
            self.message_changed.emit(
                (
                    "The built-in 03:37am "
                    "application cannot be deleted."
                )
            )
            return False

        entry = (
            self.application_store.get(
                entry_id
            )
        )

        try:
            deleted = (
                self.application_store.delete(
                    entry_id
                )
            )
        except (
            DiscordApplicationLibraryError,
            OSError,
        ) as error:
            self.message_changed.emit(
                str(error)
                or (
                    "Discord application "
                    "could not be deleted."
                )
            )
            return False

        if not deleted:
            self.message_changed.emit(
                "Discord application was not found."
            )
            return False

        self.refresh_from_store()

        self.entries_changed.emit()

        display_name = (
            entry.name
            if entry is not None
            else "Discord application"
        )

        self.message_changed.emit(
            f'"{display_name}" deleted.'
        )

        return True

    def open_add_dialog(
        self,
    ):
        dialog = (
            DiscordApplicationEditorDialog(
                parent=self,
            )
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        name, application_id = (
            dialog.validated_values()
        )

        self.create_entry(
            name=name,
            application_id=application_id,
        )

    def open_edit_dialog(
        self,
        entry_id: str,
    ):
        entry = (
            self.application_store.get(
                entry_id
            )
        )

        if entry is None:
            self.message_changed.emit(
                "Discord application was not found."
            )
            return

        if entry.builtin:
            self.message_changed.emit(
                (
                    "The built-in 03:37am "
                    "application cannot be edited."
                )
            )
            return

        dialog = (
            DiscordApplicationEditorDialog(
                entry=entry,
                parent=self,
            )
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        name, application_id = (
            dialog.validated_values()
        )

        self.update_entry(
            entry.entry_id,
            name=name,
            application_id=application_id,
        )

    def confirm_delete_entry(
        self,
        entry_id: str,
    ):
        entry = (
            self.application_store.get(
                entry_id
            )
        )

        if entry is None:
            self.message_changed.emit(
                "Discord application was not found."
            )
            return

        if entry.builtin:
            self.message_changed.emit(
                (
                    "The built-in 03:37am "
                    "application cannot be deleted."
                )
            )
            return

        answer = QMessageBox.question(
            self,
            "Delete Discord application",
            (
                f'Delete "{entry.name}" from your '
                "Discord Application Library?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.delete_entry(
            entry.entry_id
        )
