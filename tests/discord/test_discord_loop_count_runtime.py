import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.discord.extended_presence import (
    ExtendedDiscordPresence,
    SongPresenceUpdate,
)
from src.discord.presence import DiscordPresence
from src.discord.presence_controller import (
    PresenceController,
)
from src.discord.presence_modes import PresenceMode
from src.music.playback_cycle_detector import (
    PlaybackCycleDetector,
)


def song(
    *,
    title="Track",
    position="0:10",
    duration="3:20",
    playing=True,
    repeat_track=None,
):
    return SimpleNamespace(
        title=title,
        artist="Artist",
        album="Album",
        source_app="Spotify.exe",
        position=position,
        duration=duration,
        playing=playing,
        artwork_bytes=None,
        repeat_track=repeat_track,
        explicit_seek=False,
    )


class FakeRpc:
    def __init__(self):
        self.calls = []

    def update(self, **kwargs):
        self.calls.append(kwargs)

    def clear(self):
        pass


class FakeUploader:
    is_configured = False


class FakeSignal:
    def __init__(self):
        self.payloads = []

    def emit(self, payload):
        self.payloads.append(payload)


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

    presence._normalize_rpc_buttons = (
        lambda buttons: ()
    )

    presence._rpc_button_payload = (
        lambda buttons: []
    )

    return presence, queued


def isolated_base_presence():
    presence = object.__new__(
        DiscordPresence
    )

    presence.rpc = FakeRpc()
    presence.artwork_uploader = FakeUploader()

    presence._discord_album_for_track = (
        lambda title, album: album
    )

    return presence


def perform_end_to_start(
    presence,
    *,
    repeat_track,
    title="Track",
):
    presence.update_song(
        song(
            title=title,
            position="3:19",
            duration="3:20",
            repeat_track=repeat_track,
        )
    )

    presence.update_song(
        song(
            title=title,
            position="0:01",
            duration="3:20",
            repeat_track=repeat_track,
        )
    )


class RuntimeWithSetter:
    def __init__(self):
        self.events = []

    def set_music_loop_count_enabled(
        self,
        enabled,
    ):
        self.events.append(
            (
                "setting",
                bool(enabled),
            )
        )

    def update_song(
        self,
        value,
        buttons=None,
    ):
        self.events.append(
            (
                "song",
                value,
                buttons,
            )
        )

    def clear_presence(self):
        self.events.append(
            ("clear",)
        )


class RuntimeWithoutSetter:
    def __init__(self):
        self.updates = []

    def update_song(
        self,
        value,
        buttons=None,
    ):
        self.updates.append(
            (
                value,
                buttons,
            )
        )

    def clear_presence(self):
        pass


def controller_shell(
    runtime,
    *,
    latest_song,
):
    shell = SimpleNamespace(
        discord=runtime,
        _auto_afk_active=False,
        _mode_before_auto_afk=None,
        _latest_song=latest_song,
        mode_changed=FakeSignal(),
    )

    shell.save_mode = (
        lambda presence_mode: None
    )

    shell._discord_buttons_for_mode = (
        lambda presence_mode: []
    )

    shell._has_song = (
        lambda value: value is not None
    )

    return shell


