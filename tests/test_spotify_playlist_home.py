from __future__ import annotations

import unittest

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.playlist_models import (
    SpotifyPlaylistPage,
    SpotifyPlaylistSummary,
)
from src.ui.spotify_page import (
    SpotifyPage,
)
from src.ui.spotify_playlist_widgets import (
    SPOTIFY_PLAYLIST_HOME_LIMIT,
    SpotifyPlaylistHome,
    SpotifyPlaylistRow,
)


class FakeThemeManager(
    QObject
):
    theme_changed = pyqtSignal(
        dict
    )

    def theme(
        self,
    ):
        return {
            "background": "#101014",
            "card": "#18181f",
            "card_alt": "#202028",
            "border": "#34343e",
            "accent": "#ff4f91",
            "text": "#f4f4f6",
            "muted": "#a6a6b1",
        }


class FakeArtworkLoader(
    QObject
):
    artwork_ready = pyqtSignal(
        str,
        object,
    )

    artwork_failed = pyqtSignal(
        str
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.requests = []

    def request(
        self,
        url,
    ):
        self.requests.append(
            url
        )

        return True


class FakeSearchRuntime(
    QObject
):
    result_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
    )

    busy_changed = pyqtSignal(
        bool
    )

    search_started = pyqtSignal(
        str
    )

    search_finished = pyqtSignal(
        str
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.busy = False
        self.active_query = None

    def search(
        self,
        *args,
        **kwargs,
    ):
        pass


class FakePlaylistRuntime(
    QObject
):
    playlists_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
        str,
    )

    busy_changed = pyqtSignal(
        bool
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.calls = []
        self.busy = False

    def load_playlists(
        self,
        *,
        limit=50,
        offset=0,
    ):
        self.calls.append(
            {
                "limit": limit,
                "offset": offset,
            }
        )

    def load_playlist_items(
        self,
        playlist_id,
        *,
        limit=50,
        offset=0,
        market=None,
    ):
        pass


class FakeResult:
    def __init__(
        self,
        *,
        ready,
        playlists_page=None,
        message="",
    ):
        self.ready = ready
        self.playlists_page = (
            playlists_page
        )
        self.message = message


def playlist(
    *,
    spotify_id="playlist-1",
    name="Late Night",
    owner_name="03:37am",
    total_items=42,
    artwork_reference=(
        "https://i.scdn.co/image/example"
    ),
):
    return SpotifyPlaylistSummary(
        spotify_id=spotify_id,
        name=name,
        spotify_uri=(
            "spotify:playlist:"
            + spotify_id
        ),
        owner_name=owner_name,
        total_items=total_items,
        artwork_reference=(
            artwork_reference
        ),
    )


def page(
    *playlists,
    total=None,
):
    if total is None:
        total = len(
            playlists
        )

    return SpotifyPlaylistPage(
        playlists=tuple(
            playlists
        ),
        limit=50,
        offset=0,
        total=total,
    )


class SpotifyPlaylistHomeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication(
                []
            )
        )

    def make_home(
        self,
    ):
        runtime = (
            FakePlaylistRuntime()
        )

        artwork_loader = (
            FakeArtworkLoader()
        )

        home = SpotifyPlaylistHome(
            runtime,
            theme_manager=(
                FakeThemeManager()
            ),
            artwork_loader=(
                artwork_loader
            ),
        )

        self.addCleanup(
            home.deleteLater
        )

        return (
            home,
            runtime,
            artwork_loader,
        )

    def test_constructor_does_not_start_request(
        self,
    ):
        _home, runtime, _loader = (
            self.make_home()
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_ensure_loaded_requests_first_50_playlists(
        self,
    ):
        home, runtime, _loader = (
            self.make_home()
        )

        self.assertTrue(
            home.ensure_loaded()
        )

        self.assertEqual(
            runtime.calls,
            [
                {
                    "limit": (
                        SPOTIFY_PLAYLIST_HOME_LIMIT
                    ),
                    "offset": 0,
                }
            ],
        )

        self.assertEqual(
            SPOTIFY_PLAYLIST_HOME_LIMIT,
            50,
        )

    def test_ensure_loaded_only_auto_requests_once(
        self,
    ):
        home, runtime, _loader = (
            self.make_home()
        )

        home.ensure_loaded()
        home.ensure_loaded()

        self.assertEqual(
            len(
                runtime.calls
            ),
            1,
        )

    def test_ready_result_populates_playlist_rows(
        self,
    ):
        home, _runtime, _loader = (
            self.make_home()
        )

        loaded_page = page(
            playlist(
                spotify_id="one",
                name="One",
            ),
            playlist(
                spotify_id="two",
                name="Two",
            ),
        )

        home.handle_playlists_ready(
            FakeResult(
                ready=True,
                playlists_page=(
                    loaded_page
                ),
                message=(
                    "Spotify playlists loaded."
                ),
            )
        )

        self.assertTrue(
            home.loaded
        )

        self.assertEqual(
            len(
                home.rows
            ),
            2,
        )

        self.assertEqual(
            home.count_badge.text(),
            "2",
        )

    def test_row_displays_name_owner_and_item_count(
        self,
    ):
        row = SpotifyPlaylistRow(
            playlist(
                name="LLJW",
                owner_name="Riley",
                total_items=86,
            ),
            artwork_loader=(
                FakeArtworkLoader()
            ),
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            row.name_label.text(),
            "LLJW",
        )

        self.assertEqual(
            row.owner_label.text(),
            "By Riley",
        )

        self.assertEqual(
            row.count_label.text(),
            "86 items",
        )

    def test_playlist_row_requests_artwork(
        self,
    ):
        loader = FakeArtworkLoader()

        reference = (
            "https://i.scdn.co/image/playlist"
        )

        row = SpotifyPlaylistRow(
            playlist(
                artwork_reference=(
                    reference
                )
            ),
            artwork_loader=loader,
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            loader.requests,
            [
                reference
            ],
        )

    def test_matching_artwork_replaces_fallback(
        self,
    ):
        loader = FakeArtworkLoader()

        item = playlist()

        row = SpotifyPlaylistRow(
            item,
            artwork_loader=loader,
        )

        self.addCleanup(
            row.deleteLater
        )

        pixmap = QPixmap(
            8,
            8,
        )

        loader.artwork_ready.emit(
            item.artwork_reference,
            pixmap,
        )

        self.assertEqual(
            row.artwork_label.text(),
            "",
        )

        self.assertIsNotNone(
            row.artwork_label.pixmap()
        )

    def test_empty_ready_page_shows_empty_state(
        self,
    ):
        home, _runtime, _loader = (
            self.make_home()
        )

        home.handle_playlists_ready(
            FakeResult(
                ready=True,
                playlists_page=page(),
            )
        )

        self.assertEqual(
            home.rows,
            (),
        )

        self.assertTrue(
            home.empty_label.isVisible()
            or not home.isVisible()
        )

        self.assertEqual(
            home.count_badge.text(),
            "0",
        )

    def test_non_ready_result_is_user_safe(
        self,
    ):
        home, _runtime, _loader = (
            self.make_home()
        )

        home.handle_playlists_ready(
            FakeResult(
                ready=False,
                message=(
                    "Reconnect Spotify before "
                    "loading playlists."
                ),
            )
        )

        self.assertFalse(
            home.loaded
        )

        self.assertIn(
            "Reconnect Spotify",
            home.status_label.text(),
        )

    def test_runtime_failure_is_user_safe(
        self,
    ):
        home, runtime, _loader = (
            self.make_home()
        )

        runtime.failed.emit(
            "playlists",
            "network_error",
            "Spotify playlists could not be loaded.",
        )

        self.assertIn(
            "could not be loaded",
            home.status_label.text(),
        )

    def test_busy_state_disables_refresh(
        self,
    ):
        home, runtime, _loader = (
            self.make_home()
        )

        runtime.busy_changed.emit(
            True
        )

        self.assertFalse(
            home.refresh_button.isEnabled()
        )

        self.assertEqual(
            home.refresh_button.text(),
            "Loading...",
        )

        runtime.busy_changed.emit(
            False
        )

        self.assertTrue(
            home.refresh_button.isEnabled()
        )

    def test_spotify_page_construction_does_not_load_playlists(
        self,
    ):
        runtime = (
            FakePlaylistRuntime()
        )

        page_widget = SpotifyPage(
            search_runtime=(
                FakeSearchRuntime()
            ),
            playlist_runtime=runtime,
            theme_manager=(
                FakeThemeManager()
            ),
        )

        self.addCleanup(
            page_widget.deleteLater
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

        self.assertIs(
            page_widget.playlist_home.artwork_loader,
            page_widget.search_page.artwork_loader,
        )

        self.assertIs(
            page_widget.playlist_detail.artwork_loader,
            page_widget.search_page.artwork_loader,
        )

    def test_activating_spotify_page_loads_playlists_once(
        self,
    ):
        runtime = (
            FakePlaylistRuntime()
        )

        page_widget = SpotifyPage(
            search_runtime=(
                FakeSearchRuntime()
            ),
            playlist_runtime=runtime,
            theme_manager=(
                FakeThemeManager()
            ),
        )

        self.addCleanup(
            page_widget.deleteLater
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

        self.assertTrue(
            page_widget.activate()
        )

        self.assertEqual(
            runtime.calls,
            [
                {
                    "limit": (
                        SPOTIFY_PLAYLIST_HOME_LIMIT
                    ),
                    "offset": 0,
                }
            ],
        )

        self.assertFalse(
            page_widget.activate()
        )

        self.assertEqual(
            len(
                runtime.calls
            ),
            1,
        )

    def test_search_section_does_not_load_home_until_home_selected(
        self,
    ):
        runtime = (
            FakePlaylistRuntime()
        )

        page_widget = SpotifyPage(
            search_runtime=(
                FakeSearchRuntime()
            ),
            playlist_runtime=runtime,
            theme_manager=(
                FakeThemeManager()
            ),
        )

        self.addCleanup(
            page_widget.deleteLater
        )

        page_widget.show_search()

        self.assertFalse(
            page_widget.activate()
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

        page_widget.show_home()

        self.assertEqual(
            runtime.calls,
            [
                {
                    "limit": (
                        SPOTIFY_PLAYLIST_HOME_LIMIT
                    ),
                    "offset": 0,
                }
            ],
        )

    def test_manual_refresh_can_request_again(
        self,
    ):
        home, runtime, _loader = (
            self.make_home()
        )

        home.ensure_loaded()

        home.handle_playlists_ready(
            FakeResult(
                ready=True,
                playlists_page=page(
                    playlist()
                ),
            )
        )

        self.assertTrue(
            home.refresh()
        )

        self.assertEqual(
            len(
                runtime.calls
            ),
            2,
        )
