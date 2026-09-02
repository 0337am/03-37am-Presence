from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.discord.application_library import (
    APPLICATION_LIBRARY_STORAGE_KIND,
    BUILTIN_APPLICATION_ENTRY,
    BUILTIN_APPLICATION_ENTRY_ID,
    BUILTIN_APPLICATION_NAME,
    DiscordApplicationLibraryError,
    DiscordApplicationLibraryStore,
    MAX_STORAGE_FILE_BYTES,
    SCHEMA_VERSION,
    is_valid_user_entry_id,
)
from src.discord.identity_preferences import (
    DEFAULT_DISCORD_APPLICATION_ID,
)


APPLICATION_ID_A = (
    "1096663809097203752"
)

APPLICATION_ID_B = (
    "123456789012345678"
)


class DiscordApplicationLibraryTests(
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

    def test_builtin_entry_is_stable(
        self,
    ):
        self.assertEqual(
            BUILTIN_APPLICATION_ENTRY.entry_id,
            BUILTIN_APPLICATION_ENTRY_ID,
        )

        self.assertEqual(
            BUILTIN_APPLICATION_ENTRY.name,
            BUILTIN_APPLICATION_NAME,
        )

        self.assertEqual(
            BUILTIN_APPLICATION_ENTRY.application_id,
            DEFAULT_DISCORD_APPLICATION_ID,
        )

        self.assertTrue(
            BUILTIN_APPLICATION_ENTRY.builtin
        )

    def test_empty_library_exposes_builtin(
        self,
    ):
        self.assertEqual(
            self.store.list_entries(),
            [
                BUILTIN_APPLICATION_ENTRY
            ],
        )

        self.assertFalse(
            self.path.exists()
        )

    def test_create_round_trip(
        self,
    ):
        created = self.store.create(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        self.assertTrue(
            is_valid_user_entry_id(
                created.entry_id
            )
        )

        reloaded = (
            DiscordApplicationLibraryStore(
                self.path
            )
        )

        self.assertEqual(
            reloaded.get(
                created.entry_id
            ),
            created,
        )

    def test_schema_versioned_payload(
        self,
    ):
        self.store.create(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        payload = json.loads(
            self.path.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            payload["kind"],
            APPLICATION_LIBRARY_STORAGE_KIND,
        )

        self.assertEqual(
            payload["schema_version"],
            SCHEMA_VERSION,
        )

        self.assertEqual(
            len(
                payload["applications"]
            ),
            1,
        )

        self.assertNotIn(
            BUILTIN_APPLICATION_ENTRY_ID,
            self.path.read_text(
                encoding="utf-8"
            ),
        )

    def test_duplicate_application_id_rejected(
        self,
    ):
        self.store.create(
            name="First",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        with self.assertRaisesRegex(
            DiscordApplicationLibraryError,
            "Application IDs must be unique",
        ):
            self.store.create(
                name="Second",
                application_id=(
                    APPLICATION_ID_A
                ),
            )

    def test_builtin_application_id_rejected(
        self,
    ):
        with self.assertRaisesRegex(
            DiscordApplicationLibraryError,
            "Application IDs must be unique",
        ):
            self.store.create(
                name="Duplicate 03:37am",
                application_id=(
                    DEFAULT_DISCORD_APPLICATION_ID
                ),
            )

    def test_duplicate_name_rejected_case_insensitively(
        self,
    ):
        self.store.create(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        with self.assertRaisesRegex(
            DiscordApplicationLibraryError,
            "names must be unique",
        ):
            self.store.create(
                name="sword art online",
                application_id=(
                    APPLICATION_ID_B
                ),
            )

    def test_builtin_name_is_reserved(
        self,
    ):
        with self.assertRaisesRegex(
            DiscordApplicationLibraryError,
            "names must be unique",
        ):
            self.store.create(
                name=(
                    BUILTIN_APPLICATION_NAME
                ),
                application_id=(
                    APPLICATION_ID_A
                ),
            )

    def test_invalid_application_id_rejected(
        self,
    ):
        with self.assertRaises(
            DiscordApplicationLibraryError
        ):
            self.store.create(
                name="Invalid",
                application_id="not-an-id",
            )

    def test_update_preserves_entry_id(
        self,
    ):
        created = self.store.create(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        updated = self.store.update(
            created.entry_id,
            name="SAO",
            application_id=(
                APPLICATION_ID_B
            ),
        )

        self.assertEqual(
            updated.entry_id,
            created.entry_id,
        )

        self.assertEqual(
            updated.name,
            "SAO",
        )

        self.assertEqual(
            updated.application_id,
            APPLICATION_ID_B,
        )

    def test_update_collision_is_rejected(
        self,
    ):
        first = self.store.create(
            name="First",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        second = self.store.create(
            name="Second",
            application_id=(
                APPLICATION_ID_B
            ),
        )

        with self.assertRaises(
            DiscordApplicationLibraryError
        ):
            self.store.update(
                second.entry_id,
                name=first.name,
            )

        with self.assertRaises(
            DiscordApplicationLibraryError
        ):
            self.store.update(
                second.entry_id,
                application_id=(
                    first.application_id
                ),
            )

    def test_delete_user_entry(
        self,
    ):
        created = self.store.create(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        self.assertTrue(
            self.store.delete(
                created.entry_id
            )
        )

        self.assertIsNone(
            self.store.get(
                created.entry_id
            )
        )

        self.assertFalse(
            self.store.delete(
                created.entry_id
            )
        )

    def test_builtin_cannot_be_edited(
        self,
    ):
        with self.assertRaisesRegex(
            DiscordApplicationLibraryError,
            "cannot be edited",
        ):
            self.store.update(
                BUILTIN_APPLICATION_ENTRY_ID,
                name="Changed",
            )

    def test_builtin_cannot_be_deleted(
        self,
    ):
        with self.assertRaisesRegex(
            DiscordApplicationLibraryError,
            "cannot be deleted",
        ):
            self.store.delete(
                BUILTIN_APPLICATION_ENTRY_ID
            )

    def test_find_by_application_id(
        self,
    ):
        created = self.store.create(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        self.assertEqual(
            self.store.find_by_application_id(
                APPLICATION_ID_A
            ),
            created,
        )

        self.assertEqual(
            self.store.find_by_application_id(
                DEFAULT_DISCORD_APPLICATION_ID
            ),
            BUILTIN_APPLICATION_ENTRY,
        )

        self.assertIsNone(
            self.store.find_by_application_id(
                "invalid"
            )
        )

    def test_legacy_migration_is_idempotent(
        self,
    ):
        first = (
            self.store
            .migrate_legacy_application_id(
                APPLICATION_ID_A
            )
        )

        second = (
            self.store
            .migrate_legacy_application_id(
                APPLICATION_ID_A
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

    def test_builtin_legacy_id_is_not_persisted(
        self,
    ):
        result = (
            self.store
            .migrate_legacy_application_id(
                DEFAULT_DISCORD_APPLICATION_ID
            )
        )

        self.assertEqual(
            result,
            BUILTIN_APPLICATION_ENTRY,
        )

        self.assertFalse(
            self.path.exists()
        )

    def test_invalid_legacy_id_is_ignored(
        self,
    ):
        self.assertIsNone(
            self.store
            .migrate_legacy_application_id(
                "invalid"
            )
        )

        self.assertFalse(
            self.path.exists()
        )

    def test_legacy_name_collision_gets_unique_name(
        self,
    ):
        self.store.create(
            name=(
                "Imported Discord Application"
            ),
            application_id=(
                APPLICATION_ID_A
            ),
        )

        migrated = (
            self.store
            .migrate_legacy_application_id(
                APPLICATION_ID_B
            )
        )

        self.assertIsNotNone(
            migrated
        )

        self.assertEqual(
            migrated.name,
            "Imported Discord Application 2",
        )

    def test_corrupt_storage_is_quarantined(
        self,
    ):
        self.path.write_text(
            "{ broken",
            encoding="utf-8",
        )

        self.assertEqual(
            self.store.list_entries(),
            [
                BUILTIN_APPLICATION_ENTRY
            ],
        )

        self.assertFalse(
            self.path.exists()
        )

        quarantined = list(
            self.path.parent.glob(
                self.path.name
                + ".corrupt-*"
            )
        )

        self.assertEqual(
            len(quarantined),
            1,
        )

    def test_unsupported_schema_is_quarantined(
        self,
    ):
        self.path.write_text(
            json.dumps(
                {
                    "kind": (
                        APPLICATION_LIBRARY_STORAGE_KIND
                    ),
                    "schema_version": (
                        SCHEMA_VERSION + 1
                    ),
                    "applications": [],
                }
            ),
            encoding="utf-8",
        )

        self.assertEqual(
            self.store.list_entries(),
            [
                BUILTIN_APPLICATION_ENTRY
            ],
        )

        self.assertFalse(
            self.path.exists()
        )

    def test_oversize_storage_is_quarantined(
        self,
    ):
        self.path.write_bytes(
            b"x"
            * (
                MAX_STORAGE_FILE_BYTES
                + 1
            )
        )

        self.assertEqual(
            self.store.list_entries(),
            [
                BUILTIN_APPLICATION_ENTRY
            ],
        )

        self.assertFalse(
            self.path.exists()
        )

    def test_reset_removes_user_library(
        self,
    ):
        self.store.create(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        self.store.reset_user_entries()

        self.assertFalse(
            self.path.exists()
        )

        self.assertEqual(
            self.store.list_entries(),
            [
                BUILTIN_APPLICATION_ENTRY
            ],
        )


if __name__ == "__main__":
    unittest.main()
