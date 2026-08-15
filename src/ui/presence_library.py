from pathlib import Path

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QMouseEvent,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.discord.presence_modes import (
    MODE_NAMES,
)


FILTER_ALL = "all"
FILTER_PINNED = "pinned"

FILTER_OPTIONS = (
    (FILTER_ALL, "All"),
    (FILTER_PINNED, "Pinned"),
    ("afk", "AFK"),
    ("sleep", "Sleeping"),
    ("working", "Working"),
    ("custom", "Custom"),
)


def _clean_text(
    value,
) -> str:
    return str(
        value
        or ""
    ).strip()


def _preset_value(
    preset,
    name,
    default="",
):
    return getattr(
        preset,
        name,
        default,
    )


class PresenceLibraryCard(QFrame):
    selected = pyqtSignal(str)
    apply_requested = pyqtSignal(str)
    action_requested = pyqtSignal(str, str)

    def __init__(
        self,
        preset,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.setObjectName(
            "presenceLibraryCard"
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self.setMinimumHeight(
            150
        )

        self._preset = None
        self._preset_id = ""
        self._selected = False
        self._theme = {}

        root = QHBoxLayout(
            self
        )

        root.setContentsMargins(
            10,
            10,
            10,
            10,
        )

        root.setSpacing(
            10
        )

        self.artwork = QLabel(
            "PRES"
        )

        self.artwork.setObjectName(
            "presenceLibraryArtwork"
        )

        self.artwork.setFixedSize(
            96,
            96,
        )

        self.artwork.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        root.addWidget(
            self.artwork,
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        content = QVBoxLayout()
        content.setSpacing(
            4
        )

        badge_row = QHBoxLayout()
        badge_row.setSpacing(
            6
        )

        self.mode_badge = QLabel(
            "CUSTOM"
        )

        self.mode_badge.setObjectName(
            "presenceLibraryModeBadge"
        )

        self.pin_badge = QLabel(
            "PIN"
        )

        self.pin_badge.setObjectName(
            "presenceLibraryPinBadge"
        )

        self.pin_badge.setToolTip(
            "Pinned Presence"
        )

        badge_row.addWidget(
            self.mode_badge
        )

        badge_row.addWidget(
            self.pin_badge
        )

        badge_row.addStretch()

        self.menu_button = QPushButton(
            "..."
        )

        self.menu_button.setObjectName(
            "presenceLibraryMenuButton"
        )

        self.menu_button.setFixedSize(
            28,
            26,
        )

        self.menu_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.menu_button.setToolTip(
            "Presence actions"
        )

        badge_row.addWidget(
            self.menu_button
        )

        content.addLayout(
            badge_row
        )

        self.name_label = QLabel(
            "Presence"
        )

        self.name_label.setObjectName(
            "presenceLibraryName"
        )

        self.name_label.setWordWrap(
            True
        )

        content.addWidget(
            self.name_label
        )

        self.title_label = QLabel(
            ""
        )

        self.title_label.setObjectName(
            "presenceLibraryTitle"
        )

        self.title_label.setWordWrap(
            True
        )

        content.addWidget(
            self.title_label
        )

        self.message_label = QLabel(
            ""
        )

        self.message_label.setObjectName(
            "presenceLibraryMessage"
        )

        self.message_label.setWordWrap(
            True
        )

        content.addWidget(
            self.message_label
        )

        content.addStretch()

        action_row = QHBoxLayout()
        action_row.setSpacing(
            6
        )

        self.open_button = QPushButton(
            "Edit"
        )

        self.open_button.setObjectName(
            "presenceLibrarySecondaryButton"
        )

        self.open_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.apply_button = QPushButton(
            "Apply"
        )

        self.apply_button.setObjectName(
            "presenceLibraryApplyButton"
        )

        self.apply_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        action_row.addStretch()
        action_row.addWidget(
            self.open_button
        )
        action_row.addWidget(
            self.apply_button
        )

        content.addLayout(
            action_row
        )

        root.addLayout(
            content,
            stretch=1,
        )

        self.open_button.clicked.connect(
            self._emit_selected
        )

        self.apply_button.clicked.connect(
            self._emit_apply
        )

        self.menu_button.clicked.connect(
            self._show_action_menu
        )

        self.set_preset(
            preset
        )

    @property
    def preset_id(
        self,
    ) -> str:
        return self._preset_id

    @property
    def preset(
        self,
    ):
        return self._preset

    def set_preset(
        self,
        preset,
    ):
        preset_id = _clean_text(
            _preset_value(
                preset,
                "preset_id",
            )
        )

        if not preset_id:
            raise ValueError(
                "Presence Library cards require a preset ID."
            )

        self._preset = preset
        self._preset_id = preset_id

        name = (
            _clean_text(
                _preset_value(
                    preset,
                    "name",
                )
            )
            or "Untitled Presence"
        )

        mode = (
            _clean_text(
                _preset_value(
                    preset,
                    "mode",
                )
            ).casefold()
            or "custom"
        )

        title = _clean_text(
            _preset_value(
                preset,
                "title",
            )
        )

        message = _clean_text(
            _preset_value(
                preset,
                "message",
            )
        )

        pinned = bool(
            _preset_value(
                preset,
                "pinned",
                False,
            )
        )

        mode_name = (
            MODE_NAMES.get(
                mode,
                mode.replace(
                    "_",
                    " ",
                ).title(),
            )
            or "Custom"
        )

        self.name_label.setText(
            name
        )

        self.mode_badge.setText(
            mode_name.upper()
        )

        self.pin_badge.setVisible(
            pinned
        )

        self.title_label.setText(
            title
            or mode_name
        )

        self.title_label.setVisible(
            bool(
                title
                or mode_name
            )
        )

        self.message_label.setText(
            message
        )

        self.message_label.setVisible(
            bool(message)
        )

        image_path = Path(
            _clean_text(
                _preset_value(
                    preset,
                    "image_path",
                )
            )
        )

        pixmap = QPixmap()

        if (
            image_path.is_file()
            and pixmap.load(
                str(image_path)
            )
            and not pixmap.isNull()
        ):
            self.artwork.setText(
                ""
            )

            self.artwork.setPixmap(
                pixmap.scaled(
                    self.artwork.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        else:
            self.artwork.clear()

            fallback = (
                mode_name[:4].upper()
                or "PRES"
            )

            self.artwork.setText(
                fallback
            )

        self.setProperty(
            "presenceMode",
            mode
        )

        self.setProperty(
            "pinned",
            pinned
        )

        self._refresh_style()

    def set_selected(
        self,
        selected,
    ):
        selected = bool(
            selected
        )

        if selected == self._selected:
            return

        self._selected = selected

        self.setProperty(
            "selected",
            selected
        )

        self._refresh_style()

    def _refresh_style(
        self,
    ):
        style = self.style()

        if style is None:
            return

        style.unpolish(
            self
        )

        style.polish(
            self
        )

        self.update()

    def _emit_selected(
        self,
    ):
        self.selected.emit(
            self._preset_id
        )

    def _emit_apply(
        self,
    ):
        self.apply_requested.emit(
            self._preset_id
        )

    def _emit_action(
        self,
        action,
    ):
        action = _clean_text(
            action
        ).casefold()

        if action not in {
            "edit",
            "rename",
            "duplicate",
            "pin",
            "delete",
        }:
            return

        self.action_requested.emit(
            self._preset_id,
            action,
        )

    def _show_action_menu(
        self,
    ):
        menu = QMenu(
            self
        )

        edit_action = menu.addAction(
            "Edit"
        )

        rename_action = menu.addAction(
            "Rename"
        )

        duplicate_action = menu.addAction(
            "Duplicate"
        )

        menu.addSeparator()

        pinned = bool(
            _preset_value(
                self._preset,
                "pinned",
                False,
            )
        )

        pin_action = menu.addAction(
            "Unpin"
            if pinned
            else "Pin"
        )

        menu.addSeparator()

        delete_action = menu.addAction(
            "Delete"
        )

        edit_action.triggered.connect(
            lambda checked=False:
            self._emit_action(
                "edit"
            )
        )

        rename_action.triggered.connect(
            lambda checked=False:
            self._emit_action(
                "rename"
            )
        )

        duplicate_action.triggered.connect(
            lambda checked=False:
            self._emit_action(
                "duplicate"
            )
        )

        pin_action.triggered.connect(
            lambda checked=False:
            self._emit_action(
                "pin"
            )
        )

        delete_action.triggered.connect(
            lambda checked=False:
            self._emit_action(
                "delete"
            )
        )

        menu.exec(
            self.menu_button.mapToGlobal(
                self.menu_button.rect().bottomLeft()
            )
        )

    def mousePressEvent(
        self,
        event: QMouseEvent,
    ):
        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self._emit_selected()

        super().mousePressEvent(
            event
        )


class PresenceLibraryPanel(QFrame):
    preset_selected = pyqtSignal(str)
    preset_apply_requested = pyqtSignal(str)
    preset_action_requested = pyqtSignal(str, str)
    create_requested = pyqtSignal()

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.setObjectName(
            "presenceLibraryPanel"
        )

        self._presets = ()
        self._selected_id = ""
        self._active_filter = FILTER_ALL
        self._cards = {}
        self._columns = 2
        self._theme = {}

        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            16,
            16,
            16,
            16,
        )

        root.setSpacing(
            12
        )

        header = QHBoxLayout()
        header.setSpacing(
            10
        )

        heading_group = QVBoxLayout()
        heading_group.setSpacing(
            2
        )

        self.heading = QLabel(
            "PRESENCE LIBRARY"
        )

        self.heading.setObjectName(
            "presenceLibraryHeading"
        )

        self.subtitle = QLabel(
            "Your saved Discord identities, ready when you are."
        )

        self.subtitle.setObjectName(
            "presenceLibrarySubtitle"
        )

        self.subtitle.setWordWrap(
            True
        )

        heading_group.addWidget(
            self.heading
        )

        heading_group.addWidget(
            self.subtitle
        )

        header.addLayout(
            heading_group
        )

        header.addStretch()

        self.create_button = QPushButton(
            "+ New Presence"
        )

        self.create_button.setObjectName(
            "presenceLibraryCreateButton"
        )

        self.create_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        header.addWidget(
            self.create_button,
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        root.addLayout(
            header
        )

        controls = QHBoxLayout()
        controls.setSpacing(
            8
        )

        self.search_input = QLineEdit()

        self.search_input.setObjectName(
            "presenceLibrarySearch"
        )

        self.search_input.setPlaceholderText(
            "Search your Presence Library..."
        )

        self.search_input.setClearButtonEnabled(
            True
        )

        self.filter_box = QComboBox()

        self.filter_box.setObjectName(
            "presenceLibraryFilter"
        )

        self.filter_box.setMinimumWidth(
            110
        )

        for value, label in FILTER_OPTIONS:
            self.filter_box.addItem(
                label,
                value,
            )

        controls.addWidget(
            self.search_input,
            stretch=1,
        )

        controls.addWidget(
            self.filter_box
        )

        root.addLayout(
            controls
        )

        self.summary_label = QLabel(
            "No saved presences yet"
        )

        self.summary_label.setObjectName(
            "presenceLibrarySummary"
        )

        root.addWidget(
            self.summary_label
        )

        self.scroll = QScrollArea()

        self.scroll.setObjectName(
            "presenceLibraryScroll"
        )

        self.scroll.setWidgetResizable(
            True
        )

        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.scroll_container = QWidget()

        self.scroll_container.setObjectName(
            "presenceLibraryContainer"
        )

        self.grid = QGridLayout(
            self.scroll_container
        )

        self.grid.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.grid.setHorizontalSpacing(
            10
        )

        self.grid.setVerticalSpacing(
            10
        )

        self.grid.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        self.empty_state = QFrame()

        self.empty_state.setObjectName(
            "presenceLibraryEmpty"
        )

        empty_layout = QVBoxLayout(
            self.empty_state
        )

        empty_layout.setContentsMargins(
            20,
            30,
            20,
            30,
        )

        empty_layout.setSpacing(
            5
        )

        self.empty_title = QLabel(
            "Your Presence Library is empty"
        )

        self.empty_title.setObjectName(
            "presenceLibraryEmptyTitle"
        )

        self.empty_title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.empty_text = QLabel(
            "Create a Presence and it will appear here as a reusable card."
        )

        self.empty_text.setObjectName(
            "presenceLibraryEmptyText"
        )

        self.empty_text.setWordWrap(
            True
        )

        self.empty_text.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        empty_layout.addStretch()

        empty_layout.addWidget(
            self.empty_title
        )

        empty_layout.addWidget(
            self.empty_text
        )

        empty_layout.addStretch()

        self.grid.addWidget(
            self.empty_state,
            0,
            0,
            1,
            self._columns,
        )

        self.scroll.setWidget(
            self.scroll_container
        )

        root.addWidget(
            self.scroll,
            stretch=1,
        )

        self.create_button.clicked.connect(
            self.create_requested.emit
        )

        self.search_input.textChanged.connect(
            self.refresh
        )

        self.filter_box.currentIndexChanged.connect(
            self._filter_changed
        )

    @property
    def cards(
        self,
    ) -> dict:
        return dict(
            self._cards
        )

    @property
    def selected_id(
        self,
    ) -> str:
        return self._selected_id

    def set_presets(
        self,
        presets,
        selected_id="",
    ):
        try:
            normalized = tuple(
                presets
            )
        except TypeError as error:
            raise TypeError(
                "Presence Library presets must be iterable."
            ) from error

        self._presets = tuple(
            sorted(
                normalized,
                key=lambda preset: (
                    not bool(
                        _preset_value(
                            preset,
                            "pinned",
                            False,
                        )
                    ),
                    _clean_text(
                        _preset_value(
                            preset,
                            "name",
                        )
                    ).casefold(),
                ),
            )
        )

        self._selected_id = _clean_text(
            selected_id
        )

        self.refresh()

    def set_selected_id(
        self,
        preset_id,
    ):
        self._selected_id = _clean_text(
            preset_id
        )

        for card_id, card in self._cards.items():
            card.set_selected(
                card_id
                == self._selected_id
            )

    def _filter_changed(
        self,
        *_,
    ):
        value = _clean_text(
            self.filter_box.currentData()
        ).casefold()

        self._active_filter = (
            value
            if value
            else FILTER_ALL
        )

        self.refresh()

    def _matches(
        self,
        preset,
    ) -> bool:
        query = _clean_text(
            self.search_input.text()
        ).casefold()

        mode = _clean_text(
            _preset_value(
                preset,
                "mode",
            )
        ).casefold()

        pinned = bool(
            _preset_value(
                preset,
                "pinned",
                False,
            )
        )

        if (
            self._active_filter
            == FILTER_PINNED
            and not pinned
        ):
            return False

        if (
            self._active_filter
            not in {
                FILTER_ALL,
                FILTER_PINNED,
            }
            and mode
            != self._active_filter
        ):
            return False

        if not query:
            return True

        searchable = " ".join(
            (
                _clean_text(
                    _preset_value(
                        preset,
                        "name",
                    )
                ),
                _clean_text(
                    _preset_value(
                        preset,
                        "title",
                    )
                ),
                _clean_text(
                    _preset_value(
                        preset,
                        "message",
                    )
                ),
                MODE_NAMES.get(
                    mode,
                    mode,
                ),
            )
        ).casefold()

        return query in searchable

    def _clear_grid(
        self,
    ):
        while self.grid.count():
            item = self.grid.takeAt(
                0
            )

            widget = item.widget()

            if widget is None:
                continue

            widget.hide()
            widget.setParent(
                None
            )
            widget.deleteLater()

        self._cards = {}

    def refresh(
        self,
        *_,
    ):
        self._clear_grid()

        visible = tuple(
            preset
            for preset in self._presets
            if self._matches(
                preset
            )
        )

        if not visible:
            self.empty_state = QFrame()

            self.empty_state.setObjectName(
                "presenceLibraryEmpty"
            )

            empty_layout = QVBoxLayout(
                self.empty_state
            )

            empty_layout.setContentsMargins(
                20,
                28,
                20,
                28,
            )

            empty_layout.setSpacing(
                5
            )

            title = QLabel(
                (
                    "No matching presences"
                    if self._presets
                    else "Your Presence Library is empty"
                )
            )

            title.setObjectName(
                "presenceLibraryEmptyTitle"
            )

            title.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            detail = QLabel(
                (
                    "Try another search or filter."
                    if self._presets
                    else
                    "Create a Presence and it will appear here as a reusable card."
                )
            )

            detail.setObjectName(
                "presenceLibraryEmptyText"
            )

            detail.setWordWrap(
                True
            )

            detail.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            empty_layout.addStretch()
            empty_layout.addWidget(
                title
            )
            empty_layout.addWidget(
                detail
            )
            empty_layout.addStretch()

            self.grid.addWidget(
                self.empty_state,
                0,
                0,
                1,
                self._columns,
            )

            self.summary_label.setText(
                (
                    "No matches"
                    if self._presets
                    else "No saved presences yet"
                )
            )

            return

        for index, preset in enumerate(
            visible
        ):
            card = PresenceLibraryCard(
                preset,
                self.scroll_container,
            )

            preset_id = card.preset_id

            card.set_selected(
                preset_id
                == self._selected_id
            )

            card.selected.connect(
                self._card_selected
            )

            card.apply_requested.connect(
                self.preset_apply_requested.emit
            )

            card.action_requested.connect(
                self.preset_action_requested.emit
            )

            row = (
                index
                // self._columns
            )

            column = (
                index
                % self._columns
            )

            self.grid.addWidget(
                card,
                row,
                column,
            )

            self._cards[
                preset_id
            ] = card

        for column in range(
            self._columns
        ):
            self.grid.setColumnStretch(
                column,
                1,
            )

        count = len(
            visible
        )

        total = len(
            self._presets
        )

        if count == total:
            text = (
                f"{total} saved presence"
                + (
                    ""
                    if total == 1
                    else "s"
                )
            )
        else:
            text = (
                f"{count} of {total} shown"
            )

        self.summary_label.setText(
            text
        )

    def _card_selected(
        self,
        preset_id,
    ):
        self.set_selected_id(
            preset_id
        )

        self.preset_selected.emit(
            preset_id
        )

    def resizeEvent(
        self,
        event,
    ):
        desired_columns = (
            3
            if self.width() >= 980
            else 2
        )

        if desired_columns != self._columns:
            self._columns = desired_columns

            self.refresh()

        super().resizeEvent(
            event
        )

    def apply_theme(
        self,
        theme,
    ):
        self._theme = dict(
            theme
            if isinstance(
                theme,
                dict,
            )
            else {}
        )

        text = self._theme.get(
            "text",
            "#ffffff",
        )

        muted = self._theme.get(
            "muted",
            "#b9aeb8",
        )

        accent = self._theme.get(
            "accent",
            "#ff6ea9",
        )

        card = self._theme.get(
            "card",
            "#2a1721",
        )

        card_alt = self._theme.get(
            "card_alt",
            "#351d2a",
        )

        background = self._theme.get(
            "background",
            "#160d12",
        )

        border = self._theme.get(
            "border",
            "#5a3346",
        )

        self.setStyleSheet(
            f"""
            QFrame#presenceLibraryPanel {{
                background: {card};
                border: 1px solid {border};
                border-radius: 16px;
            }}

            QLabel#presenceLibraryHeading {{
                color: {accent};
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1.2px;
            }}

            QLabel#presenceLibrarySubtitle,
            QLabel#presenceLibrarySummary,
            QLabel#presenceLibraryMessage,
            QLabel#presenceLibraryEmptyText {{
                color: {muted};
                font-size: 10px;
            }}

            QPushButton#presenceLibraryCreateButton,
            QPushButton#presenceLibraryApplyButton {{
                color: {background};
                background: {accent};
                border: 1px solid {accent};
                border-radius: 9px;
                padding: 8px 12px;
                font-size: 10px;
                font-weight: 750;
            }}

            QPushButton#presenceLibraryCreateButton:hover,
            QPushButton#presenceLibraryApplyButton:hover {{
                color: {text};
                border-color: {text};
            }}

            QPushButton#presenceLibrarySecondaryButton {{
                color: {text};
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 9px;
                font-weight: 650;
            }}

            QPushButton#presenceLibrarySecondaryButton:hover {{
                border-color: {accent};
            }}

            QLineEdit#presenceLibrarySearch,
            QComboBox#presenceLibraryFilter {{
                color: {text};
                background: {background};
                border: 1px solid {border};
                border-radius: 9px;
                padding: 8px 10px;
                font-size: 10px;
            }}

            QComboBox#presenceLibraryFilter {{
                padding-right: 30px;
            }}

            QComboBox#presenceLibraryFilter::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border: none;
                background: transparent;
            }}

            QLineEdit#presenceLibrarySearch:focus,
            QComboBox#presenceLibraryFilter:focus {{
                border: 1px solid {accent};
            }}

            QScrollArea#presenceLibraryScroll,
            QWidget#presenceLibraryContainer {{
                background: transparent;
                border: none;
            }}

            QFrame#presenceLibraryCard {{
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 13px;
            }}

            QFrame#presenceLibraryCard:hover {{
                border: 1px solid {accent};
            }}

            QFrame#presenceLibraryCard[selected="true"] {{
                background: {card};
                border: 2px solid {accent};
            }}

            QLabel#presenceLibraryArtwork {{
                color: {muted};
                background: {background};
                border: 1px solid {border};
                border-radius: 11px;
                font-size: 11px;
                font-weight: 800;
            }}

            QLabel#presenceLibraryModeBadge,
            QLabel#presenceLibraryPinBadge {{
                color: {accent};
                background: {background};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 3px 6px;
                font-size: 8px;
                font-weight: 750;
            }}

            QPushButton#presenceLibraryMenuButton {{
                color: {muted};
                background: {background};
                border: 1px solid {border};
                border-radius: 7px;
                padding: 0px;
                font-size: 12px;
                font-weight: 800;
            }}

            QPushButton#presenceLibraryMenuButton:hover {{
                color: {text};
                border-color: {accent};
                background: {card};
            }}

            QMenu {{
                color: {text};
                background: {card};
                border: 1px solid {border};
                padding: 4px;
            }}

            QMenu::item {{
                padding: 7px 24px 7px 9px;
                border-radius: 6px;
            }}

            QMenu::item:selected {{
                background: {accent};
                color: {background};
            }}

            QMenu::separator {{
                height: 1px;
                background: {border};
                margin: 4px 6px;
            }}

            QLabel#presenceLibraryName {{
                color: {text};
                font-size: 14px;
                font-weight: 750;
            }}

            QLabel#presenceLibraryTitle,
            QLabel#presenceLibraryEmptyTitle {{
                color: {text};
                font-size: 11px;
                font-weight: 650;
            }}

            QFrame#presenceLibraryEmpty {{
                background: {card_alt};
                border: 1px dashed {border};
                border-radius: 12px;
            }}
            """
        )


__all__ = [
    "FILTER_ALL",
    "FILTER_PINNED",
    "FILTER_OPTIONS",
    "PresenceLibraryCard",
    "PresenceLibraryPanel",
]