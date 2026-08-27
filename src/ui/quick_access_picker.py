from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.system.quick_access_catalogue import (
    addable_quick_access_catalogue,
)
from src.system.quick_access_preferences import (
    QuickAccessItem,
)


FALLBACK_THEME = {
    "background": "#0b1020",
    "card": "#182139",
    "card_alt": "#11182b",
    "accent": "#6ea8ff",
    "text": "#f5f7ff",
    "muted": "#9ba9c5",
    "border": "#2d3b60",
}

_DYNAMIC_GROUP_PRESENTATION = {
    "spotify_playlists": {
        "title": "Playlists",
        "detail": "Browse your Spotify playlists",
        "description": (
            "Choose a Spotify playlist to add "
            "to Quick Access."
        ),
        "search_placeholder": "Search playlists",
    },
}


def _merged_theme(
    theme: dict | None,
) -> dict:
    merged = dict(
        FALLBACK_THEME
    )

    if isinstance(
        theme,
        dict,
    ):
        for key in tuple(
            merged
        ):
            value = theme.get(
                key
            )

            if value:
                merged[
                    key
                ] = str(
                    value
                )

    return merged


class QuickAccessPickerDialog(QDialog):
    def __init__(
        self,
        existing_item_ids: Iterable[str],
        theme: dict | None = None,
        parent: QWidget | None = None,
        *,
        dynamic_items: Iterable[QuickAccessItem] = (),
    ):
        super().__init__(
            parent
        )

        self._theme = _merged_theme(
            theme
        )

        self._selected_item_id = None

        existing_item_ids = tuple(
            str(
                item_id
                or ""
            ).strip().casefold()
            for item_id in existing_item_ids
        )

        existing_ids = set(
            existing_item_ids
        )

        dynamic_items = tuple(
            dynamic_items
        )

        dynamic_entries = []
        seen_dynamic_ids = set()

        for dynamic_item in dynamic_items:
            if not isinstance(
                dynamic_item,
                QuickAccessItem,
            ):
                raise TypeError(
                    "dynamic_items must contain "
                    "QuickAccessItem values."
                )

            if (
                dynamic_item.kind
                not in {
                    "presence_preset",
                    "presence_mode",
                    "launcher_card",
                    "spotify_playlist",
                }
            ):
                raise ValueError(
                    "Unsupported dynamic Quick Access "
                    "item kind."
                )

            if (
                dynamic_item.item_id
                in seen_dynamic_ids
            ):
                raise ValueError(
                    "Dynamic Quick Access items contain "
                    "duplicate IDs."
                )

            seen_dynamic_ids.add(
                dynamic_item.item_id
            )

            if (
                dynamic_item.item_id
                in existing_ids
            ):
                continue

            dynamic_entries.append(
                dynamic_item
            )

        playlist_entries = tuple(
            entry
            for entry in dynamic_entries
            if (
                entry.kind
                == "spotify_playlist"
            )
        )

        root_dynamic_entries = tuple(
            entry
            for entry in dynamic_entries
            if (
                entry.kind
                != "spotify_playlist"
            )
        )

        self._group_entries = {}

        if playlist_entries:
            self._group_entries[
                "spotify_playlists"
            ] = playlist_entries

        self._entries = (
            tuple(
                addable_quick_access_catalogue(
                    existing_item_ids
                )
            )
            + root_dynamic_entries
        )

        self._rows = []
        self._group_rows = []

        self.setObjectName(
            "quickAccessPickerDialog"
        )

        self.setWindowTitle(
            "Add Quick Access Shortcut"
        )

        self.setModal(
            True
        )

        self.setMinimumWidth(
            520
        )

        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            20,
            20,
            20,
            20,
        )

        root.setSpacing(
            12
        )

        title = QLabel(
            "ADD SHORTCUT"
        )

        title.setObjectName(
            "pickerTitle"
        )

        description = QLabel(
            "Choose another destination to add to "
            "Quick Access."
        )

        description.setObjectName(
            "pickerDescription"
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

        self.scroll = QScrollArea()

        self.scroll.setObjectName(
            "quickAccessPickerScroll"
        )

        self.scroll.setWidgetResizable(
            True
        )

        self.scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.scroll.viewport().setObjectName(
            "quickAccessPickerViewport"
        )

        self.content = QWidget()

        self.content.setObjectName(
            "quickAccessPickerContent"
        )

        self.content_layout = QVBoxLayout(
            self.content
        )

        self.content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.content_layout.setSpacing(
            9
        )

        self.empty_label = QLabel(
            "Everything currently available is already "
            "in Quick Access."
        )

        self.empty_label.setObjectName(
            "pickerEmpty"
        )

        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.empty_label.setWordWrap(
            True
        )

        if (
            self._entries
            or self._group_entries
        ):
            self.empty_label.hide()

            for entry in self._entries:
                self._add_entry_row(
                    entry
                )

            for (
                group_key,
                entries,
            ) in self._group_entries.items():
                self._add_group_row(
                    group_key,
                    entries,
                )

        else:
            self.content_layout.addWidget(
                self.empty_label,
                stretch=1,
            )

        self.content_layout.addStretch()

        self.scroll.setWidget(
            self.content
        )

        root.addWidget(
            self.scroll,
            stretch=1,
        )

        close_button = QPushButton(
            "Cancel"
        )

        close_button.setObjectName(
            "secondaryButton"
        )

        close_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        close_button.clicked.connect(
            self.reject
        )

        footer = QHBoxLayout()

        footer.addStretch()

        footer.addWidget(
            close_button
        )

        root.addLayout(
            footer
        )

        self.apply_theme(
            self._theme
        )

    def _add_entry_row(
        self,
        entry,
    ) -> None:
        row = QFrame()

        row.setObjectName(
            "quickAccessPickerRow"
        )

        row_layout = QHBoxLayout(
            row
        )

        row_layout.setContentsMargins(
            12,
            10,
            12,
            10,
        )

        row_layout.setSpacing(
            12
        )

        text_layout = QVBoxLayout()

        text_layout.setSpacing(
            2
        )

        title = QLabel(
            entry.title
        )

        title.setObjectName(
            "pickerRowTitle"
        )

        detail = QLabel(
            entry.detail
        )

        detail.setObjectName(
            "pickerRowDetail"
        )

        detail.setWordWrap(
            True
        )

        text_layout.addWidget(
            title
        )

        text_layout.addWidget(
            detail
        )

        add_button = QPushButton(
            "Add"
        )

        add_button.setObjectName(
            "primaryButton"
        )

        add_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        add_button.setMinimumWidth(
            74
        )

        add_button.clicked.connect(
            lambda checked=False,
            item_id=entry.item_id:
            self._choose(
                item_id
            )
        )

        row_layout.addLayout(
            text_layout,
            stretch=1,
        )

        row_layout.addWidget(
            add_button
        )

        self.content_layout.addWidget(
            row
        )

        self._rows.append(
            {
                "item_id": entry.item_id,
                "row": row,
                "title": title,
                "detail": detail,
                "add": add_button,
            }
        )

    def _add_group_row(
        self,
        group_key: str,
        entries,
    ) -> None:
        metadata = (
            _DYNAMIC_GROUP_PRESENTATION.get(
                group_key
            )
        )

        if (
            not isinstance(
                metadata,
                dict,
            )
            or not entries
        ):
            return

        row = QFrame()

        row.setObjectName(
            "quickAccessPickerRow"
        )

        row_layout = QHBoxLayout(
            row
        )

        row_layout.setContentsMargins(
            12,
            10,
            12,
            10,
        )

        row_layout.setSpacing(
            12
        )

        text_layout = QVBoxLayout()

        text_layout.setSpacing(
            2
        )

        title_text = str(
            metadata.get(
                "title",
                "",
            )
            or ""
        ).strip()

        detail_text = str(
            metadata.get(
                "detail",
                "",
            )
            or ""
        ).strip()

        title = QLabel(
            title_text
        )

        title.setObjectName(
            "pickerRowTitle"
        )

        detail = QLabel(
            detail_text
        )

        detail.setObjectName(
            "pickerRowDetail"
        )

        detail.setWordWrap(
            True
        )

        text_layout.addWidget(
            title
        )

        text_layout.addWidget(
            detail
        )

        open_button = QPushButton(
            "Browse"
        )

        open_button.setObjectName(
            "primaryButton"
        )

        open_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        open_button.setMinimumWidth(
            74
        )

        open_button.clicked.connect(
            lambda checked=False,
            key=group_key:
            self._open_group(
                key
            )
        )

        row_layout.addLayout(
            text_layout,
            stretch=1,
        )

        row_layout.addWidget(
            open_button
        )

        self.content_layout.addWidget(
            row
        )

        self._group_rows.append(
            {
                "group_key": group_key,
                "row": row,
                "title": title,
                "detail": detail,
                "open": open_button,
            }
        )


    def _open_group(
        self,
        group_key: str,
    ) -> None:
        entries = (
            self._group_entries.get(
                group_key,
                ()
            )
        )

        metadata = (
            _DYNAMIC_GROUP_PRESENTATION.get(
                group_key
            )
        )

        if (
            not entries
            or not isinstance(
                metadata,
                dict,
            )
        ):
            return

        dialog = QuickAccessGroupPickerDialog(
            entries,
            title=str(
                metadata.get(
                    "title",
                    "Shortcuts",
                )
                or "Shortcuts"
            ),
            description=str(
                metadata.get(
                    "description",
                    "",
                )
                or ""
            ),
            search_placeholder=str(
                metadata.get(
                    "search_placeholder",
                    "Search",
                )
                or "Search"
            ),
            theme=self._theme,
            parent=self,
        )

        if not dialog.exec():
            return

        selected_item_id = (
            dialog.selected_item_id()
        )

        if not selected_item_id:
            return

        self._accept_group_item(
            group_key,
            selected_item_id,
        )


    def _accept_group_item(
        self,
        group_key: str,
        item_id: str,
    ) -> bool:
        entries = (
            self._group_entries.get(
                group_key,
                ()
            )
        )

        allowed = {
            entry.item_id
            for entry in entries
        }

        normalized = str(
            item_id
            or ""
        ).strip().casefold()

        if normalized not in allowed:
            return False

        self._selected_item_id = (
            normalized
        )

        self.accept()

        return True


    def _choose(
        self,
        item_id: str,
    ) -> None:
        allowed = {
            entry.item_id
            for entry in self._entries
        }

        normalized = str(
            item_id
            or ""
        ).strip().casefold()

        if normalized not in allowed:
            return

        self._selected_item_id = normalized

        self.accept()

    def selected_item_id(
        self,
    ) -> str | None:
        return self._selected_item_id

    def apply_theme(
        self,
        theme: dict | None,
    ) -> None:
        self._theme = _merged_theme(
            theme
        )

        background = self._theme[
            "background"
        ]
        card = self._theme[
            "card"
        ]
        card_alt = self._theme[
            "card_alt"
        ]
        accent = self._theme[
            "accent"
        ]
        text = self._theme[
            "text"
        ]
        muted = self._theme[
            "muted"
        ]
        border = self._theme[
            "border"
        ]

        self.setStyleSheet(
            f"""
            QDialog#quickAccessPickerDialog {{
                background: {background};
                color: {text};
            }}

            QLabel#pickerTitle {{
                background: transparent;
                color: {accent};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#pickerDescription,
            QLabel#pickerEmpty {{
                background: transparent;
                color: {muted};
                font-size: 12px;
            }}

            QScrollArea#quickAccessPickerScroll,
            QWidget#quickAccessPickerViewport,
            QWidget#quickAccessPickerContent {{
                background: transparent;
                border: none;
            }}

            QFrame#quickAccessPickerRow {{
                background: {card};
                border: 1px solid {border};
                border-radius: 10px;
            }}

            QLabel#pickerRowTitle {{
                background: transparent;
                color: {text};
                font-weight: 600;
            }}

            QLabel#pickerRowDetail {{
                background: transparent;
                color: {muted};
                font-size: 11px;
            }}

            QLineEdit#quickAccessGroupSearch {{
                min-height: 32px;
                padding: 0 10px;
                color: {text};
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 8px;
                selection-background-color: {accent};
                selection-color: {background};
            }}

            QLineEdit#quickAccessGroupSearch:focus {{
                border: 1px solid {accent};
            }}

            QPushButton#secondaryButton {{
                min-height: 28px;
                padding: 0 12px;
                color: {text};
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 8px;
            }}

            QPushButton#secondaryButton:hover {{
                color: {accent};
                border: 1px solid {accent};
            }}

            QPushButton#primaryButton {{
                min-height: 28px;
                padding: 0 14px;
                color: {background};
                background: {accent};
                border: 1px solid {accent};
                border-radius: 8px;
                font-weight: 600;
            }}

            QPushButton#primaryButton:hover {{
                border: 1px solid {text};
            }}

            QPushButton#primaryButton:pressed {{
                color: {accent};
                background: {card_alt};
            }}
            """
        )

class QuickAccessGroupPickerDialog(QDialog):
    def __init__(
        self,
        entries: Iterable[QuickAccessItem],
        *,
        title: str,
        description: str,
        search_placeholder: str,
        theme: dict | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(
            parent
        )

        self._theme = _merged_theme(
            theme
        )

        entries = tuple(
            entries
        )

        for entry in entries:
            if not isinstance(
                entry,
                QuickAccessItem,
            ):
                raise TypeError(
                    "entries must contain "
                    "QuickAccessItem values."
                )

        self._entries = entries
        self._selected_item_id = None
        self._rows = []

        checked_title = (
            str(
                title
                or "Shortcuts"
            ).strip()
            or "Shortcuts"
        )

        checked_description = str(
            description
            or ""
        ).strip()

        checked_placeholder = (
            str(
                search_placeholder
                or "Search"
            ).strip()
            or "Search"
        )

        self.setObjectName(
            "quickAccessPickerDialog"
        )

        self.setWindowTitle(
            checked_title
        )

        self.setModal(
            True
        )

        self.setMinimumWidth(
            520
        )

        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            20,
            20,
            20,
            20,
        )

        root.setSpacing(
            12
        )

        heading = QLabel(
            checked_title.upper()
        )

        heading.setObjectName(
            "pickerTitle"
        )

        root.addWidget(
            heading
        )

        description_label = QLabel(
            checked_description
        )

        description_label.setObjectName(
            "pickerDescription"
        )

        description_label.setWordWrap(
            True
        )

        root.addWidget(
            description_label
        )

        self.search_edit = QLineEdit()

        self.search_edit.setObjectName(
            "quickAccessGroupSearch"
        )

        self.search_edit.setPlaceholderText(
            checked_placeholder
        )

        self.search_edit.setClearButtonEnabled(
            True
        )

        root.addWidget(
            self.search_edit
        )

        self.scroll = QScrollArea()

        self.scroll.setObjectName(
            "quickAccessPickerScroll"
        )

        self.scroll.setWidgetResizable(
            True
        )

        self.scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.content = QWidget()

        self.content.setObjectName(
            "quickAccessPickerContent"
        )

        self.content_layout = QVBoxLayout(
            self.content
        )

        self.content_layout.setContentsMargins(
            0,
            2,
            0,
            2,
        )

        self.content_layout.setSpacing(
            9
        )

        self.empty_label = QLabel(
            "No matching shortcuts."
        )

        self.empty_label.setObjectName(
            "pickerEmpty"
        )

        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.empty_label.setWordWrap(
            True
        )

        self.content_layout.addWidget(
            self.empty_label
        )

        self.empty_label.hide()

        for entry in self._entries:
            QuickAccessPickerDialog._add_entry_row(
                self,
                entry,
            )

        self.content_layout.addStretch()

        self.scroll.setWidget(
            self.content
        )

        root.addWidget(
            self.scroll,
            stretch=1,
        )

        footer = QHBoxLayout()

        footer.addStretch()

        close_button = QPushButton(
            "Back"
        )

        close_button.setObjectName(
            "secondaryButton"
        )

        close_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        close_button.clicked.connect(
            self.reject
        )

        footer.addWidget(
            close_button
        )

        root.addLayout(
            footer
        )

        self.search_edit.textChanged.connect(
            self._filter_rows
        )

        QuickAccessPickerDialog.apply_theme(
            self,
            self._theme,
        )


    def _filter_rows(
        self,
        query: str,
    ) -> None:
        normalized = str(
            query
            or ""
        ).strip().casefold()

        visible_count = 0

        for row in self._rows:
            title = str(
                row[
                    "title"
                ].text()
                or ""
            )

            detail = str(
                row[
                    "detail"
                ].text()
                or ""
            )

            haystack = (
                title
                + " "
                + detail
            ).casefold()

            matches = (
                not normalized
                or normalized
                in haystack
            )

            row[
                "row"
            ].setHidden(
                not matches
            )

            if matches:
                visible_count += 1

        self.empty_label.setHidden(
            visible_count > 0
        )


    def _choose(
        self,
        item_id: str,
    ) -> bool:
        allowed = {
            entry.item_id
            for entry in self._entries
        }

        normalized = str(
            item_id
            or ""
        ).strip().casefold()

        if normalized not in allowed:
            return False

        self._selected_item_id = (
            normalized
        )

        self.accept()

        return True


    def selected_item_id(
        self,
    ) -> str | None:
        return self._selected_item_id
