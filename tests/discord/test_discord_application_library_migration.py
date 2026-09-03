from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY,
    DiscordApplicationLibraryError,
    DiscordApplicationLibraryStore,
)
from src.discord.application_library_migration import (
    migrate_legacy_discord_identity_to_library,
)
from src.discord.identity_preferences import (
    DEFAULT_DISCORD_APPLICATION_ID,
    IDENTITY_MODE_CUSTOM,
    IDENTITY_MODE_DEFAULT,
    DiscordIdentityPreferences,
)


APPLICATION_ID_A = (
    "1096663809097203752"
)


class _FailingOSErrorStore:
    def migrate_legacy_application_id(
        self,
        application_id,
    ):
        raise OSError(
            "simulated write failure"
        )


class _FailingLibraryErrorStore:
    def migrate_legacy_application_id(
        self,
        application_id,
    ):
        raise DiscordApplicationLibraryError(
            "simulated library failure"
        )


class _InvalidReturnStore:
    def migrate_legacy_application_id(
        self,
        application_id,
    ):
        return "not-an-entry"


class DiscordApplicationLibraryMigrationTests(
    unittest.TestCase
):
    def setUp(self):
        self.temporary = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temporary.cleanup
        )

        self.path = (
            Path(self.temporary.name)
            / "discord_applications.json"
        )

        self.store = (
            DiscordApplicationLibraryStore(
                self.path
            )
        )

    def test_empty_legacy_identity_does_nothing(
        self,
    ):
        preferences = (
            DiscordIdentityPreferences()
        )

        result = (
            migrate_legacy_discord_identity_to_library(
                preferences,
                self.store,
            )
        )

        self.assertIsNone(result)
        self.assertFalse(
            self.path.exists()
        )

    def test_inactive_retained_custom_id_is_preserved(
        self,
    ):
        preferences = (
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_DEFAULT,
                custom_application_id=(
                    APPLICATION_ID_A
                ),
            )
        )

        self.assertEqual(
            preferences.resolved_application_id,
            DEFAULT_DISCORD_APPLICATION_ID,
        )

        result = (
            migrate_legacy_discord_identity_to_library(
                preferences,
                self.store,
            )
        )

        self.assertIsNotNone(result)

        self.assertEqual(
            result.application_id,
            APPLICATION_ID_A,
        )

        self.assertEqual(
            preferences.normalized_mode,
            IDENTITY_MODE_DEFAULT,
        )

        self.assertEqual(
            preferences.resolved_application_id,
            DEFAULT_DISCORD_APPLICATION_ID,
        )

    def test_active_custom_id_is_preserved_without_changing_it(
        self,
    ):
        preferences = (
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id=(
                    APPLICATION_ID_A
                ),
            )
        )

        result = (
            migrate_legacy_discord_identity_to_library(
                preferences,
                self.store,
            )
        )

        self.assertIsNotNone(result)

        self.assertEqual(
            result.application_id,
            APPLICATION_ID_A,
        )

        self.assertEqual(
            preferences.custom_application_id,
            APPLICATION_ID_A,
        )

        self.assertEqual(
            preferences.resolved_application_id,
            APPLICATION_ID_A,
        )

    def test_builtin_id_resolves_without_user_entry(
        self,
    ):
        preferences = (
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id=(
                    DEFAULT_DISCORD_APPLICATION_ID
                ),
            )
        )

        result = (
            migrate_legacy_discord_identity_to_library(
                preferences,
                self.store,
            )
        )

        self.assertEqual(
            result,
            BUILTIN_APPLICATION_ENTRY,
        )

        self.assertFalse(
            self.path.exists()
        )

    def test_repeated_startup_migration_is_idempotent(
        self,
    ):
        preferences = (
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id=(
                    APPLICATION_ID_A
                ),
            )
        )

        first = (
            migrate_legacy_discord_identity_to_library(
                preferences,
                self.store,
            )
        )

        second = (
            migrate_legacy_discord_identity_to_library(
                preferences,
                self.store,
            )
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            len(
                self.store.user_entries()
            ),
            1,
        )

    def test_existing_library_entry_is_reused(
        self,
    ):
        existing = self.store.create(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        preferences = (
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id=(
                    APPLICATION_ID_A
                ),
            )
        )

        result = (
            migrate_legacy_discord_identity_to_library(
                preferences,
                self.store,
            )
        )

        self.assertEqual(
            result,
            existing,
        )

        self.assertEqual(
            len(
                self.store.user_entries()
            ),
            1,
        )

    def test_invalid_legacy_id_is_ignored_safely(
        self,
    ):
        preferences = (
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id="invalid",
            )
        )

        result = (
            migrate_legacy_discord_identity_to_library(
                preferences,
                self.store,
            )
        )

        self.assertIsNone(result)

        self.assertFalse(
            self.path.exists()
        )

    def test_storage_os_error_is_fail_open(
        self,
    ):
        preferences = (
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id=(
                    APPLICATION_ID_A
                ),
            )
        )

        result = (
            migrate_legacy_discord_identity_to_library(
                preferences,
                _FailingOSErrorStore(),
            )
        )

        self.assertIsNone(result)

        self.assertEqual(
            preferences.resolved_application_id,
            APPLICATION_ID_A,
        )

    def test_library_error_is_fail_open(
        self,
    ):
        preferences = (
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id=(
                    APPLICATION_ID_A
                ),
            )
        )

        result = (
            migrate_legacy_discord_identity_to_library(
                preferences,
                _FailingLibraryErrorStore(),
            )
        )

        self.assertIsNone(result)

    def test_invalid_store_result_is_fail_open(
        self,
    ):
        preferences = (
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id=(
                    APPLICATION_ID_A
                ),
            )
        )

        result = (
            migrate_legacy_discord_identity_to_library(
                preferences,
                _InvalidReturnStore(),
            )
        )

        self.assertIsNone(result)

    def test_invalid_store_interface_is_rejected(
        self,
    ):
        with self.assertRaises(TypeError):
            migrate_legacy_discord_identity_to_library(
                DiscordIdentityPreferences(),
                object(),
            )

    def test_main_window_migrates_before_rpc_construction(
        self,
    ):
        source = Path(
            "src/ui/main_window.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "DiscordApplicationLibraryStore",
            source,
        )

        self.assertIn(
            "migrate_legacy_discord_identity_to_library",
            source,
        )

        library_index = source.index(
            "self.discord_application_library_store = ("
        )

        identity_index = source.index(
            "self.discord_identity_preferences_store = ("
        )

        load_index = source.index(
            "discord_identity_preferences = ("
        )

        migration_start = source.index(
            "migrated_legacy_discord_application = ("
        )

        rpc_index = source.index(
            "self.discord = (",
            migration_start,
        )

        migration_source = source[
            migration_start:
            rpc_index
        ]

        rpc_source = source[
            rpc_index:
            source.index(
                "self.presence_controller = (",
                rpc_index,
            )
        ]

        self.assertLess(
            library_index,
            identity_index,
        )

        self.assertLess(
            identity_index,
            load_index,
        )

        self.assertLess(
            load_index,
            migration_start,
        )

        self.assertLess(
            migration_start,
            rpc_index,
        )

        self.assertIn(
            "migrate_legacy_discord_identity_to_library(",
            migration_source,
        )

        self.assertIn(
            "discord_identity_preferences,",
            migration_source,
        )

        self.assertIn(
            "self.discord_application_library_store,",
            migration_source,
        )

        self.assertIn(
            (
                "discord_identity_preferences\n"
                "                    "
                ".resolved_application_id"
            ),
            rpc_source,
        )


if __name__ == "__main__":
    unittest.main()
