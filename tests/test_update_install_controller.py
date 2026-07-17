from __future__ import annotations

from pathlib import Path
import unittest

from src.ui.update_install_controller import (
    UpdateInstallController,
)


ROOT = Path(__file__).resolve().parents[1]

CONTROLLER_PATH = (
    ROOT
    / "src"
    / "ui"
    / "update_install_controller.py"
)


class UpdateInstallControllerTests(
    unittest.TestCase
):
    def test_launch_forwards_safe_dependencies(self):
        calls = []
        download_result = object()
        returned_result = object()

        def opener(path):
            calls.append(
                ("open", path)
            )

        def quit_callback():
            calls.append(
                ("quit", None)
            )

        def launcher(
            supplied_download,
            *,
            user_approved,
            opener,
            quit_callback,
        ):
            calls.append(
                (
                    "launch",
                    supplied_download,
                    user_approved,
                    opener,
                    quit_callback,
                )
            )
            return returned_result

        controller = UpdateInstallController(
            launcher=launcher,
            opener=opener,
        )

        controller.set_quit_callback(
            quit_callback
        )

        result = controller.launch(
            download_result,
            user_approved=True,
        )

        self.assertIs(
            result,
            returned_result,
        )

        self.assertTrue(
            controller.quit_callback_available
        )

        launch_call = calls[0]

        self.assertEqual(
            launch_call[0],
            "launch",
        )

        self.assertIs(
            launch_call[1],
            download_result,
        )

        self.assertTrue(
            launch_call[2]
        )

        self.assertIs(
            launch_call[3],
            opener,
        )

        self.assertIs(
            launch_call[4],
            quit_callback,
        )

    def test_approval_is_forwarded_as_boolean(self):
        approvals = []

        def launcher(
            download_result,
            *,
            user_approved,
            opener,
            quit_callback,
        ):
            approvals.append(
                user_approved
            )
            return object()

        controller = UpdateInstallController(
            launcher=launcher
        )

        controller.launch(
            object(),
            user_approved=False,
        )

        self.assertEqual(
            approvals,
            [False],
        )

    def test_non_callable_quit_callback_is_rejected(self):
        controller = UpdateInstallController()

        controller.set_quit_callback(
            "not callable"
        )

        self.assertFalse(
            controller.quit_callback_available
        )

    def test_no_real_process_runner_exists(self):
        source = CONTROLLER_PATH.read_text(
            encoding="utf-8-sig"
        )

        self.assertNotIn(
            "subprocess",
            source,
        )

        self.assertNotIn(
            "os.system",
            source,
        )

        self.assertNotIn(
            "shell=True",
            source,
        )

    def test_official_installer_layer_is_used(self):
        source = CONTROLLER_PATH.read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "launch_downloaded_update",
            source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
