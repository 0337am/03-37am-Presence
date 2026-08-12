from __future__ import annotations

from src.ui.spotify_playlist_widgets import (
    SpotifyPlaylistHome,
)

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.spotify_search import SpotifySearchPage
from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
)
from src.spotify.playlist_models import (
    SpotifyPlaylistSummary,
)
from src.spotify.album_models import (
    SpotifyAlbumSummary,
)
from src.ui.theme import ThemeManager
from src.ui.spotify_playlist_detail import (
    SpotifyPlaylistDetail,
)
from src.ui.spotify_liked_songs_detail import (
    SpotifyLikedSongsDetail,
)
from src.ui.spotify_album_detail import (
    SpotifyAlbumDetail,
)
from src.ui.spotify_artist_detail import (
    SpotifyArtistDetail,
)


SPOTIFY_HOME_INDEX = 0
SPOTIFY_SEARCH_INDEX = 1


def _theme_value(
    theme: dict,
    key: str,
    fallback: str,
) -> str:
    value = str(
        theme.get(
            key,
            fallback,
        )
        or fallback
    ).strip()

    return value


SPOTIFY_PLAYLIST_DETAIL_INDEX = 2
SPOTIFY_LIKED_SONGS_INDEX = 3
SPOTIFY_ALBUM_DETAIL_INDEX = 4
SPOTIFY_ARTIST_DETAIL_INDEX = 5
class SpotifyPage(
    QWidget
):
    def __init__(
        self,
        *,
        search_runtime,
        playlist_runtime,
        album_runtime=None,
        artist_runtime=None,
        playback_runtime=None,
        liked_songs_runtime=None,
        theme_manager=None,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        load_playlists = getattr(
            playlist_runtime,
            "load_playlists",
            None,
        )

        load_playlist_items = getattr(
            playlist_runtime,
            "load_playlist_items",
            None,
        )

        if not callable(
            load_playlists
        ):
            raise TypeError(
                (
                    "playlist_runtime must provide "
                    "a callable load_playlists method"
                )
            )

        if not callable(
            load_playlist_items
        ):
            raise TypeError(
                (
                    "playlist_runtime must provide "
                    "a callable load_playlist_items method"
                )
            )

        self.search_runtime = (
            search_runtime
        )

        self.playlist_runtime = (
            playlist_runtime
        )

        self.album_runtime = (
            album_runtime
        )

        self.artist_runtime = (
            artist_runtime
        )

        self.playback_runtime = (
            playback_runtime
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

        self._activated = False
        self._current_song = None

        self._playlist_detail_return_index = (
            SPOTIFY_HOME_INDEX
        )

        self._album_detail_return_index = (
            SPOTIFY_SEARCH_INDEX
        )

        self._artist_detail_return_index = (
            SPOTIFY_HOME_INDEX
        )

        self.setObjectName(
            "spotifyRoot"
        )

        self.build_ui()

        self._install_playlist_home()
        self._install_playlist_detail()
        self._install_liked_songs_detail()

        if self.album_runtime is not None:
            self._install_album_detail()

        if self.artist_runtime is not None:
            self._install_artist_detail()

        self.connect_signals()

        self.theme_manager.theme_changed.connect(
            self.apply_theme
        )

        self.apply_theme(
            self.theme_manager.theme()
        )

        self.show_home()

    @property
    def current_section(
        self,
    ) -> str:
        if (
            self.content_stack.currentIndex()
            == SPOTIFY_ARTIST_DETAIL_INDEX
        ):
            return "artist_detail"

        if (
            self.content_stack.currentIndex()
            == SPOTIFY_ALBUM_DETAIL_INDEX
        ):
            return "album_detail"

        if (
            self.content_stack.currentIndex()
            == SPOTIFY_LIKED_SONGS_INDEX
        ):
            return "liked_songs"

        if (
            self.content_stack.currentIndex()
            == SPOTIFY_PLAYLIST_DETAIL_INDEX
        ):
            return "playlist_detail"
        if (
            self.content_stack.currentIndex()
            == SPOTIFY_SEARCH_INDEX
        ):
            return "search"

        return "home"

    def build_ui(
        self,
    ) -> None:
        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        root.setSpacing(
            0
        )

        self.section_navigation = (
            QFrame()
        )

        self.section_navigation.setObjectName(
            "spotifySectionNavigation"
        )

        navigation_layout = QHBoxLayout(
            self.section_navigation
        )

        navigation_layout.setContentsMargins(
            20,
            12,
            20,
            10,
        )

        navigation_layout.setSpacing(
            8
        )

        self.home_button = QPushButton(
            "Home"
        )

        self.home_button.setObjectName(
            "spotifySectionButton"
        )

        self.home_button.setCheckable(
            True
        )

        self.home_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.search_button = QPushButton(
            "Search"
        )

        self.search_button.setObjectName(
            "spotifySectionButton"
        )

        self.search_button.setCheckable(
            True
        )

        self.search_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        navigation_layout.addWidget(
            self.home_button
        )

        navigation_layout.addWidget(
            self.search_button
        )

        navigation_layout.addStretch()

        root.addWidget(
            self.section_navigation
        )

        self.content_stack = (
            QStackedWidget()
        )

        self.content_stack.setObjectName(
            "spotifyContentStack"
        )

        self.home_page = QWidget()
        self.home_page.setObjectName(
            "spotifyHomeRoot"
        )

        home_layout = QVBoxLayout(
            self.home_page
        )

        home_layout.setContentsMargins(
            20,
            8,
            20,
            18,
        )

        home_layout.setSpacing(
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

        self.home_title = QLabel(
            "Spotify"
        )

        self.home_title.setObjectName(
            "spotifyHomeTitle"
        )

        self.home_subtitle = QLabel(
            (
                "Your music, playlists, and playback "
                "in one place."
            )
        )

        self.home_subtitle.setObjectName(
            "spotifyHomeSubtitle"
        )

        heading_group.addWidget(
            self.home_title
        )

        heading_group.addWidget(
            self.home_subtitle
        )

        self.home_badge = QLabel(
            "HOME"
        )

        self.home_badge.setObjectName(
            "spotifyHomeBadge"
        )

        self.home_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        header.addLayout(
            heading_group
        )

        header.addStretch()

        header.addWidget(
            self.home_badge,
            alignment=(
                Qt.AlignmentFlag.AlignVCenter
            ),
        )

        home_layout.addLayout(
            header
        )

        self.home_card = QFrame()
        self.home_card.setObjectName(
            "spotifyHomeCard"
        )

        self.home_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        home_card_layout = QVBoxLayout(
            self.home_card
        )

        home_card_layout.setContentsMargins(
            16,
            15,
            16,
            15,
        )

        home_card_layout.setSpacing(
            5
        )

        self.home_card_title = QLabel(
            "Your Spotify home"
        )

        self.home_card_title.setObjectName(
            "spotifyHomeCardTitle"
        )

        self.home_card_text = QLabel(
            (
                "Your playlists are ready to be "
                "connected to this view. Search is "
                "already available from the tab above."
            )
        )

        self.home_card_text.setObjectName(
            "spotifyHomeCardText"
        )

        self.home_card_text.setWordWrap(
            True
        )

        home_card_layout.addWidget(
            self.home_card_title
        )

        home_card_layout.addWidget(
            self.home_card_text
        )

        home_layout.addWidget(
            self.home_card
        )

        home_layout.addStretch()

        self.search_page = (
            SpotifySearchPage(
                self.search_runtime,
                theme_manager=(
                    self.theme_manager
                ),
                parent=self,
            )
        )

        self.content_stack.addWidget(
            self.home_page
        )

        self.content_stack.addWidget(
            self.search_page
        )

        root.addWidget(
            self.content_stack,
            stretch=1,
        )

    def connect_signals(
        self,
    ) -> None:
        self.home_button.clicked.connect(
            self.show_home
        )

        self.search_button.clicked.connect(
            self.show_search
        )

        self.search_page.track_activated.connect(
            self._handle_search_track_activated
        )

        self.search_page.playlist_activated.connect(
            self._handle_search_playlist_activated
        )

        self.search_page.album_activated.connect(
            self._handle_search_album_activated
        )

        self.search_page.artist_activated.connect(
            self._handle_search_artist_activated
        )

        self.playlist_home.playlist_activated.connect(
            self.show_playlist_detail
        )

        self.playlist_home.liked_songs_activated.connect(
            self.show_liked_songs
        )

        self.playlist_detail.back_requested.connect(
            self._show_playlist_detail_return_section
        )

        self.liked_songs_detail.back_requested.connect(
            self.show_home
        )

        album_detail = getattr(
            self,
            "album_detail",
            None,
        )

        if album_detail is not None:
            album_detail.back_requested.connect(
                self._show_album_detail_return_section
            )

        artist_detail = getattr(
            self,
            "artist_detail",
            None,
        )

        if artist_detail is not None:
            artist_detail.back_requested.connect(
                self._show_artist_detail_return_section
            )

            artist_detail.album_activated.connect(
                self._handle_artist_album_activated
            )

    def _handle_artist_album_activated(
        self,
        album,
    ) -> bool:
        if not isinstance(
            album,
            SpotifyAlbumSummary,
        ):
            return False

        if not hasattr(
            self,
            "album_detail",
        ):
            return False

        album_id = str(
            album.spotify_id
            or ""
        ).strip()

        album_uri = str(
            album.uri
            or ""
        ).strip()

        if (
            not album_id
            or album_uri
            != "spotify:album:" + album_id
        ):
            return False

        try:
            item = SpotifySearchItem(
                item_type=(
                    SpotifySearchItemType.ALBUM
                ),
                spotify_id=album_id,
                name=album.name,
                uri=album_uri,
                spotify_url=(
                    album.spotify_url
                ),
                image_url=(
                    album.image_url
                ),
                subtitle=(
                    album.artist_text
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            return False

        return bool(
            self.show_album_detail(
                item
            )
        )

    def _handle_search_artist_activated(
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
            is not SpotifySearchItemType.ARTIST
        ):
            return False

        if not hasattr(
            self,
            "artist_detail",
        ):
            return False

        artist_uri = (
            item.uri.strip()
            if isinstance(
                item.uri,
                str,
            )
            else ""
        )

        expected_uri = (
            "spotify:artist:"
            + item.spotify_id
        )

        if artist_uri != expected_uri:
            return False

        return bool(
            self.show_artist_detail(
                item.spotify_id,
                seed_name=item.name,
                seed_image_url=(
                    item.image_url
                ),
            )
        )

    def _handle_search_album_activated(
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

        if not hasattr(
            self,
            "album_detail",
        ):
            return False

        album_uri = (
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

        if album_uri != expected_uri:
            return False

        return bool(
            self.show_album_detail(
                item
            )
        )

    def _handle_search_playlist_activated(
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
            is not SpotifySearchItemType.PLAYLIST
        ):
            return False

        playlist_uri = (
            item.uri.strip()
            if isinstance(
                item.uri,
                str,
            )
            else ""
        )

        expected_uri = (
            "spotify:playlist:"
            + item.spotify_id
        )

        if playlist_uri != expected_uri:
            return False

        owner_name = (
            item.subtitle.strip()
            if isinstance(
                item.subtitle,
                str,
            )
            else ""
        )

        if owner_name.casefold() == "playlist":
            owner_name = ""

        artwork_reference = (
            item.image_url.strip()
            if isinstance(
                item.image_url,
                str,
            )
            else ""
        )

        try:
            playlist = SpotifyPlaylistSummary(
                spotify_id=item.spotify_id,
                name=item.name,
                spotify_uri=playlist_uri,
                owner_name=owner_name,
                total_items=0,
                artwork_reference=(
                    artwork_reference
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            return False

        return bool(
            self.show_playlist_detail(
                playlist
            )
        )

    def _handle_search_track_activated(
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
            is not SpotifySearchItemType.TRACK
        ):
            return False

        spotify_uri = (
            item.uri.strip()
            if isinstance(
                item.uri,
                str,
            )
            else ""
        )

        expected_uri = (
            "spotify:track:"
            + item.spotify_id
        )

        if spotify_uri != expected_uri:
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

        play_track(
            spotify_uri
        )

        return True

    def _set_section(
        self,
        index: int,
    ) -> None:
        if index in (
            SPOTIFY_PLAYLIST_DETAIL_INDEX,
            SPOTIFY_LIKED_SONGS_INDEX,
            SPOTIFY_ALBUM_DETAIL_INDEX,
            SPOTIFY_ARTIST_DETAIL_INDEX,
        ):
            self.content_stack.setCurrentIndex(
                index
            )

            self.home_button.setChecked(
                False
            )

            self.search_button.setChecked(
                False
            )

            return
        if index not in (
            SPOTIFY_HOME_INDEX,
            SPOTIFY_SEARCH_INDEX,
        ):
            index = (
                SPOTIFY_HOME_INDEX
            )

        self.content_stack.setCurrentIndex(
            index
        )

        self.home_button.setChecked(
            index
            == SPOTIFY_HOME_INDEX
        )

        self.search_button.setChecked(
            index
            == SPOTIFY_SEARCH_INDEX
        )

    def _install_playlist_home(
        self,
    ) -> None:
        previous_home = (
            self.content_stack.widget(
                SPOTIFY_HOME_INDEX
            )
        )

        current_widget = (
            self.content_stack
            .currentWidget()
        )

        search_artwork_loader = (
            getattr(
                getattr(
                    self,
                    "search_page",
                    None,
                ),
                "artwork_loader",
                None,
            )
        )

        self.playlist_home = (
            SpotifyPlaylistHome(
                self.playlist_runtime,
                liked_songs_runtime=(
                    self.liked_songs_runtime
                ),
                theme_manager=(
                    self.theme_manager
                ),
                artwork_loader=(
                    search_artwork_loader
                ),
                parent=(
                    self.content_stack
                ),
            )
        )

        if previous_home is not None:
            self.content_stack.removeWidget(
                previous_home
            )

        self.content_stack.insertWidget(
            SPOTIFY_HOME_INDEX,
            self.playlist_home,
        )

        self.home_page = (
            self.playlist_home
        )

        if (
            current_widget is None
            or current_widget
            is previous_home
        ):
            self.content_stack.setCurrentWidget(
                self.playlist_home
            )

        else:
            self.content_stack.setCurrentWidget(
                current_widget
            )

        if previous_home is not None:
            previous_home.deleteLater()


    def set_current_song(
        self,
        song,
    ) -> None:
        self._current_song = song

        for detail_name in (
            "playlist_detail",
            "liked_songs_detail",
            "album_detail",
        ):
            detail = getattr(
                self,
                detail_name,
                None,
            )

            setter = getattr(
                detail,
                "set_current_song",
                None,
            )

            if callable(
                setter
            ):
                setter(
                    song
                )

    def activate(
        self,
    ) -> bool:
        self._activated = True

        if (
            self.content_stack.currentIndex()
            != SPOTIFY_HOME_INDEX
        ):
            return False

        return bool(
            self.playlist_home.ensure_loaded()
        )

    def show_home(
        self,
    ) -> None:
        self._set_section(
            SPOTIFY_HOME_INDEX
        )

        if self._activated:
            self.playlist_home.ensure_loaded()

    def show_search(
        self,
    ) -> None:
        self._set_section(
            SPOTIFY_SEARCH_INDEX
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
            QWidget#spotifyRoot {{
                background: transparent;
                color: {text};
            }}

            QFrame#spotifySectionNavigation {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {border};
            }}

            QPushButton#spotifySectionButton {{
                color: {muted};
                background: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: 700;
            }}

            QPushButton#spotifySectionButton:hover {{
                color: {text};
                background: {card};
                border: 1px solid {border};
            }}

            QPushButton#spotifySectionButton:checked {{
                color: {accent};
                background: {card_alt};
                border: 1px solid {accent};
            }}

            QWidget#spotifyHomeRoot {{
                background: transparent;
            }}

            QLabel#spotifyHomeTitle {{
                color: {text};
                font-size: 22px;
                font-weight: 800;
            }}

            QLabel#spotifyHomeSubtitle,
            QLabel#spotifyHomeCardText {{
                color: {muted};
                font-size: 10px;
            }}

            QLabel#spotifyHomeBadge {{
                color: {accent};
                background: {card};
                border: 1px solid {accent};
                border-radius: 9px;
                padding: 4px 9px;
                font-size: 9px;
                font-weight: 800;
            }}

            QFrame#spotifyHomeCard {{
                background: {card};
                border: 1px solid {border};
                border-radius: 12px;
            }}

            QLabel#spotifyHomeCardTitle {{
                color: {text};
                font-size: 12px;
                font-weight: 800;
            }}

            QStackedWidget#spotifyContentStack {{
                background: {background};
                border: none;
            }}
            """
        )

    def _install_playlist_detail(
        self,
    ) -> None:
        search_artwork_loader = getattr(
            getattr(
                self,
                "search_page",
                None,
            ),
            "artwork_loader",
            None,
        )

        self.playlist_detail = (
            SpotifyPlaylistDetail(
                self.playlist_runtime,
                playback_runtime=(
                    self.playback_runtime
                ),
                theme_manager=(
                    self.theme_manager
                ),
                artwork_loader=(
                    search_artwork_loader
                ),
                parent=(
                    self.content_stack
                ),
            )
        )

        index = self.content_stack.addWidget(
            self.playlist_detail
        )

        if (
            index
            != SPOTIFY_PLAYLIST_DETAIL_INDEX
        ):
            raise RuntimeError(
                (
                    "Spotify playlist detail page "
                    "was inserted at an unexpected "
                    "stack index."
                )
            )


    def _install_liked_songs_detail(
        self,
    ) -> None:
        self.liked_songs_detail = (
            SpotifyLikedSongsDetail(
                self.liked_songs_runtime,
                playback_runtime=(
                    self.playback_runtime
                ),
                theme_manager=(
                    self.theme_manager
                ),
                parent=(
                    self.content_stack
                ),
            )
        )

        index = self.content_stack.addWidget(
            self.liked_songs_detail
        )

        if (
            index
            != SPOTIFY_LIKED_SONGS_INDEX
        ):
            raise RuntimeError(
                (
                    "Spotify Liked Songs detail "
                    "was inserted at an "
                    "unexpected stack index."
                )
            )

    def _install_album_detail(
        self,
    ) -> None:
        self.album_detail = (
            SpotifyAlbumDetail(
                self.album_runtime,
                playback_runtime=(
                    self.playback_runtime
                ),
                theme_manager=(
                    self.theme_manager
                ),
                parent=(
                    self.content_stack
                ),
            )
        )

        index = self.content_stack.addWidget(
            self.album_detail
        )

        if (
            index
            != SPOTIFY_ALBUM_DETAIL_INDEX
        ):
            raise RuntimeError(
                (
                    "Spotify album detail page "
                    "was inserted at an unexpected "
                    "stack index."
                )
            )

    def _install_artist_detail(
        self,
    ) -> None:
        self.artist_detail = (
            SpotifyArtistDetail(
                self.artist_runtime,
                theme_manager=(
                    self.theme_manager
                ),
                parent=(
                    self.content_stack
                ),
            )
        )

        index = self.content_stack.addWidget(
            self.artist_detail
        )

        if (
            index
            != SPOTIFY_ARTIST_DETAIL_INDEX
        ):
            raise RuntimeError(
                (
                    "Spotify artist detail page "
                    "was inserted at an unexpected "
                    "stack index."
                )
            )


    def _show_album_detail_return_section(
        self,
    ) -> None:
        if (
            self._album_detail_return_index
            == SPOTIFY_ARTIST_DETAIL_INDEX
        ):
            self._set_section(
                SPOTIFY_ARTIST_DETAIL_INDEX
            )

            return

        if (
            self._album_detail_return_index
            == SPOTIFY_SEARCH_INDEX
        ):
            self.show_search()

            return

        self.show_home()

    def show_album_detail(
        self,
        item,
    ) -> bool:
        album_detail = getattr(
            self,
            "album_detail",
            None,
        )

        if album_detail is None:
            return False

        current_index = (
            self.content_stack.currentIndex()
        )

        if current_index in {
            SPOTIFY_HOME_INDEX,
            SPOTIFY_SEARCH_INDEX,
            SPOTIFY_ARTIST_DETAIL_INDEX,
        }:
            self._album_detail_return_index = (
                current_index
            )

        if not album_detail.set_search_item(
            item
        ):
            return False

        self._set_section(
            SPOTIFY_ALBUM_DETAIL_INDEX
        )

        return bool(
            album_detail.load()
        )

    def _show_artist_detail_return_section(
        self,
    ) -> None:
        if (
            self._artist_detail_return_index
            == SPOTIFY_SEARCH_INDEX
        ):
            self.show_search()

            return

        self.show_home()

    def show_artist_detail(
        self,
        artist_id,
        *,
        seed_name: str = "",
        seed_image_url: str = "",
    ) -> bool:
        artist_detail = getattr(
            self,
            "artist_detail",
            None,
        )

        if artist_detail is None:
            return False

        current_index = (
            self.content_stack.currentIndex()
        )

        if current_index in {
            SPOTIFY_HOME_INDEX,
            SPOTIFY_SEARCH_INDEX,
        }:
            self._artist_detail_return_index = (
                current_index
            )

        try:
            accepted = (
                artist_detail.set_artist_id(
                    artist_id,
                    seed_name=seed_name,
                    seed_image_url=(
                        seed_image_url
                    ),
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return False

        if not accepted:
            return False

        self._set_section(
            SPOTIFY_ARTIST_DETAIL_INDEX
        )

        return bool(
            artist_detail.load()
        )

    def _show_playlist_detail_return_section(
        self,
    ) -> None:
        if (
            self._playlist_detail_return_index
            == SPOTIFY_SEARCH_INDEX
        ):
            self.show_search()

            return

        self.show_home()

    def show_playlist_detail(
        self,
        playlist,
    ) -> bool:
        current_index = (
            self.content_stack.currentIndex()
        )

        if current_index in {
            SPOTIFY_HOME_INDEX,
            SPOTIFY_SEARCH_INDEX,
        }:
            self._playlist_detail_return_index = (
                current_index
            )

        self.playlist_detail.set_playlist(
            playlist
        )

        self._set_section(
            SPOTIFY_PLAYLIST_DETAIL_INDEX
        )

        return bool(
            self.playlist_detail.load()
        )


    def show_liked_songs(
        self,
    ) -> bool:
        self._set_section(
            SPOTIFY_LIKED_SONGS_INDEX
        )

        return bool(
            self.liked_songs_detail.load()
        )
