from __future__ import annotations

from PyQt6.QtCore import QTimer

from src.ui.spotify_artwork import SpotifyArtworkLoader

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.spotify.qt_search_runtime import (
    SpotifyQtSearchRuntimeError,
)
from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
    SpotifySearchResults,
)
from src.spotify.search_service import (
    SpotifySearchServiceResult,
    SpotifySearchServiceStatus,
)
from src.ui.theme import ThemeManager


SEARCH_SECTION_ORDER = (
    SpotifySearchItemType.TRACK,
    SpotifySearchItemType.ALBUM,
    SpotifySearchItemType.ARTIST,
    SpotifySearchItemType.PLAYLIST,
)

SEARCH_SECTION_TITLES = {
    SpotifySearchItemType.TRACK: "Tracks",
    SpotifySearchItemType.ALBUM: "Albums",
    SpotifySearchItemType.ARTIST: "Artists",
    SpotifySearchItemType.PLAYLIST: "Playlists",
}

SEARCH_SECTION_ICONS = {
    SpotifySearchItemType.TRACK: "♪",
    SpotifySearchItemType.ALBUM: "▣",
    SpotifySearchItemType.ARTIST: "●",
    SpotifySearchItemType.PLAYLIST: "≡",
}


def _theme_value(
    theme: dict,
    key: str,
    fallback: str,
) -> str:
    value = theme.get(
        key,
        fallback,
    )

    if not isinstance(
        value,
        str,
    ):
        return fallback

    value = value.strip()

    return (
        value
        if value
        else fallback
    )


SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS = 350
SPOTIFY_LIVE_SEARCH_MINIMUM_CHARACTERS = 2


