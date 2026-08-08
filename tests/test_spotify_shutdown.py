from __future__ import annotations

from pathlib import Path
import threading
import time
import unittest

from PyQt6.QtCore import (
    QCoreApplication,
)

from src.spotify.connection_controller import (
    SpotifyConnectionController,
    SpotifyConnectionResult,
    SpotifyConnectionStatus,
)
from src.spotify.oauth_callback import (
    LoopbackCallbackCancelled,
    SpotifyLoopbackCallbackServer,
)
from src.spotify.oauth_session import (
    SpotifyOAuthSession,
    SpotifyOAuthSessionResult,
    SpotifyOAuthSessionStatus,
)
from src.spotify.qt_connection_runtime import (
    SpotifyQtConnectionRuntime,
)


TEST_CLIENT_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)


class MinimalSessionManager:
    def resolve(
        self,
    ):
        raise AssertionError(
            "resolve should not be used"
        )

    def persist_authorized_token(
        self,
        token,
    ):
        raise AssertionError(
            "cancelled authorization must not persist"
        )

    def disconnect(
        self,
    ):
        raise AssertionError(
            "disconnect should not be used"
        )


class CancelledOAuthSession:
    def connect(
        self,
    ):
        return SpotifyOAuthSessionResult(
            status=(
                SpotifyOAuthSessionStatus
                .CANCELLED
            ),
            message=(
                "Spotify authorization was cancelled."
            ),
        )


class CapturingOAuthFactory:
    def __init__(
        self,
    ):
        self.cancel_requested = None

    def __call__(
        self,
        client_id,
        *,
        browser_opener,
        callback_timeout_seconds,
        cancel_requested=None,
    ):
        self.cancel_requested = (
            cancel_requested
        )

        return CancelledOAuthSession()


class CancellableController:
    def __init__(
        self,
        started_event,
    ):
        self.started_event = (
            started_event
        )

        self.cancel_requested = (
            lambda: False
        )

    def set_cancel_requested(
        self,
        cancel_requested,
    ):
        self.cancel_requested = (
            cancel_requested
        )

    def restore(
        self,
    ):
        return SpotifyConnectionResult(
            status=(
                SpotifyConnectionStatus
                .DISCONNECTED
            ),
            message="disconnected",
        )

    def connect(
        self,
    ):
        self.started_event.set()

        deadline = (
            time.monotonic()
            + 5.0
        )

        while (
            not self.cancel_requested()
            and time.monotonic()
            < deadline
        ):
            time.sleep(
                0.01
            )

        if not self.cancel_requested():
            raise RuntimeError(
                "cancellation was never requested"
            )

        return SpotifyConnectionResult(
            status=(
                SpotifyConnectionStatus
                .CANCELLED
            ),
            message=(
                "Spotify authorization was cancelled."
            ),
        )

    def disconnect(
        self,
    ):
        return SpotifyConnectionResult(
            status=(
                SpotifyConnectionStatus
                .DISCONNECTED
            ),
            message="disconnected",
        )


class CancellableControllerFactory:
    def __init__(
        self,
        started_event,
    ):
        self.started_event = (
            started_event
        )

        self.controller = None

    def __call__(
        self,
        client_id,
        *,
        browser_opener,
    ):
        self.controller = (
            CancellableController(
                self.started_event
            )
        )

        return self.controller


class SpotifyCallbackCancellationTests(
    unittest.TestCase
):
    def test_callback_wait_can_be_cancelled_quickly(
        self,
    ):
        cancel_event = (
            threading.Event()
        )

        timer = threading.Timer(
            0.05,
            cancel_event.set,
        )

        server = (
            SpotifyLoopbackCallbackServer()
        )

        started = time.monotonic()

        timer.start()

        try:
            with self.assertRaises(
                LoopbackCallbackCancelled
            ):
                server.wait_for_callback(
                    timeout_seconds=3.0,
                    cancel_requested=(
                        cancel_event.is_set
                    ),
                )

        finally:
            timer.cancel()
            server.close()

        elapsed = (
            time.monotonic()
            - started
        )

        self.assertLess(
            elapsed,
            1.0,
        )

        self.assertTrue(
            server.closed
        )


