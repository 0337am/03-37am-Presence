from __future__ import annotations

import threading
import unittest


from PyQt6.QtCore import (
    QCoreApplication,
    QEventLoop,
    QTimer,
    QUrl,
)

from src.spotify.connection_controller import (
    SpotifyConnectionError,
)
from src.spotify.connection_controller import (
    SpotifyConnectionResult,
)
from src.spotify.connection_controller import (
    SpotifyConnectionStatus,
)
from src.spotify.models import (
    SpotifyTokenBundle,
)
from src.spotify.qt_connection_runtime import (
    SpotifyQtConnectionRuntime,
)
from src.spotify.qt_connection_runtime import (
    SpotifyQtConnectionRuntimeError,
)
from src.spotify.qt_connection_runtime import (
    SpotifyQtConnectionState,
)
from src.spotify.qt_connection_runtime import (
    open_spotify_authorization_url,
)


TEST_CLIENT_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)


def make_token() -> SpotifyTokenBundle:
    return SpotifyTokenBundle(
        access_token=(
            "dummy-access-secret-qt"
        ),
        refresh_token=(
            "dummy-refresh-secret-qt"
        ),
        token_type="Bearer",
        expires_in=3600,
        granted_scopes=(
            "user-read-private",
        ),
        obtained_at=1000.0,
        authorized_at=900.0,
    )


def connected_result():
    return SpotifyConnectionResult(
        status=(
            SpotifyConnectionStatus.CONNECTED
        ),
        token=make_token(),
        message="Spotify is connected.",
    )


def disconnected_result():
    return SpotifyConnectionResult(
        status=(
            SpotifyConnectionStatus.DISCONNECTED
        ),
        message="Spotify is disconnected.",
    )


class FakeController:
    def __init__(
        self,
        *,
        browser_opener,
        operation_threads,
        result_map=None,
        error_map=None,
    ):
        self.browser_opener = (
            browser_opener
        )
        self.operation_threads = (
            operation_threads
        )
        self.result_map = (
            result_map
            or {}
        )
        self.error_map = (
            error_map
            or {}
        )

    def _run(
        self,
        operation,
    ):
        self.operation_threads[
            operation
        ] = threading.get_ident()

        error = self.error_map.get(
            operation
        )

        if error is not None:
            raise error

        return self.result_map[
            operation
        ]

    def restore(
        self,
    ):
        return self._run(
            "restore"
        )

    def connect(
        self,
    ):
        self.operation_threads[
            "connect"
        ] = threading.get_ident()

        if not self.browser_opener(
            (
                "https://accounts.spotify.com/"
                "authorize?client_id=test"
            )
        ):
            raise SpotifyConnectionError(
                "authorization_failed",
                (
                    "Spotify authorization did not "
                    "complete successfully."
                ),
            )

        error = self.error_map.get(
            "connect"
        )

        if error is not None:
            raise error

        return self.result_map[
            "connect"
        ]

    def disconnect(
        self,
    ):
        return self._run(
            "disconnect"
        )


class FakeControllerFactory:
    def __init__(
        self,
        *,
        result_map=None,
        error_map=None,
    ):
        self.result_map = (
            result_map
            or {}
        )
        self.error_map = (
            error_map
            or {}
        )
        self.operation_threads = {}
        self.factory_threads = []
        self.browser_openers = []

    def __call__(
        self,
        client_id,
        *,
        browser_opener,
    ):
        self.factory_threads.append(
            threading.get_ident()
        )

        self.browser_openers.append(
            browser_opener
        )

        if client_id != TEST_CLIENT_ID:
            raise AssertionError(
                "Unexpected client ID."
            )

        return FakeController(
            browser_opener=(
                browser_opener
            ),
            operation_threads=(
                self.operation_threads
            ),
            result_map=(
                self.result_map
            ),
            error_map=(
                self.error_map
            ),
        )


class UnexpectedFailureFactory:
    def __call__(
        self,
        client_id,
        *,
        browser_opener,
    ):
        raise RuntimeError(
            "sensitive unexpected detail"
        )


class BlockingController:
    def __init__(
        self,
        *,
        browser_opener,
        release_event,
    ):
        self.release_event = (
            release_event
        )

    def restore(
        self,
    ):
        self.release_event.wait(
            2.0
        )

        return disconnected_result()

    def connect(
        self,
    ):
        return connected_result()

    def disconnect(
        self,
    ):
        return disconnected_result()


