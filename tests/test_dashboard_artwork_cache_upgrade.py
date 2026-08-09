from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.music.song import Song
from src.ui.dashboard import DashboardPage


class DashboardArtworkCacheUpgradeTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp.cleanup
        )

        self.cache_directory = Path(
            self.temp.name
        )

        self.page = SimpleNamespace(
            _artwork_cache_directory=(
                lambda: self.cache_directory
            ),
            _artwork_identity=(
                DashboardPage._artwork_identity
            ),
        )

        self.song = Song(
            title=(
                "Toxic Humans "
                "(Session Edit)"
            ),
            artist="Juice WRLD",
            album="Studio Sessions",
            source_app="Spotify.exe",
            artwork_bytes=None,
        )

    def cache_path(
        self,
    ):
        key = (
            DashboardPage._artwork_identity(
                self.song.title,
                self.song.artist,
                self.song.album,
                self.song.source_app,
            )
        )

        return (
            self.cache_directory
            / f"{key}.img"
        )

    def cache(
        self,
    ):
        DashboardPage.cache_song_artwork(
            self.page,
            self.song,
        )

    def test_bad_fallback_can_be_repaired_by_larger_artwork(
        self,
    ):
        fallback = b"f" * 7125
        real_artwork = b"r" * 100773

        self.cache_path().write_bytes(
            fallback
        )

        self.song.artwork_bytes = (
            real_artwork
        )

        self.cache()

        self.assertEqual(
            self.cache_path().read_bytes(),
            real_artwork,
        )

    def test_good_artwork_is_not_downgraded_by_small_fallback(
        self,
    ):
        real_artwork = b"r" * 100773
        fallback = b"f" * 7125

        self.cache_path().write_bytes(
            real_artwork
        )

        self.song.artwork_bytes = (
            fallback
        )

        self.cache()

        self.assertEqual(
            self.cache_path().read_bytes(),
            real_artwork,
        )

    def test_first_artwork_is_cached_normally(
        self,
    ):
        artwork = b"a" * 50000

        self.song.artwork_bytes = (
            artwork
        )

        self.cache()

        self.assertEqual(
            self.cache_path().read_bytes(),
            artwork,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
