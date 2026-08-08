from __future__ import annotations

import io
import json
from pathlib import Path
import socket
from threading import Thread
import time
import unittest
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import parse_qs
from urllib.request import urlopen

from src.spotify.constants import (
    SPOTIFY_CONNECT_SCOPES,
)
from src.spotify.constants import (
    SPOTIFY_TOKEN_URL,
)
from src.spotify.models import SpotifyTokenBundle
from src.spotify.oauth_callback import (
    LoopbackCallbackError,
)
from src.spotify.oauth_callback import (
    LoopbackCallbackTimeout,
)
from src.spotify.oauth_callback import (
    SpotifyLoopbackCallbackServer,
)
from src.spotify.token_client import (
    MAX_TOKEN_RESPONSE_BYTES,
)
from src.spotify.token_client import (
    SpotifyTokenClient,
)
from src.spotify.token_client import (
    SpotifyTokenError,
)


TEST_CLIENT_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)

TEST_VERIFIER = (
    "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_"
    "wW1gFWFOEjXk"
)

TEST_STATE = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopq"
)


class FakeResponse:
    def __init__(
        self,
        payload,
        *,
        status=200,
        response_url=SPOTIFY_TOKEN_URL,
        raw_body=None,
        headers=None,
    ):
        if raw_body is None:
            raw_body = json.dumps(
                payload
            ).encode(
                "utf-8"
            )

        self._body = raw_body
        self.status = status
        self._response_url = response_url

        if headers is None:
            headers = {
                "Content-Length": str(
                    len(
                        self._body
                    )
                ),
            }

        self.headers = headers

    def read(
        self,
        amount=-1,
    ):
        if amount is None or amount < 0:
            return self._body

        return self._body[:amount]

    def geturl(
        self,
    ):
        return self._response_url

    def __enter__(
        self,
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False


class RecordingUrlopen:
    def __init__(
        self,
        response=None,
        *,
        error=None,
    ):
        self.response = response
        self.error = error
        self.calls = []

    def __call__(
        self,
        request,
        *,
        timeout,
    ):
        self.calls.append(
            (
                request,
                timeout,
            )
        )

        if self.error is not None:
            raise self.error

        return self.response


def token_payload(
    *,
    access_token="access-secret",
    refresh_token="refresh-secret",
    scope="user-read-private",
    expires_in=3600,
):
    result = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": scope,
    }

    if refresh_token is not None:
        result[
            "refresh_token"
        ] = refresh_token

    return result


class SpotifyLoopbackCallbackTests(
    unittest.TestCase
):
    def test_server_binds_only_to_loopback_with_dynamic_port(
        self,
    ):
        with SpotifyLoopbackCallbackServer() as server:
            self.assertEqual(
                server.host,
                "127.0.0.1",
            )

            self.assertGreater(
                server.port,
                0,
            )

            self.assertLessEqual(
                server.port,
                65535,
            )

            self.assertEqual(
                server.redirect_uri,
                (
                    "http://127.0.0.1:"
                    f"{server.port}/callback"
                ),
            )

    def test_non_loopback_bind_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyLoopbackCallbackServer(
                host="0.0.0.0"
            )

    def test_successful_callback_is_captured_without_logging_secrets(
        self,
    ):
        server = SpotifyLoopbackCallbackServer()

        result_holder = {}
        error_holder = {}

        def waiter():
            try:
                result_holder[
                    "result"
                ] = server.wait_for_callback(
                    timeout_seconds=2.0
                )
            except Exception as error:
                error_holder[
                    "error"
                ] = error

        thread = Thread(
            target=waiter,
            daemon=True,
        )

        thread.start()

        callback_url = (
            f"{server.redirect_uri}"
            "?code=authorization-code"
            f"&state={TEST_STATE}"
        )

        with urlopen(
            callback_url,
            timeout=2.0,
        ) as response:
            body = response.read()

            self.assertEqual(
                response.status,
                200,
            )

            self.assertIn(
                b"return to 03:37am Presence",
                body,
            )

            self.assertEqual(
                response.headers.get(
                    "Cache-Control"
                ),
                "no-store",
            )

        thread.join(
            timeout=2.0
        )

        self.assertFalse(
            thread.is_alive()
        )

        self.assertNotIn(
            "error",
            error_holder,
        )

        result = result_holder[
            "result"
        ]

        self.assertEqual(
            result.callback_url,
            callback_url,
        )

        rendered = repr(
            result
        )

        self.assertNotIn(
            "authorization-code",
            rendered,
        )

        self.assertNotIn(
            TEST_STATE,
            rendered,
        )

        self.assertTrue(
            server.closed
        )

    def test_wrong_path_does_not_consume_callback(
        self,
    ):
        server = SpotifyLoopbackCallbackServer()

        result_holder = {}

        def waiter():
            result_holder[
                "result"
            ] = server.wait_for_callback(
                timeout_seconds=2.0
            )

        thread = Thread(
            target=waiter,
            daemon=True,
        )

        thread.start()

        wrong_url = (
            f"http://127.0.0.1:"
            f"{server.port}/wrong"
        )

        with self.assertRaises(
            HTTPError
        ) as context:
            urlopen(
                wrong_url,
                timeout=2.0,
            )

        self.assertEqual(
            context.exception.code,
            404,
        )

        context.exception.close()

        callback_url = (
            f"{server.redirect_uri}"
            "?code=authorization-code"
            f"&state={TEST_STATE}"
        )

        with urlopen(
            callback_url,
            timeout=2.0,
        ) as response:
            response.read()

            self.assertEqual(
                response.status,
                200,
            )

        thread.join(
            timeout=2.0
        )

        self.assertFalse(
            thread.is_alive()
        )

        self.assertEqual(
            result_holder[
                "result"
            ].callback_url,
            callback_url,
        )

    def test_timeout_is_friendly_and_closes_server(
        self,
    ):
        server = SpotifyLoopbackCallbackServer()

        with self.assertRaises(
            LoopbackCallbackTimeout
        ):
            server.wait_for_callback(
                timeout_seconds=0.05
            )

        self.assertTrue(
            server.closed
        )

    def test_closed_server_cannot_wait_again(
        self,
    ):
        server = SpotifyLoopbackCallbackServer()
        server.close()

        with self.assertRaises(
            LoopbackCallbackError
        ):
            server.wait_for_callback(
                timeout_seconds=1.0
            )


class SpotifyTokenClientTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        with SpotifyLoopbackCallbackServer() as server:
            self.redirect_uri = (
                server.redirect_uri
            )

    def test_authorization_code_exchange_contract(
        self,
    ):
        transport = RecordingUrlopen(
            FakeResponse(
                token_payload()
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
            timeout_seconds=7.5,
            clock=lambda: 1234.0,
        )

        token = client.exchange_authorization_code(
            "authorization-code",
            self.redirect_uri,
            TEST_VERIFIER,
            requested_scopes=SPOTIFY_CONNECT_SCOPES,
        )

        self.assertEqual(
            len(
                transport.calls
            ),
            1,
        )

        request, timeout = (
            transport.calls[0]
        )

        self.assertEqual(
            request.full_url,
            SPOTIFY_TOKEN_URL,
        )

        self.assertEqual(
            request.get_method(),
            "POST",
        )

        self.assertEqual(
            timeout,
            7.5,
        )

        headers = {
            key.casefold(): value
            for key, value
            in request.header_items()
        }

        self.assertEqual(
            headers[
                "content-type"
            ],
            (
                "application/"
                "x-www-form-urlencoded"
            ),
        )

        self.assertEqual(
            headers[
                "accept"
            ],
            "application/json",
        )

        self.assertNotIn(
            "authorization",
            headers,
        )

        body = parse_qs(
            request.data.decode(
                "utf-8"
            )
        )

        self.assertEqual(
            body[
                "client_id"
            ],
            [
                TEST_CLIENT_ID,
            ],
        )

        self.assertEqual(
            body[
                "grant_type"
            ],
            [
                "authorization_code",
            ],
        )

        self.assertEqual(
            body[
                "code"
            ],
            [
                "authorization-code",
            ],
        )

        self.assertEqual(
            body[
                "redirect_uri"
            ],
            [
                self.redirect_uri,
            ],
        )

        self.assertEqual(
            body[
                "code_verifier"
            ],
            [
                TEST_VERIFIER,
            ],
        )

        forbidden_field = (
            "client_"
            + "secret"
        )

        self.assertNotIn(
            forbidden_field,
            body,
        )

        self.assertEqual(
            token.access_token,
            "access-secret",
        )

        self.assertEqual(
            token.refresh_token,
            "refresh-secret",
        )

        self.assertEqual(
            token.granted_scopes,
            (
                "user-read-private",
            ),
        )

        self.assertEqual(
            token.obtained_at,
            1234.0,
        )

        self.assertEqual(
            token.authorized_at,
            1234.0,
        )

    def test_exchange_falls_back_to_requested_scopes_when_omitted(
        self,
    ):
        payload = token_payload()
        payload.pop(
            "scope"
        )

        transport = RecordingUrlopen(
            FakeResponse(
                payload
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
            clock=lambda: 50.0,
        )

        token = client.exchange_authorization_code(
            "authorization-code",
            self.redirect_uri,
            TEST_VERIFIER,
        )

        self.assertEqual(
            token.granted_scopes,
            SPOTIFY_CONNECT_SCOPES,
        )

    def test_initial_exchange_requires_refresh_token(
        self,
    ):
        transport = RecordingUrlopen(
            FakeResponse(
                token_payload(
                    refresh_token=None
                )
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
        )

        with self.assertRaises(
            SpotifyTokenError
        ) as context:
            client.exchange_authorization_code(
                "authorization-code",
                self.redirect_uri,
                TEST_VERIFIER,
            )

        self.assertEqual(
            context.exception.error_code,
            "invalid_response",
        )

    def test_refresh_preserves_original_refresh_token_and_authorization_time(
        self,
    ):
        response = token_payload(
            access_token="new-access",
            refresh_token=None,
            scope="",
        )

        transport = RecordingUrlopen(
            FakeResponse(
                response
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
            clock=lambda: 900.0,
        )

        current = SpotifyTokenBundle(
            access_token="old-access",
            refresh_token="original-refresh",
            granted_scopes=(
                "user-read-private",
            ),
            obtained_at=100.0,
            authorized_at=50.0,
        )

        refreshed = client.refresh_access_token(
            current
        )

        self.assertEqual(
            refreshed.access_token,
            "new-access",
        )

        self.assertEqual(
            refreshed.refresh_token,
            "original-refresh",
        )

        self.assertEqual(
            refreshed.granted_scopes,
            current.granted_scopes,
        )

        self.assertEqual(
            refreshed.obtained_at,
            900.0,
        )

        self.assertEqual(
            refreshed.authorized_at,
            50.0,
        )

        request, _ = (
            transport.calls[0]
        )

        body = parse_qs(
            request.data.decode(
                "utf-8"
            )
        )

        self.assertEqual(
            body[
                "grant_type"
            ],
            [
                "refresh_token",
            ],
        )

        self.assertEqual(
            body[
                "refresh_token"
            ],
            [
                "original-refresh",
            ],
        )

        self.assertEqual(
            body[
                "client_id"
            ],
            [
                TEST_CLIENT_ID,
            ],
        )

    def test_refresh_accepts_rotated_refresh_token(
        self,
    ):
        transport = RecordingUrlopen(
            FakeResponse(
                token_payload(
                    access_token="new-access",
                    refresh_token="rotated-refresh",
                )
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
            clock=lambda: 500.0,
        )

        current = SpotifyTokenBundle(
            access_token="old-access",
            refresh_token="original-refresh",
            granted_scopes=(
                "user-read-private",
            ),
            obtained_at=100.0,
            authorized_at=25.0,
        )

        refreshed = client.refresh_access_token(
            current
        )

        self.assertEqual(
            refreshed.refresh_token,
            "rotated-refresh",
        )

        self.assertEqual(
            refreshed.authorized_at,
            25.0,
        )

    def test_refresh_without_refresh_token_requires_reauthorization(
        self,
    ):
        transport = RecordingUrlopen(
            FakeResponse(
                token_payload()
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
        )

        current = SpotifyTokenBundle(
            access_token="access",
            refresh_token="",
        )

        with self.assertRaises(
            SpotifyTokenError
        ) as context:
            client.refresh_access_token(
                current
            )

        self.assertEqual(
            context.exception.error_code,
            "reauthorization_required",
        )

        self.assertEqual(
            len(
                transport.calls
            ),
            0,
        )

    def test_invalid_grant_is_friendly_and_does_not_echo_server_description(
        self,
    ):
        body = json.dumps(
            {
                "error": "invalid_grant",
                "error_description": (
                    "server included sensitive detail"
                ),
            }
        ).encode(
            "utf-8"
        )

        error = HTTPError(
            SPOTIFY_TOKEN_URL,
            400,
            "Bad Request",
            {},
            io.BytesIO(
                body
            ),
        )

        transport = RecordingUrlopen(
            error=error
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
        )

        with self.assertRaises(
            SpotifyTokenError
        ) as context:
            client.exchange_authorization_code(
                "authorization-code",
                self.redirect_uri,
                TEST_VERIFIER,
            )

        failure = context.exception

        self.assertTrue(
            error.fp is None
            or error.fp.closed
        )

        self.assertEqual(
            failure.error_code,
            "reauthorization_required",
        )

        self.assertEqual(
            failure.spotify_error,
            "invalid_grant",
        )

        self.assertNotIn(
            "sensitive detail",
            str(
                failure
            ),
        )

    def test_offline_error_is_friendly(
        self,
    ):
        transport = RecordingUrlopen(
            error=URLError(
                "offline"
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
        )

        with self.assertRaises(
            SpotifyTokenError
        ) as context:
            client.exchange_authorization_code(
                "authorization-code",
                self.redirect_uri,
                TEST_VERIFIER,
            )

        self.assertEqual(
            context.exception.error_code,
            "network_error",
        )

    def test_timeout_is_friendly(
        self,
    ):
        transport = RecordingUrlopen(
            error=socket.timeout()
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
        )

        with self.assertRaises(
            SpotifyTokenError
        ) as context:
            client.exchange_authorization_code(
                "authorization-code",
                self.redirect_uri,
                TEST_VERIFIER,
            )

        self.assertEqual(
            context.exception.error_code,
            "timeout",
        )

    def test_malformed_json_is_rejected(
        self,
    ):
        transport = RecordingUrlopen(
            FakeResponse(
                {},
                raw_body=b"{invalid-json",
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
        )

        with self.assertRaises(
            SpotifyTokenError
        ) as context:
            client.exchange_authorization_code(
                "authorization-code",
                self.redirect_uri,
                TEST_VERIFIER,
            )

        self.assertEqual(
            context.exception.error_code,
            "invalid_response",
        )

    def test_oversized_response_is_rejected_before_body_use(
        self,
    ):
        transport = RecordingUrlopen(
            FakeResponse(
                {},
                raw_body=b"{}",
                headers={
                    "Content-Length": str(
                        MAX_TOKEN_RESPONSE_BYTES
                        + 1
                    ),
                },
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
        )

        with self.assertRaises(
            SpotifyTokenError
        ) as context:
            client.exchange_authorization_code(
                "authorization-code",
                self.redirect_uri,
                TEST_VERIFIER,
            )

        self.assertEqual(
            context.exception.error_code,
            "response_too_large",
        )

    def test_untrusted_final_response_url_is_rejected(
        self,
    ):
        transport = RecordingUrlopen(
            FakeResponse(
                token_payload(),
                response_url=(
                    "https://example.com/token"
                ),
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
        )

        with self.assertRaises(
            SpotifyTokenError
        ) as context:
            client.exchange_authorization_code(
                "authorization-code",
                self.redirect_uri,
                TEST_VERIFIER,
            )

        self.assertEqual(
            context.exception.error_code,
            "untrusted_response",
        )

    def test_invalid_inputs_do_not_touch_network(
        self,
    ):
        transport = RecordingUrlopen(
            FakeResponse(
                token_payload()
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
        )

        with self.assertRaises(
            ValueError
        ):
            client.exchange_authorization_code(
                "",
                self.redirect_uri,
                TEST_VERIFIER,
            )

        with self.assertRaises(
            ValueError
        ):
            client.exchange_authorization_code(
                "code",
                self.redirect_uri,
                "short",
            )

        self.assertEqual(
            len(
                transport.calls
            ),
            0,
        )

    def test_token_model_repr_still_hides_transport_credentials(
        self,
    ):
        transport = RecordingUrlopen(
            FakeResponse(
                token_payload()
            )
        )

        client = SpotifyTokenClient(
            TEST_CLIENT_ID,
            urlopen=transport,
            clock=lambda: 100.0,
        )

        token = client.exchange_authorization_code(
            "authorization-code",
            self.redirect_uri,
            TEST_VERIFIER,
        )

        rendered = repr(
            token
        )

        self.assertNotIn(
            "access-secret",
            rendered,
        )

        self.assertNotIn(
            "refresh-secret",
            rendered,
        )


class SpotifyOAuthTransportBoundaryTests(
    unittest.TestCase
):
    def test_transport_has_no_browser_or_persistence_layer(
        self,
    ):
        root = (
            Path(
                __file__
            )
            .resolve()
            .parents[1]
        )

        production_files = (
            "src/spotify/oauth_callback.py",
            "src/spotify/token_client.py",
        )

        combined = "\n".join(
            (
                root
                / relative
            ).read_text(
                encoding="utf-8"
            )
            for relative in production_files
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
                    combined,
                )

    def test_token_transport_has_no_client_secret_contract(
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
            / "token_client.py"
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
