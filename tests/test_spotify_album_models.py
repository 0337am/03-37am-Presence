import unittest

from src.spotify.album_models import (
    SpotifyAlbumParseError,
    spotify_album_summary_from_payload,
    spotify_album_track_from_payload,
    spotify_album_tracks_page_from_payload,
)


def album_payload():
    return {
        "id": "album123",
        "name": "Example Album",
        "uri": "spotify:album:album123",
        "album_type": "album",
        "total_tracks": 2,
        "artists": [
            {
                "name": "Artist One",
            },
        ],
        "images": [
            {
                "url": "https://example.test/large.jpg",
            },
            {
                "url": "https://example.test/small.jpg",
            },
        ],
        "external_urls": {
            "spotify": (
                "https://open.spotify.com/album/album123"
            ),
        },
        "release_date": "2026-08-10",
        "release_date_precision": "day",
    }


def track_payload(
    *,
    spotify_id="track123",
    track_number=1,
):
    return {
        "id": spotify_id,
        "name": "Example Track",
        "uri": (
            "spotify:track:"
            + spotify_id
        ),
        "artists": [
            {
                "name": "Artist One",
            },
            {
                "name": "Artist Two",
            },
        ],
        "duration_ms": 185000,
        "disc_number": 1,
        "track_number": track_number,
        "explicit": True,
        "is_playable": True,
        "external_urls": {
            "spotify": (
                "https://open.spotify.com/track/"
                + spotify_id
            ),
        },
    }


class SpotifyAlbumModelTests(
    unittest.TestCase
):
    def test_album_summary_maps_core_fields(
        self,
    ):
        album = (
            spotify_album_summary_from_payload(
                album_payload()
            )
        )

        self.assertEqual(
            album.spotify_id,
            "album123",
        )

        self.assertEqual(
            album.name,
            "Example Album",
        )

        self.assertEqual(
            album.artist_text,
            "Artist One",
        )

        self.assertEqual(
            album.total_tracks,
            2,
        )

        self.assertEqual(
            album.release_date,
            "2026-08-10",
        )

    def test_album_summary_uses_first_artwork(
        self,
    ):
        album = (
            spotify_album_summary_from_payload(
                album_payload()
            )
        )

        self.assertEqual(
            album.image_url,
            "https://example.test/large.jpg",
        )

    def test_album_summary_rejects_mismatched_uri(
        self,
    ):
        payload = album_payload()

        payload[
            "uri"
        ] = "spotify:album:other"

        with self.assertRaises(
            SpotifyAlbumParseError
        ):
            spotify_album_summary_from_payload(
                payload
            )

    def test_track_maps_core_fields(
        self,
    ):
        track = (
            spotify_album_track_from_payload(
                track_payload()
            )
        )

        self.assertEqual(
            track.spotify_id,
            "track123",
        )

        self.assertEqual(
            track.artist_text,
            "Artist One, Artist Two",
        )

        self.assertEqual(
            track.duration_ms,
            185000,
        )

        self.assertEqual(
            track.track_number,
            1,
        )

        self.assertTrue(
            track.explicit
        )

        self.assertTrue(
            track.is_playable
        )

    def test_track_allows_missing_is_playable(
        self,
    ):
        payload = track_payload()

        payload.pop(
            "is_playable"
        )

        track = (
            spotify_album_track_from_payload(
                payload
            )
        )

        self.assertIsNone(
            track.is_playable
        )

    def test_track_rejects_mismatched_uri(
        self,
    ):
        payload = track_payload()

        payload[
            "uri"
        ] = "spotify:track:other"

        with self.assertRaises(
            SpotifyAlbumParseError
        ):
            spotify_album_track_from_payload(
                payload
            )

    def test_tracks_page_maps_pagination(
        self,
    ):
        page = (
            spotify_album_tracks_page_from_payload(
                {
                    "items": [
                        track_payload(),
                        track_payload(
                            spotify_id="track456",
                            track_number=2,
                        ),
                    ],
                    "limit": 2,
                    "offset": 0,
                    "total": 2,
                    "next": None,
                    "previous": None,
                }
            )
        )

        self.assertEqual(
            len(
                page.items
            ),
            2,
        )

        self.assertEqual(
            page.total,
            2,
        )

        self.assertTrue(
            page.complete
        )

    def test_tracks_page_rejects_non_list_items(
        self,
    ):
        with self.assertRaises(
            SpotifyAlbumParseError
        ):
            spotify_album_tracks_page_from_payload(
                {
                    "items": {},
                    "limit": 1,
                    "offset": 0,
                    "total": 1,
                }
            )

    def test_tracks_page_rejects_negative_total(
        self,
    ):
        with self.assertRaises(
            SpotifyAlbumParseError
        ):
            spotify_album_tracks_page_from_payload(
                {
                    "items": [],
                    "limit": 1,
                    "offset": 0,
                    "total": -1,
                }
            )

    def test_tracks_page_rejects_invalid_track(
        self,
    ):
        bad = track_payload()

        bad[
            "uri"
        ] = "spotify:track:wrong"

        with self.assertRaises(
            SpotifyAlbumParseError
        ):
            spotify_album_tracks_page_from_payload(
                {
                    "items": [
                        bad
                    ],
                    "limit": 1,
                    "offset": 0,
                    "total": 1,
                }
            )


if __name__ == "__main__":
    unittest.main()
