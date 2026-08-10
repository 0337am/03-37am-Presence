import unittest
from types import SimpleNamespace

from src.spotify.artist_models import (
    spotify_artist_albums_page_from_payload,
    spotify_artist_summary_from_payload,
)
from src.spotify.artist_service import (
    DEFAULT_SPOTIFY_ARTIST_ALBUM_LIMIT,
    SpotifyArtistService,
    SpotifyArtistServiceResult,
    SpotifyArtistServiceStatus,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiError,
)


def artist_payload():
    return {
        "id": "artist123",
        "name": "Artist One",
        "type": "artist",
        "uri": "spotify:artist:artist123",
        "external_urls": {
            "spotify": (
                "https://open.spotify.com/"
                "artist/artist123"
            ),
        },
        "images": [
            {
                "url": (
                    "https://i.scdn.co/"
                    "image/artist-image"
                ),
            },
        ],
    }


def album_payload():
    return {
        "id": "album123",
        "name": "Album One",
        "type": "album",
        "uri": "spotify:album:album123",
        "album_type": "album",
        "total_tracks": 12,
        "artists": [
            {
                "id": "artist123",
                "name": "Artist One",
                "type": "artist",
                "uri": (
                    "spotify:artist:artist123"
                ),
            },
        ],
        "external_urls": {
            "spotify": (
                "https://open.spotify.com/"
                "album/album123"
            ),
        },
        "images": [
            {
                "url": (
                    "https://i.scdn.co/"
                    "image/album-image"
                ),
            },
        ],
        "release_date": "2026-08-10",
        "release_date_precision": "day",
    }


def albums_payload():
    return {
        "items": [
            album_payload(),
        ],
        "limit": 10,
        "offset": 0,
        "total": 1,
        "next": None,
        "previous": None,
    }


