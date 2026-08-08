from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import (
    QSettings,
)

from src.artwork.cloudinary_preferences import (
    CloudinaryPreferences,
)
from src.music.source_preferences import (
    SourcePreferences,
)
from src.system.afk_preferences import (
    AfkPreferences,
)
from src.system.global_hotkeys import (
    HotkeyBinding,
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
)
from src.system.media_hotkey_preferences import (
    MediaHotkeyPreferences,
)
from src.system.media_hotkeys import (
    ACTION_NEXT,
    ACTION_PLAY_PAUSE,
)
from src.system.settings_backup import (
    BACKUP_SCHEMA_VERSION,
    SettingsBackupManager,
    SettingsBackupValidationError,
    SettingsBackupError,
)
from src.ui.dashboard_layout import (
    preset_layout,
)


class MemoryStore:
    def __init__(
        self,
        value,
    ):
        self.value = value
        self.saved = []

    def load(
        self,
    ):
        return self.value

    def save(
        self,
        value,
    ):
        self.value = value
        self.saved.append(
            value
        )


def hotkey_preferences(
    *,
    enabled=True,
    key=0x39,
    action=ACTION_PLAY_PAUSE,
    seek_seconds=15.0,
):
    return MediaHotkeyPreferences(
        enabled=enabled,
        seek_seconds=seek_seconds,
        bindings={
            action:
                HotkeyBinding(
                    modifiers=(
                        MOD_CONTROL
                        | MOD_ALT
                        | MOD_SHIFT
                    ),
                    virtual_key=key,
                ),
        },
    )


class SettingsHotkeyBackupTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.root = Path(
            self.temp.name
        )

        self.settings = QSettings(
            str(
                self.root
                / "settings.ini"
            ),
            QSettings.Format.IniFormat,
        )

        self.source_store = (
            MemoryStore(
                SourcePreferences()
            )
        )

        self.afk_store = (
            MemoryStore(
                AfkPreferences()
            )
        )

        self.cloudinary_store = (
            MemoryStore(
                CloudinaryPreferences()
            )
        )

        self.dashboard_store = (
            MemoryStore(
                preset_layout(
                    "Default"
                )
            )
        )

        self.dashboard_profile_store = (
            MemoryStore(
                ()
            )
        )

        self.custom_card_store = (
            MemoryStore(
                ()
            )
        )

        self.presence_preset_store = (
            MemoryStore(
                ()
            )
        )

        self.media_hotkey_store = (
            MemoryStore(
                hotkey_preferences()
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
            )
        )

        self.manager._automatic_backup_directory = (
            lambda:
            self.root
            / "automatic-backups"
        )

        self.startup_is_enabled = patch(
            (
                "src.system.settings_backup."
                "StartupManager.is_enabled"
            ),
            return_value=False,
        )

        self.startup_is_enabled.start()

    def tearDown(
        self,
    ):
        self.startup_is_enabled.stop()

        self.settings.clear()
        self.settings.sync()

        self.temp.cleanup()

    def test_capture_includes_media_hotkeys(
        self,
    ):
        payload = (
            self.manager.capture()
        )

        self.assertEqual(
            BACKUP_SCHEMA_VERSION,
            6,
        )

        hotkeys = payload[
            "settings"
        ][
            "media_hotkeys"
        ]

        self.assertTrue(
            hotkeys[
                "included"
            ]
        )

        self.assertTrue(
            hotkeys[
                "preferences"
            ][
                "enabled"
            ]
        )

        self.assertIn(
            ACTION_PLAY_PAUSE,
            hotkeys[
                "preferences"
            ][
                "bindings"
            ],
        )

    def test_current_schema_requires_media_hotkey_section(
        self,
    ):
        payload = (
            self.manager.capture()
        )

        payload = copy.deepcopy(
            payload
        )

        payload[
            "settings"
        ].pop(
            "media_hotkeys"
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

    def test_legacy_schema_preserves_hotkey_marker(
        self,
    ):
        payload = copy.deepcopy(
            self.manager.capture()
        )

        payload[
            "schema_version"
        ] = 5

        payload[
            "settings"
        ].pop(
            "media_hotkeys"
        )

        validated = (
            SettingsBackupManager
            .validate_payload(
                payload
            )
        )

        self.assertEqual(
            validated[
                "settings"
            ][
                "media_hotkeys"
            ],
            {
                "included": False,
            },
        )

    def test_invalid_media_hotkeys_are_rejected(
        self,
    ):
        payload = copy.deepcopy(
            self.manager.capture()
        )

        preferences = payload[
            "settings"
        ][
            "media_hotkeys"
        ][
            "preferences"
        ]

        preferences[
            "bindings"
        ][
            ACTION_NEXT
        ] = copy.deepcopy(
            preferences[
                "bindings"
            ][
                ACTION_PLAY_PAUSE
            ]
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

    def test_preview_reports_media_hotkeys(
        self,
    ):
        path = (
            self.root
            / "settings-backup.json"
        )

        self.manager.export_backup(
            path
        )

        preview = (
            self.manager.preview_backup(
                path
            )
        )

        self.assertTrue(
            preview.includes_media_hotkeys
        )

    def test_restore_restores_media_hotkeys(
        self,
    ):
        backed_up = (
            hotkey_preferences(
                seek_seconds=25.0
            )
        )

        self.media_hotkey_store.value = (
            backed_up
        )

        path = (
            self.root
            / "settings-backup.json"
        )

        self.manager.export_backup(
            path
        )

        changed = (
            hotkey_preferences(
                key=0x4E,
                action=ACTION_NEXT,
                seek_seconds=5.0,
            )
        )

        self.media_hotkey_store.value = (
            changed
        )

        with patch(
            (
                "src.system.settings_backup."
                "StartupManager.set_enabled"
            ),
            return_value=True,
        ):
            result = (
                self.manager.restore_backup(
                    path
                )
            )

        self.assertEqual(
            self.media_hotkey_store.value,
            backed_up,
        )

        self.assertTrue(
            result.restored_media_hotkeys
        )

    def test_legacy_restore_preserves_current_hotkeys(
        self,
    ):
        payload = copy.deepcopy(
            self.manager.capture()
        )

        payload[
            "schema_version"
        ] = 5

        payload[
            "settings"
        ].pop(
            "media_hotkeys"
        )

        path = (
            self.root
            / "legacy-settings.json"
        )

        path.write_text(
            json.dumps(
                payload
            ),
            encoding="utf-8",
        )

        current = (
            hotkey_preferences(
                key=0x4E,
                action=ACTION_NEXT,
                seek_seconds=30.0,
            )
        )

        self.media_hotkey_store.value = (
            current
        )

        with patch(
            (
                "src.system.settings_backup."
                "StartupManager.set_enabled"
            ),
            return_value=True,
        ):
            result = (
                self.manager.restore_backup(
                    path
                )
            )

        self.assertEqual(
            self.media_hotkey_store.value,
            current,
        )

        self.assertFalse(
            result.restored_media_hotkeys
        )

    def test_failed_restore_rolls_back_hotkeys(
        self,
    ):
        backup_value = (
            hotkey_preferences(
                seek_seconds=40.0
            )
        )

        self.media_hotkey_store.value = (
            backup_value
        )

        path = (
            self.root
            / "rollback-test.json"
        )

        self.manager.export_backup(
            path
        )

        original = (
            hotkey_preferences(
                key=0x4E,
                action=ACTION_NEXT,
                seek_seconds=7.0,
            )
        )

        self.media_hotkey_store.value = (
            original
        )

        startup_results = [
            False,
            True,
        ]

        def set_startup(
            enabled,
            start_minimized=True,
        ):
            return startup_results.pop(
                0
            )

        with patch(
            (
                "src.system.settings_backup."
                "StartupManager.set_enabled"
            ),
            side_effect=set_startup,
        ):
            with self.assertRaises(
                SettingsBackupError
            ):
                self.manager.restore_backup(
                    path
                )

        self.assertEqual(
            self.media_hotkey_store.value,
            original,
        )

    def test_safety_backup_contains_pre_restore_hotkeys(
        self,
    ):
        backup_value = (
            hotkey_preferences(
                seek_seconds=22.0
            )
        )

        self.media_hotkey_store.value = (
            backup_value
        )

        path = (
            self.root
            / "restore-source.json"
        )

        self.manager.export_backup(
            path
        )

        current = (
            hotkey_preferences(
                key=0x4E,
                action=ACTION_NEXT,
                seek_seconds=9.0,
            )
        )

        self.media_hotkey_store.value = (
            current
        )

        with patch(
            (
                "src.system.settings_backup."
                "StartupManager.set_enabled"
            ),
            return_value=True,
        ):
            result = (
                self.manager.restore_backup(
                    path
                )
            )

        safety = json.loads(
            result.safety_backup_path.read_text(
                encoding="utf-8"
            )
        )

        restored_safety = (
            SettingsBackupManager
            .validate_payload(
                safety
            )
        )

        safety_preferences = (
            restored_safety[
                "settings"
            ][
                "media_hotkeys"
            ][
                "preferences"
            ]
        )

        self.assertEqual(
            safety_preferences[
                "seek_seconds"
            ],
            current.seek_seconds,
        )

    def test_settings_ui_wires_shared_store_and_live_refresh(
        self,
    ):
        source = (
            Path(
                "src/ui/settings.py"
            ).read_text(
                encoding="utf-8-sig"
            )
        )

        self.assertIn(
            "self.media_hotkey_preferences_store",
            source,
        )

        self.assertIn(
            "media_hotkey_store=(",
            source,
        )

        self.assertIn(
            "preference_store=(",
            source,
        )

        self.assertIn(
            "self.media_hotkeys_card.refresh_from_store()",
            source,
        )

        self.assertIn(
            "self.media_hotkeys_card.reload_runtime()",
            source,
        )

        self.assertIn(
            "Global media hotkeys were restored",
            source,
        )


if __name__ == "__main__":
    unittest.main()
