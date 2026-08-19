from __future__ import annotations

from pathlib import Path
import unittest
from tests.repo_paths import REPO_ROOT


ROOT = REPO_ROOT

SETTINGS_PATH = (
    ROOT
    / "src"
    / "ui"
    / "settings.py"
)

CHECK_CONTROLLER_PATH = (
    ROOT
    / "src"
    / "ui"
    / "update_controller.py"
)

DOWNLOAD_CONTROLLER_PATH = (
    ROOT
    / "src"
    / "ui"
    / "update_download_controller.py"
)

INSTALL_CONTROLLER_PATH = (
    ROOT
    / "src"
    / "ui"
    / "update_install_controller.py"
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

        cls.check_controller_source = (
            CHECK_CONTROLLER_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

        cls.download_controller_source = (
            DOWNLOAD_CONTROLLER_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

        cls.install_controller_source = (
            INSTALL_CONTROLLER_PATH.read_text(
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

    def test_settings_uses_check_controller(self):
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

    def test_settings_uses_download_controller(self):
        self.assertIn(
            "UpdateDownloadController",
            self.settings_source,
        )

        self.assertIn(
            "describe_download_progress",
            self.settings_source,
        )

        self.assertIn(
            "describe_download_result",
            self.settings_source,
        )

        self.assertIn(
            ".start_download(",
            self.settings_source,
        )

    def test_update_card_is_navigable(self):
        self.assertIn(
            '"updates": updates',
            self.settings_source,
        )

    def test_download_button_and_progress_exist(self):
        self.assertIn(
            '"Download update"',
            self.settings_source,
        )

        self.assertIn(
            "QProgressBar",
            self.settings_source,
        )

        self.assertIn(
            '"updateProgress"',
            self.settings_source,
        )

    def test_download_and_install_are_connected_safely(self):
        self.assertIn(
            "download_update",
            self.download_controller_source,
        )

        self.assertNotIn(
            "update_installer",
            self.download_controller_source,
        )

        self.assertIn(
            "launch_downloaded_update",
            self.install_controller_source,
        )

        self.assertIn(
            "UpdateInstallController",
            self.settings_source,
        )

        self.assertIn(
            '"Install update"',
            self.settings_source,
        )

        self.assertIn(
            "install_verified_update",
            self.settings_source,
        )

        self.assertNotIn(
            "TrayController",
            self.settings_source,
        )

    def test_controllers_use_daemon_threads(self):
        self.assertIn(
            "threading.Thread",
            self.check_controller_source,
        )

        self.assertIn(
            "daemon=True",
            self.check_controller_source,
        )

        self.assertIn(
            "threading.Thread",
            self.download_controller_source,
        )

        self.assertIn(
            "daemon=True",
            self.download_controller_source,
        )

    def test_official_checker_and_downloader_are_used(self):
        self.assertIn(
            "check_for_updates",
            self.check_controller_source,
        )

        self.assertIn(
            "timeout_seconds",
            self.check_controller_source,
        )

        self.assertIn(
            "download_update",
            self.download_controller_source,
        )

        self.assertIn(
            "progress_callback",
            self.download_controller_source,
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

    def test_verified_download_state_is_retained(self):
        self.assertIn(
            "_verified_update_download",
            self.settings_source,
        )

        self.assertIn(
            "Downloaded & verified",
            self.settings_source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
