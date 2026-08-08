from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


from src.spotify.connection_controller import (
    SpotifyConnectionController,
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
from src.spotify.credential_store import (
    SpotifyCredentialStore,
)
from src.spotify.models import (
    SpotifyTokenBundle,
)
from src.spotify.oauth_session import (
    SpotifyOAuthSessionError,
)
from src.spotify.session_manager import (
    SpotifySessionManager,
)
from src.spotify.session_manager import (
    SpotifySessionManagerError,
)
from src.spotify.session_manager import (
    SpotifySessionResult,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)


TEST_CLIENT_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)


def make_token(
    *,
    suffix: str = "one",
    obtained_at: float = 1000.0,
) -> SpotifyTokenBundle:
    return SpotifyTokenBundle(
        access_token=(
            f"dummy-access-secret-{suffix}"
        ),
        refresh_token=(
            f"dummy-refresh-secret-{suffix}"
        ),
        token_type="Bearer",
        expires_in=3600,
        granted_scopes=(
            "user-read-private",
        ),
        obtained_at=obtained_at,
        authorized_at=900.0,
    )


class FakeSessionManager:
    def __init__(
        self,
        *,
        resolve_result=None,
        resolve_error=None,
        persist_result=None,
        persist_error=None,
        disconnect_result=None,
        disconnect_error=None,
    ):
        self.resolve_result = resolve_result
        self.resolve_error = resolve_error
        self.persist_result = persist_result
        self.persist_error = persist_error
        self.disconnect_result = (
            disconnect_result
        )
        self.disconnect_error = (
            disconnect_error
        )

        self.resolve_calls = 0
        self.persist_calls = []
        self.disconnect_calls = 0

    def resolve(
        self,
    ):
        self.resolve_calls += 1

        if self.resolve_error is not None:
            raise self.resolve_error

        if self.resolve_result is None:
            return SpotifySessionResult(
                status=(
                    SpotifySessionStatus.DISCONNECTED
                )
            )

        return self.resolve_result

    def persist_authorized_token(
        self,
        token,
    ):
        self.persist_calls.append(
            token
        )

        if self.persist_error is not None:
            raise self.persist_error

        if self.persist_result is not None:
            return self.persist_result

        return SpotifySessionResult(
            status=SpotifySessionStatus.READY,
            token=token,
        )

    def disconnect(
        self,
    ):
        self.disconnect_calls += 1

        if self.disconnect_error is not None:
            raise self.disconnect_error

        if self.disconnect_result is not None:
            return self.disconnect_result

        return SpotifySessionResult(
            status=(
                SpotifySessionStatus.DISCONNECTED
            )
        )


class FakeOAuthResult:
    def __init__(
        self,
        *,
        connected=False,
        denied=False,
        token=None,
    ):
        self.connected = connected
        self.denied = denied
        self.token = token


class FakeOAuthSession:
    def __init__(
        self,
        *,
        result=None,
        error=None,
    ):
        self.result = result
        self.error = error
        self.connect_calls = 0

    def connect(
        self,
    ):
        self.connect_calls += 1

        if self.error is not None:
            raise self.error

        return self.result


class FakeOAuthFactory:
    def __init__(
        self,
        session,
    ):
        self.session = session
        self.calls = []

    def __call__(
        self,
        client_id,
        *,
        browser_opener,
        callback_timeout_seconds,
    ):
        self.calls.append(
            {
                "client_id": client_id,
                "browser_opener": (
                    browser_opener
                ),
                "callback_timeout_seconds": (
                    callback_timeout_seconds
                ),
            }
        )

        return self.session


class FakeRefreshClient:
    def __init__(
        self,
        refreshed,
    ):
        self.refreshed = refreshed
        self.calls = []

    def refresh_access_token(
        self,
        token,
    ):
        self.calls.append(
            token
        )

        return self.refreshed


def fake_browser_opener(
    url,
):
    return True


