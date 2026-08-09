from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.spotify.liked_songs_service import (
    SpotifyLikedSongsService,
    SpotifyLikedSongsServiceStatus,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiError,
)


class FakeSessionManager:
    def __init__(
        self,
        result=None,
        error=None,
    ):
        self.result = result
        self.error = error

    def resolve(
        self,
    ):
        if self.error is not None:
            raise self.error

        return self.result


class FakeApi:
    def __init__(
        self,
        payload=None,
        error=None,
    ):
        self.payload = payload
        self.error = error
        self.calls = []

    def get_json(
        self,
        token,
        path,
        *,
        query=None,
    ):
        self.calls.append(
            (
                token,
                path,
                query,
            )
        )

        if self.error is not None:
            raise self.error

        return self.payload


def session(
    status=SpotifySessionStatus.READY,
    token="access-token",
):
    return SimpleNamespace(
        status=status,
        token=(
            SimpleNamespace(
                access_token=token
            )
            if token is not None
            else None
        ),
    )


class SpotifyLikedSongsServiceTests(
    unittest.TestCase
):
    def test_constructor_requires_session_resolve(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyLikedSongsService(
                object(),
                api_client=FakeApi(),
            )

    def test_constructor_requires_api_get_json(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyLikedSongsService(
                FakeSessionManager(
                    session()
                ),
                api_client=object(),
            )

    def test_ready_summary_requests_only_one_saved_track(
        self,
    ):
        api = FakeApi(
            {
                "total": 321,
                "items": [],
            }
        )

        service = SpotifyLikedSongsService(
            FakeSessionManager(
                session()
            ),
            api_client=api,
        )

        result = service.get_summary()

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            result.total,
            321,
        )

        self.assertEqual(
            api.calls,
            [
                (
                    "access-token",
                    "/me/tracks",
                    {
                        "limit": 1,
                        "offset": 0,
                    },
                )
            ],
        )

    def test_disconnected_session_is_safe(
        self,
    ):
        service = SpotifyLikedSongsService(
            FakeSessionManager(
                session(
                    SpotifySessionStatus
                    .DISCONNECTED,
                    token=None,
                )
            ),
            api_client=FakeApi(),
        )

        result = service.get_summary()

        self.assertEqual(
            result.status,
            SpotifyLikedSongsServiceStatus
            .DISCONNECTED,
        )

        self.assertFalse(
            result.ready
        )

    def test_reauthorization_session_is_safe(
        self,
    ):
        service = SpotifyLikedSongsService(
            FakeSessionManager(
                session(
                    SpotifySessionStatus
                    .REAUTHORIZATION_REQUIRED,
                    token=None,
                )
            ),
            api_client=FakeApi(),
        )

        result = service.get_summary()

        self.assertTrue(
            result.requires_reauthorization
        )

    def test_refreshed_session_is_preserved(
        self,
    ):
        service = SpotifyLikedSongsService(
            FakeSessionManager(
                session(
                    SpotifySessionStatus
                    .REFRESHED,
                )
            ),
            api_client=FakeApi(
                {
                    "total": 12,
                }
            ),
        )

        result = service.get_summary()

        self.assertTrue(
            result.ready
        )

        self.assertTrue(
            result.refreshed
        )

    def test_api_reauthorization_maps_to_reconnect(
        self,
    ):
        service = SpotifyLikedSongsService(
            FakeSessionManager(
                session()
            ),
            api_client=FakeApi(
                error=SpotifyWebApiError(
                    "reauthorization_required",
                    "expired",
                )
            ),
        )

        result = service.get_summary()

        self.assertTrue(
            result.requires_reauthorization
        )

    def test_rate_limit_preserves_retry_after(
        self,
    ):
        service = SpotifyLikedSongsService(
            FakeSessionManager(
                session()
            ),
            api_client=FakeApi(
                error=SpotifyWebApiError(
                    "rate_limited",
                    "slow down",
                    retry_after_seconds=9,
                )
            ),
        )

        result = service.get_summary()

        self.assertEqual(
            result.status,
            SpotifyLikedSongsServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.retry_after_seconds,
            9,
        )

    def test_missing_total_is_invalid_response(
        self,
    ):
        service = SpotifyLikedSongsService(
            FakeSessionManager(
                session()
            ),
            api_client=FakeApi(
                {}
            ),
        )

        result = service.get_summary()

        self.assertEqual(
            result.error_code,
            "invalid_response",
        )

    def test_boolean_total_is_invalid_response(
        self,
    ):
        service = SpotifyLikedSongsService(
            FakeSessionManager(
                session()
            ),
            api_client=FakeApi(
                {
                    "total": True,
                }
            ),
        )

        result = service.get_summary()

        self.assertEqual(
            result.error_code,
            "invalid_response",
        )

    def test_negative_total_is_invalid_response(
        self,
    ):
        service = SpotifyLikedSongsService(
            FakeSessionManager(
                session()
            ),
            api_client=FakeApi(
                {
                    "total": -1,
                }
            ),
        )

        result = service.get_summary()

        self.assertEqual(
            result.error_code,
            "invalid_response",
        )

    def test_unexpected_api_exception_is_safe(
        self,
    ):
        service = SpotifyLikedSongsService(
            FakeSessionManager(
                session()
            ),
            api_client=FakeApi(
                error=RuntimeError(
                    "simulated network failure"
                )
            ),
        )

        result = service.get_summary()

        self.assertEqual(
            result.status,
            SpotifyLikedSongsServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.error_code,
            "spotify_api_error",
        )
