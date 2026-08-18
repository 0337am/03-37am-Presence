from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.discord.presence_controller import (
    PresenceController,
)
from src.discord.presence_link_buttons import (
    PresenceLinkButton,
    PresenceLinkButtonError,
)
from src.discord.presence_modes import (
    PresenceMode,
)
from src.discord.presence_presets import (
    SCHEMA_VERSION,
    PresencePreset,
    PresencePresetError,
    PresencePresetStorage,
    PresencePresetStore,
    preset_from_dict,
)


def make_buttons():
    return (
        PresenceLinkButton(
            label="Website",
            url="https://example.com/",
        ),
        PresenceLinkButton(
            label="Discord",
            url="https://discord.com/",
        ),
    )


class FakeSettings:
    def __init__(
        self,
        initial=None,
    ):
        self.data = dict(
            initial or {}
        )
        self.sync_count = 0

    def value(
        self,
        key,
        default=None,
        type=None,
    ):
        value = self.data.get(
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
        self.data[
            key
        ] = value

    def sync(
        self,
    ):
        self.sync_count += 1


class MemoryPresetStore(
    PresencePresetStore
):
    def __init__(
        self,
    ):
        self.presets = []

    def load(
        self,
    ):
        return list(
            self.presets
        )

    def save(
        self,
        presets,
    ):
        self.presets = [
            preset.normalized()
            for preset in presets
        ]

        return PresencePresetStorage(
            presets=tuple(
                self.presets
            )
        )

    def get(
        self,
        preset_id,
    ):
        for preset in self.presets:
            if (
                preset.preset_id
                == preset_id
            ):
                return preset

        return None

    def upsert(
        self,
        preset,
    ):
        preset = preset.normalized()

        replaced = False
        updated = []

        for existing in self.presets:
            if (
                existing.preset_id
                == preset.preset_id
            ):
                updated.append(
                    preset
                )
                replaced = True
            else:
                updated.append(
                    existing
                )

        if not replaced:
            updated.append(
                preset
            )

        self.presets = updated

        return preset

    def copy_image_for_preset(
        self,
        image_path,
        preset_id,
    ):
        return ""


class PresencePresetLinkButtonTests(
    unittest.TestCase
):
    def test_schema_version_remains_one(
        self,
    ):
        self.assertEqual(
            SCHEMA_VERSION,
            1,
        )

    def test_old_schema_one_preset_defaults_buttons_off(
        self,
    ):
        preset = preset_from_dict(
            {
                "id": "old-preset",
                "name": "Old Preset",
                "mode": "custom",
                "title": "Old",
                "message": "Still works",
                "image_path": "",
                "show_elapsed": False,
                "pinned": False,
                "created_at": (
                    "2026-08-15T00:00:00Z"
                ),
                "updated_at": (
                    "2026-08-15T00:00:00Z"
                ),
            }
        )

        self.assertFalse(
            preset.show_buttons
        )

        self.assertEqual(
            preset.buttons,
            (),
        )

    def test_preset_dictionary_round_trip_preserves_buttons(
        self,
    ):
        original = PresencePreset(
            preset_id="button-preset",
            name="Links",
            mode="custom",
            title="Find me",
            message="Useful links",
            show_buttons=True,
            buttons=make_buttons(),
        ).normalized()

        data = original.to_dict()

        self.assertTrue(
            data[
                "show_buttons"
            ]
        )

        self.assertEqual(
            len(
                data[
                    "buttons"
                ]
            ),
            2,
        )

        restored = preset_from_dict(
            data
        )

        self.assertEqual(
            restored.buttons,
            original.buttons,
        )

        self.assertTrue(
            restored.show_buttons
        )

    def test_preset_to_presence_mode_preserves_buttons(
        self,
    ):
        preset = PresencePreset(
            preset_id="button-preset",
            name="Links",
            mode="working",
            show_buttons=False,
            buttons=make_buttons(),
        ).normalized()

        mode = preset.to_presence_mode()

        self.assertFalse(
            mode.show_buttons
        )

        self.assertEqual(
            mode.buttons,
            make_buttons(),
        )

    def test_music_presets_keep_buttons_and_disabled_suppresses_buttons(
        self,
    ):
        music = PresencePreset(
            preset_id="music-preset",
            name="Music",
            mode="music",
            show_buttons=True,
            buttons=make_buttons(),
        ).normalized()

        self.assertTrue(
            music.show_buttons
        )

        self.assertEqual(
            music.buttons,
            make_buttons(),
        )

        disabled = PresencePreset(
            preset_id="disabled-preset",
            name="Disabled",
            mode="disabled",
            show_buttons=True,
            buttons=make_buttons(),
        ).normalized()

        self.assertFalse(
            disabled.show_buttons
        )

        self.assertEqual(
            disabled.buttons,
            (),
        )

    def test_invalid_preset_button_is_wrapped_as_preset_error(
        self,
    ):
        with self.assertRaises(
            PresencePresetError
        ):
            PresencePreset(
                preset_id="unsafe",
                name="Unsafe",
                mode="custom",
                show_buttons=True,
                buttons=(
                    {
                        "label": "Unsafe",
                        "url": (
                            "file:///secret.txt"
                        ),
                    },
                ),
            ).normalized()

    def test_create_preserves_hidden_button_configuration(
        self,
    ):
        store = MemoryPresetStore()

        preset = store.create(
            name="Hidden Links",
            presence_mode=PresenceMode(
                mode="afk",
                title="Away",
                message="Back later",
                show_buttons=False,
                buttons=make_buttons(),
            ),
        )

        self.assertFalse(
            preset.show_buttons
        )

        self.assertEqual(
            preset.buttons,
            make_buttons(),
        )

    def test_update_from_mode_replaces_button_configuration(
        self,
    ):
        store = MemoryPresetStore()

        preset = store.create(
            name="Links",
            presence_mode=PresenceMode(
                mode="custom",
                show_buttons=False,
                buttons=(
                    make_buttons()[0],
                ),
            ),
        )

        updated = store.update_from_mode(
            preset.preset_id,
            name=preset.name,
            presence_mode=PresenceMode(
                mode="custom",
                show_buttons=True,
                buttons=make_buttons(),
            ),
        )

        self.assertTrue(
            updated.show_buttons
        )

        self.assertEqual(
            updated.buttons,
            make_buttons(),
        )

    def test_duplicate_inherits_buttons_but_not_pin(
        self,
    ):
        store = MemoryPresetStore()

        source = store.create(
            name="Links",
            presence_mode=PresenceMode(
                mode="custom",
                show_buttons=True,
                buttons=make_buttons(),
            ),
            pinned=True,
        )

        duplicate = store.duplicate(
            source.preset_id
        )

        self.assertTrue(
            duplicate.show_buttons
        )

        self.assertEqual(
            duplicate.buttons,
            source.buttons,
        )

        self.assertFalse(
            duplicate.pinned
        )


class PresenceControllerLinkButtonPersistenceTests(
    unittest.TestCase
):
    def make_controller_proxy(
        self,
        settings,
    ):
        return SimpleNamespace(
            store=settings
        )

    def test_missing_saved_fields_default_off(
        self,
    ):
        settings = FakeSettings()

        mode = PresenceController.load_mode(
            self.make_controller_proxy(
                settings
            ),
            "custom",
        )

        self.assertFalse(
            mode.show_buttons
        )

        self.assertEqual(
            mode.buttons,
            (),
        )

    def test_hidden_buttons_round_trip_through_settings(
        self,
    ):
        settings = FakeSettings()
        proxy = self.make_controller_proxy(
            settings
        )

        original = PresenceMode(
            mode="custom",
            title="Links",
            message="Hidden for now",
            show_buttons=False,
            buttons=make_buttons(),
        )

        PresenceController.save_mode(
            proxy,
            original,
        )

        restored = PresenceController.load_mode(
            proxy,
            "custom",
        )

        self.assertFalse(
            restored.show_buttons
        )

        self.assertEqual(
            restored.buttons,
            make_buttons(),
        )

        self.assertIn(
            "presence/custom/buttons",
            settings.data,
        )

    def test_enabled_buttons_round_trip_through_settings(
        self,
    ):
        settings = FakeSettings()
        proxy = self.make_controller_proxy(
            settings
        )

        original = PresenceMode(
            mode="working",
            title="Working",
            message="Busy",
            show_buttons=True,
            buttons=make_buttons(),
        )

        PresenceController.save_mode(
            proxy,
            original,
        )

        restored = PresenceController.load_mode(
            proxy,
            "working",
        )

        self.assertTrue(
            restored.show_buttons
        )

        self.assertEqual(
            restored.buttons,
            make_buttons(),
        )

    def test_malformed_saved_buttons_fail_closed(
        self,
    ):
        settings = FakeSettings(
            {
                (
                    "presence/custom/"
                    "show_buttons"
                ): True,
                (
                    "presence/custom/"
                    "buttons"
                ): "{not-json",
            }
        )

        mode = PresenceController.load_mode(
            self.make_controller_proxy(
                settings
            ),
            "custom",
        )

        self.assertFalse(
            mode.show_buttons
        )

        self.assertEqual(
            mode.buttons,
            (),
        )

    def test_invalid_button_save_does_not_partially_write_settings(
        self,
    ):
        settings = FakeSettings()
        proxy = self.make_controller_proxy(
            settings
        )

        invalid = PresenceMode(
            mode="custom",
            title="Unsafe",
            show_buttons=True,
            buttons=(
                {
                    "label": "Unsafe",
                    "url": "file:///secret",
                },
            ),
        )

        with self.assertRaises(
            PresenceLinkButtonError
        ):
            PresenceController.save_mode(
                proxy,
                invalid,
            )

        self.assertEqual(
            settings.data,
            {},
        )

        self.assertEqual(
            settings.sync_count,
            0,
        )

    def test_music_round_trips_button_configuration(
        self,
    ):
        settings = FakeSettings()

        proxy = self.make_controller_proxy(
            settings
        )

        PresenceController.save_mode(
            proxy,
            PresenceMode(
                mode="music",
                show_buttons=True,
                buttons=make_buttons(),
            ),
        )

        self.assertEqual(
            settings.data.get(
                "presence/active_mode"
            ),
            "music",
        )

        self.assertTrue(
            settings.data.get(
                "presence/music/show_buttons"
            )
        )

        self.assertIn(
            "presence/music/buttons",
            settings.data,
        )

        restored = PresenceController.load_mode(
            proxy,
            "music",
        )

        self.assertTrue(
            restored.show_buttons
        )

        self.assertEqual(
            restored.buttons,
            make_buttons(),
        )


if __name__ == "__main__":
    unittest.main()
