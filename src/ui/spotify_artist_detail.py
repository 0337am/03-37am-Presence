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
    SpotifyAlbumSummary,
)
from src.spotify.artist_service import (
    SpotifyArtistServiceResult,
    _validate_artist_id,
)
from src.spotify.qt_artist_runtime import (
    OPERATION_ARTIST,
    OPERATION_ARTIST_ALBUMS,
)
from src.ui.spotify_artwork import (
    SpotifyArtworkLoader,
)
from src.ui.theme import (
    ThemeManager,
)


SPOTIFY_ARTIST_DETAIL_LIMIT = 10


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


def _album_metadata(
    album: SpotifyAlbumSummary,
) -> str:
    parts = []

    album_type = str(
        album.album_type
        or ""
    ).strip()

    if album_type:
        parts.append(
            album_type.replace(
                "_",
                " ",
            ).title()
        )

    release_date = str(
        album.release_date
        or ""
    ).strip()

    if release_date:
        parts.append(
            release_date
        )

    total_tracks = int(
        album.total_tracks
    )

    if total_tracks == 1:
        parts.append(
            "1 track"
        )

    elif total_tracks > 1:
        parts.append(
            f"{total_tracks} tracks"
        )

    return " | ".join(
        parts
    )


class SpotifyArtistAlbumRow(
    QFrame
):
    activated = pyqtSignal(
        object
    )

    def __init__(
        self,
        album: SpotifyAlbumSummary,
        *,
        parent=None,
    ) -> None:
        if not isinstance(
            album,
            SpotifyAlbumSummary,
        ):
            raise TypeError(
                (
                    "album must be a "
                    "SpotifyAlbumSummary"
                )
            )

        super().__init__(
            parent
        )

        self.album = album

        self.setObjectName(
            "spotifyArtistAlbumRow"
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            12,
            9,
            12,
            9,
        )

        layout.setSpacing(
            3
        )

        self.title_label = QLabel(
            album.name,
            self,
        )

        self.title_label.setObjectName(
            "spotifyArtistAlbumTitle"
        )

        self.title_label.setWordWrap(
            True
        )

        self.artist_label = QLabel(
            album.artist_text,
            self,
        )

        self.artist_label.setObjectName(
            "spotifyArtistAlbumArtist"
        )

        self.artist_label.setWordWrap(
            True
        )

        self.metadata_label = QLabel(
            _album_metadata(
                album
            ),
            self,
        )

        self.metadata_label.setObjectName(
            "spotifyArtistAlbumMetadata"
        )

        self.metadata_label.setWordWrap(
            True
        )

        layout.addWidget(
            self.title_label
        )

        if album.artist_text:
            layout.addWidget(
                self.artist_label
            )

        layout.addWidget(
            self.metadata_label
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        for label in (
            self.title_label,
            self.artist_label,
            self.metadata_label,
        ):
            label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )

    def activate(
        self,
    ) -> bool:
        self.activated.emit(
            self.album
        )

        return True

    def mousePressEvent(
        self,
        event,
    ) -> None:
        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self.activate()

        super().mousePressEvent(
            event
        )


