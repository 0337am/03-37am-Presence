from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import (
    QPoint,
    QTimer,
    Qt,
)
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication,
    QSlider,
)

from src.music.song import Song
from src.ui.dashboard import (
    DashboardPage,
    PlaybackSeekSlider,
)


REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


class DashboardPlaybackSeekTests(
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

        self.page.refresh_dashboard_data = (
            lambda: None
        )

    def tearDown(
        self,
    ):
        self.page.stop_media_worker()

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
        duration="3:38",
        position="0:37",
        playing=True,
        source_app="Spotify.exe",
    ):
        return Song(
            title="Example Track",
            artist="Example Artist",
            album="Example Album",
            duration=duration,
            position=position,
            playing=playing,
            source_app=source_app,
        )

    def test_now_playing_progress_is_seek_slider(
        self,
    ):
        self.assertIsInstance(
            self.page.progress,
            PlaybackSeekSlider,
        )

        self.assertIsInstance(
            self.page.progress,
            QSlider,
        )

        self.assertEqual(
            self.page.progress.orientation(),
            Qt.Orientation.Horizontal,
        )

        self.assertEqual(
            self.page.progress.minimum(),
            0,
        )

        self.assertEqual(
            self.page.progress.maximum(),
            10000,
        )

        self.assertFalse(
            self.page.progress.isEnabled()
        )

    def test_seek_slider_has_accessible_metadata(
        self,
    ):
        self.assertEqual(
            self.page.progress.accessibleName(),
            "Playback position",
        )

        self.assertIn(
            "seek",
            self.page.progress
            .accessibleDescription()
            .casefold(),
        )

        self.assertEqual(
            self.page.progress.focusPolicy(),
            Qt.FocusPolicy.StrongFocus,
        )

    def test_known_duration_enables_scrubbing(
        self,
    ):
        self.page.apply_song(
            self.song()
        )

        self.assertTrue(
            self.page.progress.isEnabled()
        )

    def test_unknown_duration_keeps_scrubbing_disabled(
        self,
    ):
        self.page.apply_song(
            self.song(
                duration="0:00"
            )
        )

        self.assertFalse(
            self.page.progress.isEnabled()
        )

    def test_scrub_preview_updates_current_timestamp(
        self,
    ):
        self.page.apply_song(
            self.song()
        )

        self.page.progress.setValue(
            5000
        )

        self.page._begin_playback_scrub()

        self.assertTrue(
            self.page._playback_scrubbing
        )

        self.assertEqual(
            self.page.current_time.text(),
            "1:49",
        )

    def test_smooth_refresh_does_not_fight_active_scrub(
        self,
    ):
        self.page.apply_song(
            self.song()
        )

        self.page.progress.setValue(
            8000
        )

        self.page._begin_playback_scrub()

        before_value = (
            self.page.progress.value()
        )

        before_text = (
            self.page.current_time.text()
        )

        self.page.refresh_playback_presentation()

        self.assertEqual(
            self.page.progress.value(),
            before_value,
        )

        self.assertEqual(
            self.page.current_time.text(),
            before_text,
        )

    def test_authoritative_update_progress_yields_during_scrub(
        self,
    ):
        self.page.apply_song(
            self.song()
        )

        self.page.progress.setValue(
            7500
        )

        self.page._begin_playback_scrub()

        before_value = (
            self.page.progress.value()
        )

        self.page.update_progress(
            self.song(
                position="0:05"
            )
        )

        self.assertEqual(
            self.page.progress.value(),
            before_value,
        )

    def test_commit_emits_target_seconds_and_source_without_mutating_song(
        self,
    ):
        song = self.song()

        self.page.apply_song(
            song
        )

        emitted = []

        self.page.playback_seek_requested.connect(
            lambda seconds, source:
            emitted.append(
                (
                    seconds,
                    source,
                )
            )
        )

        original_position = (
            song.position
        )

        self.page.progress.setValue(
            5000
        )

        self.page._begin_playback_scrub()

        self.page._commit_playback_scrub(
            5000
        )

        self.assertFalse(
            self.page._playback_scrubbing
        )

        self.assertEqual(
            len(
                emitted
            ),
            1,
        )

        self.assertAlmostEqual(
            emitted[0][0],
            109.0,
            places=3,
        )

        self.assertEqual(
            emitted[0][1],
            "Spotify.exe",
        )

        self.assertEqual(
            song.position,
            original_position,
        )

    def test_pointer_mapping_clamps_across_entire_timeline(
        self,
    ):
        slider = (
            self.page.progress
        )

        slider.setFixedWidth(
            201
        )

        self.assertEqual(
            slider._value_from_pointer(
                -100
            ),
            0,
        )

        self.assertEqual(
            slider._value_from_pointer(
                100
            ),
            5000,
        )

        self.assertEqual(
            slider._value_from_pointer(
                500
            ),
            10000,
        )

    def test_mouse_drag_commits_seek(
        self,
    ):
        self.page.apply_song(
            self.song()
        )

        self.page.show()

        slider = (
            self.page.progress
        )

        slider.setFixedWidth(
            401
        )

        self.app.processEvents()

        emitted = []

        self.page.playback_seek_requested.connect(
            lambda seconds, source:
            emitted.append(
                (
                    seconds,
                    source,
                )
            )
        )

        QTest.mousePress(
            slider,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(
                40,
                max(
                    1,
                    slider.height()
                    // 2,
                ),
            ),
        )

        QTest.mouseMove(
            slider,
            QPoint(
                320,
                max(
                    1,
                    slider.height()
                    // 2,
                ),
            ),
        )

        QTest.mouseRelease(
            slider,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(
                320,
                max(
                    1,
                    slider.height()
                    // 2,
                ),
            ),
        )

        self.app.processEvents()

        self.assertEqual(
            len(
                emitted
            ),
            1,
        )

        self.assertAlmostEqual(
            emitted[0][0],
            174.4,
            delta=2.0,
        )

        self.assertEqual(
            emitted[0][1],
            "Spotify.exe",
        )

    def test_main_window_wires_dashboard_seek_to_coordinator(
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
                "playback_seek_requested"
                ".connect("
            ),
            source,
        )

        self.assertIn(
            (
                "playback_control_coordinator"
                ".request_seek"
            ),
            source,
        )


    def test_pending_seek_holds_target_across_stale_snapshot(
        self,
    ):
        self.page.apply_song(
            self.song(
                position="0:37"
            )
        )

        self.page.progress.setValue(
            5000
        )
        self.page._begin_playback_scrub()
        self.page._commit_playback_scrub(
            5000
        )

        self.assertTrue(
            self.page._playback_seek_pending
        )
        self.assertEqual(
            self.page.current_time.text(),
            "1:49",
        )

        self.page.apply_song(
            self.song(
                position="0:38"
            )
        )

        self.assertTrue(
            self.page._playback_seek_pending
        )
        self.assertEqual(
            self.page.progress.value(),
            5000,
        )
        self.assertEqual(
            self.page.current_time.text(),
            "1:49",
        )

    def test_authoritative_seek_snapshot_releases_pending_hold(
        self,
    ):
        self.page.apply_song(
            self.song(
                position="0:37"
            )
        )

        self.page.progress.setValue(
            5000
        )
        self.page._begin_playback_scrub()
        self.page._commit_playback_scrub(
            5000
        )

        self.assertTrue(
            self.page._playback_seek_pending
        )

        self.page.apply_song(
            self.song(
                position="1:50"
            )
        )

        self.assertFalse(
            self.page._playback_seek_pending
        )
        self.assertEqual(
            self.page.current_time.text(),
            "1:50",
        )
        self.assertGreater(
            self.page.progress.value(),
            4900,
        )

    def test_pending_seek_timeout_releases_hold(
        self,
    ):
        self.page.apply_song(
            self.song()
        )

        self.page.progress.setValue(
            6000
        )
        self.page._begin_playback_scrub()
        self.page._commit_playback_scrub(
            6000
        )

        self.assertTrue(
            self.page._playback_seek_pending
        )
        self.assertTrue(
            self.page
            ._playback_seek_pending_timer
            .isActive()
        )

        self.page._expire_playback_seek_pending()

        self.assertFalse(
            self.page._playback_seek_pending
        )
        self.assertFalse(
            self.page
            ._playback_seek_pending_timer
            .isActive()
        )
        self.assertIsNone(
            self.page._playback_seek_target_seconds
        )

    def test_new_scrub_cancels_previous_pending_hold(
        self,
    ):
        self.page.apply_song(
            self.song()
        )

        self.page.progress.setValue(
            5000
        )
        self.page._begin_playback_scrub()
        self.page._commit_playback_scrub(
            5000
        )

        self.assertTrue(
            self.page._playback_seek_pending
        )

        self.page.progress.setValue(
            7000
        )
        self.page._begin_playback_scrub()

        self.assertFalse(
            self.page._playback_seek_pending
        )
        self.assertTrue(
            self.page._playback_scrubbing
        )

    def test_rapid_new_seek_replaces_pending_target_and_restarts_timer(
        self,
    ):
        self.page.apply_song(
            self.song()
        )

        self.page.progress.setValue(
            4000
        )
        self.page._begin_playback_scrub()
        self.page._commit_playback_scrub(
            4000
        )

        first_target = (
            self.page._playback_seek_target_seconds
        )

        self.assertTrue(
            self.page
            ._playback_seek_pending_timer
            .isActive()
        )

        self.page.progress.setValue(
            7500
        )
        self.page._begin_playback_scrub()
        self.page._commit_playback_scrub(
            7500
        )

        second_target = (
            self.page._playback_seek_target_seconds
        )

        self.assertNotEqual(
            first_target,
            second_target,
        )
        self.assertTrue(
            self.page._playback_seek_pending
        )
        self.assertTrue(
            self.page
            ._playback_seek_pending_timer
            .isActive()
        )

    def test_track_change_cancels_pending_seek_hold(
        self,
    ):
        self.page.apply_song(
            self.song()
        )

        self.page.progress.setValue(
            5000
        )
        self.page._begin_playback_scrub()
        self.page._commit_playback_scrub(
            5000
        )

        self.assertTrue(
            self.page._playback_seek_pending
        )

        different_song = Song(
            title="Different Track",
            artist="Example Artist",
            album="Example Album",
            duration="3:38",
            position="0:04",
            playing=True,
            source_app="Spotify.exe",
        )

        self.page.apply_song(
            different_song
        )

        self.assertFalse(
            self.page._playback_seek_pending
        )
        self.assertEqual(
            self.page.current_time.text(),
            "0:04",
        )

    def test_pointer_mapping_uses_handle_center_travel_span(
        self,
    ):
        slider = self.page.progress

        slider.setFixedWidth(
            201
        )

        self.assertEqual(
            slider._value_from_pointer(
                4
            ),
            0,
        )
        self.assertEqual(
            slider._value_from_pointer(
                100
            ),
            5000,
        )
        self.assertEqual(
            slider._value_from_pointer(
                196
            ),
            10000,
        )

    def test_seek_polish_removes_link_cursor_tooltip_and_uses_subtle_theme(
        self,
    ):
        self.assertNotEqual(
            self.page.progress.cursor().shape(),
            Qt.CursorShape.PointingHandCursor,
        )

        self.assertEqual(
            self.page.progress.toolTip(),
            "",
        )

        source = (
            REPO_ROOT
            / "src"
            / "ui"
            / "dashboard.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "PLAYBACK_SEEK_HANDLE_WIDTH_PX = 8",
            source,
        )

        self.assertIn(
            "QFrame#playbackProgressVisual {{",
            source,
        )

        self.assertIn(
            'background: {theme["background"]};',
            source,
        )

        self.assertIn(
            "QFrame#playbackProgressPlayed {{",
            source,
        )

        self.assertIn(
            'background: {theme["accent"]};',
            source,
        )

        self.assertIn(
            "self.progress_visual.setFixedHeight(",
            source,
        )

        self.assertIn(
            "            4",
            source,
        )

        slider_class_start = source.index(
            "class PlaybackSeekSlider("
        )

        slider_class_end = source.index(
            "class DashboardPage(",
            slider_class_start,
        )

        slider_source = source[
            slider_class_start:
            slider_class_end
        ]

        self.assertIn(
            "def paintEvent(",
            slider_source,
        )

        self.assertIn(
            "event.accept()",
            slider_source,
        )

        self.assertNotIn(
            "super().paintEvent(",
            slider_source,
        )

        self.assertNotIn(
            "QSlider#playbackProgress",
            source,
        )

        self.assertNotIn(
            "self.progress.setToolTip(",
            source,
        )


    def test_seek_progress_visual_mirrors_slider_value(
        self,
    ):
        self.page.progress.setValue(
            4321
        )

        self.assertEqual(
            self.page.progress_visual.value(),
            4321,
        )

        visual_layout = (
            self.page
            .progress_visual
            .layout()
        )

        self.assertEqual(
            visual_layout.stretch(
                0
            ),
            4321,
        )

        self.assertEqual(
            visual_layout.stretch(
                1
            ),
            5679,
        )

    def test_seek_uses_original_progress_visual_under_input_overlay(
        self,
    ):
        self.assertEqual(
            self.page.progress_visual.objectName(),
            "playbackProgressVisual",
        )

        self.assertEqual(
            self.page.progress_stack.objectName(),
            "playbackProgressStack",
        )

        self.assertEqual(
            self.page.progress_stack.layout().count(),
            2,
        )

        source = (
            REPO_ROOT
            / "src"
            / "ui"
            / "dashboard.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "self.progress_visual = PlaybackProgressVisual()",
            source,
        )

        self.assertIn(
            "class PlaybackProgressVisual(",
            source,
        )

        self.assertIn(
            "self.progress_visual.setFixedHeight(",
            source,
        )

        self.assertIn(
            "self.progress.valueChanged.connect(",
            source,
        )

        self.assertIn(
            "self.progress_visual.setValue",
            source,
        )

        self.assertNotIn(
            "def set_seek_colors(",
            source,
        )

if __name__ == "__main__":
    unittest.main()
