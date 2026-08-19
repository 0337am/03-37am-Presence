import unittest

from src.music.playback_cycle_detector import (
    PlaybackCycleDetector,
)


TRACK_A = "track-a"
TRACK_B = "track-b"


class PlaybackCycleDetectorTests(unittest.TestCase):
    def setUp(self):
        self.detector = PlaybackCycleDetector()

    def observe(
        self,
        *,
        identity=TRACK_A,
        position=0.0,
        duration=200.0,
        playing=True,
        repeat_track=None,
        explicit_seek=False,
    ):
        return self.detector.observe(
            identity=identity,
            position_seconds=position,
            duration_seconds=duration,
            playing=playing,
            repeat_track=repeat_track,
            explicit_seek=explicit_seek,
        )

    def test_initial_observation_starts_cycle_zero(self):
        result = self.observe(
            position=20.0
        )

        self.assertFalse(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )
        self.assertTrue(
            result.identity_changed
        )

    def test_continuous_playback_does_not_increment(self):
        self.observe(
            position=20.0
        )

        result = self.observe(
            position=21.0
        )

        self.assertFalse(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )

    def test_repeat_wrap_increments_once(self):
        self.observe(
            position=199.0,
            repeat_track=True,
        )

        result = self.observe(
            position=0.4,
            repeat_track=True,
        )

        self.assertTrue(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            1,
        )

    def test_second_repeat_wrap_increments_again(self):
        self.observe(
            position=199.0,
            repeat_track=True,
        )

        self.observe(
            position=0.4,
            repeat_track=True,
        )

        self.observe(
            position=199.2,
            repeat_track=True,
        )

        result = self.observe(
            position=0.3,
            repeat_track=True,
        )

        self.assertTrue(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            2,
        )

    def test_track_change_resets_cycle(self):
        self.observe(
            position=199.0,
            repeat_track=True,
        )

        self.observe(
            position=0.2,
            repeat_track=True,
        )

        result = self.observe(
            identity=TRACK_B,
            position=10.0,
            repeat_track=True,
        )

        self.assertFalse(
            result.replayed
        )
        self.assertTrue(
            result.identity_changed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )

    def test_backward_seek_mid_track_does_not_increment(self):
        self.observe(
            position=120.0
        )

        result = self.observe(
            position=30.0
        )

        self.assertFalse(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )

    def test_seek_from_end_to_start_can_be_suppressed(self):
        self.observe(
            position=199.0,
            repeat_track=True,
        )

        result = self.observe(
            position=0.5,
            repeat_track=True,
            explicit_seek=True,
        )

        self.assertFalse(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )

    def test_repeat_false_suppresses_end_to_start_wrap(self):
        self.observe(
            position=199.0,
            repeat_track=False,
        )

        result = self.observe(
            position=0.5,
            repeat_track=False,
        )

        self.assertFalse(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )

    def test_repeat_unknown_allows_conservative_wrap(self):
        self.observe(
            position=199.0,
            repeat_track=None,
        )

        result = self.observe(
            position=0.5,
            repeat_track=None,
        )

        self.assertTrue(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            1,
        )

    def test_paused_current_sample_does_not_increment(self):
        self.observe(
            position=199.0,
            repeat_track=True,
        )

        result = self.observe(
            position=0.5,
            playing=False,
            repeat_track=True,
        )

        self.assertFalse(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )

    def test_previous_paused_sample_does_not_increment(self):
        self.observe(
            position=199.0,
            playing=False,
            repeat_track=True,
        )

        result = self.observe(
            position=0.5,
            playing=True,
            repeat_track=True,
        )

        self.assertFalse(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )

    def test_invalid_duration_does_not_increment(self):
        self.observe(
            position=199.0,
            duration=None,
            repeat_track=True,
        )

        result = self.observe(
            position=0.5,
            duration=None,
            repeat_track=True,
        )

        self.assertFalse(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )

    def test_negative_position_does_not_increment(self):
        self.observe(
            position=199.0,
            repeat_track=True,
        )

        result = self.observe(
            position=-1.0,
            repeat_track=True,
        )

        self.assertFalse(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )

    def test_small_backward_jitter_near_end_does_not_increment(self):
        self.observe(
            position=199.2,
            repeat_track=True,
        )

        result = self.observe(
            position=198.7,
            repeat_track=True,
        )

        self.assertFalse(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )

    def test_clear_resets_state(self):
        self.observe(
            position=199.0,
            repeat_track=True,
        )

        self.observe(
            position=0.2,
            repeat_track=True,
        )

        self.detector.clear()

        self.assertEqual(
            self.detector.cycle_index,
            0,
        )

        self.assertIsNone(
            self.detector.identity
        )

        result = self.observe(
            position=40.0
        )

        self.assertFalse(
            result.replayed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )

    def test_none_identity_resets_state(self):
        self.observe(
            position=199.0,
            repeat_track=True,
        )

        self.observe(
            position=0.2,
            repeat_track=True,
        )

        result = self.observe(
            identity=None,
            position=0.0,
            playing=False,
        )

        self.assertFalse(
            result.replayed
        )
        self.assertTrue(
            result.identity_changed
        )
        self.assertEqual(
            result.cycle_index,
            0,
        )
        self.assertIsNone(
            self.detector.identity
        )


if __name__ == "__main__":
    unittest.main()