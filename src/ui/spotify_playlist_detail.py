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

from src.spotify.playlist_models import (
    SpotifyPlaylistSummary,
)
from src.spotify.qt_playlist_runtime import (
    OPERATION_PLAYLIST_ITEMS,
)
from src.ui.theme import (
    ThemeManager,
)


SPOTIFY_PLAYLIST_DETAIL_LIMIT = 50


def _theme_value(
    theme: dict,
    key: str,
    fallback: str,
) -> str:
    return str(
        theme.get(
            key,
            fallback,
        )
        or fallback
    ).strip()


def format_duration(
    duration_ms,
) -> str:
    if (
        duration_ms is None
        or isinstance(
            duration_ms,
            bool,
        )
    ):
        return "--:--"

    try:
        milliseconds = int(
            duration_ms
        )

    except (
        TypeError,
        ValueError,
    ):
        return "--:--"

    if milliseconds < 0:
        return "--:--"

    total_seconds = (
        milliseconds // 1000
    )

    hours = (
        total_seconds // 3600
    )

    minutes = (
        total_seconds % 3600
    ) // 60

    seconds = (
        total_seconds % 60
    )

    if hours:
        return (
            str(hours)
            + ":"
            + str(minutes).zfill(2)
            + ":"
            + str(seconds).zfill(2)
        )

    return (
        str(minutes)
        + ":"
        + str(seconds).zfill(2)
    )