class SpotifyArtistDetail(
    QWidget
):
    album_activated = pyqtSignal(
        object
    )

    back_requested = pyqtSignal()

    def __init__(
        self,
        artist_runtime,
        *,
        theme_manager=None,
        artwork_loader=None,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        load_artist = getattr(
            artist_runtime,
            "load_artist",
            None,
        )

        load_artist_albums = getattr(
            artist_runtime,
            "load_artist_albums",
            None,
        )

        if not callable(
            load_artist
        ):
            raise TypeError(
                (
                    "artist_runtime must provide "
                    "a callable load_artist method"
                )
            )

        if not callable(
            load_artist_albums
        ):
            raise TypeError(
                (
                    "artist_runtime must provide "
                    "a callable load_artist_albums "
                    "method"
                )
            )

        self.artist_runtime = (
            artist_runtime
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

        self._artist_id = ""
        self._artist = None
        self._artwork_reference = ""

        self._album_rows = []
        self._loaded_count = 0
        self._total_albums = 0

        self._pending_initial_albums = False

        self.setObjectName(
            "spotifyArtistDetail"
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

    @property
    def artist_id(
        self,
    ) -> str:
        return self._artist_id

    @property
    def album_rows(
        self,
    ) -> tuple:
        return tuple(
            self._album_rows
        )

    @property
    def loaded_count(
        self,
    ) -> int:
        return self._loaded_count

    @property
    def total_albums(
        self,
    ) -> int:
        return self._total_albums

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
            "spotifyArtistBackButton"
        )

        self.back_button.clicked.connect(
            self.back_requested.emit
        )

        self.artwork_label = QLabel(
            "Artist",
            self,
        )

        self.artwork_label.setObjectName(
            "spotifyArtistArtwork"
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
            "Artist",
            self,
        )

        self.title_label.setObjectName(
            "spotifyArtistTitle"
        )

        self.title_label.setWordWrap(
            True
        )

        self.metadata_label = QLabel(
            "Artist",
            self,
        )

        self.metadata_label.setObjectName(
            "spotifyArtistMetadata"
        )

        self.metadata_label.setWordWrap(
            True
        )

        self.status_label = QLabel(
            "",
            self,
        )

        self.status_label.setObjectName(
            "spotifyArtistStatus"
        )

        self.status_label.setWordWrap(
            True
        )

        heading.addWidget(
            self.title_label
        )

        heading.addWidget(
            self.metadata_label
        )

        heading.addWidget(
            self.status_label
        )

        heading.addStretch(
            1
        )

        header.addWidget(
            self.back_button,
            0,
            Qt.AlignmentFlag.AlignTop,
        )

        header.addWidget(
            self.artwork_label,
            0,
            Qt.AlignmentFlag.AlignTop,
        )

        header.addLayout(
            heading,
            1,
        )

        root.addLayout(
            header
        )

        self.scroll_area = QScrollArea(
            self
        )

        self.scroll_area.setObjectName(
            "spotifyArtistAlbumScroll"
        )

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.album_container = QWidget(
            self.scroll_area
        )

        self.album_container.setObjectName(
            "spotifyArtistAlbumContainer"
        )

        self.album_layout = QVBoxLayout(
            self.album_container
        )

        self.album_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.album_layout.setSpacing(
            8
        )

        self.empty_label = QLabel(
            "Artist releases have not been loaded yet.",
            self.album_container,
        )

        self.empty_label.setObjectName(
            "spotifyArtistEmpty"
        )

        self.empty_label.setWordWrap(
            True
        )

        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.album_layout.addWidget(
            self.empty_label
        )

        self.album_layout.addStretch(
            1
        )

        self.scroll_area.setWidget(
            self.album_container
        )

        root.addWidget(
            self.scroll_area,
            1,
        )

        self.load_more_button = QPushButton(
            "Load more",
            self,
        )

        self.load_more_button.setObjectName(
            "spotifyArtistLoadMore"
        )

        self.load_more_button.setVisible(
            False
        )

        self.load_more_button.clicked.connect(
            self.load_more
        )

        root.addWidget(
            self.load_more_button,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

    def _connect_runtime(
        self,
    ) -> None:
        artist_ready = getattr(
            self.artist_runtime,
            "artist_ready",
            None,
        )

        albums_ready = getattr(
            self.artist_runtime,
            "artist_albums_ready",
            None,
        )

        failed = getattr(
            self.artist_runtime,
            "failed",
            None,
        )

        operation_finished = getattr(
            self.artist_runtime,
            "operation_finished",
            None,
        )

        if artist_ready is not None:
            artist_ready.connect(
                self.handle_artist_ready
            )

        if albums_ready is not None:
            albums_ready.connect(
                self.handle_artist_albums_ready
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
                "Artist"
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

    def set_artist_id(
        self,
        artist_id,
        *,
        seed_name: str = "",
        seed_image_url: str = "",
    ) -> bool:
        checked_artist_id = (
            _validate_artist_id(
                artist_id
            )
        )

        if not isinstance(
            seed_name,
            str,
        ):
            raise TypeError(
                "seed_name must be text."
            )

        if not isinstance(
            seed_image_url,
            str,
        ):
            raise TypeError(
                "seed_image_url must be text."
            )

        self._artist_id = (
            checked_artist_id
        )

        self._artist = None
        self._pending_initial_albums = False

        self.title_label.setText(
            seed_name.strip()
            or "Artist"
        )

        self.metadata_label.setText(
            "Artist"
        )

        self.status_label.setText(
            ""
        )

        self._set_artwork_reference(
            seed_image_url
        )

        self._clear_albums()

        self.empty_label.setText(
            "Artist releases have not been loaded yet."
        )

        return True

    def load(
        self,
    ) -> bool:
        if not self._artist_id:
            return False

        self._clear_albums()

        self.status_label.setText(
            "Loading artist..."
        )

        self.empty_label.setText(
            "Loading artist..."
        )

        try:
            self.artist_runtime.load_artist(
                self._artist_id
            )

        except Exception:
            self._show_error(
                "Spotify artist could not be loaded."
            )

            return False

        return True

    def load_more(
        self,
    ) -> bool:
        if not self._artist_id:
            return False

        if (
            self._total_albums > 0
            and self._loaded_count
            >= self._total_albums
        ):
            self.load_more_button.setVisible(
                False
            )

            return False

        try:
            self.artist_runtime.load_artist_albums(
                self._artist_id,
                limit=(
                    SPOTIFY_ARTIST_DETAIL_LIMIT
                ),
                offset=(
                    self._loaded_count
                ),
            )

        except Exception:
            self._show_error(
                (
                    "More Spotify artist releases "
                    "could not be loaded."
                )
            )

            return False

        self.status_label.setText(
            "Loading more releases..."
        )

        return True

    def handle_artist_ready(
        self,
        artist_id: str,
        result,
    ) -> None:
        if (
            artist_id
            != self._artist_id
        ):
            return

        if not isinstance(
            result,
            SpotifyArtistServiceResult,
        ):
            self._show_error(
                "Spotify returned invalid artist data."
            )

            return

        if (
            not result.ready
            or result.artist is None
        ):
            self._show_error(
                result.message
                or "Spotify artist could not be loaded."
            )

            return

        artist = result.artist

        if (
            artist.spotify_id
            != self._artist_id
        ):
            return

        self._artist = artist

        self.title_label.setText(
            artist.name
        )

        self.metadata_label.setText(
            "Artist"
        )

        self._set_artwork_reference(
            artist.image_url
        )

        self.status_label.setText(
            "Artist loaded. Loading releases..."
        )

        self.empty_label.setText(
            "Loading releases..."
        )

        self._pending_initial_albums = True

    def handle_operation_finished(
        self,
        operation: str,
        artist_id: str,
    ) -> None:
        if (
            artist_id
            != self._artist_id
        ):
            return

        if (
            operation
            != OPERATION_ARTIST
            or not self._pending_initial_albums
        ):
            return

        self._pending_initial_albums = False

        try:
            self.artist_runtime.load_artist_albums(
                self._artist_id,
                limit=(
                    SPOTIFY_ARTIST_DETAIL_LIMIT
                ),
                offset=0,
            )

        except Exception:
            self._show_error(
                (
                    "Spotify artist releases "
                    "could not be loaded."
                )
            )

    def handle_artist_albums_ready(
        self,
        artist_id: str,
        result,
    ) -> None:
        if (
            artist_id
            != self._artist_id
        ):
            return

        if not isinstance(
            result,
            SpotifyArtistServiceResult,
        ):
            self._show_error(
                (
                    "Spotify returned invalid "
                    "artist release data."
                )
            )

            return

        if (
            not result.ready
            or result.albums_page is None
        ):
            self._show_error(
                result.message
                or (
                    "Spotify artist releases "
                    "could not be loaded."
                )
            )

            return

        page = result.albums_page

        if page.offset == 0:
            self._clear_albums()

        for album in page.items:
            self._append_album(
                album
            )

        self._loaded_count = max(
            self._loaded_count,
            (
                page.offset
                + len(
                    page.items
                )
            ),
        )

        self._total_albums = (
            page.total
        )

        if not self._album_rows:
            self.empty_label.setText(
                "No artist releases were returned."
            )

            self.empty_label.setVisible(
                True
            )

        else:
            self.empty_label.setVisible(
                False
            )

        complete = (
            page.complete
            or self._loaded_count
            >= self._total_albums
        )

        self.load_more_button.setVisible(
            not complete
        )

        if self._total_albums == 1:
            self.status_label.setText(
                "1 release loaded."
            )

        else:
            self.status_label.setText(
                (
                    f"{self._loaded_count} of "
                    f"{self._total_albums} "
                    "releases loaded."
                )
            )

    def handle_runtime_failure(
        self,
        operation: str,
        artist_id: str,
        error_code: str,
        message: str,
    ) -> None:
        if (
            artist_id
            != self._artist_id
        ):
            return

        if operation not in {
            OPERATION_ARTIST,
            OPERATION_ARTIST_ALBUMS,
        }:
            return

        self._show_error(
            message
            or "Spotify artist data could not be loaded."
        )

    def _append_album(
        self,
        album,
    ) -> None:
        if not isinstance(
            album,
            SpotifyAlbumSummary,
        ):
            return

        row = SpotifyArtistAlbumRow(
            album,
            parent=self.album_container,
        )

        row.activated.connect(
            self.album_activated.emit
        )

        insert_index = max(
            0,
            self.album_layout.count() - 1,
        )

        self.album_layout.insertWidget(
            insert_index,
            row,
        )

        self._album_rows.append(
            row
        )

    def _clear_albums(
        self,
    ) -> None:
        for row in self._album_rows:
            self.album_layout.removeWidget(
                row
            )

            row.deleteLater()

        self._album_rows = []

        self._loaded_count = 0
        self._total_albums = 0

        self.load_more_button.setVisible(
            False
        )

        self.empty_label.setVisible(
            True
        )

    def _show_error(
        self,
        message: str,
    ) -> None:
        checked = str(
            message
            or "Spotify artist data could not be loaded."
        ).strip()

        self.status_label.setText(
            checked
        )

        if not self._album_rows:
            self.empty_label.setText(
                checked
            )

            self.empty_label.setVisible(
                True
            )

        self.load_more_button.setVisible(
            False
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
            QWidget#spotifyArtistDetail {{
                background: {background};
            }}

            QLabel#spotifyArtistArtwork {{
                color: {muted};
                background: {card};
                border: 1px solid {border};
                border-radius: 10px;
                font-weight: 800;
            }}

            QLabel#spotifyArtistTitle {{
                color: {text};
                font-size: 24px;
                font-weight: 800;
            }}

            QLabel#spotifyArtistMetadata,
            QLabel#spotifyArtistStatus,
            QLabel#spotifyArtistEmpty,
            QLabel#spotifyArtistAlbumArtist,
            QLabel#spotifyArtistAlbumMetadata {{
                color: {muted};
            }}

            QFrame#spotifyArtistAlbumRow {{
                background: {card};
                border: 1px solid {border};
                border-radius: 9px;
            }}

            QLabel#spotifyArtistAlbumTitle {{
                color: {text};
                font-weight: 700;
            }}

            QPushButton#spotifyArtistBackButton,
            QPushButton#spotifyArtistLoadMore {{
                color: {text};
                background: {card};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 7px 12px;
                font-weight: 700;
            }}

            QPushButton#spotifyArtistBackButton:hover,
            QPushButton#spotifyArtistLoadMore:hover {{
                border-color: {accent};
            }}

            QScrollArea#spotifyArtistAlbumScroll {{
                background: transparent;
                border: none;
            }}

            QWidget#spotifyArtistAlbumContainer {{
                background: transparent;
            }}
            """
        )
