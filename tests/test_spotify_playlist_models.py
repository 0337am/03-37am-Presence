from __future__ import annotations

import dataclasses
import unittest
from pathlib import Path

from src.media.unified_track import (
    UnifiedTrackSource,
)
from src.spotify.playlist_models import (
    SpotifyPlaylistItemsPage,
    SpotifyPlaylistPage,
    SpotifyPlaylistParseError,
    SpotifyPlaylistSummary,
    SpotifyPlaylistTrack,
    spotify_playlist_items_page_from_payload,
    spotify_playlist_page_from_payload,
)


def playlist_payload(
    *,
    current_items=True,
):
    data = {
        "id": "playlist123",
        "name": "Local Juice",
        "uri": (
            "spotify:playlist:playlist123"
        ),
        "owner": {
            "id": "owner1",
            "display_name": "Owner",
        },
        "description": "Test playlist",
        "public": False,
        "collaborative": False,
        "images": [
            {
                "url": (
                    "https://i.scdn.co/"
                    "playlist-image"
                ),
            },
        ],
    }

    if current_items:
        data[
            "items"
        ] = {
            "href": "https://api.spotify.com/x",
            "total": 86,
        }

    else:
        data[
            "tracks"
        ] = {
            "href": "https://api.spotify.com/x",
            "total": 86,
        }

    return data


def catalogue_track(
    *,
    name="Rental",
):
    return {
        "album": {
            "name": "Album",
            "images": [
                {
                    "url": (
                        "https://i.scdn.co/"
                        "album-image"
                    ),
                },
            ],
        },
        "artists": [
            {
                "name": "Juice WRLD",
            },
        ],
        "duration_ms": 240000,
        "id": "track123",
        "is_local": False,
        "is_playable": True,
        "name": name,
        "type": "track",
        "uri": (
            "spotify:track:track123"
        ),
    }


def local_track(
    *,
    name="Rental",
    uri=(
        "spotify:local:Juice%20WRLD:"
        "Unreleased:Rental:240"
    ),
):
    return {
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
        "name": name,
        "type": "track",
        "uri": uri,
    }


def items_page(
    entries,
):
    return {
        "href": "https://api.spotify.com/x",
        "limit": 50,
        "offset": 0,
        "total": len(
            entries
        ),
        "items": entries,
    }


