from __future__ import annotations

import threading
import time
import unittest

from PyQt6.QtCore import (
    QThread,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.queue_models import (
    SpotifyQueueSnapshot,
)
from src.spotify.queue_service import (
    SpotifyQueueServiceResult,
    SpotifyQueueServiceStatus,
)
from src.spotify.qt_queue_runtime import (
    SpotifyQtQueueRuntime,
    SpotifyQtQueueRuntimeError,
    _SpotifyQueueWorker,
)


def ready_result():
    return SpotifyQueueServiceResult(
        status=(
            SpotifyQueueServiceStatus.READY
        ),
        queue=SpotifyQueueSnapshot(
            currently_playing=None,
            items=(),
        ),
        message="Spotify Queue loaded.",
    )


class ReadyService:

    def __init__(
        self,
        *,
        started=None,
        release=None,
    ):
        self.started = started
        self.release = release
        self.thread = None
        self.calls = 0

    def get_queue(
        self,
    ):
        self.calls += 1

        self.thread = (
            QThread.currentThread()
        )

        if self.started is not None:
            self.started.set()

        if self.release is not None:
            self.release.wait(
                1.0
            )

        return ready_result()


class InvalidResultService:

    def get_queue(
        self,
    ):
        return object()


class MissingService:
    pass


class SpotifyQueueWorkerTests(
    unittest.TestCase
):

    def test_worker_forwards_valid_result(
        self,
    ):
        service = ReadyService()

        worker = _SpotifyQueueWorker(
            lambda: service
        )

        results = []
        failures = []
        finished = []

        worker.result_ready.connect(
            results.append
        )

        worker.failed.connect(
            lambda code, message:
            failures.append(
                (
                    code,
                    message,
                )
            )
        )

        worker.finished.connect(
            lambda:
            finished.append(
                True
            )
        )

        worker.run()

        self.assertEqual(
            len(results),
            1,
        )

        self.assertTrue(
            results[0].ready
        )

        self.assertEqual(
            failures,
            [],
        )

        self.assertEqual(
            finished,
            [
                True,
            ],
        )

    def test_worker_rejects_invalid_result(
        self,
    ):
        worker = _SpotifyQueueWorker(
            InvalidResultService
        )

        failures = []

        worker.failed.connect(
            lambda code, message:
            failures.append(
                (
                    code,
                    message,
                )
            )
        )

        worker.run()

        self.assertTrue(
            failures
        )

        self.assertEqual(
            failures[0][0],
            "invalid_result",
        )

    def test_worker_rejects_missing_service_method(
        self,
    ):
        worker = _SpotifyQueueWorker(
            MissingService
        )

        failures = []

        worker.failed.connect(
            lambda code, message:
            failures.append(
                (
                    code,
                    message,
                )
            )
        )

        worker.run()

        self.assertTrue(
            failures
        )

        self.assertEqual(
            failures[0][0],
            "invalid_service",
        )

    def test_worker_wraps_factory_exception(
        self,
    ):
        def broken_factory():
            raise RuntimeError(
                "boom"
            )

        worker = _SpotifyQueueWorker(
            broken_factory
        )

        failures = []

        worker.failed.connect(
            lambda code, message:
            failures.append(
                (
                    code,
                    message,
                )
            )
        )

        worker.run()

        self.assertTrue(
            failures
        )

        self.assertEqual(
            failures[0][0],
            "service_error",
        )


class SpotifyQtQueueRuntimeTests(
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

    def test_result_is_forwarded_asynchronously(
        self,
    ):
        service = ReadyService()

        runtime = SpotifyQtQueueRuntime(
            lambda: service
        )

        self.addCleanup(
            runtime.shutdown
        )

        results = []

        runtime.queue_ready.connect(
            results.append
        )

        runtime.load_queue()

        self.assertTrue(
            self.wait_until(
                lambda:
                bool(results)
                and not runtime.busy
            )
        )

        self.assertEqual(
            len(results),
            1,
        )

        self.assertTrue(
            results[0].ready
        )

        self.assertIsNot(
            service.thread,
            QThread.currentThread(),
        )

    def test_busy_runtime_rejects_second_request(
        self,
    ):
        started = threading.Event()
        release = threading.Event()

        service = ReadyService(
            started=started,
            release=release,
        )

        runtime = SpotifyQtQueueRuntime(
            lambda: service
        )

        self.addCleanup(
            runtime.shutdown
        )

        self.addCleanup(
            release.set
        )

        runtime.load_queue()

        self.assertTrue(
            started.wait(
                1.0
            )
        )

        with self.assertRaises(
            SpotifyQtQueueRuntimeError
        ) as caught:
            runtime.load_queue()

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

    def test_busy_lifecycle_wraps_operation(
        self,
    ):
        runtime = SpotifyQtQueueRuntime(
            ReadyService
        )

        self.addCleanup(
            runtime.shutdown
        )

        states = []
        started = []
        finished = []

        runtime.busy_changed.connect(
            states.append
        )

        runtime.operation_started.connect(
            lambda:
            started.append(
                True
            )
        )

        runtime.operation_finished.connect(
            lambda:
            finished.append(
                True
            )
        )

        runtime.load_queue()

        self.assertTrue(
            self.wait_until(
                lambda:
                bool(finished)
                and not runtime.busy
            )
        )

        self.assertEqual(
            started,
            [
                True,
            ],
        )

        self.assertEqual(
            finished,
            [
                True,
            ],
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

    def test_runtime_forwards_worker_failure(
        self,
    ):
        runtime = SpotifyQtQueueRuntime(
            InvalidResultService
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

        runtime.load_queue()

        self.assertTrue(
            self.wait_until(
                lambda:
                bool(failures)
                and not runtime.busy
            )
        )

        self.assertEqual(
            failures[0][0],
            "invalid_result",
        )

    def test_idle_shutdown_succeeds(
        self,
    ):
        runtime = SpotifyQtQueueRuntime(
            ReadyService
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
        runtime = SpotifyQtQueueRuntime(
            ReadyService
        )

        self.assertTrue(
            runtime.shutdown()
        )

        with self.assertRaises(
            SpotifyQtQueueRuntimeError
        ) as caught:
            runtime.load_queue()

        self.assertEqual(
            caught.exception.error_code,
            "shutting_down",
        )

    def test_constructor_requires_callable_factory(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyQtQueueRuntime(
                object()
            )


if __name__ == "__main__":
    unittest.main()
