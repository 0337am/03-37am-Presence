from __future__ import annotations

import ast
import unittest
from pathlib import Path

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY,
    BUILTIN_APPLICATION_ENTRY_ID,
    DiscordApplicationEntry,
)
from src.discord.session_manager import (
    DISCORD_PRESENCE_LANE_IDS,
    MUSIC_LANE_ID,
    SECONDARY_LANE_ID,
    DiscordPresenceSessionManager,
    DiscordPresenceSessionManagerError,
)


USER_ENTRY_ID = (
    "discord_app_0123456789abcdef"
)

SECOND_ENTRY_ID = (
    "discord_app_fedcba9876543210"
)

USER_APPLICATION_ID = (
    "1096663809097203752"
)

SECOND_APPLICATION_ID = (
    "1523801127962022071"
)


def entry(
    entry_id=USER_ENTRY_ID,
    application_id=USER_APPLICATION_ID,
    name="Example",
):
    return DiscordApplicationEntry(
        entry_id=entry_id,
        name=name,
        application_id=application_id,
    )


class FakeSession:
    def __init__(
        self,
        client_id,
        *,
        connect_result=True,
        connect_error=False,
        update_song_error=False,
        update_custom_error=False,
        clear_error=False,
        close_error=False,
    ):
        self.client_id = client_id
        self.connect_result = connect_result
        self.connect_error = connect_error

        self.update_song_error = (
            update_song_error
        )

        self.update_custom_error = (
            update_custom_error
        )

        self.clear_error = clear_error
        self.close_error = close_error

        self.connect_count = 0
        self.clear_count = 0
        self.close_count = 0

        self.song_updates = []
        self.custom_updates = []

    def connect(self):
        self.connect_count += 1

        if self.connect_error:
            raise RuntimeError(
                "connect failed"
            )

        return self.connect_result

    def update_song(
        self,
        song,
        *,
        buttons=None,
    ):
        if self.update_song_error:
            raise RuntimeError(
                "song update failed"
            )

        self.song_updates.append(
            (
                song,
                buttons,
            )
        )

    def update_custom(
        self,
        **payload,
    ):
        if self.update_custom_error:
            raise RuntimeError(
                "custom update failed"
            )

        self.custom_updates.append(
            dict(
                payload
            )
        )

    def clear_presence(self):
        self.clear_count += 1

        if self.clear_error:
            raise RuntimeError(
                "clear failed"
            )

    def close(self):
        self.close_count += 1

        if self.close_error:
            raise RuntimeError(
                "close failed"
            )


class FakeFactory:
    def __init__(self):
        self.sessions = []
        self.options = {}

    def configure(
        self,
        client_id,
        **options,
    ):
        self.options[
            client_id
        ] = dict(
            options
        )

    def __call__(
        self,
        *,
        client_id,
    ):
        session = FakeSession(
            client_id,
            **self.options.get(
                client_id,
                {},
            ),
        )

        self.sessions.append(
            session
        )

        return session


class MutableResolver:
    def __init__(
        self,
        entries=None,
    ):
        self.entries = dict(
            entries or {}
        )

        self.calls = []
        self.raise_error = False
        self.override = None

    def __call__(
        self,
        entry_id,
    ):
        self.calls.append(
            entry_id
        )

        if self.raise_error:
            raise RuntimeError(
                "resolver failed"
            )

        if self.override is not None:
            return self.override

        return self.entries.get(
            entry_id
        )


def manager_with(
    *entries,
):
    resolver = MutableResolver(
        {
            item.entry_id: item
            for item in entries
        }
    )

    factory = FakeFactory()

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


