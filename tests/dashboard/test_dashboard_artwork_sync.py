from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.music.song import Song
from src.ui.dashboard import DashboardPage
from src.ui.main_window import MainWindow


class DashboardArtworkRecoveryTests(
    unittest.TestCase
):
    def setUp(self):
        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        cache_directory = Path(
            self.temp_directory.name
        )

        self.page = SimpleNamespace(
            _last_artwork_signature=(
                "old-signature",
            ),
            _artwork_cache_directory=(
                lambda: cache_directory
            ),
            _artwork_identity=(
                DashboardPage._artwork_identity
            ),
        )

    def tearDown(self):
        self.temp_directory.cleanup()

    @staticmethod
    def make_song(
        *,
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        source_app="Spotify",
        artwork_bytes=None,
    ):
        return Song(
            title=title,
            artist=artist,
            album=album,
            duration="3:00",
            position="0:10",
            playing=True,
            artwork_bytes=artwork_bytes,
            source_app=source_app,
        )

    def cache_path_for(self, song):
        cache_key = (
            DashboardPage._artwork_identity(
                song.title,
                song.artist,
                song.album,
                song.source_app,
            )
        )

        return (
            self.page._artwork_cache_directory()
            / f"{cache_key}.img"
        )

    def restore(self, song):
        return (
            DashboardPage
            .restore_cached_song_artwork(
                self.page,
                song,
            )
        )

    def test_restores_matching_cached_artwork(
        self,
    ):
        song = self.make_song()

        self.cache_path_for(song).write_bytes(
            b"cached-artwork"
        )

        restored = self.restore(song)

        self.assertTrue(restored)

        self.assertEqual(
            song.artwork_bytes,
            b"cached-artwork",
        )

        self.assertIsNone(
            self.page._last_artwork_signature
        )

    def test_does_not_replace_fresh_artwork(
        self,
    ):
        song = self.make_song(
            artwork_bytes=b"fresh-artwork",
        )

        self.cache_path_for(song).write_bytes(
            b"older-cached-artwork"
        )

        restored = self.restore(song)

        self.assertFalse(restored)

        self.assertEqual(
            song.artwork_bytes,
            b"fresh-artwork",
        )

    def test_does_not_use_another_tracks_artwork(
        self,
    ):
        cached_song = self.make_song(
            title="First Song",
        )

        current_song = self.make_song(
            title="Second Song",
        )

        self.cache_path_for(
            cached_song
        ).write_bytes(
            b"first-song-artwork"
        )

        restored = self.restore(
            current_song
        )

        self.assertFalse(restored)

        self.assertFalse(
            current_song.artwork_bytes
        )

    def test_missing_cache_is_safe(self):
        song = self.make_song()

        restored = self.restore(song)

        self.assertFalse(restored)
        self.assertFalse(song.artwork_bytes)


class MainWindowArtworkOrderingTests(
    unittest.TestCase
):
    def test_restores_before_discord_update(
        self,
    ):
        events = []

        song = Song(
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            artwork_bytes=None,
            source_app="Spotify",
        )

        def restore(current_song):
            events.append("restore")

            current_song.artwork_bytes = (
                b"cached-artwork"
            )

            return True

        def publish(current_song):
            events.append(
                (
                    "discord",
                    current_song.artwork_bytes,
                )
            )

        def add_to_library(current_song):
            events.append(
                (
                    "library",
                    current_song.artwork_bytes,
                )
            )

        window = SimpleNamespace(
            dashboard_page=SimpleNamespace(
                restore_cached_song_artwork=restore
            ),
            presence_controller=SimpleNamespace(
                handle_song=publish
            ),
            library_page=SimpleNamespace(
                add_song=add_to_library
            ),
        )

        MainWindow.handle_song_update(
            window,
            song,
        )

        self.assertEqual(
            events,
            [
                "restore",
                (
                    "discord",
                    b"cached-artwork",
                ),
                (
                    "library",
                    b"cached-artwork",
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
