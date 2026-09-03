from __future__ import annotations

import unittest
from pathlib import Path

from src.discord.extended_presence import (
    CustomPresenceUpdate,
    ExtendedDiscordPresence,
)
from src.discord.presence_modes import (
    PresenceMode,
)
from src.discord.presence_presets import (
    SCHEMA_VERSION,
    PresencePreset,
    preset_from_dict,
)


ROOT = Path(__file__).resolve().parents[2]

CONTROLLER_PATH = (
    ROOT
    / "src"
    / "discord"
    / "presence_controller.py"
)

STUDIO_PATH = (
    ROOT
    / "src"
    / "ui"
    / "presence_page.py"
)


class CaptureRpc:
    def __init__(self):
        self.updates = []

    def update(
        self,
        **options,
    ):
        self.updates.append(
            dict(options)
        )


class FakeArtworkUploader:
    is_configured = True

    def get_or_upload(
        self,
        image_bytes,
    ):
        if not image_bytes:
            return None

        return (
            "https://example.invalid/"
            "presence.png"
        )


def make_publisher():
    publisher = object.__new__(
        ExtendedDiscordPresence
    )

    publisher.rpc = CaptureRpc()
    publisher.artwork_uploader = (
        FakeArtworkUploader()
    )

    return publisher


def make_update(
    text,
):
    return CustomPresenceUpdate(
        title="Hi",
        message=":3",
        image_bytes=b"image",
        image_name=text,
        show_elapsed=False,
        started_at=None,
        buttons=(),
        party_size=None,
    )


class PresenceArtworkHoverTextTests(
    unittest.TestCase
):
    def test_blank_normalizes_empty(
        self,
    ):
        mode = PresenceMode(
            mode="custom",
            artwork_hover_text="",
        )

        self.assertEqual(
            mode.normalized_artwork_hover_text(),
            "",
        )

    def test_custom_text_is_cleaned_and_limited(
        self,
    ):
        mode = PresenceMode(
            mode="custom",
            artwork_hover_text=(
                "  Sword Art Online\x00  "
            ),
        )

        self.assertEqual(
            mode.normalized_artwork_hover_text(),
            "Sword Art Online",
        )

        long_mode = PresenceMode(
            mode="working",
            artwork_hover_text=(
                "x" * 200
            ),
        )

        self.assertEqual(
            len(
                long_mode
                .normalized_artwork_hover_text()
            ),
            128,
        )

    def test_music_and_disabled_ignore_hover(
        self,
    ):
        for mode_name in (
            "music",
            "disabled",
        ):
            mode = PresenceMode(
                mode=mode_name,
                artwork_hover_text="Hidden",
            )

            self.assertEqual(
                mode.normalized_artwork_hover_text(),
                "",
            )

    def test_blank_publisher_omits_large_text(
        self,
    ):
        publisher = make_publisher()

        publisher._publish_custom(
            make_update("")
        )

        options = publisher.rpc.updates[-1]

        self.assertIn(
            "large_image",
            options,
        )

        self.assertNotIn(
            "large_text",
            options,
        )

    def test_custom_publisher_uses_exact_text(
        self,
    ):
        publisher = make_publisher()

        publisher._publish_custom(
            make_update(
                "Sword Art Online"
            )
        )

        self.assertEqual(
            publisher.rpc.updates[-1][
                "large_text"
            ],
            "Sword Art Online",
        )

    def test_dedupe_key_includes_hover_text(
        self,
    ):
        blank = (
            ExtendedDiscordPresence
            ._make_presence_key(
                make_update("")
            )
        )

        custom = (
            ExtendedDiscordPresence
            ._make_presence_key(
                make_update(
                    "Sword Art Online"
                )
            )
        )

        self.assertNotEqual(
            blank,
            custom,
        )

    def test_preset_schema_remains_two_and_roundtrips(
        self,
    ):
        self.assertEqual(
            SCHEMA_VERSION,
            2,
        )

        preset = PresencePreset(
            preset_id=(
                "presence_preset_"
                "0123456789abcdef"
            ),
            name="AFK",
            mode="afk",
            artwork_hover_text=(
                "Away from keyboard"
            ),
        )

        payload = preset.to_dict()

        self.assertEqual(
            payload[
                "artwork_hover_text"
            ],
            "Away from keyboard",
        )

        restored = preset_from_dict(
            payload
        )

        self.assertEqual(
            restored.artwork_hover_text,
            "Away from keyboard",
        )

        self.assertEqual(
            restored
            .to_presence_mode()
            .artwork_hover_text,
            "Away from keyboard",
        )

    def test_legacy_preset_defaults_hover_blank(
        self,
    ):
        restored = preset_from_dict(
            {
                "id": (
                    "presence_preset_"
                    "0123456789abcdef"
                ),
                "name": "Legacy",
                "mode": "custom",
            }
        )

        self.assertEqual(
            restored.artwork_hover_text,
            "",
        )

    def test_controller_routes_primary_secondary_and_afk(
        self,
    ):
        source = CONTROLLER_PATH.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"artwork_hover_text"',
            source,
        )

        self.assertGreaterEqual(
            source.count(
                ".normalized_artwork_hover_text()"
            ),
            4,
        )

        self.assertIn(
            "afk_mode\n"
            "                "
            ".normalized_artwork_hover_text()",
            source,
        )

    def test_studio_collection_is_backward_compatible_and_link_safe(
        self,
    ):
        source = STUDIO_PATH.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"Artwork hover text"',
            source,
        )

        self.assertIn(
            '"Leave blank for no hover text"',
            source,
        )

        self.assertIn(
            '"artwork_hover_input"',
            source,
        )

        self.assertIn(
            'artwork_hover_text = ""',
            source,
        )

        self.assertIn(
            "hover_text_getter",
            source,
        )

        collector_start = source.index(
            "    def current_editor_presence_mode("
        )

        collector_end = source.index(
            "    def on_preset_changed(",
            collector_start,
        )

        collector = source[
            collector_start:collector_end
        ]

        self.assertNotIn(
            '"music",\n            "disabled"',
            collector,
        )


if __name__ == "__main__":
    unittest.main()
