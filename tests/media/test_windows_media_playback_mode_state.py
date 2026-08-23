import enum
import inspect
import unittest
from types import SimpleNamespace

from src.music.song import Song
from src.music.windows_media import WindowsMedia


class RepeatMode(enum.Enum):
    NONE = 0
    TRACK = 1
    LIST = 2


class FakeSession:
    def __init__(
        self,
        playback_info=None,
        *,
        error=None,
    ):
        self.playback_info = (
            playback_info
        )

        self.error = error

    def get_playback_info(
        self,
    ):
        if self.error is not None:
            raise self.error

        return self.playback_info


class WindowsMediaPlaybackModeStateTests(
    unittest.TestCase
):
    def test_song_defaults_new_state_unknown(
        self,
    ):
        song = Song()

        self.assertIsNone(
            song.repeat_track
        )

        self.assertIsNone(
            song.shuffle_active
        )

        self.assertIsNone(
            song.repeat_mode
        )

    def test_song_legacy_positional_order_is_preserved(
        self,
    ):
        song = Song(
            "Title",
            "Artist",
            "Album",
            "3:00",
            "1:00",
            True,
            b"art",
            "Spotify.exe",
            True,
        )

        self.assertEqual(
            song.title,
            "Title",
        )

        self.assertEqual(
            song.source_app,
            "Spotify.exe",
        )

        self.assertTrue(
            song.repeat_track
        )

        self.assertIsNone(
            song.shuffle_active
        )

        self.assertIsNone(
            song.repeat_mode
        )

    def test_track_repeat_and_shuffle_on_are_normalized(
        self,
    ):
        state = (
            WindowsMedia()
            ._playback_control_state(
                FakeSession(
                    SimpleNamespace(
                        is_shuffle_active=True,
                        auto_repeat_mode=(
                            RepeatMode.TRACK
                        ),
                    )
                )
            )
        )

        self.assertEqual(
            state,
            (
                True,
                "track",
            ),
        )

    def test_context_repeat_and_shuffle_off_are_normalized(
        self,
    ):
        state = (
            WindowsMedia()
            ._playback_control_state(
                FakeSession(
                    SimpleNamespace(
                        is_shuffle_active=False,
                        auto_repeat_mode=(
                            RepeatMode.LIST
                        ),
                    )
                )
            )
        )

        self.assertEqual(
            state,
            (
                False,
                "context",
            ),
        )

    def test_repeat_off_is_distinct_from_context(
        self,
    ):
        state = (
            WindowsMedia()
            ._playback_control_state(
                FakeSession(
                    SimpleNamespace(
                        is_shuffle_active=False,
                        auto_repeat_mode=(
                            RepeatMode.NONE
                        ),
                    )
                )
            )
        )

        self.assertEqual(
            state,
            (
                False,
                "off",
            ),
        )

    def test_string_repeat_modes_are_normalized(
        self,
    ):
        media = WindowsMedia()

        expected = {
            "off": "off",
            "none": "off",
            "context": "context",
            "list": "context",
            "track": "track",
        }

        for raw, normalized in expected.items():
            with self.subTest(
                raw=raw
            ):
                self.assertEqual(
                    media._normalize_repeat_mode_state(
                        raw
                    ),
                    normalized,
                )

    def test_missing_state_remains_unknown(
        self,
    ):
        state = (
            WindowsMedia()
            ._playback_control_state(
                FakeSession(
                    SimpleNamespace()
                )
            )
        )

        self.assertEqual(
            state,
            (
                None,
                None,
            ),
        )

    def test_unrecognized_state_remains_unknown(
        self,
    ):
        state = (
            WindowsMedia()
            ._playback_control_state(
                FakeSession(
                    SimpleNamespace(
                        is_shuffle_active=1,
                        auto_repeat_mode=object(),
                    )
                )
            )
        )

        self.assertEqual(
            state,
            (
                None,
                None,
            ),
        )

    def test_playback_info_failure_is_safe(
        self,
    ):
        state = (
            WindowsMedia()
            ._playback_control_state(
                FakeSession(
                    error=RuntimeError(
                        "simulated failure"
                    )
                )
            )
        )

        self.assertEqual(
            state,
            (
                None,
                None,
            ),
        )

    def test_production_song_constructor_exposes_states(
        self,
    ):
        source = inspect.getsource(
            WindowsMedia._song_from_session
        )

        self.assertIn(
            "_playback_control_state(",
            source,
        )

        self.assertIn(
            "shuffle_active=shuffle_active",
            source,
        )

        self.assertIn(
            "repeat_mode=repeat_mode",
            source,
        )

        self.assertIn(
            "repeat_track=",
            source,
        )


if __name__ == "__main__":
    unittest.main()
