from __future__ import annotations

import unittest
from pathlib import Path


class DiscordApplicationLibrarySettingsWiringTests(
    unittest.TestCase
):
    @staticmethod
    def settings_source() -> str:
        return Path(
            "src/ui/settings.py"
        ).read_text(
            encoding="utf-8-sig"
        )

    @staticmethod
    def main_window_source() -> str:
        return Path(
            "src/ui/main_window.py"
        ).read_text(
            encoding="utf-8-sig"
        )

    def test_settings_accepts_application_store_dependency(
        self,
    ):
        source = self.settings_source()

        self.assertIn(
            "discord_application_store=None,",
            source,
        )

        self.assertIn(
            "self.discord_application_store = (",
            source,
        )

        self.assertIn(
            "discord_application_store\n"
            "        )",
            source,
        )

    def test_settings_constructs_card_from_shared_store(
        self,
    ):
        source = self.settings_source()

        self.assertIn(
            (
                "from src.ui."
                "discord_application_library_card import ("
            ),
            source,
        )

        start = source.index(
            "self.discord_application_library_card = ("
        )

        end = source.index(
            "self.discord_identity_card = (",
            start,
        )

        construction = source[
            start:end
        ]

        self.assertIn(
            "DiscordApplicationLibrarySettingsCard(",
            construction,
        )

        self.assertIn(
            "application_store=(",
            construction,
        )

        self.assertIn(
            "self.discord_application_store",
            construction,
        )

    def test_application_messages_route_to_discord_status(
        self,
    ):
        source = self.settings_source()

        start = source.index(
            (
                "self.discord_application_library_card."
                "message_changed.connect("
            )
        )

        end = source.index(
            "self.discord_identity_card = (",
            start,
        )

        wiring = source[
            start:end
        ]

        self.assertIn(
            "self.set_status_message(",
            wiring,
        )

        self.assertIn(
            'category="discord"',
            wiring,
        )

    def test_card_is_registered_in_discord_category(
        self,
    ):
        source = self.settings_source()

        self.assertIn(
            '"discord_applications": (',
            source,
        )

        self.assertIn(
            '"discord_applications": "discord",',
            source,
        )

        start = source.index(
            '"discord": (\n'
        )

        end = source.index(
            '"customization": (',
            start,
        )

        category = source[
            start:end
        ]

        application_index = category.index(
            "self.discord_application_library_card"
        )

        identity_index = category.index(
            "self.discord_identity_card"
        )

        self.assertLess(
            application_index,
            identity_index,
        )

    def test_library_has_explicit_deep_links(
        self,
    ):
        source = self.settings_source()

        self.assertIn(
            (
                '"discord applications": '
                '"discord_applications"'
            ),
            source,
        )

        self.assertIn(
            (
                '"discord application library": '
                '"discord_applications"'
            ),
            source,
        )

        self.assertIn(
            (
                '"application library": '
                '"discord_applications"'
            ),
            source,
        )

        self.assertIn(
            '"discord": "discord_identity"',
            source,
        )

        self.assertIn(
            '"application id": "discord_identity"',
            source,
        )

    def test_main_window_passes_shared_store(
        self,
    ):
        source = self.main_window_source()

        start = source.index(
            "self.settings_page = SettingsPage("
        )

        end = source.index(
            "self.spotify_local_candidate_snapshot = (",
            start,
        )

        handoff = source[
            start:end
        ]

        self.assertIn(
            "discord_application_store=(",
            handoff,
        )

        self.assertIn(
            "self.discord_application_library_store",
            handoff,
        )

        self.assertEqual(
            handoff.count(
                "self.discord_application_library_store"
            ),
            1,
        )

    def test_reset_all_preserves_application_library(
        self,
    ):
        source = self.settings_source()

        start = source.index(
            "    def reset_settings(self):"
        )

        end = source.find(
            "\n    def ",
            start + 8,
        )

        reset_source = (
            source[start:]
            if end < 0
            else source[
                start:end
            ]
        )

        self.assertNotIn(
            "discord_application_library_card",
            reset_source,
        )

        self.assertNotIn(
            "discord_application_store",
            reset_source,
        )

        self.assertIn(
            "self.discord_identity_card.reset_preferences()",
            reset_source,
        )


if __name__ == "__main__":
    unittest.main()
