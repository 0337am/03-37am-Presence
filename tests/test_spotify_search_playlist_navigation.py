from __future__ import annotations

import os
import unittest
from types import SimpleNamespace

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import (
    QObject,
    Qt,
    pyqtSignal,
)
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.spotify.playlist_models import (
    SpotifyPlaylistSummary,
)
from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
)
from src.ui.spotify_page import (
    SPOTIFY_HOME_INDEX,
    SPOTIFY_PLAYLIST_DETAIL_INDEX,
    SPOTIFY_SEARCH_INDEX,
    SpotifyPage,
)
from src.ui.spotify_search import (
    SpotifySearchPage,
    SpotifySearchResultRow,
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
        return {}


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

    search_finished = pyqtSignal(
        str
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.busy = False
        self.calls = []

    def search(
        self,
        *args,
        **kwargs,
    ):
        self.calls.append(
            (
                args,
                kwargs,
            )
        )

        return True


class FakeArtworkLoader:
    def request(
        self,
        *args,
        **kwargs,
    ):
        raise AssertionError(
            (
                "Artwork should not be requested "
                "for empty-image fixtures."
            )
        )


class StackStub:
    def __init__(
        self,
        index,
    ):
        self.index = index

    def currentIndex(
        self,
    ):
        return self.index


class DetailStub:
    def __init__(
        self,
    ):
        self.playlists = []
        self.load_calls = 0

    def set_playlist(
        self,
        playlist,
    ):
        self.playlists.append(
            playlist
        )

    def load(
        self,
    ):
        self.load_calls += 1

        return True


def search_item(
    item_type,
    spotify_id,
    *,
    name="Result",
    uri=None,
    subtitle="",
    image_url="",
):
    if uri is None:
        uri = (
            "spotify:"
            + item_type.value
            + ":"
            + spotify_id
        )

    return SpotifySearchItem(
        item_type=item_type,
        spotify_id=spotify_id,
        name=name,
        uri=uri,
        subtitle=subtitle,
        image_url=image_url,
    )


def playlist_summary():
    return SpotifyPlaylistSummary(
        spotify_id="playlist-1",
        name="Playlist One",
        spotify_uri=(
            "spotify:playlist:playlist-1"
        ),
        owner_name="Owner",
        total_items=10,
        artwork_reference="",
    )


class SpotifySearchPlaylistNavigationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_playlist_row_emits_activation_on_left_click(
        self,
    ):
        playlist = search_item(
            SpotifySearchItemType.PLAYLIST,
            "playlist-1",
        )

        row = SpotifySearchResultRow(
            playlist,
            artwork_loader=(
                FakeArtworkLoader()
            ),
        )

        self.addCleanup(
            row.deleteLater
        )

        captured = []

        row.activated.connect(
            captured.append
        )

        QTest.mouseClick(
            row,
            Qt.MouseButton.LeftButton,
        )

        self.assertEqual(
            captured,
            [
                playlist
            ],
        )


    def test_artist_row_is_interactive(
        self,
    ):
        artist = search_item(
            SpotifySearchItemType.ARTIST,
            "artist-1",
        )

        row = SpotifySearchResultRow(
            artist,
            artwork_loader=(
                FakeArtworkLoader()
            ),
        )

        self.addCleanup(
            row.deleteLater
        )

        captured = []

        row.activated.connect(
            captured.append
        )

        QTest.mouseClick(
            row,
            Qt.MouseButton.LeftButton,
        )

        self.assertEqual(
            captured,
            [
                artist
            ],
        )

    def test_search_page_emits_playlist_activation(
        self,
    ):
        playlist = search_item(
            SpotifySearchItemType.PLAYLIST,
            "playlist-1",
        )

        page = SpotifySearchPage(
            FakeSearchRuntime(),
            theme_manager=(
                FakeThemeManager()
            ),
            artwork_loader=(
                FakeArtworkLoader()
            ),
        )

        self.addCleanup(
            page.deleteLater
        )

        captured = []

        page.playlist_activated.connect(
            captured.append
        )

        page.sections[
            SpotifySearchItemType.PLAYLIST
        ].set_items(
            (
                playlist,
            )
        )

        QTest.mouseClick(
            page.sections[
                SpotifySearchItemType.PLAYLIST
            ].rows[
                0
            ],
            Qt.MouseButton.LeftButton,
        )

        self.assertEqual(
            captured,
            [
                playlist
            ],
        )

    def test_playlist_activation_does_not_emit_track_signal(
        self,
    ):
        playlist = search_item(
            SpotifySearchItemType.PLAYLIST,
            "playlist-1",
        )

        page = SpotifySearchPage(
            FakeSearchRuntime(),
            theme_manager=(
                FakeThemeManager()
            ),
            artwork_loader=(
                FakeArtworkLoader()
            ),
        )

        self.addCleanup(
            page.deleteLater
        )

        track_events = []

        page.track_activated.connect(
            track_events.append
        )

        page.sections[
            SpotifySearchItemType.PLAYLIST
        ].set_items(
            (
                playlist,
            )
        )

        QTest.mouseClick(
            page.sections[
                SpotifySearchItemType.PLAYLIST
            ].rows[
                0
            ],
            Qt.MouseButton.LeftButton,
        )

        self.assertEqual(
            track_events,
            [],
        )

    def test_page_handler_builds_playlist_summary(
        self,
    ):
        captured = []

        host = SimpleNamespace(
            show_playlist_detail=(
                lambda playlist:
                (
                    captured.append(
                        playlist
                    )
                    or True
                )
            )
        )

        item = search_item(
            SpotifySearchItemType.PLAYLIST,
            "playlist-1",
            name="Playlist One",
            subtitle="Owner",
            image_url=(
                "https://i.scdn.co/"
                "image/playlist"
            ),
        )

        result = (
            SpotifyPage
            ._handle_search_playlist_activated(
                host,
                item,
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            len(
                captured
            ),
            1,
        )

        playlist = captured[
            0
        ]

        self.assertIsInstance(
            playlist,
            SpotifyPlaylistSummary,
        )

        self.assertEqual(
            playlist.spotify_id,
            "playlist-1",
        )

        self.assertEqual(
            playlist.spotify_uri,
            (
                "spotify:playlist:"
                "playlist-1"
            ),
        )

        self.assertEqual(
            playlist.name,
            "Playlist One",
        )

        self.assertEqual(
            playlist.owner_name,
            "Owner",
        )

        self.assertEqual(
            playlist.artwork_reference,
            (
                "https://i.scdn.co/"
                "image/playlist"
            ),
        )

    def test_page_handler_rejects_untrusted_playlist_uri(
        self,
    ):
        captured = []

        host = SimpleNamespace(
            show_playlist_detail=(
                lambda playlist:
                (
                    captured.append(
                        playlist
                    )
                    or True
                )
            )
        )

        item = search_item(
            SpotifySearchItemType.PLAYLIST,
            "playlist-1",
            uri=(
                "spotify:playlist:"
                "different"
            ),
        )

        result = (
            SpotifyPage
            ._handle_search_playlist_activated(
                host,
                item,
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            captured,
            [],
        )

    def test_page_handler_rejects_non_playlist(
        self,
    ):
        captured = []

        host = SimpleNamespace(
            show_playlist_detail=(
                lambda playlist:
                (
                    captured.append(
                        playlist
                    )
                    or True
                )
            )
        )

        track = search_item(
            SpotifySearchItemType.TRACK,
            "track-1",
        )

        result = (
            SpotifyPage
            ._handle_search_playlist_activated(
                host,
                track,
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            captured,
            [],
        )

    def test_show_playlist_detail_remembers_search_origin(
        self,
    ):
        detail = DetailStub()
        sections = []

        host = SimpleNamespace(
            content_stack=(
                StackStub(
                    SPOTIFY_SEARCH_INDEX
                )
            ),
            playlist_detail=detail,
            _playlist_detail_return_index=(
                SPOTIFY_HOME_INDEX
            ),
            _set_section=(
                sections.append
            ),
        )

        result = (
            SpotifyPage
            .show_playlist_detail(
                host,
                playlist_summary(),
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            host._playlist_detail_return_index,
            SPOTIFY_SEARCH_INDEX,
        )

        self.assertEqual(
            sections,
            [
                SPOTIFY_PLAYLIST_DETAIL_INDEX
            ],
        )

    def test_show_playlist_detail_remembers_home_origin(
        self,
    ):
        detail = DetailStub()
        sections = []

        host = SimpleNamespace(
            content_stack=(
                StackStub(
                    SPOTIFY_HOME_INDEX
                )
            ),
            playlist_detail=detail,
            _playlist_detail_return_index=(
                SPOTIFY_SEARCH_INDEX
            ),
            _set_section=(
                sections.append
            ),
        )

        result = (
            SpotifyPage
            .show_playlist_detail(
                host,
                playlist_summary(),
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            host._playlist_detail_return_index,
            SPOTIFY_HOME_INDEX,
        )

    def test_back_returns_to_saved_search_section(
        self,
    ):
        calls = []

        host = SimpleNamespace(
            _playlist_detail_return_index=(
                SPOTIFY_SEARCH_INDEX
            ),
            show_search=(
                lambda:
                calls.append(
                    "search"
                )
            ),
            show_home=(
                lambda:
                calls.append(
                    "home"
                )
            ),
        )

        (
            SpotifyPage
            ._show_playlist_detail_return_section(
                host
            )
        )

        self.assertEqual(
            calls,
            [
                "search"
            ],
        )

    def test_back_returns_home_for_home_origin(
        self,
    ):
        calls = []

        host = SimpleNamespace(
            _playlist_detail_return_index=(
                SPOTIFY_HOME_INDEX
            ),
            show_search=(
                lambda:
                calls.append(
                    "search"
                )
            ),
            show_home=(
                lambda:
                calls.append(
                    "home"
                )
            ),
        )

        (
            SpotifyPage
            ._show_playlist_detail_return_section(
                host
            )
        )

        self.assertEqual(
            calls,
            [
                "home"
            ],
        )


if __name__ == "__main__":
    unittest.main()
