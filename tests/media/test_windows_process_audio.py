from __future__ import annotations

import threading
import time
import unittest
from pathlib import Path

from src.media.windows_process_audio import (
    ANALYSIS_RATE_HZ,
    ANALYSIS_SAMPLE_COUNT,
    CAPTURE_CHANNELS,
    CAPTURE_SAMPLE_RATE,
    ProcessInfo,
    SpotifyAudioSpectrumService,
    select_process_tree_root,
)
from tests.repo_paths import REPO_ROOT


class ProcessTreeTests(
    unittest.TestCase
):
    def test_selects_single_spotify_root(
        self,
    ):
        processes = (
            ProcessInfo(
                100,
                5,
                "Spotify.exe",
            ),
            ProcessInfo(
                101,
                100,
                "Spotify.exe",
            ),
            ProcessInfo(
                102,
                100,
                "Spotify.exe",
            ),
            ProcessInfo(
                200,
                5,
                "Other.exe",
            ),
        )

        self.assertEqual(
            select_process_tree_root(
                processes,
                "Spotify.exe",
            ),
            100,
        )

    def test_process_name_is_case_insensitive(
        self,
    ):
        processes = (
            ProcessInfo(
                100,
                5,
                "SPOTIFY.EXE",
            ),
            ProcessInfo(
                101,
                100,
                "spotify.exe",
            ),
        )

        self.assertEqual(
            select_process_tree_root(
                processes,
                "Spotify.exe",
            ),
            100,
        )

    def test_returns_none_without_matching_process(
        self,
    ):
        processes = (
            ProcessInfo(
                200,
                5,
                "Other.exe",
            ),
        )

        self.assertIsNone(
            select_process_tree_root(
                processes,
                "Spotify.exe",
            )
        )

    def test_returns_none_for_ambiguous_roots(
        self,
    ):
        processes = (
            ProcessInfo(
                100,
                5,
                "Spotify.exe",
            ),
            ProcessInfo(
                200,
                6,
                "Spotify.exe",
            ),
        )

        self.assertIsNone(
            select_process_tree_root(
                processes,
                "Spotify.exe",
            )
        )

    def test_blank_executable_name_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            select_process_tree_root(
                (),
                "",
            )