class BlockingControllerFactory:
    def __init__(
        self,
        release_event,
    ):
        self.release_event = (
            release_event
        )

    def __call__(
        self,
        client_id,
        *,
        browser_opener,
    ):
        return BlockingController(
            browser_opener=(
                browser_opener
            ),
            release_event=(
                self.release_event
            ),
        )


class QtRuntimeTestCase(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QCoreApplication.instance()
        )

        if cls.app is None:
            cls.app = (
                QCoreApplication(
                    []
                )
            )

    def wait_for_runtime(
        self,
        runtime,
        *,
        timeout_ms=3000,
    ):
        if not runtime.busy:
            return

        loop = QEventLoop()

        timed_out = {
            "value": False,
        }

        def timeout():
            timed_out[
                "value"
            ] = True
            loop.quit()

        timer = QTimer()

        timer.setSingleShot(
            True
        )

        timer.timeout.connect(
            timeout
        )

        runtime.operation_finished.connect(
            loop.quit
        )

        timer.start(
            timeout_ms
        )

        loop.exec()

        timer.stop()

        if timed_out[
            "value"
        ]:
            self.fail(
                "Spotify Qt runtime did not finish."
            )


class SpotifyAuthorizationLauncherTests(
    QtRuntimeTestCase
):
    def test_valid_spotify_authorization_url_is_opened(
        self,
    ):
        opened = []

        def fake_open_url(
            url,
        ):
            opened.append(
                url
            )
            return True

        result = (
            open_spotify_authorization_url(
                (
                    "https://accounts.spotify.com/"
                    "authorize?client_id=test"
                ),
                open_url=fake_open_url,
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            len(
                opened
            ),
            1,
        )

        self.assertIsInstance(
            opened[
                0
            ],
            QUrl,
        )

        self.assertEqual(
            opened[
                0
            ].host(),
            "accounts.spotify.com",
        )

    def test_untrusted_authorization_urls_are_rejected(
        self,
    ):
        opened = []

        def fake_open_url(
            url,
        ):
            opened.append(
                url
            )
            return True

        urls = (
            "http://accounts.spotify.com/authorize",
            "https://evil.example/authorize",
            "https://accounts.spotify.com/not-authorize",
            "https://user:pass@accounts.spotify.com/authorize",
            "",
        )

        for url in urls:
            with self.subTest(
                url=url
            ):
                self.assertFalse(
                    open_spotify_authorization_url(
                        url,
                        open_url=fake_open_url,
                    )
                )

        self.assertEqual(
            opened,
            [],
        )

    def test_browser_launcher_exception_is_safe(
        self,
    ):
        def failing_open_url(
            url,
        ):
            raise RuntimeError(
                "simulated launcher failure"
            )

        self.assertFalse(
            open_spotify_authorization_url(
                (
                    "https://accounts.spotify.com/"
                    "authorize?client_id=test"
                ),
                open_url=failing_open_url,
            )
        )

    def test_open_url_dependency_must_be_callable(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            open_spotify_authorization_url(
                (
                    "https://accounts.spotify.com/"
                    "authorize"
                ),
                open_url=None,
            )


class SpotifyQtConnectionRuntimeTests(
    QtRuntimeTestCase
):
    def test_restore_runs_off_gui_thread(
        self,
    ):
        main_thread = (
            threading.get_ident()
        )

        factory = FakeControllerFactory(
            result_map={
                "restore": (
                    disconnected_result()
                ),
            }
        )

        runtime = (
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                controller_factory=factory,
                browser_launcher=(
                    lambda url: True
                ),
            )
        )

        received = []

        runtime.result_ready.connect(
            lambda operation, result: (
                received.append(
                    (
                        operation,
                        result,
                    )
                )
            )
        )

        runtime.restore()

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            len(
                received
            ),
            1,
        )

        self.assertEqual(
            received[
                0
            ][
                0
            ],
            "restore",
        )

        self.assertNotEqual(
            factory.operation_threads[
                "restore"
            ],
            main_thread,
        )

        self.assertNotEqual(
            factory.factory_threads[
                0
            ],
            main_thread,
        )

    def test_connect_worker_uses_gui_thread_browser_bridge(
        self,
    ):
        main_thread = (
            threading.get_ident()
        )

        factory = FakeControllerFactory(
            result_map={
                "connect": (
                    connected_result()
                ),
            }
        )

        browser_threads = []
        browser_urls = []

        def browser_launcher(
            url,
        ):
            browser_threads.append(
                threading.get_ident()
            )

            browser_urls.append(
                url
            )

            return True

        runtime = (
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                controller_factory=factory,
                browser_launcher=(
                    browser_launcher
                ),
            )
        )

        received = []

        runtime.result_ready.connect(
            lambda operation, result: (
                received.append(
                    (
                        operation,
                        result,
                    )
                )
            )
        )

        runtime.connect_spotify()

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            browser_threads,
            [
                main_thread,
            ],
        )

        self.assertEqual(
            len(
                browser_urls
            ),
            1,
        )

        self.assertNotEqual(
            factory.operation_threads[
                "connect"
            ],
            main_thread,
        )

        self.assertEqual(
            received[
                0
            ][
                0
            ],
            "connect",
        )

        self.assertTrue(
            received[
                0
            ][
                1
            ].connected
        )

    def test_gui_result_contains_no_oauth_credentials(
        self,
    ):
        token = SpotifyTokenBundle(
            access_token=(
                "access-secret-must-not-cross-ui"
            ),
            refresh_token=(
                "refresh-secret-must-not-cross-ui"
            ),
            token_type="Bearer",
            expires_in=3600,
            granted_scopes=(
                "user-read-private",
            ),
            obtained_at=1000.0,
            authorized_at=900.0,
        )

        controller_result = (
            SpotifyConnectionResult(
                status=(
                    SpotifyConnectionStatus.CONNECTED
                ),
                token=token,
                message="Spotify is connected.",
            )
        )

        factory = FakeControllerFactory(
            result_map={
                "restore": controller_result,
            }
        )

        runtime = (
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                controller_factory=factory,
                browser_launcher=(
                    lambda url: True
                ),
            )
        )

        received = []

        runtime.result_ready.connect(
            lambda operation, result: (
                received.append(
                    (
                        operation,
                        result,
                    )
                )
            )
        )

        runtime.restore()

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            len(
                received
            ),
            1,
        )

        gui_result = received[
            0
        ][
            1
        ]

        self.assertIsInstance(
            gui_result,
            SpotifyQtConnectionState,
        )

        self.assertTrue(
            gui_result.connected
        )

        self.assertFalse(
            hasattr(
                gui_result,
                "token",
            )
        )

        self.assertFalse(
            hasattr(
                gui_result,
                "access_token",
            )
        )

        self.assertFalse(
            hasattr(
                gui_result,
                "refresh_token",
            )
        )

        rendered = repr(
            gui_result
        )

        self.assertNotIn(
            "access-secret-must-not-cross-ui",
            rendered,
        )

        self.assertNotIn(
            "refresh-secret-must-not-cross-ui",
            rendered,
        )

    def test_disconnect_runs_off_gui_thread(
        self,
    ):
        main_thread = (
            threading.get_ident()
        )

        factory = FakeControllerFactory(
            result_map={
                "disconnect": (
                    disconnected_result()
                ),
            }
        )

        runtime = (
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                controller_factory=factory,
                browser_launcher=(
                    lambda url: True
                ),
            )
        )

        runtime.disconnect()

        self.wait_for_runtime(
            runtime
        )

        self.assertNotEqual(
            factory.operation_threads[
                "disconnect"
            ],
            main_thread,
        )

    def test_busy_runtime_rejects_second_operation(
        self,
    ):
        release_event = (
            threading.Event()
        )

        runtime = (
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                controller_factory=(
                    BlockingControllerFactory(
                        release_event
                    )
                ),
                browser_launcher=(
                    lambda url: True
                ),
            )
        )

        runtime.restore()

        self.assertTrue(
            runtime.busy
        )

        self.assertEqual(
            runtime.active_operation,
            "restore",
        )

        with self.assertRaises(
            SpotifyQtConnectionRuntimeError
        ) as context:
            runtime.disconnect()

        self.assertEqual(
            context.exception.error_code,
            "busy",
        )

        release_event.set()

        self.wait_for_runtime(
            runtime
        )

        self.assertFalse(
            runtime.busy
        )

        self.assertIsNone(
            runtime.active_operation
        )

    def test_controller_error_is_forwarded(
        self,
    ):
        factory = FakeControllerFactory(
            result_map={},
            error_map={
                "restore": (
                    SpotifyConnectionError(
                        "restore_failed",
                        "Spotify could not be restored.",
                    )
                ),
            },
        )

        runtime = (
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                controller_factory=factory,
                browser_launcher=(
                    lambda url: True
                ),
            )
        )

        failures = []

        runtime.failed.connect(
            lambda operation, code, message: (
                failures.append(
                    (
                        operation,
                        code,
                        message,
                    )
                )
            )
        )

        runtime.restore()

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            failures,
            [
                (
                    "restore",
                    "restore_failed",
                    "Spotify could not be restored.",
                ),
            ],
        )

    def test_unexpected_exception_does_not_leak_detail(
        self,
    ):
        runtime = (
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                controller_factory=(
                    UnexpectedFailureFactory()
                ),
                browser_launcher=(
                    lambda url: True
                ),
            )
        )

        failures = []

        runtime.failed.connect(
            lambda operation, code, message: (
                failures.append(
                    (
                        operation,
                        code,
                        message,
                    )
                )
            )
        )

        runtime.restore()

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            len(
                failures
            ),
            1,
        )

        self.assertEqual(
            failures[
                0
            ][
                1
            ],
            "operation_failed",
        )

        rendered = (
            failures[
                0
            ][
                2
            ]
        )

        self.assertNotIn(
            "sensitive unexpected detail",
            rendered,
        )

    def test_browser_failure_reaches_controller_safely(
        self,
    ):
        factory = FakeControllerFactory(
            result_map={
                "connect": (
                    connected_result()
                ),
            }
        )

        runtime = (
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                controller_factory=factory,
                browser_launcher=(
                    lambda url: False
                ),
            )
        )

        failures = []

        runtime.failed.connect(
            lambda operation, code, message: (
                failures.append(
                    (
                        operation,
                        code,
                        message,
                    )
                )
            )
        )

        runtime.connect_spotify()

        self.wait_for_runtime(
            runtime
        )

        self.assertEqual(
            len(
                failures
            ),
            1,
        )

        self.assertEqual(
            failures[
                0
            ][
                0
            ],
            "connect",
        )

        self.assertEqual(
            failures[
                0
            ][
                1
            ],
            "authorization_failed",
        )

    def test_busy_state_signals_wrap_operation(
        self,
    ):
        factory = FakeControllerFactory(
            result_map={
                "restore": (
                    disconnected_result()
                ),
            }
        )

        runtime = (
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                controller_factory=factory,
                browser_launcher=(
                    lambda url: True
                ),
            )
        )

        busy_states = []
        started = []
        finished = []

        runtime.busy_changed.connect(
            busy_states.append
        )

        runtime.operation_started.connect(
            started.append
        )

        runtime.operation_finished.connect(
            finished.append
        )

        runtime.restore()

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
                "restore",
            ],
        )

        self.assertEqual(
            finished,
            [
                "restore",
            ],
        )

    def test_constructor_validates_inputs(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyQtConnectionRuntime(
                "",
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                controller_factory=object(),
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                browser_launcher=object(),
            )

        with self.assertRaises(
            ValueError
        ):
            SpotifyQtConnectionRuntime(
                TEST_CLIENT_ID,
                browser_bridge_timeout_seconds=0,
            )


class SpotifyQtConnectionRuntimeBoundaryTests(
    unittest.TestCase
):
    def test_runtime_uses_expected_qt_worker_lifecycle(
        self,
    ):
        from pathlib import Path

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

        required = (
            "QObject",
            "QThread",
            "moveToThread",
            "worker.finished.connect",
            "thread.quit",
            "worker.deleteLater",
            "thread.deleteLater",
            "QDesktopServices",
            "SpotifyQtConnectionState",
        )

        for marker in required:
            with self.subTest(
                marker=marker
            ):
                self.assertIn(
                    marker,
                    source,
                )

    def test_runtime_does_not_own_credentials_or_settings(
        self,
    ):
        from pathlib import Path

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

        forbidden = (
            "QSettings",
            "CryptProtectData",
            "CryptUnprotectData",
            "spotify_auth.dat",
            "client_secret",
            "access_token",
            "refresh_token",
            "os.startfile",
            "webbrowser",
            "logging.",
            "print(",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )


if __name__ == "__main__":
    unittest.main()
