from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from PyQt6.QtCore import (
    QRectF,
    QSize,
    Qt,
)
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.system.quick_access_catalogue import (
    addable_quick_access_catalogue,
    quick_access_catalogue_entry,
)
from src.system.quick_access_preferences import (
    DEFAULT_QUICK_ACCESS_ITEMS,
    MAX_ITEMS,
    QuickAccessItem,
    QuickAccessPreferences,
)
from src.ui.quick_access_picker import (
    QuickAccessPickerDialog,
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


def _contrast_colour(
    colour: str,
) -> QColor:
    accent = QColor(
        colour
    )

    if not accent.isValid():
        return QColor(
            "#0b1020"
        )

    red = accent.redF()
    green = accent.greenF()
    blue = accent.blueF()

    luminance = (
        0.2126 * red
        + 0.7152 * green
        + 0.0722 * blue
    )

    return QColor(
        "#111116"
        if luminance >= 0.58
        else "#ffffff"
    )


class QuickAccessCheckBox(QCheckBox):
    def __init__(
        self,
        text: str,
        parent: QWidget | None = None,
    ):
        super().__init__(
            text,
            parent,
        )

        self._theme = dict(
            FALLBACK_THEME
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setMouseTracking(
            True
        )

    def set_theme(
        self,
        theme: dict,
    ) -> None:
        self._theme = _merged_theme(
            theme
        )

        self.update()

    def sizeHint(
        self,
    ) -> QSize:
        hint = super().sizeHint()

        width = (
            26
            + self.fontMetrics().horizontalAdvance(
                self.text()
            )
        )

        return QSize(
            max(
                hint.width(),
                width,
            ),
            max(
                hint.height(),
                26,
            ),
        )

    def paintEvent(
        self,
        event,
    ) -> None:
        del event

        theme = self._theme

        painter = QPainter(
            self
        )

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        indicator_size = 16.0
        indicator_x = 1.0
        indicator_y = (
            self.height()
            - indicator_size
        ) / 2.0

        accent = QColor(
            theme[
                "accent"
            ]
        )
        border = QColor(
            theme[
                "border"
            ]
        )
        card_alt = QColor(
            theme[
                "card_alt"
            ]
        )
        text = QColor(
            theme[
                "text"
            ]
        )
        muted = QColor(
            theme[
                "muted"
            ]
        )

        if (
            self.underMouse()
            or self.hasFocus()
        ):
            outline = accent
        else:
            outline = border

        painter.setPen(
            QPen(
                outline,
                1.2,
            )
        )

        painter.setBrush(
            accent
            if self.isChecked()
            else card_alt
        )

        painter.drawRoundedRect(
            QRectF(
                indicator_x,
                indicator_y,
                indicator_size,
                indicator_size,
            ),
            4.5,
            4.5,
        )

        if self.isChecked():
            check_pen = QPen(
                _contrast_colour(
                    theme[
                        "accent"
                    ]
                ),
                1.8,
            )

            check_pen.setCapStyle(
                Qt.PenCapStyle.RoundCap
            )

            check_pen.setJoinStyle(
                Qt.PenJoinStyle.RoundJoin
            )

            painter.setPen(
                check_pen
            )

            y = indicator_y

            painter.drawLine(
                5,
                int(
                    y + 8
                ),
                8,
                int(
                    y + 11
                ),
            )

            painter.drawLine(
                8,
                int(
                    y + 11
                ),
                14,
                int(
                    y + 5
                ),
            )

        painter.setPen(
            text
            if self.isEnabled()
            else muted
        )

        painter.setFont(
            self.font()
        )

        text_left = 26

        painter.drawText(
            text_left,
            0,
            max(
                0,
                self.width()
                - text_left,
            ),
            self.height(),
            int(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
            ),
            self.text(),
        )

        painter.end()


class QuickAccessManagerDialog(QDialog):
    def __init__(
        self,
        preferences: QuickAccessPreferences,
        theme: dict | None = None,
        parent: QWidget | None = None,
        *,
        dynamic_items: Iterable[QuickAccessItem] = (),
    ):
        super().__init__(
            parent
        )

        if not isinstance(
            preferences,
            QuickAccessPreferences,
        ):
            raise TypeError(
                "preferences must be "
                "QuickAccessPreferences."
            )

        self._theme = _merged_theme(
            theme
        )

        self.setObjectName(
            "quickAccessManagerDialog"
        )

        self.setWindowTitle(
            "Manage Quick Access"
        )

        self.setModal(
            True
        )

        self.setMinimumWidth(
            680
        )

        dynamic_items = tuple(
            dynamic_items
        )

        dynamic_items_by_id = {}

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
                in dynamic_items_by_id
            ):
                raise ValueError(
                    "Dynamic Quick Access items contain "
                    "duplicate IDs."
                )

            dynamic_items_by_id[
                dynamic_item.item_id
            ] = dynamic_item

        self._dynamic_items_by_id = (
            dynamic_items_by_id
        )

        refreshed_items = []

        for item in preferences.items:
            live_item = None

            if (
                item.kind
                in {
                    "presence_preset",
                    "presence_mode",
                    "launcher_card",
                    "spotify_playlist",
                }
            ):
                live_item = (
                    self._dynamic_items_by_id.get(
                        item.item_id
                    )
                )

            if live_item is None:
                refreshed_items.append(
                    item
                )
                continue

            refreshed_items.append(
                replace(
                    live_item,
                    visible=item.visible,
                )
            )

        self._items = refreshed_items

        self._rows = []

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
            13
        )

        title = QLabel(
            "QUICK ACCESS"
        )

        title.setObjectName(
            "dialogTitle"
        )

        description = QLabel(
            "Choose what appears on the Dashboard "
            "and arrange the shortcuts in the order "
            "you want."
        )

        description.setObjectName(
            "dialogDescription"
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

        self.items_container = QFrame()

        self.items_container.setObjectName(
            "quickAccessManagerItems"
        )

        self.items_layout = QVBoxLayout(
            self.items_container
        )

        self.items_layout.setContentsMargins(
            0,
            2,
            0,
            2,
        )

        self.items_layout.setSpacing(
            9
        )

        root.addWidget(
            self.items_container
        )

        controls = QHBoxLayout()

        controls.setSpacing(
            9
        )

        self.add_button = QPushButton(
            "Add shortcut"
        )

        self.add_button.setObjectName(
            "secondaryButton"
        )

        self.add_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.add_button.setMinimumWidth(
            112
        )

        self.add_button.setToolTip(
            "Add another destination to Quick Access"
        )

        self.add_button.clicked.connect(
            lambda checked=False:
            self._open_add_shortcut_picker()
        )

        controls.addWidget(
            self.add_button
        )

        self.reset_button = QPushButton(
            "Reset defaults"
        )

        self.reset_button.setObjectName(
            "secondaryButton"
        )

        self.reset_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.reset_button.setMinimumWidth(
            112
        )

        self.reset_button.clicked.connect(
            self._reset_defaults
        )

        controls.addWidget(
            self.reset_button
        )

        controls.addStretch()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        self.save_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )

        if self.save_button is not None:
            self.save_button.setText(
                "Save"
            )

            self.save_button.setObjectName(
                "primaryButton"
            )

            self.save_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            self.save_button.setMinimumWidth(
                88
            )

        self.cancel_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )

        if self.cancel_button is not None:
            self.cancel_button.setObjectName(
                "secondaryButton"
            )

            self.cancel_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            self.cancel_button.setMinimumWidth(
                88
            )

        self.buttons.accepted.connect(
            self.accept
        )

        self.buttons.rejected.connect(
            self.reject
        )

        controls.addWidget(
            self.buttons
        )

        root.addLayout(
            controls
        )

        self._rebuild_rows()
        self.apply_theme(
            self._theme
        )

    def _clear_rows(
        self,
    ) -> None:
        while self.items_layout.count():
            layout_item = (
                self.items_layout.takeAt(
                    0
                )
            )

            widget = (
                layout_item.widget()
            )

            if widget is not None:
                widget.deleteLater()

        self._rows = []

    def _rebuild_rows(
        self,
    ) -> None:
        self._clear_rows()

        item_count = len(
            self._items
        )

        for index, item in enumerate(
            self._items
        ):
            row = QFrame()

            row.setObjectName(
                "quickAccessManagerRow"
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
                10
            )

            visible_box = QuickAccessCheckBox(
                item.title
            )

            visible_box.setObjectName(
                "quickAccessManagerVisible"
            )

            visible_box.setChecked(
                item.visible
            )

            visible_box.setToolTip(
                (
                    "Show "
                    + item.title
                    + " in Quick Access"
                )
            )

            visible_box.set_theme(
                self._theme
            )

            detail = QLabel(
                item.detail
            )

            detail.setObjectName(
                "quickAccessManagerDetail"
            )

            detail.setWordWrap(
                True
            )

            up_button = QPushButton(
                "Up"
            )

            up_button.setObjectName(
                "secondaryButton"
            )

            up_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            up_button.setMinimumWidth(
                64
            )

            up_button.setEnabled(
                index > 0
            )

            up_button.clicked.connect(
                lambda checked=False,
                row_index=index:
                self._move_item(
                    row_index,
                    -1,
                )
            )

            down_button = QPushButton(
                "Down"
            )

            down_button.setObjectName(
                "secondaryButton"
            )

            down_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            down_button.setMinimumWidth(
                64
            )

            down_button.setEnabled(
                index < item_count - 1
            )

            down_button.clicked.connect(
                lambda checked=False,
                row_index=index:
                self._move_item(
                    row_index,
                    1,
                )
            )

            remove_button = QPushButton(
                "Remove"
            )

            remove_button.setObjectName(
                "secondaryButton"
            )

            remove_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            remove_button.setMinimumWidth(
                76
            )

            remove_button.setToolTip(
                "Remove this shortcut"
            )

            remove_button.clicked.connect(
                lambda checked=False,
                row_index=index:
                self._remove_item(
                    row_index
                )
            )

            row_layout.addWidget(
                visible_box
            )

            row_layout.addWidget(
                detail,
                stretch=1,
            )

            row_layout.addWidget(
                up_button
            )

            row_layout.addWidget(
                down_button
            )

            row_layout.addWidget(
                remove_button
            )

            self.items_layout.addWidget(
                row
            )

            self._rows.append(
                {
                    "item_id": item.item_id,
                    "row": row,
                    "visible": visible_box,
                    "detail": detail,
                    "up": up_button,
                    "down": down_button,
                    "remove": remove_button,
                }
            )

        self.items_layout.addStretch()

        for row in self._rows:
            row[
                "visible"
            ].set_theme(
                self._theme
            )

        self._update_add_button_state()


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

        accent_text = (
            _contrast_colour(
                accent
            ).name()
        )

        self.setStyleSheet(
            f"""
            QDialog#quickAccessManagerDialog {{
                background: {background};
                color: {text};
            }}

            QLabel#dialogTitle {{
                background: transparent;
                color: {accent};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#dialogDescription {{
                background: transparent;
                color: {muted};
                font-size: 12px;
            }}

            QFrame#quickAccessManagerItems {{
                background: transparent;
                border: none;
            }}

            QFrame#quickAccessManagerRow {{
                background: {card};
                border: 1px solid {border};
                border-radius: 10px;
            }}

            QLabel#quickAccessManagerDetail {{
                background: transparent;
                color: {muted};
                font-size: 11px;
            }}

            QCheckBox#quickAccessManagerVisible {{
                background: transparent;
                color: {text};
                font-weight: 600;
                spacing: 8px;
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

            QPushButton#secondaryButton:pressed {{
                background: {card};
            }}

            QPushButton#secondaryButton:disabled {{
                color: {muted};
                background: {card};
                border: 1px solid {border};
            }}

            QPushButton#primaryButton {{
                min-height: 28px;
                padding: 0 15px;
                color: {accent_text};
                background: {accent};
                border: 1px solid {accent};
                border-radius: 8px;
                font-weight: 600;
            }}

            QPushButton#primaryButton:hover {{
                border: 1px solid {text};
            }}

            QPushButton#primaryButton:pressed {{
                background: {card_alt};
                color: {accent};
                border: 1px solid {accent};
            }}

            QDialogButtonBox {{
                background: transparent;
            }}
            """
        )

        for row in self._rows:
            row[
                "visible"
            ].set_theme(
                self._theme
            )

    def _addable_entries(
        self,
    ):
        if len(
            self._items
        ) >= MAX_ITEMS:
            return ()

        existing_ids = {
            item.item_id
            for item in self._items
        }

        static_entries = tuple(
            addable_quick_access_catalogue(
                existing_ids
            )
        )

        dynamic_entries = tuple(
            item
            for item
            in self._dynamic_items_by_id.values()
            if (
                item.item_id
                not in existing_ids
            )
        )

        return (
            static_entries
            + dynamic_entries
        )

    def _update_add_button_state(
        self,
    ) -> None:
        add_button = getattr(
            self,
            "add_button",
            None,
        )

        if add_button is None:
            return

        add_button.setEnabled(
            bool(
                self._addable_entries()
            )
        )

    def _add_item(
        self,
        item_id: str,
    ) -> bool:
        self._sync_visibility()

        if len(
            self._items
        ) >= MAX_ITEMS:
            return False

        normalized = str(
            item_id
            or ""
        ).strip().casefold()

        entry = quick_access_catalogue_entry(
            normalized
        )

        if entry is None:
            entry = (
                self._dynamic_items_by_id.get(
                    normalized
                )
            )

        if entry is None:
            return False

        existing_ids = {
            item.item_id
            for item in self._items
        }

        if entry.item_id in existing_ids:
            return False

        self._items.append(
            QuickAccessItem(
                item_id=entry.item_id,
                kind=entry.kind,
                target=entry.target,
                title=entry.title,
                detail=entry.detail,
                icon_key=entry.icon_key,
                visible=True,
            )
        )

        self._rebuild_rows()

        return True

    def _remove_item(
        self,
        index: int,
    ) -> bool:
        self._sync_visibility()

        if not (
            0
            <= int(
                index
            )
            < len(
                self._items
            )
        ):
            return False

        self._items.pop(
            int(
                index
            )
        )

        self._rebuild_rows()

        return True

    def _open_add_shortcut_picker(
        self,
    ) -> None:
        self._sync_visibility()

        dialog = QuickAccessPickerDialog(
            [
                item.item_id
                for item in self._items
            ],
            theme=self._theme,
            parent=self,
            dynamic_items=tuple(
                self._dynamic_items_by_id.values()
            ),
        )

        if not dialog.exec():
            return

        selected_item_id = (
            dialog.selected_item_id()
        )

        if not selected_item_id:
            return

        self._add_item(
            selected_item_id
        )

    def _sync_visibility(
        self,
    ) -> None:
        visible_by_id = {
            row["item_id"]:
            row["visible"].isChecked()
            for row in self._rows
        }

        self._items = [
            replace(
                item,
                visible=visible_by_id.get(
                    item.item_id,
                    item.visible,
                ),
            )
            for item in self._items
        ]

    def _move_item(
        self,
        index: int,
        delta: int,
    ) -> None:
        self._sync_visibility()

        destination = (
            int(index)
            + int(delta)
        )

        if not (
            0
            <= index
            < len(self._items)
        ):
            return

        if not (
            0
            <= destination
            < len(self._items)
        ):
            return

        item = self._items.pop(
            index
        )

        self._items.insert(
            destination,
            item,
        )

        self._rebuild_rows()

    def _reset_defaults(
        self,
    ) -> None:
        self._items = list(
            DEFAULT_QUICK_ACCESS_ITEMS
        )

        self._rebuild_rows()

    def preferences(
        self,
    ) -> QuickAccessPreferences:
        self._sync_visibility()

        return QuickAccessPreferences(
            items=tuple(
                self._items
            )
        )
