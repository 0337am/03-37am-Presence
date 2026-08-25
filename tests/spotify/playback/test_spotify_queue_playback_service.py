from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.spotify.playback_service import (
    SpotifyPlaybackService,
    SpotifyPlaybackServiceStatus,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiError,
)


def session(
    status=SpotifySessionStatus.READY,
):
    return SimpleNamespace(
        status=status,
        token=SimpleNamespace(
            access_token="access-token"
        ),
    )


class SessionStub:

    def __init__(
        self,
        status=SpotifySessionStatus.READY,
    ):
        self.status = status

    def resolve(
        self,
    ):
        return session(
            self.status
        )


class LegacyApi:

    def __init__(
        self,
    ):
        self.calls = []

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
        access_token,
    ):
        self.calls.append(
            (
                "devices",
                access_token,
            )
        )

        return {
            "devices": [],
        }


class QueueApi(
    LegacyApi
):

    def __init__(
        self,
        *,
        devices=None,
        error=None,
        invalid=False,
    ):
        super().__init__()

        self.devices = (
            {
                "devices": [],
            }
            if devices is None
            else {
                "devices": devices,
            }
        )

        self.error = error
        self.invalid = invalid

    def get_available_devices(
        self,
        access_token,
    ):
        self.calls.append(
            (
                "devices",
                access_token,
            )
        )

        return self.devices

    def add_to_queue(
        self,
        access_token,
        spotify_uri,
        *,
        device_id=None,
    ):
        self.calls.append(
            (
                "queue",
                access_token,
                spotify_uri,
                device_id,
            )
        )

        if self.invalid:
            raise ValueError(
                "invalid queue URI"
            )

        if self.error is not None:
            raise self.error


class SpotifyQueuePlaybackServiceTests(
    unittest.TestCase
):

    def test_add_to_queue_uses_active_device(
        self,
    ):
        api = QueueApi(
            devices=[
                {
                    "id": "inactive",
                    "is_active": False,
                    "is_restricted": False,
                    "type": "Computer",
                },
                {
                    "id": "active",
                    "is_active": True,
                    "is_restricted": False,
                    "type": "Computer",
                },
            ]
        )

        result = (
            SpotifyPlaybackService(
                SessionStub(),
                api_client=api,
            )
            .add_to_queue(
                "spotify:track:track123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyPlaybackServiceStatus.READY,
        )

        self.assertIn(
            (
                "queue",
                "access-token",
                "spotify:track:track123",
                "active",
            ),
            api.calls,
        )

    def test_add_to_queue_without_devices_uses_none(
        self,
    ):
        api = QueueApi()

        result = (
            SpotifyPlaybackService(
                SessionStub(),
                api_client=api,
            )
            .add_to_queue(
                "spotify:episode:episode456"
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertIn(
            (
                "queue",
                "access-token",
                "spotify:episode:episode456",
                None,
            ),
            api.calls,
        )

    def test_add_to_queue_invalid_request_is_safe(
        self,
    ):
        api = QueueApi(
            invalid=True
        )

        result = (
            SpotifyPlaybackService(
                SessionStub(),
                api_client=api,
            )
            .add_to_queue(
                "spotify:album:album123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyPlaybackServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_playback_request",
        )

    def test_add_to_queue_reauthorization_is_preserved(
        self,
    ):
        api = QueueApi(
            error=SpotifyWebApiError(
                "reauthorization_required",
                "expired",
            )
        )

        result = (
            SpotifyPlaybackService(
                SessionStub(),
                api_client=api,
            )
            .add_to_queue(
                "spotify:track:track123"
            )
        )

        self.assertTrue(
            result.requires_reauthorization
        )

    def test_add_to_queue_rate_limit_preserves_retry_after(
        self,
    ):
        api = QueueApi(
            error=SpotifyWebApiError(
                "rate_limited",
                "slow down",
                retry_after_seconds=7,
            )
        )

        result = (
            SpotifyPlaybackService(
                SessionStub(),
                api_client=api,
            )
            .add_to_queue(
                "spotify:track:track123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyPlaybackServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "rate_limited",
        )

        self.assertEqual(
            result.retry_after_seconds,
            7,
        )

    def test_add_to_queue_preserves_refreshed_session(
        self,
    ):
        api = QueueApi()

        result = (
            SpotifyPlaybackService(
                SessionStub(
                    SpotifySessionStatus.REFRESHED
                ),
                api_client=api,
            )
            .add_to_queue(
                "spotify:track:track123"
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertTrue(
            result.refreshed
        )

    def test_missing_add_to_queue_api_is_safe(
        self,
    ):
        api = LegacyApi()

        result = (
            SpotifyPlaybackService(
                SessionStub(),
                api_client=api,
            )
            .add_to_queue(
                "spotify:track:track123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyPlaybackServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_playback_api",
        )

        self.assertEqual(
            api.calls,
            [],
        )


if __name__ == "__main__":
    unittest.main()
