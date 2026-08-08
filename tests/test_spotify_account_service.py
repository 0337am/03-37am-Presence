from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest

from src.spotify.account_service import (
    SpotifyAccountService,
    SpotifyAccountServiceError,
    SpotifyAccountServiceResult,
    SpotifyAccountServiceStatus,
)
from src.spotify.models import (
    SpotifyAccount,
    SpotifyTokenBundle,
)
from src.spotify.session_manager import (
    SpotifySessionManagerError,
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiError,
)


def make_token(
    *,
    access_token="test-access-token",
):
    return SpotifyTokenBundle(
        access_token=access_token,
        refresh_token="test-refresh-token",
        token_type="Bearer",
        expires_in=3600,
        granted_scopes=(
            "user-read-private",
        ),
        obtained_at=1000.0,
        authorized_at=900.0,
    )


def make_account():
    return SpotifyAccount(
        account_id="stable-account-id",
        display_name="03:37am",
        user_id="legacy-user-id",
        uri="spotify:user:legacy-user-id",
        profile_url=(
            "https://open.spotify.com/user/"
            "legacy-user-id"
        ),
        image_url=(
            "https://i.scdn.co/image/profile"
        ),
    )


class FakeSessionManager:
    def __init__(
        self,
        result=None,
        error=None,
    ):
        self.result = result
        self.error = error
        self.resolve_calls = 0

    def resolve(
        self,
    ):
        self.resolve_calls += 1

        if self.error is not None:
            raise self.error

        return self.result


class FakeApiClient:
    def __init__(
        self,
        result=None,
        error=None,
    ):
        self.result = (
            result
            if result is not None
            else make_account()
        )

        self.error = error
        self.tokens = []

    def get_current_user_profile(
        self,
        access_token,
    ):
        self.tokens.append(
            access_token
        )

        if self.error is not None:
            raise self.error

        return self.result


