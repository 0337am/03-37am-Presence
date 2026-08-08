from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs
from urllib.parse import urlencode
from urllib.parse import urlsplit
import unittest

from src.spotify.constants import (
    SPOTIFY_CONNECT_SCOPES,
)
from src.spotify.models import (
    SpotifyTokenBundle,
)
from src.spotify.oauth_callback import (
    LoopbackCallbackError,
)
from src.spotify.oauth_callback import (
    LoopbackCallbackResult,
)
from src.spotify.oauth_callback import (
    LoopbackCallbackTimeout,
)
from src.spotify.oauth_session import (
    SpotifyOAuthSession,
)
from src.spotify.oauth_session import (
    SpotifyOAuthSessionError,
)
from src.spotify.oauth_session import (
    SpotifyOAuthSessionResult,
)
from src.spotify.oauth_session import (
    SpotifyOAuthSessionStatus,
)
from src.spotify.token_client import (
    SpotifyTokenError,
)


TEST_CLIENT_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)

TEST_REDIRECT_URI = (
    "http://127.0.0.1:54321/callback"
)


def authorization_state(
    url: str,
) -> str:
    parameters = parse_qs(
        urlsplit(
            url
        ).query
    )

    return parameters[
        "state"
    ][0]


class FakeCallbackServer:
    def __init__(
        self,
        *,
        redirect_uri=TEST_REDIRECT_URI,
        wait_error=None,
    ):
        self.redirect_uri = redirect_uri
        self.wait_error = wait_error
        self.callback_url = None
        self.wait_calls = []
        self.entered = False
        self.closed = False

    def set_success(
        self,
        authorization_url: str,
        *,
        code="authorization-code",
    ):
        state = authorization_state(
            authorization_url
        )

        query = urlencode(
            {
                "code": code,
                "state": state,
            }
        )

        self.callback_url = (
            f"{self.redirect_uri}?"
            f"{query}"
        )

    def set_denied(
        self,
        authorization_url: str,
    ):
        state = authorization_state(
            authorization_url
        )

        query = urlencode(
            {
                "error": "access_denied",
                "state": state,
                "error_description": (
                    "User declined Spotify access"
                ),
            }
        )

        self.callback_url = (
            f"{self.redirect_uri}?"
            f"{query}"
        )

    def set_wrong_state(
        self,
    ):
        query = urlencode(
            {
                "code": "authorization-code",
                "state": ("Z" * 43),
            }
        )

        self.callback_url = (
            f"{self.redirect_uri}?"
            f"{query}"
        )

    def wait_for_callback(
        self,
        *,
        timeout_seconds,
    ):
        self.wait_calls.append(
            timeout_seconds
        )

        if self.wait_error is not None:
            raise self.wait_error

        if self.callback_url is None:
            raise AssertionError(
                "Fake callback URL was not configured"
            )

        target = urlsplit(
            self.callback_url
        )

        request_target = (
            target.path
            + (
                f"?{target.query}"
                if target.query
                else ""
            )
        )

        return LoopbackCallbackResult(
            callback_url=self.callback_url,
            request_target=request_target,
        )

    def __enter__(
        self,
    ):
        self.entered = True
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.closed = True
        return False


class FakeBrowser:
    def __init__(
        self,
        *,
        result=True,
        error=None,
        on_open=None,
    ):
        self.result = result
        self.error = error
        self.on_open = on_open
        self.urls = []

    def __call__(
        self,
        url,
    ):
        self.urls.append(
            url
        )

        if self.error is not None:
            raise self.error

        if self.on_open is not None:
            self.on_open(
                url
            )

        return self.result


class FakeTokenClient:
    def __init__(
        self,
        *,
        result=None,
        error=None,
    ):
        if result is None:
            result = SpotifyTokenBundle(
                access_token="access-secret",
                refresh_token="refresh-secret",
                granted_scopes=(
                    "user-read-private",
                ),
                obtained_at=100.0,
                authorized_at=100.0,
            )

        self.result = result
        self.error = error
        self.calls = []

    def exchange_authorization_code(
        self,
        code,
        redirect_uri,
        code_verifier,
        *,
        requested_scopes,
    ):
        self.calls.append(
            {
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
                "requested_scopes": tuple(
                    requested_scopes
                ),
            }
        )

        if self.error is not None:
            raise self.error

        return self.result


