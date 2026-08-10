from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.media.spotify_playlist_resolver import (
    ResolvedSpotifyPlaylistItem,
    ResolvedSpotifyPlaylistPage,
)
from src.spotify.playlist_models import (
    SpotifyPlaylistItemsPage,
)
from src.ui.spotify_playlist_detail import (
    SpotifyPlaylistTrackRow,
)
from src.ui.theme import ThemeManager


SPOTIFY_LIKED_SONGS_PAGE_LIMIT = 50


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

    checked = value.strip()

    return checked or fallback


def _catalogue_page(
    page: SpotifyPlaylistItemsPage,
) -> ResolvedSpotifyPlaylistPage:
    if not isinstance(
        page,
        SpotifyPlaylistItemsPage,
    ):
        raise TypeError(
            (
                "page must be a "
                "SpotifyPlaylistItemsPage"
            )
        )

    resolved = []
    skipped_local = 0

    for item in page.items:
        if item.is_local:
            skipped_local += 1
            continue

        resolved.append(
            ResolvedSpotifyPlaylistItem(
                playlist_item=item,
                unified_track=(
                    item.track
                    .to_unified_track()
                ),
            )
        )

    return ResolvedSpotifyPlaylistPage(
        items=tuple(
            resolved
        ),
        limit=page.limit,
        offset=page.offset,
        total=page.total,
        omitted_items=(
            page.omitted_items
            + skipped_local
        ),
    )


