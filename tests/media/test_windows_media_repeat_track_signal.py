import enum
import unittest
from types import SimpleNamespace

from src.music.song import Song
from src.music.windows_media import WindowsMedia
from tests.repo_paths import REPO_ROOT


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


class WindowsMediaRepeatTrackSignalTests(
    unittest.TestCase
):
    def test_song_defaults_repeat_track_unknown(
        self,
    ):
        self.assertIsNone(
            Song().repeat_track
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
        )

        self.assertEqual(
            song.source_app,
            "Spotify.exe",
        )

        self.assertIsNone(
            song.repeat_track
        )

    def test_repeat_track_mode_returns_true(
        self,
    ):
        state = (
            WindowsMedia
            ._repeat_track_state(
                FakeSession(
                    SimpleNamespace(
                        auto_repeat_mode=(
                            RepeatMode.TRACK
                        )
                    )
                )
            )
        )

        self.assertIs(
            state,
            True,
        )

    def test_repeat_list_mode_returns_false(
        self,
    ):
        state = (
            WindowsMedia
            ._repeat_track_state(
                FakeSession(
                    SimpleNamespace(
                        auto_repeat_mode=(
                            RepeatMode.LIST
                        )
                    )
                )
            )
        )

        self.assertIs(
            state,
            False,
        )

    def test_repeat_none_mode_returns_false(
        self,
    ):
        state = (
            WindowsMedia
            ._repeat_track_state(
                FakeSession(
                    SimpleNamespace(
                        auto_repeat_mode=(
                            RepeatMode.NONE
                        )
                    )
                )
            )
        )

        self.assertIs(
            state,
            False,
        )

    def test_missing_playback_info_returns_unknown(
        self,
    ):
        state = (
            WindowsMedia
            ._repeat_track_state(
                FakeSession(
                    None
                )
            )
        )

        self.assertIsNone(
            state
        )

    def test_unrecognized_repeat_mode_returns_unknown(
        self,
    ):
        state = (
            WindowsMedia
            ._repeat_track_state(
                FakeSession(
                    SimpleNamespace(
                        auto_repeat_mode=(
                            "unexpected-mode"
                        )
                    )
                )
            )
        )

        self.assertIsNone(
            state
        )

    def test_playback_info_error_returns_unknown(
        self,
    ):
        state = (
            WindowsMedia
            ._repeat_track_state(
                FakeSession(
                    error=RuntimeError(
                        "simulated"
                    )
                )
            )
        )

        self.assertIsNone(
            state
        )

    def test_production_song_constructor_populates_repeat_track(
        self,
    ):
        source = (
            REPO_ROOT
            / "src"
            / "music"
            / "windows_media.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertEqual(
            source.count(
                "repeat_track="
                "self._repeat_track_state("
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()