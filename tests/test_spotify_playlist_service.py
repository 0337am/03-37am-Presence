from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.spotify.playlist_service import (
    SpotifyPlaylistService,
    SpotifyPlaylistServiceStatus,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)


def playlist_page_payload():
    return {
        "limit": 50,
        "offset": 0,
        "total": 1,
        "items": [
            {
                "id": "playlist123",
                "name": "Local Juice",
                "uri": (
                    "spotify:playlist:playlist123"
                ),
                "owner": {
                    "id": "owner",
                    "display_name": "Owner",
                },
                "description": "",
                "public": False,
                "collaborative": False,
                "images": [],
                "items": {
                    "href": "https://api.spotify.com/x",
                    "total": 1,
                },
            },
        ],
    }


def item_page_payload():
    return {
        "limit": 50,
        "offset": 0,
        "total": 1,
        "items": [
            {
                "added_at": (
                    "2026-08-08T00:00:00Z"
                ),
                "is_local": True,
                "item": {
                    "album": {
                        "name": "Unreleased",
                        "images": [],
                    },
                    "artists": [
                        {
                            "name": "Juice WRLD",
                        },
                    ],
                    "duration_ms": 240000,
                    "id": None,
                    "is_local": True,
                    "is_playable": False,
                    "name": "Rental",
                    "type": "track",
                    "uri": (
                        "spotify:local:"
                        "Juice%20WRLD:"
                        "Unreleased:"
                        "Rental:240"
                    ),
                },
            },
        ],
    }


class FakeSessionManager:
    def __init__(
        self,
        status=SpotifySessionStatus.READY,
        *,
        access_token="safe-token",
        error=None,
    ):
        self.status = status
        self.access_token = (
            access_token
        )
        self.error = error
        self.calls = 0

    def resolve(
        self,
    ):
        self.calls += 1

        if self.error is not None:
            raise self.error

        return SimpleNamespace(
            status=self.status,
            token=SimpleNamespace(
                access_token=(
                    self.access_token
                )
            ),
        )


class FakeApi:
    def __init__(
        self,
        payload,
        *,
        error=None,
    ):
        self.payload = payload
        self.error = error
        self.calls = []

    def get_json(
        self,
        access_token,
        path,
        *,
        query=None,
    ):
        self.calls.append(
            (
                access_token,
                path,
                query,
            )
        )

        if self.error is not None:
            raise self.error

        return self.payload


class FakeWebApiError(
    RuntimeError
):
    def __init__(
        self,
        error_code,
        *,
        retry_after_seconds=None,
    ):
        super().__init__(
            error_code
        )

        self.error_code = (
            error_code
        )

        self.retry_after_seconds = (
            retry_after_seconds
        )


