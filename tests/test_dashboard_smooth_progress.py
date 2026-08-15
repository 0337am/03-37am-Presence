from __future__ import annotations

import inspect
import unittest
from types import SimpleNamespace

import src.ui.dashboard as dashboard_module
from src.ui.dashboard import (
    DashboardPage,
)


class FakeLabel:
    def __init__(
        self,
    ):
        self.value = None
        self.hidden = False

    def setText(
        self,
        value,
    ):
        self.value = value

    def setHidden(
        self,
        hidden,
    ):
        self.hidden = bool(hidden)


class FakeProgress:
    def __init__(
        self,
    ):
        self.value = None

    def setValue(
        self,
        value,
    ):
        self.value = value


class FakePresentationClock:
    def __init__(
        self,
        state,
    ):
        self.state = state

    def current(
        self,
    ):
        return self.state


class FakeTimer:
    def __init__(
        self,
    ):
        self.stopped = False

    def stop(
        self,
    ):
        self.stopped = True


class DashboardSmoothProgressTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.module_source = (
            inspect.getsource(
                dashboard_module
            )
        )

        cls.constructor_source = (
            inspect.getsource(
                DashboardPage.__init__
            )
        )

        cls.apply_source = (
            inspect.getsource(
                DashboardPage.apply_song
            )
        )

        cls.refresh_source = (
            inspect.getsource(
                DashboardPage
                .refresh_playback_presentation
            )
        )

        cls.stop_source = (
            inspect.getsource(
                DashboardPage.stop_media_worker
            )
        )

    def test_dashboard_imports_presentation_clock(
        self,
    ):
        self.assertIn(
            (
                "PlaybackPresentationClock"
            ),
            self.module_source,
        )

        self.assertIn(
            (
                "format_playback_time"
            ),
            self.module_source,
        )

    def test_dashboard_constructs_presentation_timer(
        self,
    ):
        self.assertIn(
            (
                "self.playback_presentation_timer"
            ),
            self.constructor_source,
        )

        self.assertIn(
            (
                "self.refresh_playback_presentation"
            ),
            self.constructor_source,
        )

    def test_presentation_timer_uses_250ms_interval(
        self,
    ):
        self.assertIn(
            "250",
            self.constructor_source,
        )

    def test_apply_song_reanchors_presentation_clock(
        self,
    ):
        self.assertIn(
            (
                "self.playback_presentation_clock"
                ".observe("
            ),
            self.apply_source,
        )

        self.assertIn(
            "position_seconds=",
            self.apply_source,
        )

        self.assertIn(
            "duration_seconds=",
            self.apply_source,
        )

        self.assertIn(
            "identity=",
            self.apply_source,
        )

    def test_empty_song_clears_presentation_clock(
        self,
    ):
        empty_branch = (
            self.apply_source
            .split(
                "self._last_worker_error",
                1,
            )[0]
        )

        self.assertIn(
            (
                "self.playback_presentation_clock"
                ".clear()"
            ),
            empty_branch,
        )

    def test_progress_bar_uses_high_resolution_range(
        self,
    ):
        self.assertIn(
            (
                "self.progress.setRange("
            ),
            self.module_source,
        )

        self.assertIn(
            "10000",
            self.module_source,
        )

    def test_refresh_playback_presentation_updates_labels_and_progress(
        self,
    ):
        current_time = FakeLabel()
        preview_time = FakeLabel()
        progress = FakeProgress()

        state = SimpleNamespace(
            position_seconds=42.5,
            duration_seconds=100.0,
            playing=True,
        )

        fake = SimpleNamespace(
            playback_presentation_clock=(
                FakePresentationClock(
                    state
                )
            ),
            current_time=current_time,
            preview_time=preview_time,
            progress=progress,
            song=SimpleNamespace(
                playing=True,
                duration="1:40",
            ),
        )

        fake._discord_music_preview_active = lambda: True

        DashboardPage.refresh_playback_presentation(
            fake
        )

        self.assertEqual(
            current_time.value,
            "0:42",
        )

        self.assertEqual(
            preview_time.value,
            "0:42 / 1:40",
        )

        self.assertEqual(
            progress.value,
            4250,
        )

    def test_stop_media_worker_stops_presentation_timer(
        self,
    ):
        self.assertIn(
            (
                "playback_presentation_timer"
            ),
            self.stop_source,
        )

        self.assertIn(
            ".stop()",
            self.stop_source,
        )
