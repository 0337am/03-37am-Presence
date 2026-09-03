from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY_ID,
)
from src.discord.presence_controller import (
    PresenceController,
)
from src.discord.presence_modes import (
    PresenceMode,
)
from src.discord.session_manager import (
    MUSIC_LANE_ID,
    SECONDARY_LANE_ID,
)


USER_ENTRY_ID = (
    "discord_app_0123456789abcdef"
)

MISSING_ENTRY_ID = (
    "discord_app_aaaaaaaaaaaaaaaa"
)

BUTTONS = [
    {
        "label": "Open",
        "url": "https://example.com",
    }
]


class FakeSignal:
    def __init__(
        self,
    ):
        self.values = []

    def emit(
        self,
        value,
    ):
        self.values.append(
            value
        )


class FakeManager:
    def __init__(
        self,
        events,
    ):
        self.events = events
        self.update_result = True
        self.release_result = True
        self.raise_update = False
        self.raise_release = False

    def update_secondary(
        self,
        application_entry_id,
        *,
        title,
        message,
        image_bytes=None,
        image_name="",
        show_elapsed=False,
        buttons=None,
        party_size=None,
    ):
        self.events.append(
            (
                "manager",
                "update_secondary",
                application_entry_id,
                title,
                message,
                image_bytes,
                image_name,
                show_elapsed,
                buttons,
                party_size,
            )
        )

        if self.raise_update:
            raise RuntimeError(
                "secondary publish failed"
            )

        return self.update_result

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

        if self.raise_release:
            raise RuntimeError(
                "release failed"
            )

        return self.release_result


class FakeLegacyDiscord:
    def __init__(
        self,
        events,
    ):
        self.events = events

    def connect(
        self,
    ):
        self.events.append(
            (
                "legacy",
                "connect",
            )
        )

        return True

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

    def clear_presence(
        self,
    ):
        self.events.append(
            (
                "legacy",
                "clear",
            )
        )

    def close(
        self,
    ):
        self.events.append(
            (
                "legacy",
                "close",
            )
        )


def make_mode(
    *,
    mode="custom",
    entry_id=USER_ENTRY_ID,
    title="Floor 35",
    message="Solo",
    show_elapsed=False,
    show_party=False,
):
    return PresenceMode(
        mode=mode,
        title=title,
        message=message,
        show_elapsed=show_elapsed,
        show_party=show_party,
        party_current=1,
        party_maximum=1,
        application_entry_id=entry_id,
    )


