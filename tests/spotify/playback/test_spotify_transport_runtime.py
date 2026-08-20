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


def ready_result(
    message="ready",
):
    return SpotifyPlaybackServiceResult(
        status=(
            SpotifyPlaybackServiceStatus.READY
        ),
        message=message,
    )


def process_until(
    predicate,
    *,
    timeout=3.0,
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
            app.processEvents()
            return True

        time.sleep(
            0.01
        )

    app.processEvents()

    return bool(
        predicate()
    )


class TransportService:
    def __init__(
        self,
        *,
        result=None,
        thread_ids=None,
    ):
        self.result = (
            result
            if result is not None
            else ready_result()
        )

        self.thread_ids = (
            thread_ids
            if thread_ids is not None
            else []
        )

        self.calls = []

    def _run(
        self,
        name,
    ):
        self.calls.append(
            name
        )

        self.thread_ids.append(
            threading.get_ident()
        )

        return self.result

    def resume_playback(
        self,
    ):
        return self._run(
            "resume_playback"
        )

    def pause_playback(
        self,
    ):
        return self._run(
            "pause_playback"
        )

    def skip_next(
        self,
    ):
        return self._run(
            "skip_next"
        )

    def skip_previous(
        self,
    ):
        return self._run(
            "skip_previous"
        )


class MixedService(
    TransportService
):
    def __init__(
        self,
        *,
        transport_started=None,
        transport_release=None,
        playback_started=None,
        playback_release=None,
    ):
        super().__init__()

        self.transport_started = (
            transport_started
        )

        self.transport_release = (
            transport_release
        )

        self.playback_started = (
            playback_started
        )

        self.playback_release = (
            playback_release
        )

    def resume_playback(
        self,
    ):
        if (
            self.transport_started
            is not None
        ):
            self.transport_started.set()

        if (
            self.transport_release
            is not None
        ):
            self.transport_release.wait(
                2.0
            )

        return super().resume_playback()

    def play_track(
        self,
        spotify_uri,
    ):
        del spotify_uri

        if (
            self.playback_started
            is not None
        ):
            self.playback_started.set()

        if (
            self.playback_release
            is not None
        ):
            self.playback_release.wait(
                2.0
            )

        self.calls.append(
            "play_track"
        )

        self.thread_ids.append(
            threading.get_ident()
        )

        return ready_result()


class MissingControlService:
    def play_track(
        self,
        spotify_uri,
    ):
        del spotify_uri
        return ready_result()


class InvalidResultService:
    def resume_playback(
        self,
    ):
        return object()


class SpotifyTransportRuntimeTests(
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

    def wait_until(
        self,
        predicate,
    ):
        self.assertTrue(
            process_until(
                predicate
            )
        )

    def test_all_controls_dispatch_in_worker_thread(
        self,
    ):
        caller = (
            threading.get_ident()
        )

        worker_threads = []

        service = TransportService(
            thread_ids=worker_threads
        )

        runtime = (
            SpotifyQtPlaybackRuntime(
                lambda: service
            )
        )

        self.addCleanup(
            runtime.shutdown
        )

        methods = (
            "resume_playback",
            "pause_playback",
            "skip_next",
            "skip_previous",
        )

        for name in methods:
            getattr(
                runtime,
                name,
            )()

            self.assertTrue(
                runtime.busy
            )

            self.wait_until(
                lambda:
                not runtime.busy
            )

        self.assertEqual(
            service.calls,
            list(methods),
        )

        self.assertEqual(
            len(worker_threads),
            4,
        )

        self.assertTrue(
            all(
                thread_id != caller
                for thread_id
                in worker_threads
            )
        )

    def test_control_result_is_forwarded(
        self,
    ):
        expected = ready_result(
            "transport ready"
        )

        runtime = (
            SpotifyQtPlaybackRuntime(
                lambda:
                TransportService(
                    result=expected
                )
            )
        )

        self.addCleanup(
            runtime.shutdown
        )

        results = []

        runtime.result_ready.connect(
            results.append
        )

        runtime.pause_playback()

        self.wait_until(
            lambda:
            not runtime.busy
        )

        self.assertEqual(
            results,
            [
                expected,
            ],
        )

    def test_control_lifecycle_has_separate_signals(
        self,
    ):
        runtime = (
            SpotifyQtPlaybackRuntime(
                lambda:
                TransportService()
            )
        )

        self.addCleanup(
            runtime.shutdown
        )

        events = []
        playback_finished = []

        runtime.busy_changed.connect(
            lambda busy:
            events.append(
                (
                    "busy",
                    busy,
                )
            )
        )

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

        runtime.playback_finished.connect(
            playback_finished.append
        )

        runtime.skip_next()

        self.wait_until(
            lambda:
            not runtime.busy
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
                "skip_next",
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
                "skip_next",
            ),
            events,
        )

        self.assertEqual(
            playback_finished,
            [],
        )

    def test_busy_control_rejects_second_control(
        self,
    ):
        started = threading.Event()
        release = threading.Event()

        service = MixedService(
            transport_started=started,
            transport_release=release,
        )

        runtime = (
            SpotifyQtPlaybackRuntime(
                lambda: service
            )
        )

        self.addCleanup(
            release.set
        )

        self.addCleanup(
            runtime.shutdown
        )

        runtime.resume_playback()

        self.assertTrue(
            started.wait(
                1.0
            )
        )

        with self.assertRaises(
            SpotifyQtPlaybackRuntimeError
        ) as caught:
            runtime.skip_next()

        self.assertEqual(
            caught.exception.error_code,
            "busy",
        )

        release.set()

        self.wait_until(
            lambda:
            not runtime.busy
        )

    def test_busy_control_rejects_track_playback(
        self,
    ):
        started = threading.Event()
        release = threading.Event()

        service = MixedService(
            transport_started=started,
            transport_release=release,
        )

        runtime = (
            SpotifyQtPlaybackRuntime(
                lambda: service
            )
        )

        self.addCleanup(
            release.set
        )

        self.addCleanup(
            runtime.shutdown
        )

        runtime.resume_playback()

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

        self.wait_until(
            lambda:
            not runtime.busy
        )

    def test_busy_track_playback_rejects_control(
        self,
    ):
        started = threading.Event()
        release = threading.Event()

        service = MixedService(
            playback_started=started,
            playback_release=release,
        )

        runtime = (
            SpotifyQtPlaybackRuntime(
                lambda: service
            )
        )

        self.addCleanup(
            release.set
        )

        self.addCleanup(
            runtime.shutdown
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
            runtime.pause_playback()

        self.assertEqual(
            caught.exception.error_code,
            "busy",
        )

        release.set()

        self.wait_until(
            lambda:
            not runtime.busy
        )

    def test_shutdown_blocks_transport_control(
        self,
    ):
        runtime = (
            SpotifyQtPlaybackRuntime(
                lambda:
                TransportService()
            )
        )

        self.assertTrue(
            runtime.shutdown()
        )

        with self.assertRaises(
            SpotifyQtPlaybackRuntimeError
        ) as caught:
            runtime.resume_playback()

        self.assertEqual(
            caught.exception.error_code,
            "shutting_down",
        )

    def test_missing_control_service_method_is_safe(
        self,
    ):
        runtime = (
            SpotifyQtPlaybackRuntime(
                lambda:
                MissingControlService()
            )
        )

        self.addCleanup(
            runtime.shutdown
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

        runtime.resume_playback()

        self.wait_until(
            lambda:
            not runtime.busy
        )

        self.assertTrue(
            failures
        )

        self.assertEqual(
            failures[0][0],
            "invalid_service",
        )

    def test_invalid_control_result_is_safe(
        self,
    ):
        runtime = (
            SpotifyQtPlaybackRuntime(
                lambda:
                InvalidResultService()
            )
        )

        self.addCleanup(
            runtime.shutdown
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

        runtime.resume_playback()

        self.wait_until(
            lambda:
            not runtime.busy
        )

        self.assertTrue(
            failures
        )

        self.assertEqual(
            failures[0][0],
            "invalid_service_result",
        )

    def test_control_service_factory_exception_is_safe(
        self,
    ):
        def factory():
            raise RuntimeError(
                "simulated setup failure"
            )

        runtime = (
            SpotifyQtPlaybackRuntime(
                factory
            )
        )

        self.addCleanup(
            runtime.shutdown
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

        runtime.skip_previous()

        self.wait_until(
            lambda:
            not runtime.busy
        )

        self.assertTrue(
            failures
        )

        self.assertEqual(
            failures[0][0],
            "runtime_setup_failed",
        )


if __name__ == "__main__":
    unittest.main()
