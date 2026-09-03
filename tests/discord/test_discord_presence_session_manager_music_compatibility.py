from __future__ import annotations

import unittest

from src.discord.application_library import (
    DiscordApplicationEntry,
)
from src.discord.session_manager import (
    MUSIC_LANE_ID,
    SECONDARY_LANE_ID,
    DiscordPresenceSessionManager,
)


ENTRY_ID = (
    "discord_app_0123456789abcdef"
)

SECOND_ENTRY_ID = (
    "discord_app_fedcba9876543210"
)

APPLICATION_ID = (
    "1096663809097203752"
)

SECOND_APPLICATION_ID = (
    "1523801127962022071"
)


ENTRY = DiscordApplicationEntry(
    entry_id=ENTRY_ID,
    name="Music",
    application_id=APPLICATION_ID,
)

SECOND_ENTRY = DiscordApplicationEntry(
    entry_id=SECOND_ENTRY_ID,
    name="Secondary",
    application_id=SECOND_APPLICATION_ID,
)


class _BaseSession:
    def __init__(
        self,
        client_id,
    ):
        self.client_id = client_id

        self.connect_count = 0
        self.clear_count = 0
        self.close_count = 0

        self.song_updates = []
        self.custom_updates = []
        self.events = []

    def connect(self):
        self.connect_count += 1
        self.events.append(
            ("connect",)
        )
        return True

    def update_song(
        self,
        song,
        *,
        buttons=None,
    ):
        self.song_updates.append(
            (
                song,
                buttons,
            )
        )

        self.events.append(
            (
                "song",
                song,
                buttons,
            )
        )

    def update_custom(
        self,
        **payload,
    ):
        self.custom_updates.append(
            dict(
                payload
            )
        )

        self.events.append(
            (
                "custom",
                dict(
                    payload
                ),
            )
        )

    def clear_presence(self):
        self.clear_count += 1

        self.events.append(
            ("clear",)
        )

    def close(self):
        self.close_count += 1

        self.events.append(
            ("close",)
        )


class _LoopAwareSession(
    _BaseSession
):
    def __init__(
        self,
        client_id,
    ):
        super().__init__(
            client_id
        )

        self.loop_values = []
        self.raise_loop_error = False

    def set_music_loop_count_enabled(
        self,
        enabled,
    ):
        if self.raise_loop_error:
            raise RuntimeError(
                "loop setting failed"
            )

        self.loop_values.append(
            enabled
        )

        self.events.append(
            (
                "loop",
                enabled,
            )
        )


class _Factory:
    def __init__(
        self,
        session_type=_LoopAwareSession,
    ):
        self.session_type = (
            session_type
        )

        self.sessions = []

    def __call__(
        self,
        *,
        client_id,
    ):
        session = self.session_type(
            client_id
        )

        self.sessions.append(
            session
        )

        return session


class _Resolver:
    def __init__(self):
        self.entries = {
            ENTRY_ID: ENTRY,
            SECOND_ENTRY_ID: SECOND_ENTRY,
        }

        self.calls = []

    def __call__(
        self,
        entry_id,
    ):
        self.calls.append(
            entry_id
        )

        return self.entries.get(
            entry_id
        )


def _manager(
    session_type=_LoopAwareSession,
):
    resolver = _Resolver()

    factory = _Factory(
        session_type
    )

    manager = (
        DiscordPresenceSessionManager(
            resolver,
            session_factory=factory,
        )
    )

    return (
        manager,
        resolver,
        factory,
    )


