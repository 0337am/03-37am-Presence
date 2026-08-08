from __future__ import annotations

from io import BytesIO
import json
import socket
import unittest
from urllib.error import HTTPError
from urllib.error import URLError

from src.spotify.models import (
    SpotifyAccount,
)
from src.spotify.web_api import (
    CURRENT_USER_PROFILE_URL,
    MAX_SPOTIFY_API_RESPONSE_BYTES,
    SPOTIFY_API_USER_AGENT,
    SpotifyWebApiClient,
    SpotifyWebApiError,
    spotify_account_from_payload,
)


class FakeResponse:
    def __init__(
        self,
        payload,
        *,
        status=200,
        url=CURRENT_USER_PROFILE_URL,
        headers=None,
        raw_body=None,
    ):
        self.status = status
        self._url = url
        self.headers = dict(
            headers or {}
        )

        if raw_body is None:
            raw_body = json.dumps(
                payload
            ).encode(
                "utf-8"
            )

        self._stream = BytesIO(
            raw_body
        )

        self.closed = False

    def read(
        self,
        size=-1,
    ):
        return self._stream.read(
            size
        )

    def geturl(
        self,
    ):
        return self._url

    def getcode(
        self,
    ):
        return self.status

    def __enter__(
        self,
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        self.closed = True
        self._stream.close()
        return False


class RecordingUrlOpen:
    def __init__(
        self,
        response,
    ):
        self.response = response
        self.requests = []
        self.timeouts = []

    def __call__(
        self,
        request,
        *,
        timeout,
    ):
        self.requests.append(
            request
        )

        self.timeouts.append(
            timeout
        )

        if isinstance(
            self.response,
            BaseException,
        ):
            raise self.response

        return self.response


def profile_payload():
    return {
        "account_id": "stable-account-id",
        "display_name": "03:37am",
        "id": "legacy-user-id",
        "uri": "spotify:user:legacy-user-id",
        "external_urls": {
            "spotify": (
                "https://open.spotify.com/user/"
                "legacy-user-id"
            ),
        },
        "images": [
            {
                "url": (
                    "https://i.scdn.co/image/"
                    "profile-image"
                ),
                "height": 300,
                "width": 300,
            },
        ],
        "type": "user",
    }


class SpotifyProfileParserTests(
    unittest.TestCase
):
    def test_profile_maps_to_existing_account_model(
        self,
    ):
        account = spotify_account_from_payload(
            profile_payload()
        )

        self.assertIsInstance(
            account,
            SpotifyAccount,
        )

        self.assertEqual(
            account.account_id,
            "stable-account-id",
        )

        self.assertEqual(
            account.display_name,
            "03:37am",
        )

        self.assertEqual(
            account.user_id,
            "legacy-user-id",
        )

        self.assertEqual(
            account.uri,
            "spotify:user:legacy-user-id",
        )

        self.assertEqual(
            account.profile_url,
            (
                "https://open.spotify.com/user/"
                "legacy-user-id"
            ),
        )

        self.assertEqual(
            account.image_url,
            (
                "https://i.scdn.co/image/"
                "profile-image"
            ),
        )

    def test_account_id_is_required(
        self,
    ):
        payload = profile_payload()
        payload.pop(
            "account_id"
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            spotify_account_from_payload(
                payload
            )

        self.assertEqual(
            caught.exception.error_code,
            "invalid_response",
        )

    def test_account_id_cannot_be_empty(
        self,
    ):
        payload = profile_payload()
        payload[
            "account_id"
        ] = "   "

        with self.assertRaises(
            SpotifyWebApiError
        ):
            spotify_account_from_payload(
                payload
            )

    def test_display_name_may_be_null(
        self,
    ):
        payload = profile_payload()
        payload[
            "display_name"
        ] = None

        account = spotify_account_from_payload(
            payload
        )

        self.assertEqual(
            account.display_name,
            "",
        )

    def test_optional_profile_fields_may_be_absent(
        self,
    ):
        payload = {
            "account_id": "stable-account-id",
        }

        account = spotify_account_from_payload(
            payload
        )

        self.assertEqual(
            account.display_name,
            "",
        )

        self.assertEqual(
            account.user_id,
            "",
        )

        self.assertEqual(
            account.uri,
            "",
        )

        self.assertEqual(
            account.profile_url,
            "",
        )

        self.assertEqual(
            account.image_url,
            "",
        )

    def test_invalid_external_urls_are_rejected(
        self,
    ):
        payload = profile_payload()
        payload[
            "external_urls"
        ] = []

        with self.assertRaises(
            SpotifyWebApiError
        ):
            spotify_account_from_payload(
                payload
            )

    def test_invalid_images_are_rejected(
        self,
    ):
        payload = profile_payload()
        payload[
            "images"
        ] = {}

        with self.assertRaises(
            SpotifyWebApiError
        ):
            spotify_account_from_payload(
                payload
            )

    def test_empty_images_are_supported(
        self,
    ):
        payload = profile_payload()
        payload[
            "images"
        ] = []

        account = spotify_account_from_payload(
            payload
        )

        self.assertEqual(
            account.image_url,
            "",
        )

    def test_non_mapping_payload_is_rejected(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            spotify_account_from_payload(
                []
            )


class SpotifyWebApiClientTests(
    unittest.TestCase
):
    def test_constructor_validates_dependencies(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyWebApiClient(
                urlopen=42
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyWebApiClient(
                timeout_seconds=True
            )

        with self.assertRaises(
            ValueError
        ):
            SpotifyWebApiClient(
                timeout_seconds=0
            )

    def test_current_profile_request_contract(
        self,
    ):
        response = FakeResponse(
            profile_payload()
        )

        transport = RecordingUrlOpen(
            response
        )

        client = SpotifyWebApiClient(
            urlopen=transport,
            timeout_seconds=7.5,
        )

        account = (
            client.get_current_user_profile(
                "test-access-token"
            )
        )

        self.assertEqual(
            account.account_id,
            "stable-account-id",
        )

        self.assertEqual(
            len(
                transport.requests
            ),
            1,
        )

        request = transport.requests[0]

        self.assertEqual(
            request.full_url,
            CURRENT_USER_PROFILE_URL,
        )

        self.assertEqual(
            request.get_method(),
            "GET",
        )

        self.assertEqual(
            request.get_header(
                "Authorization"
            ),
            "Bearer test-access-token",
        )

        self.assertEqual(
            request.get_header(
                "Accept"
            ),
            "application/json",
        )

        self.assertEqual(
            request.get_header(
                "User-agent"
            ),
            SPOTIFY_API_USER_AGENT,
        )

        self.assertEqual(
            transport.timeouts,
            [
                7.5,
            ],
        )

        self.assertTrue(
            response.closed
        )

    def test_access_token_is_validated_before_network(
        self,
    ):
        transport = RecordingUrlOpen(
            FakeResponse(
                profile_payload()
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        for token in (
            "",
            "   ",
            "token with spaces",
        ):
            with self.subTest(
                token=token
            ):
                with self.assertRaises(
                    ValueError
                ):
                    client.get_current_user_profile(
                        token
                    )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_access_token_type_is_validated(
        self,
    ):
        transport = RecordingUrlOpen(
            FakeResponse(
                profile_payload()
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        with self.assertRaises(
            TypeError
        ):
            client.get_current_user_profile(
                None
            )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_untrusted_final_response_url_is_rejected(
        self,
    ):
        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                FakeResponse(
                    profile_payload(),
                    url=(
                        "https://example.com/"
                        "stolen"
                    ),
                )
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "untrusted_response",
        )

        self.assertNotIn(
            "secret-token",
            str(
                caught.exception
            ),
        )

    def test_invalid_json_is_rejected(
        self,
    ):
        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                FakeResponse(
                    {},
                    raw_body=b"{bad json",
                )
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "invalid_response",
        )

    def test_json_array_is_rejected(
        self,
    ):
        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                FakeResponse(
                    [],
                )
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "invalid_response",
        )

    def test_content_length_limit_is_enforced(
        self,
    ):
        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                FakeResponse(
                    profile_payload(),
                    headers={
                        "Content-Length": str(
                            MAX_SPOTIFY_API_RESPONSE_BYTES
                            + 1
                        ),
                    },
                )
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "response_too_large",
        )

    def test_body_limit_is_enforced_without_header(
        self,
    ):
        body = (
            b"x"
            * (
                MAX_SPOTIFY_API_RESPONSE_BYTES
                + 1
            )
        )

        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                FakeResponse(
                    {},
                    raw_body=body,
                )
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "response_too_large",
        )

    def test_401_requires_reauthorization(
        self,
    ):
        error = HTTPError(
            CURRENT_USER_PROFILE_URL,
            401,
            "Unauthorized",
            {},
            BytesIO(
                b'{"error":{"status":401}}'
            ),
        )

        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                error
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "reauthorization_required",
        )

        self.assertNotIn(
            "secret-token",
            str(
                caught.exception
            ),
        )

    def test_403_is_friendly(
        self,
    ):
        error = HTTPError(
            CURRENT_USER_PROFILE_URL,
            403,
            "Forbidden",
            {},
            BytesIO(
                b'{"error":{"status":403}}'
            ),
        )

        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                error
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "forbidden",
        )

    def test_429_uses_retry_after(
        self,
    ):
        error = HTTPError(
            CURRENT_USER_PROFILE_URL,
            429,
            "Too Many Requests",
            {
                "Retry-After": "12",
            },
            BytesIO(
                b'{"error":{"status":429}}'
            ),
        )

        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                error
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "rate_limited",
        )

        self.assertEqual(
            caught.exception.retry_after_seconds,
            12,
        )

    def test_429_quota_exceeded_is_distinguished(
        self,
    ):
        error = HTTPError(
            CURRENT_USER_PROFILE_URL,
            429,
            "Too Many Requests",
            {
                "Retry-After": "30",
            },
            BytesIO(
                b'{"reason":"QUOTA_EXCEEDED"}'
            ),
        )

        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                error
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "quota_exceeded",
        )

        self.assertEqual(
            caught.exception.retry_after_seconds,
            30,
        )

    def test_503_is_friendly(
        self,
    ):
        error = HTTPError(
            CURRENT_USER_PROFILE_URL,
            503,
            "Unavailable",
            {},
            BytesIO(
                b""
            ),
        )

        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                error
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "spotify_unavailable",
        )

    def test_timeout_is_friendly(
        self,
    ):
        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                socket.timeout()
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "timeout",
        )

    def test_urlerror_timeout_is_friendly(
        self,
    ):
        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                URLError(
                    socket.timeout()
                )
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "timeout",
        )

    def test_offline_error_is_friendly(
        self,
    ):
        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                URLError(
                    "offline"
                )
            )
        )

        with self.assertRaises(
            SpotifyWebApiError
        ) as caught:
            client.get_current_user_profile(
                "secret-token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "network_error",
        )

    def test_error_repr_does_not_include_credentials(
        self,
    ):
        error = SpotifyWebApiError(
            "test",
            "safe message",
        )

        rendered = repr(
            error
        )

        self.assertNotIn(
            "access_token",
            rendered
        )

        self.assertNotIn(
            "refresh_token",
            rendered
        )


class SpotifyWebApiBoundaryTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        from pathlib import Path

        cls.source = (
            Path(
                __file__
            )
            .resolve()
            .parents[1]
            / "src"
            / "spotify"
            / "web_api.py"
        ).read_text(
            encoding="utf-8"
        )

    def test_transport_does_not_own_oauth_or_persistence(
        self,
    ):
        forbidden = (
            "SpotifySessionManager",
            "SpotifyCredentialStore",
            "windows_dpapi",
            "QSettings",
            "PyQt6",
            "client_secret",
            "refresh_token",
            "spotify_auth.dat",
            "oauth_callback",
            "OAuthSession",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    self.source,
                )

    def test_transport_uses_spotify_api_base_and_existing_model(
        self,
    ):
        self.assertIn(
            "SPOTIFY_API_BASE_URL",
            self.source,
        )

        self.assertIn(
            "SpotifyAccount",
            self.source,
        )

        self.assertIn(
            'f"{SPOTIFY_API_BASE_URL}/me"',
            self.source,
        )

    def test_default_transport_blocks_redirects(
        self,
    ):
        self.assertIn(
            "_NoSpotifyRedirectHandler",
            self.source,
        )

        self.assertIn(
            "return None",
            self.source,
        )

    def test_bearer_header_is_request_only(
        self,
    ):
        self.assertIn(
            '"Authorization"',
            self.source,
        )

        self.assertIn(
            'f"Bearer {token}"',
            self.source,
        )

        self.assertNotIn(
            "print(",
            self.source,
        )

        self.assertNotIn(
            "logging.",
            self.source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
