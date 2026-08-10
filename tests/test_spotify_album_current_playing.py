import inspect
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.album_models import (
    SpotifyAlbumTrack,
)
from src.ui.spotify_album_detail import (
    SpotifyAlbumDetail,
)
from src.ui.spotify_page import (
    SpotifyPage,
)


def ensure_app():
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


def track(
    *,
    spotify_id,
    name="Example Track",
    artists=(
        "Artist One",
    ),
):
    return SpotifyAlbumTrack(
        spotify_id=spotify_id,
        name=name,
        uri=(
            "spotify:track:"
            + spotify_id
        ),
        artists=artists,
        duration_ms=125000,
        disc_number=1,
        track_number=1,
    )


def song(
    *,
    title="Example Track",
    artist="Artist One",
    album="Example Album",
    playing=True,
    source_app="Spotify.exe",
):
    return SimpleNamespace(
        title=title,
        artist=artist,
        album=album,
        playing=playing,
        source_app=source_app,
    )


class FakeAlbumRuntime(
    QObject
):
    album_ready = pyqtSignal(
        str,
        object,
    )

    album_tracks_ready = pyqtSignal(
        str,
        object,
    )

    failed = pyqtSignal(
        str,
        str,
        str,
        str,
    )

    operation_finished = pyqtSignal(
        str,
        str,
    )

    def load_album(
        self,
        album_id,
        *,
        market=None,
    ):
        del album_id
        del market

    def load_album_tracks(
        self,
        album_id,
        *,
        limit,
        offset,
        market=None,
    ):
        del album_id
        del limit
        del offset
        del market


class SpotifyAlbumCurrentPlayingTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = ensure_app()

    def make_detail(
        self,
    ):
        detail = SpotifyAlbumDetail(
            FakeAlbumRuntime()
        )

        detail._album = SimpleNamespace(
            name="Example Album"
        )

        self.addCleanup(
            detail.deleteLater
        )

        return detail

    def append_one(
        self,
        detail,
        *,
        spotify_id="track123",
        name="Example Track",
        artists=(
            "Artist One",
        ),
    ):
        detail._append_track(
            track(
                spotify_id=spotify_id,
                name=name,
                artists=artists,
            )
        )

        return detail._track_rows[-1]

    def test_exact_spotify_song_highlights_row(
        self,
    ):
        detail = self.make_detail()
        row = self.append_one(
            detail
        )

        detail.set_current_song(
            song()
        )

        self.assertTrue(
            row.playing
        )

    def test_paused_song_clears_highlight(
        self,
    ):
        detail = self.make_detail()
        row = self.append_one(
            detail
        )

        detail.set_current_song(
            song()
        )

        self.assertTrue(
            row.playing
        )

        detail.set_current_song(
            song(
                playing=False
            )
        )

        self.assertFalse(
            row.playing
        )

    def test_non_spotify_source_does_not_highlight(
        self,
    ):
        detail = self.make_detail()
        row = self.append_one(
            detail
        )

        detail.set_current_song(
            song(
                source_app="chrome.exe"
            )
        )

        self.assertFalse(
            row.playing
        )

    def test_primary_artist_matches_multi_artist_track(
        self,
    ):
        detail = self.make_detail()
        row = self.append_one(
            detail,
            artists=(
                "Artist One",
                "Guest Artist",
            ),
        )

        detail.set_current_song(
            song(
                artist="Artist One"
            )
        )

        self.assertTrue(
            row.playing
        )

    def test_full_multi_artist_text_matches(
        self,
    ):
        detail = self.make_detail()
        row = self.append_one(
            detail,
            artists=(
                "Artist One",
                "Guest Artist",
            ),
        )

        detail.set_current_song(
            song(
                artist=(
                    "Artist One, Guest Artist"
                )
            )
        )

        self.assertTrue(
            row.playing
        )

    def test_secondary_collaborator_alone_does_not_match(
        self,
    ):
        detail = self.make_detail()
        row = self.append_one(
            detail,
            artists=(
                "Artist One",
                "Guest Artist",
            ),
        )

        detail.set_current_song(
            song(
                artist="Guest Artist"
            )
        )

        self.assertFalse(
            row.playing
        )

    def test_other_album_does_not_highlight(
        self,
    ):
        detail = self.make_detail()
        row = self.append_one(
            detail
        )

        detail.set_current_song(
            song(
                album="Different Album"
            )
        )

        self.assertFalse(
            row.playing
        )

    def test_ambiguous_duplicate_rows_do_not_highlight(
        self,
    ):
        detail = self.make_detail()

        first = self.append_one(
            detail,
            spotify_id="track123",
        )

        second = self.append_one(
            detail,
            spotify_id="track456",
        )

        detail.set_current_song(
            song()
        )

        self.assertFalse(
            first.playing
        )

        self.assertFalse(
            second.playing
        )

    def test_current_truth_applies_to_later_appended_row(
        self,
    ):
        detail = self.make_detail()

        detail.set_current_song(
            song()
        )

        row = self.append_one(
            detail
        )

        self.assertTrue(
            row.playing
        )

    def test_switching_song_moves_highlight(
        self,
    ):
        detail = self.make_detail()

        first = self.append_one(
            detail,
            spotify_id="track123",
        )

        second = self.append_one(
            detail,
            spotify_id="track456",
            name="Second Track",
        )

        detail.set_current_song(
            song()
        )

        self.assertTrue(
            first.playing
        )

        self.assertFalse(
            second.playing
        )

        detail.set_current_song(
            song(
                title="Second Track"
            )
        )

        self.assertFalse(
            first.playing
        )

        self.assertTrue(
            second.playing
        )

    def test_spotify_page_forwards_truth_to_album_detail(
        self,
    ):
        source = inspect.getsource(
            SpotifyPage.set_current_song
        )

        self.assertIn(
            '"album_detail"',
            source,
        )


if __name__ == "__main__":
    unittest.main()
