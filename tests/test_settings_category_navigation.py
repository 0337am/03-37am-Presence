from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication


class SettingsCategoryNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._previous_qt_platform = os.environ.get(
            "QT_QPA_PLATFORM"
        )
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    @classmethod
    def tearDownClass(cls):
        if cls._previous_qt_platform is None:
            os.environ.pop(
                "QT_QPA_PLATFORM",
                None,
            )
        else:
            os.environ[
                "QT_QPA_PLATFORM"
            ] = cls._previous_qt_platform

    def setUp(self):
        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        self._previous_local_app_data = (
            os.environ.get(
                "LOCALAPPDATA"
            )
        )

        os.environ[
            "LOCALAPPDATA"
        ] = self.temp_directory.name

        QSettings.setDefaultFormat(
            QSettings.Format.IniFormat
        )

        QSettings.setPath(
            QSettings.Format.IniFormat,
            QSettings.Scope.UserScope,
            self.temp_directory.name,
        )

        QSettings.setPath(
            QSettings.Format.IniFormat,
            QSettings.Scope.SystemScope,
            self.temp_directory.name,
        )

        startup_patcher = patch(
            "src.system.startup.StartupManager.is_enabled",
            return_value=False,
        )
        startup_set_patcher = patch(
            "src.system.startup.StartupManager.set_enabled",
            return_value=True,
        )

        self.addCleanup(
            startup_patcher.stop
        )
        self.addCleanup(
            startup_set_patcher.stop
        )

        startup_patcher.start()
        startup_set_patcher.start()

        from src.ui.settings import SettingsPage

        self.page = SettingsPage()
        self.app.processEvents()

    def tearDown(self):
        self.page.close()
        self.page.deleteLater()
        self.app.processEvents()

        if self._previous_local_app_data is None:
            os.environ.pop(
                "LOCALAPPDATA",
                None,
            )
        else:
            os.environ[
                "LOCALAPPDATA"
            ] = self._previous_local_app_data

        self.temp_directory.cleanup()

    def test_expected_categories_exist(self):
        self.assertEqual(
            set(
                self.page.settings_category_buttons
            ),
            {
                "general",
                "discord",
                "customization",
                "spotify",
                "local_music",
                "playback",
                "library_data",
                "updates",
                "advanced",
            },
        )

    def test_general_is_selected_initially(self):
        self.assertEqual(
            self.page._active_settings_category,
            "general",
        )

        self.assertTrue(
            self.page.settings_category_buttons[
                "general"
            ].isChecked()
        )

    def test_only_selected_category_cards_are_visible(self):
        for category in (
            self.page.settings_category_cards
        ):
            with self.subTest(
                category=category
            ):
                self.page._set_active_settings_category(
                    category
                )
                self.app.processEvents()

                for (
                    candidate_category,
                    cards,
                ) in (
                    self.page
                    .settings_category_cards
                    .items()
                ):
                    expected_visible = (
                        candidate_category
                        == category
                    )

                    for card in cards:
                        self.assertEqual(
                            not card.isHidden(),
                            expected_visible,
                        )

    def test_existing_deep_links_select_correct_category(self):
        expectations = {
            "startup": "general",
            "discord": "discord",
            "theme": "customization",
            "spotify": "spotify",
            "local files": "local_music",
            "hotkeys": "playback",
            "data": "library_data",
            "updates": "updates",
            "advanced": "advanced",
        }

        for (
            section,
            expected_category,
        ) in expectations.items():
            with self.subTest(
                section=section
            ):
                self.page.show_section(
                    section
                )
                self.app.processEvents()

                self.assertEqual(
                    self.page._active_settings_category,
                    expected_category,
                )

                self.assertTrue(
                    self.page.settings_category_buttons[
                        expected_category
                    ].isChecked()
                )

    def test_spotify_status_is_scoped_to_spotify(self):
        self.page.spotify_connection_card.message_changed.emit(
            "Spotify is connected."
        )
        self.app.processEvents()

        self.assertEqual(
            self.page.status.text(),
            "",
        )

        self.page._set_active_settings_category(
            "spotify"
        )

        self.assertEqual(
            self.page.status.text(),
            "Spotify is connected.",
        )

        self.page._set_active_settings_category(
            "playback"
        )

        self.assertEqual(
            self.page.status.text(),
            "",
        )

    def test_artwork_status_is_scoped_to_discord(self):
        self.page._set_active_settings_category(
            "playback"
        )

        self.page.artwork_hosting_card.message_changed.emit(
            "Artwork hosting connected."
        )

        self.app.processEvents()

        self.assertEqual(
            self.page.status.text(),
            "",
        )

        self.page._set_active_settings_category(
            "discord"
        )

        self.assertEqual(
            self.page.status.text(),
            "Artwork hosting connected.",
        )

    def test_generic_status_belongs_to_active_category(self):
        self.page._set_active_settings_category(
            "playback"
        )

        self.page.set_status_message(
            "Hotkeys saved."
        )

        self.assertEqual(
            self.page.status.text(),
            "Hotkeys saved.",
        )

        self.page._set_active_settings_category(
            "general"
        )

        self.assertEqual(
            self.page.status.text(),
            "",
        )

        self.page._set_active_settings_category(
            "playback"
        )

        self.assertEqual(
            self.page.status.text(),
            "Hotkeys saved.",
        )


if __name__ == "__main__":
    unittest.main()
