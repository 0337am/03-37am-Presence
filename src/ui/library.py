from datetime import datetime, timedelta

from PyQt6.QtCore import (
    Qt,
    pyqtSlot,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.library.history_store import (
    HistoryStore,
    HistoryTrack,
)
from src.ui.theme import ThemeManager


class LibraryPage(QWidget):
    def __init__(
        self,
        theme_manager=None,
    ):
        super().__init__()

        self.setObjectName(
            "libraryRoot"
        )

        self.theme_manager = (
            theme_manager
            or ThemeManager(self)
        )

        self.history_store = (
            HistoryStore()
        )

        self._last_track_key = None
        self._last_status = None
        self._current_track_event_recorded = False

        self._page_size = 50
        self._page_offset = 0
        self._query_total_tracks = 0

        self.build_ui()
        self.connect_signals()

        self.theme_manager.theme_changed.connect(
            self.apply_theme
        )

        self.apply_theme(
            self.theme_manager.theme()
        )

        self.load_history()

    def build_ui(self):
        self.root_layout = QVBoxLayout(
            self
        )
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

        self.page_title = QLabel(
            "Library"
        )
        self.page_title.setObjectName(
            "libraryTitle"
        )

        self.page_subtitle = QLabel(
            "Your persistent listening history"
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

        self.play_badge = QLabel(
            "0 PLAYS"
        )
        self.play_badge.setObjectName(
            "playBadge"
        )
        self.play_badge.setAlignment(
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

        header_layout.addLayout(
            title_layout
        )
        header_layout.addStretch()
        header_layout.addWidget(
            self.track_badge,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        header_layout.addWidget(
            self.play_badge,
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

        status_dot = QLabel(
            "\u25cf"
        )
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
            "Waiting for media"
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

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setObjectName(
            "librarySearch"
        )
        self.search_input.setPlaceholderText(
            "Search songs, artists, albums, or sources"
        )
        self.search_input.setClearButtonEnabled(
            True
        )

        self.refresh_button = QPushButton(
            "Refresh"
        )
        self.refresh_button.setObjectName(
            "secondaryButton"
        )
        self.refresh_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.source_filter = QComboBox()
        self.source_filter.setObjectName(
            "libraryFilter"
        )
        self.source_filter.setMinimumWidth(
            132
        )

        source_options = (
            ("All sources", "all"),
            ("Spotify", "spotify"),
            ("SoundCloud", "soundcloud"),
            ("Chrome", "chrome"),
            ("Edge", "edge"),
            ("Firefox", "firefox"),
            ("Brave", "brave"),
            ("Opera", "opera"),
            ("Vivaldi", "vivaldi"),
            ("Other", "other"),
        )

        for label, value in source_options:
            self.source_filter.addItem(
                label,
                value,
            )

        self.sort_box = QComboBox()
        self.sort_box.setObjectName(
            "libraryFilter"
        )
        self.sort_box.setMinimumWidth(
            140
        )

        sort_options = (
            ("Newest first", "newest"),
            ("Oldest first", "oldest"),
            ("Most played", "most_played"),
            ("Title A–Z", "title"),
            ("Artist A–Z", "artist"),
        )

        for label, value in sort_options:
            self.sort_box.addItem(
                label,
                value,
            )

        self.date_range_box = QComboBox()
        self.date_range_box.setObjectName(
            "libraryFilter"
        )
        self.date_range_box.setMinimumWidth(
            126
        )
        self.date_range_box.setAccessibleName(
            "Library date range"
        )

        date_range_options = (
            ("All time", "all"),
            ("Today", "today"),
            ("Last 7 days", "last_7"),
            ("Last 30 days", "last_30"),
            ("This year", "this_year"),
        )

        for label, value in date_range_options:
            self.date_range_box.addItem(
                label,
                value,
            )

        controls_layout.addWidget(
            self.search_input,
            stretch=1,
        )
        controls_layout.addWidget(
            self.source_filter
        )
        controls_layout.addWidget(
            self.sort_box
        )
        controls_layout.addWidget(
            self.date_range_box
        )
        controls_layout.addWidget(
            self.refresh_button
        )

        self.root_layout.addLayout(
            controls_layout
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
            "No listening history yet.\n"
            "Play something and it will appear here."
        )
        self.empty_label.setObjectName(
            "emptyLibrary"
        )
        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.empty_label.setWordWrap(True)

        self.table = QTableWidget(
            0,
            6,
        )
        self.table.setObjectName(
            "historyTable"
        )

        self.table.setHorizontalHeaderLabels(
            [
                "Song",
                "Artist",
                "Album",
                "Source",
                "Plays",
                "Last played",
            ]
        )

        self.table.setSelectionBehavior(
            QAbstractItemView
            .SelectionBehavior
            .SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView
            .SelectionMode
            .SingleSelection
        )

        self.table.setEditTriggers(
            QAbstractItemView
            .EditTrigger
            .NoEditTriggers
        )

        self.table.setAlternatingRowColors(
            True
        )

        self.table.verticalHeader().setVisible(
            False
        )

        self.table.setShowGrid(
            False
        )

        header = (
            self.table.horizontalHeader()
        )

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

        header.setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        card_layout.addWidget(
            self.empty_label
        )

        card_layout.addWidget(
            self.table,
            stretch=1,
        )

        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(8)

        self.result_summary = QLabel(
            "0 results"
        )
        self.result_summary.setObjectName(
            "resultSummary"
        )

        self.previous_button = QPushButton(
            "Previous"
        )
        self.previous_button.setObjectName(
            "secondaryButton"
        )
        self.previous_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.previous_button.setAccessibleName(
            "Previous Library page"
        )

        self.next_button = QPushButton(
            "Next"
        )
        self.next_button.setObjectName(
            "secondaryButton"
        )
        self.next_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.next_button.setAccessibleName(
            "Next Library page"
        )

        pagination_layout.addWidget(
            self.result_summary
        )
        pagination_layout.addStretch()
        pagination_layout.addWidget(
            self.previous_button
        )
        pagination_layout.addWidget(
            self.next_button
        )

        card_layout.addLayout(
            pagination_layout
        )

        self.root_layout.addWidget(
            self.library_card,
            stretch=1,
        )

    def connect_signals(self):
        self.search_input.textChanged.connect(
            self.reset_pagination_and_load
        )

        self.refresh_button.clicked.connect(
            self.load_history
        )

        self.source_filter.currentIndexChanged.connect(
            self.reset_pagination_and_load
        )

        self.sort_box.currentIndexChanged.connect(
            self.reset_pagination_and_load
        )

        self.date_range_box.currentIndexChanged.connect(
            self.reset_pagination_and_load
        )

        self.previous_button.clicked.connect(
            self.previous_page
        )

        self.next_button.clicked.connect(
            self.next_page
        )

        self.clear_button.clicked.connect(
            self.clear_history
        )

    @pyqtSlot(dict)
    def apply_theme(
        self,
        theme: dict,
    ):
        compact = theme.get(
            "compact",
            True,
        )

        margin = (
            18 if compact else 24
        )

        spacing = (
            10 if compact else 14
        )

        title_size = (
            23 if compact else 27
        )

        row_height = (
            34 if compact else 42
        )

        header_height = (
            34 if compact else 40
        )

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

            QLabel#trackBadge,
            QLabel#playBadge {{
                color: {theme["accent"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 5px 10px;
                font-size: 10px;
                font-weight: 700;
            }}

            QPushButton#clearButton,
            QPushButton#secondaryButton {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 7px 12px;
                font-size: 10px;
                font-weight: 650;
            }}

            QPushButton#clearButton:hover,
            QPushButton#secondaryButton:hover {{
                border: 1px solid {theme["accent"]};
            }}

            QPushButton#clearButton:pressed,
            QPushButton#secondaryButton:pressed {{
                background: {theme["background"]};
            }}

            QPushButton#clearButton:disabled,
            QPushButton#secondaryButton:disabled {{
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

            QLineEdit#librarySearch,
            QComboBox#libraryFilter {{
                color: {theme["text"]};
                background: {theme["card_alt"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 8px 11px;
                font-size: 11px;
                selection-background-color: {theme["accent"]};
            }}

            QLineEdit#librarySearch:hover,
            QLineEdit#librarySearch:focus,
            QComboBox#libraryFilter:hover,
            QComboBox#libraryFilter:focus {{
                border: 1px solid {theme["accent"]};
            }}

            QComboBox#libraryFilter::drop-down {{
                border: none;
                width: 22px;
            }}

            QComboBox#libraryFilter QAbstractItemView {{
                color: {theme["text"]};
                background: {theme["card"]};
                border: 1px solid {theme["border"]};
                selection-color: {theme["text"]};
                selection-background-color: {theme["accent"]};
                outline: none;
            }}

            QLabel#resultSummary {{
                color: {theme["muted"]};
                font-size: 10px;
                font-weight: 600;
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

    def load_history(
        self,
        *_,
    ):
        search_text = (
            self.search_input.text().strip()
        )

        source_filter = str(
            self.source_filter.currentData()
            or "all"
        )

        sort_mode = str(
            self.sort_box.currentData()
            or "newest"
        )

        date_range = str(
            self.date_range_box.currentData()
            or "all"
        )

        date_from, date_to = (
            self._date_range_bounds(
                date_range
            )
        )

        result = self.history_store.query_tracks(
            search_text=search_text,
            source_filter=source_filter,
            sort_mode=sort_mode,
            date_from=date_from,
            date_to=date_to,
            limit=self._page_size,
            offset=self._page_offset,
        )

        corrected_offset = (
            self._normalise_page_offset(
                total_tracks=result.total_tracks,
                page_size=self._page_size,
                offset=self._page_offset,
            )
        )

        if corrected_offset != self._page_offset:
            self._page_offset = corrected_offset

            result = self.history_store.query_tracks(
                search_text=search_text,
                source_filter=source_filter,
                sort_mode=sort_mode,
                date_from=date_from,
                date_to=date_to,
                limit=self._page_size,
                offset=self._page_offset,
            )

        tracks = list(
            result.tracks
        )

        self._query_total_tracks = (
            result.total_tracks
        )

        self.populate_table(
            tracks
        )

        self.track_badge.setText(
            self._format_count(
                result.total_tracks,
                "TRACK",
                "TRACKS",
            )
        )

        self.play_badge.setText(
            self._format_count(
                result.total_plays,
                "PLAY",
                "PLAYS",
            )
        )

        total_library_tracks = (
            self.history_store.count_tracks()
        )

        has_results = bool(tracks)

        self.table.setVisible(
            has_results
        )

        self.empty_label.setVisible(
            not has_results
        )

        self.clear_button.setEnabled(
            total_library_tracks > 0
        )

        self.previous_button.setEnabled(
            self._page_offset > 0
        )

        self.next_button.setEnabled(
            result.has_more
        )

        self.result_summary.setText(
            self._page_summary(
                total_tracks=result.total_tracks,
                offset=self._page_offset,
                row_count=len(tracks),
            )
        )

        if not has_results:
            filters_active = (
                bool(search_text)
                or source_filter != "all"
                or date_range != "all"
            )

            if filters_active:
                self.empty_label.setText(
                    "No tracks match the current filters."
                )
            else:
                self.empty_label.setText(
                    "No listening history yet.\n"
                    "Play something and it will appear here."
                )

        latest_tracks = (
            self.history_store.list_tracks(
                limit=1,
            )
        )

        if latest_tracks:
            latest = latest_tracks[0]

            self.latest_status.setText(
                f"{latest.last_status}: "
                f"{latest.title}"
            )

        elif not search_text:
            self.latest_status.setText(
                "Waiting for media"
            )

    def reset_pagination_and_load(
        self,
        *_,
    ):
        self._page_offset = 0
        self.load_history()

    def previous_page(
        self,
        *_,
    ):
        self._page_offset = max(
            0,
            self._page_offset
            - self._page_size,
        )

        self.load_history()

    def next_page(
        self,
        *_,
    ):
        next_offset = (
            self._page_offset
            + self._page_size
        )

        if next_offset >= self._query_total_tracks:
            return

        self._page_offset = next_offset
        self.load_history()

    @staticmethod
    def _date_range_bounds(
        selected_range: str,
        today=None,
    ) -> tuple[str, str]:
        selected = str(
            selected_range
            or "all"
        ).strip().lower()

        reference = (
            today
            if today is not None
            else datetime.now()
        )

        current_date = (
            reference.date()
            if isinstance(
                reference,
                datetime,
            )
            else reference
        )

        if selected == "today":
            start_date = current_date

        elif selected == "last_7":
            start_date = (
                current_date
                - timedelta(days=6)
            )

        elif selected == "last_30":
            start_date = (
                current_date
                - timedelta(days=29)
            )

        elif selected == "this_year":
            start_date = current_date.replace(
                month=1,
                day=1,
            )

        else:
            return "", ""

        return (
            start_date.strftime(
                "%Y-%m-%d"
            ),
            current_date.strftime(
                "%Y-%m-%d"
            ),
        )

    @staticmethod
    def _normalise_page_offset(
        *,
        total_tracks: int,
        page_size: int,
        offset: int,
    ) -> int:
        safe_total = max(
            0,
            int(total_tracks),
        )

        safe_page_size = max(
            1,
            int(page_size),
        )

        safe_offset = max(
            0,
            int(offset),
        )

        if safe_total == 0:
            return 0

        maximum_offset = (
            (safe_total - 1)
            // safe_page_size
            * safe_page_size
        )

        aligned_offset = (
            safe_offset
            // safe_page_size
            * safe_page_size
        )

        return min(
            aligned_offset,
            maximum_offset,
        )

    @staticmethod
    def _page_summary(
        *,
        total_tracks: int,
        offset: int,
        row_count: int,
    ) -> str:
        safe_total = max(
            0,
            int(total_tracks),
        )

        safe_offset = max(
            0,
            int(offset),
        )

        safe_rows = max(
            0,
            int(row_count),
        )

        if safe_total == 0 or safe_rows == 0:
            return "0 results"

        first_result = safe_offset + 1

        last_result = min(
            safe_total,
            safe_offset + safe_rows,
        )

        return (
            f"Showing {first_result}-"
            f"{last_result} of {safe_total}"
        )

    def _matches_source_filter(
        self,
        track: HistoryTrack,
        selected_filter: str,
    ) -> bool:
        selected = str(
            selected_filter or "all"
        ).strip().lower()

        if selected == "all":
            return True

        display_source = self._display_source(
            track.source_app
        ).strip().lower()

        known_sources = {
            "spotify",
            "soundcloud",
            "chrome",
            "edge",
            "firefox",
            "brave",
            "opera",
            "vivaldi",
        }

        if selected == "other":
            return (
                display_source
                not in known_sources
            )

        return (
            display_source == selected
        )

    @staticmethod
    def _sort_tracks(
        tracks: list[HistoryTrack],
        sort_mode: str,
    ) -> list[HistoryTrack]:
        selected = str(
            sort_mode or "newest"
        ).strip().lower()

        sorted_tracks = list(
            tracks
        )

        if selected == "oldest":
            sorted_tracks.sort(
                key=lambda track: (
                    track.last_played,
                    track.track_id,
                )
            )

        elif selected == "most_played":
            sorted_tracks.sort(
                key=lambda track: (
                    -track.play_count,
                    track.title.lower(),
                    track.artist.lower(),
                )
            )

        elif selected == "title":
            sorted_tracks.sort(
                key=lambda track: (
                    track.title.lower(),
                    track.artist.lower(),
                    track.last_played,
                )
            )

        elif selected == "artist":
            sorted_tracks.sort(
                key=lambda track: (
                    track.artist.lower(),
                    track.title.lower(),
                    track.last_played,
                )
            )

        else:
            sorted_tracks.sort(
                key=lambda track: (
                    track.last_played,
                    track.track_id,
                ),
                reverse=True,
            )

        return sorted_tracks

    def populate_table(
        self,
        tracks: list[HistoryTrack],
    ):
        self.table.setUpdatesEnabled(
            False
        )

        try:
            self.table.clearContents()
            self.table.setRowCount(
                len(tracks)
            )

            for row, track in enumerate(
                tracks
            ):
                values = [
                    track.title,
                    track.artist,
                    track.album,
                    self._display_source(
                        track.source_app
                    ),
                    str(track.play_count),
                    self._format_timestamp(
                        track.last_played
                    ),
                ]

                for column, value in enumerate(
                    values
                ):
                    item = QTableWidgetItem(
                        value
                    )

                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        track.track_id,
                    )

                    alignment = (
                        Qt.AlignmentFlag.AlignVCenter
                        | Qt.AlignmentFlag.AlignLeft
                    )

                    if column in {
                        3,
                        4,
                    }:
                        alignment = (
                            Qt.AlignmentFlag.AlignCenter
                        )

                    item.setTextAlignment(
                        alignment
                    )

                    self.table.setItem(
                        row,
                        column,
                        item,
                    )

        finally:
            self.table.setUpdatesEnabled(
                True
            )

    def add_song(
        self,
        song,
    ):
        if song is None:
            return

        title = str(
            getattr(
                song,
                "title",
                "",
            )
            or ""
        ).strip()

        artist = str(
            getattr(
                song,
                "artist",
                "",
            )
            or ""
        ).strip()

        album = str(
            getattr(
                song,
                "album",
                "",
            )
            or ""
        ).strip()

        source_app = str(
            getattr(
                song,
                "source_app",
                "",
            )
            or ""
        ).strip()

        ignored_titles = {
            "unknown title",
            "nothing playing",
            "waiting for media...",
        }

        if (
            not title
            or title.lower()
            in ignored_titles
        ):
            return

        track_key = (
            title.lower(),
            artist.lower(),
            album.lower(),
            source_app.lower(),
        )

        status = (
            "Playing"
            if bool(
                getattr(
                    song,
                    "playing",
                    False,
                )
            )
            else "Paused"
        )

        if (
            track_key
            == self._last_track_key
        ):
            if (
                status
                != getattr(
                    self,
                    "_last_status",
                    None,
                )
            ):
                self.history_store.update_current(
                    song
                )

                if (
                    status == "Playing"
                    and not self
                    ._current_track_event_recorded
                ):
                    event_recorded = (
                        self.history_store
                        .record_event(song)
                    )

                    self._current_track_event_recorded = (
                        bool(event_recorded)
                    )

                self._last_status = status
                self.load_history()

            self.latest_status.setText(
                f"{status}: {title}"
            )
            return

        self.history_store.record_play(
            song
        )

        self._last_track_key = track_key
        self._last_status = status
        self._current_track_event_recorded = (
            status == "Playing"
        )

        self.latest_status.setText(
            f"{status}: {title}"
        )

        self.load_history()

    def clear_history(self):
        response = QMessageBox.question(
            self,
            "Clear listening history",
            (
                "Permanently delete every saved "
                "track from your Library?"
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

        self.history_store.clear_history()

        self._last_track_key = None
        self._last_status = None
        self._current_track_event_recorded = False
        self._page_offset = 0

        self.load_history()

        self.latest_status.setText(
            "History cleared"
        )

    @staticmethod
    def _display_source(
        source_app: str,
    ) -> str:
        source = str(
            source_app or ""
        ).strip()

        lowered = source.lower()

        if "spotify" in lowered:
            return "Spotify"

        if (
            "chrome" in lowered
            or "googlechrome" in lowered
        ):
            return "Chrome"

        if (
            "msedge" in lowered
            or "microsoftedge" in lowered
        ):
            return "Edge"

        if "firefox" in lowered:
            return "Firefox"

        if "soundcloud" in lowered:
            return "SoundCloud"

        if not source:
            return "Unknown"

        cleaned = (
            source
            .replace(".exe", "")
            .replace("_", " ")
            .strip()
        )

        return (
            cleaned[:24]
            or "Unknown"
        )

    @staticmethod
    def _format_timestamp(
        value: str,
    ) -> str:
        try:
            parsed = datetime.strptime(
                value,
                "%Y-%m-%d %H:%M:%S",
            )

            return parsed.strftime(
                "%d %b %Y  %H:%M"
            )

        except (
            TypeError,
            ValueError,
        ):
            return str(
                value or ""
            )

    @staticmethod
    def _format_count(
        count: int,
        singular: str,
        plural: str,
    ) -> str:
        safe_count = max(
            0,
            int(count),
        )

        label = (
            singular
            if safe_count == 1
            else plural
        )

        return (
            f"{safe_count} {label}"
        )