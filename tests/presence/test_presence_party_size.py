from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.discord.presence_controller import (
    PresenceController,
)
from src.discord.presence_modes import (
    PresenceMode,
)
from src.discord.presence_presets import (
    SCHEMA_VERSION,
    PresencePreset,
    PresencePresetStore,
    preset_from_dict,
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
            return bool(value)

        return value

    def setValue(
        self,
        key,
        value,
    ):
        self.data[key] = value

    def sync(self):
        self.sync_count += 1


class FakeDiscord:
    def __init__(self):
        self.custom_updates = []
        self.clear_count = 0

    def update_custom(
        self,
        **options,
    ):
        self.custom_updates.append(
            dict(options)
        )

    def clear_presence(self):
        self.clear_count += 1


class PresencePartyModeTests(
    unittest.TestCase
):
    def test_custom_party_can_be_enabled(self):
        mode = PresenceMode(
            mode="custom",
            show_party=True,
            party_current=1,
            party_maximum=2,
        )

        self.assertTrue(
            mode.party_enabled()
        )

        self.assertEqual(
            mode.discord_party_size(),
            [1, 2],
        )

    def test_disabled_party_keeps_saved_numbers(self):
        mode = PresenceMode(
            mode="custom",
            show_party=False,
            party_current=4,
            party_maximum=10,
        )

        self.assertFalse(
            mode.party_enabled()
        )

        self.assertEqual(
            mode.normalized_party_size(),
            (4, 10),
        )

        self.assertIsNone(
            mode.discord_party_size()
        )

    def test_party_is_custom_presence_only(self):
        for name in (
            "music",
            "afk",
            "sleep",
            "working",
            "disabled",
        ):
            with self.subTest(
                mode=name
            ):
                mode = PresenceMode(
                    mode=name,
                    show_party=True,
                    party_current=3,
                    party_maximum=6,
                )

                self.assertFalse(
                    mode.party_enabled()
                )

                self.assertIsNone(
                    mode.discord_party_size()
                )

    def test_party_values_are_bounded_and_consistent(self):
        mode = PresenceMode(
            mode="custom",
            show_party=True,
            party_current="7",
            party_maximum="2",
        )

        self.assertEqual(
            mode.normalized_party_size(),
            (7, 7),
        )

        invalid = PresenceMode(
            mode="custom",
            show_party=True,
            party_current="invalid",
            party_maximum=None,
        )

        self.assertEqual(
            invalid.normalized_party_size(),
            (1, 2),
        )


class PresencePartySettingsTests(
    unittest.TestCase
):
    def make_controller(
        self,
        initial=None,
    ):
        controller = PresenceController(
            FakeDiscord()
        )

        controller.store = FakeSettings(
            initial
        )

        return controller

    def test_old_settings_default_party_off(self):
        controller = self.make_controller()

        mode = controller.load_mode(
            "custom"
        )

        self.assertFalse(
            mode.show_party
        )

        self.assertEqual(
            mode.normalized_party_size(),
            (1, 2),
        )

    def test_hidden_party_numbers_round_trip(self):
        controller = self.make_controller()

        controller.save_mode(
            PresenceMode(
                mode="custom",
                title="Floor 22",
                message="Exploring",
                show_party=False,
                party_current=4,
                party_maximum=10,
            )
        )

        restored = controller.load_mode(
            "custom"
        )

        self.assertFalse(
            restored.show_party
        )

        self.assertEqual(
            restored.normalized_party_size(),
            (4, 10),
        )

    def test_enabled_party_round_trips(self):
        controller = self.make_controller()

        controller.save_mode(
            PresenceMode(
                mode="custom",
                show_party=True,
                party_current=1,
                party_maximum=2,
            )
        )

        restored = controller.load_mode(
            "custom"
        )

        self.assertTrue(
            restored.show_party
        )

        self.assertEqual(
            restored.discord_party_size(),
            [1, 2],
        )

    def test_apply_custom_forwards_native_party_size(self):
        discord = FakeDiscord()

        controller = PresenceController(
            discord
        )

        controller.store = FakeSettings()

        controller.apply_mode(
            PresenceMode(
                mode="custom",
                title="Floor 22",
                message="Exploring",
                show_party=True,
                party_current=1,
                party_maximum=2,
            )
        )

        self.assertEqual(
            discord.custom_updates[-1][
                "party_size"
            ],
            [1, 2],
        )

    def test_non_custom_apply_forwards_no_party(self):
        discord = FakeDiscord()

        controller = PresenceController(
            discord
        )

        controller.store = FakeSettings()

        controller.apply_mode(
            PresenceMode(
                mode="working",
                title="Working",
                message="Busy",
                show_party=True,
                party_current=4,
                party_maximum=8,
            )
        )

        self.assertIsNone(
            discord.custom_updates[-1][
                "party_size"
            ]
        )


class PresencePartyPresetTests(
    unittest.TestCase
):
    def test_schema_one_old_preset_defaults_party_off(self):
        self.assertEqual(
            SCHEMA_VERSION,
            1,
        )

        preset = preset_from_dict(
            {
                "id": "presence_preset_0123456789abcdef",
                "name": "Legacy",
                "mode": "custom",
                "title": "Old custom",
                "message": "Still valid",
                "image_path": "",
                "show_elapsed": False,
                "show_buttons": False,
                "buttons": [],
                "pinned": False,
                "created_at": "",
                "updated_at": "",
            }
        )

        self.assertFalse(
            preset.show_party
        )

        self.assertEqual(
            (
                preset.party_current,
                preset.party_maximum,
            ),
            (1, 2),
        )

        self.assertIsNone(
            preset.to_presence_mode()
            .discord_party_size()
        )

    def test_custom_party_preset_dictionary_round_trip(self):
        original = PresencePreset(
            preset_id=(
                "presence_preset_1111111111111111"
            ),
            name="Floor 22",
            mode="custom",
            title="Floor 22",
            message="Exploring",
            show_party=True,
            party_current=1,
            party_maximum=2,
        ).normalized()

        data = original.to_dict()

        self.assertTrue(
            data["show_party"]
        )

        self.assertEqual(
            data["party_current"],
            1,
        )

        self.assertEqual(
            data["party_maximum"],
            2,
        )

        restored = preset_from_dict(
            data
        )

        self.assertEqual(
            restored.to_presence_mode()
            .discord_party_size(),
            [1, 2],
        )

    def test_hidden_custom_party_preserves_numbers(self):
        preset = PresencePreset(
            preset_id=(
                "presence_preset_2222222222222222"
            ),
            name="Hidden party",
            mode="custom",
            show_party=False,
            party_current=4,
            party_maximum=10,
        ).normalized()

        self.assertFalse(
            preset.show_party
        )

        self.assertEqual(
            (
                preset.party_current,
                preset.party_maximum,
            ),
            (4, 10),
        )

        restored = preset_from_dict(
            preset.to_dict()
        )

        self.assertFalse(
            restored.show_party
        )

        self.assertEqual(
            (
                restored.party_current,
                restored.party_maximum,
            ),
            (4, 10),
        )

    def test_non_custom_preset_cannot_enable_party(self):
        for mode in (
            "music",
            "afk",
            "sleep",
            "working",
            "disabled",
        ):
            with self.subTest(
                mode=mode
            ):
                preset = PresencePreset(
                    preset_id=(
                        "presence_preset_3333333333333333"
                    ),
                    name="Not custom",
                    mode=mode,
                    show_party=True,
                    party_current=3,
                    party_maximum=8,
                ).normalized()

                self.assertFalse(
                    preset.show_party
                )

                self.assertIsNone(
                    preset.to_presence_mode()
                    .discord_party_size()
                )

    def test_store_create_update_and_duplicate_preserve_party(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            )

            store = PresencePresetStore(
                storage_path=(
                    root
                    / "presence_presets.json"
                ),
                image_directory=(
                    root
                    / "images"
                ),
            )

            created = store.create(
                name="Party",
                presence_mode=PresenceMode(
                    mode="custom",
                    title="Floor 22",
                    message="Exploring",
                    show_party=True,
                    party_current=2,
                    party_maximum=6,
                ),
            )

            self.assertTrue(
                created.show_party
            )

            self.assertEqual(
                (
                    created.party_current,
                    created.party_maximum,
                ),
                (2, 6),
            )

            duplicate = store.duplicate(
                created.preset_id
            )

            self.assertTrue(
                duplicate.show_party
            )

            self.assertEqual(
                (
                    duplicate.party_current,
                    duplicate.party_maximum,
                ),
                (2, 6),
            )

            updated = store.update_from_mode(
                created.preset_id,
                name=created.name,
                presence_mode=PresenceMode(
                    mode="custom",
                    title="Floor 22",
                    message="Exploring",
                    show_party=False,
                    party_current=5,
                    party_maximum=12,
                ),
            )

            self.assertFalse(
                updated.show_party
            )

            self.assertEqual(
                (
                    updated.party_current,
                    updated.party_maximum,
                ),
                (5, 12),
            )

            reloaded = store.get(
                created.preset_id
            )

            self.assertIsNotNone(
                reloaded
            )

            self.assertFalse(
                reloaded.show_party
            )

            self.assertEqual(
                (
                    reloaded.party_current,
                    reloaded.party_maximum,
                ),
                (5, 12),
            )


if __name__ == "__main__":
    unittest.main()