class DiscordLoopCountRuntimeTests(
    unittest.TestCase
):
    def test_song_presence_update_legacy_positional_order_is_preserved(
        self,
    ):
        update = SongPresenceUpdate(
            song(),
            (),
            2,
            True,
        )

        self.assertEqual(
            update.playback_cycle_index,
            2,
        )

        self.assertTrue(
            update.force_publish
        )

        self.assertFalse(
            update.show_loop_count
        )

        self.assertEqual(
            update.visible_loop_count,
            0,
        )

    def test_setting_change_requests_immediate_publish(
        self,
    ):
        presence, _queued = (
            isolated_extended_presence()
        )

        presence.set_music_loop_count_enabled(
            True
        )

        self.assertTrue(
            presence._show_loop_count
        )

        self.assertTrue(
            presence._music_loop_count_publish_pending
        )

    def test_same_setting_does_not_request_publish(
        self,
    ):
        presence, _queued = (
            isolated_extended_presence()
        )

        presence._show_loop_count = True

        presence.set_music_loop_count_enabled(
            True
        )

        self.assertFalse(
            presence._music_loop_count_publish_pending
        )

    def test_trusted_repeat_increments_visible_count(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        perform_end_to_start(
            presence,
            repeat_track=True,
        )

        self.assertEqual(
            queued[-1].visible_loop_count,
            1,
        )

    def test_unknown_repeat_does_not_increment_visible_count_but_keeps_timer_publish(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        perform_end_to_start(
            presence,
            repeat_track=None,
        )

        self.assertEqual(
            queued[-1].visible_loop_count,
            0,
        )

        self.assertTrue(
            queued[-1].force_publish
        )

        self.assertGreaterEqual(
            queued[-1].playback_cycle_index,
            1,
        )

    def test_known_repeat_off_does_not_increment_visible_count(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        perform_end_to_start(
            presence,
            repeat_track=False,
        )

        self.assertEqual(
            queued[-1].visible_loop_count,
            0,
        )

    def test_track_change_resets_visible_count(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        perform_end_to_start(
            presence,
            repeat_track=True,
        )

        self.assertEqual(
            queued[-1].visible_loop_count,
            1,
        )

        presence.update_song(
            song(
                title="Different Track",
                position="0:05",
                repeat_track=True,
            )
        )

        self.assertEqual(
            queued[-1].visible_loop_count,
            0,
        )

    def test_none_song_resets_visible_count(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        perform_end_to_start(
            presence,
            repeat_track=True,
        )

        self.assertEqual(
            queued[-1].visible_loop_count,
            1,
        )

        presence.update_song(None)

        self.assertEqual(
            presence._visible_loop_count,
            0,
        )

        self.assertIsNone(
            queued[-1]
        )

    def test_enabling_after_existing_loop_preserves_current_count(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        perform_end_to_start(
            presence,
            repeat_track=True,
        )

        self.assertEqual(
            queued[-1].visible_loop_count,
            1,
        )

        self.assertFalse(
            queued[-1].show_loop_count
        )

        presence.set_music_loop_count_enabled(
            True
        )

        presence.update_song(
            song(
                position="0:02",
                repeat_track=True,
            )
        )

        self.assertTrue(
            queued[-1].show_loop_count
        )

        self.assertEqual(
            queued[-1].visible_loop_count,
            1,
        )

        self.assertTrue(
            queued[-1].force_publish
        )

    def test_hidden_publisher_preserves_old_base_call(
        self,
    ):
        presence, _queued = (
            isolated_extended_presence()
        )

        item = SongPresenceUpdate(
            song=song(),
            buttons=(),
            playback_cycle_index=3,
            force_publish=True,
            show_loop_count=False,
            visible_loop_count=3,
        )

        with patch.object(
            DiscordPresence,
            "_publish_song",
        ) as publish:
            ExtendedDiscordPresence._publish_song(
                presence,
                item,
            )

        publish.assert_called_once_with(
            item.song,
            buttons=[],
        )

    def test_visible_publisher_forwards_trusted_loop_count(
        self,
    ):
        presence, _queued = (
            isolated_extended_presence()
        )

        item = SongPresenceUpdate(
            song=song(
                repeat_track=True
            ),
            buttons=(),
            show_loop_count=True,
            visible_loop_count=3,
        )

        with patch.object(
            DiscordPresence,
            "_publish_song",
        ) as publish:
            ExtendedDiscordPresence._publish_song(
                presence,
                item,
            )

        publish.assert_called_once_with(
            item.song,
            buttons=[],
            loop_count=3,
        )

    def test_presence_key_changes_when_visibility_changes(
        self,
    ):
        base_song = song(
            repeat_track=True
        )

        hidden = SongPresenceUpdate(
            song=base_song,
            buttons=(),
            show_loop_count=False,
            visible_loop_count=2,
        )

        visible = SongPresenceUpdate(
            song=base_song,
            buttons=(),
            show_loop_count=True,
            visible_loop_count=2,
        )

        self.assertNotEqual(
            ExtendedDiscordPresence._make_presence_key(
                hidden
            ),
            ExtendedDiscordPresence._make_presence_key(
                visible
            ),
        )

    def test_presence_key_changes_with_visible_count(
        self,
    ):
        first = SongPresenceUpdate(
            song=song(
                repeat_track=True
            ),
            buttons=(),
            show_loop_count=True,
            visible_loop_count=1,
        )

        second = SongPresenceUpdate(
            song=song(
                repeat_track=True
            ),
            buttons=(),
            show_loop_count=True,
            visible_loop_count=2,
        )

        self.assertNotEqual(
            ExtendedDiscordPresence._make_presence_key(
                first
            ),
            ExtendedDiscordPresence._make_presence_key(
                second
            ),
        )

    def test_base_playing_state_renders_loop_count(
        self,
    ):
        presence = isolated_base_presence()

        presence._publish_song(
            song(
                repeat_track=True
            ),
            loop_count=1,
        )

        self.assertEqual(
            presence.rpc.calls[-1][
                "state"
            ],
            "by Artist \u2022 Loop \u00d71",
        )

    def test_base_paused_state_renders_loop_count(
        self,
    ):
        presence = isolated_base_presence()

        presence._publish_song(
            song(
                playing=False,
                repeat_track=True,
            ),
            loop_count=2,
        )

        self.assertEqual(
            presence.rpc.calls[-1][
                "state"
            ],
            "Paused \u2022 Artist \u2022 Loop \u00d72",
        )

    def test_base_zero_count_preserves_existing_state(
        self,
    ):
        presence = isolated_base_presence()

        presence._publish_song(
            song(),
            loop_count=0,
        )

        self.assertEqual(
            presence.rpc.calls[-1][
                "state"
            ],
            "by Artist",
        )

    def test_controller_music_apply_forwards_setting_before_song_update(
        self,
    ):
        current_song = song(
            repeat_track=True
        )

        runtime = RuntimeWithSetter()

        shell = controller_shell(
            runtime,
            latest_song=current_song,
        )

        PresenceController.apply_mode(
            shell,
            PresenceMode(
                mode="music",
                show_loop_count=True,
            ),
        )

        self.assertEqual(
            runtime.events[0],
            (
                "setting",
                True,
            ),
        )

        self.assertEqual(
            runtime.events[1][0],
            "song",
        )

        self.assertIs(
            runtime.events[1][1],
            current_song,
        )

    def test_controller_without_loop_setter_remains_compatible(
        self,
    ):
        current_song = song()

        runtime = RuntimeWithoutSetter()

        shell = controller_shell(
            runtime,
            latest_song=current_song,
        )

        PresenceController.apply_mode(
            shell,
            PresenceMode(
                mode="music",
                show_loop_count=True,
            ),
        )

        self.assertEqual(
            len(runtime.updates),
            1,
        )

        self.assertIs(
            runtime.updates[0][0],
            current_song,
        )


if __name__ == "__main__":
    unittest.main()