class SpotifyPlaylistServiceTests(
    unittest.TestCase
):
    def test_constructor_requires_session_resolve(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyPlaylistService(
                object()
            )

    def test_constructor_requires_api_get_json(
        self,
    ):
        session = (
            FakeSessionManager()
        )

        with self.assertRaises(
            TypeError
        ):
            SpotifyPlaylistService(
                session,
                api_client=object(),
            )

    def test_list_limit_is_validated_before_session(
        self,
    ):
        session = (
            FakeSessionManager()
        )

        service = (
            SpotifyPlaylistService(
                session,
                api_client=FakeApi(
                    playlist_page_payload()
                ),
            )
        )

        with self.assertRaises(
            ValueError
        ):
            service.get_current_playlists(
                limit=51
            )

        self.assertEqual(
            session.calls,
            0,
        )

    def test_list_offset_is_validated_before_session(
        self,
    ):
        session = (
            FakeSessionManager()
        )

        service = (
            SpotifyPlaylistService(
                session,
                api_client=FakeApi(
                    playlist_page_payload()
                ),
            )
        )

        with self.assertRaises(
            ValueError
        ):
            service.get_current_playlists(
                offset=-1
            )

        self.assertEqual(
            session.calls,
            0,
        )

    def test_playlist_id_is_validated_before_session(
        self,
    ):
        session = (
            FakeSessionManager()
        )

        service = (
            SpotifyPlaylistService(
                session,
                api_client=FakeApi(
                    item_page_payload()
                ),
            )
        )

        with self.assertRaises(
            ValueError
        ):
            service.get_playlist_items(
                "../secret"
            )

        self.assertEqual(
            session.calls,
            0,
        )

    def test_market_is_validated_before_session(
        self,
    ):
        session = (
            FakeSessionManager()
        )

        service = (
            SpotifyPlaylistService(
                session,
                api_client=FakeApi(
                    item_page_payload()
                ),
            )
        )

        with self.assertRaises(
            ValueError
        ):
            service.get_playlist_items(
                "playlist123",
                market="GBR",
            )

        self.assertEqual(
            session.calls,
            0,
        )

    def test_disconnected_session_never_calls_api(
        self,
    ):
        api = FakeApi(
            playlist_page_payload()
        )

        service = (
            SpotifyPlaylistService(
                FakeSessionManager(
                    SpotifySessionStatus
                    .DISCONNECTED
                ),
                api_client=api,
            )
        )

        result = (
            service.get_current_playlists()
        )

        self.assertIs(
            result.status,
            SpotifyPlaylistServiceStatus
            .DISCONNECTED,
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_reauthorization_session_never_calls_api(
        self,
    ):
        api = FakeApi(
            playlist_page_payload()
        )

        service = (
            SpotifyPlaylistService(
                FakeSessionManager(
                    SpotifySessionStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                api_client=api,
            )
        )

        result = (
            service.get_current_playlists()
        )

        self.assertIs(
            result.status,
            SpotifyPlaylistServiceStatus
            .REAUTHORIZATION_REQUIRED,
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_ready_list_builds_expected_request(
        self,
    ):
        api = FakeApi(
            playlist_page_payload()
        )

        service = (
            SpotifyPlaylistService(
                FakeSessionManager(),
                api_client=api,
            )
        )

        result = (
            service.get_current_playlists(
                limit=25,
                offset=5,
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            api.calls,
            [
                (
                    "safe-token",
                    "/me/playlists",
                    {
                        "limit": 25,
                        "offset": 5,
                    },
                ),
            ],
        )

    def test_refreshed_session_is_preserved(
        self,
    ):
        service = (
            SpotifyPlaylistService(
                FakeSessionManager(
                    SpotifySessionStatus
                    .REFRESHED
                ),
                api_client=FakeApi(
                    playlist_page_payload()
                ),
            )
        )

        result = (
            service.get_current_playlists()
        )

        self.assertTrue(
            result.ready
        )

        self.assertTrue(
            result.refreshed
        )

    def test_ready_items_builds_current_items_endpoint(
        self,
    ):
        api = FakeApi(
            item_page_payload()
        )

        service = (
            SpotifyPlaylistService(
                FakeSessionManager(),
                api_client=api,
            )
        )

        result = (
            service.get_playlist_items(
                "playlist123",
                limit=40,
                offset=10,
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            api.calls[
                0
            ][1],
            (
                "/playlists/"
                "playlist123/items"
            ),
        )

        self.assertEqual(
            api.calls[
                0
            ][2],
            {
                "limit": 40,
                "offset": 10,
            },
        )

    def test_items_request_includes_market_when_set(
        self,
    ):
        api = FakeApi(
            item_page_payload()
        )

        service = (
            SpotifyPlaylistService(
                FakeSessionManager(),
                api_client=api,
            )
        )

        service.get_playlist_items(
            "playlist123",
            market="gb",
        )

        self.assertEqual(
            api.calls[
                0
            ][2][
                "market"
            ],
            "GB",
        )

    def test_web_api_reauthorization_maps_to_service_state(
        self,
    ):
        error = FakeWebApiError(
            "reauthorization_required"
        )

        api = FakeApi(
            None,
            error=error,
        )

        service = (
            SpotifyPlaylistService(
                FakeSessionManager(),
                api_client=api,
            )
        )

        with patch(
            (
                "src.spotify.playlist_service."
                "SpotifyWebApiError"
            ),
            FakeWebApiError,
        ):
            result = (
                service.get_current_playlists()
            )

        self.assertIs(
            result.status,
            SpotifyPlaylistServiceStatus
            .REAUTHORIZATION_REQUIRED,
        )

    def test_rate_limit_metadata_is_preserved(
        self,
    ):
        error = FakeWebApiError(
            "rate_limit",
            retry_after_seconds=17,
        )

        api = FakeApi(
            None,
            error=error,
        )

        service = (
            SpotifyPlaylistService(
                FakeSessionManager(),
                api_client=api,
            )
        )

        with patch(
            (
                "src.spotify.playlist_service."
                "SpotifyWebApiError"
            ),
            FakeWebApiError,
        ):
            result = (
                service.get_current_playlists()
            )

        self.assertIs(
            result.status,
            SpotifyPlaylistServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.error_code,
            "rate_limit",
        )

        self.assertEqual(
            result.retry_after_seconds,
            17,
        )

    def test_forbidden_error_is_preserved(
        self,
    ):
        error = FakeWebApiError(
            "forbidden"
        )

        service = (
            SpotifyPlaylistService(
                FakeSessionManager(),
                api_client=FakeApi(
                    None,
                    error=error,
                ),
            )
        )

        with patch(
            (
                "src.spotify.playlist_service."
                "SpotifyWebApiError"
            ),
            FakeWebApiError,
        ):
            result = (
                service.get_playlist_items(
                    "playlist123"
                )
            )

        self.assertIs(
            result.status,
            SpotifyPlaylistServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.error_code,
            "forbidden",
        )

    def test_unexpected_api_exception_is_safe(
        self,
    ):
        service = (
            SpotifyPlaylistService(
                FakeSessionManager(),
                api_client=FakeApi(
                    None,
                    error=RuntimeError(
                        "private detail"
                    ),
                ),
            )
        )

        result = (
            service.get_current_playlists()
        )

        self.assertEqual(
            result.error_code,
            "spotify_api_error",
        )

        self.assertNotIn(
            "private detail",
            result.message,
        )

    def test_session_exception_is_safe(
        self,
    ):
        service = (
            SpotifyPlaylistService(
                FakeSessionManager(
                    error=RuntimeError(
                        "private detail"
                    )
                ),
                api_client=FakeApi(
                    playlist_page_payload()
                ),
            )
        )

        result = (
            service.get_current_playlists()
        )

        self.assertEqual(
            result.error_code,
            "session_error",
        )

        self.assertNotIn(
            "private detail",
            result.message,
        )

    def test_invalid_playlist_response_is_safe(
        self,
    ):
        service = (
            SpotifyPlaylistService(
                FakeSessionManager(),
                api_client=FakeApi(
                    {
                        "not": "a page",
                    }
                ),
            )
        )

        result = (
            service.get_current_playlists()
        )

        self.assertEqual(
            result.error_code,
            "invalid_response",
        )

    def test_invalid_items_response_is_safe(
        self,
    ):
        service = (
            SpotifyPlaylistService(
                FakeSessionManager(),
                api_client=FakeApi(
                    {
                        "limit": 50,
                        "offset": 0,
                        "total": 1,
                        "items": [
                            {
                                "is_local": True,
                                "item": {
                                    "type": "track",
                                    "name": "",
                                },
                            },
                        ],
                    }
                ),
            )
        )

        result = (
            service.get_playlist_items(
                "playlist123"
            )
        )

        self.assertEqual(
            result.error_code,
            "invalid_response",
        )


class SpotifyPlaylistServiceBoundaryTests(
    unittest.TestCase
):
    def test_service_owns_no_qt_local_index_playback_or_credentials(
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
            / "playlist_service.py"
        ).read_text(
            encoding="utf-8"
        )

        for forbidden in (
            "PyQt",
            "QSettings",
            "SpotifyCredentialStore",
            "SpotifyTokenClient",
            "refresh_token",
            "LocalMusicIndex",
            "LocalTrackResolver",
            "LocalTrackCandidate",
            "playback",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    source,
                )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
