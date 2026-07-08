from datetime import datetime

from PyQt6.QtCore import (
    Qt,
    pyqtSlot,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.theme import ThemeManager


class LibraryPage(QWidget):
    def __init__(
        self,
        theme_manager=None,
    ):
        super().__init__()

        self.setObjectName("libraryRoot")

        self.theme_manager = (
            theme_manager
            or ThemeManager(self)
        )

        self._last_track_key = None
        self._track_count = 0

        self.build_ui()

        self.theme_manager.theme_changed.connect(
            self.apply_theme
        )

        self.apply_theme(
            self.theme_manager.theme()
        )

        self.update_library_state()

    def build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )
        self.root_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(1)

        self.page_title = QLabel("Library")
        self.page_title.setObjectName(
            "libraryTitle"
        )

        self.page_subtitle = QLabel(
            "Songs played during this session"
        )
        self.page_subtitle.setObjectName(
            "librarySubtitle"
        )

        title_layout.addWidget(
            self.page_title
        )
        title_layout.addWidget(
            self.page_subtitle
        )

        self.track_badge = QLabel(
            "0 TRACKS"
        )
        self.track_badge.setObjectName(
            "trackBadge"
        )
        self.track_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.clear_button = QPushButton(
            "Clear history"
        )
        self.clear_button.setObjectName(
            "clearButton"
        )
        self.clear_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.clear_button.clicked.connect(
            self.clear_history
        )

        header_layout.addLayout(
            title_layout
        )
        header_layout.addStretch()
        header_layout.addWidget(
            self.track_badge,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        header_layout.addWidget(
            self.clear_button,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )

        self.root_layout.addLayout(
            header_layout
        )

        self.status_card = QFrame()
        self.status_card.setObjectName(
            "statusCard"
        )

        status_layout = QHBoxLayout(
            self.status_card
        )
        status_layout.setContentsMargins(
            14,
            10,
            14,
            10,
        )
        status_layout.setSpacing(8)

        status_dot = QLabel("●")
        status_dot.setObjectName(
            "statusDot"
        )

        status_title = QLabel(
            "Latest activity"
        )
        status_title.setObjectName(
            "statusTitle"
        )

        self.latest_status = QLabel(
            "Waiting for Spotify"
        )
        self.latest_status.setObjectName(
            "latestStatus"
        )

        status_layout.addWidget(
            status_dot
        )
        status_layout.addWidget(
            status_title
        )
        status_layout.addStretch()
        status_layout.addWidget(
            self.latest_status
        )

        self.root_layout.addWidget(
            self.status_card
        )

        self.library_card = QFrame()
        self.library_card.setObjectName(
            "libraryCard"
        )

        card_layout = QVBoxLayout(
            self.library_card
        )
        card_layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )
        card_layout.setSpacing(8)

        self.empty_label = QLabel(
            "No songs have been played yet.\n"
            "Start Spotify and your session history "
            "will appear here."
        )
        self.empty_label.setObjectName(
            "emptyLibrary"
        )
        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.empty_label.setWordWrap(True)

        self.table = QTableWidget(0, 5)
        self.table.setObjectName(
            "historyTable"
        )

        self.table.setHorizontalHeaderLabels(
            [
                "Song",
                "Artist",
                "Album",
                "Status",
                "Last played",
            ]
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(
            False
        )
        self.table.setShowGrid(False)

        header = self.table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        card_layout.addWidget(
            self.empty_label
        )
        card_layout.addWidget(
            self.table,
            stretch=1,
        )

        self.root_layout.addWidget(
            self.library_card,
            stretch=1,
        )

    @pyqtSlot(dict)
    def apply_theme(self, theme: dict):
        compact = theme.get(
            "compact",
            True,
        )

        margin = 18 if compact else 24
        spacing = 10 if compact else 14
        title_size = 23 if compact else 27
        row_height = 34 if compact else 42
        header_height = 34 if compact else 40

        self.root_layout.setContentsMargins(
            margin,
            margin,
            margin,
            margin,
        )

        self.root_layout.setSpacing(
            spacing
        )

        self.table.verticalHeader().setDefaultSectionSize(
            row_height
        )

        self.table.horizontalHeader().setFixedHeight(
            header_height
        )

        self.setStyleSheet(
            f"""
            QWidget#libraryRoot {{
                background: {theme["background"]};
            }}

            QLabel#libraryTitle {{
                color: {theme["text"]};
                font-size: {title_size}px;
                font-weight: 700;
            }}

            QLabel#librarySubtitle {{
                color: {theme["muted"]};
                font-size: 11px;
            }}

            QLabel#trackBadge {{
                color: {theme["accent"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 5px 10px;
                font-size: 10px;
                font-weight: 700;
            }}

            QPushButton#clearButton {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 7px 12px;
                font-size: 10px;
                font-weight: 650;
            }}

            QPushButton#clearButton:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QPushButton#clearButton:pressed {{
                background: {theme["background"]};
            }}

            QPushButton#clearButton:disabled {{
                color: {theme["muted"]};
                background: {theme["background"]};
                border-color: {theme["border"]};
            }}

            QFrame#statusCard {{
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
            }}

            QLabel#statusDot {{
                color: {theme["accent"]};
                font-size: 9px;
            }}

            QLabel#statusTitle {{
                color: {theme["muted"]};
                font-size: 10px;
            }}

            QLabel#latestStatus {{
                color: {theme["text"]};
                font-size: 10px;
                font-weight: 650;
            }}

            QFrame#libraryCard {{
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}

            QLabel#emptyLibrary {{
                color: {theme["muted"]};
                font-size: 12px;
                padding: 30px;
            }}

            QTableWidget#historyTable {{
                color: {theme["text"]};
                background: transparent;
                alternate-background-color: {theme["card_alt"]};
                border: none;
                selection-color: {theme["text"]};
                selection-background-color: {theme["accent"]};
                gridline-color: {theme["border"]};
                font-size: 11px;
                outline: none;
            }}

            QTableWidget#historyTable::item {{
                padding-left: 9px;
                padding-right: 9px;
                border-bottom: 1px solid {theme["border"]};
            }}

            QTableWidget#historyTable::item:selected {{
                color: {theme["text"]};
                background: {theme["accent"]};
            }}

            QHeaderView::section {{
                color: {theme["accent"]};
                background: {theme["card_alt"]};
                border: none;
                border-bottom: 1px solid {theme["border"]};
                padding-left: 9px;
                padding-right: 9px;
                font-size: 10px;
                font-weight: 700;
            }}

            QScrollBar:vertical {{
                background: {theme["background"]};
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }}

            QScrollBar::handle:vertical {{
                background: {theme["border"]};
                min-height: 28px;
                border-radius: 5px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {theme["accent"]};
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}

            QScrollBar:horizontal {{
                background: {theme["background"]};
                height: 10px;
                margin: 0px;
                border-radius: 5px;
            }}

            QScrollBar::handle:horizontal {{
                background: {theme["border"]};
                min-width: 28px;
                border-radius: 5px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background: {theme["accent"]};
            }}

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            """
        )

    def add_song(self, song):
        if song is None:
            return

        title = str(
            getattr(song, "title", "")
            or ""
        ).strip()

        artist = str(
            getattr(song, "artist", "")
            or ""
        ).strip()

        album = str(
            getattr(song, "album", "")
            or ""
        ).strip()

        ignored_titles = {
            "unknown title",
            "nothing playing",
            "waiting for media...",
        }

        if (
            not title
            or title.lower() in ignored_titles
        ):
            return

        track_key = (
            title.lower(),
            artist.lower(),
            album.lower(),
        )

        is_playing = bool(
            getattr(song, "playing", False)
        )

        status = (
            "Playing"
            if is_playing
            else "Paused"
        )

        played_time = (
            datetime.now().strftime(
                "%H:%M:%S"
            )
        )

        if (
            track_key == self._last_track_key
            and self.table.rowCount() > 0
        ):
            status_item = self.table.item(
                0,
                3,
            )

            time_item = self.table.item(
                0,
                4,
            )

            if status_item is not None:
                status_item.setText(
                    status
                )

            if time_item is not None:
                time_item.setText(
                    played_time
                )

            self.latest_status.setText(
                f"{status}: {title}"
            )

            self.update_library_state()
            return

        self._last_track_key = track_key

        self.table.insertRow(0)

        values = [
            title,
            artist or "Unknown artist",
            album or "No album",
            status,
            played_time,
        ]

        for column, value in enumerate(
            values
        ):
            item = QTableWidgetItem(
                value
            )

            item.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter
                | Qt.AlignmentFlag.AlignLeft
            )

            if column == 3:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

            self.table.setItem(
                0,
                column,
                item,
            )

        while self.table.rowCount() > 100:
            last_row = (
                self.table.rowCount() - 1
            )

            self.table.removeRow(
                last_row
            )

        self._track_count = (
            self.table.rowCount()
        )

        self.latest_status.setText(
            f"{status}: {title}"
        )

        self.update_library_state()

    def update_library_state(self):
        count = self.table.rowCount()

        self._track_count = count

        if count == 1:
            badge_text = "1 TRACK"
        else:
            badge_text = (
                f"{count} TRACKS"
            )

        self.track_badge.setText(
            badge_text
        )

        has_history = count > 0

        self.table.setVisible(
            has_history
        )

        self.empty_label.setVisible(
            not has_history
        )

        self.clear_button.setEnabled(
            has_history
        )

        if not has_history:
            self.latest_status.setText(
                "Waiting for Spotify"
            )

    def clear_history(self):
        self.table.clearContents()
        self.table.setRowCount(0)

        self._last_track_key = None
        self._track_count = 0

        self.latest_status.setText(
            "History cleared"
        )

        self.update_library_state()