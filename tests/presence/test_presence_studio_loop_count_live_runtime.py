import threading
import unittest
from types import SimpleNamespace

from src.discord.extended_presence import (
    ExtendedDiscordPresence,
)
from src.discord.presence_controller import (
    PresenceController,
)
from src.music.playback_cycle_detector import (
    PlaybackCycleDetector,
)
from src.ui.presence_page import PresencePage
from tests.repo_paths import REPO_ROOT


class FakeSettings:
    def __init__(self):
        self.data = {
            "presence/active_mode": "music",
        }

    def value(
        self,
        key,
        default=None,
        *,
        type=None,
    ):
        value = self.data.get(
            key,
            default,
        )

        if type is bool:
            return bool(value)

        return value

    def setValue(
        self,
        key,
        value,
    ):
        self.data[key] = value

    def sync(self):
        pass


def isolated_extended_presence():
    presence = object.__new__(
        ExtendedDiscordPresence
    )

    presence._stop_event = threading.Event()

    presence._playback_cycle_detector = (
        PlaybackCycleDetector()
    )

    presence._show_loop_count = False
    presence._visible_loop_count = 0
    presence._music_loop_count_publish_pending = False

    queued = []

    presence._replace_queued_item = queued.append
    presence._normalize_rpc_buttons = lambda buttons: ()

    return presence, queued


def current_song():
    return SimpleNamespace(
        title="Lost In My Head",
        artist="Juice WRLD",
        album="",
        source_app="Spotify.exe",
        position="0:10",
        duration="2:47",
        playing=True,
        artwork_bytes=None,
        repeat_track=True,
        explicit_seek=False,
    )


class PresenceStudioLoopCountLiveRuntimeTests(
    unittest.TestCase
):
    def test_checkbox_handler_reaches_live_discord_runtime(
        self,
    ):
        discord, queued = isolated_extended_presence()

        controller = PresenceController(
            discord
        )
        controller.store = FakeSettings()
        controller._latest_song = current_song()

        page = SimpleNamespace(
            current_mode="music",
            controller=controller,
        )

        PresencePage.apply_music_loop_count_setting(
            page,
            True,
        )

        self.assertTrue(
            discord._show_loop_count
        )

        self.assertTrue(
            controller.store.data[
                "presence/music/show_loop_count"
            ]
        )

        self.assertTrue(
            queued[-1].show_loop_count
        )

        self.assertTrue(
            queued[-1].force_publish
        )

    def test_checkbox_toggle_is_connected_to_runtime_handler(
        self,
    ):
        source = (
            REPO_ROOT
            / "src"
            / "ui"
            / "presence_page.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "self.loop_count_box.toggled.connect(\n"
            "            "
            "self.apply_music_loop_count_setting\n"
            "        )",
            source,
        )


if __name__ == "__main__":
    unittest.main()
