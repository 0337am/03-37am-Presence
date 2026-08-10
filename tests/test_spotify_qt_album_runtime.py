import time
import unittest
from types import SimpleNamespace

from PyQt6.QtCore import (
    QCoreApplication,
)

from src.spotify.album_models import (
    SpotifyAlbumSummary,
    SpotifyAlbumTrack,
    SpotifyAlbumTracksPage,
)
from src.spotify.album_service import (
    SpotifyAlbumServiceResult,
    SpotifyAlbumServiceStatus,
)
from src.spotify.qt_album_runtime import (
    OPERATION_ALBUM,
    OPERATION_ALBUM_TRACKS,
    SpotifyQtAlbumRuntime,
    SpotifyQtAlbumRuntimeError,
    _SpotifyAlbumWorker,
)


def ensure_app():
    app = QCoreApplication.instance()

    if app is None:
        app = QCoreApplication(
            []
        )

    return app


def wait_for(
    predicate,
    *,
    timeout=2.0,
):
    app = ensure_app()

    deadline = (
        time.monotonic()
        + timeout
    )

    while (
        time.monotonic()
        < deadline
    ):
        app.processEvents()

        if predicate():
            return True

        time.sleep(
            0.005
        )

    app.processEvents()

    return bool(
        predicate()
    )


def album():
    return SpotifyAlbumSummary(
        spotify_id="album123",
        name="Example Album",
        uri="spotify:album:album123",
        artists=(
            "Artist One",
        ),
        total_tracks=1,
    )


def tracks_page():
    return SpotifyAlbumTracksPage(
        items=(
            SpotifyAlbumTrack(
                spotify_id="track123",
                name="Example Track",
                uri="spotify:track:track123",
                artists=(
                    "Artist One",
                ),
                duration_ms=120000,
                disc_number=1,
                track_number=1,
            ),
        ),
        limit=50,
        offset=0,
        total=1,
    )


def album_result():
    return SpotifyAlbumServiceResult(
        status=(
            SpotifyAlbumServiceStatus.READY
        ),
        album=album(),
    )


def tracks_result():
    return SpotifyAlbumServiceResult(
        status=(
            SpotifyAlbumServiceStatus.READY
        ),
        tracks_page=tracks_page(),
    )


class FakeAlbumService:
    def __init__(
        self,
    ):
        self.calls = []

    def get_album(
        self,
        album_id,
        *,
        market=None,
    ):
        self.calls.append(
            (
                "album",
                album_id,
                market,
            )
        )

        return album_result()

    def get_album_tracks(
        self,
        album_id,
        *,
        limit,
        offset,
        market=None,
    ):
        self.calls.append(
            (
                "tracks",
                album_id,
                limit,
                offset,
                market,
            )
        )

        return tracks_result()


class SpotifyQtAlbumWorkerTests(
    unittest.TestCase
):
    def test_worker_loads_album(
        self,
    ):
        service = FakeAlbumService()

        worker = _SpotifyAlbumWorker(
            lambda: service,
            OPERATION_ALBUM,
            "album123",
            limit=50,
            offset=0,
            market="GB",
        )

        results = []

        worker.result_ready.connect(
            lambda *args:
            results.append(
                args
            )
        )

        worker.run()

        self.assertEqual(
            service.calls,
            [
                (
                    "album",
                    "album123",
                    "GB",
                ),
            ],
        )

        self.assertEqual(
            results[0][0],
            OPERATION_ALBUM,
        )

    def test_worker_loads_album_tracks(
        self,
    ):
        service = FakeAlbumService()

        worker = _SpotifyAlbumWorker(
            lambda: service,
            OPERATION_ALBUM_TRACKS,
            "album123",
            limit=20,
            offset=40,
            market="US",
        )

        results = []

        worker.result_ready.connect(
            lambda *args:
            results.append(
                args
            )
        )

        worker.run()

        self.assertEqual(
            service.calls,
            [
                (
                    "tracks",
                    "album123",
                    20,
                    40,
                    "US",
                ),
            ],
        )

        self.assertEqual(
            results[0][0],
            OPERATION_ALBUM_TRACKS,
        )

    def test_worker_rejects_invalid_result(
        self,
    ):
        class InvalidService:
            def get_album(
                self,
                album_id,
                *,
                market=None,
            ):
                return object()

        worker = _SpotifyAlbumWorker(
            lambda: InvalidService(),
            OPERATION_ALBUM,
            "album123",
            limit=50,
            offset=0,
            market="",
        )

        failures = []

        worker.failed.connect(
            lambda *args:
            failures.append(
                args
            )
        )

        worker.run()

        self.assertEqual(
            failures[0][2],
            "invalid_result",
        )

    def test_worker_wraps_service_exception(
        self,
    ):
        def broken_factory():
            raise RuntimeError(
                "boom"
            )

        worker = _SpotifyAlbumWorker(
            broken_factory,
            OPERATION_ALBUM,
            "album123",
            limit=50,
            offset=0,
            market="",
        )

        failures = []

        worker.failed.connect(
            lambda *args:
            failures.append(
                args
            )
        )

        worker.run()

        self.assertEqual(
            failures[0][2],
            "service_error",
        )


class SpotifyQtAlbumRuntimeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        ensure_app()

    def test_constructor_requires_factory(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyQtAlbumRuntime(
                None
            )

    def test_load_album_validates_id_before_thread(
        self,
    ):
        runtime = SpotifyQtAlbumRuntime(
            FakeAlbumService
        )

        with self.assertRaises(
            ValueError
        ):
            runtime.load_album(
                ""
            )

        self.assertFalse(
            runtime.busy
        )

    def test_load_tracks_validates_limit_before_thread(
        self,
    ):
        runtime = SpotifyQtAlbumRuntime(
            FakeAlbumService
        )

        with self.assertRaises(
            ValueError
        ):
            runtime.load_album_tracks(
                "album123",
                limit=51,
            )

        self.assertFalse(
            runtime.busy
        )

    def test_album_result_is_emitted_asynchronously(
        self,
    ):
        service = FakeAlbumService()

        runtime = SpotifyQtAlbumRuntime(
            lambda: service
        )

        results = []

        runtime.album_ready.connect(
            lambda *args:
            results.append(
                args
            )
        )

        runtime.load_album(
            "album123",
            market="gb",
        )

        self.assertTrue(
            wait_for(
                lambda:
                bool(
                    results
                )
                and not runtime.busy
            )
        )

        self.assertEqual(
            service.calls,
            [
                (
                    "album",
                    "album123",
                    "GB",
                ),
            ],
        )

        self.assertEqual(
            results[0][0],
            "album123",
        )

        self.assertTrue(
            results[0][1].ready
        )

    def test_tracks_result_is_emitted_asynchronously(
        self,
    ):
        service = FakeAlbumService()

        runtime = SpotifyQtAlbumRuntime(
            lambda: service
        )

        results = []

        runtime.album_tracks_ready.connect(
            lambda *args:
            results.append(
                args
            )
        )

        runtime.load_album_tracks(
            "album123",
            limit=20,
            offset=40,
            market="us",
        )

        self.assertTrue(
            wait_for(
                lambda:
                bool(
                    results
                )
                and not runtime.busy
            )
        )

        self.assertEqual(
            service.calls,
            [
                (
                    "tracks",
                    "album123",
                    20,
                    40,
                    "US",
                ),
            ],
        )

        self.assertTrue(
            results[0][1].ready
        )

    def test_busy_runtime_rejects_second_request(
        self,
    ):
        runtime = SpotifyQtAlbumRuntime(
            FakeAlbumService
        )

        runtime._busy = True

        with self.assertRaises(
            SpotifyQtAlbumRuntimeError
        ) as raised:
            runtime.load_album(
                "album123"
            )

        self.assertEqual(
            raised.exception.error_code,
            "busy",
        )

    def test_shutting_down_runtime_rejects_request(
        self,
    ):
        runtime = SpotifyQtAlbumRuntime(
            FakeAlbumService
        )

        runtime._shutting_down = True

        with self.assertRaises(
            SpotifyQtAlbumRuntimeError
        ) as raised:
            runtime.load_album(
                "album123"
            )

        self.assertEqual(
            raised.exception.error_code,
            "shutting_down",
        )

    def test_result_router_uses_album_signal(
        self,
    ):
        runtime = SpotifyQtAlbumRuntime(
            FakeAlbumService
        )

        seen = []

        runtime.album_ready.connect(
            lambda *args:
            seen.append(
                args
            )
        )

        runtime._handle_worker_result(
            OPERATION_ALBUM,
            "album123",
            album_result(),
        )

        self.assertEqual(
            len(
                seen
            ),
            1,
        )

    def test_result_router_uses_tracks_signal(
        self,
    ):
        runtime = SpotifyQtAlbumRuntime(
            FakeAlbumService
        )

        seen = []

        runtime.album_tracks_ready.connect(
            lambda *args:
            seen.append(
                args
            )
        )

        runtime._handle_worker_result(
            OPERATION_ALBUM_TRACKS,
            "album123",
            tracks_result(),
        )

        self.assertEqual(
            len(
                seen
            ),
            1,
        )

    def test_failure_is_forwarded(
        self,
    ):
        runtime = SpotifyQtAlbumRuntime(
            FakeAlbumService
        )

        seen = []

        runtime.failed.connect(
            lambda *args:
            seen.append(
                args
            )
        )

        runtime._handle_worker_failure(
            OPERATION_ALBUM,
            "album123",
            "simulated",
            "Safe failure.",
        )

        self.assertEqual(
            seen,
            [
                (
                    OPERATION_ALBUM,
                    "album123",
                    "simulated",
                    "Safe failure.",
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
