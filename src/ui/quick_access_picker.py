from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
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

        self._entries = (
            tuple(
                addable_quick_access_catalogue(
                    existing_item_ids
                )
            )
            + tuple(
                dynamic_entries
            )
        )

        self._rows = []

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

        if self._entries:
            self.empty_label.hide()

            for entry in self._entries:
                self._add_entry_row(
                    entry
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
