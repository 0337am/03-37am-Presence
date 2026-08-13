from __future__ import annotations

import unittest
from pathlib import Path

from src.ui.dashboard import DashboardPage


class _FakeTimer:
    def __init__(self):
        self.active = False
        self.start_calls = 0
        self.stop_calls = 0

    def isActive(self):
        return self.active

    def start(self):
        self.active = True
        self.start_calls += 1

    def stop(self):
        self.active = False
        self.stop_calls += 1


class _FakeLabel:
    def __init__(self):
        self.text = ""
        self.visible = False

    def setText(self, text):
        self.text = str(text)

    def setVisible(self, visible):
        self.visible = bool(visible)

    def clear(self):
        self.text = ""


class _FakeSpectrumService:
    def __init__(self, levels=None):
        self.latest_levels = (
            tuple(levels)
            if levels is not None
            else (0.0,) * 8
        )

        self.start_calls = 0
        self.stop_calls = []
        self.shutdown_calls = []

    def start(self):
        self.start_calls += 1
        return True

    def stop(self, timeout_seconds=0.0):
        self.stop_calls.append(
            float(timeout_seconds)
        )
        return True

    def shutdown(self, timeout_seconds=0.0):
        self.shutdown_calls.append(
            float(timeout_seconds)
        )
        return True


class _FakeSong:
    def __init__(self, source_app):
        self.source_app = source_app


class _FakeWorker:
    def __init__(self, running=False):
        self.running = running
        self.stop_calls = 0
        self.wait_calls = []

    def isRunning(self):
        return self.running

    def stop(self):
        self.stop_calls += 1

    def wait(self, timeout):
        self.wait_calls.append(timeout)
        return True


class _FakeDashboard:
    def __init__(
        self,
        source_app="Spotify.exe",
        levels=None,
    ):
        self.song = _FakeSong(
            source_app
        )

        self.equalizer = _FakeLabel()
        self.equalizer_timer = _FakeTimer()

        self.spotify_audio_spectrum_service = (
            _FakeSpectrumService(
                levels=levels
            )
        )

        self.dashboard_timer = _FakeTimer()
        self.playback_presentation_timer = _FakeTimer()
        self.media_worker = None

    def stop_equalizer_animation(self):
        return DashboardPage.stop_equalizer_animation(
            self
        )

    def advance_equalizer(self):
        return DashboardPage.advance_equalizer(
            self
        )


class DashboardAudioEqualizerTests(
    unittest.TestCase
):
    def test_spotify_starts_real_spectrum_service(self):
        dashboard = _FakeDashboard(
            source_app="Spotify.exe",
            levels=(
                0.0,
                0.15,
                0.3,
                0.45,
                0.6,
                0.75,
                0.9,
                1.0,
            ),
        )

        DashboardPage.start_equalizer_animation(
            dashboard
        )

        self.assertEqual(
            dashboard
            .spotify_audio_spectrum_service
            .start_calls,
            1,
        )

        self.assertTrue(
            dashboard.equalizer_timer.active
        )

        self.assertTrue(
            dashboard.equalizer.visible
        )

        self.assertEqual(
            len(dashboard.equalizer.text),
            8,
        )

    def test_spotify_source_matching_is_case_insensitive(self):
        dashboard = _FakeDashboard(
            source_app="SpotifyAB.SpotifyMusic"
        )

        DashboardPage.start_equalizer_animation(
            dashboard
        )

        self.assertEqual(
            dashboard
            .spotify_audio_spectrum_service
            .start_calls,
            1,
        )

    def test_non_spotify_source_has_no_fake_equalizer(self):
        dashboard = _FakeDashboard(
            source_app="chrome.exe"
        )

        DashboardPage.start_equalizer_animation(
            dashboard
        )

        self.assertEqual(
            dashboard
            .spotify_audio_spectrum_service
            .start_calls,
            0,
        )

        self.assertFalse(
            dashboard.equalizer_timer.active
        )

        self.assertFalse(
            dashboard.equalizer.visible
        )

        self.assertEqual(
            dashboard.equalizer.text,
            "",
        )

    def test_advance_equalizer_uses_latest_real_levels(self):
        dashboard = _FakeDashboard(
            levels=(
                0.0,
                1.0,
                0.0,
                1.0,
                0.0,
                1.0,
                0.0,
                1.0,
            )
        )

        DashboardPage.advance_equalizer(
            dashboard
        )

        self.assertEqual(
            dashboard.equalizer.text,
            "▁█▁█▁█▁█",
        )

    def test_stop_equalizer_stops_service_and_hides_label(self):
        dashboard = _FakeDashboard()

        dashboard.equalizer_timer.start()
        dashboard.equalizer.setVisible(True)
        dashboard.equalizer.setText(
            "████████"
        )

        DashboardPage.stop_equalizer_animation(
            dashboard
        )

        self.assertFalse(
            dashboard.equalizer_timer.active
        )

        self.assertFalse(
            dashboard.equalizer.visible
        )

        self.assertEqual(
            dashboard.equalizer.text,
            "",
        )

        self.assertEqual(
            dashboard
            .spotify_audio_spectrum_service
            .stop_calls,
            [0.5],
        )

    def test_media_worker_shutdown_shuts_down_spectrum(self):
        dashboard = _FakeDashboard()
        dashboard.media_worker = None

        DashboardPage.stop_media_worker(
            dashboard
        )

        self.assertEqual(
            dashboard
            .spotify_audio_spectrum_service
            .shutdown_calls,
            [2.0],
        )

    def test_existing_media_worker_shutdown_is_preserved(self):
        dashboard = _FakeDashboard()

        worker = _FakeWorker(
            running=True
        )

        dashboard.media_worker = worker

        DashboardPage.stop_media_worker(
            dashboard
        )

        self.assertEqual(
            worker.stop_calls,
            1,
        )

        self.assertEqual(
            worker.wait_calls,
            [7000],
        )

    def test_old_fake_equalizer_frames_are_removed(self):
        path = (
            Path(__file__)
            .resolve()
            .parents[1]
            / "src"
            / "ui"
            / "dashboard.py"
        )

        source = path.read_text(
            encoding="utf-8-sig"
        )

        self.assertNotIn(
            "_equalizer_frames",
            source,
        )

        self.assertNotIn(
            "_equalizer_index",
            source,
        )

        self.assertIn(
            "SpotifyAudioSpectrumService",
            source,
        )

        self.assertIn(
            "spectrum_levels_to_text",
            source,
        )

    def test_equalizer_refresh_is_about_30_hz(self):
        path = (
            Path(__file__)
            .resolve()
            .parents[1]
            / "src"
            / "ui"
            / "dashboard.py"
        )

        source = path.read_text(
            encoding="utf-8-sig"
        )

        expected = (
            "self.equalizer_timer.setInterval(\n"
            "            33\n"
            "        )"
        )

        self.assertIn(
            expected,
            source,
        )


if __name__ == "__main__":
    unittest.main()