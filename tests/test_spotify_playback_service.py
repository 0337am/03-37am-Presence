from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.spotify.playback_service import (
    SpotifyPlaybackService,
    SpotifyPlaybackServiceResult,
    SpotifyPlaybackServiceStatus,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiError,
)


TRACK_URI = (
    "spotify:track:"
    "4uLU6hMCjMI75M1A2tKUQC"
)


class SessionManagerStub:
    def __init__(
        self,
        result=None,
        *,
        error=None,
    ):
        self.result = result
        self.error = error
        self.calls = 0

    def resolve(
        self,
    ):
        self.calls += 1

        if self.error is not None:
            raise self.error

        return self.result


class ApiStub:
    def __init__(
        self,
        *,
        error=None,
        devices=None,
    ):
        self.error = error
        self.devices = (
            {
                "devices": []
            }
            if devices is None
            else {
                "devices": devices
            }
        )

        self.calls = []
        self.device_calls = []
        self.playlist_calls = []

    def start_playback(
        self,
        access_token,
        spotify_uri,
        *,
        device_id=None,
    ):
        self.calls.append(
            (
                access_token,
                spotify_uri,
            )
        )

        if self.error is not None:
            raise self.error

    def get_available_devices(
        self,
        access_token,
    ):
        self.device_calls.append(
            access_token
        )

        return self.devices

    def start_playlist_playback(
        self,
        access_token,
        playlist_uri,
        spotify_uri,
        *,
        device_id=None,
    ):
        self.playlist_calls.append(
            (
                access_token,
                playlist_uri,
                spotify_uri,
                device_id,
            )
        )

        if self.error is not None:
            raise self.error


def session(
    status,
    *,
    access_token="secret-access-token",
):
    token = (
        None
        if access_token is None
        else SimpleNamespace(
            access_token=access_token
        )
    )

    return SimpleNamespace(
        status=status,
        token=token,
    )


