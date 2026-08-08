from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


from src.spotify.credential_store import (
    SpotifyCredentialStore,
)
from src.spotify.credential_store import (
    SpotifyCredentialStoreError,
)
from src.spotify.models import (
    SpotifyTokenBundle,
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
from src.spotify.token_client import (
    SpotifyTokenError,
)


TEST_CLIENT_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)


def make_token(
    *,
    suffix: str = "old",
    obtained_at: float = 1000.0,
    expires_in: int = 3600,
    refresh_token=(
        "dummy-refresh-secret-old"
    ),
) -> SpotifyTokenBundle:
    return SpotifyTokenBundle(
        access_token=(
            f"dummy-access-secret-{suffix}"
        ),
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
        granted_scopes=(
            "user-read-private",
        ),
        obtained_at=obtained_at,
        authorized_at=900.0,
    )


class FakeStore:
    def __init__(
        self,
        *,
        token=None,
        load_error=None,
        save_error=None,
        delete_error=None,
    ):
        self.token = token
        self.load_error = load_error
        self.save_error = save_error
        self.delete_error = delete_error

        self.load_calls = 0
        self.save_calls = []
        self.delete_calls = 0

    def load(
        self,
    ):
        self.load_calls += 1

        if self.load_error is not None:
            raise self.load_error

        return self.token

    def save(
        self,
        token,
    ):
        self.save_calls.append(
            token
        )

        if self.save_error is not None:
            raise self.save_error

        self.token = token

    def delete(
        self,
    ):
        self.delete_calls += 1

        if self.delete_error is not None:
            raise self.delete_error

        existed = (
            self.token is not None
        )

        self.token = None

        return existed


class FakeTokenClient:
    def __init__(
        self,
        *,
        result=None,
        error=None,
    ):
        self.result = result
        self.error = error
        self.calls = []

    def refresh_access_token(
        self,
        token,
    ):
        self.calls.append(
            token
        )

        if self.error is not None:
            raise self.error

        if self.result is None:
            raise AssertionError(
                "Fake refresh result was not configured."
            )

        return self.result


