from __future__ import annotations

import os
import unittest
from types import SimpleNamespace

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
)
from src.ui.spotify_search import (
    SpotifySearchPage,
    SpotifySearchResultRow,
)


class FakeSignal:
    def __init__(
        self,
    ):
        self.values = []

    def emit(
        self,
        value,
    ):
        self.values.append(
            value
        )


def artist_item():
    return SpotifySearchItem(
        item_type=(
            SpotifySearchItemType.ARTIST
        ),
        spotify_id="artist123",
        name="Artist One",
        uri=(
            "spotify:artist:artist123"
        ),
        image_url="",
        subtitle="Artist",
    )


class SpotifySearchArtistActivationTests(
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

    def test_artist_row_emits_activation(
        self,
    ):
        artist = artist_item()

        row = SpotifySearchResultRow(
            artist
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

    def test_search_page_exposes_artist_signal(
        self,
    ):
        self.assertTrue(
            hasattr(
                SpotifySearchPage,
                "artist_activated",
            )
        )

    def test_search_page_routes_artist_activation(
        self,
    ):
        target = SimpleNamespace(
            track_activated=FakeSignal(),
            playlist_activated=FakeSignal(),
            album_activated=FakeSignal(),
            artist_activated=FakeSignal(),
        )

        artist = artist_item()

        SpotifySearchPage._handle_item_activated(
            target,
            artist,
        )

        self.assertEqual(
            target.artist_activated.values,
            [
                artist
            ],
        )

        self.assertEqual(
            target.track_activated.values,
            [],
        )

        self.assertEqual(
            target.playlist_activated.values,
            [],
        )

        self.assertEqual(
            target.album_activated.values,
            [],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
