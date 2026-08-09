from __future__ import annotations

import time
import unittest

from PyQt6.QtCore import (
    QEventLoop,
    QThread,
    QTimer,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.liked_songs_service import (
    SpotifyLikedSongsServiceResult,
    SpotifyLikedSongsServiceStatus,
)
from src.spotify.qt_liked_songs_runtime import (
    SpotifyQtLikedSongsRuntime,
    SpotifyQtLikedSongsRuntimeError,
)


class ReadyService:
    def __init__(
        self,
        *,
        total=10,
        delay=0.0,
    ):
        self.total = total
        self.delay = delay
        self.thread = None

    def get_summary(
        self,
    ):
        self.thread = (
            QThread.currentThread()
        )

        if self.delay:
            time.sleep(
                self.delay
            )

        return SpotifyLikedSongsServiceResult(
            status=(
                SpotifyLikedSongsServiceStatus.READY
            ),
            total=self.total,
        )


class InvalidService:
    def get_summary(
        self,
    ):
        return object()


class SpotifyQtLikedSongsRuntimeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication(
                []
            )
        )

    def wait_for_signal(
        self,
        signal,
        action,
        *,
        timeout_ms=2500,
    ):
        loop = QEventLoop()
        values = []

        def handler(
            *args,
        ):
            values.append(
                args
            )

            loop.quit()

        signal.connect(
            handler
        )

        QTimer.singleShot(
            timeout_ms,
            loop.quit,
        )

        action()
        loop.exec()

        try:
            signal.disconnect(
                handler
            )
        except Exception:
            pass

        return values

    def test_constructor_requires_callable_factory(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyQtLikedSongsRuntime(
                None
            )

    def test_summary_result_is_forwarded_asynchronously(
        self,
    ):
        service = ReadyService(
            total=77
        )

        runtime = SpotifyQtLikedSongsRuntime(
            lambda: service
        )

        self.addCleanup(
            runtime.shutdown
        )

        values = self.wait_for_signal(
            runtime.summary_ready,
            runtime.load_summary,
        )

        self.assertEqual(
            len(values),
            1,
        )

        result = values[0][0]

        self.assertEqual(
            result.total,
            77,
        )

        self.assertIsNot(
            service.thread,
            QThread.currentThread(),
        )

    def test_busy_runtime_rejects_second_request(
        self,
    ):
        runtime = SpotifyQtLikedSongsRuntime(
            lambda: ReadyService(
                delay=0.1
            )
        )

        self.addCleanup(
            runtime.shutdown
        )

        runtime.load_summary()

        with self.assertRaises(
            SpotifyQtLikedSongsRuntimeError
        ):
            runtime.load_summary()

    def test_factory_exception_is_safe_failure(
        self,
    ):
        def broken_factory():
            raise RuntimeError(
                "simulated"
            )

        runtime = SpotifyQtLikedSongsRuntime(
            broken_factory
        )

        self.addCleanup(
            runtime.shutdown
        )

        values = self.wait_for_signal(
            runtime.failed,
            runtime.load_summary,
        )

        self.assertEqual(
            len(values),
            1,
        )

        self.assertEqual(
            values[0][0],
            "runtime_setup_failed",
        )

    def test_invalid_service_result_is_rejected(
        self,
    ):
        runtime = SpotifyQtLikedSongsRuntime(
            lambda: InvalidService()
        )

        self.addCleanup(
            runtime.shutdown
        )

        values = self.wait_for_signal(
            runtime.failed,
            runtime.load_summary,
        )

        self.assertEqual(
            len(values),
            1,
        )

        self.assertEqual(
            values[0][0],
            "invalid_result",
        )

    def test_busy_lifecycle_wraps_operation(
        self,
    ):
        runtime = SpotifyQtLikedSongsRuntime(
            lambda: ReadyService()
        )

        self.addCleanup(
            runtime.shutdown
        )

        states = []

        runtime.busy_changed.connect(
            states.append
        )

        values = self.wait_for_signal(
            runtime.operation_finished,
            runtime.load_summary,
        )

        self.assertEqual(
            len(values),
            1,
        )

        self.assertGreaterEqual(
            len(states),
            2,
        )

        self.assertTrue(
            states[0]
        )

        self.assertFalse(
            states[-1]
        )

    def test_idle_shutdown_succeeds(
        self,
    ):
        runtime = SpotifyQtLikedSongsRuntime(
            lambda: ReadyService()
        )

        self.assertTrue(
            runtime.shutdown()
        )

        self.assertFalse(
            runtime.busy
        )

    def test_shutdown_runtime_rejects_new_requests(
        self,
    ):
        runtime = SpotifyQtLikedSongsRuntime(
            lambda: ReadyService()
        )

        runtime.shutdown()

        with self.assertRaises(
            SpotifyQtLikedSongsRuntimeError
        ):
            runtime.load_summary()
