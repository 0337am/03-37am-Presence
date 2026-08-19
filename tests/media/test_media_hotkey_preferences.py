from __future__ import annotations

import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.system.global_hotkeys import (
    HotkeyBinding,
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
)
from src.system.media_hotkey_preferences import (
    FILE_NAME,
    SCHEMA_VERSION,
    MediaHotkeyPreferences,
    MediaHotkeyPreferencesStore,
    media_hotkey_preferences_from_payload,
    media_hotkey_preferences_to_payload,
)
from src.system.media_hotkeys import (
    ACTION_NEXT,
    ACTION_PLAY_PAUSE,
    ACTION_PREVIOUS,
    ACTION_REPEAT,
    ACTION_SEEK_BACKWARD,
    ACTION_SEEK_FORWARD,
    ACTION_SHUFFLE,
    DEFAULT_SEEK_SECONDS,
)


def shortcut(
    key,
    modifiers=MOD_CONTROL,
):
    return HotkeyBinding(
        modifiers=modifiers,
        virtual_key=key,
    )


class MediaHotkeyPreferencesTests(
    unittest.TestCase
):
    def test_defaults_are_disabled_and_unbound(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences()
        )

        self.assertFalse(
            preferences.enabled
        )

        self.assertEqual(
            preferences.seek_seconds,
            DEFAULT_SEEK_SECONDS,
        )

        self.assertEqual(
            preferences.bindings,
            {},
        )

        self.assertEqual(
            preferences.controller_bindings(),
            {},
        )

    def test_enabled_preferences_expose_bindings(
        self,
    ):
        binding = shortcut(
            0x31
        )

        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding,
                },
            )
        )

        self.assertEqual(
            preferences.controller_bindings(),
            {
                ACTION_PLAY_PAUSE:
                    binding,
            },
        )

    def test_duplicate_bindings_are_rejected(
        self,
    ):
        duplicate = shortcut(
            0x31
        )

        with self.assertRaises(
            ValueError
        ):
            MediaHotkeyPreferences(
                bindings={
                    ACTION_PLAY_PAUSE:
                        duplicate,
                    ACTION_NEXT:
                        duplicate,
                },
            )

    def test_unknown_action_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            MediaHotkeyPreferences(
                bindings={
                    "launch_moon":
                        shortcut(
                            0x31
                        ),
                },
            )

    def test_invalid_seek_values_are_rejected(
        self,
    ):
        for value in (
            0,
            -1,
            math.inf,
            -math.inf,
            math.nan,
            "nope",
        ):
            with self.assertRaises(
                ValueError
            ):
                MediaHotkeyPreferences(
                    seek_seconds=value
                )

    def test_enabled_must_be_boolean(
        self,
    ):
        for value in (
            1,
            0,
            "true",
            None,
        ):
            with self.assertRaises(
                TypeError
            ):
                MediaHotkeyPreferences(
                    enabled=value
                )


