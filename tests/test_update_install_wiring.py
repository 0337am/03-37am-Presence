from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

MAIN_SOURCE = (
    ROOT / "main.py"
).read_text(
    encoding="utf-8-sig"
)

WINDOW_SOURCE = (
    ROOT
    / "src"
    / "ui"
    / "main_window.py"
).read_text(
    encoding="utf-8-sig"
)

SETTINGS_SOURCE = (
    ROOT
    / "src"
    / "ui"
    / "settings.py"
).read_text(
    encoding="utf-8-sig"
)

DOWNLOAD_CONTROLLER_SOURCE = (
    ROOT
    / "src"
    / "ui"
    / "update_download_controller.py"
).read_text(
    encoding="utf-8-sig"
)


class UpdateInstallWiringTests(
    unittest.TestCase
):
    def test_main_passes_tray_quit_callback(self):
        self.assertIn(
            "window.set_update_quit_callback",
            MAIN_SOURCE,
        )

        self.assertIn(
            "tray_controller.quit_application",
            MAIN_SOURCE,
        )

    def test_main_window_relays_callback_to_settings(self):
        self.assertIn(
            "def set_update_quit_callback",
            WINDOW_SOURCE,
        )

        self.assertIn(
            (
                "self.settings_page"
                ".set_update_quit_callback"
            ),
            WINDOW_SOURCE,
        )

    def test_settings_never_imports_tray(self):
        self.assertNotIn(
            "TrayController",
            SETTINGS_SOURCE,
        )

        self.assertNotIn(
            "src.ui.tray",
            SETTINGS_SOURCE,
        )

    def test_download_controller_still_cannot_launch(self):
        self.assertNotIn(
            "update_installer",
            DOWNLOAD_CONTROLLER_SOURCE,
        )

        self.assertNotIn(
            "launch_downloaded_update",
            DOWNLOAD_CONTROLLER_SOURCE,
        )

    def test_install_requires_confirmation(self):
        self.assertIn(
            "QMessageBox.question",
            SETTINGS_SOURCE,
        )

        self.assertIn(
            "StandardButton.Yes",
            SETTINGS_SOURCE,
        )

        self.assertIn(
            "user_approved=True",
            SETTINGS_SOURCE,
        )

    def test_install_button_only_uses_verified_result(self):
        self.assertIn(
            "self._verified_update_download",
            SETTINGS_SOURCE,
        )

        self.assertIn(
            '"Install update"',
            SETTINGS_SOURCE,
        )

        self.assertIn(
            "install_verified_update",
            SETTINGS_SOURCE,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
