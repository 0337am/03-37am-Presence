from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY,
    BUILTIN_APPLICATION_ENTRY_ID,
    DiscordApplicationEntry,
)
from src.discord.application_library_migration import (
    LEGACY_ASSIGNABLE_PRESENCE_MODES,
    migrate_legacy_discord_identity_to_presence_assignments,
)
from src.discord.identity_preferences import (
    IDENTITY_MODE_CUSTOM,
    IDENTITY_MODE_DEFAULT,
    DiscordIdentityPreferences,
)


USER_ENTRY = DiscordApplicationEntry(
    entry_id="discord_app_0123456789abcdef",
    name="Legacy Application",
    application_id="123456789012345678",
)

EXPLICIT_ENTRY_ID = (
    "discord_app_fedcba9876543210"
)


class _MemorySettings:
    def __init__(
        self,
        values=None,
        *,
        fail_contains=False,
        fail_set=False,
        fail_sync=False,
    ):
        self.values = dict(
            values or {}
        )

        self.fail_contains = bool(
            fail_contains
        )

        self.fail_set = bool(
            fail_set
        )

        self.fail_sync = bool(
            fail_sync
        )

        self.sync_count = 0

    def contains(
        self,
        key,
    ):
        if self.fail_contains:
            raise OSError(
                "simulated contains failure"
            )

        return key in self.values

    def setValue(
        self,
        key,
        value,
    ):
        if self.fail_set:
            raise OSError(
                "simulated write failure"
            )

        self.values[
            key
        ] = value

    def sync(self):
        self.sync_count += 1

        if self.fail_sync:
            raise OSError(
                "simulated sync failure"
            )


def _custom_preferences(
    application_id="123456789012345678",
):
    return DiscordIdentityPreferences(
        mode=IDENTITY_MODE_CUSTOM,
        custom_application_id=application_id,
    )


def _default_preferences(
    application_id="123456789012345678",
):
    return DiscordIdentityPreferences(
        mode=IDENTITY_MODE_DEFAULT,
        custom_application_id=application_id,
    )


def _assignment_key(
    mode,
):
    return (
        f"presence/{mode}/"
        "application_entry_id"
    )