class FakeSessionManager:
    def __init__(
        self,
        status=SpotifySessionStatus.READY,
        *,
        access_token="token123",
    ):
        self.status = status
        self.access_token = access_token

    def resolve(
        self,
    ):
        return SimpleNamespace(
            status=self.status,
            token=SimpleNamespace(
                access_token=self.access_token
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


class FakeSpotifyWebApiError(
    SpotifyWebApiError
):
    def __init__(
        self,
        error_code,
        *,
        retry_after_seconds=None,
    ):
        Exception.__init__(
            self,
            error_code,
        )

        self.error_code = (
            error_code
        )

        self.retry_after_seconds = (
            retry_after_seconds
        )


class SpotifyArtistServiceResultTests(
    unittest.TestCase
):
    def test_ready_result_requires_payload(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyArtistServiceResult(
                status=(
                    SpotifyArtistServiceStatus
                    .READY
                )
            )

    def test_ready_result_rejects_two_payloads(
        self,
    ):
        artist = (
            spotify_artist_summary_from_payload(
                artist_payload()
            )
        )

        page = (
            spotify_artist_albums_page_from_payload(
                albums_payload()
            )
        )

        with self.assertRaises(
            ValueError
        ):
            SpotifyArtistServiceResult(
                status=(
                    SpotifyArtistServiceStatus
                    .READY
                ),
                artist=artist,
                albums_page=page,
            )

    def test_non_ready_result_rejects_payload(
        self,
    ):
        artist = (
            spotify_artist_summary_from_payload(
                artist_payload()
            )
        )

        with self.assertRaises(
            ValueError
        ):
            SpotifyArtistServiceResult(
                status=(
                    SpotifyArtistServiceStatus
                    .DISCONNECTED
                ),
                artist=artist,
            )

    def test_retry_after_is_validated(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyArtistServiceResult(
                status=(
                    SpotifyArtistServiceStatus
                    .ERROR
                ),
                error_code="rate_limited",
                retry_after_seconds=-1,
            )


class SpotifyArtistServiceTests(
    unittest.TestCase
):
    def test_constructor_requires_resolve(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyArtistService(
                object()
            )

    def test_get_artist_uses_artist_endpoint(
        self,
    ):
        api = FakeApiClient(
            artist_payload()
        )

        service = SpotifyArtistService(
            FakeSessionManager(),
            api_client=api,
        )

        result = service.get_artist(
            "artist123"
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            result.artist.name,
            "Artist One",
        )

        self.assertEqual(
            api.calls,
            [
                (
                    "token123",
                    "/artists/artist123",
                    None,
                ),
            ],
        )

    def test_get_artist_albums_uses_paged_endpoint(
        self,
    ):
        api = FakeApiClient(
            albums_payload()
        )

        service = SpotifyArtistService(
            FakeSessionManager(),
            api_client=api,
        )

        result = (
            service.get_artist_albums(
                "artist123",
                limit=10,
                offset=20,
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            result.albums_page.items[
                0
            ].name,
            "Album One",
        )

        self.assertEqual(
            api.calls,
            [
                (
                    "token123",
                    (
                        "/artists/"
                        "artist123/albums"
                    ),
                    {
                        "limit": 10,
                        "offset": 20,
                    },
                ),
            ],
        )

    def test_artist_album_limit_matches_api_boundary(
        self,
    ):
        self.assertEqual(
            DEFAULT_SPOTIFY_ARTIST_ALBUM_LIMIT,
            10,
        )

        service = SpotifyArtistService(
            FakeSessionManager(),
            api_client=FakeApiClient(
                albums_payload()
            ),
        )

        with self.assertRaises(
            ValueError
        ):
            service.get_artist_albums(
                "artist123",
                limit=11,
            )

    def test_artist_albums_forwards_market(
        self,
    ):
        api = FakeApiClient(
            albums_payload()
        )

        service = SpotifyArtistService(
            FakeSessionManager(),
            api_client=api,
        )

        service.get_artist_albums(
            "artist123",
            limit=5,
            offset=10,
            market="gb",
        )

        self.assertEqual(
            api.calls[
                0
            ][2],
            {
                "limit": 5,
                "offset": 10,
                "market": "GB",
            },
        )

    def test_disconnected_result_is_safe(
        self,
    ):
        api = FakeApiClient(
            artist_payload()
        )

        service = SpotifyArtistService(
            FakeSessionManager(
                SpotifySessionStatus
                .DISCONNECTED
            ),
            api_client=api,
        )

        result = service.get_artist(
            "artist123"
        )

        self.assertEqual(
            result.status,
            SpotifyArtistServiceStatus
            .DISCONNECTED,
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
            artist_payload()
        )

        service = SpotifyArtistService(
            FakeSessionManager(
                SpotifySessionStatus
                .REAUTHORIZATION_REQUIRED
            ),
            api_client=api,
        )

        result = service.get_artist(
            "artist123"
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
        service = SpotifyArtistService(
            FakeSessionManager(
                SpotifySessionStatus
                .REFRESHED
            ),
            api_client=FakeApiClient(
                artist_payload()
            ),
        )

        result = service.get_artist(
            "artist123"
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
        api = FakeApiClient(
            artist_payload()
        )

        service = SpotifyArtistService(
            FakeSessionManager(
                access_token=""
            ),
            api_client=api,
        )

        result = service.get_artist(
            "artist123"
        )

        self.assertEqual(
            result.status,
            SpotifyArtistServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "session_error",
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_invalid_artist_response_is_safe(
        self,
    ):
        api = FakeApiClient(
            {
                "id": "artist123",
                "name": "Artist One",
                "type": "artist",
                "uri": (
                    "spotify:artist:different"
                ),
            }
        )

        service = SpotifyArtistService(
            FakeSessionManager(),
            api_client=api,
        )

        result = service.get_artist(
            "artist123"
        )

        self.assertEqual(
            result.status,
            SpotifyArtistServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_response",
        )

    def test_invalid_album_page_response_is_safe(
        self,
    ):
        api = FakeApiClient(
            {
                "items": {},
                "limit": 10,
                "offset": 0,
                "total": 0,
            }
        )

        service = SpotifyArtistService(
            FakeSessionManager(),
            api_client=api,
        )

        result = (
            service.get_artist_albums(
                "artist123"
            )
        )

        self.assertEqual(
            result.status,
            SpotifyArtistServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_response",
        )

    def test_rate_limit_metadata_is_preserved(
        self,
    ):
        api = FakeApiClient(
            error=FakeSpotifyWebApiError(
                "rate_limited",
                retry_after_seconds=9,
            )
        )

        service = SpotifyArtistService(
            FakeSessionManager(),
            api_client=api,
        )

        result = service.get_artist(
            "artist123"
        )

        self.assertEqual(
            result.status,
            SpotifyArtistServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "rate_limited",
        )

        self.assertEqual(
            result.retry_after_seconds,
            9,
        )

    def test_api_reauthorization_is_mapped(
        self,
    ):
        api = FakeApiClient(
            error=FakeSpotifyWebApiError(
                "reauthorization_required"
            )
        )

        service = SpotifyArtistService(
            FakeSessionManager(),
            api_client=api,
        )

        result = service.get_artist(
            "artist123"
        )

        self.assertTrue(
            result.requires_reauthorization
        )

    def test_unexpected_api_error_is_safe(
        self,
    ):
        api = FakeApiClient(
            error=RuntimeError(
                "boom"
            )
        )

        service = SpotifyArtistService(
            FakeSessionManager(),
            api_client=api,
        )

        result = service.get_artist(
            "artist123"
        )

        self.assertEqual(
            result.status,
            SpotifyArtistServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "spotify_api_error",
        )

    def test_invalid_artist_id_is_rejected_before_api(
        self,
    ):
        api = FakeApiClient(
            artist_payload()
        )

        service = SpotifyArtistService(
            FakeSessionManager(),
            api_client=api,
        )

        with self.assertRaises(
            ValueError
        ):
            service.get_artist(
                "../bad"
            )

        self.assertEqual(
            api.calls,
            [],
        )


if __name__ == "__main__":
    unittest.main()