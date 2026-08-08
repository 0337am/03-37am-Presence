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
from src.ui.theme import ThemeManager


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


class SpotifyPage(
    QWidget
):
    def __init__(
        self,
        *,
        search_runtime,
        playlist_runtime,
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

        self.theme_manager = (
            theme_manager
            or ThemeManager(
                self
            )
        )

        self._activated = False

        self.setObjectName(
            "spotifyRoot"
        )

        self.build_ui()

        self._install_playlist_home()
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

    def _set_section(
        self,
        index: int,
    ) -> None:
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