class SpotifyOAuthCancellationTests(
    unittest.TestCase
):
    def test_pre_cancelled_session_never_opens_browser(
        self,
    ):
        browser_calls = []

        def forbidden_server_factory():
            raise AssertionError(
                (
                    "callback server should not "
                    "start after cancellation"
                )
            )

        session = SpotifyOAuthSession(
            TEST_CLIENT_ID,
            browser_opener=(
                lambda url: (
                    browser_calls.append(
                        url
                    )
                    or True
                )
            ),
            cancel_requested=(
                lambda: True
            ),
            callback_server_factory=(
                forbidden_server_factory
            ),
        )

        result = session.connect()

        self.assertTrue(
            result.cancelled
        )

        self.assertFalse(
            result.connected
        )

        self.assertEqual(
            browser_calls,
            [],
        )

        self.assertIsNone(
            result.token
        )


class SpotifyControllerCancellationTests(
    unittest.TestCase
):
    def test_controller_forwards_cancellation_checker(
        self,
    ):
        oauth_factory = (
            CapturingOAuthFactory()
        )

        controller = (
            SpotifyConnectionController(
                TEST_CLIENT_ID,
                session_manager=(
                    MinimalSessionManager()
                ),
                oauth_session_factory=(
                    oauth_factory
                ),
                browser_opener=(
                    lambda url: True
                ),
            )
        )

        cancel_event = (
            threading.Event()
        )

        controller.set_cancel_requested(
            cancel_event.is_set
        )

        cancel_event.set()

        result = controller.connect()

        self.assertTrue(
            callable(
                oauth_factory.cancel_requested
            )
        )

        self.assertTrue(
            oauth_factory.cancel_requested()
        )

        self.assertTrue(
            result.cancelled
        )


class SpotifyQtShutdownTests(
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

    def process_until(
        self,
        condition,
        *,
        timeout=2.0,
    ):
        deadline = (
            time.monotonic()
            + timeout
        )

        while (
            not condition()
            and time.monotonic()
            < deadline
        ):
            self.app.processEvents()

            time.sleep(
                0.005
            )

        self.app.processEvents()

    def test_shutdown_stops_active_connect_worker(
        self,
    ):
        started_event = (
            threading.Event()
        )

        factory = (
            CancellableControllerFactory(
                started_event
            )
        )

        runtime = (
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                controller_factory=(
                    factory
                ),
                browser_launcher=(
                    lambda url: True
                ),
            )
        )

        runtime.connect_spotify()

        self.process_until(
            started_event.is_set
        )

        self.assertTrue(
            started_event.is_set()
        )

        self.assertTrue(
            runtime.busy
        )

        started = time.monotonic()

        completed = runtime.shutdown()

        elapsed = (
            time.monotonic()
            - started
        )

        self.assertTrue(
            completed
        )

        self.assertLess(
            elapsed,
            2.0,
        )

        self.assertFalse(
            runtime.busy
        )

        self.assertIsNone(
            runtime.active_operation
        )

    def test_runtime_never_force_terminates_qthread(
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
            / "qt_connection_runtime.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            ".terminate(",
            source,
        )

        self.assertIn(
            "request_cancel",
            source,
        )

        self.assertIn(
            "thread.wait",
            source,
        )


class SpotifyShutdownWiringTests(
    unittest.TestCase
):
    def test_main_window_shutdown_stops_spotify_runtime(
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
            / "ui"
            / "main_window.py"
        ).read_text(
            encoding="utf-8"
        )

        shutdown_start = source.index(
            "    def shutdown(self):"
        )

        close_event_start = source.index(
            "    def closeEvent(",
            shutdown_start,
        )

        shutdown_source = source[
            shutdown_start:
            close_event_start
        ]

        self.assertIn(
            "spotify_connection_runtime",
            shutdown_source,
        )

        self.assertIn(
            "shutdown_spotify",
            shutdown_source,
        )

        self.assertIn(
            "shutdown_spotify()",
            shutdown_source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
