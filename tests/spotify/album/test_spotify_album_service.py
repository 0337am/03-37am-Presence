import unittest
from types import SimpleNamespace

from src.spotify.album_service import (
    SpotifyAlbumService,
    SpotifyAlbumServiceResult,
    SpotifyAlbumServiceStatus,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)


def album_payload():
    return {
        "id": "album123",
        "name": "Example Album",
        "uri": "spotify:album:album123",
        "album_type": "album",
        "total_tracks": 1,
        "artists": [
            {
                "name": "Artist One",
            },
        ],
        "images": [],
        "external_urls": {},
        "release_date": "2026",
        "release_date_precision": "year",
    }


def track_payload():
    return {
        "id": "track123",
        "name": "Example Track",
        "uri": "spotify:track:track123",
        "artists": [
            {
                "name": "Artist One",
            },
        ],
        "duration_ms": 120000,
        "disc_number": 1,
        "track_number": 1,
        "explicit": False,
        "external_urls": {},
    }


def tracks_payload():
    return {
        "items": [
            track_payload()
        ],
        "limit": 50,
        "offset": 0,
        "total": 1,
        "next": None,
        "previous": None,
    }


class FakeSessionManager:
    def __init__(
        self,
        status=SpotifySessionStatus.READY,
    ):
        self.status = status

    def resolve(
        self,
    ):
        return SimpleNamespace(
            status=self.status,
            token=SimpleNamespace(
                access_token="token123"
            ),
        )


class FakeApiClient:
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


