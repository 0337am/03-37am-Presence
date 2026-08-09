from __future__ import annotations

import json
import socket
import unittest
from io import BytesIO
from urllib.error import (
    HTTPError,
)

from src.spotify.constants import (
    SPOTIFY_API_BASE_URL,
)
from src.spotify.web_api import (
    SPOTIFY_API_USER_AGENT,
    SpotifyWebApiClient,
    SpotifyWebApiError,
)


PLAYBACK_URL = (
    f"{SPOTIFY_API_BASE_URL}"
    "/me/player/play"
)

TRACK_URI = (
    "spotify:track:"
    "4iV5W9uYEdYUVa79Axb7Rh"
)


class FakeResponse:
    def __init__(
        self,
        *,
        status: int = 204,
        url: str = PLAYBACK_URL,
        body: bytes = b"",
        headers=None,
    ) -> None:
        self.status = status
        self._url = url
        self._body = body
        self.headers = (
            {}
            if headers is None
            else headers
        )
        self.closed = False

    def __enter__(
        self,
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        self.close()
        return False

    def geturl(
        self,
    ):
        return self._url

    def getcode(
        self,
    ):
        return self.status

    def read(
        self,
        size=-1,
    ):
        if size is None or size < 0:
            return self._body

        return self._body[
            :size
        ]

    def close(
        self,
    ):
        self.closed = True


class RecordingUrlOpen:
    def __init__(
        self,
        outcome,
    ) -> None:
        self.outcome = outcome
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
            self.outcome,
            BaseException,
        ):
            raise self.outcome

        return self.outcome


class SpotifyPlaybackApiTests(
    unittest.TestCase
):
    def test_start_playback_request_contract(
        self,
    ):
        response = FakeResponse()

        transport = RecordingUrlOpen(
            response
        )

        client = SpotifyWebApiClient(
            urlopen=transport,
            timeout_seconds=6.5,
        )

        result = client.start_playback(
            "test-access-token",
            TRACK_URI,
        )

        self.assertIsNone(
            result
        )

        self.assertEqual(
            len(
                transport.requests
            ),
            1,
        )

        request = transport.requests[
            0
        ]

        self.assertEqual(
            request.full_url,
            PLAYBACK_URL,
        )

        self.assertEqual(
            request.get_method(),
            "PUT",
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
                "Content-type"
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
            json.loads(
                request.data.decode(
                    "utf-8"
                )
            ),
            {
                "uris": [
                    TRACK_URI,
                ],
            },
        )

        self.assertEqual(
            transport.timeouts,
            [
                6.5,
            ],
        )

        self.assertTrue(
            response.closed
        )

    def test_empty_204_body_is_success(
        self,
    ):
        client = SpotifyWebApiClient(
            urlopen=RecordingUrlOpen(
                FakeResponse(
                    status=204,
                    body=b"",
                )
            )
        )

        self.assertIsNone(
            client.start_playback(
                "token",
                TRACK_URI,
            )
        )

    def test_local_uri_is_rejected_before_network(
        self,
    ):
        transport = RecordingUrlOpen(
            FakeResponse()
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        with self.assertRaises(
            ValueError
        ):
            client.start_playback(
                "token",
                (
                    "spotify:local:"
                    "Juice+WRLD:"
                    "Studio+Sessions:"
                    "Toxic+Humans:796"
                ),
            )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_malformed_catalogue_uris_are_rejected(
        self,
    ):
        transport = RecordingUrlOpen(
            FakeResponse()
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        invalid_values = (
            "",
            " spotify:track:abc",
            "spotify:track:",
            "spotify:track:abc def",
            "spotify:album:abc",
            "spotify:track:abc/def",
        )

        for value in invalid_values:
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    ValueError
                ):
                    client.start_playback(
                        "token",
                        value,
                    )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_track_uri_type_is_validated(
        self,
    ):
        transport = RecordingUrlOpen(
            FakeResponse()
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        with self.assertRaises(
            TypeError
        ):
            client.start_playback(
                "token",
                None,
            )

        self.assertEqual(
            transport.requests,
            [],
        )

    def test_access_token_is_validated_before_network(
        self,
    ):
        transport = RecordingUrlOpen(
            FakeResponse()
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        with self.assertRaises(
            ValueError
        ):
            client.start_playback(
                "",
                TRACK_URI,
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
            client.start_playback(
                "secret-token",
                TRACK_URI,
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

    def test_403_uses_existing_friendly_error_mapping(
        self,
    ):
        error = HTTPError(
            PLAYBACK_URL,
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
            client.start_playback(
                "token",
                TRACK_URI,
            )

        self.assertEqual(
            caught.exception.error_code,
            "forbidden",
        )

    def test_429_preserves_retry_after(
        self,
    ):
        error = HTTPError(
            PLAYBACK_URL,
            429,
            "Too Many Requests",
            {
                "Retry-After": "9",
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
            client.start_playback(
                "token",
                TRACK_URI,
            )

        self.assertEqual(
            caught.exception.error_code,
            "rate_limited",
        )

        self.assertEqual(
            caught.exception.retry_after_seconds,
            9,
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
            client.start_playback(
                "token",
                TRACK_URI,
            )

        self.assertEqual(
            caught.exception.error_code,
            "timeout",
        )


    def test_playlist_context_playback_contract(
        self,
    ):
        response = FakeResponse(
            url=(
                PLAYBACK_URL
                + "?device_id=desktop-device"
            )
        )

        transport = RecordingUrlOpen(
            response
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        client.start_playlist_playback(
            "token",
            "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
            TRACK_URI,
            device_id="desktop-device",
        )

        request = transport.requests[0]

        self.assertEqual(
            request.get_method(),
            "PUT",
        )

        self.assertEqual(
            request.full_url,
            (
                PLAYBACK_URL
                + "?device_id=desktop-device"
            ),
        )

        self.assertEqual(
            json.loads(
                request.data.decode(
                    "utf-8"
                )
            ),
            {
                "context_uri": (
                    "spotify:playlist:"
                    "37i9dQZF1DXcBWIGoYBM5M"
                ),
                "offset": {
                    "uri": TRACK_URI,
                },
            },
        )

    def test_available_devices_uses_player_devices_endpoint(
        self,
    ):
        url = (
            f"{SPOTIFY_API_BASE_URL}"
            "/me/player/devices"
        )

        transport = RecordingUrlOpen(
            FakeResponse(
                status=200,
                url=url,
                body=b'{"devices":[]}',
            )
        )

        client = SpotifyWebApiClient(
            urlopen=transport
        )

        payload = client.get_available_devices(
            "token"
        )

        self.assertEqual(
            payload,
            {
                "devices": [],
            },
        )

        self.assertEqual(
            transport.requests[0].full_url,
            url,
        )

if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