class SpotifyPlaylistModelTests(
    unittest.TestCase
):
    def test_playlist_summary_uses_current_items_total(
        self,
    ):
        page = (
            spotify_playlist_page_from_payload(
                {
                    "limit": 50,
                    "offset": 0,
                    "total": 1,
                    "items": [
                        playlist_payload(),
                    ],
                }
            )
        )

        self.assertEqual(
            page.playlists[
                0
            ].total_items,
            86,
        )

    def test_playlist_summary_falls_back_to_deprecated_tracks_total(
        self,
    ):
        page = (
            spotify_playlist_page_from_payload(
                {
                    "limit": 50,
                    "offset": 0,
                    "total": 1,
                    "items": [
                        playlist_payload(
                            current_items=False
                        ),
                    ],
                }
            )
        )

        self.assertEqual(
            page.playlists[
                0
            ].total_items,
            86,
        )

    def test_playlist_summary_uses_first_valid_artwork(
        self,
    ):
        page = (
            spotify_playlist_page_from_payload(
                {
                    "limit": 50,
                    "offset": 0,
                    "total": 1,
                    "items": [
                        playlist_payload(),
                    ],
                }
            )
        )

        self.assertEqual(
            page.playlists[
                0
            ].artwork_reference,
            (
                "https://i.scdn.co/"
                "playlist-image"
            ),
        )

    def test_playlist_page_parses_current_response(
        self,
    ):
        page = (
            spotify_playlist_page_from_payload(
                {
                    "limit": 50,
                    "offset": 5,
                    "total": 7,
                    "items": [
                        playlist_payload(),
                    ],
                }
            )
        )

        self.assertIsInstance(
            page,
            SpotifyPlaylistPage,
        )

        self.assertEqual(
            page.limit,
            50,
        )

        self.assertEqual(
            page.offset,
            5,
        )

        self.assertEqual(
            page.total,
            7,
        )

    def test_local_item_becomes_reference(
        self,
    ):
        page = (
            spotify_playlist_items_page_from_payload(
                items_page(
                    [
                        {
                            "added_at": (
                                "2026-08-08T00:00:00Z"
                            ),
                            "is_local": True,
                            "item": local_track(),
                        },
                    ]
                )
            )
        )

        reference = (
            page.items[
                0
            ].track.to_local_reference()
        )

        self.assertEqual(
            reference.title,
            "Rental",
        )

        self.assertEqual(
            reference.artist,
            "Juice WRLD",
        )

        self.assertTrue(
            reference.spotify_local_uri.startswith(
                "spotify:local:"
            )
        )

    def test_item_field_is_preferred_over_legacy_track(
        self,
    ):
        page = (
            spotify_playlist_items_page_from_payload(
                items_page(
                    [
                        {
                            "is_local": False,
                            "item": catalogue_track(
                                name="Current"
                            ),
                            "track": catalogue_track(
                                name="Legacy"
                            ),
                        },
                    ]
                )
            )
        )

        self.assertEqual(
            page.items[
                0
            ].track.title,
            "Current",
        )

    def test_legacy_track_field_is_supported(
        self,
    ):
        page = (
            spotify_playlist_items_page_from_payload(
                items_page(
                    [
                        {
                            "is_local": False,
                            "track": catalogue_track(),
                        },
                    ]
                )
            )
        )

        self.assertEqual(
            page.items[
                0
            ].track.title,
            "Rental",
        )

    def test_item_positions_preserve_raw_playlist_index_when_entries_are_omitted(
        self,
    ):
        from unittest.mock import patch

        from src.spotify.playlist_models import (
            SpotifyPlaylistTrack,
        )

        track = SpotifyPlaylistTrack(
            title="Position Test",
            artist="Test Artist",
            album="Test Album",
            duration_ms=180000,
            spotify_id="track123",
            spotify_uri=(
                "spotify:track:track123"
            ),
            artwork_reference="",
            is_local=False,
            playable=True,
        )

        payload = items_page(
            [
                {
                    "is_local": False,
                    "added_at": (
                        "2026-08-08T00:00:00Z"
                    ),
                    "item": {
                        "type": "track",
                    },
                },
                {
                    "is_local": False,
                    "item": None,
                },
                {
                    "is_local": False,
                    "added_at": (
                        "2026-08-08T00:00:00Z"
                    ),
                    "item": {
                        "type": "track",
                    },
                },
            ]
        )

        payload["offset"] = 27

        with patch(
            (
                "src.spotify.playlist_models."
                "_track_from_payload"
            ),
            return_value=track,
        ):
            page = (
                spotify_playlist_items_page_from_payload(
                    payload
                )
            )

        self.assertEqual(
            page.omitted_items,
            1,
        )

        self.assertEqual(
            [
                item.position
                for item in page.items
            ],
            [
                27,
                29,
            ],
        )

    def test_playlist_item_position_rejects_invalid_values(
        self,
    ):
        from dataclasses import replace
        from unittest.mock import patch

        from src.spotify.playlist_models import (
            SpotifyPlaylistTrack,
        )

        track = SpotifyPlaylistTrack(
            title="Position Test",
            artist="Test Artist",
            album="Test Album",
            duration_ms=180000,
            spotify_id="track123",
            spotify_uri=(
                "spotify:track:track123"
            ),
            artwork_reference="",
            is_local=False,
            playable=True,
        )

        payload = items_page(
            [
                {
                    "is_local": False,
                    "added_at": (
                        "2026-08-08T00:00:00Z"
                    ),
                    "item": {
                        "type": "track",
                    },
                },
            ]
        )

        with patch(
            (
                "src.spotify.playlist_models."
                "_track_from_payload"
            ),
            return_value=track,
        ):
            page = (
                spotify_playlist_items_page_from_payload(
                    payload
                )
            )

        item = page.items[0]

        with self.assertRaises(
            ValueError
        ):
            replace(
                item,
                position=-1,
            )

        with self.assertRaises(
            TypeError
        ):
            replace(
                item,
                position=True,
            )

    def test_null_item_is_omitted(
        self,
    ):
        page = (
            spotify_playlist_items_page_from_payload(
                items_page(
                    [
                        {
                            "is_local": False,
                            "item": None,
                        },
                    ]
                )
            )
        )

        self.assertEqual(
            page.items,
            (),
        )

        self.assertEqual(
            page.omitted_items,
            1,
        )

    def test_non_track_item_is_omitted(
        self,
    ):
        page = (
            spotify_playlist_items_page_from_payload(
                items_page(
                    [
                        {
                            "is_local": False,
                            "item": {
                                "type": "episode",
                            },
                        },
                    ]
                )
            )
        )

        self.assertEqual(
            page.items,
            (),
        )

        self.assertEqual(
            page.omitted_items,
            1,
        )

    def test_catalogue_track_becomes_unified_track(
        self,
    ):
        page = (
            spotify_playlist_items_page_from_payload(
                items_page(
                    [
                        {
                            "is_local": False,
                            "item": catalogue_track(),
                        },
                    ]
                )
            )
        )

        unified = (
            page.items[
                0
            ].track.to_unified_track()
        )

        self.assertIs(
            unified.source,
            UnifiedTrackSource.SPOTIFY,
        )

        self.assertEqual(
            unified.spotify_id,
            "track123",
        )

    def test_local_track_requires_resolution_before_unified_track(
        self,
    ):
        page = (
            spotify_playlist_items_page_from_payload(
                items_page(
                    [
                        {
                            "is_local": True,
                            "item": local_track(),
                        },
                    ]
                )
            )
        )

        with self.assertRaises(
            ValueError
        ):
            page.items[
                0
            ].track.to_unified_track()

    def test_local_uri_marks_item_local(
        self,
    ):
        track = local_track()

        track[
            "is_local"
        ] = False

        page = (
            spotify_playlist_items_page_from_payload(
                items_page(
                    [
                        {
                            "is_local": False,
                            "item": track,
                        },
                    ]
                )
            )
        )

        self.assertTrue(
            page.items[
                0
            ].is_local
        )

    def test_invalid_local_uri_is_rejected(
        self,
    ):
        track = local_track(
            uri="spotify:track:wrong"
        )

        with self.assertRaises(
            ValueError
        ):
            spotify_playlist_items_page_from_payload(
                items_page(
                    [
                        {
                            "is_local": True,
                            "item": track,
                        },
                    ]
                )
            )

    def test_artist_names_are_joined(
        self,
    ):
        track = local_track()

        track[
            "artists"
        ] = [
            {
                "name": "Juice WRLD",
            },
            {
                "name": "Marshmello",
            },
        ]

        page = (
            spotify_playlist_items_page_from_payload(
                items_page(
                    [
                        {
                            "is_local": True,
                            "item": track,
                        },
                    ]
                )
            )
        )

        self.assertEqual(
            page.items[
                0
            ].track.artist,
            "Juice WRLD, Marshmello",
        )

    def test_missing_track_title_is_rejected(
        self,
    ):
        track = catalogue_track()

        track[
            "name"
        ] = ""

        with self.assertRaises(
            ValueError
        ):
            spotify_playlist_items_page_from_payload(
                items_page(
                    [
                        {
                            "is_local": False,
                            "item": track,
                        },
                    ]
                )
            )

    def test_page_rejects_invalid_counts(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyPlaylistItemsPage(
                items=(),
                limit=True,
                offset=0,
                total=0,
            )

    def test_models_are_frozen(
        self,
    ):
        summary = (
            SpotifyPlaylistSummary(
                spotify_id="playlist123",
                name="Test",
                spotify_uri=(
                    "spotify:playlist:playlist123"
                ),
            )
        )

        with self.assertRaises(
            dataclasses.FrozenInstanceError
        ):
            summary.name = "Changed"


class SpotifyPlaylistModelBoundaryTests(
    unittest.TestCase
):
    def test_models_own_no_network_qt_credentials_or_playback(
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
            / "playlist_models.py"
        ).read_text(
            encoding="utf-8"
        )

        for forbidden in (
            "PyQt",
            "QSettings",
            "SpotifyCredentialStore",
            "SpotifySessionManager",
            "SpotifyTokenClient",
            "access_token",
            "refresh_token",
            "urllib",
            "requests.",
            "LocalMusicIndex",
            "LocalTrackResolver",
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