def make_controller(
    *,
    with_manager=True,
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

    controller._discord_buttons_for_mode = (
        lambda mode: BUTTONS
    )

    return (
        controller,
        manager,
        events,
    )


def event_index(
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


class DiscordPresenceSecondaryCoordinatorTests(
    unittest.TestCase
):
    def test_constructor_starts_without_secondary_presence(
        self,
    ):
        controller, _, _ = (
            make_controller()
        )

        self.assertIsNone(
            controller.secondary_presence_mode
        )

        self.assertIsNone(
            controller.secondary_mode
        )

    def test_secondary_presence_property_is_lightweight_shell_safe(
        self,
    ):
        shell = SimpleNamespace()

        self.assertIsNone(
            PresenceController
            .secondary_presence_mode
            .fget(
                shell
            )
        )

    def test_secondary_rejects_music_mode(
        self,
    ):
        controller, _, events = (
            make_controller()
        )

        self.assertFalse(
            controller.apply_secondary_mode(
                make_mode(
                    mode="music"
                )
            )
        )

        self.assertEqual(
            events,
            [],
        )

    def test_secondary_disabled_mode_clears_secondary_lane(
        self,
    ):
        controller, _, events = (
            make_controller()
        )

        controller._secondary_presence_mode = (
            make_mode()
        )

        self.assertTrue(
            controller.apply_secondary_mode(
                make_mode(
                    mode="disabled"
                )
            )
        )

        self.assertIn(
            (
                "manager",
                "release",
                SECONDARY_LANE_ID,
            ),
            events,
        )

        self.assertIsNone(
            controller.secondary_presence_mode
        )

    def test_secondary_requires_manager_and_never_falls_back_to_legacy(
        self,
    ):
        controller, _, events = (
            make_controller(
                with_manager=False
            )
        )

        self.assertFalse(
            controller.apply_secondary_mode(
                make_mode()
            )
        )

        self.assertEqual(
            events,
            [],
        )

    def test_secondary_routes_custom_payload_to_manager(
        self,
    ):
        controller, _, events = (
            make_controller()
        )

        self.assertTrue(
            controller.apply_secondary_mode(
                make_mode(
                    title="Floor 35",
                    message="Solo",
                )
            )
        )

        update = next(
            event
            for event in events
            if event[
                :2
            ] == (
                "manager",
                "update_secondary",
            )
        )

        self.assertEqual(
            update[
                2
            ],
            USER_ENTRY_ID,
        )

        self.assertEqual(
            update[
                3
            ],
            "Floor 35",
        )

        self.assertEqual(
            update[
                4
            ],
            "Solo",
        )

    def test_secondary_forwards_buttons(
        self,
    ):
        controller, _, events = (
            make_controller()
        )

        controller.apply_secondary_mode(
            make_mode()
        )

        update = next(
            event
            for event in events
            if event[
                :2
            ] == (
                "manager",
                "update_secondary",
            )
        )

        self.assertEqual(
            update[
                8
            ],
            BUTTONS,
        )

    def test_secondary_forwards_elapsed_setting(
        self,
    ):
        controller, _, events = (
            make_controller()
        )

        controller.apply_secondary_mode(
            make_mode(
                show_elapsed=True
            )
        )

        update = next(
            event
            for event in events
            if event[
                :2
            ] == (
                "manager",
                "update_secondary",
            )
        )

        self.assertIs(
            update[
                7
            ],
            True,
        )

    def test_secondary_forwards_party_size(
        self,
    ):
        controller, _, events = (
            make_controller()
        )

        controller.apply_secondary_mode(
            make_mode(
                show_party=True
            )
        )

        update = next(
            event
            for event in events
            if event[
                :2
            ] == (
                "manager",
                "update_secondary",
            )
        )

        self.assertEqual(
            update[
                9
            ],
            [
                1,
                1,
            ],
        )

    def test_secondary_none_assignment_uses_builtin_reference(
        self,
    ):
        controller, _, events = (
            make_controller()
        )

        controller.apply_secondary_mode(
            make_mode(
                entry_id=None
            )
        )

        update = next(
            event
            for event in events
            if event[
                :2
            ] == (
                "manager",
                "update_secondary",
            )
        )

        self.assertEqual(
            update[
                2
            ],
            BUILTIN_APPLICATION_ENTRY_ID,
        )

    def test_missing_reference_is_forwarded_without_substitution(
        self,
    ):
        controller, _, events = (
            make_controller()
        )

        controller.apply_secondary_mode(
            make_mode(
                entry_id=MISSING_ENTRY_ID
            )
        )

        update = next(
            event
            for event in events
            if event[
                :2
            ] == (
                "manager",
                "update_secondary",
            )
        )

        self.assertEqual(
            update[
                2
            ],
            MISSING_ENTRY_ID,
        )

    def test_failed_secondary_publish_releases_requested_lane(
        self,
    ):
        controller, manager, events = (
            make_controller()
        )

        manager.update_result = False

        self.assertFalse(
            controller.apply_secondary_mode(
                make_mode()
            )
        )

        self.assertIn(
            (
                "manager",
                "release",
                SECONDARY_LANE_ID,
            ),
            events,
        )

        self.assertIsNone(
            controller.secondary_presence_mode
        )

    def test_secondary_publish_exception_fails_closed(
        self,
    ):
        controller, manager, events = (
            make_controller()
        )

        manager.raise_update = True

        self.assertFalse(
            controller.apply_secondary_mode(
                make_mode()
            )
        )

        self.assertIn(
            (
                "manager",
                "release",
                SECONDARY_LANE_ID,
            ),
            events,
        )

    def test_successful_secondary_apply_tracks_runtime_mode(
        self,
    ):
        controller, _, _ = (
            make_controller()
        )

        mode = make_mode(
            mode="working",
            title="Working",
        )

        self.assertTrue(
            controller.apply_secondary_mode(
                mode
            )
        )

        self.assertIs(
            controller.secondary_presence_mode,
            mode,
        )

        self.assertEqual(
            controller.secondary_mode,
            "working",
        )

    def test_secondary_apply_emits_secondary_signal(
        self,
    ):
        controller, _, _ = (
            make_controller()
        )

        values = []

        controller.secondary_mode_changed.connect(
            values.append
        )

        self.assertTrue(
            controller.apply_secondary_mode(
                make_mode()
            )
        )

        self.assertEqual(
            len(
                values
            ),
            1,
        )

        self.assertEqual(
            values[
                0
            ][
                "mode"
            ],
            "custom",
        )

    def test_failed_secondary_apply_does_not_emit_active_state(
        self,
    ):
        controller, manager, _ = (
            make_controller()
        )

        values = []

        controller.secondary_mode_changed.connect(
            values.append
        )

        manager.update_result = False

        self.assertFalse(
            controller.apply_secondary_mode(
                make_mode()
            )
        )

        self.assertEqual(
            values,
            [],
        )

    def test_clear_secondary_releases_only_secondary_lane(
        self,
    ):
        controller, _, events = (
            make_controller()
        )

        controller._secondary_presence_mode = (
            make_mode()
        )

        self.assertTrue(
            controller.clear_secondary_mode()
        )

        self.assertEqual(
            events,
            [
                (
                    "manager",
                    "release",
                    SECONDARY_LANE_ID,
                )
            ],
        )

    def test_failed_clear_keeps_tracked_secondary_state(
        self,
    ):
        controller, manager, _ = (
            make_controller()
        )

        mode = make_mode()

        controller._secondary_presence_mode = (
            mode
        )

        manager.release_result = False

        self.assertFalse(
            controller.clear_secondary_mode()
        )

        self.assertIs(
            controller.secondary_presence_mode,
            mode,
        )

    def test_music_apply_does_not_clear_secondary_lane(
        self,
    ):
        events = []

        shell = SimpleNamespace(
            _auto_afk_active=False,
            _mode_before_auto_afk=None,
            _latest_song=None,
            discord_session_manager=object(),
            save_mode=lambda mode: events.append(
                (
                    "controller",
                    "save",
                )
            ),
            _stop_legacy_discord=lambda: True,
            load_mode=lambda mode: PresenceMode(
                mode="music"
            ),
            _publish_music_with_manager=(
                lambda mode, song: events.append(
                    (
                        "manager",
                        "music",
                    )
                )
            ),
            _release_music_lane=lambda: (
                events.append(
                    (
                        "manager",
                        "release_music",
                    )
                )
                or True
            ),
            clear_secondary_mode=lambda: (
                events.append(
                    (
                        "manager",
                        "clear_secondary",
                    )
                )
                or True
            ),
            mode_changed=FakeSignal(),
        )

        PresenceController.apply_mode(
            shell,
            PresenceMode(
                mode="music"
            ),
        )

        self.assertNotIn(
            (
                "manager",
                "clear_secondary",
            ),
            events,
        )

        self.assertIn(
            (
                "manager",
                "music",
            ),
            events,
        )

    def test_exclusive_custom_clears_secondary_before_music_and_legacy(
        self,
    ):
        events = []

        legacy = FakeLegacyDiscord(
            events
        )

        shell = SimpleNamespace(
            _auto_afk_active=False,
            _mode_before_auto_afk=None,
            discord_session_manager=object(),
            save_mode=lambda mode: events.append(
                (
                    "controller",
                    "save",
                )
            ),
            clear_secondary_mode=lambda: (
                events.append(
                    (
                        "manager",
                        "clear_secondary",
                    )
                )
                or True
            ),
            _release_music_lane=lambda: (
                events.append(
                    (
                        "manager",
                        "release_music",
                    )
                )
                or True
            ),
            _start_legacy_discord=lambda: (
                events.append(
                    (
                        "legacy",
                        "start",
                    )
                )
                or True
            ),
            _discord_buttons_for_mode=(
                lambda mode: BUTTONS
            ),
            discord=legacy,
            mode_changed=FakeSignal(),
        )

        PresenceController.apply_mode(
            shell,
            make_mode(),
        )

        secondary_index = event_index(
            events,
            (
                "manager",
                "clear_secondary",
            ),
        )

        music_index = event_index(
            events,
            (
                "manager",
                "release_music",
            ),
        )

        legacy_index = event_index(
            events,
            (
                "legacy",
                "start",
            ),
        )

        self.assertLess(
            secondary_index,
            music_index,
        )

        self.assertLess(
            music_index,
            legacy_index,
        )

    def test_failed_secondary_clear_blocks_exclusive_legacy_start(
        self,
    ):
        events = []

        shell = SimpleNamespace(
            _auto_afk_active=False,
            _mode_before_auto_afk=None,
            discord_session_manager=object(),
            save_mode=lambda mode: None,
            clear_secondary_mode=lambda: False,
            _release_music_lane=lambda: (
                events.append(
                    (
                        "manager",
                        "release_music",
                    )
                )
                or True
            ),
            _start_legacy_discord=lambda: (
                events.append(
                    (
                        "legacy",
                        "start",
                    )
                )
                or True
            ),
            _discord_buttons_for_mode=(
                lambda mode: BUTTONS
            ),
            discord=FakeLegacyDiscord(
                events
            ),
            mode_changed=FakeSignal(),
        )

        PresenceController.apply_mode(
            shell,
            make_mode(),
        )

        self.assertNotIn(
            (
                "manager",
                "release_music",
            ),
            events,
        )

        self.assertNotIn(
            (
                "legacy",
                "start",
            ),
            events,
        )

    def test_disabled_mode_clears_secondary_and_music(
        self,
    ):
        events = []

        shell = SimpleNamespace(
            _auto_afk_active=False,
            _mode_before_auto_afk=None,
            discord_session_manager=object(),
            save_mode=lambda mode: None,
            clear_secondary_mode=lambda: (
                events.append(
                    (
                        "manager",
                        "clear_secondary",
                    )
                )
                or True
            ),
            _release_music_lane=lambda: (
                events.append(
                    (
                        "manager",
                        "release_music",
                    )
                )
                or True
            ),
            _stop_legacy_discord=lambda: (
                events.append(
                    (
                        "legacy",
                        "stop",
                    )
                )
                or True
            ),
            mode_changed=FakeSignal(),
        )

        PresenceController.apply_mode(
            shell,
            PresenceMode(
                mode="disabled"
            ),
        )

        self.assertIn(
            (
                "manager",
                "clear_secondary",
            ),
            events,
        )

        self.assertIn(
            (
                "manager",
                "release_music",
            ),
            events,
        )

        self.assertIn(
            (
                "legacy",
                "stop",
            ),
            events,
        )

    def test_secondary_apply_does_not_write_primary_active_mode(
        self,
    ):
        controller, _, _ = (
            make_controller()
        )

        def forbidden_save(
            mode,
        ):
            raise AssertionError(
                "Secondary runtime must not "
                "overwrite primary active mode."
            )

        controller.save_mode = (
            forbidden_save
        )

        self.assertTrue(
            controller.apply_secondary_mode(
                make_mode()
            )
        )

    def test_failed_secondary_replacement_clears_stale_runtime_state(
        self,
    ):
        controller, manager, events = (
            make_controller()
        )

        original = make_mode(
            title="Original",
            message="Still active",
        )

        self.assertTrue(
            controller.apply_secondary_mode(
                original
            )
        )

        self.assertIs(
            controller.secondary_presence_mode,
            original,
        )

        emitted = []

        controller.secondary_mode_changed.connect(
            emitted.append
        )

        events.clear()

        manager.update_result = False

        replacement = make_mode(
            title="Replacement",
            message="Should fail",
        )

        self.assertFalse(
            controller.apply_secondary_mode(
                replacement
            )
        )

        self.assertIsNone(
            controller.secondary_presence_mode
        )

        self.assertIsNone(
            controller.secondary_mode
        )

        self.assertEqual(
            emitted,
            [
                {},
            ],
        )

        self.assertIn(
            (
                "manager",
                "release",
                SECONDARY_LANE_ID,
            ),
            events,
        )


if __name__ == "__main__":
    unittest.main()