class SpotifyPlaylistTrackRow(
    QFrame
):
    activated = pyqtSignal(
        object
    )

    def __init__(
        self,
        resolved_item,
        *,
        number: int,
        artwork_loader=None,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        self.resolved_item = (
            resolved_item
        )
        self.artwork_loader = artwork_loader
        self._artwork_installed = False

        self._number_text = str(
            number
        )

        self.playing = False

        self.setObjectName(
            "spotifyPlaylistTrackRow"
        )

        self.setProperty(
            "playing",
            False,
        )

        layout = QHBoxLayout(
            self
        )

        layout.setContentsMargins(
            12,
            9,
            12,
            9,
        )

        layout.setSpacing(
            10
        )

        self.number_label = QLabel(
            self._number_text,
            self,
        )

        self.number_label.setObjectName(
            "spotifyPlaylistTrackNumber"
        )

        self.number_label.setProperty(
            "playing",
            False,
        )

        self.number_label.setFixedWidth(
            28
        )

        self.number_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        track = getattr(
            resolved_item,
            "unified_track",
            None,
        )

        is_local = bool(
            getattr(
                resolved_item,
                "is_local",
                False,
            )
        )

        self._artwork_reference = (
            str(
                getattr(
                    track,
                    "artwork_reference",
                    "",
                )
                or ""
            ).strip()
            if not is_local
            else ""
        )

        self.artwork_label = QLabel(
            "\u266b",
            self,
        )
        self.artwork_label.setObjectName(
            "spotifyPlaylistTrackArtwork"
        )
        self.artwork_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.artwork_label.setFixedSize(
            44,
            44,
        )

        title = str(
            getattr(
                track,
                "title",
                "",
            )
            or "Unknown track"
        )

        artist = str(
            getattr(
                track,
                "artist",
                "",
            )
            or "Unknown artist"
        )

        information = QVBoxLayout()

        information.setSpacing(
            1
        )

        self.title_label = QLabel(
            title,
            self,
        )

        self.title_label.setObjectName(
            "spotifyPlaylistTrackTitle"
        )

        self.title_label.setProperty(
            "playing",
            False,
        )

        self.title_label.setWordWrap(
            True
        )

        self.artist_label = QLabel(
            artist,
            self,
        )

        self.artist_label.setObjectName(
            "spotifyPlaylistTrackArtist"
        )

        self.artist_label.setWordWrap(
            True
        )

        information.addWidget(
            self.title_label
        )

        information.addWidget(
            self.artist_label
        )

        local_available = getattr(
            resolved_item,
            "local_available",
            None,
        )

        self.local_badge = QLabel(
            "",
            self,
        )

        self.local_badge.setObjectName(
            "spotifyPlaylistLocalBadge"
        )

        self.local_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        if is_local:
            if local_available is True:
                self.local_badge.setText(
                    "LOCAL"
                )

            else:
                self.local_badge.setText(
                    "LOCAL • UNAVAILABLE"
                )

                self.local_badge.setObjectName(
                    "spotifyPlaylistUnavailableBadge"
                )

            self.local_badge.setVisible(
                True
            )

        else:
            self.local_badge.setVisible(
                False
            )

        spotify_uri = str(
            getattr(
                track,
                "spotify_uri",
                "",
            )
            or ""
        ).strip()

        track_playable = bool(
            getattr(
                track,
                "playable",
                False,
            )
        )

        playlist_position = getattr(
            resolved_item,
            "position",
            None,
        )

        valid_playlist_position = bool(
            not isinstance(
                playlist_position,
                bool,
            )
            and isinstance(
                playlist_position,
                int,
            )
            and playlist_position >= 0
        )

        self.playback_available = bool(
            (
                is_local
                and local_available is True
                and track_playable
                and valid_playlist_position
            )
            or (
                not is_local
                and track_playable
                and spotify_uri.startswith(
                    "spotify:track:"
                )
            )
        )

        if self.playback_available:
            self.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

        self.duration_label = QLabel(
            format_duration(
                getattr(
                    track,
                    "duration_ms",
                    None,
                )
            ),
            self,
        )

        self.duration_label.setObjectName(
            "spotifyPlaylistTrackDuration"
        )

        self.duration_label.setAlignment(
            (
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )
        )

        self.duration_label.setMinimumWidth(
            52
        )

        layout.addWidget(
            self.number_label
        )

        layout.addWidget(
            self.artwork_label
        )

        layout.addLayout(
            information,
            stretch=1,
        )

        layout.addWidget(
            self.local_badge
        )

        layout.addWidget(
            self.duration_label
        )

        self._request_artwork()

    def _request_artwork(
        self,
    ) -> None:
        if (
            not self._artwork_reference
            or self.artwork_loader is None
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
            not callable(request)
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
                self._artwork_reference
            )
        except Exception:
            return

    def _handle_artwork_ready(
        self,
        artwork_url: str,
        pixmap,
    ) -> None:
        if artwork_url != self._artwork_reference:
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
            not callable(is_null)
            or not callable(scaled)
            or is_null()
        ):
            return

        display = scaled(
            self.artwork_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        if display.isNull():
            return

        self.artwork_label.setText("")
        self.artwork_label.setPixmap(display)
        self._artwork_installed = True

    def _handle_artwork_failed(
        self,
        artwork_url: str,
    ) -> None:
        if artwork_url != self._artwork_reference:
            return

        # The fallback is already present. In particular, never
        # replace a good pixmap after a later failure signal.
        if self._artwork_installed:
            return


    def set_playing(
        self,
        playing: bool,
    ) -> bool:
        state = bool(
            playing
        )

        if state == self.playing:
            return False

        self.playing = state

        self.setProperty(
            "playing",
            state,
        )

        self.number_label.setProperty(
            "playing",
            state,
        )

        self.title_label.setProperty(
            "playing",
            state,
        )

        self.number_label.setText(
            self._number_text
        )

        for widget in (
            self,
            self.number_label,
            self.title_label,
        ):
            style = widget.style()

            style.unpolish(
                widget
            )

            style.polish(
                widget
            )

            widget.update()

        return True

    def activate(
        self,
    ) -> bool:
        if not self.playback_available:
            return False

        self.activated.emit(
            self.resolved_item
        )

        return True

    def mouseReleaseEvent(
        self,
        event,
    ) -> None:
        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self.activate()

        super().mouseReleaseEvent(
            event
        )


class SpotifyPlaylistDetail(
    QWidget
):
    back_requested = pyqtSignal()

    def __init__(
        self,
        runtime,
        *,
        playback_runtime=None,
        theme_manager=None,
        artwork_loader=None,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        load_items = getattr(
            runtime,
            "load_playlist_items",
            None,
        )

        if not callable(
            load_items
        ):
            raise TypeError(
                (
                    "runtime must provide a callable "
                    "load_playlist_items method"
                )
            )

        self.runtime = runtime

        if playback_runtime is not None:
            for method_name in (
                "play_playlist_track",
                "play_playlist_position",
            ):
                play_method = getattr(
                    playback_runtime,
                    method_name,
                    None,
                )

                if not callable(
                    play_method
                ):
                    raise TypeError(
                        (
                            "playback_runtime must "
                            "provide a callable "
                            + method_name
                            + " method"
                        )
                    )

        self.playback_runtime = (
            playback_runtime
        )
        self.artwork_loader = artwork_loader

        self._active_playback_title = ""
        self._current_song = None

        self.theme_manager = (
            theme_manager
            or ThemeManager(
                self
            )
        )

        self.playlist = None
        self.rows = []
        self.last_result = None

        self._pending_load = False
        self._request_active = False

        self._pending_next_page = False
        self._requested_offset = None
        self._next_offset = 0
        self._total = None

        self._omitted_items = 0
        self._local_count = 0
        self._unavailable_local_count = 0
        self._local_snapshot_missing = False

        self._pagination_enabled = True

        self.setObjectName(
            "spotifyPlaylistDetailRoot"
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
            "← Back"
        )

        self.back_button.setObjectName(
            "spotifyPlaylistBackButton"
        )

        self.back_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        heading = QVBoxLayout()

        heading.setSpacing(
            1
        )

        self.title_label = QLabel(
            "Playlist"
        )

        self.title_label.setObjectName(
            "spotifyPlaylistDetailTitle"
        )

        self.subtitle_label = QLabel(
            "Choose a playlist from Spotify Home."
        )

        self.subtitle_label.setObjectName(
            "spotifyPlaylistDetailSubtitle"
        )

        heading.addWidget(
            self.title_label
        )

        heading.addWidget(
            self.subtitle_label
        )

        header.addWidget(
            self.back_button,
            alignment=(
                Qt.AlignmentFlag.AlignTop
            ),
        )

        header.addLayout(
            heading,
            stretch=1,
        )

        root.addLayout(
            header
        )

        self.status_label = QLabel(
            "Select a playlist to view its tracks."
        )

        self.status_label.setObjectName(
            "spotifyPlaylistDetailStatus"
        )

        self.status_label.setWordWrap(
            True
        )

        root.addWidget(
            self.status_label
        )

        self.scroll = QScrollArea()

        self.scroll.setObjectName(
            "spotifyPlaylistTrackScroll"
        )

        self.scroll.setWidgetResizable(
            True
        )

        self.scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.track_container = QWidget()

        self.track_container.setObjectName(
            "spotifyPlaylistTrackContainer"
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
            "No tracks to display."
        )

        self.empty_label.setObjectName(
            "spotifyPlaylistDetailEmpty"
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

    def connect_signals(
        self,
    ) -> None:
        self.back_button.clicked.connect(
            self._handle_back_clicked
        )

        signal_specs = (
            (
                "playlist_items_ready",
                self.handle_items_ready,
            ),
            (
                "failed",
                self.handle_runtime_failure,
            ),
            (
                "operation_finished",
                self.handle_operation_finished,
            ),
            (
                "busy_changed",
                self.handle_busy_changed,
            ),
        )

        for (
            signal_name,
            handler,
        ) in signal_specs:
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
            playback_signal_specs = (
                (
                    "result_ready",
                    self.handle_playback_result,
                ),
                (
                    "failed",
                    self.handle_playback_failure,
                ),
            )

            for (
                signal_name,
                handler,
            ) in playback_signal_specs:
                signal = getattr(
                    self.playback_runtime,
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

    @staticmethod
    def _identity_text(
        value,
    ) -> str:
        return " ".join(
            str(
                value
                or ""
            ).split()
        ).casefold()

    @classmethod
    def _spotify_song_is_playing(
        cls,
        song,
    ) -> bool:
        if song is None:
            return False

        if not bool(
            getattr(
                song,
                "playing",
                False,
            )
        ):
            return False

        title = cls._identity_text(
            getattr(
                song,
                "title",
                "",
            )
        )

        if not title:
            return False

        source_app = cls._identity_text(
            getattr(
                song,
                "source_app",
                "",
            )
        )

        return (
            "spotify"
            in source_app
        )

    @classmethod
    def _row_matches_song(
        cls,
        row,
        song,
    ) -> bool:
        track = getattr(
            getattr(
                row,
                "resolved_item",
                None,
            ),
            "unified_track",
            None,
        )

        if track is None:
            return False

        return (
            cls._identity_text(
                getattr(
                    track,
                    "title",
                    "",
                )
            )
            == cls._identity_text(
                getattr(
                    song,
                    "title",
                    "",
                )
            )
            and cls._identity_text(
                getattr(
                    track,
                    "artist",
                    "",
                )
            )
            == cls._identity_text(
                getattr(
                    song,
                    "artist",
                    "",
                )
            )
        )

    def _matching_current_row(
        self,
    ):
        song = self._current_song

        if not self._spotify_song_is_playing(
            song
        ):
            return None

        candidates = [
            row
            for row in self.rows
            if self._row_matches_song(
                row,
                song,
            )
        ]

        if len(
            candidates
        ) == 1:
            return candidates[0]

        if len(
            candidates
        ) <= 1:
            return None

        song_album = self._identity_text(
            getattr(
                song,
                "album",
                "",
            )
        )

        if not song_album:
            return None

        album_matches = []

        for row in candidates:
            track = getattr(
                getattr(
                    row,
                    "resolved_item",
                    None,
                ),
                "unified_track",
                None,
            )

            if track is None:
                continue

            track_album = (
                self._identity_text(
                    getattr(
                        track,
                        "album",
                        "",
                    )
                )
            )

            if (
                track_album
                == song_album
            ):
                album_matches.append(
                    row
                )

        if len(
            album_matches
        ) == 1:
            return album_matches[0]

        return None

    def _refresh_playing_rows(
        self,
    ) -> None:
        matching_row = (
            self._matching_current_row()
        )

        for row in self.rows:
            setter = getattr(
                row,
                "set_playing",
                None,
            )

            if callable(
                setter
            ):
                setter(
                    row is matching_row
                )

    def set_current_song(
        self,
        song,
    ) -> None:
        self._current_song = song

        self._refresh_playing_rows()

    def _update_playlist_subtitle(
        self,
        total_items,
    ) -> None:
        if self.playlist is None:
            return

        try:
            checked_total = int(
                total_items
            )

        except (
            TypeError,
            ValueError,
        ):
            return

        if checked_total < 0:
            return

        owner = (
            self.playlist.owner_name
            or "Unknown owner"
        )

        count = (
            str(
                checked_total
            )
            + (
                " track"
                if checked_total == 1
                else " tracks"
            )
        )

        self.subtitle_label.setText(
            (
                owner
                + " | "
                + count
            )
        )


    def set_playlist(
        self,
        playlist,
    ) -> None:
        if not isinstance(
            playlist,
            SpotifyPlaylistSummary,
        ):
            raise TypeError(
                (
                    "playlist must be a "
                    "SpotifyPlaylistSummary"
                )
            )

        self.playlist = playlist
        self.last_result = None

        self._pending_load = False
        self._request_active = False
        self._pending_next_page = False

        self._requested_offset = None
        self._next_offset = 0
        self._total = None

        self._omitted_items = 0
        self._local_count = 0
        self._unavailable_local_count = 0
        self._local_snapshot_missing = False

        self._pagination_enabled = True

        self.clear_tracks()

        self.title_label.setText(
            playlist.name
        )

        owner = (
            playlist.owner_name
            or "Unknown owner"
        )

        count = (
            str(
                playlist.total_items
            )
            + (
                " track"
                if playlist.total_items == 1
                else " tracks"
            )
        )

        self.subtitle_label.setText(
            (
                owner
                + " | "
                + count
            )
        )

        self.status_label.setText(
            "Ready to load playlist tracks."
        )


    def load(
        self,
    ) -> bool:
        if self.playlist is None:
            return False

        if not self._pagination_enabled:
            return False

        if bool(
            getattr(
                self.runtime,
                "busy",
                False,
            )
        ):
            self._pending_load = True

            self.status_label.setText(
                (
                    "Waiting for the current "
                    "Spotify request to finish..."
                )
            )

            return False

        return self._request_page(
            0
        )

    def clear_tracks(
        self,
    ) -> None:
        for row in self.rows:
            self.track_layout.removeWidget(
                row
            )

            row.deleteLater()

        self.rows.clear()

        self.empty_label.setText(
            "No tracks to display."
        )

        self.empty_label.setVisible(
            True
        )

    def set_resolved_page(
        self,
        page,
        *,
        local_snapshot_available=None,
    ) -> bool:
        self.clear_tracks()

        self._omitted_items = 0
        self._local_count = 0
        self._unavailable_local_count = 0
        self._local_snapshot_missing = False

        self._next_offset = 0
        self._total = None

        return self._append_resolved_page(
            page,
            local_snapshot_available=(
                local_snapshot_available
            ),
        )

    @staticmethod
    def _playlist_items_error_message(
        error_code,
        message,
    ) -> str:
        checked_code = str(
            error_code
            or ""
        ).strip().lower()

        if checked_code == "forbidden":
            return (
                "Spotify did not allow this app "
                "to load tracks for this playlist."
            )

        return str(
            message
            or (
                "Spotify could not load "
                "this playlist."
            )
        ).strip()

    @staticmethod
    def _playlist_items_error_is_forbidden(
        error_code,
    ) -> bool:
        return (
            str(
                error_code
                or ""
            ).strip().lower()
            == "forbidden"
        )

    def _update_playlist_subtitle_unavailable(
        self,
    ) -> None:
        if self.playlist is None:
            return

        owner = (
            self.playlist.owner_name
            or "Unknown owner"
        )

        self.subtitle_label.setText(
            (
                owner
                + " | track count unavailable"
            )
        )


    def handle_items_ready(
        self,
        playlist_id: str,
        result,
    ) -> None:
        if self.playlist is None:
            return

        if (
            str(
                playlist_id
            )
            != self.playlist.spotify_id
        ):
            return

        if not self._request_active:
            return

        requested_offset = (
            self._requested_offset
        )

        self._request_active = False
        self._requested_offset = None

        if not self._pagination_enabled:
            return

        self.last_result = result

        if not bool(
            getattr(
                result,
                "ready",
                False,
            )
        ):
            self._pending_load = False
            self._pending_next_page = False

            error_code = getattr(
                result,
                "error_code",
                "",
            )

            message = (
                self._playlist_items_error_message(
                    error_code,
                    getattr(
                        result,
                        "message",
                        "",
                    ),
                )
            )

            if self.rows:
                self.status_label.setText(
                    (
                        str(
                            len(
                                self.rows
                            )
                        )
                        + " tracks loaded • "
                        + message
                    )
                )

            else:
                self.clear_tracks()

                if (
                    self
                    ._playlist_items_error_is_forbidden(
                        error_code
                    )
                ):
                    self.empty_label.setText(
                        "Track list unavailable."
                    )


                    self._update_playlist_subtitle_unavailable()

                self.status_label.setText(
                    message
                )

            return

        page = getattr(
            result,
            "resolved_page",
            None,
        )

        if page is None:
            self._pending_load = False
            self._pending_next_page = False

            message = (
                "Spotify returned no usable "
                "playlist track page."
            )

            if self.rows:
                self.status_label.setText(
                    (
                        str(
                            len(
                                self.rows
                            )
                        )
                        + " tracks loaded • "
                        + message
                    )
                )

            else:
                self.clear_tracks()

                self.status_label.setText(
                    message
                )

            return

        page_offset = int(
            getattr(
                page,
                "offset",
                -1,
            )
        )

        if (
            requested_offset is None
            or page_offset
            != requested_offset
        ):
            self._pending_load = False
            self._pending_next_page = False

            self.status_label.setText(
                (
                    "Spotify returned playlist "
                    "pagination out of sequence."
                )
            )

            return

        if page_offset == 0:
            complete = (
                self.set_resolved_page(
                    page,
                    local_snapshot_available=(
                        getattr(
                            result,
                            "local_snapshot_available",
                            None,
                        )
                    ),
                )
            )

        else:
            complete = (
                self._append_resolved_page(
                    page,
                    local_snapshot_available=(
                        getattr(
                            result,
                            "local_snapshot_available",
                            None,
                        )
                    ),
                )
            )

        self._pending_load = False

        self._pending_next_page = (
            not complete
            and self._pagination_enabled
        )

    def handle_runtime_failure(
        self,
        operation: str,
        target: str,
        error_code: str,
        message: str,
    ) -> None:
        if (
            operation
            != OPERATION_PLAYLIST_ITEMS
        ):
            return

        if self.playlist is None:
            return

        if (
            str(
                target
            )
            != self.playlist.spotify_id
        ):
            return

        if not self._request_active:
            return

        self._request_active = False
        self._requested_offset = None

        self._pending_load = False
        self._pending_next_page = False

        if not self._pagination_enabled:
            return

        safe_message = (
            self._playlist_items_error_message(
                error_code,
                message,
            )
        )

        if self.rows:
            self.status_label.setText(
                (
                    str(
                        len(
                            self.rows
                        )
                    )
                    + " tracks loaded • "
                    + safe_message
                )
            )

        else:
            if (
                self
                ._playlist_items_error_is_forbidden(
                    error_code
                )
            ):
                self.empty_label.setText(
                    "Track list unavailable."
                )


                self._update_playlist_subtitle_unavailable()

            self.status_label.setText(
                safe_message
            )

    def handle_busy_changed(
        self,
        busy: bool,
    ) -> None:
        if busy:
            return

        if not self._pending_load:
            return

        operation_finished = getattr(
            self.runtime,
            "operation_finished",
            None,
        )

        if operation_finished is not None:
            return

        self.load()

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

        is_local = bool(
            getattr(
                resolved_item,
                "is_local",
                False,
            )
        )

        if not bool(
            getattr(
                track,
                "playable",
                False,
            )
        ):
            return False

        playlist_position = None
        spotify_uri = ""

        if is_local:
            if (
                getattr(
                    resolved_item,
                    "local_available",
                    None,
                )
                is not True
            ):
                return False

            playlist_position = getattr(
                resolved_item,
                "position",
                None,
            )

            if (
                isinstance(
                    playlist_position,
                    bool,
                )
                or not isinstance(
                    playlist_position,
                    int,
                )
                or playlist_position < 0
            ):
                return False

        else:
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
            or "track"
        )

        self.status_label.setText(
            (
                "Starting "
                + self._active_playback_title
                + "..."
            )
        )

        try:
            if self.playlist is None:
                self._active_playback_title = ""

                self.status_label.setText(
                    (
                        "Spotify playlist context "
                        "is unavailable."
                    )
                )

                return False

            if is_local:
                (
                    self.playback_runtime
                    .play_playlist_position(
                        self.playlist.spotify_id,
                        playlist_position,
                    )
                )

            else:
                (
                    self.playback_runtime
                    .play_playlist_track(
                        self.playlist.spotify_id,
                        spotify_uri,
                    )
                )

        except Exception as error:
            error_code = str(
                getattr(
                    error,
                    "error_code",
                    "",
                )
                or ""
            )

            if error_code == "busy":
                message = (
                    "A Spotify playback request "
                    "is already running."
                )

            elif error_code == "shutting_down":
                message = (
                    "Spotify playback is "
                    "shutting down."
                )

            else:
                message = (
                    "Spotify playback could "
                    "not start."
                )

            self._active_playback_title = ""

            self.status_label.setText(
                message
            )

            return False

        return True


    def handle_playback_result(
        self,
        result,
    ) -> None:
        title = (
            self._active_playback_title
            or "track"
        )

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
                "not be started."
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
            message = (
                message
                + " Try again in "
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
        self._active_playback_title = ""

        safe_message = str(
            message
            or (
                "Spotify playback could "
                "not be started."
            )
        ).strip()

        self.status_label.setText(
            safe_message
        )

    def _handle_back_clicked(
        self,
    ) -> None:
        self._pagination_enabled = False
        self._pending_load = False
        self._pending_next_page = False

        self.back_requested.emit()

    def _request_page(
        self,
        offset: int,
    ) -> bool:
        if self.playlist is None:
            return False

        if not self._pagination_enabled:
            return False

        if self._request_active:
            return False

        if bool(
            getattr(
                self.runtime,
                "busy",
                False,
            )
        ):
            if offset == 0:
                self._pending_load = True

            else:
                self._pending_next_page = True

            return False

        checked_offset = int(
            offset
        )

        if checked_offset < 0:
            return False

        self._pending_load = False

        if checked_offset > 0:
            self._pending_next_page = False

        self._request_active = True
        self._requested_offset = (
            checked_offset
        )

        if checked_offset == 0:
            self.status_label.setText(
                "Loading playlist tracks..."
            )

        else:
            total = (
                self._total
                if self._total is not None
                else self.playlist.total_items
            )

            self.status_label.setText(
                (
                    str(
                        len(
                            self.rows
                        )
                    )
                    + " / "
                    + str(
                        total
                    )
                    + " tracks loaded • "
                    "loading more..."
                )
            )

        try:
            self.runtime.load_playlist_items(
                self.playlist.spotify_id,
                limit=(
                    SPOTIFY_PLAYLIST_DETAIL_LIMIT
                ),
                offset=checked_offset,
            )

        except Exception:
            self._request_active = False
            self._requested_offset = None

            if checked_offset == 0:
                self.status_label.setText(
                    (
                        "Playlist tracks could not "
                        "be requested right now."
                    )
                )

            else:
                self.status_label.setText(
                    (
                        str(
                            len(
                                self.rows
                            )
                        )
                        + " tracks loaded • "
                        "remaining tracks could not "
                        "be requested right now."
                    )
                )

            return False

        return True

    def _append_resolved_page(
        self,
        page,
        *,
        local_snapshot_available=None,
    ) -> bool:
        items = tuple(
            getattr(
                page,
                "items",
                (),
            )
        )

        page_offset = int(
            getattr(
                page,
                "offset",
                0,
            )
            or 0
        )

        page_limit = int(
            getattr(
                page,
                "limit",
                0,
            )
            or 0
        )

        page_total = int(
            getattr(
                page,
                "total",
                0,
            )
            or 0
        )

        omitted_items = int(
            getattr(
                page,
                "omitted_items",
                0,
            )
            or 0
        )

        if page_limit <= 0:
            self._pending_next_page = False

            self.status_label.setText(
                (
                    "Spotify returned invalid "
                    "playlist pagination."
                )
            )

            return True

        if (
            self._total is not None
            and page_total
            != self._total
        ):
            self._pending_next_page = False

            self.status_label.setText(
                (
                    "Spotify changed the playlist "
                    "while it was loading. "
                    "Reopen it to refresh."
                )
            )

            return True

        self._total = page_total

        self._update_playlist_subtitle(
            page_total
        )

        stretch_index = (
            self.track_layout.count()
            - 1
        )

        for item in items:
            row = (
                SpotifyPlaylistTrackRow(
                    item,
                    number=(
                        len(
                            self.rows
                        )
                        + 1
                    ),
                    artwork_loader=(
                        self.artwork_loader
                    ),
                    parent=(
                        self.track_container
                    ),
                )
            )

            row.activated.connect(
                self._handle_track_activated
            )

            self.rows.append(
                row
            )

            self.track_layout.insertWidget(
                stretch_index,
                row,
            )

            stretch_index += 1

        self._refresh_playing_rows()

        self.empty_label.setVisible(
            not bool(
                self.rows
            )
        )

        self._omitted_items += (
            omitted_items
        )

        page_local_count = int(
            getattr(
                page,
                "local_count",
                0,
            )
            or 0
        )

        self._local_count += (
            page_local_count
        )

        self._unavailable_local_count += int(
            getattr(
                page,
                "unavailable_local_count",
                0,
            )
            or 0
        )

        if (
            page_local_count > 0
            and local_snapshot_available
            is False
        ):
            self._local_snapshot_missing = True

        next_offset = (
            page_offset
            + page_limit
        )

        if next_offset <= page_offset:
            self._pending_next_page = False

            self.status_label.setText(
                (
                    "Spotify returned invalid "
                    "playlist pagination."
                )
            )

            return True

        self._next_offset = min(
            next_offset,
            page_total,
        )

        complete = (
            self._next_offset
            >= page_total
        )

        self._update_pagination_status(
            complete=complete
        )

        return complete

    def _update_pagination_status(
        self,
        *,
        complete: bool,
    ) -> None:
        total = (
            self._total
            if self._total is not None
            else 0
        )

        shown = len(
            self.rows
        )

        if complete:
            if self._omitted_items:
                summary = (
                    str(
                        shown
                    )
                    + " tracks loaded • "
                    + str(
                        self._omitted_items
                    )
                    + (
                        " unsupported playlist item skipped"
                        if self._omitted_items == 1
                        else " unsupported playlist items skipped"
                    )
                )

            else:
                summary = (
                    str(
                        shown
                    )
                    + " / "
                    + str(
                        total
                    )
                    + " tracks loaded"
                )

        else:
            summary = (
                str(
                    shown
                )
                + " / "
                + str(
                    total
                )
                + " tracks loaded • "
                "loading more..."
            )

        if self._local_count:
            summary += (
                " • "
                + str(
                    self._local_count
                )
                + " local"
            )

        if self._unavailable_local_count:
            summary += (
                " • "
                + str(
                    self._unavailable_local_count
                )
                + " unavailable"
            )

        if self._local_snapshot_missing:
            summary += (
                " • Rescan Local Music in "
                "Settings to resolve local tracks"
            )

        self.status_label.setText(
            summary
        )

    def handle_operation_finished(
        self,
        operation: str,
        target: str,
    ) -> None:
        if self.playlist is None:
            return

        if not self._pagination_enabled:
            return

        if self._request_active:
            return

        if self._pending_load:
            if not bool(
                getattr(
                    self.runtime,
                    "busy",
                    False,
                )
            ):
                self.load()

            return

        if (
            operation
            != OPERATION_PLAYLIST_ITEMS
        ):
            return

        if (
            str(
                target
            )
            != self.playlist.spotify_id
        ):
            return

        if not self._pending_next_page:
            return

        if self._total is None:
            return

        if self._next_offset >= self._total:
            self._pending_next_page = False
            return

        self._request_page(
            self._next_offset
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
            QWidget#spotifyPlaylistDetailRoot {{
                background: transparent;
                color: {text};
            }}

            QPushButton#spotifyPlaylistBackButton {{
                color: {text};
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 7px 10px;
                font-weight: 650;
            }}

            QPushButton#spotifyPlaylistBackButton:hover {{
                border: 1px solid {accent};
            }}

            QLabel#spotifyPlaylistDetailTitle {{
                color: {text};
                font-size: 22px;
                font-weight: 750;
            }}

            QLabel#spotifyPlaylistDetailSubtitle,
            QLabel#spotifyPlaylistDetailStatus,
            QLabel#spotifyPlaylistDetailEmpty,
            QLabel#spotifyPlaylistTrackArtist,
            QLabel#spotifyPlaylistTrackDuration,
            QLabel#spotifyPlaylistTrackNumber {{
                color: {muted};
            }}

            QScrollArea#spotifyPlaylistTrackScroll {{
                background: transparent;
                border: none;
            }}

            QWidget#spotifyPlaylistTrackContainer {{
                background: transparent;
            }}

            QFrame#spotifyPlaylistTrackRow {{
                background: {card};
                border: 1px solid {border};
                border-radius: 10px;
            }}

            QFrame#spotifyPlaylistTrackRow[playing="true"] {{
                background: {card_alt};
                border: 1px solid {accent};
            }}

            QLabel#spotifyPlaylistTrackTitle {{
                color: {text};
                font-weight: 650;
            }}

            QLabel#spotifyPlaylistTrackTitle[playing="true"],
            QLabel#spotifyPlaylistTrackNumber[playing="true"] {{
                color: {accent};
                font-weight: 750;
            }}

            QLabel#spotifyPlaylistLocalBadge {{
                color: {accent};
                background: {background};
                border: 1px solid {accent};
                border-radius: 6px;
                padding: 3px 7px;
                font-size: 9px;
                font-weight: 750;
            }}

            QLabel#spotifyPlaylistUnavailableBadge {{
                color: {muted};
                background: {background};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 3px 7px;
                font-size: 9px;
                font-weight: 750;
            }}
            """
        )
