from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PyQt6.QtCore import QSettings

from src.discord.identity_preferences import (
    CUSTOM_APPLICATION_ID_SETTING_KEY,
    DEFAULT_DISCORD_APPLICATION_ID,
    IDENTITY_MODE_CUSTOM,
    IDENTITY_MODE_DEFAULT,
    MODE_SETTING_KEY,
    DiscordIdentityPreferences,
    DiscordIdentityPreferencesStore,
    safe_discord_application_id,
    validate_discord_application_id,
)
from src.discord.presence import DiscordPresence


CUSTOM_APPLICATION_ID = (
    "123456789012345678"
)


class DiscordIdentityValidationTests(
    unittest.TestCase
):
    def test_official_application_id_is_valid(self):
        self.assertEqual(
            validate_discord_application_id(
                DEFAULT_DISCORD_APPLICATION_ID
            ),
            DEFAULT_DISCORD_APPLICATION_ID,
        )

    def test_valid_custom_application_id_is_preserved(self):
        self.assertEqual(
            validate_discord_application_id(
                CUSTOM_APPLICATION_ID
            ),
            CUSTOM_APPLICATION_ID,
        )

    def test_application_id_rejects_non_digits(self):
        with self.assertRaises(
            ValueError
        ):
            validate_discord_application_id(
                "1234-not-discord"
            )

    def test_application_id_rejects_empty_value(self):
        with self.assertRaises(
            ValueError
        ):
            validate_discord_application_id(
                ""
            )

    def test_safe_application_id_falls_back_to_official(self):
        self.assertEqual(
            safe_discord_application_id(
                "invalid"
            ),
            DEFAULT_DISCORD_APPLICATION_ID,
        )


class DiscordIdentityPreferencesTests(
    unittest.TestCase
):
    def test_default_preferences_resolve_official_identity(self):
        preferences = (
            DiscordIdentityPreferences()
        )

        self.assertEqual(
            preferences.normalized_mode,
            IDENTITY_MODE_DEFAULT,
        )

        self.assertEqual(
            preferences.resolved_application_id,
            DEFAULT_DISCORD_APPLICATION_ID,
        )

        self.assertFalse(
            preferences.is_custom
        )

    def test_custom_preferences_resolve_custom_identity(self):
        preferences = (
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id=(
                    CUSTOM_APPLICATION_ID
                ),
            )
        )

        self.assertEqual(
            preferences.resolved_application_id,
            CUSTOM_APPLICATION_ID,
        )

        self.assertTrue(
            preferences.is_custom
        )

    def test_invalid_custom_identity_resolves_official_identity(self):
        preferences = (
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id="invalid",
            )
        )

        self.assertEqual(
            preferences.resolved_application_id,
            DEFAULT_DISCORD_APPLICATION_ID,
        )

        self.assertFalse(
            preferences.is_custom
        )


class DiscordIdentityPreferencesStoreTests(
    unittest.TestCase
):
    def setUp(self):
        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        settings_path = (
            Path(
                self.temp_directory.name
            )
            / "identity.ini"
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

    def tearDown(self):
        self.settings.clear()
        self.settings.sync()

        self.temp_directory.cleanup()

    def test_store_defaults_to_official_identity(self):
        preferences = self.store.load()

        self.assertEqual(
            preferences.mode,
            IDENTITY_MODE_DEFAULT,
        )

        self.assertEqual(
            preferences.resolved_application_id,
            DEFAULT_DISCORD_APPLICATION_ID,
        )

    def test_custom_identity_round_trip(self):
        saved = self.store.save(
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id=(
                    CUSTOM_APPLICATION_ID
                ),
            )
        )

        loaded = self.store.load()

        self.assertEqual(
            saved,
            loaded,
        )

        self.assertEqual(
            loaded.resolved_application_id,
            CUSTOM_APPLICATION_ID,
        )

    def test_invalid_saved_custom_identity_falls_back_safely(self):
        self.settings.setValue(
            MODE_SETTING_KEY,
            IDENTITY_MODE_CUSTOM,
        )

        self.settings.setValue(
            CUSTOM_APPLICATION_ID_SETTING_KEY,
            "not-a-valid-id",
        )

        self.settings.sync()

        loaded = self.store.load()

        self.assertEqual(
            loaded.mode,
            IDENTITY_MODE_DEFAULT,
        )

        self.assertEqual(
            loaded.resolved_application_id,
            DEFAULT_DISCORD_APPLICATION_ID,
        )

    def test_invalid_custom_identity_is_not_saved(self):
        with self.assertRaises(
            ValueError
        ):
            self.store.save(
                DiscordIdentityPreferences(
                    mode=IDENTITY_MODE_CUSTOM,
                    custom_application_id="bad",
                )
            )

        loaded = self.store.load()

        self.assertEqual(
            loaded.mode,
            IDENTITY_MODE_DEFAULT,
        )

    def test_switching_to_default_can_keep_valid_custom_id(self):
        self.store.save(
            DiscordIdentityPreferences(
                mode=IDENTITY_MODE_CUSTOM,
                custom_application_id=(
                    CUSTOM_APPLICATION_ID
                ),
            )
        )

        updated = self.store.update(
            mode=IDENTITY_MODE_DEFAULT
        )

        self.assertEqual(
            updated.mode,
            IDENTITY_MODE_DEFAULT,
        )

        self.assertEqual(
            updated.custom_application_id,
            CUSTOM_APPLICATION_ID,
        )

        self.assertEqual(
            updated.resolved_application_id,
            DEFAULT_DISCORD_APPLICATION_ID,
        )


class DiscordPresenceIdentityTests(
    unittest.TestCase
):
    def test_presence_uses_official_identity_by_default(self):
        presence = DiscordPresence(
            artwork_uploader=object()
        )

        self.assertEqual(
            presence.client_id,
            DEFAULT_DISCORD_APPLICATION_ID,
        )

    def test_presence_accepts_valid_custom_identity(self):
        presence = DiscordPresence(
            artwork_uploader=object(),
            client_id=CUSTOM_APPLICATION_ID,
        )

        self.assertEqual(
            presence.client_id,
            CUSTOM_APPLICATION_ID,
        )

    def test_presence_invalid_identity_falls_back_safely(self):
        presence = DiscordPresence(
            artwork_uploader=object(),
            client_id="invalid",
        )

        self.assertEqual(
            presence.client_id,
            DEFAULT_DISCORD_APPLICATION_ID,
        )


if __name__ == "__main__":
    unittest.main()
