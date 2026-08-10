import inspect
import unittest

from src.spotify.artist_service import (
    SpotifyArtistServiceResult,
    SpotifyArtistServiceStatus,
)
from src.spotify.qt_artist_runtime import (
    DEFAULT_SPOTIFY_ARTIST_RUNTIME_LIMIT,
    OPERATION_ARTIST,
    OPERATION_ARTIST_ALBUMS,
    SpotifyQtArtistRuntime,
    _SpotifyArtistWorker,
)


class FakeArtistService:
    def __init__(self):
        self.calls = []

    def get_artist(
        self,
        artist_id,
    ):
        self.calls.append(
            (
                "artist",
                artist_id,
            )
        )

        return SpotifyArtistServiceResult(
            status=(
                SpotifyArtistServiceStatus.ERROR
            ),
            error_code="test",
        )

    def get_artist_albums(
        self,
        artist_id,
        *,
        limit,
        offset,
        market=None,
    ):
        self.calls.append(
            (
                "albums",
                artist_id,
                limit,
                offset,
                market,
            )
        )

        return SpotifyArtistServiceResult(
            status=(
                SpotifyArtistServiceStatus.ERROR
            ),
            error_code="test",
        )


class SpotifyQtArtistRuntimeTests(
    unittest.TestCase
):
    def test_default_limit_is_ten(
        self,
    ):
        self.assertEqual(
            DEFAULT_SPOTIFY_ARTIST_RUNTIME_LIMIT,
            10,
        )

    def test_runtime_exposes_artist_signals(
        self,
    ):
        self.assertTrue(
            hasattr(
                SpotifyQtArtistRuntime,
                "artist_ready",
            )
        )

        self.assertTrue(
            hasattr(
                SpotifyQtArtistRuntime,
                "artist_albums_ready",
            )
        )

    def test_load_artist_has_no_market_argument(
        self,
    ):
        parameters = (
            inspect.signature(
                SpotifyQtArtistRuntime.load_artist
            ).parameters
        )

        self.assertNotIn(
            "market",
            parameters,
        )

    def test_worker_dispatches_artist(
        self,
    ):
        service = FakeArtistService()

        worker = _SpotifyArtistWorker(
            lambda: service,
            OPERATION_ARTIST,
            "artist123",
            limit=10,
            offset=0,
            market="",
        )

        captured = []

        worker.result_ready.connect(
            lambda *args: captured.append(args)
        )

        worker.run()

        self.assertEqual(
            service.calls,
            [
                (
                    "artist",
                    "artist123",
                ),
            ],
        )

        self.assertEqual(
            len(captured),
            1,
        )

    def test_worker_dispatches_artist_albums(
        self,
    ):
        service = FakeArtistService()

        worker = _SpotifyArtistWorker(
            lambda: service,
            OPERATION_ARTIST_ALBUMS,
            "artist123",
            limit=5,
            offset=10,
            market="GB",
        )

        captured = []

        worker.result_ready.connect(
            lambda *args: captured.append(args)
        )

        worker.run()

        self.assertEqual(
            service.calls,
            [
                (
                    "albums",
                    "artist123",
                    5,
                    10,
                    "GB",
                ),
            ],
        )

        self.assertEqual(
            len(captured),
            1,
        )

    def test_invalid_artist_id_is_rejected(
        self,
    ):
        runtime = SpotifyQtArtistRuntime(
            lambda: FakeArtistService()
        )

        self.addCleanup(
            runtime.shutdown
        )

        with self.assertRaises(
            ValueError
        ):
            runtime.load_artist(
                "../bad"
            )

    def test_album_limit_is_enforced(
        self,
    ):
        runtime = SpotifyQtArtistRuntime(
            lambda: FakeArtistService()
        )

        self.addCleanup(
            runtime.shutdown
        )

        with self.assertRaises(
            ValueError
        ):
            runtime.load_artist_albums(
                "artist123",
                limit=11,
            )

    def test_factory_must_be_callable(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyQtArtistRuntime(
                object()
            )


if __name__ == "__main__":
    unittest.main()