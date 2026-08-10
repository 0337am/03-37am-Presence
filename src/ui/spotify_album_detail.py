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

from src.spotify.album_models import (
    SpotifyAlbumTrack,
)
from src.spotify.qt_album_runtime import (
    OPERATION_ALBUM,
    OPERATION_ALBUM_TRACKS,
    SpotifyQtAlbumRuntimeError,
)
from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
)
from src.ui.theme import (
    ThemeManager,
)
from src.ui.spotify_artwork import (
    SpotifyArtworkLoader,
)


SPOTIFY_ALBUM_DETAIL_LIMIT = 50


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


def format_album_duration(
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

    minutes = (
        total_seconds // 60
    )

    seconds = (
        total_seconds % 60
    )

    return (
        str(minutes)
        + ":"
        + str(seconds).zfill(2)
    )


class SpotifyAlbumTrackRow(
    QFrame
):
    activated = pyqtSignal(object)

    def __init__(
        self,
        track: SpotifyAlbumTrack,
        *,
        number: int,
        parent=None,
    ) -> None:
        if not isinstance(
            track,
            SpotifyAlbumTrack,
        ):
            raise TypeError(
                (
                    "track must be a "
                    "SpotifyAlbumTrack"
                )
            )

        super().__init__(
            parent
        )

        self.track = track

        if getattr(
            track,
            "is_playable",
            None,
        ) is not False:
            self.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

        self.setObjectName(
            "spotifyAlbumTrackRow"
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

        self.number_label = QLabel(
            str(
                number
            ),
            self,
        )

        self.number_label.setObjectName(
            "spotifyAlbumTrackNumber"
        )

        self.number_label.setFixedWidth(
            32
        )

        self.number_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        information = QVBoxLayout()

        information.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        information.setSpacing(
            1
        )

        self.title_label = QLabel(
            track.name,
            self,
        )

        self.title_label.setObjectName(
            "spotifyAlbumTrackTitle"
        )

        self.title_label.setWordWrap(
            True
        )

        self.artist_label = QLabel(
            track.artist_text,
            self,
        )

        self.artist_label.setObjectName(
            "spotifyAlbumTrackArtist"
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

        self.explicit_label = QLabel(
            "E" if track.explicit else "",
            self,
        )

        self.explicit_label.setObjectName(
            "spotifyAlbumExplicitBadge"
        )

        self.explicit_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.explicit_label.setVisible(
            bool(
                track.explicit
            )
        )

        self.duration_label = QLabel(
            format_album_duration(
                track.duration_ms
            ),
            self,
        )

        self.duration_label.setObjectName(
            "spotifyAlbumTrackDuration"
        )

        root.addWidget(
            self.number_label
        )

        root.addLayout(
            information,
            stretch=1,
        )

        root.addWidget(
            self.explicit_label
        )

        root.addWidget(
            self.duration_label
        )

    def activate(
        self,
    ) -> bool:
        if getattr(
            self.track,
            "is_playable",
            None,
        ) is False:
            return False

        spotify_id = str(
            getattr(
                self.track,
                "spotify_id",
                "",
            )
            or ""
        ).strip()

        spotify_uri = str(
            getattr(
                self.track,
                "uri",
                "",
            )
            or ""
        ).strip()

        if (
            not spotify_id
            or spotify_uri
            != "spotify:track:" + spotify_id
        ):
            return False

        self.activated.emit(
            self.track
        )

        return True

    def mouseReleaseEvent(
        self,
        event,
    ) -> None:
        if (
            event.button()
            == Qt.MouseButton.LeftButton
            and self.rect().contains(
                event.position().toPoint()
            )
        ):
            self.activate()

        super().mouseReleaseEvent(
            event
        )


class SpotifyAlbumDetail(
    QWidget
):
    back_requested = pyqtSignal()

    def __init__(
        self,
        album_runtime,
        *,
        playback_runtime=None,
        artwork_loader=None,
        theme_manager=None,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        if playback_runtime is not None:
            play_track = getattr(
                playback_runtime,
                "play_track",
                None,
            )

            if not callable(
                play_track
            ):
                raise TypeError(
                    (
                        "playback_runtime must provide "
                        "a callable play_track method"
                    )
                )

        self.playback_runtime = (
            playback_runtime
        )

        load_album = getattr(
            album_runtime,
            "load_album",
            None,
        )

        load_album_tracks = getattr(
            album_runtime,
            "load_album_tracks",
            None,
        )

        if not callable(
            load_album
        ):
            raise TypeError(
                (
                    "album_runtime must provide "
                    "a callable load_album method"
                )
            )

        if not callable(
            load_album_tracks
        ):
            raise TypeError(
                (
                    "album_runtime must provide "
                    "a callable load_album_tracks method"
                )
            )

        self.album_runtime = (
            album_runtime
        )

        self.theme_manager = (
            theme_manager
            or ThemeManager(
                self
            )
        )

        if artwork_loader is None:
            artwork_loader = (
                SpotifyArtworkLoader(
                    parent=self
                )
            )

        self.artwork_loader = (
            artwork_loader
        )

        self._search_item = None
        self._album_id = ""
        self._album = None
        self._artwork_reference = ""

        self._track_rows = []
        self._loaded_count = 0
        self._total_tracks = 0

        self._pending_initial_tracks = False

        self.setObjectName(
            "spotifyAlbumDetail"
        )

        self._build_ui()
        self._connect_runtime()
        self._connect_artwork_loader()

        self.theme_manager.theme_changed.connect(
            self.apply_theme
        )

        self.apply_theme(
            self.theme_manager.theme()
        )

    def _build_ui(
        self,
    ) -> None:
        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            20,
            16,
            20,
            20,
        )

        root.setSpacing(
            12
        )

        header = QHBoxLayout()

        header.setSpacing(
            12
        )

        self.back_button = QPushButton(
            "Back",
            self,
        )

        self.back_button.setObjectName(
            "spotifyAlbumBackButton"
        )

        self.back_button.clicked.connect(
            self.back_requested.emit
        )

        self.artwork_label = QLabel(
            "Album",
            self,
        )

        self.artwork_label.setObjectName(
            "spotifyAlbumArtwork"
        )

        self.artwork_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.artwork_label.setFixedSize(
            112,
            112,
        )

        heading = QVBoxLayout()

        heading.setSpacing(
            2
        )

        self.title_label = QLabel(
            "Album",
            self,
        )

        self.title_label.setObjectName(
            "spotifyAlbumTitle"
        )

        self.title_label.setWordWrap(
            True
        )

        self.artist_label = QLabel(
            "",
            self,
        )

        self.artist_label.setObjectName(
            "spotifyAlbumArtist"
        )

        self.artist_label.setWordWrap(
            True
        )

        self.metadata_label = QLabel(
            "",
            self,
        )

        self.metadata_label.setObjectName(
            "spotifyAlbumMetadata"
        )

        self.metadata_label.setWordWrap(
            True
        )

        heading.addWidget(
            self.title_label
        )

        heading.addWidget(
            self.artist_label
        )

        heading.addWidget(
            self.metadata_label
        )

        header.addWidget(
            self.back_button,
            alignment=(
                Qt.AlignmentFlag.AlignTop
            ),
        )

        header.addWidget(
            self.artwork_label,
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
            "",
            self,
        )

        self.status_label.setObjectName(
            "spotifyAlbumStatus"
        )

        self.status_label.setWordWrap(
            True
        )

        root.addWidget(
            self.status_label
        )

        self.scroll_area = QScrollArea(
            self
        )

        self.scroll_area.setObjectName(
            "spotifyAlbumTrackScroll"
        )

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.track_container = QWidget(
            self.scroll_area
        )

        self.track_container.setObjectName(
            "spotifyAlbumTrackContainer"
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
            "Choose an album from Search.",
            self.track_container,
        )

        self.empty_label.setObjectName(
            "spotifyAlbumEmpty"
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

        self.track_layout.addStretch(
            1
        )

        self.scroll_area.setWidget(
            self.track_container
        )

        root.addWidget(
            self.scroll_area,
            stretch=1,
        )

        self.load_more_button = QPushButton(
            "Load More",
            self,
        )

        self.load_more_button.setObjectName(
            "spotifyAlbumLoadMore"
        )

        self.load_more_button.setVisible(
            False
        )

        self.load_more_button.clicked.connect(
            self.load_more
        )

        root.addWidget(
            self.load_more_button
        )

    def _connect_runtime(
        self,
    ) -> None:
        album_ready = getattr(
            self.album_runtime,
            "album_ready",
            None,
        )

        tracks_ready = getattr(
            self.album_runtime,
            "album_tracks_ready",
            None,
        )

        failed = getattr(
            self.album_runtime,
            "failed",
            None,
        )

        operation_finished = getattr(
            self.album_runtime,
            "operation_finished",
            None,
        )

        if album_ready is not None:
            album_ready.connect(
                self.handle_album_ready
            )

        if tracks_ready is not None:
            tracks_ready.connect(
                self.handle_album_tracks_ready
            )

        if failed is not None:
            failed.connect(
                self.handle_runtime_failure
            )

        if operation_finished is not None:
            operation_finished.connect(
                self.handle_operation_finished
            )

    def _connect_artwork_loader(
        self,
    ) -> None:
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

        if ready is not None:
            ready.connect(
                self._handle_artwork_ready
            )

        if failed is not None:
            failed.connect(
                self._handle_artwork_failed
            )

    def _set_artwork_reference(
        self,
        reference,
    ) -> None:
        checked = (
            reference.strip()
            if isinstance(
                reference,
                str,
            )
            else ""
        )

        if (
            checked
            != self._artwork_reference
        ):
            self._artwork_reference = (
                checked
            )

            self.artwork_label.clear()
            self.artwork_label.setText(
                "Album"
            )

        if not checked:
            return

        request = getattr(
            self.artwork_loader,
            "request",
            None,
        )

        if not callable(
            request
        ):
            return

        try:
            request(
                checked
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
            != self._artwork_reference
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
            display = scaled(
                self.artwork_label.size(),
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

        self.artwork_label.setText(
            ""
        )

        self.artwork_label.setPixmap(
            display
        )

    def _handle_artwork_failed(
        self,
        artwork_url: str,
    ) -> None:
        if (
            artwork_url
            != self._artwork_reference
        ):
            return

    def _clear_tracks(
        self,
    ) -> None:
        for row in self._track_rows:
            self.track_layout.removeWidget(
                row
            )

            row.deleteLater()

        self._track_rows = []

        self._loaded_count = 0
        self._total_tracks = 0

        self.load_more_button.setVisible(
            False
        )

        self.empty_label.setVisible(
            True
        )

    def set_search_item(
        self,
        item,
    ) -> bool:
        if not isinstance(
            item,
            SpotifySearchItem,
        ):
            return False

        if (
            item.item_type
            is not SpotifySearchItemType.ALBUM
        ):
            return False

        uri = (
            item.uri.strip()
            if isinstance(
                item.uri,
                str,
            )
            else ""
        )

        expected_uri = (
            "spotify:album:"
            + item.spotify_id
        )

        if uri != expected_uri:
            return False

        self._search_item = item
        self._album_id = item.spotify_id
        self._album = None

        self._pending_initial_tracks = False

        self.title_label.setText(
            item.name
        )

        subtitle = (
            item.subtitle.strip()
            if isinstance(
                item.subtitle,
                str,
            )
            else ""
        )

        if subtitle.casefold() == "album":
            subtitle = ""

        self.artist_label.setText(
            subtitle
        )

        self.metadata_label.setText(
            "Album"
        )

        self._set_artwork_reference(
            item.image_url
        )

        self.status_label.setText(
            ""
        )

        self._clear_tracks()

        self.empty_label.setText(
            "Album tracks have not been loaded yet."
        )

        return True

    def load(
        self,
    ) -> bool:
        if not self._album_id:
            return False

        self._clear_tracks()

        self.empty_label.setText(
            "Loading album..."
        )

        self.status_label.setText(
            "Loading album..."
        )

        self._pending_initial_tracks = True

        try:
            self.album_runtime.load_album(
                self._album_id
            )

        except SpotifyQtAlbumRuntimeError as error:
            self._pending_initial_tracks = False

            self.status_label.setText(
                str(
                    error
                )
            )

            self.empty_label.setText(
                "Album unavailable."
            )

            return False

        except Exception:
            self._pending_initial_tracks = False

            self.status_label.setText(
                "Spotify album could not be loaded."
            )

            self.empty_label.setText(
                "Album unavailable."
            )

            return False

        return True

    def _metadata_text(
        self,
        album,
    ) -> str:
        parts = []

        album_type = str(
            getattr(
                album,
                "album_type",
                "",
            )
            or ""
        ).strip()

        if album_type:
            parts.append(
                album_type.title()
            )

        release_date = str(
            getattr(
                album,
                "release_date",
                "",
            )
            or ""
        ).strip()

        if release_date:
            parts.append(
                release_date
            )

        total_tracks = getattr(
            album,
            "total_tracks",
            None,
        )

        if (
            isinstance(
                total_tracks,
                int,
            )
            and not isinstance(
                total_tracks,
                bool,
            )
        ):
            suffix = (
                "track"
                if total_tracks == 1
                else "tracks"
            )

            parts.append(
                str(
                    total_tracks
                )
                + " "
                + suffix
            )

        return " | ".join(
            parts
        )

    def handle_album_ready(
        self,
        album_id: str,
        result,
    ) -> None:
        if album_id != self._album_id:
            return

        ready = bool(
            getattr(
                result,
                "ready",
                False,
            )
        )

        album = getattr(
            result,
            "album",
            None,
        )

        if (
            not ready
            or album is None
        ):
            self._pending_initial_tracks = False

            message = str(
                getattr(
                    result,
                    "message",
                    "",
                )
                or (
                    "Spotify album could "
                    "not be loaded."
                )
            )

            self.status_label.setText(
                message
            )

            self.empty_label.setText(
                "Album unavailable."
            )

            return

        self._album = album

        self.title_label.setText(
            album.name
        )

        self.artist_label.setText(
            album.artist_text
        )

        self.metadata_label.setText(
            self._metadata_text(
                album
            )
        )

        album_artwork = str(
            getattr(
                album,
                "image_url",
                "",
            )
            or ""
        ).strip()

        if album_artwork:
            self._set_artwork_reference(
                album_artwork
            )

        self.status_label.setText(
            "Album loaded. Loading tracks..."
        )

        self.empty_label.setText(
            "Loading tracks..."
        )

    def handle_operation_finished(
        self,
        operation: str,
        target: str,
    ) -> None:
        if target != self._album_id:
            return

        if operation != OPERATION_ALBUM:
            return

        if not self._pending_initial_tracks:
            return

        if self._album is None:
            self._pending_initial_tracks = False
            return

        self._pending_initial_tracks = False

        self._request_tracks(
            0
        )

    def _request_tracks(
        self,
        offset: int,
    ) -> bool:
        if not self._album_id:
            return False

        self.status_label.setText(
            "Loading album tracks..."
        )

        try:
            self.album_runtime.load_album_tracks(
                self._album_id,
                limit=(
                    SPOTIFY_ALBUM_DETAIL_LIMIT
                ),
                offset=offset,
            )

        except SpotifyQtAlbumRuntimeError as error:
            self.status_label.setText(
                str(
                    error
                )
            )

            return False

        except Exception:
            self.status_label.setText(
                (
                    "Spotify album tracks "
                    "could not be loaded."
                )
            )

            return False

        return True

    def load_more(
        self,
    ) -> bool:
        if (
            self._loaded_count
            >= self._total_tracks
        ):
            return False

        return self._request_tracks(
            self._loaded_count
        )

    def _handle_track_activated(
        self,
        track,
    ) -> bool:
        if not isinstance(
            track,
            SpotifyAlbumTrack,
        ):
            return False

        if getattr(
            track,
            "is_playable",
            None,
        ) is False:
            return False

        spotify_id = str(
            getattr(
                track,
                "spotify_id",
                "",
            )
            or ""
        ).strip()

        spotify_uri = str(
            getattr(
                track,
                "uri",
                "",
            )
            or ""
        ).strip()

        if (
            not spotify_id
            or spotify_uri
            != "spotify:track:" + spotify_id
        ):
            return False

        play_track = getattr(
            self.playback_runtime,
            "play_track",
            None,
        )

        if not callable(
            play_track
        ):
            return False

        try:
            play_track(
                spotify_uri
            )

        except Exception:
            return False

        return True

    def _append_track(
        self,
        track,
    ) -> None:
        if not isinstance(
            track,
            SpotifyAlbumTrack,
        ):
            return

        number = (
            len(
                self._track_rows
            )
            + 1
        )

        row = SpotifyAlbumTrackRow(
            track,
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

        self._track_rows.append(
            row
        )

    def handle_album_tracks_ready(
        self,
        album_id: str,
        result,
    ) -> None:
        if album_id != self._album_id:
            return

        ready = bool(
            getattr(
                result,
                "ready",
                False,
            )
        )

        page = getattr(
            result,
            "tracks_page",
            None,
        )

        if (
            not ready
            or page is None
        ):
            message = str(
                getattr(
                    result,
                    "message",
                    "",
                )
                or (
                    "Spotify album tracks "
                    "could not be loaded."
                )
            )

            self.status_label.setText(
                message
            )

            if not self._track_rows:
                self.empty_label.setText(
                    "Track list unavailable."
                )

            return

        if page.offset == 0:
            self._clear_tracks()

        for track in page.items:
            self._append_track(
                track
            )

        self._loaded_count = (
            page.offset
            + len(
                page.items
            )
        )

        self._total_tracks = (
            page.total
        )

        self.empty_label.setVisible(
            not bool(
                self._track_rows
            )
        )

        if not self._track_rows:
            self.empty_label.setText(
                "This album has no tracks."
            )

        has_more = (
            self._loaded_count
            < self._total_tracks
        )

        self.load_more_button.setVisible(
            has_more
        )

        self.status_label.setText(
            (
                "Loaded "
                + str(
                    self._loaded_count
                )
                + " of "
                + str(
                    self._total_tracks
                )
                + " tracks."
            )
        )

    def handle_runtime_failure(
        self,
        operation: str,
        target: str,
        error_code: str,
        message: str,
    ) -> None:
        del error_code

        if target != self._album_id:
            return

        if operation not in {
            OPERATION_ALBUM,
            OPERATION_ALBUM_TRACKS,
        }:
            return

        if operation == OPERATION_ALBUM:
            self._pending_initial_tracks = False

        safe_message = str(
            message
            or (
                "Spotify album data "
                "could not be loaded."
            )
        )

        self.status_label.setText(
            safe_message
        )

        if not self._track_rows:
            self.empty_label.setText(
                "Album unavailable."
            )

    def apply_theme(
        self,
        theme: dict,
    ) -> None:
        background = _theme_value(
            theme,
            "background",
            "#101014",
        )

        card = _theme_value(
            theme,
            "card",
            "#19191f",
        )

        border = _theme_value(
            theme,
            "border",
            "#303038",
        )

        text = _theme_value(
            theme,
            "text",
            "#f5f5f7",
        )

        muted = _theme_value(
            theme,
            "muted",
            "#a0a0aa",
        )

        accent = _theme_value(
            theme,
            "accent",
            "#ff4f9a",
        )

        self.setStyleSheet(
            f"""
            QWidget#spotifyAlbumDetail {{
                background: {background};
            }}

            QLabel#spotifyAlbumArtwork {{
                color: {muted};
                background: {card};
                border: 1px solid {border};
                border-radius: 10px;
                font-weight: 800;
            }}

            QLabel#spotifyAlbumTitle {{
                color: {text};
                font-size: 24px;
                font-weight: 800;
            }}

            QLabel#spotifyAlbumArtist {{
                color: {text};
                font-size: 14px;
                font-weight: 700;
            }}

            QLabel#spotifyAlbumMetadata,
            QLabel#spotifyAlbumStatus,
            QLabel#spotifyAlbumEmpty,
            QLabel#spotifyAlbumTrackArtist,
            QLabel#spotifyAlbumTrackDuration {{
                color: {muted};
            }}

            QFrame#spotifyAlbumTrackRow {{
                background: {card};
                border: 1px solid {border};
                border-radius: 9px;
            }}

            QFrame#spotifyAlbumTrackRow:hover {{
                border-color: {accent};
            }}

            QLabel#spotifyAlbumTrackNumber,
            QLabel#spotifyAlbumTrackTitle {{
                color: {text};
            }}

            QLabel#spotifyAlbumTrackTitle {{
                font-weight: 700;
            }}

            QLabel#spotifyAlbumExplicitBadge {{
                color: {text};
                background: {border};
                border-radius: 3px;
                padding: 1px 4px;
                font-size: 9px;
                font-weight: 800;
            }}

            QPushButton#spotifyAlbumBackButton,
            QPushButton#spotifyAlbumLoadMore {{
                color: {text};
                background: {card};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 7px 12px;
                font-weight: 700;
            }}

            QPushButton#spotifyAlbumBackButton:hover,
            QPushButton#spotifyAlbumLoadMore:hover {{
                border-color: {accent};
            }}

            QScrollArea#spotifyAlbumTrackScroll {{
                background: transparent;
                border: none;
            }}

            QWidget#spotifyAlbumTrackContainer {{
                background: transparent;
            }}
            """
        )