class SpotifyLikedSongsDetail(
    QWidget
):
    back_requested = pyqtSignal()

    def __init__(
        self,
        runtime=None,
        *,
        playback_runtime=None,
        theme_manager=None,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        if runtime is not None:
            load_tracks_page = getattr(
                runtime,
                "load_tracks_page",
                None,
            )

            if not callable(
                load_tracks_page
            ):
                raise TypeError(
                    (
                        "runtime must provide a "
                        "callable load_tracks_page "
                        "method"
                    )
                )

        if playback_runtime is not None:
            play_track = getattr(
                playback_runtime,
                "play_track",
                None,
            )

            play_playlist_track = getattr(
                playback_runtime,
                "play_playlist_track",
                None,
            )

            if not callable(
                play_track
            ):
                raise TypeError(
                    (
                        "playback_runtime must "
                        "provide a callable "
                        "play_track method"
                    )
                )

            if not callable(
                play_playlist_track
            ):
                raise TypeError(
                    (
                        "playback_runtime must "
                        "provide a callable "
                        "play_playlist_track method"
                    )
                )

        self.runtime = runtime
        self.playback_runtime = (
            playback_runtime
        )

        self.theme_manager = (
            theme_manager
            or ThemeManager(
                self
            )
        )

        self.rows = []

        self._current_song = None
        self.last_result = None

        self._loaded = False
        self._pagination_enabled = True

        self._request_active = False
        self._requested_offset = None
        self._pending_offset = None

        self._next_offset = 0
        self._total = None

        self._context_playlist_id = ""

        self._active_playback_title = ""

        self.setObjectName(
            "spotifyLikedSongsDetailRoot"
        )

        self.build_ui()
        self.connect_signals()

        theme_signal = getattr(
            self.theme_manager,
            "theme_changed",
            None,
        )

        connect_theme = getattr(
            theme_signal,
            "connect",
            None,
        )

        if callable(
            connect_theme
        ):
            connect_theme(
                self.apply_theme
            )

        theme_getter = getattr(
            self.theme_manager,
            "theme",
            None,
        )

        if callable(
            theme_getter
        ):
            self.apply_theme(
                theme_getter()
            )

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
            12
        )

        self.back_button = QPushButton(
            "Back"
        )

        self.back_button.setObjectName(
            "spotifyLikedSongsBack"
        )

        self.back_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        title_group = QVBoxLayout()

        title_group.setSpacing(
            2
        )

        self.title_label = QLabel(
            "Liked Songs"
        )

        self.title_label.setObjectName(
            "spotifyLikedSongsDetailTitle"
        )

        self.subtitle_label = QLabel(
            "Your saved Spotify tracks."
        )

        self.subtitle_label.setObjectName(
            "spotifyLikedSongsDetailSubtitle"
        )

        title_group.addWidget(
            self.title_label
        )

        title_group.addWidget(
            self.subtitle_label
        )

        header.addWidget(
            self.back_button
        )

        header.addLayout(
            title_group,
            stretch=1,
        )

        root.addLayout(
            header
        )

        self.status_label = QLabel(
            "Open Liked Songs to load your saved tracks."
        )

        self.status_label.setObjectName(
            "spotifyLikedSongsDetailStatus"
        )

        self.status_label.setWordWrap(
            True
        )

        root.addWidget(
            self.status_label
        )

        self.scroll = QScrollArea()

        self.scroll.setObjectName(
            "spotifyLikedSongsScroll"
        )

        self.scroll.setWidgetResizable(
            True
        )

        self.scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.track_container = QWidget()

        self.track_container.setObjectName(
            "spotifyLikedSongsTrackContainer"
        )

        self.track_layout = QVBoxLayout(
            self.track_container
        )

        self.track_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.track_layout.setSpacing(
            6
        )

        self.empty_label = QLabel(
            "No Liked Songs loaded."
        )

        self.empty_label.setObjectName(
            "spotifyLikedSongsEmpty"
        )

        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.empty_label.setWordWrap(
            True
        )

        self.track_layout.addWidget(
            self.empty_label
        )

        self.track_layout.addStretch()

        self.scroll.setWidget(
            self.track_container
        )

        root.addWidget(
            self.scroll,
            stretch=1,
        )

        self.load_more_button = QPushButton(
            "Load More"
        )

        self.load_more_button.setObjectName(
            "spotifyLikedSongsLoadMore"
        )

        self.load_more_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.load_more_button.setVisible(
            False
        )

        root.addWidget(
            self.load_more_button
        )

    def connect_signals(
        self,
    ) -> None:
        self.back_button.clicked.connect(
            self._handle_back_clicked
        )

        self.load_more_button.clicked.connect(
            self.load_more
        )

        if self.runtime is not None:
            for signal_name, handler in (
                (
                    "tracks_ready",
                    self.handle_tracks_ready,
                ),
                (
                    "failed",
                    self.handle_runtime_failure,
                ),
                (
                    "operation_finished",
                    self.handle_operation_finished,
                ),
            ):
                signal = getattr(
                    self.runtime,
                    signal_name,
                    None,
                )

                connect = getattr(
                    signal,
                    "connect",
                    None,
                )

                if callable(
                    connect
                ):
                    connect(
                        handler
                    )

        if self.playback_runtime is not None:
            result_signal = getattr(
                self.playback_runtime,
                "result_ready",
                None,
            )

            failed_signal = getattr(
                self.playback_runtime,
                "failed",
                None,
            )

            if callable(
                getattr(
                    result_signal,
                    "connect",
                    None,
                )
            ):
                result_signal.connect(
                    self.handle_playback_result
                )

            if callable(
                getattr(
                    failed_signal,
                    "connect",
                    None,
                )
            ):
                failed_signal.connect(
                    self.handle_playback_failure
                )

    def _clear_rows(
        self,
    ) -> None:
        for row in self.rows:
            row.setParent(
                None
            )

            row.deleteLater()

        self.rows = []

        self.empty_label.setVisible(
            True
        )

    def load(
        self,
        *,
        force: bool = False,
    ) -> bool:
        self._pagination_enabled = True

        if (
            self._loaded
            and not force
        ):
            self._update_status()

            return True

        self._loaded = False

        self._request_active = False
        self._requested_offset = None
        self._pending_offset = None

        self._next_offset = 0
        self._total = None

        self.last_result = None

        self._clear_rows()

        self.subtitle_label.setText(
            "Your saved Spotify tracks."
        )

        return self._request_page(
            0
        )

    def _request_page(
        self,
        offset: int,
    ) -> bool:
        if not self._pagination_enabled:
            return False

        if self.runtime is None:
            self.status_label.setText(
                "Liked Songs are unavailable."
            )

            return False

        if self._request_active:
            return False

        checked_offset = int(
            offset
        )

        if checked_offset < 0:
            return False

        if bool(
            getattr(
                self.runtime,
                "busy",
                False,
            )
        ):
            self._pending_offset = (
                checked_offset
            )

            self.status_label.setText(
                "Waiting for Spotify..."
            )

            return False

        self._pending_offset = None
        self._request_active = True
        self._requested_offset = (
            checked_offset
        )

        if checked_offset == 0:
            self.status_label.setText(
                "Loading Liked Songs..."
            )

        else:
            self.status_label.setText(
                (
                    "Loading more Liked Songs..."
                )
            )

        try:
            self.runtime.load_tracks_page(
                limit=(
                    SPOTIFY_LIKED_SONGS_PAGE_LIMIT
                ),
                offset=checked_offset,
                include_context=bool(
                    checked_offset == 0
                    and not self._context_playlist_id
                ),
            )

        except Exception as error:
            self._request_active = False
            self._requested_offset = None

            message = str(
                getattr(
                    error,
                    "message",
                    "",
                )
                or ""
            ).strip()

            self.status_label.setText(
                message
                or (
                    "Liked Songs could not "
                    "be requested."
                )
            )

            return False

        return True

    def handle_tracks_ready(
        self,
        result,
    ) -> None:
        if not self._request_active:
            return

        requested_offset = (
            self._requested_offset
        )

        self._request_active = False
        self._requested_offset = None

        self.last_result = result

        context_playlist_id = str(
            getattr(
                result,
                "context_playlist_id",
                "",
            )
            or ""
        ).strip()

        if context_playlist_id:
            self._context_playlist_id = (
                context_playlist_id
            )

        if not bool(
            getattr(
                result,
                "ready",
                False,
            )
        ):
            message = str(
                getattr(
                    result,
                    "message",
                    "",
                )
                or (
                    "Liked Songs could not "
                    "be loaded."
                )
            ).strip()

            self.status_label.setText(
                message
            )

            return

        page = getattr(
            result,
            "page",
            None,
        )

        if not isinstance(
            page,
            SpotifyPlaylistItemsPage,
        ):
            self.status_label.setText(
                (
                    "Spotify returned no usable "
                    "Liked Songs page."
                )
            )

            return

        if (
            requested_offset is None
            or page.offset
            != requested_offset
        ):
            self.status_label.setText(
                (
                    "Spotify returned Liked Songs "
                    "pagination out of sequence."
                )
            )

            return

        try:
            resolved_page = (
                _catalogue_page(
                    page
                )
            )

        except Exception:
            self.status_label.setText(
                (
                    "Liked Songs could not be "
                    "prepared for display."
                )
            )

            return

        if page.offset == 0:
            self._clear_rows()

        self._append_page(
            resolved_page
        )

        self._total = page.total

        self._next_offset = min(
            page.total,
            page.offset
            + page.limit,
        )

        self._loaded = True

        word = (
            "song"
            if page.total == 1
            else "songs"
        )

        self.subtitle_label.setText(
            (
                str(
                    page.total
                )
                + " "
                + word
            )
        )

        self.load_more_button.setVisible(
            self._next_offset
            < page.total
        )

        self._update_status()

    def _append_page(
        self,
        page: ResolvedSpotifyPlaylistPage,
    ) -> None:
        for resolved_item in page.items:
            playlist_item = (
                resolved_item.playlist_item
            )

            position = getattr(
                playlist_item,
                "position",
                None,
            )

            if (
                isinstance(
                    position,
                    bool,
                )
                or not isinstance(
                    position,
                    int,
                )
                or position < 0
            ):
                number = (
                    len(
                        self.rows
                    )
                    + 1
                )

            else:
                number = (
                    position
                    + 1
                )

            row = SpotifyPlaylistTrackRow(
                resolved_item,
                number=number,
                parent=(
                    self.track_container
                ),
            )

            row.activated.connect(
                self._handle_track_activated
            )

            insert_index = max(
                0,
                self.track_layout.count()
                - 1,
            )

            self.track_layout.insertWidget(
                insert_index,
                row,
            )

            self.rows.append(
                row
            )

        self._refresh_playing_state()

        self.empty_label.setVisible(
            not bool(
                self.rows
            )
        )

    def _update_status(
        self,
    ) -> None:
        total = (
            self._total
            if self._total is not None
            else 0
        )

        loaded = len(
            self.rows
        )

        if total == 0:
            self.empty_label.setText(
                "No Liked Songs to display."
            )

            self.status_label.setText(
                "No Liked Songs found."
            )

            return

        if (
            self._next_offset
            < total
        ):
            self.status_label.setText(
                (
                    str(
                        loaded
                    )
                    + " of "
                    + str(
                        total
                    )
                    + " songs loaded."
                )
            )

            return

        self.status_label.setText(
            (
                str(
                    loaded
                )
                + " songs loaded."
            )
        )

    def load_more(
        self,
    ) -> bool:
        if self._total is None:
            return False

        if self._next_offset >= self._total:
            self.load_more_button.setVisible(
                False
            )

            return False

        return self._request_page(
            self._next_offset
        )

    def handle_runtime_failure(
        self,
        error_code: str,
        message: str,
    ) -> None:
        if not self._request_active:
            return

        self._request_active = False
        self._requested_offset = None

        safe_message = str(
            message
            or (
                "Liked Songs could not "
                "be loaded."
            )
        ).strip()

        self.status_label.setText(
            safe_message
        )

    def handle_operation_finished(
        self,
    ) -> None:
        if not self._pagination_enabled:
            return

        if self._request_active:
            return

        pending = (
            self._pending_offset
        )

        if pending is None:
            return

        self._pending_offset = None

        self._request_page(
            pending
        )


    @staticmethod
    def _normalize_identity(
        value,
    ) -> str:
        return (
            " ".join(
                str(
                    value
                    or ""
                ).split()
            )
            .casefold()
        )

    @classmethod
    def _artist_identity_matches(
        cls,
        current_artist,
        row_artist,
    ) -> bool:
        current = cls._normalize_identity(
            current_artist
        )

        candidate = cls._normalize_identity(
            row_artist
        )

        if (
            not current
            or not candidate
        ):
            return False

        if current == candidate:
            return True

        primary, separator, _rest = (
            candidate.partition(
                ","
            )
        )

        if not separator:
            return False

        return (
            primary.strip()
            == current
        )

    @classmethod
    def _row_identity(
        cls,
        row,
    ) -> tuple[
        str,
        str,
        str,
    ]:
        resolved_item = getattr(
            row,
            "resolved_item",
            None,
        )

        track = getattr(
            resolved_item,
            "unified_track",
            None,
        )

        if track is None:
            return (
                "",
                "",
                "",
            )

        return (
            cls._normalize_identity(
                getattr(
                    track,
                    "title",
                    "",
                )
            ),
            cls._normalize_identity(
                getattr(
                    track,
                    "artist",
                    "",
                )
            ),
            cls._normalize_identity(
                getattr(
                    track,
                    "album",
                    "",
                )
            ),
        )

    def set_current_song(
        self,
        song,
    ) -> None:
        self._current_song = song

        self._refresh_playing_state()

    def _refresh_playing_state(
        self,
    ) -> None:
        rows = tuple(
            getattr(
                self,
                "rows",
                (),
            )
        )

        for row in rows:
            setter = getattr(
                row,
                "set_playing",
                None,
            )

            if callable(
                setter
            ):
                setter(
                    False
                )

        song = getattr(
            self,
            "_current_song",
            None,
        )

        if song is None:
            return

        if not bool(
            getattr(
                song,
                "playing",
                False,
            )
        ):
            return

        source = self._normalize_identity(
            getattr(
                song,
                "source_app",
                "",
            )
        )

        if "spotify" not in source:
            return

        title = self._normalize_identity(
            getattr(
                song,
                "title",
                "",
            )
        )

        artist = self._normalize_identity(
            getattr(
                song,
                "artist",
                "",
            )
        )

        album = self._normalize_identity(
            getattr(
                song,
                "album",
                "",
            )
        )

        if (
            not title
            or not artist
        ):
            return

        matches = []

        for row in rows:
            (
                row_title,
                row_artist,
                row_album,
            ) = self._row_identity(
                row
            )

            if (
                row_title == title
                and self._artist_identity_matches(
                    artist,
                    row_artist,
                )
            ):
                matches.append(
                    (
                        row,
                        row_album,
                    )
                )

        if len(
            matches
        ) == 1:
            setter = getattr(
                matches[0][0],
                "set_playing",
                None,
            )

            if callable(
                setter
            ):
                setter(
                    True
                )

            return

        if not album:
            return

        album_matches = [
            row
            for (
                row,
                row_album,
            )
            in matches
            if (
                row_album
                and row_album == album
            )
        ]

        if len(
            album_matches
        ) != 1:
            return

        setter = getattr(
            album_matches[0],
            "set_playing",
            None,
        )

        if callable(
            setter
        ):
            setter(
                True
            )

    def _handle_track_activated(
        self,
        resolved_item,
    ) -> bool:
        track = getattr(
            resolved_item,
            "unified_track",
            None,
        )

        if track is None:
            return False

        if bool(
            getattr(
                resolved_item,
                "is_local",
                False,
            )
        ):
            return False

        if not bool(
            getattr(
                track,
                "playable",
                False,
            )
        ):
            return False

        spotify_uri = str(
            getattr(
                track,
                "spotify_uri",
                "",
            )
            or ""
        ).strip()

        if not spotify_uri.startswith(
            "spotify:track:"
        ):
            return False

        if self.playback_runtime is None:
            self.status_label.setText(
                (
                    "Spotify playback controls "
                    "are unavailable."
                )
            )

            return False

        if bool(
            getattr(
                self.playback_runtime,
                "busy",
                False,
            )
        ):
            self.status_label.setText(
                (
                    "A Spotify playback request "
                    "is already running."
                )
            )

            return False

        title = str(
            getattr(
                track,
                "title",
                "",
            )
            or "track"
        ).strip()

        self._active_playback_title = (
            title
        )

        self.status_label.setText(
            (
                "Starting "
                + title
                + "..."
            )
        )

        try:
            if self._context_playlist_id:
                self.playback_runtime.play_playlist_track(
                    self._context_playlist_id,
                    spotify_uri,
                )

            else:
                self.playback_runtime.play_track(
                    spotify_uri
                )

        except Exception as error:
            self._active_playback_title = ""

            message = str(
                getattr(
                    error,
                    "message",
                    "",
                )
                or ""
            ).strip()

            self.status_label.setText(
                message
                or (
                    "Spotify playback could "
                    "not start."
                )
            )

            return False

        return True

    def handle_playback_result(
        self,
        result,
    ) -> None:
        title = (
            self._active_playback_title
        )

        if not title:
            return

        self._active_playback_title = ""

        if bool(
            getattr(
                result,
                "ready",
                False,
            )
        ):
            self.status_label.setText(
                (
                    "Playing "
                    + title
                    + "."
                )
            )

            return

        message = str(
            getattr(
                result,
                "message",
                "",
            )
            or (
                "Spotify playback could "
                "not start."
            )
        ).strip()

        retry_after = getattr(
            result,
            "retry_after_seconds",
            None,
        )

        if (
            isinstance(
                retry_after,
                int,
            )
            and not isinstance(
                retry_after,
                bool,
            )
            and retry_after > 0
        ):
            message += (
                " Try again in "
                + str(
                    retry_after
                )
                + " seconds."
            )

        self.status_label.setText(
            message
        )

    def handle_playback_failure(
        self,
        error_code: str,
        message: str,
    ) -> None:
        if not self._active_playback_title:
            return

        self._active_playback_title = ""

        self.status_label.setText(
            str(
                message
                or (
                    "Spotify playback could "
                    "not start."
                )
            ).strip()
        )

    def _handle_back_clicked(
        self,
    ) -> None:
        self._pagination_enabled = False
        self._pending_offset = None

        self.back_requested.emit()

    def apply_theme(
        self,
        theme: dict,
    ) -> None:
        background = _theme_value(
            theme,
            "background",
            "#111111",
        )

        card = _theme_value(
            theme,
            "card",
            "#181818",
        )

        card_alt = _theme_value(
            theme,
            "card_alt",
            card,
        )

        border = _theme_value(
            theme,
            "border",
            "#333333",
        )

        text = _theme_value(
            theme,
            "text",
            "#ffffff",
        )

        muted = _theme_value(
            theme,
            "muted",
            "#a0a0a0",
        )

        accent = _theme_value(
            theme,
            "accent",
            "#ff4f9a",
        )

        self.setStyleSheet(
            f"""
            QWidget#spotifyLikedSongsDetailRoot {{
                background: {background};
            }}

            QLabel#spotifyLikedSongsDetailTitle {{
                color: {text};
                font-size: 22px;
                font-weight: 800;
            }}

            QLabel#spotifyLikedSongsDetailSubtitle,
            QLabel#spotifyLikedSongsDetailStatus,
            QLabel#spotifyLikedSongsEmpty,
            QLabel#spotifyPlaylistTrackArtist,
            QLabel#spotifyPlaylistTrackDuration,
            QLabel#spotifyPlaylistTrackNumber {{
                color: {muted};
            }}

            QFrame#spotifyPlaylistTrackRow {{
                background: {card};
                border: 1px solid {border};
                border-radius: 10px;
            }}

            QLabel#spotifyPlaylistTrackTitle {{
                color: {text};
                font-weight: 700;
            }}

            QFrame#spotifyPlaylistTrackRow[playing="true"] {{
                background: {card_alt};
                border: 1px solid {accent};
            }}

            QLabel#spotifyPlaylistTrackTitle[playing="true"],
            QLabel#spotifyPlaylistTrackNumber[playing="true"] {{
                color: {accent};
                font-weight: 750;
            }}

            QPushButton#spotifyLikedSongsBack,
            QPushButton#spotifyLikedSongsLoadMore {{
                background: {card};
                color: {text};
                border: 1px solid {border};
                border-radius: 9px;
                padding: 7px 12px;
                font-weight: 700;
            }}

            QPushButton#spotifyLikedSongsBack:hover,
            QPushButton#spotifyLikedSongsLoadMore:hover {{
                border: 1px solid {accent};
                color: {accent};
            }}

            QScrollArea#spotifyLikedSongsScroll {{
                background: transparent;
                border: none;
            }}

            QWidget#spotifyLikedSongsTrackContainer {{
                background: transparent;
            }}
            """
        )
