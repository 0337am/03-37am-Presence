from __future__ import annotations

import math
import statistics
import unittest
from pathlib import Path

from src.media.audio_spectrum import (
    DEFAULT_ADAPTIVE_HEADROOM_DB,
    DEFAULT_ADAPTIVE_RANGE_DB,
    MAX_ANALYSIS_SAMPLES,
    SPECTRUM_BAND_FREQUENCIES,
    SPECTRUM_BAND_GAIN_DB,
    SPECTRUM_BAND_RANGES,
    SpectrumAnalyzer,
    spectrum_levels_to_text,
)
from tests.repo_paths import REPO_ROOT


SAMPLE_RATE = 44100
SAMPLE_COUNT = 1024


def sine_wave(
    frequency,
    *,
    amplitude=0.5,
    sample_rate=SAMPLE_RATE,
    sample_count=SAMPLE_COUNT,
):
    return tuple(
        amplitude
        * math.sin(
            (
                2.0
                * math.pi
                * float(
                    frequency
                )
                * index
            )
            / float(
                sample_rate
            )
        )
        for index in range(
            sample_count
        )
    )


def mixed_wave(
    components,
    *,
    scale=1.0,
    sample_rate=SAMPLE_RATE,
    sample_count=SAMPLE_COUNT,
):
    return tuple(
        float(
            scale
        )
        * sum(
            float(
                amplitude
            )
            * math.sin(
                (
                    2.0
                    * math.pi
                    * float(
                        frequency
                    )
                    * index
                )
                / float(
                    sample_rate
                )
            )
            for frequency, amplitude in components
        )
        for index in range(
            sample_count
        )
    )


ROCK_COMPONENTS = (
    (65.0, 0.18),
    (135.0, 0.16),
    (260.0, 0.14),
    (520.0, 0.12),
    (1050.0, 0.10),
    (2100.0, 0.08),
    (4200.0, 0.07),
    (8000.0, 0.05),
)