class SpotifyOAuthSessionTests(
    unittest.TestCase
):
    def test_successful_session_coordinates_entire_flow(
        self,
    ):
        server = FakeCallbackServer()

        browser = FakeBrowser(
            on_open=server.set_success
        )

        token_client = FakeTokenClient()

        session = SpotifyOAuthSession(
            TEST_CLIENT_ID,
            browser_opener=browser,
            callback_server_factory=(
                lambda: server
            ),
            token_client=token_client,
            callback_timeout_seconds=17.5,
        )

        result = session.connect()

        self.assertTrue(
            result.connected
        )

        self.assertFalse(
            result.denied
        )

        self.assertIs(
            result.token,
            token_client.result,
        )

        self.assertEqual(
            len(
                browser.urls
            ),
            1,
        )

        authorization_url = (
            browser.urls[0]
        )

        query = parse_qs(
            urlsplit(
                authorization_url
            ).query
        )

        self.assertEqual(
            query[
                "client_id"
            ],
            [
                TEST_CLIENT_ID,
            ],
        )

        self.assertEqual(
            query[
                "redirect_uri"
            ],
            [
                TEST_REDIRECT_URI,
            ],
        )

        self.assertEqual(
            query[
                "scope"
            ],
            [
                "user-read-private",
            ],
        )

        self.assertEqual(
            query[
                "code_challenge_method"
            ],
            [
                "S256",
            ],
        )

        self.assertNotIn(
            (
                "client_"
                + "secret"
            ),
            query,
        )

        self.assertEqual(
            server.wait_calls,
            [
                17.5,
            ],
        )

        self.assertTrue(
            server.entered
        )

        self.assertTrue(
            server.closed
        )

        self.assertEqual(
            len(
                token_client.calls
            ),
            1,
        )

        token_call = (
            token_client.calls[0]
        )

        self.assertEqual(
            token_call[
                "code"
            ],
            "authorization-code",
        )

        self.assertEqual(
            token_call[
                "redirect_uri"
            ],
            TEST_REDIRECT_URI,
        )

        self.assertEqual(
            token_call[
                "requested_scopes"
            ],
            SPOTIFY_CONNECT_SCOPES,
        )

        self.assertGreaterEqual(
            len(
                token_call[
                    "code_verifier"
                ]
            ),
            43,
        )

    def test_user_denial_returns_clean_denied_result(
        self,
    ):
        server = FakeCallbackServer()

        browser = FakeBrowser(
            on_open=server.set_denied
        )

        token_client = FakeTokenClient()

        session = SpotifyOAuthSession(
            TEST_CLIENT_ID,
            browser_opener=browser,
            callback_server_factory=(
                lambda: server
            ),
            token_client=token_client,
        )

        result = session.connect()

        self.assertTrue(
            result.denied
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

        self.assertNotIn(
            "User declined Spotify access",
            result.message,
        )

        self.assertTrue(
            server.closed
        )

    def test_browser_false_result_aborts_and_closes_listener(
        self,
    ):
        server = FakeCallbackServer()

        browser = FakeBrowser(
            result=False
        )

        token_client = FakeTokenClient()

        session = SpotifyOAuthSession(
            TEST_CLIENT_ID,
            browser_opener=browser,
            callback_server_factory=(
                lambda: server
            ),
            token_client=token_client,
        )

        with self.assertRaises(
            SpotifyOAuthSessionError
        ) as context:
            session.connect()

        self.assertEqual(
            context.exception.error_code,
            "browser_open_failed",
        )

        self.assertEqual(
            server.wait_calls,
            [],
        )

        self.assertEqual(
            token_client.calls,
            [],
        )

        self.assertTrue(
            server.closed
        )

    def test_browser_exception_is_friendly_and_closes_listener(
        self,
    ):
        server = FakeCallbackServer()

        browser = FakeBrowser(
            error=RuntimeError(
                "browser contained secret detail"
            )
        )

        session = SpotifyOAuthSession(
            TEST_CLIENT_ID,
            browser_opener=browser,
            callback_server_factory=(
                lambda: server
            ),
            token_client=FakeTokenClient(),
        )

        with self.assertRaises(
            SpotifyOAuthSessionError
        ) as context:
            session.connect()

        failure = context.exception

        self.assertEqual(
            failure.error_code,
            "browser_open_failed",
        )

        self.assertNotIn(
            "secret detail",
            str(
                failure
            ),
        )

        self.assertTrue(
            server.closed
        )

    def test_callback_timeout_is_friendly(
        self,
    ):
        server = FakeCallbackServer(
            wait_error=(
                LoopbackCallbackTimeout(
                    "provider timeout detail"
                )
            )
        )

        session = SpotifyOAuthSession(
            TEST_CLIENT_ID,
            browser_opener=(
                FakeBrowser()
            ),
            callback_server_factory=(
                lambda: server
            ),
            token_client=FakeTokenClient(),
        )

        with self.assertRaises(
            SpotifyOAuthSessionError
        ) as context:
            session.connect()

        failure = context.exception

        self.assertEqual(
            failure.error_code,
            "callback_timeout",
        )

        self.assertNotIn(
            "provider timeout detail",
            str(
                failure
            ),
        )

        self.assertTrue(
            server.closed
        )

    def test_callback_transport_error_is_friendly(
        self,
    ):
        server = FakeCallbackServer(
            wait_error=(
                LoopbackCallbackError(
                    "local transport detail"
                )
            )
        )

        session = SpotifyOAuthSession(
            TEST_CLIENT_ID,
            browser_opener=(
                FakeBrowser()
            ),
            callback_server_factory=(
                lambda: server
            ),
            token_client=FakeTokenClient(),
        )

        with self.assertRaises(
            SpotifyOAuthSessionError
        ) as context:
            session.connect()

        self.assertEqual(
            context.exception.error_code,
            "callback_error",
        )

        self.assertNotIn(
            "local transport detail",
            str(
                context.exception
            ),
        )

        self.assertTrue(
            server.closed
        )

    def test_wrong_callback_state_is_rejected_before_token_exchange(
        self,
    ):
        server = FakeCallbackServer()

        browser = FakeBrowser(
            on_open=(
                lambda url: (
                    server.set_wrong_state()
                )
            )
        )

        token_client = FakeTokenClient()

        session = SpotifyOAuthSession(
            TEST_CLIENT_ID,
            browser_opener=browser,
            callback_server_factory=(
                lambda: server
            ),
            token_client=token_client,
        )

        with self.assertRaises(
            SpotifyOAuthSessionError
        ) as context:
            session.connect()

        self.assertEqual(
            context.exception.error_code,
            "invalid_callback",
        )

        self.assertEqual(
            token_client.calls,
            [],
        )

        self.assertTrue(
            server.closed
        )

    def test_token_exchange_error_is_forwarded_safely(
        self,
    ):
        server = FakeCallbackServer()

        browser = FakeBrowser(
            on_open=server.set_success
        )

        token_client = FakeTokenClient(
            error=SpotifyTokenError(
                "network_error",
                "Could not reach Spotify.",
                spotify_error=(
                    "server_internal_detail"
                ),
            )
        )

        session = SpotifyOAuthSession(
            TEST_CLIENT_ID,
            browser_opener=browser,
            callback_server_factory=(
                lambda: server
            ),
            token_client=token_client,
        )

        with self.assertRaises(
            SpotifyOAuthSessionError
        ) as context:
            session.connect()

        failure = context.exception

        self.assertEqual(
            failure.error_code,
            "network_error",
        )

        self.assertEqual(
            str(
                failure
            ),
            "Could not reach Spotify.",
        )

        self.assertNotIn(
            "server_internal_detail",
            str(
                failure
            ),
        )

        self.assertTrue(
            server.closed
        )

    def test_invalid_token_result_is_rejected(
        self,
    ):
        server = FakeCallbackServer()

        browser = FakeBrowser(
            on_open=server.set_success
        )

        token_client = FakeTokenClient(
            result="not-a-token"
        )

        session = SpotifyOAuthSession(
            TEST_CLIENT_ID,
            browser_opener=browser,
            callback_server_factory=(
                lambda: server
            ),
            token_client=token_client,
        )

        with self.assertRaises(
            SpotifyOAuthSessionError
        ) as context:
            session.connect()

        self.assertEqual(
            context.exception.error_code,
            "invalid_token_result",
        )

        self.assertTrue(
            server.closed
        )

    def test_constructor_validates_dependencies_without_network(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyOAuthSession(
                "",
                browser_opener=(
                    lambda url: True
                ),
                token_client=FakeTokenClient(),
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyOAuthSession(
                TEST_CLIENT_ID,
                browser_opener=None,
                token_client=FakeTokenClient(),
            )

        with self.assertRaises(
            ValueError
        ):
            SpotifyOAuthSession(
                TEST_CLIENT_ID,
                browser_opener=(
                    lambda url: True
                ),
                callback_timeout_seconds=0,
                token_client=FakeTokenClient(),
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyOAuthSession(
                TEST_CLIENT_ID,
                browser_opener=(
                    lambda url: True
                ),
                callback_server_factory=None,
                token_client=FakeTokenClient(),
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyOAuthSession(
                TEST_CLIENT_ID,
                browser_opener=(
                    lambda url: True
                ),
                token_client=object(),
            )

    def test_result_repr_hides_token_credentials(
        self,
    ):
        token = SpotifyTokenBundle(
            access_token="access-secret",
            refresh_token="refresh-secret",
        )

        result = SpotifyOAuthSessionResult(
            status=(
                SpotifyOAuthSessionStatus.CONNECTED
            ),
            token=token,
            message="connected",
        )

        rendered = repr(
            result
        )

        self.assertNotIn(
            "access-secret",
            rendered,
        )

        self.assertNotIn(
            "refresh-secret",
            rendered,
        )

    def test_result_invariants_are_enforced(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyOAuthSessionResult(
                status=(
                    SpotifyOAuthSessionStatus.CONNECTED
                ),
            )

        with self.assertRaises(
            ValueError
        ):
            SpotifyOAuthSessionResult(
                status=(
                    SpotifyOAuthSessionStatus.DENIED
                ),
                token=SpotifyTokenBundle(
                    access_token="token"
                ),
            )


class SpotifyOAuthSessionBoundaryTests(
    unittest.TestCase
):
    def test_session_has_no_real_browser_or_persistence_layer(
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
            / "oauth_session.py"
        ).read_text(
            encoding="utf-8"
        )

        forbidden = (
            "webbrowser",
            "QSettings",
            "keyring",
            "win32crypt",
            "Credential Manager",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_session_has_no_client_secret_contract(
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
            / "oauth_session.py"
        ).read_text(
            encoding="utf-8"
        )

        forbidden = (
            "client_"
            + "secret"
        )

        self.assertNotIn(
            forbidden,
            source,
        )


if __name__ == "__main__":
    unittest.main()