class DiscordPresenceSessionManagerMusicCompatibilityTests(
    unittest.TestCase
):
    def test_default_music_update_does_not_touch_loop_setting(
        self,
    ):
        manager, _, factory = (
            _manager()
        )

        song = object()

        self.assertTrue(
            manager.update_music(
                ENTRY_ID,
                song,
            )
        )

        session = factory.sessions[
            0
        ]

        self.assertEqual(
            session.loop_values,
            [],
        )

        self.assertEqual(
            session.song_updates,
            [
                (
                    song,
                    None,
                )
            ],
        )

    def test_true_loop_setting_is_forwarded_before_song(
        self,
    ):
        manager, _, factory = (
            _manager()
        )

        song = object()

        self.assertTrue(
            manager.update_music(
                ENTRY_ID,
                song,
                show_loop_count=True,
            )
        )

        session = factory.sessions[
            0
        ]

        self.assertEqual(
            session.loop_values,
            [
                True,
            ],
        )

        loop_index = (
            session.events.index(
                (
                    "loop",
                    True,
                )
            )
        )

        song_index = next(
            index
            for index, event
            in enumerate(
                session.events
            )
            if event[
                0
            ] == "song"
        )

        self.assertLess(
            loop_index,
            song_index,
        )

    def test_false_loop_setting_is_forwarded_exactly(
        self,
    ):
        manager, _, factory = (
            _manager()
        )

        self.assertTrue(
            manager.update_music(
                ENTRY_ID,
                object(),
                show_loop_count=False,
            )
        )

        self.assertEqual(
            factory.sessions[
                0
            ].loop_values,
            [
                False,
            ],
        )

    def test_invalid_loop_setting_fails_before_resolution(
        self,
    ):
        manager, resolver, factory = (
            _manager()
        )

        self.assertFalse(
            manager.update_music(
                ENTRY_ID,
                object(),
                show_loop_count="false",
            )
        )

        self.assertEqual(
            resolver.calls,
            [],
        )

        self.assertEqual(
            factory.sessions,
            [],
        )

        self.assertTrue(
            manager.last_error_for_lane(
                MUSIC_LANE_ID
            )
        )

    def test_session_without_loop_setter_remains_supported(
        self,
    ):
        manager, _, factory = (
            _manager(
                _BaseSession
            )
        )

        song = object()

        buttons = [
            {
                "label": "Open",
                "url": "https://example.com",
            }
        ]

        self.assertTrue(
            manager.update_music(
                ENTRY_ID,
                song,
                buttons=buttons,
                show_loop_count=True,
            )
        )

        self.assertEqual(
            factory.sessions[
                0
            ].song_updates,
            [
                (
                    song,
                    buttons,
                )
            ],
        )

    def test_loop_setter_failure_blocks_only_music_update(
        self,
    ):
        manager, _, factory = (
            _manager()
        )

        self.assertIsNotNone(
            manager.ensure_lane(
                SECONDARY_LANE_ID,
                SECOND_ENTRY_ID,
            )
        )

        secondary_session = (
            factory.sessions[
                0
            ]
        )

        self.assertIsNotNone(
            manager.ensure_lane(
                MUSIC_LANE_ID,
                ENTRY_ID,
            )
        )

        music_session = (
            factory.sessions[
                1
            ]
        )

        music_session.raise_loop_error = (
            True
        )

        self.assertFalse(
            manager.update_music(
                ENTRY_ID,
                object(),
                show_loop_count=True,
            )
        )

        self.assertEqual(
            music_session.song_updates,
            [],
        )

        self.assertIsNotNone(
            manager.binding_for_lane(
                MUSIC_LANE_ID
            )
        )

        self.assertIsNotNone(
            manager.binding_for_lane(
                SECONDARY_LANE_ID
            )
        )

        self.assertEqual(
            secondary_session.clear_count,
            0,
        )

        self.assertEqual(
            secondary_session.close_count,
            0,
        )

        self.assertEqual(
            manager.last_error_for_lane(
                SECONDARY_LANE_ID
            ),
            "",
        )

    def test_success_after_loop_failure_clears_music_error(
        self,
    ):
        manager, _, factory = (
            _manager()
        )

        manager.ensure_lane(
            MUSIC_LANE_ID,
            ENTRY_ID,
        )

        session = factory.sessions[
            0
        ]

        session.raise_loop_error = True

        self.assertFalse(
            manager.update_music(
                ENTRY_ID,
                object(),
                show_loop_count=True,
            )
        )

        self.assertTrue(
            manager.last_error_for_lane(
                MUSIC_LANE_ID
            )
        )

        session.raise_loop_error = False

        song = object()

        self.assertTrue(
            manager.update_music(
                ENTRY_ID,
                song,
                show_loop_count=True,
            )
        )

        self.assertEqual(
            manager.last_error_for_lane(
                MUSIC_LANE_ID
            ),
            "",
        )

        self.assertEqual(
            session.song_updates[
                -1
            ][
                0
            ],
            song,
        )

    def test_buttons_and_song_are_unchanged_when_loop_setting_is_used(
        self,
    ):
        manager, _, factory = (
            _manager()
        )

        song = object()

        buttons = [
            {
                "label": "Listen",
                "url": "https://example.com/song",
            },
            {
                "label": "Profile",
                "url": "https://example.com/profile",
            },
        ]

        self.assertTrue(
            manager.update_music(
                ENTRY_ID,
                song,
                buttons=buttons,
                show_loop_count=True,
            )
        )

        session = factory.sessions[
            0
        ]

        self.assertEqual(
            session.loop_values,
            [
                True,
            ],
        )

        self.assertEqual(
            session.song_updates,
            [
                (
                    song,
                    buttons,
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
