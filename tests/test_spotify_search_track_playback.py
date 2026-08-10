from __future__ import annotations

import os
import unittest
from pathlib import Path
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

from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
)
from src.ui.spotify_page import SpotifyPage
from src.ui.spotify_search import (
    SpotifySearchPage,
    SpotifySearchResultRow,
    SpotifySearchSection,
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
                "for these empty-image fixtures."
            )
        )


class FakePlaybackRuntime:
    def __init__(
        self,
        *,
        result=True,
    ):
        self.result = result
        self.calls = []

    def play_track(
        self,
        spotify_uri,
    ):
        self.calls.append(
            spotify_uri
        )

        return self.result


def item(
    item_type,
    spotify_id,
    *,
    uri=None,
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
        name="Result",
        uri=uri,
        subtitle="Artist",
    )


class SpotifySearchTrackPlaybackTests(
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

    def test_track_row_emits_activation_on_left_click(
        self,
    ):
        track = item(
            SpotifySearchItemType.TRACK,
            "track-1",
        )

        row = SpotifySearchResultRow(
            track,
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
                track
            ],
        )

    def test_non_track_row_remains_non_interactive(
        self,
    ):
        album = item(
            SpotifySearchItemType.ALBUM,
            "album-1",
        )

        row = SpotifySearchResultRow(
            album,
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
            [],
        )

    def test_section_forwards_track_activation(
        self,
    ):
        track = item(
            SpotifySearchItemType.TRACK,
            "track-1",
        )

        section = SpotifySearchSection(
            SpotifySearchItemType.TRACK,
            artwork_loader=(
                FakeArtworkLoader()
            ),
        )

        self.addCleanup(
            section.deleteLater
        )

        captured = []

        section.item_activated.connect(
            captured.append
        )

        section.set_items(
            (
                track,
            )
        )

        QTest.mouseClick(
            section.rows[
                0
            ],
            Qt.MouseButton.LeftButton,
        )

        self.assertEqual(
            captured,
            [
                track
            ],
        )

    def test_search_page_emits_track_activation(
        self,
    ):
        track = item(
            SpotifySearchItemType.TRACK,
            "track-1",
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

        page.track_activated.connect(
            captured.append
        )

        page.sections[
            SpotifySearchItemType.TRACK
        ].set_items(
            (
                track,
            )
        )

        QTest.mouseClick(
            page.sections[
                SpotifySearchItemType.TRACK
            ].rows[
                0
            ],
            Qt.MouseButton.LeftButton,
        )

        self.assertEqual(
            captured,
            [
                track
            ],
        )

    def test_search_page_does_not_emit_album_as_track(
        self,
    ):
        album = item(
            SpotifySearchItemType.ALBUM,
            "album-1",
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

        page.track_activated.connect(
            captured.append
        )

        page.sections[
            SpotifySearchItemType.ALBUM
        ].set_items(
            (
                album,
            )
        )

        QTest.mouseClick(
            page.sections[
                SpotifySearchItemType.ALBUM
            ].rows[
                0
            ],
            Qt.MouseButton.LeftButton,
        )

        self.assertEqual(
            captured,
            [],
        )

    def test_spotify_page_handler_uses_existing_play_track(
        self,
    ):
        playback = (
            FakePlaybackRuntime()
        )

        host = SimpleNamespace(
            playback_runtime=playback
        )

        track = item(
            SpotifySearchItemType.TRACK,
            "track-1",
        )

        result = (
            SpotifyPage
            ._handle_search_track_activated(
                host,
                track,
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            playback.calls,
            [
                "spotify:track:track-1"
            ],
        )

\
    def test_spotify_page_handler_accepts_async_none_return(
        self,
    ):
        playback = FakePlaybackRuntime(
            result=None
        )

        host = SimpleNamespace(
            playback_runtime=playback
        )

        track = item(
            SpotifySearchItemType.TRACK,
            "track-1",
        )

        result = (
            SpotifyPage
            ._handle_search_track_activated(
                host,
                track,
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            playback.calls,
            [
                "spotify:track:track-1"
            ],
        )

    def test_spotify_page_handler_rejects_untrusted_track_uri(
        self,
    ):
        playback = (
            FakePlaybackRuntime()
        )

        host = SimpleNamespace(
            playback_runtime=playback
        )

        track = item(
            SpotifySearchItemType.TRACK,
            "track-1",
            uri=(
                "spotify:track:"
                "different-track"
            ),
        )

        result = (
            SpotifyPage
            ._handle_search_track_activated(
                host,
                track,
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            playback.calls,
            [],
        )

    def test_spotify_page_handler_rejects_non_track(
        self,
    ):
        playback = (
            FakePlaybackRuntime()
        )

        host = SimpleNamespace(
            playback_runtime=playback
        )

        album = item(
            SpotifySearchItemType.ALBUM,
            "album-1",
        )

        result = (
            SpotifyPage
            ._handle_search_track_activated(
                host,
                album,
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            playback.calls,
            [],
        )

    def test_spotify_page_connects_search_track_signal(
        self,
    ):
        source = Path(
            "src/ui/spotify_page.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            (
                "self.search_page."
                "track_activated.connect("
            ),
            source,
        )

        self.assertIn(
            (
                "self._handle_search_"
                "track_activated"
            ),
            source,
        )


if __name__ == "__main__":
    unittest.main()