class MediaHotkeyPreferencePayloadTests(
    unittest.TestCase
):
    def test_public_payload_helpers_round_trip(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                seek_seconds=15.0,
                bindings={
                    ACTION_PLAY_PAUSE:
                        HotkeyBinding(
                            modifiers=(
                                MOD_CONTROL
                                | MOD_ALT
                                | MOD_SHIFT
                            ),
                            virtual_key=0x39,
                        ),
                },
            )
        )

        payload = (
            media_hotkey_preferences_to_payload(
                preferences
            )
        )

        restored = (
            media_hotkey_preferences_from_payload(
                payload
            )
        )

        self.assertEqual(
            restored,
            preferences,
        )

    def test_public_payload_helper_rejects_invalid_schema(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            media_hotkey_preferences_from_payload(
                {
                    "schema_version": 999,
                    "enabled": False,
                    "seek_seconds": 10.0,
                    "bindings": {},
                }
            )


class MediaHotkeyPreferencesStoreTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        self.local_app_data = Path(
            self.temporary_directory.name
        )

        self.environment = patch.dict(
            os.environ,
            {
                "LOCALAPPDATA":
                    str(
                        self.local_app_data
                    )
            },
        )

        self.environment.start()

    def tearDown(
        self,
    ):
        self.environment.stop()

        self.temporary_directory.cleanup()

    def make_store(
        self,
    ):
        return (
            MediaHotkeyPreferencesStore()
        )

    def test_store_uses_expected_localappdata_path(
        self,
    ):
        store = self.make_store()

        self.assertEqual(
            store.file_path,
            (
                self.local_app_data
                / "0337am Presence"
                / FILE_NAME
            ),
        )

    def test_store_creates_default_file(
        self,
    ):
        store = self.make_store()

        self.assertTrue(
            store.file_path.exists()
        )

        preferences = store.load()

        self.assertFalse(
            preferences.enabled
        )

        self.assertEqual(
            preferences.bindings,
            {},
        )

    def test_default_payload_has_schema_version(
        self,
    ):
        store = self.make_store()

        payload = json.loads(
            store.file_path.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            payload["schema_version"],
            SCHEMA_VERSION,
        )

        self.assertFalse(
            payload["enabled"]
        )

        self.assertEqual(
            payload["bindings"],
            {},
        )

    def test_save_and_load_round_trip(
        self,
    ):
        store = self.make_store()

        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                seek_seconds=15.0,
                bindings={
                    ACTION_PLAY_PAUSE:
                        shortcut(
                            0x39,
                            (
                                MOD_CONTROL
                                | MOD_ALT
                                | MOD_SHIFT
                            ),
                        ),
                    ACTION_NEXT:
                        shortcut(
                            0x4E
                        ),
                },
            )
        )

        store.save(
            preferences
        )

        loaded = store.load()

        self.assertEqual(
            loaded,
            preferences,
        )

    def test_raw_json_uses_base_modifier_flags(
        self,
    ):
        store = self.make_store()

        binding = shortcut(
            0x39,
            (
                MOD_CONTROL
                | MOD_ALT
            ),
        )

        store.save(
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding,
                },
            )
        )

        payload = json.loads(
            store.file_path.read_text(
                encoding="utf-8"
            )
        )

        saved = payload[
            "bindings"
        ][
            ACTION_PLAY_PAUSE
        ]

        self.assertEqual(
            saved["modifiers"],
            (
                MOD_CONTROL
                | MOD_ALT
            ),
        )

        self.assertEqual(
            saved["virtual_key"],
            0x39,
        )

    def test_update_preserves_unspecified_values(
        self,
    ):
        store = self.make_store()

        binding = shortcut(
            0x31
        )

        store.save(
            MediaHotkeyPreferences(
                enabled=False,
                seek_seconds=12.0,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding,
                },
            )
        )

        updated = store.update(
            enabled=True
        )

        self.assertTrue(
            updated.enabled
        )

        self.assertEqual(
            updated.seek_seconds,
            12.0,
        )

        self.assertEqual(
            updated.bindings[
                ACTION_PLAY_PAUSE
            ],
            binding,
        )

    def test_update_can_replace_seek_amount(
        self,
    ):
        store = self.make_store()

        updated = store.update(
            seek_seconds=25.0
        )

        self.assertEqual(
            updated.seek_seconds,
            25.0,
        )

        self.assertEqual(
            store.load().seek_seconds,
            25.0,
        )

    def test_set_binding_persists_action(
        self,
    ):
        store = self.make_store()

        binding = shortcut(
            0x31
        )

        updated = store.set_binding(
            ACTION_PLAY_PAUSE,
            binding,
        )

        self.assertEqual(
            updated.bindings[
                ACTION_PLAY_PAUSE
            ],
            binding,
        )

        self.assertEqual(
            store.load().bindings[
                ACTION_PLAY_PAUSE
            ],
            binding,
        )

    def test_set_binding_can_replace_same_action(
        self,
    ):
        store = self.make_store()

        store.set_binding(
            ACTION_PLAY_PAUSE,
            shortcut(
                0x31
            ),
        )

        replacement = shortcut(
            0x32
        )

        updated = store.set_binding(
            ACTION_PLAY_PAUSE,
            replacement,
        )

        self.assertEqual(
            updated.bindings[
                ACTION_PLAY_PAUSE
            ],
            replacement,
        )

    def test_set_binding_rejects_binding_used_by_other_action(
        self,
    ):
        store = self.make_store()

        duplicate = shortcut(
            0x31
        )

        store.set_binding(
            ACTION_PLAY_PAUSE,
            duplicate,
        )

        with self.assertRaises(
            ValueError
        ):
            store.set_binding(
                ACTION_NEXT,
                duplicate,
            )

    def test_clear_binding_removes_only_one_action(
        self,
    ):
        store = self.make_store()

        store.save(
            MediaHotkeyPreferences(
                bindings={
                    ACTION_PLAY_PAUSE:
                        shortcut(
                            0x31
                        ),
                    ACTION_NEXT:
                        shortcut(
                            0x32
                        ),
                },
            )
        )

        updated = store.clear_binding(
            ACTION_PLAY_PAUSE
        )

        self.assertNotIn(
            ACTION_PLAY_PAUSE,
            updated.bindings,
        )

        self.assertIn(
            ACTION_NEXT,
            updated.bindings,
        )

    def test_clear_bindings_removes_every_binding(
        self,
    ):
        store = self.make_store()

        store.save(
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        shortcut(
                            0x31
                        ),
                    ACTION_NEXT:
                        shortcut(
                            0x32
                        ),
                },
            )
        )

        updated = (
            store.clear_bindings()
        )

        self.assertTrue(
            updated.enabled
        )

        self.assertEqual(
            updated.bindings,
            {},
        )

    def test_all_supported_actions_round_trip(
        self,
    ):
        store = self.make_store()

        actions = (
            ACTION_PLAY_PAUSE,
            ACTION_NEXT,
            ACTION_PREVIOUS,
            ACTION_SHUFFLE,
            ACTION_REPEAT,
            ACTION_SEEK_FORWARD,
            ACTION_SEEK_BACKWARD,
        )

        bindings = {
            action:
                shortcut(
                    0x31 + index
                )
            for index, action
            in enumerate(
                actions
            )
        }

        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings=bindings,
            )
        )

        store.save(
            preferences
        )

        self.assertEqual(
            store.load(),
            preferences,
        )

    def test_invalid_json_is_quarantined_and_replaced(
        self,
    ):
        store = self.make_store()

        store.file_path.write_text(
            "{ definitely not json",
            encoding="utf-8",
        )

        loaded = store.load()

        self.assertEqual(
            loaded,
            MediaHotkeyPreferences(),
        )

        self.assertTrue(
            store.file_path.exists()
        )

        quarantined = list(
            store.file_path.parent.glob(
                "media_hotkey_preferences"
                ".invalid-*.json"
            )
        )

        self.assertEqual(
            len(
                quarantined
            ),
            1,
        )

    def test_invalid_schema_is_quarantined_and_replaced(
        self,
    ):
        store = self.make_store()

        payload = {
            "schema_version": 999,
            "enabled": True,
            "seek_seconds": 10.0,
            "bindings": {},
        }

        store.file_path.write_text(
            json.dumps(
                payload
            ),
            encoding="utf-8",
        )

        loaded = store.load()

        self.assertEqual(
            loaded,
            MediaHotkeyPreferences(),
        )

        quarantined = list(
            store.file_path.parent.glob(
                "media_hotkey_preferences"
                ".invalid-*.json"
            )
        )

        self.assertEqual(
            len(
                quarantined
            ),
            1,
        )

    def test_duplicate_binding_payload_recovers_safely(
        self,
    ):
        store = self.make_store()

        duplicate_payload = {
            "modifiers":
                MOD_CONTROL,
            "virtual_key":
                0x31,
        }

        payload = {
            "schema_version":
                SCHEMA_VERSION,
            "enabled":
                True,
            "seek_seconds":
                10.0,
            "bindings": {
                ACTION_PLAY_PAUSE:
                    duplicate_payload,
                ACTION_NEXT:
                    dict(
                        duplicate_payload
                    ),
            },
        }

        store.file_path.write_text(
            json.dumps(
                payload
            ),
            encoding="utf-8",
        )

        loaded = store.load()

        self.assertEqual(
            loaded,
            MediaHotkeyPreferences(),
        )

    def test_save_leaves_no_temporary_file(
        self,
    ):
        store = self.make_store()

        store.save(
            MediaHotkeyPreferences(
                enabled=True,
                seek_seconds=20.0,
                bindings={
                    ACTION_PLAY_PAUSE:
                        shortcut(
                            0x31
                        ),
                },
            )
        )

        temporary_path = (
            store.file_path.with_name(
                store.file_path.name
                + ".tmp"
            )
        )

        self.assertFalse(
            temporary_path.exists()
        )

    def test_wrong_save_type_is_rejected(
        self,
    ):
        store = self.make_store()

        with self.assertRaises(
            TypeError
        ):
            store.save(
                {
                    "enabled": True
                }
            )


if __name__ == "__main__":
    unittest.main()
