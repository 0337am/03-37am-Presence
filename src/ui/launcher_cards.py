from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ui.custom_cards import (
    LAUNCHER_TARGET_APPLICATION,
    LAUNCHER_TARGET_FILE,
    LAUNCHER_TARGET_FOLDER,
    MAX_BUTTON_LABEL_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_ICON_LENGTH,
    MAX_LAUNCHER_TARGET_LENGTH,
    MAX_TITLE_LENGTH,
    LauncherCardData,
    create_launcher_card,
    normalize_launcher_target,
)
from src.ui.launcher_card_images import (
    cached_launcher_card_image_path,
    import_launcher_card_image,
)


_SCRIPT_SUFFIXES = frozenset(
    {
        ".bat",
        ".cmd",
        ".js",
        ".jse",
        ".ps1",
        ".vbs",
        ".vbe",
        ".wsf",
        ".wsh",
    }
)

_KIND_LABELS = {
    LAUNCHER_TARGET_APPLICATION: "Application",
    LAUNCHER_TARGET_FILE: "File",
    LAUNCHER_TARGET_FOLDER: "Folder",
}

_KIND_ICONS = {
    LAUNCHER_TARGET_APPLICATION: "??",
    LAUNCHER_TARGET_FILE: "??",
    LAUNCHER_TARGET_FOLDER: "??",
}