class SpotifyAlbumServiceResultTests(
    unittest.TestCase
):
    def test_ready_result_requires_one_payload(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyAlbumServiceResult(
                status=(
                    SpotifyAlbumServiceStatus.READY
                ),
            )

    def test_ready_result_rejects_two_payloads(
        self,
    ):
        payload = album_payload()

        service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=FakeApiClient(
                payload
            ),
        )

        album = (
            service.get_album(
                "album123"
            )
            .album
        )

        tracks_service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=FakeApiClient(
                tracks_payload()
            ),
        )

        page = (
            tracks_service.get_album_tracks(
                "album123"
            )
            .tracks_page
        )

        with self.assertRaises(
            ValueError
        ):
            SpotifyAlbumServiceResult(
                status=(
                    SpotifyAlbumServiceStatus.READY
                ),
                album=album,
                tracks_page=page,
            )

    def test_error_result_requires_error_code(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyAlbumServiceResult(
                status=(
                    SpotifyAlbumServiceStatus.ERROR
                ),
            )

    def test_non_ready_rejects_payload(
        self,
    ):
        service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=FakeApiClient(
                album_payload()
            ),
        )

        album = (
            service.get_album(
                "album123"
            )
            .album
        )

        with self.assertRaises(
            ValueError
        ):
            SpotifyAlbumServiceResult(
                status=(
                    SpotifyAlbumServiceStatus
                    .DISCONNECTED
                ),
                album=album,
            )

    def test_retry_after_is_validated(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyAlbumServiceResult(
                status=(
                    SpotifyAlbumServiceStatus.ERROR
                ),
                error_code="rate_limited",
                retry_after_seconds=-1,
            )


class SpotifyAlbumServiceTests(
    unittest.TestCase
):
    def test_constructor_requires_resolve(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyAlbumService(
                object()
            )

    def test_get_album_uses_album_endpoint(
        self,
    ):
        api = FakeApiClient(
            album_payload()
        )

        service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=api,
        )

        result = service.get_album(
            "album123"
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            result.album.name,
            "Example Album",
        )

        self.assertEqual(
            api.calls,
            [
                (
                    "token123",
                    "/albums/album123",
                    None,
                ),
            ],
        )

    def test_get_album_accepts_market(
        self,
    ):
        api = FakeApiClient(
            album_payload()
        )

        service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=api,
        )

        service.get_album(
            "album123",
            market="gb",
        )

        self.assertEqual(
            api.calls[0][2],
            {
                "market": "GB",
            },
        )

    def test_get_album_tracks_uses_paged_endpoint(
        self,
    ):
        api = FakeApiClient(
            tracks_payload()
        )

        service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=api,
        )

        result = service.get_album_tracks(
            "album123",
            limit=50,
            offset=0,
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            len(
                result.tracks_page.items
            ),
            1,
        )

        self.assertEqual(
            api.calls,
            [
                (
                    "token123",
                    "/albums/album123/tracks",
                    {
                        "limit": 50,
                        "offset": 0,
                    },
                ),
            ],
        )

    def test_get_album_tracks_forwards_market(
        self,
    ):
        api = FakeApiClient(
            tracks_payload()
        )

        service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=api,
        )

        service.get_album_tracks(
            "album123",
            limit=20,
            offset=40,
            market="us",
        )

        self.assertEqual(
            api.calls[0][2],
            {
                "limit": 20,
                "offset": 40,
                "market": "US",
            },
        )

    def test_disconnected_result_is_safe(
        self,
    ):
        api = FakeApiClient(
            album_payload()
        )

        service = SpotifyAlbumService(
            FakeSessionManager(
                SpotifySessionStatus.DISCONNECTED
            ),
            api_client=api,
        )

        result = service.get_album(
            "album123"
        )

        self.assertEqual(
            result.status,
            SpotifyAlbumServiceStatus.DISCONNECTED,
        )

        self.assertFalse(
            result.ready
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_reauthorization_result_is_safe(
        self,
    ):
        api = FakeApiClient(
            album_payload()
        )

        service = SpotifyAlbumService(
            FakeSessionManager(
                SpotifySessionStatus
                .REAUTHORIZATION_REQUIRED
            ),
            api_client=api,
        )

        result = service.get_album(
            "album123"
        )

        self.assertTrue(
            result.requires_reauthorization
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_refreshed_session_is_preserved(
        self,
    ):
        api = FakeApiClient(
            album_payload()
        )

        service = SpotifyAlbumService(
            FakeSessionManager(
                SpotifySessionStatus.REFRESHED
            ),
            api_client=api,
        )

        result = service.get_album(
            "album123"
        )

        self.assertTrue(
            result.ready
        )

        self.assertTrue(
            result.refreshed
        )

    def test_invalid_album_response_is_safe(
        self,
    ):
        api = FakeApiClient(
            {
                "id": "album123",
                "uri": "spotify:album:wrong",
            }
        )

        service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=api,
        )

        result = service.get_album(
            "album123"
        )

        self.assertEqual(
            result.status,
            SpotifyAlbumServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_response",
        )

    def test_invalid_track_page_response_is_safe(
        self,
    ):
        api = FakeApiClient(
            {
                "items": {},
                "limit": 50,
                "offset": 0,
                "total": 0,
            }
        )

        service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=api,
        )

        result = service.get_album_tracks(
            "album123"
        )

        self.assertEqual(
            result.status,
            SpotifyAlbumServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_response",
        )

    def test_unexpected_api_error_is_safe(
        self,
    ):
        api = FakeApiClient(
            error=RuntimeError(
                "boom"
            )
        )

        service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=api,
        )

        result = service.get_album(
            "album123"
        )

        self.assertEqual(
            result.status,
            SpotifyAlbumServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "spotify_api_error",
        )

    def test_invalid_limit_is_rejected_before_request(
        self,
    ):
        api = FakeApiClient(
            tracks_payload()
        )

        service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=api,
        )

        with self.assertRaises(
            ValueError
        ):
            service.get_album_tracks(
                "album123",
                limit=51,
            )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_invalid_market_is_rejected_before_request(
        self,
    ):
        api = FakeApiClient(
            album_payload()
        )

        service = SpotifyAlbumService(
            FakeSessionManager(),
            api_client=api,
        )

        with self.assertRaises(
            ValueError
        ):
            service.get_album(
                "album123",
                market="United Kingdom",
            )

        self.assertEqual(
            api.calls,
            [],
        )


if __name__ == "__main__":
    unittest.main()
