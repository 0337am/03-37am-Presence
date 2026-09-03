from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.discord.presence_controller import (
    PresenceController,
)
from src.discord.presence_modes import (
    PresenceMode,
)
from src.discord.session_manager import (
    MUSIC_LANE_ID,
)
from src.ui.main_window import (
    MainWindow,
)


MUSIC_ENTRY_ID = (
    "discord_app_0123456789abcdef"
)

MISSING_ENTRY_ID = (
    "discord_app_aaaaaaaaaaaaaaaa"
)

BUTTONS = [
    {
        "label": "Listen",
        "url": "https://example.com/listen",
    }
]


def make_song(
    title="Track",
):
    return SimpleNamespace(
        title=title,
        artist="Artist",
        album="Album",
        playing=True,
    )


class FakeStore:
    def __init__(
        self,
        values=None,
    ):
        self.values = dict(
            values or {}
        )

    def value(
        self,
        key,
        default=None,
        type=None,
    ):
        value = self.values.get(
            key,
            default,
        )

        if type is bool:
            return bool(
                value
            )

        return value

    def setValue(
        self,
        key,
        value,
    ):
        self.values[
            key
        ] = value

    def sync(
        self,
    ):
        return None


class FakeLegacyDiscord:
    def __init__(
        self,
        events,
    ):
        self.events = events

        self.is_connected = False
        self.is_running = False

        self.profile_identity = {
            "username": "Legacy",
        }

        self.fail_connect = False
        self.fail_clear = False
        self.fail_close = False

    def connect(
        self,
    ):
        self.events.append(
            (
                "legacy",
                "connect",
            )
        )

        if self.fail_connect:
            raise RuntimeError(
                "connect failed"
            )

        self.is_running = True
        self.is_connected = True

        return True

    def close(
        self,
    ):
        self.events.append(
            (
                "legacy",
                "close",
            )
        )

        if self.fail_close:
            raise RuntimeError(
                "close failed"
            )

        self.is_running = False
        self.is_connected = False

    def clear_presence(
        self,
    ):
        self.events.append(
            (
                "legacy",
                "clear",
            )
        )

        if self.fail_clear:
            raise RuntimeError(
                "clear failed"
            )

    def update_song(
        self,
        value,
        *,
        buttons=None,
    ):
        self.events.append(
            (
                "legacy",
                "song",
                value,
                buttons,
            )
        )

    def update_custom(
        self,
        **payload,
    ):
        self.events.append(
            (
                "legacy",
                "custom",
                payload,
            )
        )

    def set_music_loop_count_enabled(
        self,
        enabled,
    ):
        self.events.append(
            (
                "legacy",
                "loop",
                bool(
                    enabled
                ),
            )
        )


class FakeManager:
    def __init__(
        self,
        events,
    ):
        self.events = events

        self.update_result = True
        self.ensure_result = True
        self.release_result = True
        self.clear_result = True

        self.connected = True
        self.running = True

        self.profile = {
            "username": "Music",
        }

    def update_music(
        self,
        application_entry_id,
        value,
        *,
        buttons=None,
        show_loop_count=None,
    ):
        self.events.append(
            (
                "manager",
                "update_music",
                application_entry_id,
                value,
                buttons,
                show_loop_count,
            )
        )

        return self.update_result

    def ensure_lane(
        self,
        lane_id,
        application_entry_id,
    ):
        self.events.append(
            (
                "manager",
                "ensure",
                lane_id,
                application_entry_id,
            )
        )

        if not self.ensure_result:
            return None

        return object()

    def clear_lane(
        self,
        lane_id,
    ):
        self.events.append(
            (
                "manager",
                "clear",
                lane_id,
            )
        )

        return self.clear_result

    def release_lane(
        self,
        lane_id,
    ):
        self.events.append(
            (
                "manager",
                "release",
                lane_id,
            )
        )

        return self.release_result

    def profile_identity_for_lane(
        self,
        lane_id,
    ):
        return dict(
            self.profile
        )

    def lane_is_connected(
        self,
        lane_id,
    ):
        return self.connected

    def lane_is_running(
        self,
        lane_id,
    ):
        return self.running