class SpectrumServiceTests(
    unittest.TestCase
):
    def wait_until(
        self,
        predicate,
        timeout=1.0,
    ):
        deadline = (
            time.monotonic()
            + timeout
        )

        while (
            time.monotonic()
            < deadline
        ):
            if predicate():
                return True

            time.sleep(
                0.005
            )

        return bool(
            predicate()
        )

    def make_service(
        self,
        *,
        process_finder,
        capture_runner,
        events=None,
    ):
        events = (
            events
            if events is not None
            else []
        )

        def com_initializer():
            events.append(
                "com_init"
            )

        def com_uninitializer():
            events.append(
                "com_uninit"
            )

        return SpotifyAudioSpectrumService(
            retry_interval_seconds=0.01,
            process_finder=(
                process_finder
            ),
            capture_runner=(
                capture_runner
            ),
            com_initializer=(
                com_initializer
            ),
            com_uninitializer=(
                com_uninitializer
            ),
        )

    def test_capture_service_publishes_levels(
        self,
    ):
        events = []

        def process_finder():
            return 1234

        def capture_runner(
            process_id,
            stop_event,
            publish,
        ):
            events.append(
                (
                    "capture",
                    process_id,
                )
            )

            publish(
                (
                    0.1,
                    0.2,
                    0.3,
                    0.4,
                    0.5,
                    0.6,
                    0.7,
                    0.8,
                )
            )

            stop_event.wait(
                1.0
            )

        service = self.make_service(
            process_finder=(
                process_finder
            ),
            capture_runner=(
                capture_runner
            ),
            events=events,
        )

        try:
            self.assertTrue(
                service.start()
            )

            self.assertTrue(
                self.wait_until(
                    lambda: (
                        service.target_process_id
                        == 1234
                    )
                )
            )

            self.assertTrue(
                self.wait_until(
                    lambda: (
                        service.latest_levels[7]
                        == 0.8
                    )
                )
            )

            self.assertEqual(
                service.target_process_id,
                1234,
            )

            self.assertEqual(
                service.last_error,
                "",
            )

        finally:
            self.assertTrue(
                service.stop()
            )

        self.assertIn(
            "com_init",
            events,
        )

        self.assertIn(
            "com_uninit",
            events,
        )

        self.assertIn(
            (
                "capture",
                1234,
            ),
            events,
        )

    def test_start_is_idempotent_while_running(
        self,
    ):
        entered = (
            threading.Event()
        )

        def capture_runner(
            process_id,
            stop_event,
            publish,
        ):
            entered.set()

            stop_event.wait(
                1.0
            )

        service = self.make_service(
            process_finder=lambda: 1234,
            capture_runner=(
                capture_runner
            ),
        )

        try:
            self.assertTrue(
                service.start()
            )

            self.assertTrue(
                entered.wait(
                    1.0
                )
            )

            self.assertFalse(
                service.start()
            )

        finally:
            self.assertTrue(
                service.stop()
            )

    def test_stop_is_idempotent(
        self,
    ):
        service = self.make_service(
            process_finder=lambda: None,
            capture_runner=lambda *args: None,
        )

        self.assertTrue(
            service.stop()
        )

        self.assertTrue(
            service.start()
        )

        self.assertTrue(
            service.stop()
        )

        self.assertTrue(
            service.stop()
        )

    def test_missing_spotify_retries_without_error(
        self,
    ):
        calls = {
            "finder": 0,
        }

        entered = (
            threading.Event()
        )

        def process_finder():
            calls["finder"] += 1

            if calls["finder"] < 3:
                return None

            return 555

        def capture_runner(
            process_id,
            stop_event,
            publish,
        ):
            entered.set()

            stop_event.wait(
                1.0
            )

        service = self.make_service(
            process_finder=(
                process_finder
            ),
            capture_runner=(
                capture_runner
            ),
        )

        try:
            self.assertTrue(
                service.start()
            )

            self.assertTrue(
                entered.wait(
                    1.0
                )
            )

            self.assertGreaterEqual(
                calls["finder"],
                3,
            )

            self.assertEqual(
                service.target_process_id,
                555,
            )

            self.assertEqual(
                service.last_error,
                "",
            )

        finally:
            self.assertTrue(
                service.stop()
            )

    def test_capture_failure_is_recorded_and_retried(
        self,
    ):
        calls = {
            "capture": 0,
        }

        retried = (
            threading.Event()
        )

        def capture_runner(
            process_id,
            stop_event,
            publish,
        ):
            calls["capture"] += 1

            if calls["capture"] == 1:
                raise RuntimeError(
                    "synthetic capture failure"
                )

            retried.set()

            stop_event.wait(
                1.0
            )

        service = self.make_service(
            process_finder=lambda: 1234,
            capture_runner=(
                capture_runner
            ),
        )

        try:
            self.assertTrue(
                service.start()
            )

            self.assertTrue(
                retried.wait(
                    1.0
                )
            )

            self.assertGreaterEqual(
                calls["capture"],
                2,
            )

        finally:
            self.assertTrue(
                service.stop()
            )

    def test_levels_are_cleared_after_shutdown(
        self,
    ):
        published = (
            threading.Event()
        )

        def capture_runner(
            process_id,
            stop_event,
            publish,
        ):
            publish(
                (1.0,) * 8
            )

            published.set()

            stop_event.wait(
                1.0
            )

        service = self.make_service(
            process_finder=lambda: 1234,
            capture_runner=(
                capture_runner
            ),
        )

        self.assertTrue(
            service.start()
        )

        self.assertTrue(
            published.wait(
                1.0
            )
        )

        self.assertEqual(
            service.latest_levels,
            (1.0,) * 8,
        )

        self.assertTrue(
            service.shutdown()
        )

        self.assertEqual(
            service.latest_levels,
            (0.0,) * 8,
        )

        self.assertIsNone(
            service.target_process_id
        )

    def test_out_of_range_published_levels_are_bounded(
        self,
    ):
        published = (
            threading.Event()
        )

        def capture_runner(
            process_id,
            stop_event,
            publish,
        ):
            publish(
                (
                    -5.0,
                    0.0,
                    0.25,
                    0.5,
                    0.75,
                    1.0,
                    2.0,
                    50.0,
                )
            )

            published.set()

            stop_event.wait(
                1.0
            )

        service = self.make_service(
            process_finder=lambda: 1234,
            capture_runner=(
                capture_runner
            ),
        )

        try:
            self.assertTrue(
                service.start()
            )

            self.assertTrue(
                published.wait(
                    1.0
                )
            )

            self.assertEqual(
                service.latest_levels,
                (
                    0.0,
                    0.0,
                    0.25,
                    0.5,
                    0.75,
                    1.0,
                    1.0,
                    1.0,
                ),
            )

        finally:
            self.assertTrue(
                service.stop()
            )

    def test_capture_constants_are_intentionally_bounded(
        self,
    ):
        self.assertEqual(
            CAPTURE_SAMPLE_RATE,
            44100,
        )

        self.assertEqual(
            CAPTURE_CHANNELS,
            2,
        )

        self.assertEqual(
            ANALYSIS_SAMPLE_COUNT,
            1024,
        )

        self.assertEqual(
            ANALYSIS_RATE_HZ,
            30.0,
        )

    def test_source_has_no_disk_network_playback_or_focus_control(
        self,
    ):
        path = (
            REPO_ROOT
            / "src"
            / "media"
            / "windows_process_audio.py"
        )

        source = path.read_text(
            encoding="utf-8"
        )

        forbidden = (
            "PyQt6",
            "QMediaPlayer",
            "os.startfile",
            "spotify:local:",
            "SetForegroundWindow",
            "ShowWindow",
            "SendInput",
            "mouse_event",
            "keybd_event",
            "requests.",
            "urllib",
            "QNetworkAccessManager",
            "WriteFile",
            "CreateFileW",
            "wave.open",
        )

        for token in forbidden:
            with self.subTest(
                token=token
            ):
                self.assertNotIn(
                    token,
                    source,
                )

    def test_comtypes_is_declared_runtime_dependency(
        self,
    ):
        path = (
            REPO_ROOT
            / "requirements.txt"
        )

        lines = {
            line.strip().casefold()
            for line in path.read_text(
                encoding="utf-8-sig"
            ).splitlines()
        }

        self.assertIn(
            "comtypes==1.4.16",
            lines,
        )


if __name__ == "__main__":
    unittest.main()