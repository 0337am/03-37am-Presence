from __future__ import annotations

import inspect
import threading
import unittest

from PyQt6.QtCore import (
    QCoreApplication,
    QEventLoop,
    QTimer,
)

from winsdk.windows.media import (
    MediaPlaybackAutoRepeatMode,
)

from src.music.playback_control_coordinator import (
    ACTION_REPEAT,
    ACTION_SHUFFLE,
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
            (
                "resume_playback",
                None,
            )
        )

    def pause_playback(
        self,
    ):
        self.calls.append(
            (
                "pause_playback",
                None,
            )
        )

    def skip_next(
        self,
    ):
        self.calls.append(
            (
                "skip_next",
                None,
            )
        )

    def skip_previous(
        self,
    ):
        self.calls.append(
            (
                "skip_previous",
                None,
            )
        )

    def set_shuffle(
        self,
        enabled,
    ):
        self.calls.append(
            (
                "set_shuffle",
                enabled,
            )
        )

    def set_repeat_mode(
        self,
        mode,
    ):
        self.calls.append(
            (
                "set_repeat_mode",
                mode,
            )
        )


class LegacySpotifyRuntime:
    def resume_playback(
        self,
    ):
        return None

    def pause_playback(
        self,
    ):
        return None

    def skip_next(
        self,
    ):
        return None

    def skip_previous(
        self,
    ):
        return None


class PlaybackShuffleRepeatCoordinatorTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QCoreApplication.instance()
            or QCoreApplication(
                []
            )
        )

    def coordinator(
        self,
        *,
        spotify=None,
        media_controls_factory=None,
    ):
        runtime = (
            spotify
            if spotify is not None
            else FakeSpotifyRuntime()
        )

        if media_controls_factory is None:
            class UnusedMediaControls:
                pass

            media_controls_factory = (
                UnusedMediaControls
            )

        result = PlaybackControlCoordinator(
            runtime,
            media_controls_factory=(
                media_controls_factory
            ),
        )

        self.addCleanup(
            result.shutdown
        )

        return result

    def wait_for_media_completion(
        self,
        coordinator,
        trigger,
    ):
        completed = []
        failures = []

        loop = QEventLoop()

        def on_completed(
            action,
            success,
        ):
            completed.append(
                (
                    action,
                    success,
                )
            )

            loop.quit()

        def on_failed(
            action,
            message,
        ):
            failures.append(
                (
                    action,
                    message,
                )
            )

            loop.quit()

        coordinator.control_completed.connect(
            on_completed
        )

        coordinator.control_failed.connect(
            on_failed
        )

        timer = QTimer()

        timer.setSingleShot(
            True
        )

        timer.timeout.connect(
            loop.quit
        )

        timer.start(
            2000
        )

        accepted = trigger()

        if (
            accepted
            and not completed
            and not failures
        ):
            loop.exec()

        timer.stop()

        self.app.processEvents()

        return (
            accepted,
            completed,
            failures,
        )

    def test_spotify_shuffle_uses_official_runtime(
        self,
    ):
        runtime = FakeSpotifyRuntime()

        coordinator = self.coordinator(
            spotify=runtime
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
            coordinator.request_shuffle(
                True,
                "Spotify.exe",
            )
        )

        self.assertTrue(
            coordinator.request_shuffle(
                False,
                "Spotify.exe",
            )
        )

        self.assertEqual(
            runtime.calls,
            [
                (
                    "set_shuffle",
                    True,
                ),
                (
                    "set_shuffle",
                    False,
                ),
            ],
        )

        self.assertEqual(
            dispatched,
            [
                (
                    ACTION_SHUFFLE,
                    "spotify",
                ),
                (
                    ACTION_SHUFFLE,
                    "spotify",
                ),
            ],
        )

    def test_spotify_repeat_uses_official_runtime(
        self,
    ):
        runtime = FakeSpotifyRuntime()

        coordinator = self.coordinator(
            spotify=runtime
        )

        for mode in (
            "off",
            "context",
            "track",
        ):
            with self.subTest(
                mode=mode
            ):
                self.assertTrue(
                    coordinator.request_repeat_mode(
                        mode,
                        "Spotify.exe",
                    )
                )

        self.assertEqual(
            runtime.calls,
            [
                (
                    "set_repeat_mode",
                    "off",
                ),
                (
                    "set_repeat_mode",
                    "context",
                ),
                (
                    "set_repeat_mode",
                    "track",
                ),
            ],
        )

    def test_spotify_source_matching_is_case_insensitive(
        self,
    ):
        runtime = FakeSpotifyRuntime()

        coordinator = self.coordinator(
            spotify=runtime
        )

        self.assertTrue(
            coordinator.request_shuffle(
                True,
                "SPOTIFY.EXE",
            )
        )

        self.assertTrue(
            coordinator.request_repeat_mode(
                "track",
                "sPoTiFy.ExE",
            )
        )

        self.assertEqual(
            runtime.calls,
            [
                (
                    "set_shuffle",
                    True,
                ),
                (
                    "set_repeat_mode",
                    "track",
                ),
            ],
        )

    def test_invalid_shuffle_state_is_rejected(
        self,
    ):
        runtime = FakeSpotifyRuntime()

        coordinator = self.coordinator(
            spotify=runtime
        )

        for invalid in (
            1,
            0,
            None,
            "true",
        ):
            with self.subTest(
                invalid=invalid
            ):
                self.assertFalse(
                    coordinator.request_shuffle(
                        invalid,
                        "Spotify.exe",
                    )
                )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_invalid_repeat_state_is_rejected(
        self,
    ):
        runtime = FakeSpotifyRuntime()

        coordinator = self.coordinator(
            spotify=runtime
        )

        for invalid in (
            None,
            True,
            "list",
            " context ",
            "",
        ):
            with self.subTest(
                invalid=invalid
            ):
                self.assertFalse(
                    coordinator.request_repeat_mode(
                        invalid,
                        "Spotify.exe",
                    )
                )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_missing_spotify_shuffle_fails_safely(
        self,
    ):
        coordinator = self.coordinator(
            spotify=LegacySpotifyRuntime()
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
            coordinator.request_shuffle(
                True,
                "Spotify.exe",
            )
        )

        self.assertEqual(
            failures[0][0],
            ACTION_SHUFFLE,
        )

        self.assertIn(
            "unavailable",
            failures[0][1],
        )

    def test_missing_spotify_repeat_fails_safely(
        self,
    ):
        coordinator = self.coordinator(
            spotify=LegacySpotifyRuntime()
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
            coordinator.request_repeat_mode(
                "track",
                "Spotify.exe",
            )
        )

        self.assertEqual(
            failures[0][0],
            ACTION_REPEAT,
        )

        self.assertIn(
            "unavailable",
            failures[0][1],
        )

    def test_non_spotify_shuffle_runs_on_media_worker(
        self,
    ):
        calls = []

        main_thread = (
            threading.get_ident()
        )

        class RecordingControls:
            def set_shuffle(
                self,
                enabled,
            ):
                calls.append(
                    (
                        enabled,
                        threading.get_ident(),
                    )
                )

                return True

        coordinator = self.coordinator(
            media_controls_factory=(
                RecordingControls
            )
        )

        (
            accepted,
            completed,
            failures,
        ) = self.wait_for_media_completion(
            coordinator,
            lambda:
            coordinator.request_shuffle(
                False,
                "chrome.exe",
            ),
        )

        self.assertTrue(
            accepted
        )

        self.assertEqual(
            failures,
            [],
        )

        self.assertEqual(
            completed,
            [
                (
                    ACTION_SHUFFLE,
                    True,
                ),
            ],
        )

        self.assertEqual(
            calls[0][0],
            False,
        )

        self.assertNotEqual(
            calls[0][1],
            main_thread,
        )

    def test_non_spotify_repeat_off_maps_to_none_enum(
        self,
    ):
        calls = []

        class RecordingControls:
            def set_repeat_mode(
                self,
                mode,
            ):
                calls.append(
                    mode
                )

                return True

        coordinator = self.coordinator(
            media_controls_factory=(
                RecordingControls
            )
        )

        (
            accepted,
            completed,
            failures,
        ) = self.wait_for_media_completion(
            coordinator,
            lambda:
            coordinator.request_repeat_mode(
                "off",
                "chrome.exe",
            ),
        )

        self.assertTrue(
            accepted
        )

        self.assertEqual(
            failures,
            [],
        )

        self.assertEqual(
            completed,
            [
                (
                    ACTION_REPEAT,
                    True,
                ),
            ],
        )

        self.assertEqual(
            calls,
            [
                MediaPlaybackAutoRepeatMode.NONE,
            ],
        )

    def test_non_spotify_repeat_context_maps_to_list_enum(
        self,
    ):
        calls = []

        class RecordingControls:
            def set_repeat_mode(
                self,
                mode,
            ):
                calls.append(
                    mode
                )

                return True

        coordinator = self.coordinator(
            media_controls_factory=(
                RecordingControls
            )
        )

        (
            accepted,
            completed,
            failures,
        ) = self.wait_for_media_completion(
            coordinator,
            lambda:
            coordinator.request_repeat_mode(
                "context",
                "vlc.exe",
            ),
        )

        self.assertTrue(
            accepted
        )

        self.assertEqual(
            failures,
            [],
        )

        self.assertEqual(
            calls,
            [
                MediaPlaybackAutoRepeatMode.LIST,
            ],
        )

    def test_non_spotify_repeat_track_maps_to_track_enum(
        self,
    ):
        calls = []

        class RecordingControls:
            def set_repeat_mode(
                self,
                mode,
            ):
                calls.append(
                    mode
                )

                return True

        coordinator = self.coordinator(
            media_controls_factory=(
                RecordingControls
            )
        )

        (
            accepted,
            completed,
            failures,
        ) = self.wait_for_media_completion(
            coordinator,
            lambda:
            coordinator.request_repeat_mode(
                "track",
                "firefox.exe",
            ),
        )

        self.assertTrue(
            accepted
        )

        self.assertEqual(
            failures,
            [],
        )

        self.assertEqual(
            calls,
            [
                MediaPlaybackAutoRepeatMode.TRACK,
            ],
        )

    def test_state_routing_contains_no_unsafe_playback_path(
        self,
    ):
        source = inspect.getsource(
            PlaybackControlCoordinator
        )

        for forbidden in (
            "SetForegroundWindow",
            "BringWindowToTop",
            "SetActiveWindow",
            "SendInput",
            "keybd_event",
            "mouse_event",
            "pyautogui",
            "QMediaPlayer",
            "os.startfile",
            "spotify:local:",
            "spotify:track:",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    source,
                )


if __name__ == "__main__":
    unittest.main()
