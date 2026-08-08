from __future__ import annotations

from pathlib import Path
import threading
import time
import unittest

from PyQt6.QtCore import (
    QCoreApplication,
)

from src.spotify.qt_search_runtime import (
    SpotifyQtSearchRuntime,
    SpotifyQtSearchRuntimeError,
)
from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
    SpotifySearchPage,
    SpotifySearchResults,
)
from src.spotify.search_service import (
    SpotifySearchServiceResult,
    SpotifySearchServiceStatus,
)


def ready_result(
    query="query",
):
    item = SpotifySearchItem(
        item_type=(
            SpotifySearchItemType.TRACK
        ),
        spotify_id="track-1",
        name="Track One",
        uri=(
            "spotify:track:track-1"
        ),
        subtitle="Artist One",
    )

    page = SpotifySearchPage(
        item_type=(
            SpotifySearchItemType.TRACK
        ),
        items=(
            item,
        ),
        limit=5,
        offset=0,
        total=1,
    )

    results = SpotifySearchResults(
        query=query,
        pages=(
            page,
        ),
    )

    return SpotifySearchServiceResult(
        status=(
            SpotifySearchServiceStatus.READY
        ),
        results=results,
        message=(
            "Spotify search completed."
        ),
    )


def disconnected_result():
    return SpotifySearchServiceResult(
        status=(
            SpotifySearchServiceStatus
            .DISCONNECTED
        ),
        message=(
            "Connect Spotify before searching."
        ),
    )


class RecordingService:
    def __init__(
        self,
        *,
        result=None,
        error=None,
        entered_event=None,
        release_event=None,
    ):
        if result is None:
            result = ready_result()

        self.result = result
        self.error = error

        self.entered_event = (
            entered_event
        )

        self.release_event = (
            release_event
        )

        self.calls = []
        self.search_threads = []

    def search(
        self,
        query,
        *,
        types=None,
        limit=5,
        offset=0,
        market=None,
    ):
        self.search_threads.append(
            threading.get_ident()
        )

        self.calls.append(
            {
                "query": query,
                "types": types,
                "limit": limit,
                "offset": offset,
                "market": market,
            }
        )

        if self.entered_event is not None:
            self.entered_event.set()

        if self.release_event is not None:
            self.release_event.wait(
                5
            )

        if self.error is not None:
            raise self.error

        return self.result


class RecordingServiceFactory:
    def __init__(
        self,
        service,
    ):
        self.service = service

        self.calls = 0

        self.factory_threads = []

    def __call__(
        self,
    ):
        self.calls += 1

        self.factory_threads.append(
            threading.get_ident()
        )

        return self.service


class InvalidServiceFactory:
    def __call__(
        self,
    ):
        return object()


class RaisingFactory:
    def __call__(
        self,
    ):
        raise RuntimeError(
            "sensitive factory detail"
        )