class LauncherCardDialog(QDialog):
    def __init__(
        self,
        parent=None,
        card: LauncherCardData | None = None,
        *,
        image_root: Path | str | None = None,
    ):
        super().__init__(parent)

        self._editing_card = card
        self._result_card = None
        self._image_root = image_root
        self._image_asset = (
            card.image_asset
            if card is not None
            else ""
        )
        self._pending_image_path = ""

        self.setWindowTitle(
            "Edit Launcher card"
            if card is not None
            else "Add Launcher card"
        )
        self.setModal(True)
        self.setMinimumWidth(500)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            18,
            18,
            18,
            18,
        )
        root.setSpacing(12)

        intro = QLabel(
            "Create a local shortcut for an application, "
            "file, or folder. Target paths stay on this "
            "device and are excluded from portable backups."
        )
        intro.setObjectName(
            "launcherCardDialogIntro"
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(9)

        self.target_kind_combo = QComboBox()
        self.target_kind_combo.addItem(
            "Application",
            LAUNCHER_TARGET_APPLICATION,
        )
        self.target_kind_combo.addItem(
            "File",
            LAUNCHER_TARGET_FILE,
        )
        self.target_kind_combo.addItem(
            "Folder",
            LAUNCHER_TARGET_FOLDER,
        )

        self.target_edit = QLineEdit()
        self.target_edit.setMaxLength(
            MAX_LAUNCHER_TARGET_LENGTH
        )
        self.target_edit.setClearButtonEnabled(
            True
        )

        self.browse_button = QPushButton(
            "Browse..."
        )
        self.browse_button.setObjectName(
            "launcherCardBrowseButton"
        )
        self.browse_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        target_controls = QWidget()
        target_layout = QHBoxLayout(
            target_controls
        )
        target_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        target_layout.setSpacing(7)
        target_layout.addWidget(
            self.target_edit,
            stretch=1,
        )
        target_layout.addWidget(
            self.browse_button
        )

        self.target_status = QLabel("")
        self.target_status.setObjectName(
            "launcherCardTargetStatus"
        )
        self.target_status.setWordWrap(True)

        target_group = QWidget()
        target_group_layout = QVBoxLayout(
            target_group
        )
        target_group_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        target_group_layout.setSpacing(5)
        target_group_layout.addWidget(
            target_controls
        )
        target_group_layout.addWidget(
            self.target_status
        )

        self.title_edit = QLineEdit()
        self.title_edit.setMaxLength(
            MAX_TITLE_LENGTH
        )
        self.title_edit.setPlaceholderText(
            "Optional, uses the target name when blank"
        )
        self.title_edit.setClearButtonEnabled(
            True
        )

        self.icon_edit = QLineEdit()
        self.icon_edit.setMaxLength(
            MAX_ICON_LENGTH
        )
        self.icon_edit.setPlaceholderText(
            "Optional emoji"
        )
        self.icon_edit.setClearButtonEnabled(
            True
        )

        self.image_preview = QLabel("")
        self.image_preview.setObjectName(
            "launcherCardImagePreview"
        )
        self.image_preview.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.image_preview.setFixedSize(
            54,
            54,
        )
        self.image_preview.setFrameShape(
            QFrame.Shape.StyledPanel
        )

        self.choose_image_button = QPushButton(
            "Choose image..."
        )
        self.choose_image_button.setObjectName(
            "launcherCardChooseImageButton"
        )
        self.choose_image_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.remove_image_button = QPushButton(
            "Remove"
        )
        self.remove_image_button.setObjectName(
            "launcherCardRemoveImageButton"
        )
        self.remove_image_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        image_buttons = QHBoxLayout()
        image_buttons.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        image_buttons.setSpacing(7)
        image_buttons.addWidget(
            self.choose_image_button
        )
        image_buttons.addWidget(
            self.remove_image_button
        )
        image_buttons.addStretch()

        self.image_status = QLabel("")
        self.image_status.setObjectName(
            "launcherCardImageStatus"
        )
        self.image_status.setWordWrap(True)

        image_details = QVBoxLayout()
        image_details.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        image_details.setSpacing(5)
        image_details.addLayout(
            image_buttons
        )
        image_details.addWidget(
            self.image_status
        )

        self.image_controls = QWidget()
        image_layout = QHBoxLayout(
            self.image_controls
        )
        image_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        image_layout.setSpacing(9)
        image_layout.addWidget(
            self.image_preview
        )
        image_layout.addLayout(
            image_details,
            stretch=1,
        )

        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText(
            "Optional description shown on larger cards"
        )
        self.description_edit.setMaximumHeight(
            96
        )

        self.button_label_edit = QLineEdit()
        self.button_label_edit.setMaxLength(
            MAX_BUTTON_LABEL_LENGTH
        )
        self.button_label_edit.setPlaceholderText(
            "Open"
        )
        self.button_label_edit.setClearButtonEnabled(
            True
        )

        self.accent_edit = QLineEdit()
        self.accent_edit.setMaxLength(7)
        self.accent_edit.setPlaceholderText(
            "Optional #RRGGBB"
        )
        self.accent_edit.setClearButtonEnabled(
            True
        )

        form.addRow(
            "Target type",
            self.target_kind_combo,
        )
        form.addRow(
            "Local target",
            target_group,
        )
        form.addRow(
            "Title",
            self.title_edit,
        )
        form.addRow(
            "Icon or emoji",
            self.icon_edit,
        )
        form.addRow(
            "Card image",
            self.image_controls,
        )
        form.addRow(
            "Description",
            self.description_edit,
        )
        form.addRow(
            "Button label",
            self.button_label_edit,
        )
        form.addRow(
            "Accent colour",
            self.accent_edit,
        )

        root.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setObjectName(
            "launcherCardDialogError"
        )
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        root.addWidget(self.error_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        ok_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )
        ok_button.setText(
            "Save changes"
            if card is not None
            else "Add card"
        )

        self.buttons.accepted.connect(
            self._validate_and_accept
        )
        self.buttons.rejected.connect(
            self.reject
        )

        root.addWidget(self.buttons)

        if card is not None:
            kind_index = (
                self.target_kind_combo.findData(
                    card.target_kind
                )
            )

            if kind_index >= 0:
                self.target_kind_combo.setCurrentIndex(
                    kind_index
                )

            self.target_edit.setText(
                card.target
            )
            self.title_edit.setText(
                card.title
            )
            self.icon_edit.setText(
                card.icon
            )
            self.description_edit.setPlainText(
                card.description
            )
            self.button_label_edit.setText(
                card.button_label
            )
            self.accent_edit.setText(
                card.accent
            )
        else:
            self.button_label_edit.setText(
                "Open"
            )

        self.target_kind_combo.currentIndexChanged.connect(
            self._target_kind_changed
        )
        self.target_edit.textChanged.connect(
            self._refresh_target_feedback
        )
        self.browse_button.clicked.connect(
            self._browse_target
        )
        self.choose_image_button.clicked.connect(
            self._choose_card_image
        )
        self.remove_image_button.clicked.connect(
            self._remove_card_image
        )

        self._refresh_image_preview()
        self._target_kind_changed()
        self.target_edit.setFocus()

    def _image_preview_path(
        self,
    ) -> Path | None:
        if self._pending_image_path:
            return Path(
                self._pending_image_path
            )

        return cached_launcher_card_image_path(
            self._image_asset,
            self._image_root,
        )

    def _refresh_image_preview(self):
        path = self._image_preview_path()
        pixmap = (
            QPixmap(str(path))
            if path is not None
            else QPixmap()
        )

        if not pixmap.isNull():
            self.image_preview.setText("")
            self.image_preview.setPixmap(
                pixmap.scaled(
                    44,
                    44,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        else:
            self.image_preview.setPixmap(
                QPixmap()
            )
            self.image_preview.setText(
                self.icon_edit.text().strip()
                or "IMG"
            )

        has_selection = bool(
            self._pending_image_path
            or self._image_asset
        )

        self.remove_image_button.setEnabled(
            has_selection
        )

        if self._pending_image_path:
            if pixmap.isNull():
                message = (
                    "The selected file cannot be "
                    "previewed. It will be fully "
                    "validated when saved."
                )
            else:
                message = (
                    "Selected image. It will be copied "
                    "into local app storage when the "
                    "card is saved."
                )

        elif self._image_asset:
            if path is None or pixmap.isNull():
                message = (
                    "The saved image is missing. "
                    "Choose a replacement or remove it. "
                    "The emoji or default icon will be "
                    "used meanwhile."
                )
            else:
                message = (
                    "Local card image. The emoji or "
                    "default icon remains its fallback."
                )

        else:
            message = (
                "Optional. A card image is used before "
                "the emoji or default icon."
            )

        self.image_status.setText(
            message
        )

    def _choose_card_image(self):
        if self._pending_image_path:
            initial_directory = str(
                Path(
                    self._pending_image_path
                ).parent
            )
        else:
            initial_directory = str(
                Path.home()
            )

        selected_path, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Choose Launcher card image",
                initial_directory,
                (
                    "Images "
                    "(*.png *.jpg *.jpeg *.webp)"
                ),
            )
        )

        if not selected_path:
            return

        self._pending_image_path = (
            selected_path
        )
        self._refresh_image_preview()

    def _remove_card_image(self):
        self._pending_image_path = ""
        self._image_asset = ""
        self._refresh_image_preview()

    def target_kind(self) -> str:
        value = (
            self.target_kind_combo.currentData()
        )

        return str(
            value
            or LAUNCHER_TARGET_FILE
        )

    def _target_kind_changed(self):
        target_kind = self.target_kind()

        if (
            target_kind
            == LAUNCHER_TARGET_APPLICATION
        ):
            self.target_edit.setPlaceholderText(
                r"C:\Program Files\Example\Example.exe"
            )
            self.browse_button.setText(
                "Choose app..."
            )
        elif (
            target_kind
            == LAUNCHER_TARGET_FOLDER
        ):
            self.target_edit.setPlaceholderText(
                r"C:\Users\YourName\Documents"
            )
            self.browse_button.setText(
                "Choose folder..."
            )
        else:
            self.target_edit.setPlaceholderText(
                r"C:\Users\YourName\Documents\file.txt"
            )
            self.browse_button.setText(
                "Choose file..."
            )

        self._refresh_target_feedback()

    def _initial_browse_directory(self) -> str:
        raw_target = (
            self.target_edit.text().strip()
        )

        if raw_target:
            try:
                target = Path(
                    normalize_launcher_target(
                        raw_target
                    )
                )

                if target.is_dir():
                    return str(target)

                if target.parent.exists():
                    return str(target.parent)

            except (TypeError, ValueError):
                pass

        return str(Path.home())

    def _browse_target(self):
        target_kind = self.target_kind()
        initial_directory = (
            self._initial_browse_directory()
        )

        selected_path = ""

        if (
            target_kind
            == LAUNCHER_TARGET_FOLDER
        ):
            selected_path = (
                QFileDialog.getExistingDirectory(
                    self,
                    "Choose Launcher folder",
                    initial_directory,
                )
            )
        else:
            if (
                target_kind
                == LAUNCHER_TARGET_APPLICATION
            ):
                file_filter = (
                    "Applications and shortcuts "
                    "(*.exe *.com *.bat *.cmd *.ps1 "
                    "*.vbs *.js *.lnk);;"
                    "All files (*)"
                )
                caption = (
                    "Choose Launcher application"
                )
            else:
                file_filter = "All files (*)"
                caption = "Choose Launcher file"

            selected_path, _ = (
                QFileDialog.getOpenFileName(
                    self,
                    caption,
                    initial_directory,
                    file_filter,
                )
            )

        if selected_path:
            self.target_edit.setText(
                selected_path
            )

    def _target_validation_error(
        self,
    ) -> str | None:
        raw_target = (
            self.target_edit.text().strip()
        )

        if not raw_target:
            return (
                "Choose a local application, "
                "file, or folder."
            )

        try:
            normalized = (
                normalize_launcher_target(
                    raw_target
                )
            )
        except (TypeError, ValueError) as error:
            return str(error)

        target_path = Path(normalized)

        if not target_path.exists():
            return (
                "The selected target does not exist."
            )

        target_kind = self.target_kind()

        if (
            target_kind
            == LAUNCHER_TARGET_FOLDER
            and not target_path.is_dir()
        ):
            return (
                "The selected target is not a folder."
            )

        if (
            target_kind
            in {
                LAUNCHER_TARGET_APPLICATION,
                LAUNCHER_TARGET_FILE,
            }
            and not target_path.is_file()
        ):
            return (
                "The selected target is not a file."
            )

        return None

    def _refresh_target_feedback(self):
        error = self._target_validation_error()

        if error is not None:
            self.target_status.setProperty(
                "targetState",
                "warning",
            )
            self.target_status.setText(error)
        else:
            target = Path(
                normalize_launcher_target(
                    self.target_edit.text()
                )
            )

            if (
                self.target_kind()
                == LAUNCHER_TARGET_APPLICATION
                and target.suffix.casefold()
                in _SCRIPT_SUFFIXES
            ):
                self.target_status.setProperty(
                    "targetState",
                    "warning",
                )
                self.target_status.setText(
                    "Script target selected. Review the "
                    "file before enabling this Launcher."
                )
            else:
                self.target_status.setProperty(
                    "targetState",
                    "ready",
                )
                self.target_status.setText(
                    f"Ready: {target.name or target}"
                )

        style = self.target_status.style()
        style.unpolish(self.target_status)
        style.polish(self.target_status)

    def validated_card(
        self,
    ) -> LauncherCardData:
        description = (
            self.description_edit
            .toPlainText()
            .strip()
        )

        if (
            len(description)
            > MAX_DESCRIPTION_LENGTH
        ):
            raise ValueError(
                "Description is too long."
            )

        target_error = (
            self._target_validation_error()
        )

        if target_error is not None:
            raise ValueError(target_error)

        card = create_launcher_card(
            card_id=(
                self._editing_card.card_id
                if self._editing_card
                is not None
                else None
            ),
            target=self.target_edit.text(),
            target_kind=self.target_kind(),
            title=self.title_edit.text(),
            icon=self.icon_edit.text(),
            image_asset=self._image_asset,
            description=description,
            button_label=(
                self.button_label_edit.text()
            ),
            accent=self.accent_edit.text(),
        )

        if not self._pending_image_path:
            return card

        image_asset = (
            import_launcher_card_image(
                self._pending_image_path,
                self._image_root,
            )
        )

        return create_launcher_card(
            card_id=card.card_id,
            target=card.target,
            target_kind=card.target_kind,
            title=card.title,
            icon=card.icon,
            image_asset=image_asset,
            description=card.description,
            button_label=card.button_label,
            accent=card.accent,
        )


    def card_data(
        self,
    ) -> LauncherCardData | None:
        return self._result_card

    def _validate_and_accept(self):
        try:
            self._result_card = (
                self.validated_card()
            )
        except (
            OSError,
            TypeError,
            ValueError,
        ) as error:
            self.error_label.setText(
                str(error)
            )
            self.error_label.show()
            return

        self.error_label.hide()
        self.accept()


class LauncherCardWidget(QFrame):
    launch_requested = pyqtSignal(str)

    def __init__(
        self,
        card: LauncherCardData,
        parent=None,
        *,
        image_root: Path | str | None = None,
    ):
        super().__init__(parent)

        self._card = card
        self._responsive_state = "large"
        self._theme = {}
        self._launch_enabled = False
        self._image_root = image_root

        self.setObjectName(
            "launcherCard"
        )
        self.setMinimumSize(1, 1)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(
            13,
            12,
            13,
            12,
        )
        self.root_layout.setSpacing(7)

        self.header_widget = QWidget(self)
        self.header_widget.setObjectName(
            "launcherCardHeader"
        )

        header = QHBoxLayout(
            self.header_widget
        )
        header.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        header.setSpacing(8)

        self.icon_label = QLabel("")
        self.icon_label.setObjectName(
            "launcherCardIcon"
        )
        self.icon_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.icon_label.setFixedSize(
            34,
            34,
        )

        self.title_label = QLabel("")
        self.title_label.setObjectName(
            "launcherCardTitle"
        )
        self.title_label.setWordWrap(True)
        self.title_label.setMinimumSize(
            0,
            0,
        )

        header.addWidget(
            self.icon_label
        )
        header.addWidget(
            self.title_label,
            stretch=1,
        )

        self.target_label = QLabel("")
        self.target_label.setObjectName(
            "launcherCardTarget"
        )
        self.target_label.setTextInteractionFlags(
            Qt.TextInteractionFlag
            .TextSelectableByMouse
        )

        self.description_label = QLabel("")
        self.description_label.setObjectName(
            "launcherCardDescription"
        )
        self.description_label.setWordWrap(True)
        self.description_label.setAlignment(
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignLeft
        )
        self.description_label.setMinimumSize(
            0,
            0,
        )

        self.open_button = QPushButton("")
        self.open_button.setObjectName(
            "launcherCardOpenButton"
        )
        self.open_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.open_button.setMinimumSize(
            0,
            0,
        )
        self.open_button.clicked.connect(
            self._emit_launch_request
        )

        self.root_layout.addWidget(
            self.header_widget
        )
        self.root_layout.addWidget(
            self.target_label
        )
        self.root_layout.addWidget(
            self.description_label,
            stretch=1,
        )
        self.root_layout.addWidget(
            self.open_button
        )

        self.update_card(card)
        self.set_launch_enabled(False)

    @property
    def card_data(
        self,
    ) -> LauncherCardData:
        return self._card

    @property
    def responsive_state(self) -> str:
        return self._responsive_state

    @property
    def launch_enabled(self) -> bool:
        return self._launch_enabled

    def _emit_launch_request(self):
        if not self._launch_enabled:
            return

        self.launch_requested.emit(
            self._card.target
        )

    def set_launch_enabled(
        self,
        enabled: bool,
    ):
        self._launch_enabled = bool(enabled)

        usable = (
            self._launch_enabled
            and self._card.is_configured
            and self._card.target_exists
        )

        self.open_button.setEnabled(usable)

        if not self._launch_enabled:
            self.open_button.setToolTip(
                "Target opening is not enabled yet."
            )
        elif not self._card.is_configured:
            self.open_button.setToolTip(
                "Choose a local target before opening."
            )
        elif not self._card.target_exists:
            self.open_button.setToolTip(
                "The saved target could not be found."
            )
        else:
            self.open_button.setToolTip(
                self._card.target
            )

    def _fallback_icon_text(self) -> str:
        return (
            self._card.icon
            or _KIND_ICONS.get(
                self._card.target_kind,
                "??",
            )
        )

    def _refresh_header_icon(self):
        path = (
            cached_launcher_card_image_path(
                self._card.image_asset,
                self._image_root,
            )
        )

        pixmap = (
            QPixmap(str(path))
            if path is not None
            else QPixmap()
        )

        if not pixmap.isNull():
            available_size = max(
                14,
                min(
                    self.icon_label.width(),
                    self.icon_label.height(),
                )
                - 8,
            )

            self.icon_label.setText("")
            self.icon_label.setPixmap(
                pixmap.scaled(
                    available_size,
                    available_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.icon_label.setToolTip(
                "Custom Launcher card image"
            )
            return

        self.icon_label.setPixmap(
            QPixmap()
        )
        self.icon_label.setText(
            self._fallback_icon_text()
        )

        if self._card.image_asset:
            self.icon_label.setToolTip(
                "Custom image missing. "
                "Using the fallback icon."
            )
        else:
            self.icon_label.setToolTip(
                self._fallback_icon_text()
            )

    def update_card(
        self,
        card: LauncherCardData,
    ):
        if not isinstance(
            card,
            LauncherCardData,
        ):
            raise TypeError(
                "Expected LauncherCardData."
            )

        self._card = card

        self._refresh_header_icon()

        self.title_label.setText(
            card.title
        )
        self.title_label.setToolTip(
            card.title
        )

        kind_label = _KIND_LABELS.get(
            card.target_kind,
            "Target",
        )

        if not card.is_configured:
            target_text = (
                f"{kind_label}: target not selected"
            )
            target_state = "missing"
        elif not card.target_exists:
            target_text = (
                f"{kind_label} missing: "
                f"{card.display_target}"
            )
            target_state = "missing"
        else:
            target_text = (
                f"{kind_label}: "
                f"{card.display_target}"
            )
            target_state = "ready"

        self.target_label.setText(
            target_text
        )
        self.target_label.setToolTip(
            card.target
            or "Target not selected"
        )
        self.target_label.setProperty(
            "targetState",
            target_state,
        )

        target_style = (
            self.target_label.style()
        )
        target_style.unpolish(
            self.target_label
        )
        target_style.polish(
            self.target_label
        )

        self.description_label.setText(
            card.description
        )
        self.description_label.setToolTip(
            card.description
        )

        self.open_button.setText(
            card.button_label
            or "Open"
        )

        self.setToolTip(
            card.target
            or "Launcher target not selected"
        )

        self.set_launch_enabled(
            self._launch_enabled
        )
        self._apply_responsive_state()

        if self._theme:
            self.set_theme(
                self._theme
            )

    def set_theme(
        self,
        theme: dict,
    ):
        self._theme = dict(
            theme
            or {}
        )

        background = self._theme.get(
            "card",
            "#18181d",
        )
        alternate = self._theme.get(
            "card_alt",
            "#222229",
        )
        border = self._theme.get(
            "border",
            "#34343e",
        )
        text = self._theme.get(
            "text",
            "#f5f5f7",
        )
        muted = self._theme.get(
            "muted",
            "#a0a0ad",
        )
        accent = (
            self._card.accent
            or self._theme.get(
                "accent",
                "#a970ff",
            )
        )
        warning = self._theme.get(
            "warning",
            "#f0a45d",
        )

        self.setStyleSheet(
            f"""
            QFrame#launcherCard {{
                background: {background};
                border: 1px solid {accent};
                border-radius: 14px;
            }}

            QWidget#launcherCardHeader {{
                background: transparent;
                border: none;
            }}

            QLabel#launcherCardIcon {{
                color: {accent};
                background: {alternate};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 4px;
                font-size: 17px;
                font-weight: 700;
            }}

            QLabel#launcherCardTitle {{
                color: {text};
                background: transparent;
                border: none;
                font-size: 13px;
                font-weight: 750;
            }}

            QLabel#launcherCardTarget {{
                color: {accent};
                background: transparent;
                border: none;
                font-size: 9px;
                font-weight: 650;
            }}

            QLabel#launcherCardTarget[
                targetState="missing"
            ] {{
                color: {warning};
            }}

            QLabel#launcherCardDescription {{
                color: {muted};
                background: transparent;
                border: none;
                font-size: 10px;
            }}

            QPushButton#launcherCardOpenButton {{
                color: {text};
                background: {alternate};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 10px;
                font-weight: 700;
            }}

            QPushButton#launcherCardOpenButton:hover {{
                border: 1px solid {accent};
            }}

            QPushButton#launcherCardOpenButton:disabled {{
                color: {muted};
                border: 1px solid {border};
            }}
            """
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_state()

    def _apply_responsive_state(self):
        width = max(
            0,
            self.width(),
        )
        height = max(
            0,
            self.height(),
        )

        if width < 145 or height < 90:
            state = "compact"
        elif width < 220 or height < 135:
            state = "medium"
        else:
            state = "large"

        self._responsive_state = state

        if state == "compact":
            self.root_layout.setContentsMargins(
                8,
                7,
                8,
                7,
            )
            self.root_layout.setSpacing(4)
            self.icon_label.setFixedSize(
                25,
                25,
            )
            self.target_label.hide()
            self.description_label.hide()
        elif state == "medium":
            self.root_layout.setContentsMargins(
                10,
                9,
                10,
                9,
            )
            self.root_layout.setSpacing(5)
            self.icon_label.setFixedSize(
                30,
                30,
            )
            self.target_label.show()
            self.description_label.hide()
        else:
            self.root_layout.setContentsMargins(
                13,
                12,
                13,
                12,
            )
            self.root_layout.setSpacing(7)
            self.icon_label.setFixedSize(
                34,
                34,
            )
            self.target_label.show()
            self.description_label.setVisible(
                bool(
                    self._card.description
                )
            )

        self._refresh_header_icon()
