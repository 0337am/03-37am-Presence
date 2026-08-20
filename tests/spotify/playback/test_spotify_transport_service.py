from __future__ import annotations

from io import BytesIO
import unittest
from urllib.error import HTTPError

from src.spotify.constants import (
    SPOTIFY_API_BASE_URL,
)
from src.spotify.playback_service import (
    SpotifyPlaybackService,
    SpotifyPlaybackServiceStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiClient,
    SpotifyWebApiError,
)


class FakeResponse:
    def __init__(
        self,
        *,
        url=None,
        status=204,
        body=b"",
        headers=None,
    ):
        self.url = url
        self.status = status
        self.body = body
        self.headers = (
            headers
            if headers is not None
            else {}
        )
        self.closed = False

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status

    def read(self, _limit=-1):
        return self.body

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        del exc_type
        del exc_value
        del traceback
        self.close()


class RecordingUrlOpen:
    def __init__(self, outcome):
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

        if (
            isinstance(
                self.outcome,
                FakeResponse,
            )
            and self.outcome.url is None
        ):
            self.outcome.url = (
                request.full_url
            )

        return self.outcome


class SessionStub:
    def resolve(self):
        raise AssertionError(
            "Unexpected session resolution."
        )


class LegacyApi:
    def start_playback(
        self,
        *args,
        **kwargs,
    ):
        del args
        del kwargs

    def start_playlist_playback(
        self,
        *args,
        **kwargs,
    ):
        del args
        del kwargs

    def start_playlist_position_playback(
        self,
        *args,
        **kwargs,
    ):
        del args
        del kwargs

    def get_available_devices(
        self,
        _access_token,
    ):
        return {
            "devices": [],
        }


class TransportApi(LegacyApi):
    def __init__(self, devices):
        self.devices = devices
        self.calls = []

    def get_available_devices(
        self,
        access_token,
    ):
        self.calls.append(
            (
                "devices",
                access_token,
                None,
            )
        )

        return self.devices

    def resume_playback(
        self,
        access_token,
        *,
        device_id=None,
    ):
        self.calls.append(
            (
                "resume",
                access_token,
                device_id,
            )
        )

    def pause_playback(
        self,
        access_token,
        *,
        device_id=None,
    ):
        self.calls.append(
            (
                "pause",
                access_token,
                device_id,
            )
        )

    def skip_next(
        self,
        access_token,
        *,
        device_id=None,
    ):
        self.calls.append(
            (
                "next",
                access_token,
                device_id,
            )
        )

    def skip_previous(
        self,
        access_token,
        *,
        device_id=None,
    ):
        self.calls.append(
            (
                "previous",
                access_token,
                device_id,
            )
        )


def make_service(api):
    service = SpotifyPlaybackService(
        SessionStub(),
        api_client=api,
    )

    service._resolve_session = (
        lambda: (
            "access-token",
            False,
            None,
        )
    )

    return service


class SpotifyTransportServiceTests(
    unittest.TestCase
):
    def assert_web_request(
        self,
        method_name,
        expected_method,
        expected_path,
    ):
        response = FakeResponse()

        transport = RecordingUrlOpen(
            response
        )

        client = SpotifyWebApiClient(
            urlopen=transport,
            timeout_seconds=6.5,
        )

        getattr(
            client,
            method_name,
        )(
            "test-access-token",
            device_id="desktop123",
        )

        self.assertEqual(
            len(transport.requests),
            1,
        )

        request = transport.requests[0]

        self.assertEqual(
            request.get_method(),
            expected_method,
        )

        self.assertEqual(
            request.full_url,
            (
                SPOTIFY_API_BASE_URL
                + expected_path
                + "?device_id=desktop123"
            ),
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

        self.assertIsNone(
            request.get_header(
                "Content-type"
            )
        )

        self.assertIsNone(
            request.data
        )

        self.assertEqual(
            transport.timeouts,
            [6.5],
        )

        self.assertTrue(
            response.closed
        )

    def test_web_resume_uses_put_play(
        self,
    ):
        self.assert_web_request(
            "resume_playback",
            "PUT",
            "/me/player/play",
        )

    def test_web_pause_uses_put_pause(
        self,
    ):
        self.assert_web_request(
            "pause_playback",
            "PUT",
            "/me/player/pause",
        )

    def test_web_next_uses_post_next(
        self,
    ):
        self.assert_web_request(
            "skip_next",
            "POST",
            "/me/player/next",
        )

    def test_web_previous_uses_post_previous(
        self,
    ):
        self.assert_web_request(
            "skip_previous",
            "POST",
            "/me/player/previous",
        )

    def test_web_transport_preserves_rate_limit_metadata(
        self,
    ):
        url = (
            SPOTIFY_API_BASE_URL
            + "/me/player/next"
        )

        error = HTTPError(
            url,
            429,
            "Too Many Requests",
            {
                "Retry-After": "7",
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
            client.skip_next(
                "token"
            )

        self.assertEqual(
            caught.exception.error_code,
            "rate_limited",
        )

        self.assertEqual(
            caught.exception.retry_after_seconds,
            7,
        )

    def test_service_resume_prefers_active_device(
        self,
    ):
        api = TransportApi(
            {
                "devices": [
                    {
                        "id": "desktop123",
                        "type": "Computer",
                        "is_active": False,
                        "is_restricted": False,
                    },
                    {
                        "id": "phone123",
                        "type": "Smartphone",
                        "is_active": True,
                        "is_restricted": False,
                    },
                ],
            }
        )

        result = (
            make_service(
                api
            ).resume_playback()
        )

        self.assertIs(
            result.status,
            SpotifyPlaybackServiceStatus.READY,
        )

        self.assertIn(
            (
                "resume",
                "access-token",
                "phone123",
            ),
            api.calls,
        )

    def test_service_pause_prefers_computer_when_none_active(
        self,
    ):
        api = TransportApi(
            {
                "devices": [
                    {
                        "id": "phone123",
                        "type": "Smartphone",
                        "is_active": False,
                        "is_restricted": False,
                    },
                    {
                        "id": "desktop123",
                        "type": "Computer",
                        "is_active": False,
                        "is_restricted": False,
                    },
                ],
            }
        )

        result = (
            make_service(
                api
            ).pause_playback()
        )

        self.assertIs(
            result.status,
            SpotifyPlaybackServiceStatus.READY,
        )

        self.assertIn(
            (
                "pause",
                "access-token",
                "desktop123",
            ),
            api.calls,
        )

    def test_service_next_without_devices_uses_active_fallback(
        self,
    ):
        api = TransportApi(
            {
                "devices": [],
            }
        )

        result = (
            make_service(
                api
            ).skip_next()
        )

        self.assertIs(
            result.status,
            SpotifyPlaybackServiceStatus.READY,
        )

        self.assertIn(
            (
                "next",
                "access-token",
                None,
            ),
            api.calls,
        )

    def test_service_previous_returns_ready(
        self,
    ):
        api = TransportApi(
            {
                "devices": [],
            }
        )

        result = (
            make_service(
                api
            ).skip_previous()
        )

        self.assertIs(
            result.status,
            SpotifyPlaybackServiceStatus.READY,
        )

        self.assertIn(
            (
                "previous",
                "access-token",
                None,
            ),
            api.calls,
        )

    def test_legacy_api_constructor_remains_compatible(
        self,
    ):
        service = SpotifyPlaybackService(
            SessionStub(),
            api_client=LegacyApi(),
        )

        result = (
            service.resume_playback()
        )

        self.assertIs(
            result.status,
            SpotifyPlaybackServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_playback_api",
        )


if __name__ == "__main__":
    unittest.main()
