import inspect
import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from src.spotify.album_models import SpotifyAlbumTrack
from src.spotify.playback_service import SpotifyPlaybackService
from src.spotify.qt_playback_runtime import SpotifyQtPlaybackRuntime
from src.ui.spotify_album_detail import SpotifyAlbumDetail


def ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def make_track():
    return SpotifyAlbumTrack(
        spotify_id="track123",
        name="Track One",
        uri="spotify:track:track123",
        artists=("Artist One",),
        duration_ms=120000,
        disc_number=1,
        track_number=1,
    )


class FakeAlbumRuntime(QObject):
    album_ready = pyqtSignal(str, object)
    album_tracks_ready = pyqtSignal(str, object)
    failed = pyqtSignal(str, str, str, str)
    operation_finished = pyqtSignal(str, str)

    def load_album(self, album_id, *, market=None):
        del album_id, market

    def load_album_tracks(
        self,
        album_id,
        *,
        limit,
        offset,
        market=None,
    ):
        del album_id, limit, offset, market


class ContextPlaybackRuntime:
    def __init__(self):
        self.album_calls = []
        self.track_calls = []

    def play_album_track(
        self,
        album_id,
        spotify_uri,
    ):
        self.album_calls.append(
            (album_id, spotify_uri)
        )

    def play_track(self, spotify_uri):
        self.track_calls.append(
            spotify_uri
        )


class SpotifyAlbumContextPlaybackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = ensure_app()

    def make_detail(self, playback):
        detail = SpotifyAlbumDetail(
            FakeAlbumRuntime(),
            playback_runtime=playback,
        )
        detail._album_id = "album123"
        self.addCleanup(detail.deleteLater)
        return detail

    def test_album_detail_prefers_album_context_playback(self):
        playback = ContextPlaybackRuntime()
        detail = self.make_detail(playback)

        self.assertTrue(
            detail._handle_track_activated(
                make_track()
            )
        )
        self.assertEqual(
            playback.album_calls,
            [
                (
                    "album123",
                    "spotify:track:track123",
                )
            ],
        )
        self.assertEqual(
            playback.track_calls,
            [],
        )

    def test_album_detail_keeps_compatibility_fallback(self):
        class LegacyRuntime:
            def __init__(self):
                self.calls = []

            def play_track(self, spotify_uri):
                self.calls.append(spotify_uri)

        playback = LegacyRuntime()
        detail = self.make_detail(playback)

        self.assertTrue(
            detail._handle_track_activated(
                make_track()
            )
        )
        self.assertEqual(
            playback.calls,
            ["spotify:track:track123"],
        )

    def test_qt_runtime_exposes_album_context_method(self):
        source = inspect.getsource(
            SpotifyQtPlaybackRuntime.play_album_track
        )
        self.assertIn("album_id", source)
        self.assertIn("_start_playback", source)

    def test_qt_worker_dispatches_album_context(self):
        import src.spotify.qt_playback_runtime as module

        source = inspect.getsource(
            module._SpotifyPlaybackWorker.run
        )
        self.assertIn('"play_album_track"', source)
        self.assertIn("self._album_id", source)

    def test_service_uses_album_context_api(self):
        source = inspect.getsource(
            SpotifyPlaybackService.play_album_track
        )
        self.assertIn(
            "start_album_playback",
            source,
        )
        self.assertIn("_album_uri", source)

    def test_web_api_has_album_context_payload(self):
        with open(
            "src/spotify/web_api.py",
            "r",
            encoding="utf-8-sig",
        ) as handle:
            source = handle.read()

        start = source.index(
            "    def start_album_playback("
        )
        end = source.index(
            "    def start_playlist_playback(",
            start,
        )
        method = source[start:end]

        self.assertIn(
            '"context_uri": context_uri',
            method,
        )
        self.assertIn('"offset": {', method)
        self.assertIn('"uri": track_uri', method)
        self.assertNotIn('"uris": [', method)


if __name__ == "__main__":
    unittest.main()
