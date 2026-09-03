from __future__ import annotations

import unittest

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY_ID,
)
from src.discord.presence_modes import (
    PresenceMode,
)
from src.discord.presence_presets import (
    LEGACY_SCHEMA_VERSION,
    PRESET_STORAGE_KIND,
    SCHEMA_VERSION,
    PresencePreset,
    PresencePresetError,
    PresencePresetStorage,
    PresencePresetStore,
    preset_from_dict,
    storage_from_dict,
)


USER_ENTRY_ID = (
    "discord_app_0123456789abcdef"
)

SECOND_ENTRY_ID = (
    "discord_app_fedcba9876543210"
)

PRESET_ID = (
    "presence_preset_0123456789abcdef"
)

LEGACY_PRESET_FIELDS = [
    "preset_id",
    "name",
    "mode",
    "title",
    "message",
    "image_path",
    "show_elapsed",
    "show_buttons",
    "buttons",
    "pinned",
    "created_at",
    "updated_at",
    "show_loop_count",
    "show_party",
    "party_current",
    "party_maximum",
]


def _preset_payload(
    *,
    application_entry_id_marker=False,
    application_entry_id=None,
):
    payload = {
        "id": PRESET_ID,
        "name": "Example",
        "mode": "custom",
        "title": "Floor 35",
        "message": "Solo",
    }

    if application_entry_id_marker:
        payload[
            "application_entry_id"
        ] = application_entry_id

    return payload


class _MemoryPresetStore(
    PresencePresetStore
):
    def __init__(
        self,
        presets=None,
    ):
        self._presets = list(
            presets or []
        )

    def load(self):
        return list(
            self._presets
        )

    def save(
        self,
        presets,
    ):
        normalized = [
            preset.normalized()
            for preset in presets
        ]

        self._presets = list(
            normalized
        )

        return PresencePresetStorage(
            presets=tuple(
                normalized
            )
        )


class PresencePresetApplicationSchemaTests(
    unittest.TestCase
):
    def test_schema_version_is_two(
        self,
    ):
        self.assertEqual(
            LEGACY_SCHEMA_VERSION,
            1,
        )

        self.assertEqual(
            SCHEMA_VERSION,
            2,
        )

    def test_application_field_is_append_only(
        self,
    ):
        fields = list(
            PresencePreset
            .__dataclass_fields__
            .keys()
        )

        self.assertEqual(
            fields[
                :len(
                    LEGACY_PRESET_FIELDS
                )
            ],
            LEGACY_PRESET_FIELDS,
        )

        self.assertEqual(
            fields[
                len(
                    LEGACY_PRESET_FIELDS
                ):
            ],
            [
                "application_entry_id",
            ],
        )

    def test_schema_one_storage_migrates_in_memory_to_two(
        self,
    ):
        storage = storage_from_dict(
            {
                "kind": PRESET_STORAGE_KIND,
                "schema_version": 1,
                "presets": [
                    _preset_payload(),
                ],
            }
        )

        self.assertEqual(
            storage.schema_version,
            SCHEMA_VERSION,
        )

        self.assertEqual(
            storage.to_dict()[
                "schema_version"
            ],
            SCHEMA_VERSION,
        )

    def test_schema_one_preset_keeps_identity_unspecified(
        self,
    ):
        storage = storage_from_dict(
            {
                "kind": PRESET_STORAGE_KIND,
                "schema_version": 1,
                "presets": [
                    _preset_payload(),
                ],
            }
        )

        preset = storage.presets[0]

        self.assertIsNone(
            preset.application_entry_id
        )

        self.assertIsNone(
            preset.to_presence_mode()
            .application_entry_id
        )

    def test_current_schema_missing_identity_is_unspecified(
        self,
    ):
        storage = storage_from_dict(
            {
                "kind": PRESET_STORAGE_KIND,
                "schema_version": SCHEMA_VERSION,
                "presets": [
                    _preset_payload(),
                ],
            }
        )

        self.assertIsNone(
            storage.presets[
                0
            ].application_entry_id
        )

    def test_future_schema_is_rejected(
        self,
    ):
        with self.assertRaises(
            PresencePresetError
        ):
            storage_from_dict(
                {
                    "kind": PRESET_STORAGE_KIND,
                    "schema_version": (
                        SCHEMA_VERSION + 1
                    ),
                    "presets": [],
                }
            )

    def test_schema_zero_is_rejected(
        self,
    ):
        with self.assertRaises(
            PresencePresetError
        ):
            storage_from_dict(
                {
                    "kind": PRESET_STORAGE_KIND,
                    "schema_version": 0,
                    "presets": [],
                }
            )


