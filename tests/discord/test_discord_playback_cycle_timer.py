import threading
import unittest
from types import SimpleNamespace

from src.discord.extended_presence import (
    ExtendedDiscordPresence,
    SongPresenceUpdate,
)
from src.discord.presence import (
    DiscordPresence,
)
from src.music.playback_cycle_detector import (
    PlaybackCycleDetector,
)


def song(
    *,
    title="Track",
    artist="Artist",
    album="Album",
    source_app="Spotify.exe",
    position="0:00",
    duration="3:20",
    playing=True,
    repeat_track=None,
    explicit_seek=False,
):
    result = SimpleNamespace(
        title=title,
        artist=artist,
        album=album,
        source_app=source_app,
        position=position,
        duration=duration,
        playing=playing,
        artwork_bytes=None,
        explicit_seek=explicit_seek,
    )

    if repeat_track is not None:
        result.repeat_track = repeat_track

    return result


def isolated_extended_presence():
    presence = object.__new__(
        ExtendedDiscordPresence
    )

    presence._stop_event = (
        threading.Event()
    )

    presence._playback_cycle_detector = (
        PlaybackCycleDetector()
    )

    queued = []

    presence._replace_queued_item = (
        queued.append
    )

    presence._normalize_rpc_buttons = (
        lambda buttons: ()
    )

    return presence, queued


class DiscordPlaybackCycleTimerTests(
    unittest.TestCase
):
    def test_song_presence_update_defaults_are_backward_compatible(
        self,
    ):
        update = SongPresenceUpdate(
            song=song(),
            buttons=(),
        )

        self.assertEqual(
            update.playback_cycle_index,
            0,
        )

        self.assertFalse(
            update.force_publish
        )

    def test_initial_song_snapshot_does_not_force_publish(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        presence.update_song(
            song(
                position="0:10"
            )
        )

        update = queued[-1]

        self.assertFalse(
            update.force_publish
        )

        self.assertEqual(
            update.playback_cycle_index,
            0,
        )

    def test_same_song_end_to_start_replay_forces_publish(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        presence.update_song(
            song(
                position="3:19"
            )
        )

        presence.update_song(
            song(
                position="0:01"
            )
        )

        update = queued[-1]

        self.assertTrue(
            update.force_publish
        )

        self.assertEqual(
            update.playback_cycle_index,
            1,
        )

        self.assertEqual(
            update.song.position,
            "0:01",
        )

    def test_second_same_song_replay_increments_cycle_index(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        presence.update_song(
            song(
                position="3:19"
            )
        )

        presence.update_song(
            song(
                position="0:01"
            )
        )

        presence.update_song(
            song(
                position="3:19"
            )
        )

        presence.update_song(
            song(
                position="0:01"
            )
        )

        update = queued[-1]

        self.assertTrue(
            update.force_publish
        )

        self.assertEqual(
            update.playback_cycle_index,
            2,
        )

    def test_track_change_resets_cycle_index(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        presence.update_song(
            song(
                position="3:19"
            )
        )

        presence.update_song(
            song(
                position="0:01"
            )
        )

        presence.update_song(
            song(
                title="Different Track",
                position="0:15",
            )
        )

        update = queued[-1]

        self.assertFalse(
            update.force_publish
        )

        self.assertEqual(
            update.playback_cycle_index,
            0,
        )

    def test_explicit_seek_suppresses_replay_classification(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        presence.update_song(
            song(
                position="3:19",
                repeat_track=True,
            )
        )

        presence.update_song(
            song(
                position="0:01",
                repeat_track=True,
                explicit_seek=True,
            )
        )

        update = queued[-1]

        self.assertFalse(
            update.force_publish
        )

        self.assertEqual(
            update.playback_cycle_index,
            0,
        )

    def test_known_repeat_disabled_suppresses_replay_classification(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        presence.update_song(
            song(
                position="3:19",
                repeat_track=False,
            )
        )

        presence.update_song(
            song(
                position="0:01",
                repeat_track=False,
            )
        )

        update = queued[-1]

        self.assertFalse(
            update.force_publish
        )

        self.assertEqual(
            update.playback_cycle_index,
            0,
        )

    def test_none_song_clears_cycle_state(
        self,
    ):
        presence, queued = (
            isolated_extended_presence()
        )

        presence.update_song(
            song(
                position="3:19"
            )
        )

        presence.update_song(
            song(
                position="0:01"
            )
        )

        self.assertEqual(
            presence._playback_cycle_detector.cycle_index,
            1,
        )

        presence.update_song(
            None
        )

        self.assertIsNone(
            queued[-1]
        )

        self.assertEqual(
            presence._playback_cycle_detector.cycle_index,
            0,
        )

        self.assertIsNone(
            presence._playback_cycle_detector.identity
        )

    def test_force_publish_bypasses_update_interval_throttle(
        self,
    ):
        presence = object.__new__(
            DiscordPresence
        )

        self.assertTrue(
            presence._should_delay_publish(
                elapsed=1.0,
                playback_state_changed=False,
                force_publish=False,
            )
        )

        self.assertFalse(
            presence._should_delay_publish(
                elapsed=1.0,
                playback_state_changed=False,
                force_publish=True,
            )
        )

    def test_force_publish_bypasses_unchanged_presence_key_dedupe(
        self,
    ):
        key = (
            "Track",
            "Artist",
        )

        self.assertTrue(
            DiscordPresence._should_dedupe_publish(
                presence_key=key,
                last_presence_key=key,
                force_publish=False,
            )
        )

        self.assertFalse(
            DiscordPresence._should_dedupe_publish(
                presence_key=key,
                last_presence_key=key,
                force_publish=True,
            )
        )


if __name__ == "__main__":
    unittest.main()