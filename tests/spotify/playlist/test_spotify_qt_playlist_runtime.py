from __future__ import annotations

import inspect
import threading
import time
import unittest

from PyQt6.QtCore import (
    QCoreApplication,
)

import src.spotify.qt_playlist_runtime as runtime_module
from src.spotify.playlist_service import (
    SpotifyPlaylistServiceResult,
)
from src.spotify.qt_playlist_runtime import (
    OPERATION_PLAYLISTS,
    OPERATION_PLAYLIST_ITEMS,
    SpotifyQtPlaylistRuntime,
    SpotifyQtPlaylistRuntimeError,
)
from src.spotify.resolved_playlist_service import (
    SpotifyResolvedPlaylistServiceResult,
)


def fake_playlist_result():
    return object.__new__(
        SpotifyPlaylistServiceResult
    )


def fake_resolved_result():
    return object.__new__(
        SpotifyResolvedPlaylistServiceResult
    )


class SpotifyQtPlaylistRuntimeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QCoreApplication.instance()
            or QCoreApplication(
                []
            )
        )

    def wait_until(
        self,
        predicate,
        *,
        timeout=2.0,
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

    def make_runtime(
        self,
        playlist_factory,
        resolved_factory,
        **kwargs,
    ):
        runtime = SpotifyQtPlaylistRuntime(
            playlist_factory,
            resolved_factory,
            **kwargs,
        )

        self.addCleanup(
            runtime.shutdown
        )

        return runtime

    def test_playlist_list_runs_off_gui_thread(
        self,
    ):
        result = fake_playlist_result()
        main_thread_id = (
            threading.get_ident()
        )

        seen = {}

        class Service:
            def get_current_playlists(
                self,
                *,
                limit,
                offset,
            ):
                seen["thread_id"] = (
                    threading.get_ident()
                )

                return result

        received = []

        runtime = self.make_runtime(
            lambda: Service(),
            lambda: object(),
        )

        runtime.playlists_ready.connect(
            received.append
        )

        runtime.load_playlists()

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    received
                )
            )
        )

        self.assertNotEqual(
            seen["thread_id"],
            main_thread_id,
        )

    def test_playlist_items_run_off_gui_thread(
        self,
    ):
        result = fake_resolved_result()
        main_thread_id = (
            threading.get_ident()
        )

        seen = {}

        class Service:
            def get_playlist_items(
                self,
                playlist_id,
                *,
                limit,
                offset,
                market,
            ):
                seen["thread_id"] = (
                    threading.get_ident()
                )

                return result

        received = []

        runtime = self.make_runtime(
            lambda: object(),
            lambda: Service(),
        )

        runtime.playlist_items_ready.connect(
            lambda playlist_id, value:
            received.append(
                (
                    playlist_id,
                    value,
                )
            )
        )

        runtime.load_playlist_items(
            "playlist-1"
        )

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    received
                )
            )
        )

        self.assertNotEqual(
            seen["thread_id"],
            main_thread_id,
        )

    def test_playlist_list_result_is_forwarded(
        self,
    ):
        result = fake_playlist_result()

        class Service:
            def get_current_playlists(
                self,
                *,
                limit,
                offset,
            ):
                return result

        received = []

        runtime = self.make_runtime(
            lambda: Service(),
            lambda: object(),
        )

        runtime.playlists_ready.connect(
            received.append
        )

        runtime.load_playlists()

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    received
                )
            )
        )

        self.assertIs(
            received[0],
            result,
        )

    def test_resolved_items_result_is_forwarded(
        self,
    ):
        result = fake_resolved_result()

        class Service:
            def get_playlist_items(
                self,
                playlist_id,
                *,
                limit,
                offset,
                market,
            ):
                return result

        received = []

        runtime = self.make_runtime(
            lambda: object(),
            lambda: Service(),
        )

        runtime.playlist_items_ready.connect(
            lambda playlist_id, value:
            received.append(
                (
                    playlist_id,
                    value,
                )
            )
        )

        runtime.load_playlist_items(
            "abc123"
        )

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    received
                )
            )
        )

        self.assertEqual(
            received[0][0],
            "abc123",
        )

        self.assertIs(
            received[0][1],
            result,
        )

    def test_playlist_list_arguments_are_forwarded_exactly(
        self,
    ):
        result = fake_playlist_result()
        seen = {}

        class Service:
            def get_current_playlists(
                self,
                *,
                limit,
                offset,
            ):
                seen["limit"] = limit
                seen["offset"] = offset
                return result

        runtime = self.make_runtime(
            lambda: Service(),
            lambda: object(),
        )

        received = []

        runtime.playlists_ready.connect(
            received.append
        )

        runtime.load_playlists(
            limit=17,
            offset=34,
        )

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    received
                )
            )
        )

        self.assertEqual(
            seen,
            {
                "limit": 17,
                "offset": 34,
            },
        )

    def test_playlist_item_arguments_are_forwarded_exactly(
        self,
    ):
        result = fake_resolved_result()
        seen = {}

        class Service:
            def get_playlist_items(
                self,
                playlist_id,
                *,
                limit,
                offset,
                market,
            ):
                seen.update(
                    {
                        "playlist_id": (
                            playlist_id
                        ),
                        "limit": limit,
                        "offset": offset,
                        "market": market,
                    }
                )

                return result

        runtime = self.make_runtime(
            lambda: object(),
            lambda: Service(),
        )

        received = []

        runtime.playlist_items_ready.connect(
            lambda playlist_id, value:
            received.append(
                value
            )
        )

        runtime.load_playlist_items(
            "  playlist-id  ",
            limit=23,
            offset=46,
            market="GB",
        )

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    received
                )
            )
        )

        self.assertEqual(
            seen,
            {
                "playlist_id": (
                    "playlist-id"
                ),
                "limit": 23,
                "offset": 46,
                "market": "GB",
            },
        )

    def test_busy_runtime_rejects_second_operation(
        self,
    ):
        result = fake_playlist_result()
        entered = threading.Event()
        release = threading.Event()

        class Service:
            def get_current_playlists(
                self,
                *,
                limit,
                offset,
            ):
                entered.set()

                release.wait(
                    1.0
                )

                return result

        runtime = self.make_runtime(
            lambda: Service(),
            lambda: object(),
        )

        runtime.load_playlists()

        self.assertTrue(
            entered.wait(
                1.0
            )
        )

        with self.assertRaises(
            SpotifyQtPlaylistRuntimeError
        ) as context:
            runtime.load_playlists()

        self.assertEqual(
            context.exception.error_code,
            "busy",
        )

        release.set()

        self.assertTrue(
            self.wait_until(
                lambda: not runtime.busy
            )
        )

    def test_busy_and_lifecycle_signals_wrap_operation(
        self,
    ):
        result = fake_playlist_result()
        events = []

        class Service:
            def get_current_playlists(
                self,
                *,
                limit,
                offset,
            ):
                return result

        runtime = self.make_runtime(
            lambda: Service(),
            lambda: object(),
        )

        runtime.busy_changed.connect(
            lambda value:
            events.append(
                (
                    "busy",
                    value,
                )
            )
        )

        runtime.operation_started.connect(
            lambda operation, target:
            events.append(
                (
                    "started",
                    operation,
                    target,
                )
            )
        )

        runtime.playlists_ready.connect(
            lambda value:
            events.append(
                (
                    "result",
                    value,
                )
            )
        )

        runtime.operation_finished.connect(
            lambda operation, target:
            events.append(
                (
                    "finished",
                    operation,
                    target,
                )
            )
        )

        runtime.load_playlists()

        self.assertTrue(
            self.wait_until(
                lambda: (
                    not runtime.busy
                    and any(
                        event[0]
                        == "finished"
                        for event in events
                    )
                )
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
                OPERATION_PLAYLISTS,
                "",
            ),
            events,
        )

        self.assertIn(
            (
                "result",
                result,
            ),
            events,
        )

        self.assertIn(
            (
                "finished",
                OPERATION_PLAYLISTS,
                "",
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

    def test_invalid_request_failure_is_safe(
        self,
    ):
        class Service:
            def get_current_playlists(
                self,
                *,
                limit,
                offset,
            ):
                raise ValueError(
                    "simulated"
                )

        failures = []

        runtime = self.make_runtime(
            lambda: Service(),
            lambda: object(),
        )

        runtime.failed.connect(
            lambda *values:
            failures.append(
                values
            )
        )

        runtime.load_playlists(
            limit=-1
        )

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    failures
                )
            )
        )

        self.assertEqual(
            failures[0][2],
            "invalid_request",
        )

    def test_unexpected_service_exception_is_safe(
        self,
    ):
        class Service:
            def get_current_playlists(
                self,
                *,
                limit,
                offset,
            ):
                raise RuntimeError(
                    "simulated"
                )

        failures = []

        runtime = self.make_runtime(
            lambda: Service(),
            lambda: object(),
        )

        runtime.failed.connect(
            lambda *values:
            failures.append(
                values
            )
        )

        runtime.load_playlists()

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    failures
                )
            )
        )

        self.assertEqual(
            failures[0][2],
            "operation_failed",
        )

    def test_playlist_service_factory_exception_is_safe(
        self,
    ):
        def factory():
            raise RuntimeError(
                "simulated"
            )

        failures = []

        runtime = self.make_runtime(
            factory,
            lambda: object(),
        )

        runtime.failed.connect(
            lambda *values:
            failures.append(
                values
            )
        )

        runtime.load_playlists()

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    failures
                )
            )
        )

        self.assertEqual(
            failures[0][2],
            "runtime_setup_failed",
        )

    def test_resolved_service_factory_exception_is_safe(
        self,
    ):
        def factory():
            raise RuntimeError(
                "simulated"
            )

        failures = []

        runtime = self.make_runtime(
            lambda: object(),
            factory,
        )

        runtime.failed.connect(
            lambda *values:
            failures.append(
                values
            )
        )

        runtime.load_playlist_items(
            "playlist-id"
        )

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    failures
                )
            )
        )

        self.assertEqual(
            failures[0][2],
            "runtime_setup_failed",
        )

    def test_service_without_required_method_is_rejected_safely(
        self,
    ):
        failures = []

        runtime = self.make_runtime(
            lambda: object(),
            lambda: object(),
        )

        runtime.failed.connect(
            lambda *values:
            failures.append(
                values
            )
        )

        runtime.load_playlists()

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    failures
                )
            )
        )

        self.assertEqual(
            failures[0][2],
            "runtime_setup_failed",
        )

    def test_invalid_playlist_list_result_is_rejected(
        self,
    ):
        class Service:
            def get_current_playlists(
                self,
                *,
                limit,
                offset,
            ):
                return object()

        failures = []

        runtime = self.make_runtime(
            lambda: Service(),
            lambda: object(),
        )

        runtime.failed.connect(
            lambda *values:
            failures.append(
                values
            )
        )

        runtime.load_playlists()

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    failures
                )
            )
        )

        self.assertEqual(
            failures[0][2],
            "invalid_result",
        )

    def test_invalid_resolved_result_is_rejected(
        self,
    ):
        class Service:
            def get_playlist_items(
                self,
                playlist_id,
                *,
                limit,
                offset,
                market,
            ):
                return object()

        failures = []

        runtime = self.make_runtime(
            lambda: object(),
            lambda: Service(),
        )

        runtime.failed.connect(
            lambda *values:
            failures.append(
                values
            )
        )

        runtime.load_playlist_items(
            "playlist-id"
        )

        self.assertTrue(
            self.wait_until(
                lambda: bool(
                    failures
                )
            )
        )

        self.assertEqual(
            failures[0][2],
            "invalid_result",
        )

    def test_constructor_and_playlist_id_validate_inputs(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyQtPlaylistRuntime(
                None,
                lambda: object(),
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyQtPlaylistRuntime(
                lambda: object(),
                None,
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyQtPlaylistRuntime(
                lambda: object(),
                lambda: object(),
                shutdown_wait_ms=True,
            )

        with self.assertRaises(
            ValueError
        ):
            SpotifyQtPlaylistRuntime(
                lambda: object(),
                lambda: object(),
                shutdown_wait_ms=-1,
            )

        runtime = self.make_runtime(
            lambda: object(),
            lambda: object(),
        )

        with self.assertRaises(
            TypeError
        ):
            runtime.load_playlist_items(
                None
            )

        with self.assertRaises(
            ValueError
        ):
            runtime.load_playlist_items(
                "   "
            )

    def test_shutdown_blocks_new_operations(
        self,
    ):
        runtime = self.make_runtime(
            lambda: object(),
            lambda: object(),
        )

        self.assertTrue(
            runtime.shutdown()
        )

        self.assertTrue(
            runtime.shutting_down
        )

        with self.assertRaises(
            SpotifyQtPlaylistRuntimeError
        ) as context:
            runtime.load_playlists()

        self.assertEqual(
            context.exception.error_code,
            "shutting_down",
        )

    def test_shutdown_waits_for_active_worker(
        self,
    ):
        result = fake_playlist_result()

        entered = threading.Event()
        release = threading.Event()

        class Service:
            def get_current_playlists(
                self,
                *,
                limit,
                offset,
            ):
                entered.set()

                release.wait(
                    1.0
                )

                return result

        runtime = SpotifyQtPlaylistRuntime(
            lambda: Service(),
            lambda: object(),
            shutdown_wait_ms=2000,
        )

        runtime.load_playlists()

        self.assertTrue(
            entered.wait(
                1.0
            )
        )

        timer = threading.Timer(
            0.05,
            release.set,
        )

        timer.start()

        try:
            self.assertTrue(
                runtime.shutdown()
            )

        finally:
            release.set()
            timer.cancel()

        self.assertFalse(
            runtime.busy
        )

        self.assertTrue(
            runtime.shutting_down
        )

    def test_runtime_can_complete_normal_operation_before_shutdown(
        self,
    ):
        result = fake_playlist_result()

        class Service:
            def get_current_playlists(
                self,
                *,
                limit,
                offset,
            ):
                return result

        runtime = SpotifyQtPlaylistRuntime(
            lambda: Service(),
            lambda: object(),
        )

        received = []

        runtime.playlists_ready.connect(
            received.append
        )

        runtime.load_playlists()

        self.assertTrue(
            self.wait_until(
                lambda: (
                    bool(
                        received
                    )
                    and not runtime.busy
                )
            )
        )

        self.assertTrue(
            runtime.shutdown()
        )

    def test_runtime_does_not_own_credentials_oauth_settings_or_direct_api(
        self,
    ):
        source = inspect.getsource(
            runtime_module
        )

        lowered = source.casefold()

        for forbidden in (
            "credential_store",
            "oauth",
            "qsettings",
            "spotifywebapiclient",
            "localmusic",
            "local_music",
            "settings_page",
            "access_token",
            "refresh_token",
        ):
            self.assertNotIn(
                forbidden,
                lowered,
            )

    def test_runtime_uses_expected_qthread_worker_lifecycle(
        self,
    ):
        source = inspect.getsource(
            runtime_module
        )

        self.assertIn(
            "worker.moveToThread",
            source,
        )

        self.assertIn(
            "thread.started.connect",
            source,
        )

        self.assertIn(
            "worker.finished.connect",
            source,
        )

        self.assertIn(
            "thread.quit",
            source,
        )

        self.assertIn(
            "worker.deleteLater",
            source,
        )

        self.assertIn(
            "thread.deleteLater",
            source,
        )

        self.assertNotIn(
            ".terminate(",
            source,
        )

    def test_runtime_only_exposes_credential_free_result_types(
        self,
    ):
        source = inspect.getsource(
            runtime_module
        )

        self.assertIn(
            "SpotifyPlaylistServiceResult",
            source,
        )

        self.assertIn(
            (
                "SpotifyResolvedPlaylistServiceResult"
            ),
            source,
        )

        self.assertNotIn(
            "SpotifyToken",
            source,
        )

        self.assertNotIn(
            "access_token",
            source,
        )
