from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
)

from src.ui.spotify_page import (
    SpotifyPage,
)


def artist_item(
    *,
    uri=(
        "spotify:artist:"
        "artist123"
    ),
):
    return SpotifySearchItem(
        item_type=(
            SpotifySearchItemType.ARTIST
        ),
        spotify_id="artist123",
        name="Artist One",
        uri=uri,
        image_url=(
            "https://i.scdn.co/"
            "image/artist-one"
        ),
        subtitle="Artist",
    )


class SpotifySearchArtistNavigationTests(
    unittest.TestCase
):
    def test_trusted_artist_opens_detail_with_seed_data(
        self,
    ):
        seen = []

        def show_artist_detail(
            artist_id,
            *,
            seed_name="",
            seed_image_url="",
        ):
            seen.append(
                (
                    artist_id,
                    seed_name,
                    seed_image_url,
                )
            )

            return True

        host = SimpleNamespace(
            artist_detail=object(),
            show_artist_detail=(
                show_artist_detail
            ),
        )

        result = (
            SpotifyPage
            ._handle_search_artist_activated(
                host,
                artist_item(),
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            seen,
            [
                (
                    "artist123",
                    "Artist One",
                    (
                        "https://i.scdn.co/"
                        "image/artist-one"
                    ),
                )
            ],
        )

    def test_untrusted_artist_uri_is_rejected(
        self,
    ):
        seen = []

        host = SimpleNamespace(
            artist_detail=object(),
            show_artist_detail=(
                lambda *args, **kwargs:
                seen.append(
                    (
                        args,
                        kwargs,
                    )
                )
            ),
        )

        result = (
            SpotifyPage
            ._handle_search_artist_activated(
                host,
                artist_item(
                    uri=(
                        "spotify:artist:"
                        "different"
                    )
                ),
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            seen,
            [],
        )

    def test_non_artist_item_is_rejected(
        self,
    ):
        seen = []

        host = SimpleNamespace(
            artist_detail=object(),
            show_artist_detail=(
                lambda *args, **kwargs:
                seen.append(
                    (
                        args,
                        kwargs,
                    )
                )
            ),
        )

        track = SpotifySearchItem(
            item_type=(
                SpotifySearchItemType.TRACK
            ),
            spotify_id="track123",
            name="Track One",
            uri=(
                "spotify:track:"
                "track123"
            ),
            subtitle="Artist One",
        )

        result = (
            SpotifyPage
            ._handle_search_artist_activated(
                host,
                track,
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            seen,
            [],
        )

    def test_missing_artist_detail_is_safe(
        self,
    ):
        host = SimpleNamespace(
            show_artist_detail=(
                lambda *args, **kwargs:
                True
            )
        )

        result = (
            SpotifyPage
            ._handle_search_artist_activated(
                host,
                artist_item(),
            )
        )

        self.assertFalse(
            result
        )

    def test_detail_rejection_is_propagated(
        self,
    ):
        host = SimpleNamespace(
            artist_detail=object(),
            show_artist_detail=(
                lambda *args, **kwargs:
                False
            ),
        )

        result = (
            SpotifyPage
            ._handle_search_artist_activated(
                host,
                artist_item(),
            )
        )

        self.assertFalse(
            result
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
