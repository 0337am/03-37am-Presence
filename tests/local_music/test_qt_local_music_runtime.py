from __future__ import annotations

import threading
import time
import unittest
from pathlib import Path

from PyQt6.QtCore import (
    QThread,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.media.local_music_index import (
    LocalMusicIndexError,
    LocalMusicScanCancelled,
    LocalMusicScanResult,
)
from src.media.qt_local_music_runtime import (
    LocalMusicQtRuntimeError,
    LocalMusicQtScanRuntime,
)
from tests.repo_paths import REPO_ROOT


def empty_result(
    folders=(),
):
    return LocalMusicScanResult(
        candidates=(),
        roots=tuple(
            folders
        ),
        scanned_files=0,
        indexed_files=0,
        skipped_files=0,
        limit_reached=False,
    )


def process_until(
    predicate,
    *,
    timeout_seconds=3.0,
):
    deadline = (
        time.monotonic()
        + timeout_seconds
    )

    while (
        time.monotonic()
        < deadline
    ):
        QApplication.processEvents()

        if predicate():
            return True

        time.sleep(
            0.005
        )

    QApplication.processEvents()

    return bool(
        predicate()
    )


class LocalMusicQtRuntimeBoundaryTests(
    unittest.TestCase
):
    def test_runtime_owns_no_spotify_credentials_network_or_settings(
        self,
    ):
        root = (
            REPO_ROOT
        )

        source = (
            root
            / "src"
            / "media"
            / "qt_local_music_runtime.py"
        ).read_text(
            encoding="utf-8"
        )

        for forbidden in (
            "SpotifyCredentialStore",
            "SpotifySessionManager",
            "SpotifyTokenClient",
            "access_token",
            "refresh_token",
            "client_secret",
            "urllib",
            "requests.",
            "QSettings",
            "tinytag",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    source,
                )

    def test_runtime_uses_qthread_worker_lifecycle(
        self,
    ):
        root = (
            REPO_ROOT
        )

        source = (
            root
            / "src"
            / "media"
            / "qt_local_music_runtime.py"
        ).read_text(
            encoding="utf-8"
        )

        for marker in (
            "QThread(",
            "moveToThread",
            "thread.started.connect",
            "worker.finished.connect",
            "thread.wait(",
            "requestInterruption",
            "thread.quit()",
        ):
            with self.subTest(
                marker=marker
            ):
                self.assertIn(
                    marker,
                    source,
                )

    def test_runtime_never_terminates_threads(
        self,
    ):
        root = (
            REPO_ROOT
        )

        source = (
            root
            / "src"
            / "media"
            / "qt_local_music_runtime.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            ".terminate(",
            source,
        )


class LocalMusicQtRuntimeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def tearDown(
        self,
    ):
        QApplication.processEvents()

    def test_constructor_validates_inputs(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            LocalMusicQtScanRuntime(
                index_factory=object()
            )

        with self.assertRaises(
            TypeError
        ):
            LocalMusicQtScanRuntime(
                shutdown_wait_ms=True
            )

        with self.assertRaises(
            ValueError
        ):
            LocalMusicQtScanRuntime(
                shutdown_wait_ms=0
            )

    def test_start_requires_tuple_of_string_paths(
        self,
    ):
        runtime = (
            LocalMusicQtScanRuntime()
        )

        self.addCleanup(
            runtime.shutdown
        )

        with self.assertRaises(
            TypeError
        ):
            runtime.start_scan(
                [
                    r"C:\Music",
                ]
            )

        with self.assertRaises(
            TypeError
        ):
            runtime.start_scan(
                (
                    object(),
                )
            )

        with self.assertRaises(
            ValueError
        ):
            runtime.start_scan(
                (
                    "   ",
                )
            )

    def test_successful_scan_updates_latest_result(
        self,
    ):
        expected = empty_result(
            (
                r"C:\Music",
            )
        )

        class Index:
            def scan(
                self,
                folders,
                *,
                cancel_requested=None,
            ):
                return expected

        runtime = (
            LocalMusicQtScanRuntime(
                index_factory=Index
            )
        )

        self.addCleanup(
            runtime.shutdown
        )

        received = []

        runtime.result_ready.connect(
            received.append
        )

        runtime.start_scan(
            (
                r"C:\Music",
            )
        )

        self.assertTrue(
            process_until(
                lambda: (
                    not runtime.busy
                    and bool(
                        received
                    )
                )
            )
        )

        self.assertIs(
            received[
                0
            ],
            expected,
        )

        self.assertIs(
            runtime.latest_result,
            expected,
        )

    def test_scan_runs_off_gui_thread(
        self,
    ):
        observed = []

        class Index:
            def scan(
                self,
                folders,
                *,
                cancel_requested=None,
            ):
                observed.append(
                    QThread.currentThread()
                )

                return empty_result(
                    folders
                )

        runtime = (
            LocalMusicQtScanRuntime(
                index_factory=Index
            )
        )

        self.addCleanup(
            runtime.shutdown
        )

        gui_thread = (
            QThread.currentThread()
        )

        runtime.start_scan(
            (
                r"C:\Music",
            )
        )

        self.assertTrue(
            process_until(
                lambda: (
                    not runtime.busy
                )
            )
        )

        self.assertEqual(
            len(
                observed
            ),
            1,
        )

        self.assertIsNot(
            observed[
                0
            ],
            gui_thread,
        )

    def test_folders_are_forwarded_exactly(
        self,
    ):
        observed = []

        class Index:
            def scan(
                self,
                folders,
                *,
                cancel_requested=None,
            ):
                observed.append(
                    folders
                )

                return empty_result(
                    folders
                )

        runtime = (
            LocalMusicQtScanRuntime(
                index_factory=Index
            )
        )

        self.addCleanup(
            runtime.shutdown
        )

        folders = (
            r"C:\Music",
            r"D:\Juice WRLD",
        )

        runtime.start_scan(
            folders
        )

        self.assertTrue(
            process_until(
                lambda: (
                    not runtime.busy
                )
            )
        )

        self.assertEqual(
            observed,
            [
                folders,
            ],
        )

    def test_busy_runtime_rejects_second_scan(
        self,
    ):
        started = (
            threading.Event()
        )

        release = (
            threading.Event()
        )

        class Index:
            def scan(
                self,
                folders,
                *,
                cancel_requested=None,
            ):
                started.set()

                while not release.wait(
                    0.01
                ):
                    if (
                        cancel_requested
                        is not None
                        and cancel_requested()
                    ):
                        raise (
                            LocalMusicScanCancelled(
                                "cancelled"
                            )
                        )

                return empty_result(
                    folders
                )

        runtime = (
            LocalMusicQtScanRuntime(
                index_factory=Index
            )
        )

        self.addCleanup(
            runtime.shutdown
        )

        runtime.start_scan(
            (
                r"C:\Music",
            )
        )

        self.assertTrue(
            started.wait(
                1.0
            )
        )

        with self.assertRaises(
            LocalMusicQtRuntimeError
        ) as raised:
            runtime.start_scan(
                (
                    r"D:\Music",
                )
            )

        self.assertEqual(
            raised.exception.error_code,
            "busy",
        )

        release.set()

        self.assertTrue(
            process_until(
                lambda: (
                    not runtime.busy
                )
            )
        )

    def test_invalid_result_is_safe_failure(
        self,
    ):
        class Index:
            def scan(
                self,
                folders,
                *,
                cancel_requested=None,
            ):
                return object()

        runtime = (
            LocalMusicQtScanRuntime(
                index_factory=Index
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

        runtime.start_scan(
            (
                r"C:\Music",
            )
        )

        self.assertTrue(
            process_until(
                lambda: (
                    not runtime.busy
                    and bool(
                        failures
                    )
                )
            )
        )

        self.assertEqual(
            failures[
                0
            ][0],
            "invalid_result",
        )

    def test_index_error_is_safe_failure(
        self,
    ):
        class Index:
            def scan(
                self,
                folders,
                *,
                cancel_requested=None,
            ):
                raise LocalMusicIndexError(
                    (
                        "private implementation "
                        "detail"
                    )
                )

        runtime = (
            LocalMusicQtScanRuntime(
                index_factory=Index
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

        runtime.start_scan(
            (
                r"C:\Music",
            )
        )

        self.assertTrue(
            process_until(
                lambda: (
                    not runtime.busy
                    and bool(
                        failures
                    )
                )
            )
        )

        self.assertEqual(
            failures[
                0
            ][0],
            "scan_failed",
        )

        self.assertNotIn(
            "private implementation",
            failures[
                0
            ][1],
        )

    def test_unexpected_exception_is_safe_failure(
        self,
    ):
        class Index:
            def scan(
                self,
                folders,
                *,
                cancel_requested=None,
            ):
                raise RuntimeError(
                    "secret traceback detail"
                )

        runtime = (
            LocalMusicQtScanRuntime(
                index_factory=Index
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

        runtime.start_scan(
            (
                r"C:\Music",
            )
        )

        self.assertTrue(
            process_until(
                lambda: (
                    not runtime.busy
                    and bool(
                        failures
                    )
                )
            )
        )

        self.assertEqual(
            failures[
                0
            ][0],
            "scan_failed",
        )

        self.assertNotIn(
            "secret traceback",
            failures[
                0
            ][1],
        )

    def test_cancel_scan_is_forwarded(
        self,
    ):
        started = (
            threading.Event()
        )

        class Index:
            def scan(
                self,
                folders,
                *,
                cancel_requested=None,
            ):
                started.set()

                while True:
                    if (
                        cancel_requested
                        is not None
                        and cancel_requested()
                    ):
                        raise (
                            LocalMusicScanCancelled(
                                "cancelled"
                            )
                        )

                    time.sleep(
                        0.005
                    )

        runtime = (
            LocalMusicQtScanRuntime(
                index_factory=Index
            )
        )

        self.addCleanup(
            runtime.shutdown
        )

        cancelled = []

        runtime.scan_cancelled.connect(
            lambda:
            cancelled.append(
                True
            )
        )

        runtime.start_scan(
            (
                r"C:\Music",
            )
        )

        self.assertTrue(
            started.wait(
                1.0
            )
        )

        self.assertTrue(
            runtime.cancel_scan()
        )

        self.assertTrue(
            process_until(
                lambda: (
                    not runtime.busy
                    and bool(
                        cancelled
                    )
                )
            )
        )

    def test_shutdown_blocks_new_scans(
        self,
    ):
        runtime = (
            LocalMusicQtScanRuntime()
        )

        self.assertTrue(
            runtime.shutdown()
        )

        with self.assertRaises(
            LocalMusicQtRuntimeError
        ) as raised:
            runtime.start_scan(
                (
                    r"C:\Music",
                )
            )

        self.assertEqual(
            raised.exception.error_code,
            "closed",
        )

    def test_shutdown_cancels_active_worker(
        self,
    ):
        started = (
            threading.Event()
        )

        saw_cancel = (
            threading.Event()
        )

        class Index:
            def scan(
                self,
                folders,
                *,
                cancel_requested=None,
            ):
                started.set()

                while True:
                    if (
                        cancel_requested
                        is not None
                        and cancel_requested()
                    ):
                        saw_cancel.set()

                        raise (
                            LocalMusicScanCancelled(
                                "cancelled"
                            )
                        )

                    time.sleep(
                        0.005
                    )

        runtime = (
            LocalMusicQtScanRuntime(
                index_factory=Index,
                shutdown_wait_ms=3000,
            )
        )

        runtime.start_scan(
            (
                r"C:\Music",
            )
        )

        self.assertTrue(
            started.wait(
                1.0
            )
        )

        self.assertTrue(
            runtime.shutdown()
        )

        self.assertTrue(
            saw_cancel.wait(
                1.0
            )
        )

        self.assertFalse(
            runtime.busy
        )


    def test_clear_latest_result_emits_result_cleared(
        self,
    ):
        runtime = (
            LocalMusicQtScanRuntime()
        )

        self.addCleanup(
            runtime.shutdown
        )

        runtime._latest_result = (
            empty_result(
                (
                    r"C:\Music",
                )
            )
        )

        cleared = []

        runtime.result_cleared.connect(
            lambda: cleared.append(
                True
            )
        )

        runtime.clear_latest_result()

        self.assertIsNone(
            runtime.latest_result
        )

        self.assertEqual(
            cleared,
            [
                True,
            ],
        )

    def test_clear_signal_emits_without_cached_result(
        self,
    ):
        runtime = (
            LocalMusicQtScanRuntime()
        )

        self.addCleanup(
            runtime.shutdown
        )

        cleared = []

        runtime.result_cleared.connect(
            lambda: cleared.append(
                True
            )
        )

        runtime.clear_latest_result()

        self.assertEqual(
            cleared,
            [
                True,
            ],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
