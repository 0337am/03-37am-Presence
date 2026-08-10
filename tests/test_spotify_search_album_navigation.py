import unittest

from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
)
from src.ui.spotify_page import (
    SpotifyPage,
)
from src.ui.spotify_search import (
    SpotifySearchPage,
)


class FakeSignal:
    def __init__(
        self,
    ):
        self.values = []

    def emit(
        self,
        value,
    ):
        self.values.append(
            value
        )


def album_item(
    *,
    uri="spotify:album:album123",
):
    return SpotifySearchItem(
        item_type=(
            SpotifySearchItemType.ALBUM
        ),
        spotify_id="album123",
        name="Example Album",
        uri=uri,
        subtitle="Artist One",
    )


class SpotifySearchAlbumNavigationTests(
    unittest.TestCase
):
    def test_search_page_emits_album_signal(
        self,
    ):
        target = type(
            "Target",
            (),
            {},
        )()

        target.track_activated = FakeSignal()
        target.playlist_activated = FakeSignal()
        target.album_activated = FakeSignal()

        item = album_item()

        SpotifySearchPage._handle_item_activated(
            target,
            item,
        )

        self.assertEqual(
            target.album_activated.values,
            [
                item
            ],
        )

        self.assertEqual(
            target.track_activated.values,
            [],
        )

        self.assertEqual(
            target.playlist_activated.values,
            [],
        )

    def test_spotify_page_accepts_trusted_album_uri(
        self,
    ):
        target = type(
            "Target",
            (),
            {},
        )()

        target.album_detail = object()

        seen = []

        target.show_album_detail = (
            lambda item:
            seen.append(
                item
            )
            or True
        )

        item = album_item()

        result = (
            SpotifyPage
            ._handle_search_album_activated(
                target,
                item,
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            seen,
            [
                item
            ],
        )

    def test_spotify_page_rejects_untrusted_album_uri(
        self,
    ):
        target = type(
            "Target",
            (),
            {},
        )()

        target.album_detail = object()

        target.show_album_detail = (
            lambda item:
            True
        )

        result = (
            SpotifyPage
            ._handle_search_album_activated(
                target,
                album_item(
                    uri=(
                        "spotify:album:wrong"
                    )
                ),
            )
        )

        self.assertFalse(
            result
        )

    def test_spotify_page_without_album_detail_is_safe(
        self,
    ):
        target = type(
            "Target",
            (),
            {},
        )()

        result = (
            SpotifyPage
            ._handle_search_album_activated(
                target,
                album_item(),
            )
        )

        self.assertFalse(
            result
        )


if __name__ == "__main__":
    unittest.main()
