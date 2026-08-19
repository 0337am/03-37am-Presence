from __future__ import annotations

import unittest

from src.ui.playback_presentation_clock import (
    PlaybackPresentationClock,
    format_playback_time,
)


IDENTITY = (
    "Track",
    "Artist",
    "Album",
    "spotify.exe",
)


class FakeClock:
    def __init__(
        self,
        value=100.0,
    ):
        self.value = float(
            value
        )

    def __call__(
        self,
    ):
        return self.value

    def advance(
        self,
        seconds,
    ):
        self.value += float(
            seconds
        )


class PlaybackPresentationClockTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        self.time = FakeClock()

        self.clock = (
            PlaybackPresentationClock(
                clock=self.time
            )
        )

    def observe(
        self,
        position,
        *,
        duration=180.0,
        playing=True,
        identity=IDENTITY,
    ):
        self.clock.observe(
            position_seconds=position,
            duration_seconds=duration,
            playing=playing,
            identity=identity,
        )

    def test_initial_clock_is_inactive(
        self,
    ):
        self.assertFalse(
            self.clock.active
        )

        self.assertIsNone(
            self.clock.current()
        )

    def test_first_playing_snapshot_anchors_position(
        self,
    ):
        self.observe(
            13.0
        )

        state = self.clock.current()

        self.assertAlmostEqual(
            state.position_seconds,
            13.0,
        )

        self.assertTrue(
            state.playing
        )

    def test_playing_position_advances_with_monotonic_clock(
        self,
    ):
        self.observe(
            13.0
        )

        self.time.advance(
            1.25
        )

        state = self.clock.current()

        self.assertAlmostEqual(
            state.position_seconds,
            14.25,
        )

    def test_duplicate_authoritative_snapshot_does_not_rewind(
        self,
    ):
        self.observe(
            13.0
        )

        self.time.advance(
            1.0
        )

        self.observe(
            13.0
        )

        self.time.advance(
            0.5
        )

        state = self.clock.current()

        self.assertGreaterEqual(
            state.position_seconds,
            14.4,
        )

    def test_stale_advancing_snapshot_does_not_rewind(
        self,
    ):
        self.observe(
            13.0
        )

        self.time.advance(
            2.0
        )

        self.observe(
            14.0
        )

        state = self.clock.current()

        self.assertGreaterEqual(
            state.position_seconds,
            15.0,
        )

    def test_forward_seek_reanchors(
        self,
    ):
        self.observe(
            10.0
        )

        self.time.advance(
            1.0
        )

        self.observe(
            40.0
        )

        state = self.clock.current()

        self.assertAlmostEqual(
            state.position_seconds,
            40.0,
        )

    def test_backward_seek_reanchors(
        self,
    ):
        self.observe(
            40.0
        )

        self.time.advance(
            1.0
        )

        self.observe(
            10.0
        )

        state = self.clock.current()

        self.assertAlmostEqual(
            state.position_seconds,
            10.0,
        )

    def test_track_change_reanchors(
        self,
    ):
        self.observe(
            50.0
        )

        self.time.advance(
            1.0
        )

        self.observe(
            2.0,
            identity=(
                "Different",
                "Artist",
                "Album",
                "spotify.exe",
            ),
        )

        state = self.clock.current()

        self.assertAlmostEqual(
            state.position_seconds,
            2.0,
        )

    def test_pause_freezes_at_authoritative_position(
        self,
    ):
        self.observe(
            20.0
        )

        self.time.advance(
            1.0
        )

        self.observe(
            21.0,
            playing=False,
        )

        self.time.advance(
            4.0
        )

        state = self.clock.current()

        self.assertAlmostEqual(
            state.position_seconds,
            21.0,
        )

        self.assertFalse(
            state.playing
        )

    def test_resume_reanchors_and_advances(
        self,
    ):
        self.observe(
            21.0,
            playing=False,
        )

        self.time.advance(
            3.0
        )

        self.observe(
            21.0,
            playing=True,
        )

        self.time.advance(
            1.0
        )

        state = self.clock.current()

        self.assertAlmostEqual(
            state.position_seconds,
            22.0,
        )

    def test_position_clamps_to_duration(
        self,
    ):
        self.observe(
            9.5,
            duration=10.0,
        )

        self.time.advance(
            5.0
        )

        state = self.clock.current()

        self.assertAlmostEqual(
            state.position_seconds,
            10.0,
        )

    def test_extrapolation_is_bounded_when_snapshots_stop(
        self,
    ):
        self.observe(
            30.0,
            duration=300.0,
        )

        self.time.advance(
            20.0
        )

        state = self.clock.current()

        self.assertAlmostEqual(
            state.position_seconds,
            35.0,
        )

    def test_clear_returns_clock_to_inactive_state(
        self,
    ):
        self.observe(
            10.0
        )

        self.clock.clear()

        self.assertFalse(
            self.clock.active
        )

        self.assertIsNone(
            self.clock.current()
        )

    def test_invalid_clock_dependency_rejected(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            PlaybackPresentationClock(
                clock=None
            )

    def test_invalid_numeric_values_rejected(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            self.clock.observe(
                position_seconds=True,
                duration_seconds=100,
                playing=True,
                identity=IDENTITY,
            )

        with self.assertRaises(
            ValueError
        ):
            self.clock.observe(
                position_seconds=float(
                    "nan"
                ),
                duration_seconds=100,
                playing=True,
                identity=IDENTITY,
            )

    def test_format_playback_time(
        self,
    ):
        self.assertEqual(
            format_playback_time(
                0
            ),
            "0:00",
        )

        self.assertEqual(
            format_playback_time(
                65.9
            ),
            "1:05",
        )

        self.assertEqual(
            format_playback_time(
                3661.9
            ),
            "1:01:01",
        )
