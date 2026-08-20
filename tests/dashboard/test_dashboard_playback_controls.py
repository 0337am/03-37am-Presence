from __future__ import annotations

import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import (
    QTimer,
    Qt,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.music.song import Song
from src.ui.dashboard import DashboardPage
from pathlib import Path

REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


class DashboardPlaybackControlTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def setUp(
        self,
    ):
        original_start_media_worker = (
            DashboardPage.start_media_worker
        )

        original_refresh_dashboard_data = (
            DashboardPage.refresh_dashboard_data
        )

        DashboardPage.start_media_worker = (
            lambda self: None
        )

        DashboardPage.refresh_dashboard_data = (
            lambda self: None
        )

        try:
            self.page = (
                DashboardPage()
            )

        finally:
            DashboardPage.start_media_worker = (
                original_start_media_worker
            )

            DashboardPage.refresh_dashboard_data = (
                original_refresh_dashboard_data
            )

        self.page.restore_cached_song_artwork = (
            lambda song: None
        )

        self.page.cache_song_artwork = (
            lambda song: None
        )

        self.page.update_artwork = (
            lambda song: None
        )

        self.page.update_progress = (
            lambda song: None
        )

        self.page.refresh_playback_presentation = (
            lambda: None
        )

        self.page.refresh_dashboard_data = (
            lambda: None
        )

    def tearDown(
        self,
    ):
        for timer in self.page.findChildren(
            QTimer
        ):
            timer.stop()

        self.page.close()
        self.page.deleteLater()

        self.app.processEvents()

    @staticmethod
    def song(
        *,
        playing=True,
        source_app="Spotify.exe",
    ):
        return Song(
            title="Example Track",
            artist="Example Artist",
            album="Example Album",
            duration="3:37",
            position="0:37",
            playing=playing,
            source_app=source_app,
        )

    def test_transport_buttons_exist_and_start_disabled(
        self,
    ):
        for button in (
            self.page.playback_previous_button,
            self.page.playback_play_pause_button,
            self.page.playback_next_button,
        ):
            self.assertFalse(
                button.isEnabled()
            )

    def test_playing_song_enables_controls_and_shows_pause(
        self,
    ):
        self.page.apply_song(
            self.song(
                playing=True
            )
        )

        self.assertTrue(
            self.page
            .playback_previous_button
            .isEnabled()
        )

        self.assertTrue(
            self.page
            .playback_play_pause_button
            .isEnabled()
        )

        self.assertTrue(
            self.page
            .playback_next_button
            .isEnabled()
        )

        self.assertEqual(
            self.page
            .playback_play_pause_button
            .toolTip(),
            "Pause",
        )

    def test_paused_song_shows_play(
        self,
    ):
        self.page.apply_song(
            self.song(
                playing=False
            )
        )

        self.assertEqual(
            self.page
            .playback_play_pause_button
            .toolTip(),
            "Play",
        )

    def test_buttons_emit_current_source_and_playing_truth(
        self,
    ):
        self.page.apply_song(
            self.song(
                playing=True,
                source_app="Spotify.exe",
            )
        )

        seen = []

        self.page.playback_control_requested.connect(
            lambda action, source, playing:
            seen.append(
                (
                    action,
                    source,
                    playing,
                )
            )
        )

        self.page.playback_previous_button.click()
        self.page.playback_play_pause_button.click()
        self.page.playback_next_button.click()

        self.assertEqual(
            seen,
            [
                (
                    "previous",
                    "Spotify.exe",
                    True,
                ),
                (
                    "toggle_play_pause",
                    "Spotify.exe",
                    True,
                ),
                (
                    "next",
                    "Spotify.exe",
                    True,
                ),
            ],
        )

    def test_click_does_not_optimistically_mutate_song_truth(
        self,
    ):
        song = self.song(
            playing=True
        )

        self.page.apply_song(
            song
        )

        self.page.playback_play_pause_button.click()

        self.assertTrue(
            song.playing
        )

        self.assertTrue(
            self.page.song.playing
        )

    def test_nothing_playing_disables_controls(
        self,
    ):
        self.page.apply_song(
            self.song()
        )

        self.page.show_nothing_playing()

        for button in (
            self.page.playback_previous_button,
            self.page.playback_play_pause_button,
            self.page.playback_next_button,
        ):
            self.assertFalse(
                button.isEnabled()
            )

    def test_transport_buttons_have_accessible_metadata(
        self,
    ):
        expected = {
            self.page.playback_previous_button: (
                "Previous track"
            ),
            self.page.playback_play_pause_button: (
                "Play"
            ),
            self.page.playback_next_button: (
                "Next track"
            ),
        }

        for (
            button,
            expected_name,
        ) in expected.items():
            self.assertEqual(
                button.accessibleName(),
                expected_name,
            )

            self.assertTrue(
                button.accessibleDescription()
            )

            self.assertEqual(
                button.statusTip(),
                button.accessibleDescription(),
            )

            self.assertEqual(
                button.focusPolicy(),
                Qt.FocusPolicy.StrongFocus,
            )

    def test_main_window_owns_transport_coordinator(
        self,
    ):
        source = (
            REPO_ROOT
            / "src"
            / "ui"
            / "main_window.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            (
                "from src.music."
                "playback_control_coordinator import"
            ),
            source,
        )

        self.assertIn(
            (
                "self.playback_control_coordinator "
                "="
            ),
            source,
        )

        self.assertIn(
            "PlaybackControlCoordinator(",
            source,
        )

        self.assertIn(
            "playback_control_requested.connect(",
            source,
        )

        self.assertIn(
            "shutdown_playback_controls",
            source,
        )


if __name__ == "__main__":
    unittest.main()
