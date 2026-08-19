import inspect
import os
import unittest

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
    SpotifyAlbumTrackRow,
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
    spotify_id="track123",
    playable=None,
):
    return SpotifyAlbumTrack(
        spotify_id=spotify_id,
        name="Example Track",
        uri=(
            "spotify:track:"
            + spotify_id
        ),
        artists=(
            "Artist One",
        ),
        duration_ms=125000,
        disc_number=1,
        track_number=1,
        is_playable=playable,
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


class FakePlaybackRuntime:
    def __init__(
        self,
    ):
        self.calls = []

    def play_track(
        self,
        spotify_uri,
    ):
        self.calls.append(
            spotify_uri
        )


class SpotifyAlbumPlaybackTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = ensure_app()

    def make_detail(
        self,
        playback_runtime=None,
    ):
        detail = SpotifyAlbumDetail(
            FakeAlbumRuntime(),
            playback_runtime=(
                playback_runtime
            ),
        )

        self.addCleanup(
            detail.deleteLater
        )

        return detail

    def test_track_row_activation_emits_track(
        self,
    ):
        item = track()

        row = SpotifyAlbumTrackRow(
            item,
            number=1,
        )

        self.addCleanup(
            row.deleteLater
        )

        seen = []

        row.activated.connect(
            seen.append
        )

        self.assertTrue(
            row.activate()
        )

        self.assertEqual(
            seen,
            [
                item
            ],
        )

    def test_explicitly_unplayable_row_does_not_activate(
        self,
    ):
        item = track(
            playable=False
        )

        row = SpotifyAlbumTrackRow(
            item,
            number=1,
        )

        self.addCleanup(
            row.deleteLater
        )

        seen = []

        row.activated.connect(
            seen.append
        )

        self.assertFalse(
            row.activate()
        )

        self.assertEqual(
            seen,
            [],
        )

    def test_detail_routes_album_track_to_existing_play_track(
        self,
    ):
        playback = FakePlaybackRuntime()
        detail = self.make_detail(
            playback
        )

        item = track()

        self.assertTrue(
            detail._handle_track_activated(
                item
            )
        )

        self.assertEqual(
            playback.calls,
            [
                "spotify:track:track123"
            ],
        )

    def test_appended_row_is_connected_to_playback(
        self,
    ):
        playback = FakePlaybackRuntime()
        detail = self.make_detail(
            playback
        )

        detail._append_track(
            track()
        )

        self.assertEqual(
            len(
                detail._track_rows
            ),
            1,
        )

        self.assertTrue(
            detail._track_rows[
                0
            ].activate()
        )

        self.assertEqual(
            playback.calls,
            [
                "spotify:track:track123"
            ],
        )

    def test_no_playback_runtime_keeps_activation_safe(
        self,
    ):
        detail = self.make_detail()

        self.assertFalse(
            detail._handle_track_activated(
                track()
            )
        )

    def test_invalid_playback_runtime_is_rejected(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyAlbumDetail(
                FakeAlbumRuntime(),
                playback_runtime=object(),
            )

    def test_spotify_page_passes_existing_playback_runtime(
        self,
    ):
        source = inspect.getsource(
            SpotifyPage._install_album_detail
        )

        self.assertIn(
            "playback_runtime=(",
            source,
        )

        self.assertIn(
            "self.playback_runtime",
            source,
        )


if __name__ == "__main__":
    unittest.main()
