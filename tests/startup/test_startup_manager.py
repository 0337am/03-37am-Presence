import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import src.system.startup as startup_module
from src.system.startup import StartupManager


class StartupManagerTests(unittest.TestCase):
    def test_source_command_uses_pythonw_and_main(
        self,
    ):
        with patch.object(
            startup_module.sys,
            "frozen",
            False,
            create=True,
        ), patch.object(
            startup_module.sys,
            "executable",
            r"C:\Python314\python.exe",
        ), patch.object(
            Path,
            "exists",
            return_value=True,
        ):
            command = StartupManager.build_command(
                True
            )

        expected = subprocess.list2cmdline(
            [
                r"C:\Python314\pythonw.exe",
                str(
                    startup_module.PROJECT_ROOT
                    / "main.py"
                ),
                "--minimized",
            ]
        )

        self.assertEqual(
            command,
            expected,
        )

    def test_frozen_command_uses_packaged_executable(
        self,
    ):
        executable = (
            r"C:\Program Files\03-37am Presence"
            r"\03-37am Presence.exe"
        )

        with patch.object(
            startup_module.sys,
            "frozen",
            True,
            create=True,
        ), patch.object(
            startup_module.sys,
            "executable",
            executable,
        ):
            command = StartupManager.build_command(
                False
            )

        self.assertEqual(
            command,
            subprocess.list2cmdline(
                [executable]
            ),
        )

    def test_source_mode_never_repairs_entry(
        self,
    ):
        registered = Mock()
        set_enabled = Mock()

        with patch.object(
            startup_module.sys,
            "frozen",
            False,
            create=True,
        ), patch.object(
            StartupManager,
            "registered_command",
            registered,
        ), patch.object(
            StartupManager,
            "set_enabled",
            set_enabled,
        ):
            repaired = (
                StartupManager.repair_packaged_entry()
            )

        self.assertFalse(
            repaired
        )

        registered.assert_not_called()
        set_enabled.assert_not_called()

    def test_missing_entry_is_not_created(
        self,
    ):
        set_enabled = Mock()

        with patch.object(
            startup_module.sys,
            "frozen",
            True,
            create=True,
        ), patch.object(
            StartupManager,
            "registered_command",
            return_value=None,
        ), patch.object(
            StartupManager,
            "set_enabled",
            set_enabled,
        ):
            repaired = (
                StartupManager.repair_packaged_entry()
            )

        self.assertFalse(
            repaired
        )

        set_enabled.assert_not_called()

    def test_matching_packaged_entry_is_unchanged(
        self,
    ):
        command = (
            '"C:\\Program Files\\03-37am Presence\\'
            '03-37am Presence.exe" --minimized'
        )

        set_enabled = Mock()

        with patch.object(
            startup_module.sys,
            "frozen",
            True,
            create=True,
        ), patch.object(
            StartupManager,
            "registered_command",
            return_value=command,
        ), patch.object(
            StartupManager,
            "build_command",
            return_value=command,
        ), patch.object(
            StartupManager,
            "set_enabled",
            set_enabled,
        ):
            repaired = (
                StartupManager.repair_packaged_entry()
            )

        self.assertFalse(
            repaired
        )

        set_enabled.assert_not_called()

    def test_stale_entry_is_repaired_and_preserves_mode(
        self,
    ):
        cases = (
            (
                (
                    r"C:\Python314\pythonw.exe "
                    r"C:\Project\main.py --minimized"
                ),
                True,
            ),
            (
                (
                    r"C:\Python314\pythonw.exe "
                    r"C:\Project\main.py"
                ),
                False,
            ),
        )

        for current_command, minimized in cases:
            with self.subTest(
                minimized=minimized
            ):
                set_enabled = Mock(
                    return_value=True
                )

                with patch.object(
                    startup_module.sys,
                    "frozen",
                    True,
                    create=True,
                ), patch.object(
                    StartupManager,
                    "registered_command",
                    return_value=current_command,
                ), patch.object(
                    StartupManager,
                    "build_command",
                    return_value="expected packaged command",
                ), patch.object(
                    StartupManager,
                    "set_enabled",
                    set_enabled,
                ):
                    repaired = (
                        StartupManager
                        .repair_packaged_entry()
                    )

                self.assertTrue(
                    repaired
                )

                set_enabled.assert_called_once_with(
                    True,
                    minimized,
                )

    def test_main_repairs_before_qt_application(
        self,
    ):
        source = Path(
            "main.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            (
                "from src.system.startup "
                "import StartupManager"
            ),
            source,
        )

        repair_position = source.index(
            "StartupManager.repair_packaged_entry()"
        )

        qt_position = source.index(
            "app = QApplication("
        )

        self.assertLess(
            repair_position,
            qt_position,
        )


if __name__ == "__main__":
    unittest.main()