class SpotifySessionManagerTests(
    unittest.TestCase
):
    def test_missing_credentials_are_disconnected(
        self,
    ):
        store = FakeStore()

        token_client = FakeTokenClient()

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=token_client,
            clock=lambda: 1000.0,
        )

        result = manager.resolve()

        self.assertEqual(
            result.status,
            SpotifySessionStatus.DISCONNECTED,
        )

        self.assertFalse(
            result.connected
        )

        self.assertIsNone(
            result.token
        )

        self.assertEqual(
            token_client.calls,
            [],
        )

    def test_fresh_token_is_ready_without_refresh(
        self,
    ):
        token = make_token(
            obtained_at=1000.0
        )

        store = FakeStore(
            token=token
        )

        token_client = FakeTokenClient()

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=token_client,
            clock=lambda: 1200.0,
        )

        result = manager.resolve()

        self.assertEqual(
            result.status,
            SpotifySessionStatus.READY,
        )

        self.assertTrue(
            result.connected
        )

        self.assertIs(
            result.token,
            token,
        )

        self.assertEqual(
            token_client.calls,
            [],
        )

        self.assertEqual(
            store.save_calls,
            [],
        )

    def test_token_inside_refresh_skew_is_refreshed(
        self,
    ):
        original = make_token(
            obtained_at=1000.0
        )

        refreshed = make_token(
            suffix="new",
            obtained_at=4545.0,
            refresh_token=(
                "dummy-refresh-secret-new"
            ),
        )

        store = FakeStore(
            token=original
        )

        token_client = FakeTokenClient(
            result=refreshed
        )

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=token_client,
            clock=lambda: 4540.0,
            refresh_skew_seconds=60.0,
        )

        result = manager.resolve()

        self.assertEqual(
            result.status,
            SpotifySessionStatus.REFRESHED,
        )

        self.assertTrue(
            result.connected
        )

        self.assertTrue(
            result.refreshed
        )

        self.assertIs(
            result.token,
            refreshed,
        )

        self.assertEqual(
            token_client.calls,
            [
                original,
            ],
        )

        self.assertEqual(
            store.save_calls,
            [
                refreshed,
            ],
        )

    def test_expired_token_is_refreshed_and_saved(
        self,
    ):
        original = make_token(
            obtained_at=1000.0
        )

        refreshed = make_token(
            suffix="refreshed",
            obtained_at=5000.0,
        )

        store = FakeStore(
            token=original
        )

        token_client = FakeTokenClient(
            result=refreshed
        )

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=token_client,
            clock=lambda: 5000.0,
        )

        result = manager.resolve()

        self.assertEqual(
            result.status,
            SpotifySessionStatus.REFRESHED,
        )

        self.assertIs(
            result.token,
            refreshed,
        )

        self.assertIs(
            store.token,
            refreshed,
        )

    def test_missing_refresh_token_requires_reauthorization_and_clears_store(
        self,
    ):
        token = make_token(
            refresh_token=""
        )

        store = FakeStore(
            token=token
        )

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=FakeTokenClient(),
            clock=lambda: 5000.0,
        )

        result = manager.resolve()

        self.assertTrue(
            result.requires_reauthorization
        )

        self.assertIsNone(
            result.token
        )

        self.assertEqual(
            store.delete_calls,
            1,
        )

        self.assertIsNone(
            store.token
        )

    def test_invalid_grant_requires_reauthorization_and_clears_store(
        self,
    ):
        token = make_token()

        store = FakeStore(
            token=token
        )

        token_client = FakeTokenClient(
            error=SpotifyTokenError(
                "reauthorization_required",
                (
                    "Spotify authorization "
                    "must be renewed."
                ),
                spotify_error="invalid_grant",
            )
        )

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=token_client,
            clock=lambda: 5000.0,
        )

        result = manager.resolve()

        self.assertTrue(
            result.requires_reauthorization
        )

        self.assertEqual(
            store.delete_calls,
            1,
        )

        self.assertIsNone(
            store.token
        )

    def test_transient_refresh_failure_preserves_credentials(
        self,
    ):
        token = make_token()

        store = FakeStore(
            token=token
        )

        token_client = FakeTokenClient(
            error=SpotifyTokenError(
                "network_error",
                "Could not reach Spotify.",
            )
        )

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=token_client,
            clock=lambda: 5000.0,
        )

        with self.assertRaises(
            SpotifySessionManagerError
        ) as context:
            manager.resolve()

        failure = context.exception

        self.assertEqual(
            failure.error_code,
            "refresh_failed",
        )

        self.assertEqual(
            store.delete_calls,
            0,
        )

        self.assertIs(
            store.token,
            token,
        )

        self.assertIsNone(
            failure.__cause__
        )

    def test_corrupt_store_becomes_reauthorization_required(
        self,
    ):
        store = FakeStore(
            load_error=(
                SpotifyCredentialStoreError(
                    "credential_corrupt",
                    (
                        "Saved Spotify credentials "
                        "are invalid."
                    ),
                )
            )
        )

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=FakeTokenClient(),
        )

        result = manager.resolve()

        self.assertTrue(
            result.requires_reauthorization
        )

        self.assertEqual(
            result.status,
            (
                SpotifySessionStatus
                .REAUTHORIZATION_REQUIRED
            ),
        )

    def test_non_corruption_load_failure_is_wrapped(
        self,
    ):
        store = FakeStore(
            load_error=(
                SpotifyCredentialStoreError(
                    "load_failed",
                    "simulated sensitive store detail",
                )
            )
        )

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=FakeTokenClient(),
        )

        with self.assertRaises(
            SpotifySessionManagerError
        ) as context:
            manager.resolve()

        failure = context.exception

        self.assertEqual(
            failure.error_code,
            "credential_load_failed",
        )

        self.assertNotIn(
            "sensitive store detail",
            str(
                failure
            ),
        )

        self.assertIsNone(
            failure.__cause__
        )

    def test_refreshed_token_save_failure_is_safe(
        self,
    ):
        original = make_token()

        refreshed = make_token(
            suffix="new"
        )

        store = FakeStore(
            token=original,
            save_error=(
                SpotifyCredentialStoreError(
                    "save_failed",
                    "simulated storage detail",
                )
            ),
        )

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=(
                FakeTokenClient(
                    result=refreshed
                )
            ),
            clock=lambda: 5000.0,
        )

        with self.assertRaises(
            SpotifySessionManagerError
        ) as context:
            manager.resolve()

        failure = context.exception

        self.assertEqual(
            failure.error_code,
            "credential_save_failed",
        )

        self.assertNotIn(
            "simulated storage detail",
            str(
                failure
            ),
        )

    def test_persist_authorized_token_saves_securely(
        self,
    ):
        token = make_token()

        store = FakeStore()

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=FakeTokenClient(),
        )

        result = (
            manager.persist_authorized_token(
                token
            )
        )

        self.assertEqual(
            result.status,
            SpotifySessionStatus.READY,
        )

        self.assertIs(
            result.token,
            token,
        )

        self.assertEqual(
            store.save_calls,
            [
                token,
            ],
        )

    def test_persist_authorized_token_failure_is_safe(
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

        store = FakeStore(
            save_error=(
                SpotifyCredentialStoreError(
                    "save_failed",
                    (
                        "simulated "
                        + access_marker
                    ),
                )
            )
        )

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=FakeTokenClient(),
        )

        with self.assertRaises(
            SpotifySessionManagerError
        ) as context:
            manager.persist_authorized_token(
                token
            )

        rendered = (
            repr(
                context.exception
            )
            + str(
                context.exception
            )
        )

        self.assertNotIn(
            access_marker,
            rendered,
        )

    def test_disconnect_is_idempotent(
        self,
    ):
        store = FakeStore(
            token=make_token()
        )

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=FakeTokenClient(),
        )

        first = manager.disconnect()
        second = manager.disconnect()

        self.assertEqual(
            first.status,
            SpotifySessionStatus.DISCONNECTED,
        )

        self.assertEqual(
            second.status,
            SpotifySessionStatus.DISCONNECTED,
        )

        self.assertEqual(
            store.delete_calls,
            2,
        )

    def test_delete_failure_blocks_clean_reauthorization_state(
        self,
    ):
        token = make_token(
            refresh_token=""
        )

        store = FakeStore(
            token=token,
            delete_error=(
                SpotifyCredentialStoreError(
                    "delete_failed",
                    "simulated deletion detail",
                )
            ),
        )

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=store,
            token_client=FakeTokenClient(),
            clock=lambda: 5000.0,
        )

        with self.assertRaises(
            SpotifySessionManagerError
        ) as context:
            manager.resolve()

        self.assertEqual(
            context.exception.error_code,
            "credential_delete_failed",
        )

    def test_result_repr_hides_credentials(
        self,
    ):
        token = SpotifyTokenBundle(
            access_token=(
                "access-secret-in-result"
            ),
            refresh_token=(
                "refresh-secret-in-result"
            ),
        )

        result = SpotifySessionResult(
            status=SpotifySessionStatus.READY,
            token=token,
            message="ready",
        )

        rendered = repr(
            result
        )

        self.assertNotIn(
            "access-secret-in-result",
            rendered,
        )

        self.assertNotIn(
            "refresh-secret-in-result",
            rendered,
        )

    def test_constructor_validates_dependencies(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifySessionManager(
                "",
                store=FakeStore(),
                token_client=FakeTokenClient(),
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifySessionManager(
                TEST_CLIENT_ID,
                store=object(),
                token_client=FakeTokenClient(),
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifySessionManager(
                TEST_CLIENT_ID,
                store=FakeStore(),
                token_client=object(),
            )

        with self.assertRaises(
            ValueError
        ):
            SpotifySessionManager(
                TEST_CLIENT_ID,
                store=FakeStore(),
                token_client=FakeTokenClient(),
                refresh_skew_seconds=-1,
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifySessionManager(
                TEST_CLIENT_ID,
                store=FakeStore(),
                token_client=FakeTokenClient(),
                clock=None,
            )

    def test_clock_failure_is_friendly(
        self,
    ):
        token = make_token()

        manager = SpotifySessionManager(
            TEST_CLIENT_ID,
            store=FakeStore(
                token=token
            ),
            token_client=FakeTokenClient(),
            clock=(
                lambda: float(
                    "nan"
                )
            ),
        )

        with self.assertRaises(
            SpotifySessionManagerError
        ) as context:
            manager.resolve()

        self.assertEqual(
            context.exception.error_code,
            "clock_failed",
        )


class SpotifySessionManagerBoundaryTests(
    unittest.TestCase
):
    def test_manager_has_no_browser_settings_or_direct_file_format(
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
            / "session_manager.py"
        ).read_text(
            encoding="utf-8"
        )

        forbidden = (
            "webbrowser",
            "os.startfile",
            "QSettings",
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

    def test_manager_composes_store_and_token_client_layers(
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
            / "session_manager.py"
        ).read_text(
            encoding="utf-8"
        )

        required = (
            "SpotifyCredentialStore",
            "SpotifyTokenClient",
            "refresh_access_token",
            "REAUTHORIZATION_REQUIRED",
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
    "Integrated credential lifecycle requires Windows",
)
class SpotifySessionManagerIntegrationTests(
    unittest.TestCase
):
    def test_real_encrypted_store_composes_with_refresh_lifecycle(
        self,
    ):
        original = make_token(
            obtained_at=1000.0
        )

        refreshed = make_token(
            suffix="integrated-refreshed",
            obtained_at=5000.0,
            refresh_token=(
                "dummy-refresh-secret-integrated"
            ),
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
                original
            )

            token_client = FakeTokenClient(
                result=refreshed
            )

            manager = SpotifySessionManager(
                TEST_CLIENT_ID,
                store=store,
                token_client=token_client,
                clock=lambda: 5000.0,
            )

            result = manager.resolve()

            self.assertEqual(
                result.status,
                SpotifySessionStatus.REFRESHED,
            )

            loaded = store.load()

            self.assertIsNotNone(
                loaded
            )

            self.assertEqual(
                loaded.access_token,
                refreshed.access_token,
            )

            encrypted = path.read_bytes()

            self.assertNotIn(
                refreshed.access_token.encode(
                    "utf-8"
                ),
                encrypted,
            )

            self.assertNotIn(
                refreshed.refresh_token.encode(
                    "utf-8"
                ),
                encrypted,
            )

            disconnected = (
                manager.disconnect()
            )

            self.assertEqual(
                disconnected.status,
                SpotifySessionStatus.DISCONNECTED,
            )

            self.assertFalse(
                path.exists()
            )


if __name__ == "__main__":
    unittest.main()
