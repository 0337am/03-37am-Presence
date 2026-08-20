from __future__ import annotations

import inspect
import threading
import unittest

from PyQt6.QtCore import (
    QCoreApplication,
)

from src.music.playback_control_coordinator import (
    ACTION_NEXT,
    ACTION_PREVIOUS,
    ACTION_TOGGLE_PLAY_PAUSE,
    PlaybackControlCoordinator,
    _MediaControlThread,
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
            "resume_playback"
        )

    def pause_playback(
        self,
    ):
        self.calls.append(
            "pause_playback"
        )

    def skip_next(
        self,
    ):
        self.calls.append(
            "skip_next"
        )

    def skip_previous(
        self,
    ):
        self.calls.append(
            "skip_previous"
        )


class PlaybackControlCoordinatorTests(
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
        spotify=None,
        media_factory=None,
    ):
        runtime = (
            spotify
            or FakeSpotifyRuntime()
        )

        if media_factory is None:
            class SafeUnusedControls:
                def toggle_play_pause(
                    self,
                ):
                    return True

                def skip_next(
                    self,
                ):
                    return True

                def skip_previous(
                    self,
                ):
                    return True

            media_factory = (
                SafeUnusedControls
            )

        coordinator = (
            PlaybackControlCoordinator(
                runtime,
                media_controls_factory=(
                    media_factory
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

    def test_spotify_previous_uses_official_runtime(
        self,
    ):
        coordinator, runtime = (
            self.make_coordinator()
        )

        self.assertTrue(
            coordinator.request(
                ACTION_PREVIOUS,
                "Spotify.exe",
                True,
            )
        )

        self.assertEqual(
            runtime.calls,
            [
                "skip_previous"
            ],
        )

    def test_spotify_next_uses_official_runtime(
        self,
    ):
        coordinator, runtime = (
            self.make_coordinator()
        )

        self.assertTrue(
            coordinator.request(
                ACTION_NEXT,
                "Spotify.exe",
                True,
            )
        )

        self.assertEqual(
            runtime.calls,
            [
                "skip_next"
            ],
        )

    def test_playing_spotify_toggle_pauses(
        self,
    ):
        coordinator, runtime = (
            self.make_coordinator()
        )

        self.assertTrue(
            coordinator.request(
                ACTION_TOGGLE_PLAY_PAUSE,
                "Spotify.exe",
                True,
            )
        )

        self.assertEqual(
            runtime.calls,
            [
                "pause_playback"
            ],
        )

    def test_paused_spotify_toggle_resumes(
        self,
    ):
        coordinator, runtime = (
            self.make_coordinator()
        )

        self.assertTrue(
            coordinator.request(
                ACTION_TOGGLE_PLAY_PAUSE,
                "Spotify.exe",
                False,
            )
        )

        self.assertEqual(
            runtime.calls,
            [
                "resume_playback"
            ],
        )

    def test_spotify_source_matching_is_case_insensitive(
        self,
    ):
        coordinator, runtime = (
            self.make_coordinator()
        )

        self.assertTrue(
            coordinator.request(
                ACTION_NEXT,
                "SPOTIFY.EXE",
                True,
            )
        )

        self.assertEqual(
            runtime.calls,
            [
                "skip_next"
            ],
        )

    def test_spotify_transport_requires_no_track_uri(
        self,
    ):
        coordinator, runtime = (
            self.make_coordinator()
        )

        self.assertTrue(
            coordinator.request(
                ACTION_PREVIOUS,
                "Spotify.exe",
                True,
            )
        )

        self.assertEqual(
            runtime.calls,
            [
                "skip_previous"
            ],
        )

        signature = inspect.signature(
            coordinator.request
        )

        self.assertNotIn(
            "spotify_uri",
            signature.parameters,
        )

        self.assertNotIn(
            "track_uri",
            signature.parameters,
        )

    def test_non_spotify_control_runs_off_calling_thread(
        self,
    ):
        calls = []
        thread_ids = []
        completed = threading.Event()

        main_thread_id = (
            threading.get_ident()
        )

        class RecordingControls:
            def skip_next(
                self,
            ):
                calls.append(
                    "next"
                )

                thread_ids.append(
                    threading.get_ident()
                )

                completed.set()

                return True

        coordinator, _runtime = (
            self.make_coordinator(
                media_factory=(
                    RecordingControls
                ),
            )
        )

        self.assertTrue(
            coordinator.request(
                ACTION_NEXT,
                "chrome.exe",
                True,
            )
        )

        self.assertTrue(
            completed.wait(
                2.0
            )
        )

        self.assertEqual(
            calls,
            [
                "next"
            ],
        )

        self.assertEqual(
            len(
                thread_ids
            ),
            1,
        )

        self.assertNotEqual(
            thread_ids[0],
            main_thread_id,
        )

        self.assertTrue(
            coordinator.shutdown()
        )

    def test_media_worker_dispatches_expected_method(
        self,
    ):
        calls = []

        class RecordingControls:
            def skip_previous(
                self,
            ):
                calls.append(
                    "previous"
                )

                return True

        worker = _MediaControlThread(
            RecordingControls,
            ACTION_PREVIOUS,
        )

        results = []

        worker.completed.connect(
            lambda action, success:
            results.append(
                (
                    action,
                    success,
                )
            )
        )

        worker.run()

        self.assertEqual(
            calls,
            [
                "previous"
            ],
        )

        self.assertEqual(
            results,
            [
                (
                    ACTION_PREVIOUS,
                    True,
                )
            ],
        )

    def test_busy_media_worker_rejects_overlap(
        self,
    ):
        started = threading.Event()
        release = threading.Event()

        class BlockingControls:
            def skip_next(
                self,
            ):
                started.set()

                release.wait(
                    2.0
                )

                return True

        coordinator, _runtime = (
            self.make_coordinator(
                media_factory=(
                    BlockingControls
                ),
            )
        )

        self.assertTrue(
            coordinator.request(
                ACTION_NEXT,
                "chrome.exe",
                True,
            )
        )

        self.assertTrue(
            started.wait(
                2.0
            )
        )

        self.assertFalse(
            coordinator.request(
                ACTION_PREVIOUS,
                "chrome.exe",
                True,
            )
        )

        release.set()

        self.assertTrue(
            coordinator.shutdown()
        )

    def test_invalid_action_is_rejected(
        self,
    ):
        coordinator, runtime = (
            self.make_coordinator()
        )

        self.assertFalse(
            coordinator.request(
                "not-a-control",
                "Spotify.exe",
                True,
            )
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_shutdown_blocks_future_requests(
        self,
    ):
        coordinator, runtime = (
            self.make_coordinator()
        )

        self.assertTrue(
            coordinator.shutdown()
        )

        self.assertFalse(
            coordinator.request(
                ACTION_NEXT,
                "Spotify.exe",
                True,
            )
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_coordinator_contains_no_unsafe_playback_path(
        self,
    ):
        source = inspect.getsource(
            PlaybackControlCoordinator
        )

        for forbidden in (
            "spotify:local:",
            "spotify:track:",
            "os.startfile",
            "QMediaPlayer",
            "SetForegroundWindow",
            "SendInput",
            ".terminate(",
        ):
            self.assertNotIn(
                forbidden,
                source,
            )


if __name__ == "__main__":
    unittest.main()
