from __future__ import annotations

import unittest
from pathlib import Path

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.liked_songs_service import (
    SpotifyLikedSongsServiceResult,
    SpotifyLikedSongsServiceStatus,
)
from src.ui.spotify_playlist_widgets import (
    SpotifyPlaylistHome,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeThemeManager(
    QObject
):
    theme_changed = pyqtSignal(
        dict
    )

    def theme(
        self,
    ):
        return {
            "background": "#101014",
            "card": "#18181f",
            "card_alt": "#202028",
            "border": "#34343e",
            "accent": "#ff4f91",
            "text": "#f4f4f6",
            "muted": "#a6a6b1",
        }


class FakePlaylistRuntime(
    QObject
):
    playlists_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
        str,
        str,
    )

    busy_changed = pyqtSignal(
        bool
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.calls = 0
        self.busy = False

    def load_playlists(
        self,
        *,
        limit=50,
        offset=0,
    ):
        self.calls += 1
        self.busy = True

        self.busy_changed.emit(
            True
        )

    def finish(
        self,
    ):
        self.busy = False

        self.busy_changed.emit(
            False
        )


class FakeLikedSongsRuntime(
    QObject
):
    summary_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
    )

    busy_changed = pyqtSignal(
        bool
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.calls = 0
        self.busy = False

    def load_summary(
        self,
    ):
        self.calls += 1
        self.busy = True

        self.busy_changed.emit(
            True
        )

    def finish(
        self,
    ):
        self.busy = False

        self.busy_changed.emit(
            False
        )


class SpotifyLikedSongsHomeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication(
                []
            )
        )

    def make_home(
        self,
    ):
        playlists = FakePlaylistRuntime()
        liked = FakeLikedSongsRuntime()

        home = SpotifyPlaylistHome(
            playlists,
            liked_songs_runtime=liked,
            theme_manager=FakeThemeManager(),
        )

        self.addCleanup(
            home.deleteLater
        )

        return home, playlists, liked

    def test_liked_songs_card_is_present(
        self,
    ):
        home, _playlists, _liked = (
            self.make_home()
        )

        self.assertFalse(
            home.liked_songs_card.isHidden()
        )

        self.assertEqual(
            home.liked_songs_title.text(),
            "Liked Songs",
        )

        self.assertEqual(
            home.liked_songs_count.text(),
            "Not loaded",
        )

    def test_construction_is_passive(
        self,
    ):
        _home, playlists, liked = (
            self.make_home()
        )

        self.assertEqual(
            playlists.calls,
            0,
        )

        self.assertEqual(
            liked.calls,
            0,
        )

    def test_initial_load_sequences_playlists_then_liked_songs(
        self,
    ):
        home, playlists, liked = (
            self.make_home()
        )

        self.assertTrue(
            home.ensure_loaded()
        )

        self.assertEqual(
            playlists.calls,
            1,
        )

        self.assertEqual(
            liked.calls,
            0,
        )

        playlists.finish()

        self.assertEqual(
            liked.calls,
            1,
        )

    def test_ready_result_displays_real_count(
        self,
    ):
        home, _playlists, liked = (
            self.make_home()
        )

        liked.summary_ready.emit(
            SpotifyLikedSongsServiceResult(
                status=(
                    SpotifyLikedSongsServiceStatus
                    .READY
                ),
                total=321,
            )
        )

        self.assertEqual(
            home.liked_songs_count.text(),
            "321 songs",
        )

    def test_single_song_uses_singular_word(
        self,
    ):
        home, _playlists, liked = (
            self.make_home()
        )

        liked.summary_ready.emit(
            SpotifyLikedSongsServiceResult(
                status=(
                    SpotifyLikedSongsServiceStatus
                    .READY
                ),
                total=1,
            )
        )

        self.assertEqual(
            home.liked_songs_count.text(),
            "1 song",
        )

    def test_non_ready_result_is_user_safe(
        self,
    ):
        home, _playlists, liked = (
            self.make_home()
        )

        liked.summary_ready.emit(
            SpotifyLikedSongsServiceResult(
                status=(
                    SpotifyLikedSongsServiceStatus
                    .DISCONNECTED
                ),
                message=(
                    "Connect Spotify before "
                    "loading Liked Songs."
                ),
            )
        )

        self.assertEqual(
            home.liked_songs_count.text(),
            "Unavailable",
        )

        self.assertIn(
            "Connect Spotify",
            home.liked_songs_status.text(),
        )

    def test_runtime_failure_is_user_safe(
        self,
    ):
        home, _playlists, liked = (
            self.make_home()
        )

        liked.failed.emit(
            "operation_failed",
            "Liked Songs could not be loaded.",
        )

        self.assertEqual(
            home.liked_songs_count.text(),
            "Unavailable",
        )

    def test_liked_runtime_busy_disables_refresh(
        self,
    ):
        home, _playlists, liked = (
            self.make_home()
        )

        liked.busy = True

        liked.busy_changed.emit(
            True
        )

        self.assertFalse(
            home.refresh_button.isEnabled()
        )

        liked.busy = False

        liked.busy_changed.emit(
            False
        )

        self.assertTrue(
            home.refresh_button.isEnabled()
        )

    def test_manual_refresh_sequences_both_sources(
        self,
    ):
        home, playlists, liked = (
            self.make_home()
        )

        self.assertTrue(
            home.refresh()
        )

        self.assertEqual(
            playlists.calls,
            1,
        )

        self.assertEqual(
            liked.calls,
            0,
        )

        playlists.finish()

        self.assertEqual(
            liked.calls,
            1,
        )

    def test_main_window_composes_liked_songs_runtime(
        self,
    ):
        source = (
            ROOT
            / "src"
            / "ui"
            / "main_window.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        for marker in (
            "SpotifyLikedSongsService",
            "SpotifyQtLikedSongsRuntime",
            "spotify_liked_songs_runtime",
        ):
            self.assertIn(
                marker,
                source,
            )

        self.assertIn(
            '"spotify_liked_songs_runtime"',
            source,
        )

    def test_spotify_page_passes_liked_runtime_to_home(
        self,
    ):
        source = (
            ROOT
            / "src"
            / "ui"
            / "spotify_page.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "liked_songs_runtime=None",
            source,
        )

        self.assertIn(
            "liked_songs_runtime=(",
            source,
        )
