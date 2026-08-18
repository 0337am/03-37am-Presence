from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from src.discord.identity_preferences import (
    DEFAULT_DISCORD_APPLICATION_ID,
    IDENTITY_MODE_CUSTOM,
    IDENTITY_MODE_DEFAULT,
    DiscordIdentityPreferencesStore,
)
from src.ui.discord_identity_card import (
    DiscordIdentitySettingsCard,
)


CUSTOM_APPLICATION_ID = (
    "123456789012345678"
)


class FakeDiscordIdentityRuntime:
    def __init__(self):
        self.requests = []

    def request_client_id(
        self,
        client_id,
    ):
        self.requests.append(
            client_id
        )
        return client_id


class DiscordIdentitySettingsUiTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def setUp(self):
        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        settings_path = (
            Path(
                self.temp_directory.name
            )
            / "discord-identity.ini"
        )

        self.settings = QSettings(
            str(settings_path),
            QSettings.Format.IniFormat,
        )

        self.store = (
            DiscordIdentityPreferencesStore(
                self.settings
            )
        )

        self.runtime = (
            FakeDiscordIdentityRuntime()
        )

        self.card = (
            DiscordIdentitySettingsCard(
                preference_store=self.store,
                runtime=self.runtime,
            )
        )

        self.app.processEvents()

    def tearDown(self):
        self.card.close()
        self.card.deleteLater()
        self.app.processEvents()

        self.settings.clear()
        self.settings.sync()

        self.temp_directory.cleanup()

    def test_default_identity_is_selected_initially(self):
        self.assertTrue(
            self.card.default_box.isChecked()
        )

        self.assertFalse(
            self.card.custom_box.isChecked()
        )

        self.assertFalse(
            self.card.application_id_field.isEnabled()
        )

    def test_custom_mode_enables_application_id_field(self):
        self.card.custom_box.setChecked(
            True
        )

        self.app.processEvents()

        self.assertTrue(
            self.card.application_id_field.isEnabled()
        )

    def test_custom_identity_saves_and_requests_live_switch(self):
        self.card.custom_box.setChecked(
            True
        )

        self.card.application_id_field.setText(
            CUSTOM_APPLICATION_ID
        )

        result = (
            self.card.apply_preferences()
        )

        self.assertTrue(
            result
        )

        preferences = (
            self.store.load()
        )

        self.assertEqual(
            preferences.mode,
            IDENTITY_MODE_CUSTOM,
        )

        self.assertEqual(
            preferences.custom_application_id,
            CUSTOM_APPLICATION_ID,
        )

        self.assertEqual(
            self.runtime.requests,
            [
                CUSTOM_APPLICATION_ID,
            ],
        )

    def test_invalid_custom_identity_does_not_switch_runtime(self):
        self.card.custom_box.setChecked(
            True
        )

        self.card.application_id_field.setText(
            "invalid"
        )

        result = (
            self.card.apply_preferences()
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            self.runtime.requests,
            [],
        )

        preferences = (
            self.store.load()
        )

        self.assertEqual(
            preferences.mode,
            IDENTITY_MODE_DEFAULT,
        )

    def test_switching_back_to_default_requests_official_identity(self):
        self.card.custom_box.setChecked(
            True
        )

        self.card.application_id_field.setText(
            CUSTOM_APPLICATION_ID
        )

        self.assertTrue(
            self.card.apply_preferences()
        )

        self.card.default_box.setChecked(
            True
        )

        self.assertTrue(
            self.card.apply_preferences()
        )

        preferences = (
            self.store.load()
        )

        self.assertEqual(
            preferences.mode,
            IDENTITY_MODE_DEFAULT,
        )

        self.assertEqual(
            self.runtime.requests[-1],
            DEFAULT_DISCORD_APPLICATION_ID,
        )

    def test_reset_restores_official_identity(self):
        self.card.custom_box.setChecked(
            True
        )

        self.card.application_id_field.setText(
            CUSTOM_APPLICATION_ID
        )

        self.card.apply_preferences()

        self.card.reset_preferences()

        preferences = (
            self.store.load()
        )

        self.assertEqual(
            preferences.mode,
            IDENTITY_MODE_DEFAULT,
        )

        self.assertTrue(
            self.card.default_box.isChecked()
        )

        self.assertEqual(
            self.runtime.requests[-1],
            DEFAULT_DISCORD_APPLICATION_ID,
        )

    def test_warning_explicitly_rejects_secret_credentials(self):
        text = ""

        for label in self.card.findChildren(
            __import__(
                "PyQt6.QtWidgets",
                fromlist=["QLabel"],
            ).QLabel
        ):
            text += " " + label.text()

        lowered = text.lower()

        self.assertIn(
            "client secret",
            lowered,
        )

        self.assertIn(
            "bot token",
            lowered,
        )

        self.assertIn(
            "user token",
            lowered,
        )


class DiscordIdentitySettingsWiringTests(
    unittest.TestCase
):
    def test_settings_places_identity_card_in_discord_category(self):
        source = Path(
            "src/ui/settings.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "DiscordIdentitySettingsCard",
            source,
        )

        self.assertIn(
            '"discord_identity": (',
            source,
        )

        self.assertIn(
            "self.discord_identity_card,",
            source,
        )

    def test_main_window_shares_identity_store_and_runtime_with_settings(self):
        source = Path(
            "src/ui/main_window.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "discord_identity_store=(",
            source,
        )

        self.assertIn(
            "self.discord_identity_preferences_store",
            source,
        )

        self.assertIn(
            "discord_identity_runtime=(",
            source,
        )

        self.assertIn(
            "self.discord",
            source,
        )


if __name__ == "__main__":
    unittest.main()