class SpectrumAnalyzerTests(
    unittest.TestCase
):
    def analyzer(
        self,
        **kwargs,
    ):
        return SpectrumAnalyzer(
            attack=kwargs.pop(
                "attack",
                1.0,
            ),
            release=kwargs.pop(
                "release",
                1.0,
            ),
            **kwargs,
        )

    def settle(
        self,
        analyzer,
        samples,
        *,
        frames=40,
    ):
        levels = None

        for _ in range(
            frames
        ):
            levels = analyzer.analyze(
                samples,
                SAMPLE_RATE,
            )

        return levels

    def test_exactly_eight_frequency_bands(
        self,
    ):
        self.assertEqual(
            SPECTRUM_BAND_FREQUENCIES,
            (
                63,
                125,
                250,
                500,
                1000,
                2000,
                4000,
                8000,
            ),
        )

        self.assertEqual(
            len(
                SPECTRUM_BAND_RANGES
            ),
            8,
        )

    def test_band_ranges_cover_expected_spectrum_without_gaps(
        self,
    ):
        self.assertEqual(
            SPECTRUM_BAND_RANGES[0],
            (40.0, 90.0),
        )

        self.assertEqual(
            SPECTRUM_BAND_RANGES[-1],
            (5600.0, 11000.0),
        )

        for left, right in zip(
            SPECTRUM_BAND_RANGES,
            SPECTRUM_BAND_RANGES[1:],
        ):
            self.assertEqual(
                left[1],
                right[0],
            )

    def test_band_compensation_is_gentle_and_monotonic(
        self,
    ):
        self.assertEqual(
            len(
                SPECTRUM_BAND_GAIN_DB
            ),
            8,
        )

        self.assertLessEqual(
            max(
                SPECTRUM_BAND_GAIN_DB
            ),
            4.0,
        )

        self.assertEqual(
            tuple(
                sorted(
                    SPECTRUM_BAND_GAIN_DB
                )
            ),
            SPECTRUM_BAND_GAIN_DB,
        )

    def test_adaptive_defaults_leave_real_headroom(
        self,
    ):
        self.assertEqual(
            DEFAULT_ADAPTIVE_HEADROOM_DB,
            7.0,
        )

        self.assertEqual(
            DEFAULT_ADAPTIVE_RANGE_DB,
            42.0,
        )

    def test_silence_stays_zero(
        self,
    ):
        analyzer = self.analyzer()

        levels = analyzer.analyze(
            (0.0,) * SAMPLE_COUNT,
            SAMPLE_RATE,
        )

        self.assertEqual(
            levels,
            (0.0,) * 8,
        )

    def test_low_frequency_targets_first_band(
        self,
    ):
        analyzer = self.analyzer()

        levels = self.settle(
            analyzer,
            sine_wave(
                63.0
            ),
        )

        self.assertEqual(
            max(
                range(8),
                key=levels.__getitem__,
            ),
            0,
        )

        self.assertGreater(
            levels[0],
            0.5,
        )

    def test_mid_frequency_targets_expected_band(
        self,
    ):
        analyzer = self.analyzer()

        levels = self.settle(
            analyzer,
            sine_wave(
                1000.0
            ),
        )

        self.assertEqual(
            max(
                range(8),
                key=levels.__getitem__,
            ),
            4,
        )

        self.assertGreater(
            levels[4],
            0.5,
        )

    def test_high_frequency_targets_last_band(
        self,
    ):
        analyzer = self.analyzer()

        levels = self.settle(
            analyzer,
            sine_wave(
                8000.0
            ),
        )

        self.assertEqual(
            max(
                range(8),
                key=levels.__getitem__,
            ),
            7,
        )

        self.assertGreater(
            levels[7],
            0.5,
        )

    def test_high_frequency_between_old_probe_points_is_not_missed(
        self,
    ):
        analyzer = self.analyzer()

        levels = self.settle(
            analyzer,
            sine_wave(
                6500.0
            ),
        )

        self.assertEqual(
            max(
                range(8),
                key=levels.__getitem__,
            ),
            7,
        )

        self.assertGreater(
            levels[7],
            0.5,
        )

    def test_upper_treble_near_ten_khz_is_not_missed(
        self,
    ):
        analyzer = self.analyzer()

        levels = self.settle(
            analyzer,
            sine_wave(
                10000.0
            ),
        )

        self.assertEqual(
            max(
                range(8),
                key=levels.__getitem__,
            ),
            7,
        )

        self.assertGreater(
            levels[7],
            0.5,
        )

    def test_rock_like_mix_keeps_right_half_visibly_alive(
        self,
    ):
        analyzer = self.analyzer()

        levels = self.settle(
            analyzer,
            mixed_wave(
                ROCK_COMPONENTS
            ),
        )

        left_average = statistics.mean(
            levels[:4]
        )

        right_average = statistics.mean(
            levels[4:]
        )

        self.assertGreater(
            right_average,
            0.45,
        )

        self.assertGreater(
            right_average,
            left_average * 0.55,
        )

    def test_hot_mix_does_not_pin_all_eight_bands(
        self,
    ):
        analyzer = self.analyzer()

        levels = self.settle(
            analyzer,
            mixed_wave(
                ROCK_COMPONENTS,
                scale=3.0,
            ),
            frames=60,
        )

        full_scale_bands = sum(
            1
            for value in levels
            if value >= 0.985
        )

        self.assertLess(
            full_scale_bands,
            4,
        )

        self.assertLess(
            statistics.mean(
                levels
            ),
            0.95,
        )

    def test_adaptive_reference_rises_for_hot_audio(
        self,
    ):
        analyzer = self.analyzer()

        initial = (
            analyzer.adaptive_reference_db
        )

        self.settle(
            analyzer,
            mixed_wave(
                ROCK_COMPONENTS,
                scale=3.0,
            ),
            frames=20,
        )

        self.assertGreater(
            analyzer.adaptive_reference_db,
            initial,
        )

    def test_adaptive_reference_never_falls_below_normal_baseline(
        self,
    ):
        analyzer = self.analyzer()

        quiet_samples = mixed_wave(
            ROCK_COMPONENTS,
            scale=0.03,
        )

        self.settle(
            analyzer,
            quiet_samples,
            frames=200,
        )

        self.assertGreaterEqual(
            analyzer.adaptive_reference_db,
            analyzer.reference_db,
        )

        self.assertAlmostEqual(
            analyzer.adaptive_reference_db,
            analyzer.reference_db,
            places=6,
        )

    def test_calm_mix_remains_visibly_quieter_than_hot_mix(
        self,
    ):
        calm = self.analyzer()
        hot = self.analyzer()

        calm_levels = self.settle(
            calm,
            mixed_wave(
                ROCK_COMPONENTS,
                scale=0.15,
            ),
            frames=80,
        )

        hot_levels = self.settle(
            hot,
            mixed_wave(
                ROCK_COMPONENTS,
                scale=3.0,
            ),
            frames=80,
        )

        calm_mean = statistics.mean(
            calm_levels
        )

        hot_mean = statistics.mean(
            hot_levels
        )

        self.assertGreater(
            calm_mean,
            0.20,
        )

        self.assertLess(
            calm_mean,
            hot_mean - 0.12,
        )

    def test_adaptive_reference_falls_slowly_after_quieter_audio(
        self,
    ):
        analyzer = self.analyzer()

        self.settle(
            analyzer,
            mixed_wave(
                ROCK_COMPONENTS,
                scale=3.0,
            ),
            frames=30,
        )

        hot_reference = (
            analyzer.adaptive_reference_db
        )

        analyzer.analyze(
            mixed_wave(
                ROCK_COMPONENTS,
                scale=0.15,
            ),
            SAMPLE_RATE,
        )

        quiet_reference = (
            analyzer.adaptive_reference_db
        )

        self.assertLess(
            quiet_reference,
            hot_reference,
        )

        self.assertGreater(
            quiet_reference,
            hot_reference - 2.0,
        )

    def test_volume_change_preserves_similar_visual_shape_after_settling(
        self,
    ):
        normal = self.analyzer()
        hot = self.analyzer()

        normal_levels = self.settle(
            normal,
            mixed_wave(
                ROCK_COMPONENTS,
                scale=0.5,
            ),
            frames=80,
        )

        hot_levels = self.settle(
            hot,
            mixed_wave(
                ROCK_COMPONENTS,
                scale=3.0,
            ),
            frames=80,
        )

        normal_peak = max(
            normal_levels
        )

        hot_peak = max(
            hot_levels
        )

        self.assertLess(
            abs(
                hot_peak
                - normal_peak
            ),
            0.20,
        )

        normal_shape = tuple(
            value
            / normal_peak
            for value in normal_levels
        )

        hot_shape = tuple(
            value
            / hot_peak
            for value in hot_levels
        )

        average_shape_difference = (
            statistics.mean(
                abs(
                    left - right
                )
                for left, right in zip(
                    normal_shape,
                    hot_shape,
                )
            )
        )

        self.assertLess(
            average_shape_difference,
            0.12,
        )

    def test_quiet_section_remains_visibly_quieter_immediately_after_hot_section(
        self,
    ):
        analyzer = self.analyzer()

        hot_levels = self.settle(
            analyzer,
            mixed_wave(
                ROCK_COMPONENTS,
                scale=3.0,
            ),
            frames=40,
        )

        quiet_levels = analyzer.analyze(
            mixed_wave(
                ROCK_COMPONENTS,
                scale=0.10,
            ),
            SAMPLE_RATE,
        )

        self.assertLess(
            statistics.mean(
                quiet_levels
            ),
            statistics.mean(
                hot_levels
            ),
        )

    def test_levels_are_always_bounded(
        self,
    ):
        analyzer = self.analyzer()

        levels = self.settle(
            analyzer,
            sine_wave(
                1000.0,
                amplitude=50.0,
            ),
        )

        self.assertTrue(
            all(
                0.0 <= value <= 1.0
                for value in levels
            )
        )

    def test_release_decays_instead_of_dropping_immediately(
        self,
    ):
        analyzer = SpectrumAnalyzer(
            attack=1.0,
            release=0.25,
        )

        loud = self.settle(
            analyzer,
            sine_wave(
                1000.0
            ),
            frames=20,
        )

        quiet = analyzer.analyze(
            (0.0,) * SAMPLE_COUNT,
            SAMPLE_RATE,
        )

        self.assertGreater(
            loud[4],
            quiet[4],
        )

        self.assertGreater(
            quiet[4],
            0.0,
        )

    def test_reset_clears_levels_and_adaptive_reference(
        self,
    ):
        analyzer = SpectrumAnalyzer(
            attack=1.0,
            release=0.25,
        )

        initial_reference = (
            analyzer.adaptive_reference_db
        )

        self.settle(
            analyzer,
            mixed_wave(
                ROCK_COMPONENTS,
                scale=3.0,
            ),
            frames=20,
        )

        analyzer.reset()

        self.assertEqual(
            analyzer.levels,
            (0.0,) * 8,
        )

        self.assertEqual(
            analyzer.adaptive_reference_db,
            initial_reference,
        )

    def test_short_buffer_is_safe_silence(
        self,
    ):
        analyzer = self.analyzer()

        levels = analyzer.analyze(
            (
                0.1,
                0.2,
                0.1,
                -0.1,
            ),
            SAMPLE_RATE,
        )

        self.assertEqual(
            levels,
            (0.0,) * 8,
        )

    def test_sample_rate_validation(
        self,
    ):
        analyzer = self.analyzer()

        invalid_values = (
            0,
            -1,
            float("nan"),
            float("inf"),
            True,
            None,
        )

        for value in invalid_values:
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    ValueError
                ):
                    analyzer.analyze(
                        (0.0,) * SAMPLE_COUNT,
                        value,
                    )

    def test_non_finite_samples_are_rejected(
        self,
    ):
        analyzer = self.analyzer()

        for invalid in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            samples = [0.0] * SAMPLE_COUNT
            samples[100] = invalid

            with self.subTest(
                invalid=invalid
            ):
                with self.assertRaises(
                    ValueError
                ):
                    analyzer.analyze(
                        samples,
                        SAMPLE_RATE,
                    )

    def test_analysis_window_is_bounded_to_1024_samples(
        self,
    ):
        self.assertEqual(
            MAX_ANALYSIS_SAMPLES,
            1024,
        )

        analyzer = self.analyzer()

        levels = analyzer.analyze(
            sine_wave(
                1000.0,
                sample_count=4096,
            ),
            SAMPLE_RATE,
        )

        self.assertEqual(
            len(levels),
            8,
        )

    def test_renderer_maps_minimum_levels(
        self,
    ):
        self.assertEqual(
            spectrum_levels_to_text(
                (0.0,) * 8
            ),
            "▁▁▁▁▁▁▁▁",
        )

    def test_renderer_maps_maximum_levels(
        self,
    ):
        self.assertEqual(
            spectrum_levels_to_text(
                (1.0,) * 8
            ),
            "████████",
        )

    def test_renderer_requires_eight_levels(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            spectrum_levels_to_text(
                (
                    0.0,
                    0.0,
                )
            )

    def test_source_has_no_capture_qt_network_or_heavy_math_dependency(
        self,
    ):
        path = (
            REPO_ROOT
            / "src"
            / "media"
            / "audio_spectrum.py"
        )

        source = path.read_text(
            encoding="utf-8"
        )

        forbidden = (
            "PyQt6",
            "comtypes",
            "winsdk",
            "numpy",
            "scipy",
            "requests",
            "urllib",
            "QMediaPlayer",
            "SetForegroundWindow",
            "SendInput",
            "os.startfile",
        )

        for token in forbidden:
            with self.subTest(
                token=token
            ):
                self.assertNotIn(
                    token,
                    source,
                )


if __name__ == "__main__":
    unittest.main()