class PresencePresetApplicationReferenceTests(
    unittest.TestCase
):
    def test_user_entry_round_trip(
        self,
    ):
        original = PresencePreset(
            preset_id=PRESET_ID,
            name="Example",
            application_entry_id=(
                USER_ENTRY_ID
            ),
        )

        restored = preset_from_dict(
            original.to_dict()
        )

        self.assertEqual(
            restored.application_entry_id,
            USER_ENTRY_ID,
        )

    def test_builtin_entry_round_trip(
        self,
    ):
        original = PresencePreset(
            preset_id=PRESET_ID,
            name="Example",
            application_entry_id=(
                BUILTIN_APPLICATION_ENTRY_ID
            ),
        )

        restored = preset_from_dict(
            original.to_dict()
        )

        self.assertEqual(
            restored.application_entry_id,
            BUILTIN_APPLICATION_ENTRY_ID,
        )

    def test_valid_deleted_reference_shape_is_preserved(
        self,
    ):
        preset = preset_from_dict(
            _preset_payload(
                application_entry_id_marker=True,
                application_entry_id=(
                    USER_ENTRY_ID
                ),
            )
        )

        self.assertEqual(
            preset.application_entry_id,
            USER_ENTRY_ID,
        )

    def test_invalid_nonempty_reference_is_rejected(
        self,
    ):
        with self.assertRaises(
            PresencePresetError
        ):
            preset_from_dict(
                _preset_payload(
                    application_entry_id_marker=True,
                    application_entry_id=(
                        "../../not-an-entry"
                    ),
                )
            )

    def test_blank_reference_becomes_unspecified(
        self,
    ):
        preset = preset_from_dict(
            _preset_payload(
                application_entry_id_marker=True,
                application_entry_id="   ",
            )
        )

        self.assertIsNone(
            preset.application_entry_id
        )

    def test_disabled_preset_drops_application_assignment(
        self,
    ):
        preset = PresencePreset(
            preset_id=PRESET_ID,
            name="Disabled",
            mode="disabled",
            application_entry_id=(
                USER_ENTRY_ID
            ),
        ).normalized()

        self.assertIsNone(
            preset.application_entry_id
        )

    def test_to_presence_mode_forwards_reference(
        self,
    ):
        mode = PresencePreset(
            preset_id=PRESET_ID,
            name="Example",
            mode="custom",
            application_entry_id=(
                USER_ENTRY_ID
            ),
        ).to_presence_mode()

        self.assertEqual(
            mode.application_entry_id,
            USER_ENTRY_ID,
        )

    def test_dictionary_contains_application_reference(
        self,
    ):
        payload = PresencePreset(
            preset_id=PRESET_ID,
            name="Example",
            application_entry_id=(
                USER_ENTRY_ID
            ),
        ).to_dict()

        self.assertEqual(
            payload[
                "application_entry_id"
            ],
            USER_ENTRY_ID,
        )


class PresencePresetApplicationStoreTests(
    unittest.TestCase
):
    def test_create_copies_explicit_application_reference(
        self,
    ):
        store = _MemoryPresetStore()

        created = store.create(
            name="Example",
            presence_mode=PresenceMode(
                mode="custom",
                application_entry_id=(
                    USER_ENTRY_ID
                ),
            ),
        )

        self.assertEqual(
            created.application_entry_id,
            USER_ENTRY_ID,
        )

    def test_create_can_remain_unspecified_before_ui_picker_exists(
        self,
    ):
        store = _MemoryPresetStore()

        created = store.create(
            name="Example",
            presence_mode=PresenceMode(
                mode="custom"
            ),
        )

        self.assertIsNone(
            created.application_entry_id
        )

    def test_update_can_replace_explicit_application_reference(
        self,
    ):
        store = _MemoryPresetStore()

        created = store.create(
            name="Example",
            presence_mode=PresenceMode(
                mode="custom",
                application_entry_id=(
                    USER_ENTRY_ID
                ),
            ),
        )

        updated = store.update_from_mode(
            created.preset_id,
            name="Example",
            presence_mode=PresenceMode(
                mode="custom",
                application_entry_id=(
                    SECOND_ENTRY_ID
                ),
            ),
        )

        self.assertEqual(
            updated.application_entry_id,
            SECOND_ENTRY_ID,
        )

    def test_unaware_editor_update_preserves_existing_reference(
        self,
    ):
        store = _MemoryPresetStore()

        created = store.create(
            name="Example",
            presence_mode=PresenceMode(
                mode="custom",
                application_entry_id=(
                    USER_ENTRY_ID
                ),
            ),
        )

        updated = store.update_from_mode(
            created.preset_id,
            name="Edited",
            presence_mode=PresenceMode(
                mode="custom",
                title="Edited title",
                application_entry_id=None,
            ),
        )

        self.assertEqual(
            updated.application_entry_id,
            USER_ENTRY_ID,
        )

    def test_duplicate_preserves_application_reference(
        self,
    ):
        store = _MemoryPresetStore()

        created = store.create(
            name="Example",
            presence_mode=PresenceMode(
                mode="custom",
                application_entry_id=(
                    USER_ENTRY_ID
                ),
            ),
        )

        duplicate = store.duplicate(
            created.preset_id
        )

        self.assertEqual(
            duplicate.application_entry_id,
            USER_ENTRY_ID,
        )


if __name__ == "__main__":
    unittest.main()
