from __future__ import annotations

import os
import unittest


os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
)

from src.ui.welcome import (
    ACTION_DISCORD_PRESENCE,
    ACTION_GET_STARTED,
    ACTION_MEDIA_HOTKEYS,
    ACTION_MEDIA_SOURCES,
    WelcomeDialog,
)


TEST_THEME = {
    "background": "#101010",
    "card": "#202020",
    "card_alt": "#303030",
    "accent": "#ff77aa",
    "text": "#fefefe",
    "muted": "#aaaaaa",
    "border": "#555555",
}


class WelcomeDialogTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication(
                [
                    "welcome-ui-tests"
                ]
            )
        )

    def setUp(self):
        self.dialog = (
            WelcomeDialog(
                theme=TEST_THEME
            )
        )

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()
        self.app.processEvents()

    def test_dialog_has_expected_first_launch_copy(
        self,
    ):
        self.assertEqual(
            self.dialog.windowTitle(),
            "Welcome to 03:37am Presence",
        )

        self.assertFalse(
            self.dialog.isModal()
        )

        self.assertEqual(
            len(
                self.dialog.action_buttons
            ),
            3,
        )

    def test_all_setup_actions_are_available(
        self,
    ):
        self.assertEqual(
            set(
                self.dialog.action_buttons
            ),
            {
                ACTION_MEDIA_SOURCES,
                ACTION_DISCORD_PRESENCE,
                ACTION_MEDIA_HOTKEYS,
            },
        )

    def test_music_button_emits_media_source_action(
        self,
    ):
        actions = []

        self.dialog.action_requested.connect(
            actions.append
        )

        self.dialog.action_buttons[
            ACTION_MEDIA_SOURCES
        ].click()

        self.assertEqual(
            actions,
            [
                ACTION_MEDIA_SOURCES
            ],
        )

    def test_discord_button_emits_presence_action(
        self,
    ):
        actions = []

        self.dialog.action_requested.connect(
            actions.append
        )

        self.dialog.action_buttons[
            ACTION_DISCORD_PRESENCE
        ].click()

        self.assertEqual(
            actions,
            [
                ACTION_DISCORD_PRESENCE
            ],
        )

    def test_hotkey_button_emits_hotkey_action(
        self,
    ):
        actions = []

        self.dialog.action_requested.connect(
            actions.append
        )

        self.dialog.action_buttons[
            ACTION_MEDIA_HOTKEYS
        ].click()

        self.assertEqual(
            actions,
            [
                ACTION_MEDIA_HOTKEYS
            ],
        )

    def test_get_started_emits_completion_action(
        self,
    ):
        actions = []

        self.dialog.action_requested.connect(
            actions.append
        )

        self.dialog.get_started_button.click()

        self.assertEqual(
            actions,
            [
                ACTION_GET_STARTED
            ],
        )

    def test_not_now_rejects_without_action(
        self,
    ):
        actions = []

        self.dialog.action_requested.connect(
            actions.append
        )

        self.dialog.not_now_button.click()

        self.assertEqual(
            actions,
            [],
        )

        self.assertEqual(
            self.dialog.result(),
            QDialog.DialogCode.Rejected,
        )

    def test_unknown_action_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            self.dialog.request_action(
                "turn_everything_on"
            )

    def test_theme_is_applied_to_dialog_stylesheet(
        self,
    ):
        stylesheet = (
            self.dialog.styleSheet()
        )

        for value in TEST_THEME.values():
            self.assertIn(
                value,
                stylesheet,
            )


if __name__ == "__main__":
    unittest.main()