def make_controller(
    *,
    with_manager=True,
    active_mode="music",
    application_entry_id=MUSIC_ENTRY_ID,
    latest_song=None,
):
    events = []

    legacy = FakeLegacyDiscord(
        events
    )

    manager = (
        FakeManager(
            events
        )
        if with_manager
        else None
    )

    controller = PresenceController(
        legacy,
        discord_session_manager=manager,
    )

    controller.store = FakeStore(
        {
            "presence/active_mode": (
                active_mode
            ),
            (
                "presence/music/"
                "application_entry_id"
            ): application_entry_id,
        }
    )

    controller._latest_song = (
        latest_song
    )

    controller._has_song = (
        lambda value: value is not None
    )

    controller._discord_buttons_for_mode = (
        lambda mode: BUTTONS
    )

    return (
        controller,
        legacy,
        manager,
        events,
    )


def first_index(
    events,
    prefix,
):
    for index, event in enumerate(
        events
    ):
        if event[
            :len(prefix)
        ] == prefix:
            return index

    raise AssertionError(
        "Missing event: "
        + repr(
            prefix
        )
    )


class DiscordPresenceMusicManagerHandoffTests(
    unittest.TestCase
):
    def test_constructor_remains_compatible_without_manager(
        self,
    ):
        legacy = FakeLegacyDiscord(
            []
        )

        controller = (
            PresenceController(
                legacy
            )
        )

        self.assertIs(
            controller.discord,
            legacy,
        )

        self.assertIsNone(
            controller.discord_session_manager
        )

    def test_constructor_accepts_manager(
        self,
    ):
        controller, _, manager, _ = (
            make_controller()
        )

        self.assertIs(
            controller.discord_session_manager,
            manager,
        )

    def test_music_apply_routes_to_manager(
        self,
    ):
        (
            controller,
            _,
            _,
            events,
        ) = make_controller(
            latest_song=make_song()
        )

        controller.apply_mode(
            PresenceMode(
                mode="music",
                application_entry_id=(
                    MUSIC_ENTRY_ID
                ),
            )
        )

        self.assertTrue(
            any(
                event[
                    :2
                ] == (
                    "manager",
                    "update_music",
                )
                for event in events
            )
        )

        self.assertFalse(
            any(
                event[
                    :2
                ] == (
                    "legacy",
                    "song",
                )
                for event in events
            )
        )

    def test_music_transition_closes_running_legacy_before_publish(
        self,
    ):
        (
            controller,
            legacy,
            _,
            events,
        ) = make_controller(
            latest_song=make_song()
        )

        legacy.is_connected = True
        legacy.is_running = True

        controller.apply_mode(
            PresenceMode(
                mode="music",
            )
        )

        self.assertLess(
            first_index(
                events,
                (
                    "legacy",
                    "close",
                ),
            ),
            first_index(
                events,
                (
                    "manager",
                    "update_music",
                ),
            ),
        )

    def test_music_forwards_persisted_assignment_buttons_and_loop_state(
        self,
    ):
        (
            controller,
            _,
            _,
            events,
        ) = make_controller(
            latest_song=make_song()
        )

        controller.apply_mode(
            PresenceMode(
                mode="music",
                application_entry_id=None,
                show_loop_count=True,
            )
        )

        update = next(
            event
            for event in events
            if event[
                :2
            ] == (
                "manager",
                "update_music",
            )
        )

        self.assertEqual(
            update[
                2
            ],
            MUSIC_ENTRY_ID,
        )

        self.assertEqual(
            update[
                4
            ],
            BUTTONS,
        )

        self.assertIs(
            update[
                5
            ],
            True,
        )

    def test_music_without_song_ensures_and_clears_lane(
        self,
    ):
        (
            controller,
            _,
            _,
            events,
        ) = make_controller(
            latest_song=None
        )

        controller.apply_mode(
            PresenceMode(
                mode="music",
            )
        )

        self.assertIn(
            (
                "manager",
                "ensure",
                MUSIC_LANE_ID,
                MUSIC_ENTRY_ID,
            ),
            events,
        )

        self.assertIn(
            (
                "manager",
                "clear",
                MUSIC_LANE_ID,
            ),
            events,
        )

    def test_manager_failure_never_falls_back_to_legacy_music(
        self,
    ):
        (
            controller,
            _,
            manager,
            events,
        ) = make_controller(
            latest_song=make_song()
        )

        manager.update_result = False

        controller.apply_mode(
            PresenceMode(
                mode="music",
            )
        )

        self.assertFalse(
            any(
                event[
                    :2
                ] in {
                    (
                        "legacy",
                        "connect",
                    ),
                    (
                        "legacy",
                        "song",
                    ),
                    (
                        "legacy",
                        "custom",
                    ),
                }
                for event in events
            )
        )

    def test_legacy_shutdown_failure_blocks_music_manager_publish(
        self,
    ):
        (
            controller,
            legacy,
            _,
            events,
        ) = make_controller(
            latest_song=make_song()
        )

        legacy.is_connected = True
        legacy.is_running = True
        legacy.fail_close = True

        controller.apply_mode(
            PresenceMode(
                mode="music",
            )
        )

        self.assertFalse(
            any(
                event[
                    :2
                ] == (
                    "manager",
                    "update_music",
                )
                for event in events
            )
        )

        self.assertIn(
            (
                "manager",
                "release",
                MUSIC_LANE_ID,
            ),
            events,
        )

    def test_custom_releases_music_before_legacy_publish(
        self,
    ):
        (
            controller,
            _,
            _,
            events,
        ) = make_controller()

        controller.apply_mode(
            PresenceMode(
                mode="custom",
                title="Custom",
                message="Status",
            )
        )

        self.assertLess(
            first_index(
                events,
                (
                    "manager",
                    "release",
                ),
            ),
            first_index(
                events,
                (
                    "legacy",
                    "connect",
                ),
            ),
        )

        self.assertLess(
            first_index(
                events,
                (
                    "legacy",
                    "connect",
                ),
            ),
            first_index(
                events,
                (
                    "legacy",
                    "custom",
                ),
            ),
        )

    def test_music_release_failure_blocks_custom_legacy_start(
        self,
    ):
        (
            controller,
            _,
            manager,
            events,
        ) = make_controller()

        manager.release_result = False

        controller.apply_mode(
            PresenceMode(
                mode="custom",
                title="Custom",
                message="Status",
            )
        )

        self.assertFalse(
            any(
                event[
                    :2
                ] in {
                    (
                        "legacy",
                        "connect",
                    ),
                    (
                        "legacy",
                        "custom",
                    ),
                }
                for event in events
            )
        )

    def test_disabled_attempts_both_shutdown_paths(
        self,
    ):
        (
            controller,
            legacy,
            _,
            events,
        ) = make_controller()

        legacy.is_connected = True
        legacy.is_running = True

        controller.apply_mode(
            PresenceMode(
                mode="disabled"
            )
        )

        self.assertIn(
            (
                "manager",
                "release",
                MUSIC_LANE_ID,
            ),
            events,
        )

        self.assertIn(
            (
                "legacy",
                "close",
            ),
            events,
        )

    def test_handle_song_routes_to_manager(
        self,
    ):
        (
            controller,
            _,
            _,
            events,
        ) = make_controller()

        current = make_song()

        controller.handle_song(
            current
        )

        update = next(
            event
            for event in events
            if event[
                :2
            ] == (
                "manager",
                "update_music",
            )
        )

        self.assertIs(
            update[
                3
            ],
            current,
        )

    def test_handle_song_none_clears_music_lane(
        self,
    ):
        (
            controller,
            _,
            _,
            events,
        ) = make_controller()

        controller.handle_song(
            None
        )

        self.assertIn(
            (
                "manager",
                "ensure",
                MUSIC_LANE_ID,
                MUSIC_ENTRY_ID,
            ),
            events,
        )

        self.assertIn(
            (
                "manager",
                "clear",
                MUSIC_LANE_ID,
            ),
            events,
        )

    def test_loop_toggle_routes_active_music_to_manager(
        self,
    ):
        (
            controller,
            _,
            _,
            events,
        ) = make_controller(
            latest_song=make_song()
        )

        controller.set_music_loop_count_enabled(
            True
        )

        update = next(
            event
            for event in events
            if event[
                :2
            ] == (
                "manager",
                "update_music",
            )
        )

        self.assertIs(
            update[
                5
            ],
            True,
        )

        self.assertFalse(
            any(
                event[
                    :2
                ] == (
                    "legacy",
                    "loop",
                )
                for event in events
            )
        )

    def test_loop_toggle_without_song_keeps_lane_clear(
        self,
    ):
        (
            controller,
            _,
            _,
            events,
        ) = make_controller(
            latest_song=None
        )

        controller.set_music_loop_count_enabled(
            True
        )

        self.assertIn(
            (
                "manager",
                "clear",
                MUSIC_LANE_ID,
            ),
            events,
        )

    def test_auto_afk_releases_music_before_legacy_publish(
        self,
    ):
        (
            controller,
            _,
            _,
            events,
        ) = make_controller(
            active_mode="music"
        )

        controller.enter_auto_afk()

        self.assertLess(
            first_index(
                events,
                (
                    "manager",
                    "release",
                ),
            ),
            first_index(
                events,
                (
                    "legacy",
                    "connect",
                ),
            ),
        )

        self.assertLess(
            first_index(
                events,
                (
                    "legacy",
                    "connect",
                ),
            ),
            first_index(
                events,
                (
                    "legacy",
                    "custom",
                ),
            ),
        )

    def test_auto_afk_release_failure_blocks_legacy_publish(
        self,
    ):
        (
            controller,
            _,
            manager,
            events,
        ) = make_controller(
            active_mode="music"
        )

        manager.release_result = False

        controller.enter_auto_afk()

        self.assertFalse(
            any(
                event[
                    :2
                ] in {
                    (
                        "legacy",
                        "connect",
                    ),
                    (
                        "legacy",
                        "custom",
                    ),
                }
                for event in events
            )
        )

    def test_leave_auto_afk_restores_music_manager_route(
        self,
    ):
        (
            controller,
            legacy,
            _,
            events,
        ) = make_controller(
            active_mode="music",
            latest_song=make_song(),
        )

        legacy.is_connected = True
        legacy.is_running = True

        controller._auto_afk_active = True
        controller._mode_before_auto_afk = (
            "music"
        )

        controller.leave_auto_afk()

        self.assertFalse(
            controller.auto_afk_active
        )

        self.assertTrue(
            any(
                event[
                    :2
                ] == (
                    "manager",
                    "update_music",
                )
                for event in events
            )
        )

    def test_no_manager_custom_path_preserves_legacy_behavior(
        self,
    ):
        (
            controller,
            _,
            _,
            events,
        ) = make_controller(
            with_manager=False
        )

        controller.apply_mode(
            PresenceMode(
                mode="custom",
                title="Custom",
                message="Status",
            )
        )

        self.assertTrue(
            any(
                event[
                    :2
                ] == (
                    "legacy",
                    "custom",
                )
                for event in events
            )
        )

    def test_no_manager_music_path_preserves_legacy_behavior(
        self,
    ):
        (
            controller,
            _,
            _,
            events,
        ) = make_controller(
            with_manager=False,
            latest_song=make_song(),
        )

        controller.apply_mode(
            PresenceMode(
                mode="music",
                show_loop_count=True,
            )
        )

        self.assertIn(
            (
                "legacy",
                "loop",
                True,
            ),
            events,
        )

        self.assertTrue(
            any(
                event[
                    :2
                ] == (
                    "legacy",
                    "song",
                )
                for event in events
            )
        )

    def test_missing_reference_is_forwarded_without_global_fallback(
        self,
    ):
        (
            controller,
            _,
            manager,
            events,
        ) = make_controller(
            application_entry_id=(
                MISSING_ENTRY_ID
            ),
            latest_song=make_song(),
        )

        manager.update_result = False

        controller.apply_mode(
            PresenceMode(
                mode="music",
                application_entry_id=None,
            )
        )

        update = next(
            event
            for event in events
            if event[
                :2
            ] == (
                "manager",
                "update_music",
            )
        )

        self.assertEqual(
            update[
                2
            ],
            MISSING_ENTRY_ID,
        )

        self.assertFalse(
            any(
                event[
                    :2
                ] in {
                    (
                        "legacy",
                        "connect",
                    ),
                    (
                        "legacy",
                        "song",
                    ),
                }
                for event in events
            )
        )

    def test_main_window_status_snapshot_uses_active_transport(
        self,
    ):
        events = []

        manager = FakeManager(
            events
        )

        legacy = FakeLegacyDiscord(
            events
        )

        legacy.profile_identity = {
            "username": "Legacy",
        }

        controller = SimpleNamespace(
            active_mode="music",
            auto_afk_active=False,
        )

        shell = SimpleNamespace(
            presence_controller=controller,
            discord_session_manager=manager,
            discord=legacy,
        )

        self.assertEqual(
            MainWindow._discord_status_snapshot(
                shell
            ),
            (
                {
                    "username": "Music",
                },
                True,
                True,
            ),
        )

        controller.active_mode = (
            "custom"
        )

        legacy.is_connected = False
        legacy.is_running = True

        self.assertEqual(
            MainWindow._discord_status_snapshot(
                shell
            ),
            (
                {
                    "username": "Legacy",
                },
                False,
                True,
            ),
        )

        controller.active_mode = (
            "music"
        )

        controller.auto_afk_active = (
            True
        )

        self.assertEqual(
            MainWindow._discord_status_snapshot(
                shell
            ),
            (
                {
                    "username": "Legacy",
                },
                False,
                True,
            ),
        )


if __name__ == "__main__":
    unittest.main()
