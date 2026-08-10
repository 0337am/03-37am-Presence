from __future__ import annotations

import threading
import time
import unittest

from PyQt6.QtCore import (
    QCoreApplication,
)

from src.spotify.playback_service import (
    SpotifyPlaybackServiceResult,
    SpotifyPlaybackServiceStatus,
)
from src.spotify.qt_playback_runtime import (
    SpotifyQtPlaybackRuntime,
    SpotifyQtPlaybackRuntimeError,
)


TRACK_URI = (
    "spotify:track:"
    "4uLU6hMCjMI75M1A2tKUQC"
)


def process_until(
    predicate,
    *,
    timeout=2.0,
):
    app = (
        QCoreApplication.instance()
        or QCoreApplication([])
    )

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


class ResultService:
    def __init__(
        self,
        result,
        *,
        thread_ids=None,
    ):
        self.result = result
        self.thread_ids = thread_ids
        self.playlist_calls = []
        self.position_calls = []

    def play_track(
        self,
        spotify_uri,
    ):
        if self.thread_ids is not None:
            self.thread_ids.append(
                threading.get_ident()
            )

        return self.result

    def play_playlist_position(
        self,
        playlist_id,
        position,
    ):
        if self.thread_ids is not None:
            self.thread_ids.append(
                threading.get_ident()
            )

        self.position_calls.append(
            (
                playlist_id,
                position,
            )
        )

        return self.result

    def play_playlist_track(
        self,
        playlist_id,
        spotify_uri,
    ):
        if self.thread_ids is not None:
            self.thread_ids.append(
                threading.get_ident()
            )

        self.playlist_calls.append(
            (
                playlist_id,
                spotify_uri,
            )
        )

        return self.result


class BlockingService:
    def __init__(
        self,
        started,
        release,
    ):
        self.started = started
        self.release = release

    def play_track(
        self,
        spotify_uri,
    ):
        self.started.set()

        self.release.wait(
            2.0
        )

        return SpotifyPlaybackServiceResult(
            status=(
                SpotifyPlaybackServiceStatus.READY
            ),
            message="ready",
        )


def ready_result():
    return SpotifyPlaybackServiceResult(
        status=(
            SpotifyPlaybackServiceStatus.READY
        ),
        message="ready",
    )


class SpotifyQtPlaybackRuntimeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QCoreApplication.instance()
            or QCoreApplication([])
        )

    def test_constructor_validates_service_factory(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyQtPlaybackRuntime(
                object()
            )

    def test_ready_result_is_forwarded(
        self,
    ):
        result = ready_result()

        runtime = SpotifyQtPlaybackRuntime(
            lambda:
            ResultService(
                result
            )
        )

        observed = []

        runtime.result_ready.connect(
            observed.append
        )

        runtime.play_track(
            TRACK_URI
        )

        self.assertTrue(
            process_until(
                lambda:
                (
                    observed
                    and not runtime.busy
                )
            )
        )

        self.assertIs(
            observed[0],
            result,
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_non_ready_service_result_is_forwarded(
        self,
    ):
        result = SpotifyPlaybackServiceResult(
            status=(
                SpotifyPlaybackServiceStatus
                .DISCONNECTED
            ),
            message="Connect Spotify.",
        )

        runtime = SpotifyQtPlaybackRuntime(
            lambda:
            ResultService(
                result
            )
        )

        observed = []

        runtime.result_ready.connect(
            observed.append
        )

        runtime.play_track(
            TRACK_URI
        )

        self.assertTrue(
            process_until(
                lambda:
                (
                    observed
                    and not runtime.busy
                )
            )
        )

        self.assertEqual(
            observed[0].status,
            SpotifyPlaybackServiceStatus
            .DISCONNECTED,
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_playback_runs_off_calling_thread(
        self,
    ):
        calling_thread = (
            threading.get_ident()
        )

        worker_threads = []

        runtime = SpotifyQtPlaybackRuntime(
            lambda:
            ResultService(
                ready_result(),
                thread_ids=worker_threads,
            )
        )

        runtime.play_track(
            TRACK_URI
        )

        self.assertTrue(
            process_until(
                lambda:
                (
                    worker_threads
                    and not runtime.busy
                )
            )
        )

        self.assertNotEqual(
            worker_threads[0],
            calling_thread,
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_busy_runtime_rejects_second_request(
        self,
    ):
        started = threading.Event()
        release = threading.Event()

        runtime = SpotifyQtPlaybackRuntime(
            lambda:
            BlockingService(
                started,
                release,
            )
        )

        runtime.play_track(
            TRACK_URI
        )

        self.assertTrue(
            started.wait(
                1.0
            )
        )

        with self.assertRaises(
            SpotifyQtPlaybackRuntimeError
        ) as caught:
            runtime.play_track(
                TRACK_URI
            )

        self.assertEqual(
            caught.exception.error_code,
            "busy",
        )

        release.set()

        self.assertTrue(
            process_until(
                lambda:
                not runtime.busy
            )
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_service_factory_exception_is_safe(
        self,
    ):
        def factory():
            raise RuntimeError(
                "private setup detail"
            )

        runtime = SpotifyQtPlaybackRuntime(
            factory
        )

        failures = []

        runtime.failed.connect(
            lambda code, message:
            failures.append(
                (
                    code,
                    message,
                )
            )
        )

        runtime.play_track(
            TRACK_URI
        )

        self.assertTrue(
            process_until(
                lambda:
                (
                    failures
                    and not runtime.busy
                )
            )
        )

        self.assertEqual(
            failures[0][0],
            "runtime_setup_failed",
        )

        self.assertNotIn(
            "private setup detail",
            failures[0][1],
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_service_without_play_track_is_rejected(
        self,
    ):
        runtime = SpotifyQtPlaybackRuntime(
            lambda:
            object()
        )

        failures = []

        runtime.failed.connect(
            lambda code, message:
            failures.append(
                (
                    code,
                    message,
                )
            )
        )

        runtime.play_track(
            TRACK_URI
        )

        self.assertTrue(
            process_until(
                lambda:
                (
                    failures
                    and not runtime.busy
                )
            )
        )

        self.assertEqual(
            failures[0][0],
            "invalid_service",
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_invalid_service_result_is_rejected(
        self,
    ):
        class BadService:
            def play_track(
                self,
                spotify_uri,
            ):
                return object()

        runtime = SpotifyQtPlaybackRuntime(
            lambda:
            BadService()
        )

        failures = []

        runtime.failed.connect(
            lambda code, message:
            failures.append(
                (
                    code,
                    message,
                )
            )
        )

        runtime.play_track(
            TRACK_URI
        )

        self.assertTrue(
            process_until(
                lambda:
                (
                    failures
                    and not runtime.busy
                )
            )
        )

        self.assertEqual(
            failures[0][0],
            "invalid_service_result",
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_lifecycle_signals_wrap_request(
        self,
    ):
        runtime = SpotifyQtPlaybackRuntime(
            lambda:
            ResultService(
                ready_result()
            )
        )

        events = []

        runtime.busy_changed.connect(
            lambda busy:
            events.append(
                (
                    "busy",
                    busy,
                )
            )
        )

        runtime.playback_started.connect(
            lambda uri:
            events.append(
                (
                    "started",
                    uri,
                )
            )
        )

        runtime.playback_finished.connect(
            lambda uri:
            events.append(
                (
                    "finished",
                    uri,
                )
            )
        )

        runtime.play_track(
            TRACK_URI
        )

        self.assertTrue(
            process_until(
                lambda:
                not runtime.busy
            )
        )

        self.assertIn(
            (
                "busy",
                True,
            ),
            events,
        )

        self.assertIn(
            (
                "started",
                TRACK_URI,
            ),
            events,
        )

        self.assertIn(
            (
                "busy",
                False,
            ),
            events,
        )

        self.assertIn(
            (
                "finished",
                TRACK_URI,
            ),
            events,
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_shutdown_blocks_new_playback(
        self,
    ):
        runtime = SpotifyQtPlaybackRuntime(
            lambda:
            ResultService(
                ready_result()
            )
        )

        self.assertTrue(
            runtime.shutdown()
        )

        with self.assertRaises(
            SpotifyQtPlaybackRuntimeError
        ) as caught:
            runtime.play_track(
                TRACK_URI
            )

        self.assertEqual(
            caught.exception.error_code,
            "shutting_down",
        )

    def test_invalid_runtime_uri_is_rejected_before_thread(
        self,
    ):
        runtime = SpotifyQtPlaybackRuntime(
            lambda:
            ResultService(
                ready_result()
            )
        )

        with self.assertRaises(
            ValueError
        ):
            runtime.play_track(
                "   "
            )

        self.assertFalse(
            runtime.busy
        )

        self.assertIsNone(
            runtime.active_uri
        )

        self.assertTrue(
            runtime.shutdown()
        )


    def test_playlist_position_request_runs_in_worker(
        self,
    ):
        service = ResultService(
            ready_result()
        )

        runtime = SpotifyQtPlaybackRuntime(
            lambda: service
        )

        runtime.play_playlist_position(
            "37i9dQZF1DXcBWIGoYBM5M",
            28,
        )

        self.assertTrue(
            process_until(
                lambda:
                (
                    service.position_calls
                    and not runtime.busy
                )
            )
        )

        self.assertEqual(
            service.position_calls,
            [
                (
                    "37i9dQZF1DXcBWIGoYBM5M",
                    28,
                ),
            ],
        )

        self.assertEqual(
            service.playlist_calls,
            [],
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_playlist_position_runs_off_calling_thread(
        self,
    ):
        worker_thread_ids = []

        service = ResultService(
            ready_result(),
            thread_ids=worker_thread_ids,
        )

        runtime = SpotifyQtPlaybackRuntime(
            lambda: service
        )

        calling_thread_id = (
            threading.get_ident()
        )

        runtime.play_playlist_position(
            "37i9dQZF1DXcBWIGoYBM5M",
            28,
        )

        self.assertTrue(
            process_until(
                lambda:
                (
                    worker_thread_ids
                    and not runtime.busy
                )
            )
        )

        self.assertNotEqual(
            worker_thread_ids[0],
            calling_thread_id,
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_playlist_position_lifecycle_uses_context_uri(
        self,
    ):
        runtime = SpotifyQtPlaybackRuntime(
            lambda:
            ResultService(
                ready_result()
            )
        )

        events = []

        context_uri = (
            "spotify:playlist:"
            "37i9dQZF1DXcBWIGoYBM5M"
        )

        runtime.playback_started.connect(
            lambda uri:
            events.append(
                (
                    "started",
                    uri,
                )
            )
        )

        runtime.playback_finished.connect(
            lambda uri:
            events.append(
                (
                    "finished",
                    uri,
                )
            )
        )

        runtime.play_playlist_position(
            "37i9dQZF1DXcBWIGoYBM5M",
            28,
        )

        self.assertTrue(
            process_until(
                lambda:
                not runtime.busy
            )
        )

        self.assertIn(
            (
                "started",
                context_uri,
            ),
            events,
        )

        self.assertIn(
            (
                "finished",
                context_uri,
            ),
            events,
        )

        self.assertIsNone(
            runtime.active_uri
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_playlist_position_rejects_invalid_position_before_thread(
        self,
    ):
        invalid_values = (
            (
                -1,
                ValueError,
            ),
            (
                True,
                TypeError,
            ),
            (
                False,
                TypeError,
            ),
            (
                1.5,
                TypeError,
            ),
            (
                "28",
                TypeError,
            ),
            (
                None,
                TypeError,
            ),
        )

        for (
            value,
            expected_error,
        ) in invalid_values:
            with self.subTest(
                value=value
            ):
                service = ResultService(
                    ready_result()
                )

                runtime = (
                    SpotifyQtPlaybackRuntime(
                        lambda: service
                    )
                )

                with self.assertRaises(
                    expected_error
                ):
                    runtime.play_playlist_position(
                        "37i9dQZF1DXcBWIGoYBM5M",
                        value,
                    )

                self.assertFalse(
                    runtime.busy
                )

                self.assertEqual(
                    service.position_calls,
                    [],
                )

                self.assertTrue(
                    runtime.shutdown()
                )

    def test_playlist_position_rejects_empty_playlist_before_thread(
        self,
    ):
        service = ResultService(
            ready_result()
        )

        runtime = SpotifyQtPlaybackRuntime(
            lambda: service
        )

        with self.assertRaises(
            ValueError
        ):
            runtime.play_playlist_position(
                "   ",
                28,
            )

        self.assertFalse(
            runtime.busy
        )

        self.assertEqual(
            service.position_calls,
            [],
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_playlist_context_request_runs_in_worker(
        self,
    ):
        service = ResultService(
            ready_result()
        )

        runtime = SpotifyQtPlaybackRuntime(
            lambda: service
        )

        runtime.play_playlist_track(
            "37i9dQZF1DXcBWIGoYBM5M",
            TRACK_URI,
        )

        self.assertTrue(
            process_until(
                lambda:
                (
                    service.playlist_calls
                    and not runtime.busy
                )
            )
        )

        self.assertEqual(
            service.playlist_calls,
            [
                (
                    "37i9dQZF1DXcBWIGoYBM5M",
                    TRACK_URI,
                ),
            ],
        )

        self.assertTrue(
            runtime.shutdown()
        )

if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
