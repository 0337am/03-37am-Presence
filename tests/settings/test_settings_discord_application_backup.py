from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import QSettings

from src.artwork.cloudinary_preferences import (
    CloudinaryPreferences,
)
from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY_ID,
    DiscordApplicationEntry,
    DiscordApplicationLibraryStore,
)
from src.music.source_preferences import (
    SourcePreferences,
)
from src.system.afk_preferences import (
    AfkPreferences,
)
from src.system.media_hotkey_preferences import (
    MediaHotkeyPreferences,
)
from src.system.settings_backup import (
    BACKUP_SCHEMA_VERSION,
    DISCORD_APPLICATION_BACKUP_INTRODUCED_SCHEMA_VERSION,
    SettingsBackupError,
    SettingsBackupManager,
    SettingsBackupValidationError,
)
from src.ui.dashboard_layout import (
    preset_layout,
)


APP_A = DiscordApplicationEntry(
    entry_id="discord_app_0123456789abcdef",
    name="Application A",
    application_id="123456789012345678",
)

APP_B = DiscordApplicationEntry(
    entry_id="discord_app_fedcba9876543210",
    name="Application B",
    application_id="987654321098765432",
)


class MemoryStore:
    def __init__(
        self,
        value,
    ):
        self.value = value

    def load(
        self,
    ):
        return self.value

    def save(
        self,
        value,
    ):
        self.value = value
        return value


class FailOnceStore(
    MemoryStore
):
    def __init__(
        self,
        value,
    ):
        super().__init__(
            value
        )

        self.failed = False

    def save(
        self,
        value,
    ):
        if not self.failed:
            self.failed = True

            raise OSError(
                "synthetic restore failure"
            )

        return super().save(
            value
        )


class SettingsDiscordApplicationBackupTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        self.temporary = (
            tempfile.TemporaryDirectory()
        )

        self.root = Path(
            self.temporary.name
        )

        self.settings = QSettings(
            str(
                self.root
                / "settings.ini"
            ),
            QSettings.Format.IniFormat,
        )

        self.settings.clear()
        self.settings.sync()

        self.source_store = MemoryStore(
            SourcePreferences()
        )

        self.afk_store = MemoryStore(
            AfkPreferences()
        )

        self.cloudinary_store = MemoryStore(
            CloudinaryPreferences()
        )

        self.dashboard_store = MemoryStore(
            preset_layout(
                "Default"
            )
        )

        self.dashboard_profile_store = (
            MemoryStore(
                ()
            )
        )

        self.custom_card_store = MemoryStore(
            ()
        )

        self.presence_preset_store = (
            MemoryStore(
                ()
            )
        )

        self.media_hotkey_store = (
            MemoryStore(
                MediaHotkeyPreferences()
            )
        )

        self.application_store = (
            DiscordApplicationLibraryStore(
                self.root
                / "discord_applications.json"
            )
        )

        self.manager = (
            SettingsBackupManager(
                settings=self.settings,
                source_store=(
                    self.source_store
                ),
                afk_store=(
                    self.afk_store
                ),
                cloudinary_store=(
                    self.cloudinary_store
                ),
                dashboard_store=(
                    self.dashboard_store
                ),
                dashboard_profile_store=(
                    self.dashboard_profile_store
                ),
                custom_card_store=(
                    self.custom_card_store
                ),
                presence_preset_store=(
                    self.presence_preset_store
                ),
                media_hotkey_store=(
                    self.media_hotkey_store
                ),
                discord_application_store=(
                    self.application_store
                ),
            )
        )

        self.manager._automatic_backup_directory = (
            lambda:
            self.root
            / "automatic-backups"
        )

        self.startup_read = patch(
            "src.system.settings_backup."
            "StartupManager.is_enabled",
            return_value=False,
        )

        self.startup_write = patch(
            "src.system.settings_backup."
            "StartupManager.set_enabled",
            return_value=True,
        )

        self.startup_read.start()
        self.startup_write.start()

        self.addCleanup(
            self.startup_read.stop
        )

        self.addCleanup(
            self.startup_write.stop
        )

    def tearDown(
        self,
    ):
        self.settings.clear()
        self.settings.sync()

        del self.settings

        self.temporary.cleanup()

    def write_payload(
        self,
        name: str,
        payload: dict,
    ) -> Path:
        path = (
            self.root
            / name
        )

        path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return path

    @staticmethod
    def application_payload(
        payload,
    ):
        return payload[
            "settings"
        ][
            "discord_applications"
        ][
            "storage"
        ][
            "applications"
        ]

    def test_schema_seven_introduces_application_library(
        self,
    ):
        self.assertEqual(
            BACKUP_SCHEMA_VERSION,
            7,
        )

        self.assertEqual(
            DISCORD_APPLICATION_BACKUP_INTRODUCED_SCHEMA_VERSION,
            7,
        )

        payload = (
            self.manager.capture()
        )

        applications = payload[
            "settings"
        ][
            "discord_applications"
        ]

        self.assertTrue(
            applications[
                "included"
            ]
        )

        self.assertEqual(
            applications[
                "storage"
            ][
                "applications"
            ],
            [],
        )

    def test_capture_preserves_stable_user_application_entry(
        self,
    ):
        self.application_store.save(
            (
                APP_A,
            )
        )

        applications = (
            self.application_payload(
                self.manager.capture()
            )
        )

        self.assertEqual(
            len(
                applications
            ),
            1,
        )

        self.assertEqual(
            applications[
                0
            ][
                "id"
            ],
            APP_A.entry_id,
        )

        self.assertNotIn(
            "entry_id",
            applications[
                0
            ],
        )

        self.assertEqual(
            applications[
                0
            ][
                "name"
            ],
            APP_A.name,
        )

        self.assertEqual(
            applications[
                0
            ][
                "application_id"
            ],
            APP_A.application_id,
        )

    def test_builtin_application_is_not_exported_as_user_entry(
        self,
    ):
        self.application_store.save(
            (
                APP_A,
            )
        )

        applications = (
            self.application_payload(
                self.manager.capture()
            )
        )

        self.assertFalse(
            any(
                item[
                    "id"
                ]
                == BUILTIN_APPLICATION_ENTRY_ID
                for item in applications
            )
        )

        self.assertEqual(
            self.application_store
            .list_entries()[
                0
            ].entry_id,
            BUILTIN_APPLICATION_ENTRY_ID,
        )

    def test_current_schema_requires_application_library_section(
        self,
    ):
        payload = (
            self.manager.capture()
        )

        payload[
            "settings"
        ].pop(
            "discord_applications"
        )

        with self.assertRaises(
            SettingsBackupValidationError
        ):
            (
                SettingsBackupManager
                .validate_payload(
                    payload
                )
            )

    def test_invalid_application_library_is_rejected(
        self,
    ):
        self.application_store.save(
            (
                APP_A,
            )
        )

        payload = (
            self.manager.capture()
        )

        self.application_payload(
            payload
        )[
            0
        ][
            "application_id"
        ] = "not-a-discord-id"

        with self.assertRaises(
            SettingsBackupValidationError
        ):
            (
                SettingsBackupManager
                .validate_payload(
                    payload
                )
            )

    def test_schema_six_without_library_is_legacy_safe(
        self,
    ):
        payload = (
            self.manager.capture()
        )

        payload[
            "schema_version"
        ] = 6

        payload[
            "settings"
        ].pop(
            "discord_applications"
        )

        normalized = (
            SettingsBackupManager
            .validate_payload(
                payload
            )
        )

        self.assertEqual(
            normalized[
                "schema_version"
            ],
            BACKUP_SCHEMA_VERSION,
        )

        self.assertEqual(
            normalized[
                "settings"
            ][
                "discord_applications"
            ],
            {
                "included": False,
                "storage": None,
            },
        )

    def test_legacy_restore_preserves_current_application_library(
        self,
    ):
        legacy = (
            self.manager.capture()
        )

        legacy[
            "schema_version"
        ] = 6

        legacy[
            "settings"
        ].pop(
            "discord_applications"
        )

        source = self.write_payload(
            "legacy.json",
            legacy,
        )

        self.application_store.save(
            (
                APP_B,
            )
        )

        self.manager.restore_backup(
            source
        )

        self.assertEqual(
            self.application_store
            .user_entries(),
            [
                APP_B,
            ],
        )

    def test_current_restore_replaces_application_library(
        self,
    ):
        self.application_store.save(
            (
                APP_A,
            )
        )

        source = self.write_payload(
            "current.json",
            self.manager.capture(),
        )

        self.application_store.save(
            (
                APP_B,
            )
        )

        self.manager.restore_backup(
            source
        )

        self.assertEqual(
            self.application_store
            .user_entries(),
            [
                APP_A,
            ],
        )

    def test_safety_backup_contains_pre_restore_library(
        self,
    ):
        self.application_store.save(
            (
                APP_A,
            )
        )

        source = self.write_payload(
            "source.json",
            self.manager.capture(),
        )

        self.application_store.save(
            (
                APP_B,
            )
        )

        result = (
            self.manager.restore_backup(
                source
            )
        )

        safety = json.loads(
            result.safety_backup_path
            .read_text(
                encoding="utf-8"
            )
        )

        entries = (
            self.application_payload(
                safety
            )
        )

        self.assertEqual(
            entries[
                0
            ][
                "id"
            ],
            APP_B.entry_id,
        )

    def test_failed_restore_rolls_back_application_library(
        self,
    ):
        self.application_store.save(
            (
                APP_A,
            )
        )

        source = self.write_payload(
            "rollback-source.json",
            self.manager.capture(),
        )

        self.application_store.save(
            (
                APP_B,
            )
        )

        self.manager.presence_preset_store = (
            FailOnceStore(
                ()
            )
        )

        with self.assertRaises(
            SettingsBackupError
        ):
            self.manager.restore_backup(
                source
            )

        self.assertEqual(
            self.application_store
            .user_entries(),
            [
                APP_B,
            ],
        )

    def test_manager_uses_injected_application_store(
        self,
    ):
        self.assertIs(
            self.manager
            .discord_application_store,
            self.application_store,
        )

    def test_settings_ui_wires_backup_and_live_refresh(
        self,
    ):
        source = (
            Path(
                "src/ui/settings.py"
            )
            .read_text(
                encoding="utf-8"
            )
        )

        self.assertIn(
            "discord_application_store=(",
            source,
        )

        self.assertIn(
            "self.discord_application_store",
            source,
        )

        self.assertIn(
            '"discord_application_library_card"',
            source,
        )

        self.assertIn(
            "refresh_from_store",
            source,
        )

        self.assertIn(
            '"entries_changed"',
            source,
        )

        self.assertIn(
            "emit_entries_changed",
            source,
        )


if __name__ == "__main__":
    unittest.main()
