from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from src.media.local_artwork import (
    SPOTIFY_ARTWORK_CACHE_SOURCE_APPS,
    artwork_cache_identity,
    read_local_artwork,
    read_local_cached_artwork,
)


class _FakeImages:
    any = None


class _FakeTag:
    def __init__(
        self,
        *,
        title="",
        artist="",
        album="",
        albumartist="",
    ):
        self.images = _FakeImages()
        self.title = title
        self.artist = artist
        self.album = album
        self.albumartist = albumartist


class LocalArtworkCacheFallbackTests(
    unittest.TestCase
):
    def make_file(
        self,
        name="track.mp3",
    ) -> Path:
        directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            directory.cleanup
        )

        path = (
            Path(
                directory.name
            )
            / name
        )

        path.write_bytes(
            b"audio"
        )

        return path.resolve()

    def make_cache(
        self,
    ) -> Path:
        directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            directory.cleanup
        )

        return Path(
            directory.name
        )

    def write_cache(
        self,
        directory,
        *,
        title,
        artist,
        album,
        source_app="spotify.exe",
        data=b"cached-cover",
    ):
        key = artwork_cache_identity(
            title,
            artist,
            album,
            source_app,
        )

        (
            directory
            / f"{key}.img"
        ).write_bytes(
            data
        )

    def test_identity_matches_dashboard_algorithm(
        self,
    ):
        expected = hashlib.sha256(
            (
                "cellophane"
                "|wesghost"
                "|cellophane"
                "|spotify.exe"
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        actual = artwork_cache_identity(
            " CELLOPHANE ",
            " WesGhost ",
            " CELLOPHANE ",
            " Spotify.exe ",
        )

        self.assertEqual(
            actual,
            expected,
        )

    def test_cache_is_used_after_missing_embedded_art(
        self,
    ):
        path = self.make_file()
        cache = self.make_cache()

        self.write_cache(
            cache,
            title="CELLOPHANE",
            artist="WesGhost",
            album="CELLOPHANE",
            data=b"wes-cover",
        )

        calls = []

        def reader(
            filename,
            **kwargs,
        ):
            calls.append(
                kwargs
            )

            return _FakeTag(
                title="CELLOPHANE",
                artist="WesGhost",
                album="CELLOPHANE",
            )

        result = read_local_artwork(
            path,
            tag_reader=reader,
            cache_directory=cache,
        )

        self.assertEqual(
            result,
            b"wes-cover",
        )

        self.assertEqual(
            calls,
            [
                {
                    "tags": False,
                    "duration": False,
                    "image": True,
                },
                {
                    "tags": True,
                    "duration": False,
                    "image": False,
                },
            ],
        )

    def test_wrong_identity_does_not_use_cache(
        self,
    ):
        path = self.make_file()
        cache = self.make_cache()

        self.write_cache(
            cache,
            title="Different",
            artist="WesGhost",
            album="Different",
        )

        result = read_local_cached_artwork(
            path,
            cache_directory=cache,
            tag_reader=(
                lambda *args, **kwargs:
                    _FakeTag(
                        title="ETERNITY",
                        artist="WesGhost",
                        album="ETERNITY",
                    )
            ),
        )

        self.assertIsNone(
            result
        )

    def test_albumartist_is_artist_fallback(
        self,
    ):
        path = self.make_file()
        cache = self.make_cache()

        self.write_cache(
            cache,
            title="HEROES",
            artist="WesGhost",
            album="HEROES",
            data=b"heroes-cover",
        )

        result = read_local_cached_artwork(
            path,
            cache_directory=cache,
            tag_reader=(
                lambda *args, **kwargs:
                    _FakeTag(
                        title="HEROES",
                        artist="",
                        album="HEROES",
                        albumartist="WesGhost",
                    )
            ),
        )

        self.assertEqual(
            result,
            b"heroes-cover",
        )

    def test_oversized_cache_entry_is_rejected(
        self,
    ):
        path = self.make_file()
        cache = self.make_cache()

        self.write_cache(
            cache,
            title="MIGRAINE",
            artist="WesGhost",
            album="MIGRAINE",
            data=b"12345",
        )

        result = read_local_cached_artwork(
            path,
            cache_directory=cache,
            max_bytes=4,
            tag_reader=(
                lambda *args, **kwargs:
                    _FakeTag(
                        title="MIGRAINE",
                        artist="WesGhost",
                        album="MIGRAINE",
                    )
            ),
        )

        self.assertIsNone(
            result
        )

    def test_source_app_set_stays_small_and_exact(
        self,
    ):
        self.assertEqual(
            SPOTIFY_ARTWORK_CACHE_SOURCE_APPS[
                0
            ],
            "spotify.exe",
        )

        self.assertLessEqual(
            len(
                SPOTIFY_ARTWORK_CACHE_SOURCE_APPS
            ),
            3,
        )


if __name__ == "__main__":
    unittest.main()
