import unittest

from src.music.playback_cycle_detector import (
    PlaybackCycleDetector,
)


TRACK = "lost-in-my-head"


class PlaybackCycleDetectorLiveSamplingTests(
    unittest.TestCase
):
    def setUp(self):
        self.detector = PlaybackCycleDetector()

    def observe(
        self,
        *,
        position,
        duration=167.0,
        playing=True,
        repeat_track=None,
        explicit_seek=False,
    ):
        return self.detector.observe(
            identity=TRACK,
            position_seconds=position,
            duration_seconds=duration,
            playing=playing,
            repeat_track=repeat_track,
            explicit_seek=explicit_seek,
        )

    def test_trusted_repeat_one_accepts_243_to_zero_sampling_gap(
        self,
    ):
        self.observe(
            position=163.0,
            repeat_track=True,
        )

        result = self.observe(
            position=0.0,
            repeat_track=True,
        )

        self.assertTrue(result.replayed)
        self.assertEqual(result.cycle_index, 1)

    def test_trusted_repeat_one_accepts_242_to_zero_sampling_gap(
        self,
    ):
        self.observe(
            position=162.0,
            repeat_track=True,
        )

        result = self.observe(
            position=0.0,
            repeat_track=True,
        )

        self.assertTrue(result.replayed)
        self.assertEqual(result.cycle_index, 1)

    def test_unknown_repeat_keeps_conservative_end_window(
        self,
    ):
        self.observe(
            position=163.0,
            repeat_track=None,
        )

        result = self.observe(
            position=0.0,
            repeat_track=None,
        )

        self.assertFalse(result.replayed)
        self.assertEqual(result.cycle_index, 0)

    def test_repeat_true_requires_previous_repeat_trust(
        self,
    ):
        self.observe(
            position=163.0,
            repeat_track=None,
        )

        result = self.observe(
            position=0.0,
            repeat_track=True,
        )

        self.assertFalse(result.replayed)
        self.assertEqual(result.cycle_index, 0)

    def test_trusted_repeat_rejects_mid_track_backward_jump(
        self,
    ):
        self.observe(
            position=150.0,
            repeat_track=True,
        )

        result = self.observe(
            position=0.0,
            repeat_track=True,
        )

        self.assertFalse(result.replayed)
        self.assertEqual(result.cycle_index, 0)

    def test_explicit_seek_suppresses_widened_repeat_window(
        self,
    ):
        self.observe(
            position=163.0,
            repeat_track=True,
        )

        result = self.observe(
            position=0.0,
            repeat_track=True,
            explicit_seek=True,
        )

        self.assertFalse(result.replayed)
        self.assertEqual(result.cycle_index, 0)


if __name__ == "__main__":
    unittest.main()
