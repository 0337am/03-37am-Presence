import ast
import unittest

from src.discord.presence_modes import (
    PresenceMode,
)
from src.discord.presence_presets import (
    PresencePreset,
)
from tests.repo_paths import (
    REPO_ROOT,
)


PRESETS_PATH = (
    REPO_ROOT
    / "src"
    / "discord"
    / "presence_presets.py"
)


class PresenceLoopCountPresetTests(
    unittest.TestCase
):
    def test_preset_defaults_loop_count_off(
        self,
    ):
        preset = PresencePreset(
            preset_id="test",
            name="Music",
            mode="music",
        )

        self.assertFalse(
            preset.show_loop_count
        )

    def test_legacy_field_order_is_preserved(
        self,
    ):
        fields = list(
            PresencePreset
            .__dataclass_fields__
            .keys()
        )

        legacy_fields = [
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
        ]

        historical_party_fields = [
            "show_party",
            "party_current",
            "party_maximum",
        ]

        self.assertEqual(
            fields[
                :len(legacy_fields)
            ],
            legacy_fields,
        )

        party_start = len(
            legacy_fields
        )

        self.assertEqual(
            fields[
                party_start:
                party_start
                + len(
                    historical_party_fields
                )
            ],
            historical_party_fields,
        )

    def test_music_normalization_preserves_loop_count(
        self,
    ):
        preset = PresencePreset(
            preset_id="test",
            name="Music",
            mode="music",
            show_loop_count=True,
        ).normalized()

        self.assertTrue(
            preset.show_loop_count
        )

    def test_custom_normalization_suppresses_loop_count(
        self,
    ):
        preset = PresencePreset(
            preset_id="test",
            name="Custom",
            mode="custom",
            show_loop_count=True,
        ).normalized()

        self.assertFalse(
            preset.show_loop_count
        )

    def test_disabled_normalization_suppresses_loop_count(
        self,
    ):
        preset = PresencePreset(
            preset_id="test",
            name="Disabled",
            mode="disabled",
            show_loop_count=True,
        ).normalized()

        self.assertFalse(
            preset.show_loop_count
        )

    def test_music_preset_forwards_to_presence_mode(
        self,
    ):
        mode = PresencePreset(
            preset_id="test",
            name="Music",
            mode="music",
            show_loop_count=True,
        ).to_presence_mode()

        self.assertIsInstance(
            mode,
            PresenceMode,
        )

        self.assertTrue(
            mode.show_loop_count
        )

    def test_dictionary_serializes_loop_count(
        self,
    ):
        payload = PresencePreset(
            preset_id="test",
            name="Music",
            mode="music",
            show_loop_count=True,
        ).to_dict()

        self.assertTrue(
            payload[
                "show_loop_count"
            ]
        )

    def test_source_migrates_both_store_paths(
        self,
    ):
        source = PRESETS_PATH.read_text(
            encoding="utf-8-sig"
        )

        self.assertEqual(
            source.count(
                "show_loop_count="
                "presence_mode.show_loop_count"
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()