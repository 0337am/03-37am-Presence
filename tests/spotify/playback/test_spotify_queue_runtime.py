from __future__ import annotations

import threading
import time
import unittest

from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.playback_service import (
    SpotifyPlaybackServiceResult,
    SpotifyPlaybackServiceStatus,
)
from src.spotify.qt_playback_runtime import (
    SPOTIFY_PLAYBACK_CONTROL_METHODS,
    SpotifyQtPlaybackRuntime,
    SpotifyQtPlaybackRuntimeError,
)


TRACK_URI = "spotify:track:track123"
EPISODE_URI = "spotify:episode:episode456"


def ready_result():
    return SpotifyPlaybackServiceResult(
        status=(
            SpotifyPlaybackServiceStatus.READY
        ),
        message=(
            "Spotify item added to Queue."
        ),
    )


class RuntimeHarness:

    def __init__(
        self,
    ):
        self.calls = []

    def _start_control(
        self,
        control_name,
        *,
        control_argument=None,
    ):
        self.calls.append(
            (
                control_name,
                control_argument,
            )
        )


class RuntimeQueueService:

    def __init__(
        self,
        *,
        started=None,
        release=None,
    ):
        self.started = started
        self.release = release
        self.calls = []
        self.thread_ids = []

    def add_to_queue(
        self,
        spotify_uri,
    ):
        self.calls.append(
            spotify_uri
        )

        self.thread_ids.append(
            threading.get_ident()
        )

        if self.started is not None:
            self.started.set()

        if self.release is not None:
            self.release.wait(
                1.0
            )

        return ready_result()


class SpotifyQueuePlaybackRuntimeTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
        app = QApplication.instance()

        if app is None:
            app = QApplication([])

        cls.app = app

    def wait_until(
        self,
        predicate,
        *,
        timeout=2.5,
    ):
        deadline = (
            time.monotonic()
            + timeout
        )

        while (
            time.monotonic()
            < deadline
        ):
            self.app.processEvents()

            if predicate():
                return True

            time.sleep(
                0.005
            )

        self.app.processEvents()

        return bool(
            predicate()
        )

    def test_registry_contains_add_to_queue(
        self,
    ):
        self.assertIn(
            "add_to_queue",
            SPOTIFY_PLAYBACK_CONTROL_METHODS,
        )

    def test_track_uri_routes_to_control_worker(
        self,
    ):
        harness = RuntimeHarness()

        SpotifyQtPlaybackRuntime.add_to_queue(
            harness,
            TRACK_URI,
        )

        self.assertEqual(
            harness.calls,
            [
                (
                    "add_to_queue",
                    TRACK_URI,
                ),
            ],
        )

    def test_episode_uri_routes_to_control_worker(
        self,
    ):
        harness = RuntimeHarness()

        SpotifyQtPlaybackRuntime.add_to_queue(
            harness,
            EPISODE_URI,
        )

        self.assertEqual(
            harness.calls,
            [
                (
                    "add_to_queue",
                    EPISODE_URI,
                ),
            ],
        )

    def test_invalid_queue_uri_is_rejected_before_control(
        self,
    ):
        harness = RuntimeHarness()

        for value in (
            "",
            "spotify:album:album123",
            (
                "spotify:local:"
                "Artist:Album:Song:180"
            ),
            " spotify:track:track123",
            "spotify:track:track123 ",
            "spotify:track:bad-id",
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    ValueError
                ):
                    SpotifyQtPlaybackRuntime.add_to_queue(
                        harness,
                        value,
                    )

        self.assertEqual(
            harness.calls,
            [],
        )

    def test_queue_uri_type_is_rejected_before_control(
        self,
    ):
        harness = RuntimeHarness()

        for value in (
            None,
            123,
            object(),
        ):
            with self.subTest(
                value=type(
                    value
                ).__name__
            ):
                with self.assertRaises(
                    TypeError
                ):
                    SpotifyQtPlaybackRuntime.add_to_queue(
                        harness,
                        value,
                    )

        self.assertEqual(
            harness.calls,
            [],
        )

    def test_add_to_queue_runs_off_calling_thread_and_forwards_result(
        self,
    ):
        caller = threading.get_ident()

        service = RuntimeQueueService()

        runtime = SpotifyQtPlaybackRuntime(
            lambda: service
        )

        self.addCleanup(
            runtime.shutdown
        )

        results = []

        runtime.result_ready.connect(
            results.append
        )

        runtime.add_to_queue(
            TRACK_URI
        )

        self.assertTrue(
            runtime.busy
        )

        self.assertTrue(
            self.wait_until(
                lambda:
                bool(results)
                and not runtime.busy
            )
        )

        self.assertEqual(
            service.calls,
            [
                TRACK_URI,
            ],
        )

        self.assertEqual(
            len(
                service.thread_ids
            ),
            1,
        )

        self.assertNotEqual(
            service.thread_ids[0],
            caller,
        )

        self.assertTrue(
            results[0].ready
        )

    def test_add_to_queue_uses_control_lifecycle_signals(
        self,
    ):
        runtime = SpotifyQtPlaybackRuntime(
            RuntimeQueueService
        )

        self.addCleanup(
            runtime.shutdown
        )

        events = []

        runtime.control_started.connect(
            lambda name:
            events.append(
                (
                    "started",
                    name,
                )
            )
        )

        runtime.control_finished.connect(
            lambda name:
            events.append(
                (
                    "finished",
                    name,
                )
            )
        )

        runtime.add_to_queue(
            EPISODE_URI
        )

        self.assertTrue(
            self.wait_until(
                lambda:
                not runtime.busy
            )
        )

        self.assertIn(
            (
                "started",
                "add_to_queue",
            ),
            events,
        )

        self.assertIn(
            (
                "finished",
                "add_to_queue",
            ),
            events,
        )

    def test_busy_runtime_rejects_second_queue_control(
        self,
    ):
        started = threading.Event()
        release = threading.Event()

        service = RuntimeQueueService(
            started=started,
            release=release,
        )

        runtime = SpotifyQtPlaybackRuntime(
            lambda: service
        )

        self.addCleanup(
            release.set
        )

        self.addCleanup(
            runtime.shutdown
        )

        runtime.add_to_queue(
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
            runtime.add_to_queue(
                EPISODE_URI
            )

        self.assertEqual(
            caught.exception.error_code,
            "busy",
        )

        release.set()

        self.assertTrue(
            self.wait_until(
                lambda:
                not runtime.busy
            )
        )

    def test_shutdown_blocks_queue_control(
        self,
    ):
        runtime = SpotifyQtPlaybackRuntime(
            RuntimeQueueService
        )

        self.assertTrue(
            runtime.shutdown()
        )

        with self.assertRaises(
            SpotifyQtPlaybackRuntimeError
        ) as caught:
            runtime.add_to_queue(
                TRACK_URI
            )

        self.assertEqual(
            caught.exception.error_code,
            "shutting_down",
        )


if __name__ == "__main__":
    unittest.main()