class SpotifyQtSearchRuntimeTests(
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

    def make_runtime(
        self,
        factory,
        *,
        shutdown_wait_ms=11000,
    ):
        runtime = SpotifyQtSearchRuntime(
            factory,
            shutdown_wait_ms=(
                shutdown_wait_ms
            ),
        )

        self.addCleanup(
            runtime.shutdown
        )

        return runtime

    def wait_until(
        self,
        predicate,
        *,
        timeout=3.0,
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
                return

            time.sleep(
                0.005
            )

        self.app.processEvents()

        self.fail(
            "Timed out waiting for Qt runtime."
        )

    def wait_for_runtime(
        self,
        runtime,
        *,
        timeout=3.0,
    ):
        self.wait_until(
            lambda: not runtime.busy,
            timeout=timeout,
        )

    def test_search_runs_off_gui_thread(
        self,
    ):
        main_thread = (
            threading.get_ident()
        )

        service = RecordingService()

        factory = (
            RecordingServiceFactory(
                service
            )
        )

        runtime = self.make_runtime(
            factory
        )

        runtime.search(
            "query",
            types=(
                "track",
            ),
        )

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            factory.calls,
            1,
        )

        self.assertEqual(
            len(
                factory.factory_threads
            ),
            1,
        )

        self.assertNotEqual(
            factory.factory_threads[
                0
            ],
            main_thread,
        )

        self.assertEqual(
            len(
                service.search_threads
            ),
            1,
        )

        self.assertNotEqual(
            service.search_threads[
                0
            ],
            main_thread,
        )

    def test_ready_result_is_forwarded(
        self,
    ):
        expected = ready_result(
            "query"
        )

        runtime = self.make_runtime(
            RecordingServiceFactory(
                RecordingService(
                    result=expected
                )
            )
        )

        received = []

        runtime.result_ready.connect(
            received.append
        )

        runtime.search(
            "query"
        )

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            received,
            [
                expected,
            ],
        )

    def test_non_ready_service_result_is_forwarded(
        self,
    ):
        expected = (
            disconnected_result()
        )

        runtime = self.make_runtime(
            RecordingServiceFactory(
                RecordingService(
                    result=expected
                )
            )
        )

        received = []

        runtime.result_ready.connect(
            received.append
        )

        runtime.search(
            "query"
        )

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            received,
            [
                expected,
            ],
        )

        self.assertEqual(
            received[
                0
            ].status,
            (
                SpotifySearchServiceStatus
                .DISCONNECTED
            ),
        )

    def test_search_arguments_are_forwarded_exactly(
        self,
    ):
        service = RecordingService(
            result=ready_result(
                "Juice WRLD"
            )
        )

        runtime = self.make_runtime(
            RecordingServiceFactory(
                service
            )
        )

        runtime.search(
            "Juice WRLD",
            types=(
                SpotifySearchItemType.TRACK,
                "album",
            ),
            limit=10,
            offset=5,
            market="GB",
        )

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            service.calls,
            [
                {
                    "query": "Juice WRLD",
                    "types": (
                        SpotifySearchItemType.TRACK,
                        "album",
                    ),
                    "limit": 10,
                    "offset": 5,
                    "market": "GB",
                },
            ],
        )

    def test_busy_runtime_rejects_second_search(
        self,
    ):
        entered_event = (
            threading.Event()
        )

        release_event = (
            threading.Event()
        )

        service = RecordingService(
            entered_event=entered_event,
            release_event=release_event,
        )

        runtime = self.make_runtime(
            RecordingServiceFactory(
                service
            )
        )

        runtime.search(
            "first"
        )

        self.wait_until(
            entered_event.is_set
        )

        self.assertTrue(
            runtime.busy
        )

        with self.assertRaises(
            SpotifyQtSearchRuntimeError
        ) as context:
            runtime.search(
                "second"
            )

        self.assertEqual(
            context.exception.error_code,
            "busy",
        )

        release_event.set()

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            len(
                service.calls
            ),
            1,
        )

    def test_busy_and_lifecycle_signals_wrap_search(
        self,
    ):
        runtime = self.make_runtime(
            RecordingServiceFactory(
                RecordingService()
            )
        )

        busy_states = []
        started = []
        finished = []

        runtime.busy_changed.connect(
            busy_states.append
        )

        runtime.search_started.connect(
            started.append
        )

        runtime.search_finished.connect(
            finished.append
        )

        runtime.search(
            "  query  "
        )

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            busy_states,
            [
                True,
                False,
            ],
        )

        self.assertEqual(
            started,
            [
                "query",
            ],
        )

        self.assertEqual(
            finished,
            [
                "query",
            ],
        )

        self.assertIsNone(
            runtime.active_query
        )

    def test_invalid_request_failure_is_safe(
        self,
    ):
        service = RecordingService(
            error=ValueError(
                "sensitive invalid detail"
            )
        )

        runtime = self.make_runtime(
            RecordingServiceFactory(
                service
            )
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

        runtime.search(
            "query"
        )

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            failures[
                0
            ][
                0
            ],
            "invalid_request",
        )

        self.assertNotIn(
            "sensitive invalid detail",
            failures[
                0
            ][
                1
            ],
        )

    def test_unexpected_service_exception_is_safe(
        self,
    ):
        service = RecordingService(
            error=RuntimeError(
                "sensitive unexpected detail"
            )
        )

        runtime = self.make_runtime(
            RecordingServiceFactory(
                service
            )
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

        runtime.search(
            "query"
        )

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            failures[
                0
            ][
                0
            ],
            "operation_failed",
        )

        self.assertNotIn(
            "sensitive unexpected detail",
            failures[
                0
            ][
                1
            ],
        )

    def test_service_factory_exception_is_safe(
        self,
    ):
        runtime = self.make_runtime(
            RaisingFactory()
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

        runtime.search(
            "query"
        )

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            failures[
                0
            ][
                0
            ],
            "runtime_setup_failed",
        )

        self.assertNotIn(
            "sensitive factory detail",
            failures[
                0
            ][
                1
            ],
        )

    def test_service_without_search_is_rejected_safely(
        self,
    ):
        runtime = self.make_runtime(
            InvalidServiceFactory()
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

        runtime.search(
            "query"
        )

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            failures[
                0
            ][
                0
            ],
            "runtime_setup_failed",
        )

    def test_invalid_service_result_is_rejected(
        self,
    ):
        service = RecordingService(
            result="not-a-search-result"
        )

        runtime = self.make_runtime(
            RecordingServiceFactory(
                service
            )
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

        runtime.search(
            "query"
        )

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            failures,
            [
                (
                    "invalid_result",
                    (
                        "Spotify Search returned "
                        "an invalid result."
                    ),
                ),
            ],
        )

    def test_constructor_validates_inputs(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyQtSearchRuntime(
                object()
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyQtSearchRuntime(
                lambda: RecordingService(),
                shutdown_wait_ms=True,
            )

        with self.assertRaises(
            ValueError
        ):
            SpotifyQtSearchRuntime(
                lambda: RecordingService(),
                shutdown_wait_ms=0,
            )

        with self.assertRaises(
            ValueError
        ):
            SpotifyQtSearchRuntime(
                lambda: RecordingService(),
                shutdown_wait_ms=60001,
            )

    def test_shutdown_blocks_new_searches(
        self,
    ):
        runtime = self.make_runtime(
            RecordingServiceFactory(
                RecordingService()
            )
        )

        self.assertTrue(
            runtime.shutdown()
        )

        self.assertTrue(
            runtime.shutting_down
        )

        with self.assertRaises(
            SpotifyQtSearchRuntimeError
        ) as context:
            runtime.search(
                "query"
            )

        self.assertEqual(
            context.exception.error_code,
            "shutting_down",
        )

    def test_shutdown_waits_for_active_worker(
        self,
    ):
        entered_event = (
            threading.Event()
        )

        release_event = (
            threading.Event()
        )

        service = RecordingService(
            entered_event=entered_event,
            release_event=release_event,
        )

        runtime = self.make_runtime(
            RecordingServiceFactory(
                service
            ),
            shutdown_wait_ms=2000,
        )

        received = []

        runtime.result_ready.connect(
            received.append
        )

        runtime.search(
            "query"
        )

        self.wait_until(
            entered_event.is_set
        )

        def release():
            time.sleep(
                0.05
            )

            release_event.set()

        releaser = threading.Thread(
            target=release,
            daemon=True,
        )

        releaser.start()

        stopped = runtime.shutdown()

        releaser.join(
            timeout=1
        )

        self.assertTrue(
            stopped
        )

        self.assertFalse(
            runtime.busy
        )

        self.assertIsNone(
            runtime.active_query
        )

        self.assertEqual(
            received,
            [],
        )

    def test_runtime_can_complete_normal_search_before_shutdown(
        self,
    ):
        runtime = self.make_runtime(
            RecordingServiceFactory(
                RecordingService()
            )
        )

        runtime.search(
            "query"
        )

        self.wait_for_runtime(
            runtime
        )

        self.assertFalse(
            runtime.busy
        )

        self.assertIsNone(
            runtime.active_query
        )

        self.assertTrue(
            runtime.shutdown()
        )


class SpotifyQtSearchRuntimeBoundaryTests(
    unittest.TestCase
):
    def test_runtime_does_not_own_credentials_oauth_or_settings(
        self,
    ):
        root = (
            Path(
                __file__
            )
            .resolve()
            .parents[1]
        )

        source = (
            root
            / "src"
            / "spotify"
            / "qt_search_runtime.py"
        ).read_text(
            encoding="utf-8"
        )

        forbidden = (
            "SpotifyCredentialStore",
            "windows_dpapi",
            "spotify_auth.dat",
            "SpotifyOAuthSession",
            "QSettings",
            "client_secret",
            "refresh_token",
            "access_token",
            "urllib",
            "urlopen",
            "requests.",
            "print(",
            "logging.",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_runtime_uses_expected_qthread_worker_lifecycle(
        self,
    ):
        root = (
            Path(
                __file__
            )
            .resolve()
            .parents[1]
        )

        source = (
            root
            / "src"
            / "spotify"
            / "qt_search_runtime.py"
        ).read_text(
            encoding="utf-8"
        )

        required = (
            "QThread",
            "moveToThread",
            "thread.started.connect",
            "worker.finished.connect",
            "thread.quit",
            "thread.wait",
            "requestInterruption",
        )

        for marker in required:
            with self.subTest(
                marker=marker
            ):
                self.assertIn(
                    marker,
                    source,
                )

        self.assertNotIn(
            ".terminate(",
            source,
        )

    def test_runtime_only_exposes_credential_free_result_type(
        self,
    ):
        fields = (
            SpotifySearchServiceResult
            .__dataclass_fields__
        )

        for forbidden in (
            "token",
            "access_token",
            "refresh_token",
        ):
            self.assertNotIn(
                forbidden,
                fields,
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