class SpotifyConnectionControllerTests(
    unittest.TestCase
):
    def test_restore_missing_credentials_maps_to_disconnected(
        self,
    ):
        manager = FakeSessionManager(
            resolve_result=(
                SpotifySessionResult(
                    status=(
                        SpotifySessionStatus.DISCONNECTED
                    )
                )
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=manager,
        )

        result = controller.restore()

        self.assertEqual(
            result.status,
            SpotifyConnectionStatus.DISCONNECTED,
        )

        self.assertFalse(
            result.connected
        )

        self.assertIsNone(
            result.token
        )

    def test_restore_ready_maps_to_connected(
        self,
    ):
        token = make_token()

        manager = FakeSessionManager(
            resolve_result=(
                SpotifySessionResult(
                    status=SpotifySessionStatus.READY,
                    token=token,
                )
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=manager,
        )

        result = controller.restore()

        self.assertEqual(
            result.status,
            SpotifyConnectionStatus.CONNECTED,
        )

        self.assertTrue(
            result.connected
        )

        self.assertIs(
            result.token,
            token,
        )

    def test_restore_refreshed_preserves_refreshed_state(
        self,
    ):
        token = make_token(
            suffix="refreshed"
        )

        manager = FakeSessionManager(
            resolve_result=(
                SpotifySessionResult(
                    status=(
                        SpotifySessionStatus.REFRESHED
                    ),
                    token=token,
                )
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=manager,
        )

        result = controller.restore()

        self.assertEqual(
            result.status,
            SpotifyConnectionStatus.REFRESHED,
        )

        self.assertTrue(
            result.connected
        )

        self.assertTrue(
            result.refreshed
        )

    def test_restore_reauthorization_state_is_preserved(
        self,
    ):
        manager = FakeSessionManager(
            resolve_result=(
                SpotifySessionResult(
                    status=(
                        SpotifySessionStatus
                        .REAUTHORIZATION_REQUIRED
                    )
                )
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=manager,
        )

        result = controller.restore()

        self.assertTrue(
            result.requires_reauthorization
        )

        self.assertFalse(
            result.connected
        )

    def test_restore_manager_failure_is_wrapped_safely(
        self,
    ):
        marker = (
            "sensitive-storage-detail"
        )

        manager = FakeSessionManager(
            resolve_error=(
                SpotifySessionManagerError(
                    "credential_load_failed",
                    marker,
                )
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=manager,
        )

        with self.assertRaises(
            SpotifyConnectionError
        ) as context:
            controller.restore()

        failure = context.exception

        self.assertEqual(
            failure.error_code,
            "restore_failed",
        )

        self.assertNotIn(
            marker,
            str(
                failure
            ),
        )

        self.assertIsNone(
            failure.__cause__
        )

    def test_connect_requires_browser_opener(
        self,
    ):
        manager = FakeSessionManager()

        factory = FakeOAuthFactory(
            FakeOAuthSession(
                result=FakeOAuthResult()
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=manager,
            oauth_session_factory=factory,
        )

        with self.assertRaises(
            SpotifyConnectionError
        ) as context:
            controller.connect()

        self.assertEqual(
            context.exception.error_code,
            "browser_unavailable",
        )

        self.assertEqual(
            factory.calls,
            [],
        )

    def test_successful_connect_persists_authorized_token(
        self,
    ):
        token = make_token()

        manager = FakeSessionManager()

        oauth_session = FakeOAuthSession(
            result=FakeOAuthResult(
                connected=True,
                token=token,
            )
        )

        factory = FakeOAuthFactory(
            oauth_session
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=manager,
            oauth_session_factory=factory,
            browser_opener=fake_browser_opener,
            callback_timeout_seconds=90.0,
        )

        result = controller.connect()

        self.assertEqual(
            result.status,
            SpotifyConnectionStatus.CONNECTED,
        )

        self.assertTrue(
            result.connected
        )

        self.assertIs(
            result.token,
            token,
        )

        self.assertEqual(
            manager.persist_calls,
            [
                token,
            ],
        )

        self.assertEqual(
            len(
                factory.calls
            ),
            1,
        )

        call = factory.calls[
            0
        ]

        self.assertEqual(
            call[
                "client_id"
            ],
            TEST_CLIENT_ID,
        )

        self.assertIs(
            call[
                "browser_opener"
            ],
            fake_browser_opener,
        )

        self.assertEqual(
            call[
                "callback_timeout_seconds"
            ],
            90.0,
        )

    def test_user_denial_maps_to_cancelled_without_persisting(
        self,
    ):
        manager = FakeSessionManager()

        factory = FakeOAuthFactory(
            FakeOAuthSession(
                result=FakeOAuthResult(
                    denied=True
                )
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=manager,
            oauth_session_factory=factory,
            browser_opener=fake_browser_opener,
        )

        result = controller.connect()

        self.assertTrue(
            result.cancelled
        )

        self.assertFalse(
            result.connected
        )

        self.assertEqual(
            manager.persist_calls,
            [],
        )

    def test_oauth_failure_is_wrapped_without_detail_leak(
        self,
    ):
        marker = (
            "sensitive-oauth-detail"
        )

        factory = FakeOAuthFactory(
            FakeOAuthSession(
                error=SpotifyOAuthSessionError(
                    "authorization_failed",
                    marker,
                )
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=FakeSessionManager(),
            oauth_session_factory=factory,
            browser_opener=fake_browser_opener,
        )

        with self.assertRaises(
            SpotifyConnectionError
        ) as context:
            controller.connect()

        failure = context.exception

        self.assertEqual(
            failure.error_code,
            "authorization_failed",
        )

        self.assertNotIn(
            marker,
            str(
                failure
            ),
        )

        self.assertIsNone(
            failure.__cause__
        )

    def test_invalid_oauth_result_is_rejected(
        self,
    ):
        factory = FakeOAuthFactory(
            FakeOAuthSession(
                result=FakeOAuthResult(
                    connected=False,
                    denied=False,
                )
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=FakeSessionManager(),
            oauth_session_factory=factory,
            browser_opener=fake_browser_opener,
        )

        with self.assertRaises(
            SpotifyConnectionError
        ) as context:
            controller.connect()

        self.assertEqual(
            context.exception.error_code,
            "authorization_failed",
        )

    def test_invalid_token_from_oauth_is_rejected(
        self,
    ):
        factory = FakeOAuthFactory(
            FakeOAuthSession(
                result=FakeOAuthResult(
                    connected=True,
                    token="not-a-token",
                )
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=FakeSessionManager(),
            oauth_session_factory=factory,
            browser_opener=fake_browser_opener,
        )

        with self.assertRaises(
            SpotifyConnectionError
        ) as context:
            controller.connect()

        self.assertEqual(
            context.exception.error_code,
            "authorization_failed",
        )

    def test_persistence_failure_is_wrapped_safely(
        self,
    ):
        access_marker = (
            "dummy-access-secret-never-echo"
        )

        token = SpotifyTokenBundle(
            access_token=access_marker,
            refresh_token=(
                "dummy-refresh-secret-never-echo"
            ),
        )

        manager = FakeSessionManager(
            persist_error=(
                SpotifySessionManagerError(
                    "credential_save_failed",
                    (
                        "simulated "
                        + access_marker
                    ),
                )
            )
        )

        factory = FakeOAuthFactory(
            FakeOAuthSession(
                result=FakeOAuthResult(
                    connected=True,
                    token=token,
                )
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=manager,
            oauth_session_factory=factory,
            browser_opener=fake_browser_opener,
        )

        with self.assertRaises(
            SpotifyConnectionError
        ) as context:
            controller.connect()

        failure = context.exception

        self.assertEqual(
            failure.error_code,
            "credential_save_failed",
        )

        rendered = (
            repr(
                failure
            )
            + str(
                failure
            )
        )

        self.assertNotIn(
            access_marker,
            rendered,
        )

    def test_disconnect_maps_manager_result(
        self,
    ):
        manager = FakeSessionManager()

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=manager,
        )

        result = controller.disconnect()

        self.assertEqual(
            result.status,
            SpotifyConnectionStatus.DISCONNECTED,
        )

        self.assertEqual(
            manager.disconnect_calls,
            1,
        )

    def test_disconnect_failure_is_wrapped_safely(
        self,
    ):
        marker = (
            "sensitive-delete-detail"
        )

        manager = FakeSessionManager(
            disconnect_error=(
                SpotifySessionManagerError(
                    "disconnect_failed",
                    marker,
                )
            )
        )

        controller = SpotifyConnectionController(
            TEST_CLIENT_ID,
            session_manager=manager,
        )

        with self.assertRaises(
            SpotifyConnectionError
        ) as context:
            controller.disconnect()

        failure = context.exception

        self.assertEqual(
            failure.error_code,
            "disconnect_failed",
        )

        self.assertNotIn(
            marker,
            str(
                failure
            ),
        )

    def test_result_repr_hides_credentials(
        self,
    ):
        token = SpotifyTokenBundle(
            access_token=(
                "access-secret-in-controller-result"
            ),
            refresh_token=(
                "refresh-secret-in-controller-result"
            ),
        )

        result = SpotifyConnectionResult(
            status=(
                SpotifyConnectionStatus.CONNECTED
            ),
            token=token,
            message="connected",
        )

        rendered = repr(
            result
        )

        self.assertNotIn(
            "access-secret-in-controller-result",
            rendered,
        )

        self.assertNotIn(
            "refresh-secret-in-controller-result",
            rendered,
        )

    def test_constructor_validates_dependencies(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyConnectionController(
                "",
                session_manager=FakeSessionManager(),
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyConnectionController(
                TEST_CLIENT_ID,
                session_manager=object(),
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyConnectionController(
                TEST_CLIENT_ID,
                session_manager=FakeSessionManager(),
                oauth_session_factory=object(),
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyConnectionController(
                TEST_CLIENT_ID,
                session_manager=FakeSessionManager(),
                browser_opener="not-callable",
            )

        with self.assertRaises(
            ValueError
        ):
            SpotifyConnectionController(
                TEST_CLIENT_ID,
                session_manager=FakeSessionManager(),
                callback_timeout_seconds=0,
            )


class SpotifyConnectionControllerBoundaryTests(
    unittest.TestCase
):
    def test_controller_has_no_qt_settings_browser_or_file_format(
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
            / "connection_controller.py"
        ).read_text(
            encoding="utf-8"
        )

        forbidden = (
            "PyQt",
            "QSettings",
            "webbrowser",
            "os.startfile",
            "spotify_auth.dat",
            "CryptProtectData",
            "CryptUnprotectData",
            "client_secret",
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

    def test_controller_composes_existing_spotify_layers(
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
            / "connection_controller.py"
        ).read_text(
            encoding="utf-8"
        )

        required = (
            "SpotifyOAuthSession",
            "SpotifySessionManager",
            "persist_authorized_token",
            "restore",
            "connect",
            "disconnect",
        )

        for marker in required:
            with self.subTest(
                marker=marker
            ):
                self.assertIn(
                    marker,
                    source,
                )


@unittest.skipUnless(
    os.name == "nt",
    "Integrated Spotify persistence requires Windows",
)
class SpotifyConnectionControllerIntegrationTests(
    unittest.TestCase
):
    def test_controller_restores_real_encrypted_store(
        self,
    ):
        token = make_token(
            suffix="integrated",
            obtained_at=1000.0,
        )

        with TemporaryDirectory() as temp:
            path = (
                Path(
                    temp
                )
                / "spotify_auth.dat"
            )

            store = SpotifyCredentialStore(
                path
            )

            store.save(
                token
            )

            session_manager = (
                SpotifySessionManager(
                    TEST_CLIENT_ID,
                    store=store,
                    token_client=(
                        FakeRefreshClient(
                            make_token(
                                suffix="unused-refresh"
                            )
                        )
                    ),
                    clock=lambda: 1200.0,
                )
            )

            controller = (
                SpotifyConnectionController(
                    TEST_CLIENT_ID,
                    session_manager=(
                        session_manager
                    ),
                )
            )

            result = controller.restore()

            self.assertEqual(
                result.status,
                SpotifyConnectionStatus.CONNECTED,
            )

            self.assertTrue(
                result.connected
            )

            self.assertEqual(
                result.token.access_token,
                token.access_token,
            )

            encrypted = path.read_bytes()

            self.assertNotIn(
                token.access_token.encode(
                    "utf-8"
                ),
                encrypted,
            )

            self.assertNotIn(
                token.refresh_token.encode(
                    "utf-8"
                ),
                encrypted,
            )

            disconnected = (
                controller.disconnect()
            )

            self.assertEqual(
                disconnected.status,
                SpotifyConnectionStatus.DISCONNECTED,
            )

            self.assertFalse(
                path.exists()
            )


if __name__ == "__main__":
    unittest.main()
