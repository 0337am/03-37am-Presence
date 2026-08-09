from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.spotify.playlist_models import (
    SpotifyPlaylistPage,
    SpotifyPlaylistSummary,
)
from src.spotify.qt_playlist_runtime import (
    SpotifyQtPlaylistRuntimeError,
)
from src.ui.spotify_artwork import (
    SpotifyArtworkLoader,
)
from src.ui.theme import ThemeManager


SPOTIFY_PLAYLIST_HOME_LIMIT = 50


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

    return (
        checked
        or fallback
    )


class SpotifyPlaylistRow(
    QFrame
):
    def __init__(
        self,
        playlist: SpotifyPlaylistSummary,
        *,
        artwork_loader=None,
        parent=None,
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

        super().__init__(
            parent
        )

        self.playlist = playlist
        self.artwork_loader = (
            artwork_loader
        )

        self.setObjectName(
            "spotifyPlaylistRow"
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
            10,
            12,
            10,
        )

        root.setSpacing(
            12
        )

        self.artwork_label = QLabel(
            "♫"
        )

        self.artwork_label.setObjectName(
            "spotifyPlaylistArtwork"
        )

        self.artwork_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.artwork_label.setFixedSize(
            58,
            58,
        )

        text_layout = QVBoxLayout()

        text_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        text_layout.setSpacing(
            3
        )

        self.name_label = QLabel(
            playlist.name
        )

        self.name_label.setObjectName(
            "spotifyPlaylistName"
        )

        self.name_label.setWordWrap(
            True
        )

        owner = (
            playlist.owner_name.strip()
            if playlist.owner_name
            else ""
        )

        if owner:
            owner_text = (
                "By "
                + owner
            )
        else:
            owner_text = (
                "Spotify playlist"
            )

        self.owner_label = QLabel(
            owner_text
        )

        self.owner_label.setObjectName(
            "spotifyPlaylistOwner"
        )

        self.owner_label.setWordWrap(
            True
        )

        item_word = (
            "item"
            if playlist.total_items == 1
            else "items"
        )

        self.count_label = QLabel(
            (
                str(
                    playlist.total_items
                )
                + " "
                + item_word
            )
        )

        self.count_label.setObjectName(
            "spotifyPlaylistItemCount"
        )

        text_layout.addWidget(
            self.name_label
        )

        text_layout.addWidget(
            self.owner_label
        )

        text_layout.addWidget(
            self.count_label
        )

        root.addWidget(
            self.artwork_label
        )

        root.addLayout(
            text_layout,
            stretch=1,
        )

        self._request_artwork()

    def _request_artwork(
        self,
    ) -> None:
        reference = (
            self.playlist
            .artwork_reference
            .strip()
            if self.playlist.artwork_reference
            else ""
        )

        if (
            not reference
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

        if not callable(
            request
        ):
            return

        try:
            if ready is not None:
                ready.connect(
                    self._handle_artwork_ready
                )

            if failed is not None:
                failed.connect(
                    self._handle_artwork_failed
                )

            request(
                reference
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
            != self.playlist.artwork_reference
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
            != self.playlist.artwork_reference
        ):
            return


class SpotifyPlaylistHome(
    QWidget
):
    def __init__(
        self,
        runtime,
        *,
        liked_songs_runtime=None,
        theme_manager=None,
        artwork_loader=None,
        parent=None,
    ) -> None:
        load_playlists = getattr(
            runtime,
            "load_playlists",
            None,
        )

        if not callable(
            load_playlists
        ):
            raise TypeError(
                (
                    "runtime must provide a callable "
                    "load_playlists method"
                )
            )

        super().__init__(
            parent
        )

        self.runtime = runtime

        if liked_songs_runtime is not None:
            load_summary = getattr(
                liked_songs_runtime,
                "load_summary",
                None,
            )

            if not callable(
                load_summary
            ):
                raise TypeError(
                    (
                        "liked_songs_runtime must "
                        "provide a callable "
                        "load_summary method"
                    )
                )

        self.liked_songs_runtime = (
            liked_songs_runtime
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

        self._rows = []
        self._last_result = None
        self._loaded = False
        self._auto_load_attempted = False

        self._playlist_busy = False
        self._liked_songs_busy = False
        self._liked_songs_loaded = False
        self._liked_songs_auto_load_attempted = False
        self._liked_songs_pending = False
        self._liked_songs_force_pending = False
        self._liked_songs_last_result = None

        self.setObjectName(
            "spotifyPlaylistHomeRoot"
        )

        self.build_ui()
        self._install_liked_songs_card()
        self.connect_signals()
        self._connect_liked_songs_signals()

        self.theme_manager.theme_changed.connect(
            self.apply_theme
        )

        self.theme_manager.theme_changed.connect(
            self._apply_liked_songs_theme
        )

        theme = self.theme_manager.theme()

        self.apply_theme(
            theme
        )

        self._apply_liked_songs_theme(
            theme
        )

    @property
    def rows(
        self,
    ) -> tuple[
        SpotifyPlaylistRow,
        ...,
    ]:
        return tuple(
            self._rows
        )

    @property
    def loaded(
        self,
    ) -> bool:
        return self._loaded

    @property
    def last_result(
        self,
    ):
        return self._last_result

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

        self.title_label = QLabel(
            "Your Playlists"
        )

        self.title_label.setObjectName(
            "spotifyPlaylistHomeTitle"
        )

        self.subtitle_label = QLabel(
            (
                "Playlists available through your "
                "connected Spotify account."
            )
        )

        self.subtitle_label.setObjectName(
            "spotifyPlaylistHomeSubtitle"
        )

        self.subtitle_label.setWordWrap(
            True
        )

        heading_group.addWidget(
            self.title_label
        )

        heading_group.addWidget(
            self.subtitle_label
        )

        self.count_badge = QLabel(
            "0"
        )

        self.count_badge.setObjectName(
            "spotifyPlaylistHomeBadge"
        )

        self.count_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.refresh_button = QPushButton(
            "Refresh"
        )

        self.refresh_button.setObjectName(
            "spotifyPlaylistRefreshButton"
        )

        self.refresh_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        header.addLayout(
            heading_group
        )

        header.addStretch()

        header.addWidget(
            self.count_badge,
            alignment=(
                Qt.AlignmentFlag
                .AlignVCenter
            ),
        )

        header.addWidget(
            self.refresh_button,
            alignment=(
                Qt.AlignmentFlag
                .AlignVCenter
            ),
        )

        root.addLayout(
            header
        )

        self.status_label = QLabel(
            (
                "Your playlists will load when "
                "Spotify Home is opened."
            )
        )

        self.status_label.setObjectName(
            "spotifyPlaylistStatus"
        )

        self.status_label.setWordWrap(
            True
        )

        root.addWidget(
            self.status_label
        )

        self.scroll = QScrollArea()

        self.scroll.setObjectName(
            "spotifyPlaylistScroll"
        )

        self.scroll.setWidgetResizable(
            True
        )

        self.scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.list_container = QWidget()

        self.list_container.setObjectName(
            "spotifyPlaylistList"
        )

        self.list_layout = QVBoxLayout(
            self.list_container
        )

        self.list_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.list_layout.setSpacing(
            8
        )

        self.empty_label = QLabel(
            (
                "No playlists to show yet."
            )
        )

        self.empty_label.setObjectName(
            "spotifyPlaylistEmpty"
        )

        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.empty_label.setWordWrap(
            True
        )

        self.list_layout.addWidget(
            self.empty_label
        )

        self.list_layout.addStretch()

        self.scroll.setWidget(
            self.list_container
        )

        root.addWidget(
            self.scroll,
            stretch=1,
        )

    def connect_signals(
        self,
    ) -> None:
        self.refresh_button.clicked.connect(
            self.refresh
        )

        playlists_ready = getattr(
            self.runtime,
            "playlists_ready",
            None,
        )

        failed = getattr(
            self.runtime,
            "failed",
            None,
        )

        busy_changed = getattr(
            self.runtime,
            "busy_changed",
            None,
        )

        if playlists_ready is not None:
            playlists_ready.connect(
                self.handle_playlists_ready
            )

        if failed is not None:
            failed.connect(
                self.handle_runtime_failure
            )

        if busy_changed is not None:
            busy_changed.connect(
                self.handle_busy_changed
            )

    def _install_liked_songs_card(
        self,
    ) -> None:
        self.liked_songs_card = QFrame()

        self.liked_songs_card.setObjectName(
            "spotifyLikedSongsCard"
        )

        self.liked_songs_card.setVisible(
            self.liked_songs_runtime
            is not None
        )

        layout = QHBoxLayout(
            self.liked_songs_card
        )

        layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )

        layout.setSpacing(
            12
        )

        self.liked_songs_icon = QLabel(
            "♥"
        )

        self.liked_songs_icon.setObjectName(
            "spotifyLikedSongsIcon"
        )

        self.liked_songs_icon.setFixedSize(
            58,
            58,
        )

        self.liked_songs_icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        text_group = QVBoxLayout()

        text_group.setSpacing(
            2
        )

        self.liked_songs_title = QLabel(
            "Liked Songs"
        )

        self.liked_songs_title.setObjectName(
            "spotifyLikedSongsTitle"
        )

        self.liked_songs_status = QLabel(
            "Your saved Spotify tracks."
        )

        self.liked_songs_status.setObjectName(
            "spotifyLikedSongsStatus"
        )

        self.liked_songs_status.setWordWrap(
            True
        )

        text_group.addWidget(
            self.liked_songs_title
        )

        text_group.addWidget(
            self.liked_songs_status
        )

        self.liked_songs_count = QLabel(
            "Not loaded"
        )

        self.liked_songs_count.setObjectName(
            "spotifyLikedSongsCount"
        )

        self.liked_songs_count.setAlignment(
            (
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )
        )

        layout.addWidget(
            self.liked_songs_icon
        )

        layout.addLayout(
            text_group,
            stretch=1,
        )

        layout.addWidget(
            self.liked_songs_count
        )

        root = self.layout()

        if root is None:
            raise RuntimeError(
                (
                    "Spotify playlist Home layout "
                    "is unavailable."
                )
            )

        root.insertWidget(
            0,
            self.liked_songs_card,
        )

    def _apply_liked_songs_theme(
        self,
        theme,
    ) -> None:
        if not isinstance(
            theme,
            dict,
        ):
            return

        card = str(
            theme.get(
                "card_alt",
                theme.get(
                    "card",
                    "#18181f",
                ),
            )
        )

        inner = str(
            theme.get(
                "card",
                "#18181f",
            )
        )

        border = str(
            theme.get(
                "border",
                "#34343e",
            )
        )

        accent = str(
            theme.get(
                "accent",
                "#ff4f91",
            )
        )

        text = str(
            theme.get(
                "text",
                "#f4f4f6",
            )
        )

        muted = str(
            theme.get(
                "muted",
                "#a6a6b1",
            )
        )

        self.liked_songs_card.setStyleSheet(
            (
                "QFrame#spotifyLikedSongsCard {"
                "background: "
                + card
                + "; border: 1px solid "
                + border
                + "; border-radius: 12px;"
                "}"
            )
        )

        self.liked_songs_icon.setStyleSheet(
            (
                "QLabel {"
                "color: "
                + accent
                + "; background: "
                + inner
                + "; border: 1px solid "
                + accent
                + "; border-radius: 8px;"
                "font-size: 24px;"
                "font-weight: 900;"
                "}"
            )
        )

        self.liked_songs_title.setStyleSheet(
            (
                "color: "
                + text
                + "; font-size: 13px;"
                "font-weight: 800;"
            )
        )

        self.liked_songs_status.setStyleSheet(
            (
                "color: "
                + muted
                + "; font-size: 10px;"
            )
        )

        self.liked_songs_count.setStyleSheet(
            (
                "color: "
                + accent
                + "; font-size: 11px;"
                "font-weight: 800;"
                "padding-left: 12px;"
            )
        )

    def _connect_liked_songs_signals(
        self,
    ) -> None:
        runtime = self.liked_songs_runtime

        if runtime is None:
            return

        runtime.summary_ready.connect(
            self.handle_liked_songs_ready
        )

        runtime.failed.connect(
            self.handle_liked_songs_failure
        )

        runtime.busy_changed.connect(
            self.handle_liked_songs_busy_changed
        )

    def _liked_songs_needs_load(
        self,
    ) -> bool:
        return (
            self.liked_songs_runtime
            is not None
            and not self._liked_songs_loaded
            and not self._liked_songs_auto_load_attempted
        )

    def _request_liked_songs(
        self,
    ) -> bool:
        runtime = self.liked_songs_runtime

        if runtime is None:
            return False

        if bool(
            getattr(
                runtime,
                "busy",
                False,
            )
        ):
            return False

        self.liked_songs_count.setText(
            "Loading..."
        )

        self.liked_songs_status.setText(
            "Loading your saved Spotify tracks..."
        )

        try:
            runtime.load_summary()

        except Exception as error:
            message = str(
                getattr(
                    error,
                    "message",
                    "",
                )
                or ""
            ).strip()

            self.liked_songs_count.setText(
                "Unavailable"
            )

            self.liked_songs_status.setText(
                message
                or (
                    "Liked Songs could not "
                    "be loaded."
                )
            )

            return False

        return True

    def _ensure_liked_songs_loaded(
        self,
    ) -> bool:
        if not self._liked_songs_needs_load():
            return False

        if self._playlist_busy:
            self._liked_songs_pending = True
            return False

        self._liked_songs_auto_load_attempted = True
        self._liked_songs_pending = False

        return self._request_liked_songs()

    def _drain_liked_songs_pending(
        self,
    ) -> bool:
        if self._playlist_busy:
            return False

        if self._liked_songs_force_pending:
            self._liked_songs_force_pending = False
            self._liked_songs_pending = False

            return self._request_liked_songs()

        if self._liked_songs_pending:
            self._liked_songs_pending = False

            return self._ensure_liked_songs_loaded()

        return False

    def ensure_loaded(
        self,
    ) -> bool:
        playlist_started = False

        if (
            not self._loaded
            and not self._auto_load_attempted
        ):
            self._auto_load_attempted = True

            if self._liked_songs_needs_load():
                self._liked_songs_pending = True

            playlist_started = (
                self._request_playlists()
            )

        if playlist_started:
            return True

        liked_started = (
            self._ensure_liked_songs_loaded()
        )

        return bool(
            playlist_started
            or liked_started
        )

    def refresh(
        self,
    ) -> bool:
        if self.liked_songs_runtime is not None:
            self._liked_songs_force_pending = True

        playlist_started = (
            self._request_playlists()
        )

        if playlist_started:
            return True

        liked_started = (
            self._drain_liked_songs_pending()
        )

        return bool(
            playlist_started
            or liked_started
        )

    def _request_playlists(
        self,
    ) -> bool:
        if bool(
            getattr(
                self.runtime,
                "busy",
                False,
            )
        ):
            self.status_label.setText(
                (
                    "Spotify is already loading "
                    "playlist information."
                )
            )

            return False

        self.status_label.setText(
            "Loading your Spotify playlists..."
        )

        try:
            self.runtime.load_playlists(
                limit=(
                    SPOTIFY_PLAYLIST_HOME_LIMIT
                ),
                offset=0,
            )

        except SpotifyQtPlaylistRuntimeError as error:
            self.status_label.setText(
                error.message
                or (
                    "Spotify playlists could "
                    "not be loaded."
                )
            )

            return False

        except (
            TypeError,
            ValueError,
        ):
            self.status_label.setText(
                (
                    "The Spotify playlist request "
                    "is invalid."
                )
            )

            return False

        except Exception:
            self.status_label.setText(
                (
                    "Spotify playlists could "
                    "not be loaded."
                )
            )

            return False

        return True

    def clear_playlists(
        self,
    ) -> None:
        for row in self._rows:
            self.list_layout.removeWidget(
                row
            )

            row.deleteLater()

        self._rows.clear()

        self.count_badge.setText(
            "0"
        )

        self.empty_label.setVisible(
            True
        )

    def set_playlist_page(
        self,
        page: SpotifyPlaylistPage,
    ) -> None:
        if not isinstance(
            page,
            SpotifyPlaylistPage,
        ):
            raise TypeError(
                (
                    "page must be a "
                    "SpotifyPlaylistPage"
                )
            )

        self.clear_playlists()

        for playlist in page.playlists:
            row = SpotifyPlaylistRow(
                playlist,
                artwork_loader=(
                    self.artwork_loader
                ),
                parent=(
                    self.list_container
                ),
            )

            self._rows.append(
                row
            )

            insert_at = max(
                0,
                self.list_layout.count()
                - 1,
            )

            self.list_layout.insertWidget(
                insert_at,
                row,
            )

        self.count_badge.setText(
            str(
                page.total
            )
        )

        self.empty_label.setVisible(
            not bool(
                self._rows
            )
        )

        if not self._rows:
            self.empty_label.setText(
                (
                    "No Spotify playlists were "
                    "returned for this account."
                )
            )

        shown = len(
            self._rows
        )

        if page.total > shown:
            self.status_label.setText(
                (
                    "Showing "
                    + str(
                        shown
                    )
                    + " of "
                    + str(
                        page.total
                    )
                    + " playlists."
                )
            )

        else:
            self.status_label.setText(
                (
                    str(
                        shown
                    )
                    + (
                        " playlist loaded."
                        if shown == 1
                        else " playlists loaded."
                    )
                )
            )

    def handle_playlists_ready(
        self,
        result,
    ) -> None:
        self._last_result = result

        ready = bool(
            getattr(
                result,
                "ready",
                False,
            )
        )

        page = getattr(
            result,
            "playlists_page",
            None,
        )

        if (
            ready
            and isinstance(
                page,
                SpotifyPlaylistPage,
            )
        ):
            self.set_playlist_page(
                page
            )

            self._loaded = True

            return

        self._loaded = False

        message = getattr(
            result,
            "message",
            "",
        )

        if (
            isinstance(
                message,
                str,
            )
            and message.strip()
        ):
            safe_message = (
                message.strip()
            )

        else:
            safe_message = (
                "Spotify playlists could not "
                "be loaded."
            )

        self.status_label.setText(
            safe_message
        )

    def handle_runtime_failure(
        self,
        *args,
    ) -> None:
        if args:
            operation = str(
                args[0]
                or ""
            ).strip()

            if (
                operation
                and operation
                != "playlists"
            ):
                return

        message = ""

        for value in reversed(
            args
        ):
            if (
                isinstance(
                    value,
                    str,
                )
                and value.strip()
                and value.strip()
                != "playlists"
            ):
                message = (
                    value.strip()
                )

                break

        self.status_label.setText(
            message
            or (
                "Spotify playlists could "
                "not be loaded."
            )
        )

    def _update_refresh_state(
        self,
    ) -> None:
        is_busy = bool(
            self._playlist_busy
            or self._liked_songs_busy
        )

        self.refresh_button.setEnabled(
            not is_busy
        )

        self.refresh_button.setText(
            (
                "Loading..."
                if is_busy
                else "Refresh"
            )
        )

    def handle_busy_changed(
        self,
        busy,
    ) -> None:
        self._playlist_busy = bool(
            busy
        )

        self._update_refresh_state()

        if not self._playlist_busy:
            self._drain_liked_songs_pending()

    def handle_liked_songs_ready(
        self,
        result,
    ) -> None:
        self._liked_songs_last_result = (
            result
        )

        ready = bool(
            getattr(
                result,
                "ready",
                False,
            )
        )

        total = getattr(
            result,
            "total",
            None,
        )

        if (
            ready
            and isinstance(
                total,
                int,
            )
            and not isinstance(
                total,
                bool,
            )
            and total >= 0
        ):
            self._liked_songs_loaded = True

            word = (
                "song"
                if total == 1
                else "songs"
            )

            self.liked_songs_count.setText(
                str(total)
                + " "
                + word
            )

            self.liked_songs_status.setText(
                "Your saved Spotify tracks."
            )

            return

        self._liked_songs_loaded = False

        message = getattr(
            result,
            "message",
            "",
        )

        if not isinstance(
            message,
            str,
        ):
            message = ""

        self.liked_songs_count.setText(
            "Unavailable"
        )

        self.liked_songs_status.setText(
            message.strip()
            or (
                "Liked Songs could not "
                "be loaded."
            )
        )

    def handle_liked_songs_failure(
        self,
        error_code,
        message,
    ) -> None:
        self._liked_songs_loaded = False

        safe_message = str(
            message
            or ""
        ).strip()

        self.liked_songs_count.setText(
            "Unavailable"
        )

        self.liked_songs_status.setText(
            safe_message
            or (
                "Liked Songs could not "
                "be loaded."
            )
        )

    def handle_liked_songs_busy_changed(
        self,
        busy,
    ) -> None:
        self._liked_songs_busy = bool(
            busy
        )

        self._update_refresh_state()

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
            QWidget#spotifyPlaylistHomeRoot {{
                background: {background};
                color: {text};
            }}

            QLabel#spotifyPlaylistHomeTitle {{
                color: {text};
                font-size: 22px;
                font-weight: 800;
            }}

            QLabel#spotifyPlaylistHomeSubtitle,
            QLabel#spotifyPlaylistStatus,
            QLabel#spotifyPlaylistOwner,
            QLabel#spotifyPlaylistItemCount,
            QLabel#spotifyPlaylistEmpty {{
                color: {muted};
            }}

            QLabel#spotifyPlaylistHomeSubtitle,
            QLabel#spotifyPlaylistStatus {{
                font-size: 10px;
            }}

            QLabel#spotifyPlaylistHomeBadge {{
                color: {accent};
                background: {card};
                border: 1px solid {accent};
                border-radius: 9px;
                padding: 4px 9px;
                font-size: 9px;
                font-weight: 800;
            }}

            QPushButton#spotifyPlaylistRefreshButton {{
                color: {text};
                background: {card};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 7px 12px;
                font-weight: 700;
            }}

            QPushButton#spotifyPlaylistRefreshButton:hover {{
                border: 1px solid {accent};
                background: {card_alt};
            }}

            QPushButton#spotifyPlaylistRefreshButton:disabled {{
                color: {muted};
            }}

            QScrollArea#spotifyPlaylistScroll {{
                background: transparent;
                border: none;
            }}

            QWidget#spotifyPlaylistList {{
                background: transparent;
            }}

            QFrame#spotifyPlaylistRow {{
                background: {card};
                border: 1px solid {border};
                border-radius: 11px;
            }}

            QLabel#spotifyPlaylistArtwork {{
                color: {accent};
                background: {card_alt};
                border: 1px solid {border};
                border-radius: 8px;
                font-size: 20px;
                font-weight: 800;
            }}

            QLabel#spotifyPlaylistName {{
                color: {text};
                font-size: 12px;
                font-weight: 800;
            }}

            QLabel#spotifyPlaylistOwner {{
                font-size: 10px;
            }}

            QLabel#spotifyPlaylistItemCount {{
                font-size: 9px;
            }}

            QLabel#spotifyPlaylistEmpty {{
                padding: 28px;
                font-size: 11px;
            }}
            """
        )