class SpotifyPlaybackServiceTests(
    unittest.TestCase
):
    def test_constructor_requires_session_resolver(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyPlaybackService(
                object(),
                api_client=ApiStub(),
            )

    def test_constructor_requires_playback_api(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.READY
            )
        )

        with self.assertRaises(
            TypeError
        ):
            SpotifyPlaybackService(
                manager,
                api_client=object(),
            )

    def test_local_uri_is_rejected_before_session_resolution(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.READY
            )
        )

        api = ApiStub()

        service = SpotifyPlaybackService(
            manager,
            api_client=api,
        )

        result = service.play_track(
            "spotify:local:Artist:Album:Track:123"
        )

        self.assertEqual(
            result.status,
            SpotifyPlaybackServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_track_uri",
        )

        self.assertEqual(
            manager.calls,
            0,
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_malformed_uri_is_rejected_before_session_resolution(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.READY
            )
        )

        service = SpotifyPlaybackService(
            manager,
            api_client=ApiStub(),
        )

        result = service.play_track(
            "https://open.spotify.com/track/test"
        )

        self.assertEqual(
            result.error_code,
            "invalid_track_uri",
        )

        self.assertEqual(
            manager.calls,
            0,
        )

    def test_disconnected_session_is_safe(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.DISCONNECTED,
                access_token=None,
            )
        )

        api = ApiStub()

        result = SpotifyPlaybackService(
            manager,
            api_client=api,
        ).play_track(
            TRACK_URI
        )

        self.assertEqual(
            result.status,
            SpotifyPlaybackServiceStatus.DISCONNECTED,
        )

        self.assertFalse(
            result.ready
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_reauthorization_session_is_safe(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus
                .REAUTHORIZATION_REQUIRED,
                access_token=None,
            )
        )

        result = SpotifyPlaybackService(
            manager,
            api_client=ApiStub(),
        ).play_track(
            TRACK_URI
        )

        self.assertTrue(
            result.requires_reauthorization
        )

    def test_ready_session_starts_expected_track(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.READY
            )
        )

        api = ApiStub()

        result = SpotifyPlaybackService(
            manager,
            api_client=api,
        ).play_track(
            TRACK_URI
        )

        self.assertTrue(
            result.ready
        )

        self.assertFalse(
            result.refreshed
        )

        self.assertEqual(
            api.calls,
            [
                (
                    "secret-access-token",
                    TRACK_URI,
                ),
            ],
        )

    def test_refreshed_session_is_preserved(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.REFRESHED
            )
        )

        result = SpotifyPlaybackService(
            manager,
            api_client=ApiStub(),
        ).play_track(
            TRACK_URI
        )

        self.assertTrue(
            result.ready
        )

        self.assertTrue(
            result.refreshed
        )

    def test_missing_access_token_is_safe(
        self,
    ):
        manager = SessionManagerStub(
            SimpleNamespace(
                status=(
                    SpotifySessionStatus.READY
                ),
                token=SimpleNamespace(
                    access_token=""
                ),
            )
        )

        api = ApiStub()

        result = SpotifyPlaybackService(
            manager,
            api_client=api,
        ).play_track(
            TRACK_URI
        )

        self.assertEqual(
            result.error_code,
            "invalid_session",
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_api_reauthorization_maps_to_service_state(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.READY
            )
        )

        api = ApiStub(
            error=SpotifyWebApiError(
                "reauthorization_required",
                "Reconnect.",
            )
        )

        result = SpotifyPlaybackService(
            manager,
            api_client=api,
        ).play_track(
            TRACK_URI
        )

        self.assertTrue(
            result.requires_reauthorization
        )

    def test_rate_limit_metadata_is_preserved(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.READY
            )
        )

        api = ApiStub(
            error=SpotifyWebApiError(
                "rate_limited",
                "Wait.",
                retry_after_seconds=17,
            )
        )

        result = SpotifyPlaybackService(
            manager,
            api_client=api,
        ).play_track(
            TRACK_URI
        )

        self.assertEqual(
            result.status,
            SpotifyPlaybackServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "rate_limited",
        )

        self.assertEqual(
            result.retry_after_seconds,
            17,
        )

    def test_unexpected_api_exception_is_safe(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.READY
            )
        )

        api = ApiStub(
            error=RuntimeError(
                "sensitive transport detail"
            )
        )

        result = SpotifyPlaybackService(
            manager,
            api_client=api,
        ).play_track(
            TRACK_URI
        )

        self.assertEqual(
            result.error_code,
            "playback_failed",
        )

        self.assertNotIn(
            "sensitive transport detail",
            result.message,
        )

    def test_session_exception_is_safe(
        self,
    ):
        manager = SessionManagerStub(
            error=RuntimeError(
                "sensitive session detail"
            )
        )

        api = ApiStub()

        result = SpotifyPlaybackService(
            manager,
            api_client=api,
        ).play_track(
            TRACK_URI
        )

        self.assertEqual(
            result.error_code,
            "session_error",
        )

        self.assertEqual(
            api.calls,
            [],
        )

        self.assertNotIn(
            "sensitive session detail",
            result.message,
        )

    def test_error_result_requires_error_code(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyPlaybackServiceResult(
                status=(
                    SpotifyPlaybackServiceStatus.ERROR
                )
            )

    def test_retry_after_is_validated(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyPlaybackServiceResult(
                status=(
                    SpotifyPlaybackServiceStatus.ERROR
                ),
                error_code="rate_limited",
                retry_after_seconds=-1,
            )


    def test_playlist_playback_prefers_active_device(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.READY
            )
        )

        api = ApiStub(
            devices=[
                {
                    "id": "desktop",
                    "type": "Computer",
                    "is_active": False,
                    "is_restricted": False,
                },
                {
                    "id": "phone",
                    "type": "Smartphone",
                    "is_active": True,
                    "is_restricted": False,
                },
            ]
        )

        result = SpotifyPlaybackService(
            manager,
            api_client=api,
        ).play_playlist_track(
            "37i9dQZF1DXcBWIGoYBM5M",
            TRACK_URI,
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            api.playlist_calls,
            [
                (
                    "secret-access-token",
                    (
                        "spotify:playlist:"
                        "37i9dQZF1DXcBWIGoYBM5M"
                    ),
                    TRACK_URI,
                    "phone",
                ),
            ],
        )

    def test_playlist_playback_falls_back_to_computer_when_paused(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.READY
            )
        )

        api = ApiStub(
            devices=[
                {
                    "id": "speaker",
                    "type": "Speaker",
                    "is_active": False,
                    "is_restricted": False,
                },
                {
                    "id": "desktop",
                    "type": "Computer",
                    "is_active": False,
                    "is_restricted": False,
                },
            ]
        )

        result = SpotifyPlaybackService(
            manager,
            api_client=api,
        ).play_playlist_track(
            "37i9dQZF1DXcBWIGoYBM5M",
            TRACK_URI,
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            api.playlist_calls[0][3],
            "desktop",
        )

    def test_restricted_device_is_not_selected(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.READY
            )
        )

        api = ApiStub(
            devices=[
                {
                    "id": "restricted",
                    "type": "Computer",
                    "is_active": True,
                    "is_restricted": True,
                },
                {
                    "id": "usable",
                    "type": "Computer",
                    "is_active": False,
                    "is_restricted": False,
                },
            ]
        )

        result = SpotifyPlaybackService(
            manager,
            api_client=api,
        ).play_playlist_track(
            "37i9dQZF1DXcBWIGoYBM5M",
            TRACK_URI,
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            api.playlist_calls[0][3],
            "usable",
        )

    def test_playlist_playback_without_devices_uses_active_device_fallback(
        self,
    ):
        manager = SessionManagerStub(
            session(
                SpotifySessionStatus.READY
            )
        )

        api = ApiStub(
            devices=[]
        )

        result = SpotifyPlaybackService(
            manager,
            api_client=api,
        ).play_playlist_track(
            "37i9dQZF1DXcBWIGoYBM5M",
            TRACK_URI,
        )

        self.assertTrue(
            result.ready
        )

        self.assertIsNone(
            api.playlist_calls[0][3]
        )

if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