class DiscordPresenceSessionManagerBoundaryTests(
    unittest.TestCase
):
    def test_lane_set_is_intentionally_two_lanes(
        self,
    ):
        self.assertEqual(
            DISCORD_PRESENCE_LANE_IDS,
            (
                MUSIC_LANE_ID,
                SECONDARY_LANE_ID,
            ),
        )

    def test_constructor_requires_resolver(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            DiscordPresenceSessionManager(
                None
            )

    def test_constructor_requires_factory_when_supplied(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            DiscordPresenceSessionManager(
                lambda entry_id: None,
                session_factory=object(),
            )

    def test_source_owns_no_raw_rpc_or_ui(
        self,
    ):
        source = Path(
            "src/discord/session_manager.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        tree = ast.parse(
            source
        )

        imported_modules = []

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                imported_modules.extend(
                    alias.name.casefold()
                    for alias in node.names
                )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                imported_modules.append(
                    str(
                        node.module or ""
                    ).casefold()
                )

        self.assertFalse(
            any(
                module == "pypresence"
                or module.startswith(
                    "pypresence."
                )
                for module
                in imported_modules
            )
        )

        self.assertFalse(
            any(
                module == "src.ui"
                or module.startswith(
                    "src.ui."
                )
                for module
                in imported_modules
            )
        )

        lowered = source.casefold()

        self.assertNotIn(
            "request_client_id(",
            lowered,
        )

        self.assertNotIn(
            "qsettings",
            lowered,
        )

    def test_manager_does_not_create_its_own_thread_or_queue(
        self,
    ):
        source = Path(
            "src/discord/session_manager.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        tree = ast.parse(
            source
        )

        imported_modules = []

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                imported_modules.extend(
                    alias.name.casefold()
                    for alias in node.names
                )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                imported_modules.append(
                    str(
                        node.module or ""
                    ).casefold()
                )

        for forbidden in (
            "threading",
            "queue",
        ):
            self.assertFalse(
                any(
                    module == forbidden
                    or module.startswith(
                        forbidden + "."
                    )
                    for module
                    in imported_modules
                )
            )


class DiscordPresenceSessionManagerResolutionTests(
    unittest.TestCase
):
    def test_invalid_lane_is_rejected(
        self,
    ):
        manager, _, _ = manager_with(
            entry()
        )

        with self.assertRaises(
            DiscordPresenceSessionManagerError
        ):
            manager.ensure_lane(
                "third",
                USER_ENTRY_ID,
            )

    def test_invalid_entry_reference_fails_closed(
        self,
    ):
        manager, _, factory = manager_with(
            entry()
        )

        result = manager.ensure_lane(
            MUSIC_LANE_ID,
            "../../bad",
        )

        self.assertIsNone(
            result
        )

        self.assertEqual(
            factory.sessions,
            [],
        )

        self.assertIsNone(
            manager.binding_for_lane(
                MUSIC_LANE_ID
            )
        )

    def test_builtin_entry_can_bind(
        self,
    ):
        manager, resolver, factory = (
            manager_with(
                BUILTIN_APPLICATION_ENTRY
            )
        )

        binding = manager.ensure_lane(
            MUSIC_LANE_ID,
            BUILTIN_APPLICATION_ENTRY_ID,
        )

        self.assertIsNotNone(
            binding
        )

        self.assertEqual(
            binding.application_id,
            (
                BUILTIN_APPLICATION_ENTRY
                .application_id
            ),
        )

        self.assertEqual(
            resolver.calls,
            [
                BUILTIN_APPLICATION_ENTRY_ID,
            ],
        )

        self.assertEqual(
            factory.sessions[
                0
            ].client_id,
            (
                BUILTIN_APPLICATION_ENTRY
                .application_id
            ),
        )

    def test_user_entry_can_bind(
        self,
    ):
        manager, _, factory = manager_with(
            entry()
        )

        binding = manager.ensure_lane(
            SECONDARY_LANE_ID,
            USER_ENTRY_ID,
        )

        self.assertEqual(
            binding.application_entry_id,
            USER_ENTRY_ID,
        )

        self.assertEqual(
            binding.application_id,
            USER_APPLICATION_ID,
        )

        self.assertEqual(
            factory.sessions[
                0
            ].connect_count,
            1,
        )

    def test_resolver_none_fails_closed(
        self,
    ):
        manager, _, factory = (
            manager_with()
        )

        result = manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        self.assertIsNone(
            result
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

    def test_resolver_exception_fails_closed(
        self,
    ):
        manager, resolver, factory = (
            manager_with(
                entry()
            )
        )

        resolver.raise_error = True

        self.assertIsNone(
            manager.ensure_lane(
                MUSIC_LANE_ID,
                USER_ENTRY_ID,
            )
        )

        self.assertEqual(
            factory.sessions,
            [],
        )

    def test_resolver_wrong_type_fails_closed(
        self,
    ):
        manager, resolver, factory = (
            manager_with(
                entry()
            )
        )

        resolver.override = object()

        self.assertIsNone(
            manager.ensure_lane(
                MUSIC_LANE_ID,
                USER_ENTRY_ID,
            )
        )

        self.assertEqual(
            factory.sessions,
            [],
        )

    def test_resolver_wrong_entry_id_fails_closed(
        self,
    ):
        manager, resolver, factory = (
            manager_with(
                entry()
            )
        )

        resolver.override = entry(
            SECOND_ENTRY_ID,
            SECOND_APPLICATION_ID,
        )

        self.assertIsNone(
            manager.ensure_lane(
                MUSIC_LANE_ID,
                USER_ENTRY_ID,
            )
        )

        self.assertEqual(
            factory.sessions,
            [],
        )

    def test_factory_receives_resolved_application_id(
        self,
    ):
        manager, _, factory = manager_with(
            entry()
        )

        manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        self.assertEqual(
            [
                session.client_id
                for session
                in factory.sessions
            ],
            [
                USER_APPLICATION_ID,
            ],
        )

    def test_invalid_session_interface_fails_closed(
        self,
    ):
        resolver = MutableResolver(
            {
                USER_ENTRY_ID: entry(),
            }
        )

        manager = (
            DiscordPresenceSessionManager(
                resolver,
                session_factory=(
                    lambda *,
                    client_id: object()
                ),
            )
        )

        self.assertIsNone(
            manager.ensure_lane(
                MUSIC_LANE_ID,
                USER_ENTRY_ID,
            )
        )

        self.assertIsNone(
            manager.binding_for_lane(
                MUSIC_LANE_ID
            )
        )

    def test_connect_false_fails_closed_and_closes_candidate(
        self,
    ):
        manager, _, factory = manager_with(
            entry()
        )

        factory.configure(
            USER_APPLICATION_ID,
            connect_result=False,
        )

        self.assertIsNone(
            manager.ensure_lane(
                MUSIC_LANE_ID,
                USER_ENTRY_ID,
            )
        )

        self.assertEqual(
            factory.sessions[
                0
            ].close_count,
            1,
        )

        self.assertIsNone(
            manager.binding_for_lane(
                MUSIC_LANE_ID
            )
        )

    def test_connect_exception_fails_closed_and_closes_candidate(
        self,
    ):
        manager, _, factory = manager_with(
            entry()
        )

        factory.configure(
            USER_APPLICATION_ID,
            connect_error=True,
        )

        self.assertIsNone(
            manager.ensure_lane(
                MUSIC_LANE_ID,
                USER_ENTRY_ID,
            )
        )

        self.assertEqual(
            factory.sessions[
                0
            ].close_count,
            1,
        )

    def test_same_binding_reuses_session(
        self,
    ):
        manager, _, factory = manager_with(
            entry()
        )

        first = manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        second = manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            len(
                factory.sessions
            ),
            1,
        )

        self.assertEqual(
            factory.sessions[
                0
            ].connect_count,
            2,
        )

    def test_application_id_change_rebinds_same_entry(
        self,
    ):
        manager, resolver, factory = (
            manager_with(
                entry()
            )
        )

        manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        first_session = (
            factory.sessions[
                0
            ]
        )

        resolver.entries[
            USER_ENTRY_ID
        ] = entry(
            USER_ENTRY_ID,
            SECOND_APPLICATION_ID,
            "Renamed",
        )

        binding = manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        self.assertEqual(
            binding.application_id,
            SECOND_APPLICATION_ID,
        )

        self.assertEqual(
            first_session.clear_count,
            1,
        )

        self.assertEqual(
            first_session.close_count,
            1,
        )

        self.assertEqual(
            len(
                factory.sessions
            ),
            2,
        )

    def test_duplicate_application_id_is_rejected_across_lanes(
        self,
    ):
        shared_entry = entry()

        manager, _, factory = (
            manager_with(
                shared_entry
            )
        )

        music = manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        secondary = manager.ensure_lane(
            SECONDARY_LANE_ID,
            USER_ENTRY_ID,
        )

        self.assertIsNotNone(
            music
        )

        self.assertIsNone(
            secondary
        )

        self.assertIsNotNone(
            manager.binding_for_lane(
                MUSIC_LANE_ID
            )
        )

        self.assertIsNone(
            manager.binding_for_lane(
                SECONDARY_LANE_ID
            )
        )

        self.assertEqual(
            len(
                factory.sessions
            ),
            1,
        )

    def test_duplicate_request_releases_previous_secondary_lane(
        self,
    ):
        first = entry()

        second = entry(
            SECOND_ENTRY_ID,
            SECOND_APPLICATION_ID,
            "Second",
        )

        manager, _, factory = (
            manager_with(
                first,
                second,
            )
        )

        manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        manager.ensure_lane(
            SECONDARY_LANE_ID,
            SECOND_ENTRY_ID,
        )

        secondary_session = (
            factory.sessions[
                1
            ]
        )

        result = manager.ensure_lane(
            SECONDARY_LANE_ID,
            USER_ENTRY_ID,
        )

        self.assertIsNone(
            result
        )

        self.assertEqual(
            secondary_session.clear_count,
            1,
        )

        self.assertEqual(
            secondary_session.close_count,
            1,
        )

        self.assertIsNotNone(
            manager.binding_for_lane(
                MUSIC_LANE_ID
            )
        )


class DiscordPresenceSessionManagerUpdateTests(
    unittest.TestCase
):
    def test_music_update_routes_song_and_buttons(
        self,
    ):
        manager, _, factory = manager_with(
            entry()
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
                USER_ENTRY_ID,
                song,
                buttons=buttons,
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

    def test_secondary_update_routes_complete_payload(
        self,
    ):
        manager, _, factory = manager_with(
            entry()
        )

        image_bytes = b"image"

        buttons = [
            {
                "label": "Open",
                "url": "https://example.com",
            }
        ]

        self.assertTrue(
            manager.update_secondary(
                USER_ENTRY_ID,
                title="Floor 35",
                message="Solo",
                image_bytes=image_bytes,
                image_name="Sword Art Online",
                show_elapsed=True,
                buttons=buttons,
                party_size=[
                    1,
                    1,
                ],
            )
        )

        self.assertEqual(
            factory.sessions[
                0
            ].custom_updates,
            [
                {
                    "title": "Floor 35",
                    "message": "Solo",
                    "image_bytes": image_bytes,
                    "image_name": "Sword Art Online",
                    "show_elapsed": True,
                    "buttons": buttons,
                    "party_size": [
                        1,
                        1,
                    ],
                }
            ],
        )

    def test_clear_lane_is_independent(
        self,
    ):
        first = entry()

        second = entry(
            SECOND_ENTRY_ID,
            SECOND_APPLICATION_ID,
            "Second",
        )

        manager, _, factory = (
            manager_with(
                first,
                second,
            )
        )

        manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        manager.ensure_lane(
            SECONDARY_LANE_ID,
            SECOND_ENTRY_ID,
        )

        self.assertTrue(
            manager.clear_lane(
                SECONDARY_LANE_ID
            )
        )

        self.assertEqual(
            factory.sessions[
                0
            ].clear_count,
            0,
        )

        self.assertEqual(
            factory.sessions[
                1
            ].clear_count,
            1,
        )

        self.assertIsNotNone(
            manager.binding_for_lane(
                MUSIC_LANE_ID
            )
        )

    def test_release_lane_is_independent(
        self,
    ):
        first = entry()

        second = entry(
            SECOND_ENTRY_ID,
            SECOND_APPLICATION_ID,
            "Second",
        )

        manager, _, factory = (
            manager_with(
                first,
                second,
            )
        )

        manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        manager.ensure_lane(
            SECONDARY_LANE_ID,
            SECOND_ENTRY_ID,
        )

        self.assertTrue(
            manager.release_lane(
                SECONDARY_LANE_ID
            )
        )

        self.assertIsNotNone(
            manager.binding_for_lane(
                MUSIC_LANE_ID
            )
        )

        self.assertIsNone(
            manager.binding_for_lane(
                SECONDARY_LANE_ID
            )
        )

        self.assertEqual(
            factory.sessions[
                0
            ].close_count,
            0,
        )

        self.assertEqual(
            factory.sessions[
                1
            ].close_count,
            1,
        )

    def test_secondary_update_failure_does_not_touch_music(
        self,
    ):
        first = entry()

        second = entry(
            SECOND_ENTRY_ID,
            SECOND_APPLICATION_ID,
            "Second",
        )

        manager, _, factory = (
            manager_with(
                first,
                second,
            )
        )

        manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        manager.ensure_lane(
            SECONDARY_LANE_ID,
            SECOND_ENTRY_ID,
        )

        factory.sessions[
            1
        ].update_custom_error = True

        self.assertFalse(
            manager.update_secondary(
                SECOND_ENTRY_ID,
                title="Floor 35",
                message="Solo",
            )
        )

        self.assertIsNotNone(
            manager.binding_for_lane(
                MUSIC_LANE_ID
            )
        )

        self.assertEqual(
            factory.sessions[
                0
            ].clear_count,
            0,
        )

        self.assertEqual(
            factory.sessions[
                0
            ].close_count,
            0,
        )

    def test_music_update_failure_does_not_touch_secondary(
        self,
    ):
        first = entry()

        second = entry(
            SECOND_ENTRY_ID,
            SECOND_APPLICATION_ID,
            "Second",
        )

        manager, _, factory = (
            manager_with(
                first,
                second,
            )
        )

        manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        manager.ensure_lane(
            SECONDARY_LANE_ID,
            SECOND_ENTRY_ID,
        )

        factory.sessions[
            0
        ].update_song_error = True

        self.assertFalse(
            manager.update_music(
                USER_ENTRY_ID,
                object(),
            )
        )

        self.assertIsNotNone(
            manager.binding_for_lane(
                SECONDARY_LANE_ID
            )
        )

        self.assertEqual(
            factory.sessions[
                1
            ].clear_count,
            0,
        )

        self.assertEqual(
            factory.sessions[
                1
            ].close_count,
            0,
        )

    def test_close_releases_both_and_is_idempotent(
        self,
    ):
        first = entry()

        second = entry(
            SECOND_ENTRY_ID,
            SECOND_APPLICATION_ID,
            "Second",
        )

        manager, _, factory = (
            manager_with(
                first,
                second,
            )
        )

        manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        manager.ensure_lane(
            SECONDARY_LANE_ID,
            SECOND_ENTRY_ID,
        )

        self.assertTrue(
            manager.close()
        )

        self.assertTrue(
            manager.close()
        )

        self.assertTrue(
            manager.is_closed
        )

        for session in factory.sessions:
            self.assertEqual(
                session.clear_count,
                1,
            )

            self.assertEqual(
                session.close_count,
                1,
            )

    def test_closed_manager_rejects_new_binding(
        self,
    ):
        manager, _, factory = (
            manager_with(
                entry()
            )
        )

        manager.close()

        self.assertIsNone(
            manager.ensure_lane(
                MUSIC_LANE_ID,
                USER_ENTRY_ID,
            )
        )

        self.assertEqual(
            factory.sessions,
            [],
        )

    def test_active_bindings_use_fixed_lane_order(
        self,
    ):
        first = entry()

        second = entry(
            SECOND_ENTRY_ID,
            SECOND_APPLICATION_ID,
            "Second",
        )

        manager, _, _ = manager_with(
            first,
            second,
        )

        manager.ensure_lane(
            SECONDARY_LANE_ID,
            SECOND_ENTRY_ID,
        )

        manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        self.assertEqual(
            [
                binding.lane_id
                for binding
                in manager.active_bindings()
            ],
            [
                MUSIC_LANE_ID,
                SECONDARY_LANE_ID,
            ],
        )

    def test_last_error_is_lane_scoped(
        self,
    ):
        first = entry()

        second = entry(
            SECOND_ENTRY_ID,
            SECOND_APPLICATION_ID,
            "Second",
        )

        manager, _, factory = (
            manager_with(
                first,
                second,
            )
        )

        manager.ensure_lane(
            MUSIC_LANE_ID,
            USER_ENTRY_ID,
        )

        manager.ensure_lane(
            SECONDARY_LANE_ID,
            SECOND_ENTRY_ID,
        )

        factory.sessions[
            1
        ].update_custom_error = True

        manager.update_secondary(
            SECOND_ENTRY_ID,
            title="Floor 35",
            message="Solo",
        )

        self.assertEqual(
            manager.last_error_for_lane(
                MUSIC_LANE_ID
            ),
            "",
        )

        self.assertTrue(
            manager.last_error_for_lane(
                SECONDARY_LANE_ID
            )
        )


if __name__ == "__main__":
    unittest.main()
