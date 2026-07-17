from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

SETTINGS_PATH = (
    ROOT
    / "src"
    / "ui"
    / "settings.py"
)

CONTROLLER_PATH = (
    ROOT
    / "src"
    / "ui"
    / "update_controller.py"
)


class SettingsUpdateUiTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.settings_source = (
            SETTINGS_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

        cls.controller_source = (
            CONTROLLER_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

    def test_update_card_is_present(self):
        self.assertIn(
            '"Updates"',
            self.settings_source,
        )

        self.assertIn(
            '"Check for updates"',
            self.settings_source,
        )

        self.assertIn(
            "Installed version",
            self.settings_source,
        )

    def test_current_version_uses_metadata(self):
        self.assertIn(
            (
                "from src.version import "
                "APP_VERSION, RELEASE_NAME"
            ),
            self.settings_source,
        )

        self.assertIn(
            'f"v{APP_VERSION}',
            self.settings_source,
        )

    def test_settings_uses_controller(self):
        self.assertIn(
            "UpdateCheckController",
            self.settings_source,
        )

        self.assertIn(
            "describe_update_result",
            self.settings_source,
        )

        self.assertIn(
            "self.update_controller",
            self.settings_source,
        )

        self.assertIn(
            ".start_check()",
            self.settings_source,
        )

    def test_update_labels_use_existing_style(self):
        self.assertGreaterEqual(
            self.settings_source.count(
                '"helpText"'
            ),
            2,
        )

        self.assertNotIn(
            '"helperText"',
            self.settings_source,
        )

    def test_update_card_is_navigable(self):
        self.assertIn(
            '"updates": updates',
            self.settings_source,
        )

    def test_patch_does_not_download_or_install(self):
        self.assertNotIn(
            "update_downloader",
            self.settings_source,
        )

        self.assertNotIn(
            "update_installer",
            self.settings_source,
        )

        self.assertNotIn(
            "download_update",
            self.controller_source,
        )

        self.assertNotIn(
            "launch_downloaded_update",
            self.controller_source,
        )

    def test_controller_uses_daemon_thread(self):
        self.assertIn(
            "threading.Thread",
            self.controller_source,
        )

        self.assertIn(
            "daemon=True",
            self.controller_source,
        )

    def test_official_checker_is_used(self):
        self.assertIn(
            "check_for_updates",
            self.controller_source,
        )

        self.assertIn(
            "timeout_seconds",
            self.controller_source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