class SpotifySearchResultRow(
    QFrame
):
    activated = pyqtSignal(object)

    def __init__(
        self,
        item: SpotifySearchItem,
        parent=None,
        artwork_loader=None,
    ) -> None:
        if not isinstance(
            item,
            SpotifySearchItem,
        ):
            raise TypeError(
                (
                    "item must be a "
                    "SpotifySearchItem"
                )
            )

        super().__init__(
            parent
        )

        self.item = item
        self.artwork_loader = (
            artwork_loader
        )

        self._activatable = (
            item.item_type
            in {
                SpotifySearchItemType.TRACK,
                SpotifySearchItemType.PLAYLIST,
                SpotifySearchItemType.ALBUM,
            }
        )

        if self._activatable:
            self.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

        self.setObjectName(
            "spotifySearchResultRow"
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        root = QHBoxLayout(
            self
        )

        root.setContentsMargins(
            12,
            9,
            12,
            9,
        )

        root.setSpacing(
            10
        )

        self.icon_label = QLabel(
            SEARCH_SECTION_ICONS[
                item.item_type
            ]
        )

        self.icon_label.setObjectName(
            "spotifySearchResultIcon"
        )

        self.icon_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.icon_label.setFixedSize(
            52,
            52,
        )

        text_layout = QVBoxLayout()

        text_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        text_layout.setSpacing(
            2
        )

        self.name_label = QLabel(
            item.name
        )

        self.name_label.setObjectName(
            "spotifySearchResultName"
        )

        self.name_label.setWordWrap(
            True
        )

        subtitle = (
            item.subtitle.strip()
            if item.subtitle
            else (
                SEARCH_SECTION_TITLES[
                    item.item_type
                ][:-1]
            )
        )

        self.subtitle_label = QLabel(
            subtitle
        )

        self.subtitle_label.setObjectName(
            "spotifySearchResultSubtitle"
        )

        self.subtitle_label.setWordWrap(
            True
        )

        text_layout.addWidget(
            self.name_label
        )

        text_layout.addWidget(
            self.subtitle_label
        )

        self.type_badge = QLabel(
            item.item_type.value.upper()
        )

        self.type_badge.setObjectName(
            "spotifySearchResultType"
        )

        self.type_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        root.addWidget(
            self.icon_label
        )

        root.addLayout(
            text_layout,
            stretch=1,
        )

        root.addWidget(
            self.type_badge,
            alignment=(
                Qt.AlignmentFlag.AlignVCenter
            ),
        )

        if self._activatable:
            for child in (
                self.icon_label,
                self.name_label,
                self.subtitle_label,
                self.type_badge,
            ):
                child.setAttribute(
                    (
                        Qt.WidgetAttribute
                        .WA_TransparentForMouseEvents
                    ),
                    True,
                )

        self._request_artwork()

    def mouseReleaseEvent(
        self,
        event,
    ) -> None:
        if (
            self._activatable
            and event.button()
            is Qt.MouseButton.LeftButton
        ):
            self.activated.emit(
                self.item
            )

            event.accept()

            return

        super().mouseReleaseEvent(
            event
        )

    def _request_artwork(
        self,
    ) -> None:
        artwork_url = (
            self.item.image_url.strip()
            if self.item.image_url
            else ""
        )

        if (
            not artwork_url
            or self.artwork_loader
            is None
        ):
            return

        request = getattr(
            self.artwork_loader,
            "request",
            None,
        )

        ready = getattr(
            self.artwork_loader,
            "artwork_ready",
            None,
        )

        failed = getattr(
            self.artwork_loader,
            "artwork_failed",
            None,
        )

        if (
            not callable(
                request
            )
            or ready is None
            or failed is None
        ):
            return

        try:
            ready.connect(
                self._handle_artwork_ready
            )

            failed.connect(
                self._handle_artwork_failed
            )

            request(
                artwork_url
            )

        except Exception:
            return

    def _handle_artwork_ready(
        self,
        artwork_url: str,
        pixmap,
    ) -> None:
        if (
            artwork_url
            != self.item.image_url
        ):
            return

        is_null = getattr(
            pixmap,
            "isNull",
            None,
        )

        scaled = getattr(
            pixmap,
            "scaled",
            None,
        )

        if (
            not callable(
                is_null
            )
            or not callable(
                scaled
            )
            or is_null()
        ):
            return

        try:
            display_pixmap = scaled(
                self.icon_label.size(),
                (
                    Qt.AspectRatioMode
                    .KeepAspectRatio
                ),
                (
                    Qt.TransformationMode
                    .SmoothTransformation
                ),
            )

        except Exception:
            return

        self.icon_label.setText(
            ""
        )

        self.icon_label.setPixmap(
            display_pixmap
        )

    def _handle_artwork_failed(
        self,
        artwork_url: str,
    ) -> None:
        if (
            artwork_url
            != self.item.image_url
        ):
            return


class SpotifySearchSection(
    QFrame
):
    item_activated = pyqtSignal(object)

    def __init__(
        self,
        item_type: SpotifySearchItemType,
        parent=None,
        artwork_loader=None,
    ) -> None:
        if not isinstance(
            item_type,
            SpotifySearchItemType,
        ):
            raise TypeError(
                (
                    "item_type must be a "
                    "SpotifySearchItemType"
                )
            )

        super().__init__(
            parent
        )

        self.item_type = item_type
        self.artwork_loader = (
            artwork_loader
        )

        self.setObjectName(
            "spotifySearchSection"
        )

        self.root_layout = QVBoxLayout(
            self
        )

        self.root_layout.setContentsMargins(
            14,
            12,
            14,
            14,
        )

        self.root_layout.setSpacing(
            8
        )

        header = QHBoxLayout()

        header.setSpacing(
            8
        )

        self.title_label = QLabel(
            SEARCH_SECTION_TITLES[
                item_type
            ]
        )

        self.title_label.setObjectName(
            "spotifySearchSectionTitle"
        )

        self.count_label = QLabel(
            "0"
        )

        self.count_label.setObjectName(
            "spotifySearchSectionCount"
        )

        self.count_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        header.addWidget(
            self.title_label
        )

        header.addStretch()

        header.addWidget(
            self.count_label
        )

        self.root_layout.addLayout(
            header
        )

        self.empty_label = QLabel(
            (
                "No "
                + SEARCH_SECTION_TITLES[
                    item_type
                ].casefold()
                + " found."
            )
        )

        self.empty_label.setObjectName(
            "spotifySearchSectionEmpty"
        )

        self.empty_label.setWordWrap(
            True
        )

        self.root_layout.addWidget(
            self.empty_label
        )

        self._rows = []

    @property
    def rows(
        self,
    ) -> tuple[
        SpotifySearchResultRow,
        ...,
    ]:
        return tuple(
            self._rows
        )

    def clear_results(
        self,
    ) -> None:
        for row in self._rows:
            self.root_layout.removeWidget(
                row
            )

            row.deleteLater()

        self._rows.clear()

        self.count_label.setText(
            "0"
        )

        self.empty_label.setVisible(
            True
        )

    def set_items(
        self,
        items,
    ) -> None:
        self.clear_results()

        checked_items = tuple(
            items
        )

        for item in checked_items:
            if not isinstance(
                item,
                SpotifySearchItem,
            ):
                raise TypeError(
                    (
                        "Search section items must "
                        "be SpotifySearchItem values"
                    )
                )

            if (
                item.item_type
                is not self.item_type
            ):
                raise ValueError(
                    (
                        "Search item type does not "
                        "match its section"
                    )
                )

            row = SpotifySearchResultRow(
                item,
                parent=self,
                artwork_loader=(
                    self.artwork_loader
                ),
            )

            row.activated.connect(
                self.item_activated.emit
            )

            self._rows.append(
                row
            )

            self.root_layout.addWidget(
                row
            )

        self.count_label.setText(
            str(
                len(
                    self._rows
                )
            )
        )

        self.empty_label.setVisible(
            not bool(
                self._rows
            )
        )


class SpotifySearchPage(
    QWidget
):
    track_activated = pyqtSignal(object)
    playlist_activated = pyqtSignal(object)
    album_activated = pyqtSignal(object)

    def __init__(
        self,
        runtime,
        theme_manager=None,
        parent=None,
        artwork_loader=None,
    ) -> None:
        super().__init__(
            parent
        )

        search = getattr(
            runtime,
            "search",
            None,
        )

        if not callable(
            search
        ):
            raise TypeError(
                (
                    "runtime must provide a "
                    "callable search method"
                )
            )

        self.runtime = runtime

        self.theme_manager = (
            theme_manager
            or ThemeManager(
                self
            )
        )

        self._busy = bool(
            getattr(
                runtime,
                "busy",
                False,
            )
        )

        self._last_results = None

        self._active_search_query = ""
        self._pending_search_query = None
        self._last_submitted_query = ""

        self._live_search_timer = QTimer(
            self
        )

        self._live_search_timer.setSingleShot(
            True
        )

        self._live_search_timer.setInterval(
            SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS
        )

        self._live_search_timer.timeout.connect(
            self._submit_live_search
        )

        if artwork_loader is None:
            artwork_loader = (
                SpotifyArtworkLoader(
                    parent=self
                )
            )

        request_artwork = getattr(
            artwork_loader,
            "request",
            None,
        )

        if not callable(
            request_artwork
        ):
            raise TypeError(
                (
                    "artwork_loader must provide "
                    "a callable request method"
                )
            )

        self.artwork_loader = (
            artwork_loader
        )

        self.setObjectName(
            "spotifySearchRoot"
        )

        self.build_ui()
        self.connect_signals()

        self.theme_manager.theme_changed.connect(
            self.apply_theme
        )

        self.apply_theme(
            self.theme_manager.theme()
        )

        self._sync_search_controls()

    @property
    def busy(
        self,
    ) -> bool:
        return self._busy

    @property
    def last_results(
        self,
    ) -> SpotifySearchResults | None:
        return self._last_results

    def build_ui(
        self,
    ) -> None:
        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            20,
            18,
            20,
            18,
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
            1
        )

        self.page_title = QLabel(
            "Spotify"
        )

        self.page_title.setObjectName(
            "spotifySearchTitle"
        )

        self.page_subtitle = QLabel(
            (
                "Search tracks, albums, artists, "
                "and playlists."
            )
        )

        self.page_subtitle.setObjectName(
            "spotifySearchSubtitle"
        )

        heading_group.addWidget(
            self.page_title
        )

        heading_group.addWidget(
            self.page_subtitle
        )

        self.connection_badge = QLabel(
            "SEARCH"
        )

        self.connection_badge.setObjectName(
            "spotifySearchBadge"
        )

        self.connection_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        header.addLayout(
            heading_group
        )

        header.addStretch()

        header.addWidget(
            self.connection_badge,
            alignment=(
                Qt.AlignmentFlag.AlignVCenter
            ),
        )

        root.addLayout(
            header
        )

        self.search_card = QFrame()

        self.search_card.setObjectName(
            "spotifySearchCard"
        )

        search_card_layout = QVBoxLayout(
            self.search_card
        )

        search_card_layout.setContentsMargins(
            14,
            13,
            14,
            13,
        )

        search_card_layout.setSpacing(
            8
        )

        search_heading = QLabel(
            "Search Spotify"
        )

        search_heading.setObjectName(
            "spotifySearchCardTitle"
        )

        self.search_help = QLabel(
            (
                "Results are requested using your "
                "connected Spotify account."
            )
        )

        self.search_help.setObjectName(
            "spotifySearchHelp"
        )

        self.search_help.setWordWrap(
            True
        )

        input_row = QHBoxLayout()

        input_row.setSpacing(
            8
        )

        self.search_input = QLineEdit()

        self.search_input.setObjectName(
            "spotifySearchInput"
        )

        self.search_input.setPlaceholderText(
            (
                "Search songs, artists, albums, "
                "or playlists"
            )
        )

        self.search_input.setClearButtonEnabled(
            True
        )

        self.search_button = QPushButton(
            "Search"
        )

        self.search_button.setObjectName(
            "spotifySearchButton"
        )

        self.search_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.search_button.setMinimumWidth(
            94
        )

        input_row.addWidget(
            self.search_input,
            stretch=1,
        )

        input_row.addWidget(
            self.search_button
        )

        self.status_label = QLabel(
            "Enter a search to browse Spotify."
        )

        self.status_label.setObjectName(
            "spotifySearchStatus"
        )

        self.status_label.setWordWrap(
            True
        )

        search_card_layout.addWidget(
            search_heading
        )

        search_card_layout.addWidget(
            self.search_help
        )

        search_card_layout.addLayout(
            input_row
        )

        search_card_layout.addWidget(
            self.status_label
        )

        root.addWidget(
            self.search_card
        )

        self.results_scroll = QScrollArea()

        self.results_scroll.setObjectName(
            "spotifySearchResultsScroll"
        )

        self.results_scroll.setWidgetResizable(
            True
        )

        self.results_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.results_container = QWidget()

        self.results_container.setObjectName(
            "spotifySearchResultsContainer"
        )

        self.results_layout = QVBoxLayout(
            self.results_container
        )

        self.results_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.results_layout.setSpacing(
            10
        )

        self.sections = {}

        for item_type in SEARCH_SECTION_ORDER:
            section = SpotifySearchSection(
                item_type,
                parent=(
                    self.results_container
                ),
                artwork_loader=(
                    self.artwork_loader
                ),
            )

            section.item_activated.connect(
                self._handle_item_activated
            )

            self.sections[
                item_type
            ] = section

            self.results_layout.addWidget(
                section
            )

        self.results_layout.addStretch()

        self.results_scroll.setWidget(
            self.results_container
        )

        root.addWidget(
            self.results_scroll,
            stretch=1,
        )

    def connect_signals(
        self,
    ) -> None:
        self.search_button.clicked.connect(
            self.start_search
        )

        self.search_input.returnPressed.connect(
            self.start_search
        )

        self.search_input.textChanged.connect(
            self.handle_search_text_changed
        )

        result_signal = getattr(
            self.runtime,
            "result_ready",
            None,
        )

        failure_signal = getattr(
            self.runtime,
            "failed",
            None,
        )

        busy_signal = getattr(
            self.runtime,
            "busy_changed",
            None,
        )

        finished_signal = getattr(
            self.runtime,
            "search_finished",
            None,
        )

        if (
            result_signal is None
            or failure_signal is None
            or busy_signal is None
        ):
            raise TypeError(
                (
                    "runtime must expose result_ready, "
                    "failed, and busy_changed signals"
                )
            )

        result_signal.connect(
            self.handle_result
        )

        failure_signal.connect(
            self.handle_failure
        )

        busy_signal.connect(
            self.handle_busy
        )

        if finished_signal is not None:
            finished_signal.connect(
                self.handle_search_finished
            )

    def _handle_item_activated(
        self,
        item,
    ) -> None:
        if not isinstance(
            item,
            SpotifySearchItem,
        ):
            return

        if (
            item.item_type
            is SpotifySearchItemType.TRACK
        ):
            self.track_activated.emit(
                item
            )

            return

        if (
            item.item_type
            is SpotifySearchItemType.PLAYLIST
        ):
            self.playlist_activated.emit(
                item
            )

            return

        if (
            item.item_type
            is SpotifySearchItemType.ALBUM
        ):
            self.album_activated.emit(
                item
            )


    def _sync_search_controls(
        self,
    ) -> None:
        self.search_input.setEnabled(
            True
        )

        self.search_button.setEnabled(
            (
                not self._busy
                and bool(
                    self.search_input
                    .text()
                    .strip()
                )
            )
        )

        self.search_button.setText(
            (
                "Searching..."
                if self._busy
                else "Search"
            )
        )

    def _set_status(
        self,
        message: str,
    ) -> None:
        self.status_label.setText(
            str(
                message
                or ""
            )
        )

    def clear_results(
        self,
    ) -> None:
        self._last_results = None

        for section in self.sections.values():
            section.clear_results()

    @pyqtSlot()
    def start_search(
        self,
    ) -> None:
        self._live_search_timer.stop()

        query = (
            self.search_input
            .text()
            .strip()
        )

        if not query:
            self._pending_search_query = None

            self._set_status(
                "Enter something to search for."
            )

            self._sync_search_controls()

            return

        self._submit_search(
            query,
            allow_repeat=True,
        )

    def handle_search_text_changed(
        self,
        text,
    ) -> None:
        self._live_search_timer.stop()
        self._pending_search_query = None

        query = str(
            text
            or ""
        ).strip()

        if not query:
            self.clear_results()

            self._set_status(
                "Enter a search to browse Spotify."
            )

            self._sync_search_controls()

            return

        if (
            len(
                query
            )
            < SPOTIFY_LIVE_SEARCH_MINIMUM_CHARACTERS
        ):
            self.clear_results()

            self._set_status(
                (
                    "Type at least 2 characters for "
                    "live search, or press Search."
                )
            )

            self._sync_search_controls()

            return

        self._live_search_timer.start()

        if (
            self._busy
            and query
            != self._active_search_query
        ):
            self._set_status(
                (
                    'Waiting to search Spotify for "'
                    + query
                    + '"...'
                )
            )

        self._sync_search_controls()

    def _submit_live_search(
        self,
    ) -> None:
        query = (
            self.search_input
            .text()
            .strip()
        )

        if (
            len(
                query
            )
            < SPOTIFY_LIVE_SEARCH_MINIMUM_CHARACTERS
        ):
            return

        self._submit_search(
            query,
            allow_repeat=False,
        )

    def _submit_search(
        self,
        query: str,
        *,
        allow_repeat: bool,
    ) -> bool:
        checked_query = str(
            query
            or ""
        ).strip()

        if not checked_query:
            return False

        runtime_busy = bool(
            getattr(
                self.runtime,
                "busy",
                False,
            )
        )

        if (
            self._busy
            or runtime_busy
        ):
            if (
                checked_query
                != self._active_search_query
            ):
                self._pending_search_query = (
                    checked_query
                )

                self._set_status(
                    (
                        'Waiting to search Spotify for "'
                        + checked_query
                        + '"...'
                    )
                )

            return False

        if (
            not allow_repeat
            and checked_query
            == self._last_submitted_query
            and self._last_results
            is not None
        ):
            return False

        self._pending_search_query = None

        self.clear_results()

        self._set_status(
            (
                'Searching Spotify for "'
                + checked_query
                + '"...'
            )
        )

        self._active_search_query = (
            checked_query
        )

        try:
            self.runtime.search(
                checked_query,
                limit=5,
                offset=0,
            )

        except SpotifyQtSearchRuntimeError as error:
            self._active_search_query = ""

            if (
                error.error_code
                == "busy"
            ):
                self._pending_search_query = (
                    checked_query
                )

            self._set_status(
                error.message
                or (
                    "Spotify Search could not "
                    "be started."
                )
            )

            self._sync_search_controls()

            return False

        except (
            TypeError,
            ValueError,
        ):
            self._active_search_query = ""

            self._set_status(
                (
                    "The Spotify Search request "
                    "is invalid."
                )
            )

            self._sync_search_controls()

            return False

        except Exception:
            self._active_search_query = ""

            self._set_status(
                (
                    "Spotify Search could not "
                    "be started."
                )
            )

            self._sync_search_controls()

            return False

        self._last_submitted_query = (
            checked_query
        )

        self._sync_search_controls()

        return True

    def _should_ignore_search_completion(
        self,
    ) -> bool:
        active_query = (
            self._active_search_query
            or str(
                getattr(
                    self.runtime,
                    "active_query",
                    "",
                )
                or ""
            ).strip()
        )

        if not active_query:
            return False

        current_query = (
            self.search_input
            .text()
            .strip()
        )

        return (
            current_query
            != active_query
        )

    def handle_search_finished(
        self,
        finished_query,
    ) -> None:
        checked_finished = str(
            finished_query
            or ""
        ).strip()

        if (
            not checked_finished
            or self._active_search_query
            == checked_finished
        ):
            self._active_search_query = ""

        pending_query = (
            self._pending_search_query
        )

        self._pending_search_query = None

        if not pending_query:
            return

        QTimer.singleShot(
            0,
            lambda query=pending_query:
            self._submit_pending_search(
                query
            ),
        )

    def _submit_pending_search(
        self,
        pending_query: str,
    ) -> None:
        current_query = (
            self.search_input
            .text()
            .strip()
        )

        if (
            pending_query
            != current_query
            or len(
                pending_query
            )
            < SPOTIFY_LIVE_SEARCH_MINIMUM_CHARACTERS
        ):
            return

        self._submit_search(
            pending_query,
            allow_repeat=False,
        )

    @pyqtSlot(
        bool
    )
    def handle_busy(
        self,
        busy: bool,
    ) -> None:
        self._busy = bool(
            busy
        )

        self._sync_search_controls()

    @pyqtSlot(
        object
    )
    def handle_result(
        self,
        result,
    ) -> None:
        if self._should_ignore_search_completion():
            return
        if not isinstance(
            result,
            SpotifySearchServiceResult,
        ):
            self.clear_results()

            self._set_status(
                (
                    "Spotify returned an invalid "
                    "Search result."
                )
            )

            return

        if (
            result.status
            is SpotifySearchServiceStatus
            .DISCONNECTED
        ):
            self.clear_results()

            self.connection_badge.setText(
                "OFFLINE"
            )

            self._set_status(
                (
                    result.message
                    or (
                        "Connect Spotify in Settings "
                        "before searching."
                    )
                )
            )

            return

        if (
            result.status
            is SpotifySearchServiceStatus
            .REAUTHORIZATION_REQUIRED
        ):
            self.clear_results()

            self.connection_badge.setText(
                "RECONNECT"
            )

            self._set_status(
                (
                    result.message
                    or (
                        "Reconnect Spotify in Settings "
                        "before searching."
                    )
                )
            )

            return

        if (
            result.status
            is SpotifySearchServiceStatus.ERROR
        ):
            self.clear_results()

            self.connection_badge.setText(
                "ERROR"
            )

            message = (
                result.message
                or (
                    "Spotify Search could not "
                    "be completed."
                )
            )

            if (
                result.retry_after_seconds
                is not None
            ):
                message = (
                    message
                    + " Try again in "
                    + str(
                        result.retry_after_seconds
                    )
                    + " seconds."
                )

            self._set_status(
                message
            )

            return

        if (
            result.status
            is not SpotifySearchServiceStatus.READY
            or result.results is None
        ):
            self.clear_results()

            self.connection_badge.setText(
                "ERROR"
            )

            self._set_status(
                (
                    "Spotify returned an unexpected "
                    "Search state."
                )
            )

            return

        self.show_results(
            result.results
        )

        self.connection_badge.setText(
            (
                "REFRESHED"
                if result.refreshed
                else "READY"
            )
        )

        total_visible = sum(
            len(
                result.results.items_for(
                    item_type
                )
            )
            for item_type
            in SEARCH_SECTION_ORDER
        )

        self._set_status(
            (
                "Showing "
                + str(
                    total_visible
                )
                + " Spotify result"
                + (
                    ""
                    if total_visible == 1
                    else "s"
                )
                + '.'
            )
        )

    def show_results(
        self,
        results: SpotifySearchResults,
    ) -> None:
        if not isinstance(
            results,
            SpotifySearchResults,
        ):
            raise TypeError(
                (
                    "results must be "
                    "SpotifySearchResults"
                )
            )

        self._last_results = results

        for item_type in SEARCH_SECTION_ORDER:
            self.sections[
                item_type
            ].set_items(
                results.items_for(
                    item_type
                )
            )

    @pyqtSlot(
        str,
        str,
    )
    def handle_failure(
        self,
        error_code: str,
        message: str,
    ) -> None:
        if self._should_ignore_search_completion():
            return
        self.clear_results()

        self.connection_badge.setText(
            "ERROR"
        )

        self._set_status(
            (
                str(
                    message
                    or ""
                ).strip()
                or (
                    "Spotify Search could not "
                    "be completed."
                )
            )
        )

    def apply_theme(
        self,
        theme: dict,
    ) -> None:
        if not isinstance(
            theme,
            dict,
        ):
            return

        background = _theme_value(
            theme,
            "background",
            "#101014",
        )

        card = _theme_value(
            theme,
            "card",
            "#18181f",
        )

        card_alt = _theme_value(
            theme,
            "card_alt",
            "#202028",
        )

        border = _theme_value(
            theme,
            "border",
            "#34343e",
        )

        accent = _theme_value(
            theme,
            "accent",
            "#ff4f91",
        )

        text = _theme_value(
            theme,
            "text",
            "#f4f4f6",
        )

        muted = _theme_value(
            theme,
            "muted",
            "#a6a6b1",
        )

        self.setStyleSheet(
            f"""
            QWidget#spotifySearchRoot {{
                background: transparent;
                color: {text};
            }}

            QLabel#spotifySearchTitle {{
                color: {text};
                font-size: 22px;
                font-weight: 800;
            }}

            QLabel#spotifySearchSubtitle {{
                color: {muted};
                font-size: 11px;
            }}

            QLabel#spotifySearchBadge {{
                color: {accent};
                background: {card};
                border: 1px solid {accent};
                border-radius: 9px;
                padding: 4px 9px;
                font-size: 9px;
                font-weight: 800;
            }}

            QFrame#spotifySearchCard,
            QFrame#spotifySearchSection {{
                background: {card};
                border: 1px solid {border};
                border-radius: 12px;
            }}

            QLabel#spotifySearchCardTitle,
            QLabel#spotifySearchSectionTitle {{
                color: {text};
                font-size: 12px;
                font-weight: 800;
            }}

            QLabel#spotifySearchHelp,
            QLabel#spotifySearchStatus,
            QLabel#spotifySearchSectionEmpty {{
                color: {muted};
                font-size: 10px;
            }}

            QLineEdit#spotifySearchInput {{
                color: {text};
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 8px 10px;
                selection-background-color: {accent};
            }}

            QLineEdit#spotifySearchInput:focus {{
                border: 1px solid {accent};
            }}

            QPushButton#spotifySearchButton {{
                color: {background};
                background: {accent};
                border: 1px solid {accent};
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 800;
            }}

            QPushButton#spotifySearchButton:hover {{
                border: 1px solid {text};
            }}

            QPushButton#spotifySearchButton:disabled {{
                color: {muted};
                background: {card_alt};
                border: 1px solid {border};
            }}

            QScrollArea#spotifySearchResultsScroll {{
                background: transparent;
                border: none;
            }}

            QWidget#spotifySearchResultsContainer {{
                background: transparent;
            }}

            QLabel#spotifySearchSectionCount {{
                color: {accent};
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 8px;
                min-width: 24px;
                padding: 2px 5px;
                font-size: 9px;
                font-weight: 800;
            }}

            QFrame#spotifySearchResultRow {{
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 9px;
            }}

            QLabel#spotifySearchResultIcon {{
                color: {accent};
                background: {card};
                border: 1px solid {border};
                border-radius: 7px;
                font-size: 15px;
                font-weight: 800;
            }}

            QLabel#spotifySearchResultName {{
                color: {text};
                font-size: 11px;
                font-weight: 700;
            }}

            QLabel#spotifySearchResultSubtitle {{
                color: {muted};
                font-size: 9px;
            }}

            QLabel#spotifySearchResultType {{
                color: {accent};
                border: 1px solid {border};
                border-radius: 7px;
                padding: 3px 6px;
                font-size: 8px;
                font-weight: 800;
            }}
            """
        )