class LegacyPresenceApplicationAssignmentMigrationTests(
    unittest.TestCase
):
    def test_active_custom_identity_fills_all_unassigned_modes(
        self,
    ):
        store = _MemorySettings()

        migrated = (
            migrate_legacy_discord_identity_to_presence_assignments(
                _custom_preferences(),
                USER_ENTRY,
                store,
            )
        )

        self.assertEqual(
            migrated,
            LEGACY_ASSIGNABLE_PRESENCE_MODES,
        )

        for mode in LEGACY_ASSIGNABLE_PRESENCE_MODES:
            self.assertEqual(
                store.values[
                    _assignment_key(mode)
                ],
                USER_ENTRY.entry_id,
            )

        self.assertEqual(
            store.sync_count,
            1,
        )

    def test_inactive_retained_custom_identity_remains_library_only(
        self,
    ):
        store = _MemorySettings()

        migrated = (
            migrate_legacy_discord_identity_to_presence_assignments(
                _default_preferences(),
                USER_ENTRY,
                store,
            )
        )

        self.assertEqual(
            migrated,
            (),
        )

        self.assertEqual(
            store.values,
            {},
        )

        self.assertEqual(
            store.sync_count,
            0,
        )

    def test_missing_migrated_library_entry_does_nothing(
        self,
    ):
        store = _MemorySettings()

        migrated = (
            migrate_legacy_discord_identity_to_presence_assignments(
                _custom_preferences(),
                None,
                store,
            )
        )

        self.assertEqual(
            migrated,
            (),
        )

        self.assertEqual(
            store.values,
            {},
        )

    def test_builtin_migrated_entry_is_supported(
        self,
    ):
        store = _MemorySettings()

        migrated = (
            migrate_legacy_discord_identity_to_presence_assignments(
                _custom_preferences(
                    BUILTIN_APPLICATION_ENTRY.application_id
                ),
                BUILTIN_APPLICATION_ENTRY,
                store,
            )
        )

        self.assertEqual(
            migrated,
            LEGACY_ASSIGNABLE_PRESENCE_MODES,
        )

        for mode in LEGACY_ASSIGNABLE_PRESENCE_MODES:
            self.assertEqual(
                store.values[
                    _assignment_key(mode)
                ],
                BUILTIN_APPLICATION_ENTRY_ID,
            )

    def test_existing_explicit_assignment_is_never_overwritten(
        self,
    ):
        custom_key = _assignment_key(
            "custom"
        )

        store = _MemorySettings(
            {
                custom_key: (
                    EXPLICIT_ENTRY_ID
                ),
            }
        )

        migrated = (
            migrate_legacy_discord_identity_to_presence_assignments(
                _custom_preferences(),
                USER_ENTRY,
                store,
            )
        )

        self.assertNotIn(
            "custom",
            migrated,
        )

        self.assertEqual(
            store.values[
                custom_key
            ],
            EXPLICIT_ENTRY_ID,
        )

        for mode in (
            "music",
            "afk",
            "sleep",
            "working",
        ):
            self.assertEqual(
                store.values[
                    _assignment_key(mode)
                ],
                USER_ENTRY.entry_id,
            )

    def test_existing_missing_library_reference_is_preserved(
        self,
    ):
        working_key = _assignment_key(
            "working"
        )

        store = _MemorySettings(
            {
                working_key: (
                    EXPLICIT_ENTRY_ID
                ),
            }
        )

        migrate_legacy_discord_identity_to_presence_assignments(
            _custom_preferences(),
            USER_ENTRY,
            store,
        )

        self.assertEqual(
            store.values[
                working_key
            ],
            EXPLICIT_ENTRY_ID,
        )

    def test_existing_malformed_assignment_is_still_not_rewritten(
        self,
    ):
        sleep_key = _assignment_key(
            "sleep"
        )

        store = _MemorySettings(
            {
                sleep_key: (
                    "../../legacy-corrupt-value"
                ),
            }
        )

        migrate_legacy_discord_identity_to_presence_assignments(
            _custom_preferences(),
            USER_ENTRY,
            store,
        )

        self.assertEqual(
            store.values[
                sleep_key
            ],
            "../../legacy-corrupt-value",
        )

    def test_repeated_migration_is_idempotent(
        self,
    ):
        store = _MemorySettings()

        first = (
            migrate_legacy_discord_identity_to_presence_assignments(
                _custom_preferences(),
                USER_ENTRY,
                store,
            )
        )

        second = (
            migrate_legacy_discord_identity_to_presence_assignments(
                _custom_preferences(),
                USER_ENTRY,
                store,
            )
        )

        self.assertEqual(
            first,
            LEGACY_ASSIGNABLE_PRESENCE_MODES,
        )

        self.assertEqual(
            second,
            (),
        )

        self.assertEqual(
            store.sync_count,
            1,
        )

    def test_disabled_mode_is_never_assigned(
        self,
    ):
        store = _MemorySettings()

        migrate_legacy_discord_identity_to_presence_assignments(
            _custom_preferences(),
            USER_ENTRY,
            store,
        )

        self.assertNotIn(
            _assignment_key("disabled"),
            store.values,
        )

    def test_invalid_migrated_entry_result_fails_open(
        self,
    ):
        store = _MemorySettings()

        migrated = (
            migrate_legacy_discord_identity_to_presence_assignments(
                _custom_preferences(),
                object(),
                store,
            )
        )

        self.assertEqual(
            migrated,
            (),
        )

        self.assertEqual(
            store.values,
            {},
        )

    def test_contains_failure_is_startup_safe(
        self,
    ):
        store = _MemorySettings(
            fail_contains=True
        )

        migrated = (
            migrate_legacy_discord_identity_to_presence_assignments(
                _custom_preferences(),
                USER_ENTRY,
                store,
            )
        )

        self.assertEqual(
            migrated,
            (),
        )

    def test_write_failure_is_startup_safe(
        self,
    ):
        store = _MemorySettings(
            fail_set=True
        )

        migrated = (
            migrate_legacy_discord_identity_to_presence_assignments(
                _custom_preferences(),
                USER_ENTRY,
                store,
            )
        )

        self.assertEqual(
            migrated,
            (),
        )

    def test_sync_failure_does_not_block_startup(
        self,
    ):
        store = _MemorySettings(
            fail_sync=True
        )

        migrated = (
            migrate_legacy_discord_identity_to_presence_assignments(
                _custom_preferences(),
                USER_ENTRY,
                store,
            )
        )

        self.assertEqual(
            migrated,
            LEGACY_ASSIGNABLE_PRESENCE_MODES,
        )

        self.assertEqual(
            store.sync_count,
            1,
        )

    def test_legacy_preferences_are_not_modified(
        self,
    ):
        preferences = (
            _custom_preferences()
        )

        original = replace(
            preferences
        )

        store = _MemorySettings()

        migrate_legacy_discord_identity_to_presence_assignments(
            preferences,
            USER_ENTRY,
            store,
        )

        self.assertEqual(
            preferences,
            original,
        )


class LegacyPresenceAssignmentMigrationBoundaryTests(
    unittest.TestCase
):
    def test_main_window_captures_library_migration_result(
        self,
    ):
        source = Path(
            "src/ui/main_window.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            (
                "migrated_legacy_discord_application = (\n"
                "            "
                "migrate_legacy_discord_identity_to_library("
            ),
            source,
        )

    def test_main_window_migrates_assignments_after_controller_exists(
        self,
    ):
        source = Path(
            "src/ui/main_window.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        controller_index = source.index(
            "self.presence_controller = ("
        )

        assignment_index = source.index(
            (
                "migrate_legacy_discord_identity_to_"
                "presence_assignments("
            )
        )

        afk_index = source.index(
            "self.afk_preferences_store = ("
        )

        self.assertLess(
            controller_index,
            assignment_index,
        )

        self.assertLess(
            assignment_index,
            afk_index,
        )

    def test_live_rpc_construction_still_uses_legacy_resolved_identity(
        self,
    ):
        source = Path(
            "src/ui/main_window.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        rpc_start = source.index(
            "self.discord = ("
        )

        rpc_end = source.index(
            "self.presence_controller = (",
            rpc_start,
        )

        rpc_source = source[
            rpc_start:
            rpc_end
        ]

        self.assertIn(
            (
                "discord_identity_preferences\n"
                "                    "
                ".resolved_application_id"
            ),
            rpc_source,
        )

        self.assertNotIn(
            "application_entry_id",
            rpc_source,
        )

    def test_migration_layer_owns_no_rpc_or_preset_schema(
        self,
    ):
        migration_source = Path(
            "src/discord/application_library_migration.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        preset_source = Path(
            "src/discord/presence_presets.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertNotIn(
            "request_client_id",
            migration_source,
        )

        self.assertNotIn(
            "ExtendedDiscordPresence",
            migration_source,
        )

        self.assertNotIn(
            "pypresence",
            migration_source.casefold(),
        )

        self.assertNotIn(
            "application_entry_id",
            preset_source,
        )


if __name__ == "__main__":
    unittest.main()