class SpotifyAccountServiceResultTests(
    unittest.TestCase
):
    def test_ready_result_requires_account(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyAccountServiceResult(
                status=(
                    SpotifyAccountServiceStatus
                    .READY
                )
            )

    def test_disconnected_result_rejects_account(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyAccountServiceResult(
                status=(
                    SpotifyAccountServiceStatus
                    .DISCONNECTED
                ),
                account=make_account(),
            )

    def test_result_is_credential_free(
        self,
    ):
        result = SpotifyAccountServiceResult(
            status=(
                SpotifyAccountServiceStatus
                .READY
            ),
            account=make_account(),
            message="ready",
        )

        self.assertFalse(
            hasattr(
                result,
                "token",
            )
        )

        self.assertFalse(
            hasattr(
                result,
                "access_token",
            )
        )

        self.assertFalse(
            hasattr(
                result,
                "refresh_token",
            )
        )

        rendered = repr(
            result
        )

        self.assertNotIn(
            "test-access-token",
            rendered,
        )

        self.assertNotIn(
            "test-refresh-token",
            rendered,
        )

    def test_result_properties(
        self,
    ):
        ready = SpotifyAccountServiceResult(
            status=(
                SpotifyAccountServiceStatus
                .READY
            ),
            account=make_account(),
        )

        refreshed = SpotifyAccountServiceResult(
            status=(
                SpotifyAccountServiceStatus
                .REFRESHED
            ),
            account=make_account(),
        )

        reauth = SpotifyAccountServiceResult(
            status=(
                SpotifyAccountServiceStatus
                .REAUTHORIZATION_REQUIRED
            )
        )

        self.assertTrue(
            ready.connected
        )

        self.assertFalse(
            ready.refreshed
        )

        self.assertTrue(
            refreshed.connected
        )

        self.assertTrue(
            refreshed.refreshed
        )

        self.assertTrue(
            reauth.requires_reauthorization
        )


class SpotifyAccountServiceTests(
    unittest.TestCase
):
    def make_service(
        self,
        *,
        status=SpotifySessionStatus.READY,
        token=None,
        api_client=None,
    ):
        if token is None:
            token = make_token()

        manager = FakeSessionManager(
            SimpleNamespace(
                status=status,
                token=token,
            )
        )

        api = (
            api_client
            if api_client is not None
            else FakeApiClient()
        )

        return (
            manager,
            api,
            SpotifyAccountService(
                manager,
                api_client=api,
            ),
        )

    def test_constructor_validates_session_manager(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyAccountService(
                object(),
                api_client=FakeApiClient(),
            )

    def test_constructor_validates_api_client(
        self,
    ):
        manager = FakeSessionManager()

        with self.assertRaises(
            TypeError
        ):
            SpotifyAccountService(
                manager,
                api_client=object(),
            )

    def test_disconnected_session_does_not_call_api(
        self,
    ):
        manager, api, service = (
            self.make_service(
                status=(
                    SpotifySessionStatus
                    .DISCONNECTED
                ),
            )
        )

        result = (
            service.get_current_account()
        )

        self.assertEqual(
            result.status,
            (
                SpotifyAccountServiceStatus
                .DISCONNECTED
            ),
        )

        self.assertFalse(
            result.connected
        )

        self.assertEqual(
            api.tokens,
            [],
        )

    def test_reauthorization_session_does_not_call_api(
        self,
    ):
        manager, api, service = (
            self.make_service(
                status=(
                    SpotifySessionStatus
                    .REAUTHORIZATION_REQUIRED
                ),
            )
        )

        result = (
            service.get_current_account()
        )

        self.assertEqual(
            result.status,
            (
                SpotifyAccountServiceStatus
                .REAUTHORIZATION_REQUIRED
            ),
        )

        self.assertTrue(
            result.requires_reauthorization
        )

        self.assertEqual(
            api.tokens,
            [],
        )

    def test_ready_session_loads_current_account(
        self,
    ):
        manager, api, service = (
            self.make_service()
        )

        result = (
            service.get_current_account()
        )

        self.assertEqual(
            manager.resolve_calls,
            1,
        )

        self.assertEqual(
            api.tokens,
            [
                "test-access-token",
            ],
        )

        self.assertEqual(
            result.status,
            (
                SpotifyAccountServiceStatus
                .READY
            ),
        )

        self.assertEqual(
            result.account,
            make_account(),
        )

    def test_refreshed_session_is_preserved(
        self,
    ):
        manager, api, service = (
            self.make_service(
                status=(
                    SpotifySessionStatus
                    .REFRESHED
                ),
            )
        )

        result = (
            service.get_current_account()
        )

        self.assertEqual(
            result.status,
            (
                SpotifyAccountServiceStatus
                .REFRESHED
            ),
        )

        self.assertTrue(
            result.refreshed
        )

        self.assertEqual(
            api.tokens,
            [
                "test-access-token",
            ],
        )

    def test_invalid_session_state_is_rejected(
        self,
    ):
        manager = FakeSessionManager(
            SimpleNamespace(
                status="unexpected",
                token=make_token(),
            )
        )

        service = SpotifyAccountService(
            manager,
            api_client=FakeApiClient(),
        )

        with self.assertRaises(
            SpotifyAccountServiceError
        ) as caught:
            service.get_current_account()

        self.assertEqual(
            caught.exception.error_code,
            "invalid_session_state",
        )

    def test_missing_token_is_rejected(
        self,
    ):
        manager = FakeSessionManager(
            SimpleNamespace(
                status=SpotifySessionStatus.READY,
                token=None,
            )
        )

        api = FakeApiClient()

        service = SpotifyAccountService(
            manager,
            api_client=api,
        )

        with self.assertRaises(
            SpotifyAccountServiceError
        ) as caught:
            service.get_current_account()

        self.assertEqual(
            caught.exception.error_code,
            "invalid_session",
        )

        self.assertEqual(
            api.tokens,
            [],
        )

    def test_session_manager_error_is_wrapped(
        self,
    ):
        manager = FakeSessionManager(
            error=SpotifySessionManagerError(
                "simulated",
                "internal sensitive detail",
            )
        )

        service = SpotifyAccountService(
            manager,
            api_client=FakeApiClient(),
        )

        with self.assertRaises(
            SpotifyAccountServiceError
        ) as caught:
            service.get_current_account()

        self.assertEqual(
            caught.exception.error_code,
            "session_error",
        )

        self.assertNotIn(
            "internal sensitive detail",
            str(
                caught.exception
            ),
        )

    def test_unexpected_session_error_is_safe(
        self,
    ):
        manager = FakeSessionManager(
            error=RuntimeError(
                "test-access-token"
            )
        )

        service = SpotifyAccountService(
            manager,
            api_client=FakeApiClient(),
        )

        with self.assertRaises(
            SpotifyAccountServiceError
        ) as caught:
            service.get_current_account()

        self.assertEqual(
            caught.exception.error_code,
            "session_error",
        )

        self.assertNotIn(
            "test-access-token",
            str(
                caught.exception
            ),
        )

    def test_web_api_401_becomes_reauthorization(
        self,
    ):
        api = FakeApiClient(
            error=SpotifyWebApiError(
                "reauthorization_required",
                (
                    "Spotify authorization is "
                    "no longer valid."
                ),
            )
        )

        manager, api, service = (
            self.make_service(
                api_client=api
            )
        )

        result = (
            service.get_current_account()
        )

        self.assertEqual(
            result.status,
            (
                SpotifyAccountServiceStatus
                .REAUTHORIZATION_REQUIRED
            ),
        )

        self.assertIsNone(
            result.account
        )

    def test_rate_limit_metadata_is_preserved(
        self,
    ):
        api = FakeApiClient(
            error=SpotifyWebApiError(
                "rate_limited",
                (
                    "Spotify is rate limiting "
                    "requests."
                ),
                retry_after_seconds=12,
            )
        )

        manager, api, service = (
            self.make_service(
                api_client=api
            )
        )

        with self.assertRaises(
            SpotifyAccountServiceError
        ) as caught:
            service.get_current_account()

        self.assertEqual(
            caught.exception.error_code,
            "rate_limited",
        )

        self.assertEqual(
            caught.exception.retry_after_seconds,
            12,
        )

    def test_api_timeout_is_preserved_safely(
        self,
    ):
        api = FakeApiClient(
            error=SpotifyWebApiError(
                "timeout",
                (
                    "Spotify API request "
                    "timed out."
                ),
            )
        )

        manager, api, service = (
            self.make_service(
                api_client=api
            )
        )

        with self.assertRaises(
            SpotifyAccountServiceError
        ) as caught:
            service.get_current_account()

        self.assertEqual(
            caught.exception.error_code,
            "timeout",
        )

    def test_unexpected_api_error_does_not_leak_token(
        self,
    ):
        api = FakeApiClient(
            error=RuntimeError(
                "test-access-token"
            )
        )

        manager, api, service = (
            self.make_service(
                api_client=api
            )
        )

        with self.assertRaises(
            SpotifyAccountServiceError
        ) as caught:
            service.get_current_account()

        self.assertEqual(
            caught.exception.error_code,
            "api_error",
        )

        self.assertNotIn(
            "test-access-token",
            str(
                caught.exception
            ),
        )

    def test_invalid_account_result_is_rejected(
        self,
    ):
        api = FakeApiClient(
            result={
                "account_id": "wrong-layer",
            }
        )

        manager, api, service = (
            self.make_service(
                api_client=api
            )
        )

        with self.assertRaises(
            SpotifyAccountServiceError
        ) as caught:
            service.get_current_account()

        self.assertEqual(
            caught.exception.error_code,
            "invalid_account",
        )


class SpotifyAccountServiceBoundaryTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.source = (
            Path(
                __file__
            )
            .resolve()
            .parents[1]
            / "src"
            / "spotify"
            / "account_service.py"
        ).read_text(
            encoding="utf-8"
        )

    def test_service_composes_session_and_web_api_layers(
        self,
    ):
        self.assertIn(
            "SpotifySessionStatus",
            self.source,
        )

        self.assertIn(
            "SpotifyWebApiClient",
            self.source,
        )

        self.assertIn(
            "get_current_user_profile",
            self.source,
        )

    def test_service_does_not_own_ui_oauth_or_storage(
        self,
    ):
        forbidden = (
            "PyQt6",
            "QSettings",
            "SpotifyCredentialStore",
            "windows_dpapi",
            "spotify_auth.dat",
            "oauth_callback",
            "SpotifyOAuthSession",
            "QDesktopServices",
            "webbrowser",
            "os.startfile",
            "client_secret",
            "print(",
            "logging.",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    self.source,
                )

    def test_service_result_has_no_credential_field(
        self,
    ):
        start = self.source.index(
            "class SpotifyAccountServiceResult:"
        )

        end = self.source.index(
            "class SpotifyAccountService:",
            start,
        )

        result_source = self.source[
            start:end
        ]

        self.assertNotIn(
            "token:",
            result_source,
        )

        self.assertNotIn(
            "access_token:",
            result_source,
        )

        self.assertNotIn(
            "refresh_token:",
            result_source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
