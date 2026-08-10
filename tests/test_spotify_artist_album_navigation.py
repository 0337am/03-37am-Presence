import inspect
import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from src.spotify.album_models import (
    SpotifyAlbumSummary,
)
from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
)
from src.ui.spotify_page import (
    SPOTIFY_ARTIST_DETAIL_INDEX,
    SPOTIFY_SEARCH_INDEX,
    SpotifyPage,
)


def album_summary():
    return SpotifyAlbumSummary(
        spotify_id="album123",
        name="Example Album",
        uri="spotify:album:album123",
        artists=(
            "Artist One",
        ),
        total_tracks=12,
        album_type="album",
        spotify_url=(
            "https://open.spotify.com/"
            "album/album123"
        ),
        image_url=(
            "https://i.scdn.co/"
            "image/album123"
        ),
        release_date="2026-08-10",
        release_date_precision="day",
    )


def album_item():
    return SpotifySearchItem(
        item_type=(
            SpotifySearchItemType.ALBUM
        ),
        spotify_id="album123",
        name="Example Album",
        uri="spotify:album:album123",
        spotify_url=(
            "https://open.spotify.com/"
            "album/album123"
        ),
        image_url=(
            "https://i.scdn.co/"
            "image/album123"
        ),
        subtitle="Artist One",
    )


class FakeContentStack:
    def __init__(
        self,
        index,
    ):
        self.index = index

    def currentIndex(
        self,
    ):
        return self.index


class FakeAlbumDetail:
    def __init__(
        self,
        *,
        accepts=True,
        loads=True,
    ):
        self.accepts = accepts
        self.loads = loads
        self.items = []

    def set_search_item(
        self,
        item,
    ):
        self.items.append(
            item
        )

        return self.accepts

    def load(
        self,
    ):
        return self.loads


class SpotifyArtistAlbumNavigationTests(
    unittest.TestCase
):
    def test_artist_album_activation_is_wired(
        self,
    ):
        source = inspect.getsource(
            SpotifyPage.connect_signals
        )

        self.assertIn(
            (
                "artist_detail."
                "album_activated.connect"
            ),
            source,
        )

        self.assertIn(
            (
                "self."
                "_handle_artist_album_activated"
            ),
            source,
        )

    def test_trusted_artist_album_opens_existing_album_detail(
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

        album = album_summary()

        result = (
            SpotifyPage
            ._handle_artist_album_activated(
                target,
                album,
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            len(
                seen
            ),
            1,
        )

        item = seen[
            0
        ]

        self.assertIsInstance(
            item,
            SpotifySearchItem,
        )

        self.assertIs(
            item.item_type,
            SpotifySearchItemType.ALBUM,
        )

        self.assertEqual(
            item.spotify_id,
            album.spotify_id,
        )

        self.assertEqual(
            item.name,
            album.name,
        )

        self.assertEqual(
            item.uri,
            album.uri,
        )

        self.assertEqual(
            item.spotify_url,
            album.spotify_url,
        )

        self.assertEqual(
            item.image_url,
            album.image_url,
        )

        self.assertEqual(
            item.subtitle,
            album.artist_text,
        )

    def test_non_album_summary_is_rejected(
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

        self.assertFalse(
            SpotifyPage
            ._handle_artist_album_activated(
                target,
                object(),
            )
        )

    def test_untrusted_album_uri_is_rejected(
        self,
    ):
        target = type(
            "Target",
            (),
            {},
        )()

        target.album_detail = object()

        called = []

        target.show_album_detail = (
            lambda item:
            called.append(
                item
            )
            or True
        )

        album = album_summary()

        object.__setattr__(
            album,
            "uri",
            "spotify:album:wrong",
        )

        self.assertFalse(
            SpotifyPage
            ._handle_artist_album_activated(
                target,
                album,
            )
        )

        self.assertEqual(
            called,
            [],
        )

    def test_missing_album_detail_is_safe(
        self,
    ):
        target = type(
            "Target",
            (),
            {},
        )()

        target.show_album_detail = (
            lambda item:
            True
        )

        self.assertFalse(
            SpotifyPage
            ._handle_artist_album_activated(
                target,
                album_summary(),
            )
        )

    def test_album_detail_rejection_is_propagated(
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
            False
        )

        self.assertFalse(
            SpotifyPage
            ._handle_artist_album_activated(
                target,
                album_summary(),
            )
        )

    def test_show_album_detail_records_artist_origin(
        self,
    ):
        target = type(
            "Target",
            (),
            {},
        )()

        target.album_detail = (
            FakeAlbumDetail()
        )

        target.content_stack = (
            FakeContentStack(
                SPOTIFY_ARTIST_DETAIL_INDEX
            )
        )

        target._album_detail_return_index = (
            SPOTIFY_SEARCH_INDEX
        )

        sections = []

        target._set_section = (
            sections.append
        )

        result = (
            SpotifyPage.show_album_detail(
                target,
                album_item(),
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            target._album_detail_return_index,
            SPOTIFY_ARTIST_DETAIL_INDEX,
        )

        self.assertEqual(
            sections,
            [
                4
            ],
        )

        self.assertEqual(
            target.album_detail.items,
            [
                album_item()
            ],
        )

    def test_album_back_returns_to_same_artist_section(
        self,
    ):
        target = type(
            "Target",
            (),
            {},
        )()

        target._album_detail_return_index = (
            SPOTIFY_ARTIST_DETAIL_INDEX
        )

        sections = []
        fallback_calls = []

        target._set_section = (
            sections.append
        )

        target.show_search = (
            lambda:
            fallback_calls.append(
                "search"
            )
        )

        target.show_home = (
            lambda:
            fallback_calls.append(
                "home"
            )
        )

        SpotifyPage._show_album_detail_return_section(
            target
        )

        self.assertEqual(
            sections,
            [
                SPOTIFY_ARTIST_DETAIL_INDEX
            ],
        )

        self.assertEqual(
            fallback_calls,
            [],
        )


if __name__ == "__main__":
    unittest.main()
