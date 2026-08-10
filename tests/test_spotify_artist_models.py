import unittest

from src.spotify.artist_models import (
    SpotifyArtistParseError,
    spotify_artist_albums_page_from_payload,
    spotify_artist_summary_from_payload,
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
                "width": 640,
                "height": 640,
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


class SpotifyArtistModelTests(
    unittest.TestCase
):
    def test_artist_maps_core_fields(
        self,
    ):
        artist = (
            spotify_artist_summary_from_payload(
                artist_payload()
            )
        )

        self.assertEqual(
            artist.spotify_id,
            "artist123",
        )
        self.assertEqual(
            artist.name,
            "Artist One",
        )
        self.assertEqual(
            artist.uri,
            "spotify:artist:artist123",
        )
        self.assertEqual(
            artist.spotify_url,
            (
                "https://open.spotify.com/"
                "artist/artist123"
            ),
        )
        self.assertEqual(
            artist.image_url,
            (
                "https://i.scdn.co/"
                "image/artist-image"
            ),
        )

    def test_artist_allows_missing_optional_metadata(
        self,
    ):
        payload = artist_payload()
        payload.pop("external_urls")
        payload.pop("images")

        artist = (
            spotify_artist_summary_from_payload(
                payload
            )
        )

        self.assertEqual(
            artist.spotify_url,
            "",
        )
        self.assertEqual(
            artist.image_url,
            "",
        )

    def test_artist_rejects_mismatched_uri(
        self,
    ):
        payload = artist_payload()
        payload["uri"] = (
            "spotify:artist:different"
        )

        with self.assertRaises(
            SpotifyArtistParseError
        ):
            spotify_artist_summary_from_payload(
                payload
            )

    def test_artist_rejects_wrong_type(
        self,
    ):
        payload = artist_payload()
        payload["type"] = "album"

        with self.assertRaises(
            SpotifyArtistParseError
        ):
            spotify_artist_summary_from_payload(
                payload
            )

    def test_artist_does_not_require_deprecated_fields(
        self,
    ):
        payload = artist_payload()

        self.assertNotIn(
            "followers",
            payload,
        )
        self.assertNotIn(
            "genres",
            payload,
        )
        self.assertNotIn(
            "popularity",
            payload,
        )

        artist = (
            spotify_artist_summary_from_payload(
                payload
            )
        )

        self.assertEqual(
            artist.name,
            "Artist One",
        )

    def test_artist_albums_page_maps_album_models(
        self,
    ):
        page = (
            spotify_artist_albums_page_from_payload(
                {
                    "items": [
                        album_payload(),
                    ],
                    "limit": 10,
                    "offset": 0,
                    "total": 1,
                    "next": None,
                    "previous": None,
                }
            )
        )

        self.assertEqual(
            len(page.items),
            1,
        )
        self.assertEqual(
            page.items[0].spotify_id,
            "album123",
        )
        self.assertEqual(
            page.limit,
            10,
        )
        self.assertEqual(
            page.offset,
            0,
        )
        self.assertEqual(
            page.total,
            1,
        )
        self.assertTrue(
            page.complete
        )

    def test_artist_albums_page_reports_more_results(
        self,
    ):
        page = (
            spotify_artist_albums_page_from_payload(
                {
                    "items": [
                        album_payload(),
                    ],
                    "limit": 10,
                    "offset": 0,
                    "total": 20,
                    "next": (
                        "https://api.spotify.com/"
                        "v1/artists/artist123/"
                        "albums?offset=10"
                    ),
                    "previous": None,
                }
            )
        )

        self.assertFalse(
            page.complete
        )

    def test_artist_albums_page_rejects_invalid_album(
        self,
    ):
        album = album_payload()
        album["uri"] = (
            "spotify:album:different"
        )

        with self.assertRaises(
            SpotifyArtistParseError
        ):
            spotify_artist_albums_page_from_payload(
                {
                    "items": [
                        album,
                    ],
                    "limit": 10,
                    "offset": 0,
                    "total": 1,
                    "next": None,
                    "previous": None,
                }
            )

    def test_artist_albums_page_rejects_non_list_items(
        self,
    ):
        with self.assertRaises(
            SpotifyArtistParseError
        ):
            spotify_artist_albums_page_from_payload(
                {
                    "items": {},
                    "limit": 10,
                    "offset": 0,
                    "total": 0,
                }
            )

    def test_artist_albums_page_rejects_negative_total(
        self,
    ):
        with self.assertRaises(
            SpotifyArtistParseError
        ):
            spotify_artist_albums_page_from_payload(
                {
                    "items": [],
                    "limit": 10,
                    "offset": 0,
                    "total": -1,
                }
            )


if __name__ == "__main__":
    unittest.main()