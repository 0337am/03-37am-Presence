from __future__ import annotations

import inspect
import threading
import time
import unittest

from PyQt6.QtCore import QCoreApplication

from src.music.playback_control_coordinator import (
    PlaybackControlCoordinator,
)


class FakeSpotifyRuntime:
    def __init__(
        self,
    ):
        self.calls = []

    def resume_playback(
        self,
    ):
        self.calls.append(
            ("resume_playback",)
        )

    def pause_playback(
        self,
    ):
        self.calls.append(
            ("pause_playback",)
        )

    def skip_next(
        self,
    ):
        self.calls.append(
            ("skip_next",)
        )

    def skip_previous(
        self,
    ):
        self.calls.append(
            ("skip_previous",)
        )

    def seek_to_seconds(
        self,
        seconds,
    ):
        self.calls.append(
            (
                "seek_to_seconds",
                seconds,
            )
        )


class PlaybackSeekCoordinatorTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QCoreApplication.instance()
            or QCoreApplication([])
        )

    def make_coordinator(
        self,
        *,
        spotify_runtime=None,
        media_controls_factory=None,
    ):
        runtime = (
            spotify_runtime
            if spotify_runtime is not None
            else FakeSpotifyRuntime()
        )

        if media_controls_factory is None:
            class UnusedMediaControls:
                def seek_to_seconds(
                    self,
                    seconds,
                ):
                    del seconds
                    return True

            media_controls_factory = (
                UnusedMediaControls
            )

        coordinator = (
            PlaybackControlCoordinator(
                runtime,
                media_controls_factory=(
                    media_controls_factory
                ),
            )
        )

        self.addCleanup(
            coordinator.shutdown
        )

        return (
            coordinator,
            runtime,
        )

    def test_spotify_seek_uses_official_runtime(
        self,
    ):
        (
            coordinator,
            runtime,
        ) = self.make_coordinator()

        dispatched = []

        coordinator.control_dispatched.connect(
            lambda action, source:
            dispatched.append(
                (
                    action,
                    source,
                )
            )
        )

        accepted = (
            coordinator.request_seek(
                91.25,
                "Spotify.exe",
            )
        )

        self.assertTrue(
            accepted
        )

        self.assertEqual(
            runtime.calls,
            [
                (
                    "seek_to_seconds",
                    91.25,
                )
            ],
        )

        self.assertEqual(
            dispatched,
            [
                (
                    "seek",
                    "spotify",
                )
            ],
        )

    def test_spotify_source_match_is_case_insensitive(
        self,
    ):
        (
            coordinator,
            runtime,
        ) = self.make_coordinator()

        self.assertTrue(
            coordinator.request_seek(
                12,
                "SPOTIFY.EXE",
            )
        )

        self.assertEqual(
            runtime.calls[-1],
            (
                "seek_to_seconds",
                12.0,
            ),
        )

    def test_invalid_seek_positions_are_rejected(
        self,
    ):
        (
            coordinator,
            runtime,
        ) = self.make_coordinator()

        invalid_values = (
            True,
            -0.01,
            float("inf"),
            float("-inf"),
            float("nan"),
            "not-a-number",
        )

        for value in invalid_values:
            with self.subTest(
                value=value
            ):
                self.assertFalse(
                    coordinator.request_seek(
                        value,
                        "Spotify.exe",
                    )
                )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_missing_spotify_seek_method_fails_safely(
        self,
    ):
        class LegacySpotifyRuntime:
            def resume_playback(
                self,
            ):
                pass

            def pause_playback(
                self,
            ):
                pass

            def skip_next(
                self,
            ):
                pass

            def skip_previous(
                self,
            ):
                pass

        (
            coordinator,
            _runtime,
        ) = self.make_coordinator(
            spotify_runtime=(
                LegacySpotifyRuntime()
            )
        )

        failures = []

        coordinator.control_failed.connect(
            lambda action, message:
            failures.append(
                (
                    action,
                    message,
                )
            )
        )

        self.assertFalse(
            coordinator.request_seek(
                20,
                "Spotify.exe",
            )
        )

        self.assertEqual(
            len(failures),
            1,
        )

        self.assertEqual(
            failures[0][0],
            "seek",
        )

    def test_non_spotify_seek_runs_on_media_worker_thread(
        self,
    ):
        called = threading.Event()
        calls = []
        thread_ids = []

        caller_thread = (
            threading.get_ident()
        )

        class RecordingMediaControls:
            def seek_to_seconds(
                self,
                seconds,
            ):
                calls.append(
                    seconds
                )

                thread_ids.append(
                    threading.get_ident()
                )

                called.set()

                return True

        (
            coordinator,
            _runtime,
        ) = self.make_coordinator(
            media_controls_factory=(
                RecordingMediaControls
            )
        )

        dispatched = []

        coordinator.control_dispatched.connect(
            lambda action, source:
            dispatched.append(
                (
                    action,
                    source,
                )
            )
        )

        self.assertTrue(
            coordinator.request_seek(
                43.5,
                "chrome.exe",
            )
        )

        self.assertTrue(
            called.wait(
                2.0
            )
        )

        deadline = (
            time.monotonic()
            + 2.0
        )

        while (
            coordinator.media_busy
            and time.monotonic()
            < deadline
        ):
            self.app.processEvents()
            time.sleep(
                0.005
            )

        self.assertTrue(
            coordinator.shutdown()
        )

        self.assertEqual(
            calls,
            [43.5],
        )

        self.assertEqual(
            len(thread_ids),
            1,
        )

        self.assertNotEqual(
            thread_ids[0],
            caller_thread,
        )

        self.assertEqual(
            dispatched,
            [
                (
                    "seek",
                    "windows_media",
                )
            ],
        )

    def test_seek_routing_contains_no_unsafe_playback_mechanism(
        self,
    ):
        source = inspect.getsource(
            PlaybackControlCoordinator
        )

        forbidden = (
            "spotify:local:",
            "spotify:track:",
            "os.startfile",
            "QMediaPlayer",
            "SetForegroundWindow",
            "BringWindowToTop",
            "SetActiveWindow",
            "SendInput",
            "keybd_event",
            "mouse_event",
            "pyautogui",
            ".terminate(",
        )

        for token in forbidden:
            self.assertNotIn(
                token,
                source,
            )


if __name__ == "__main__":
    unittest.main()
