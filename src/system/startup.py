import re
import subprocess
import sys
from pathlib import Path

import winreg


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "03:37am Presence"

MINIMIZED_ARGUMENT_PATTERN = re.compile(
    r"(?:^|\s)--minimized(?=\s|$)",
    re.IGNORECASE,
)


class StartupManager:
    @staticmethod
    def registered_command() -> str | None:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                winreg.KEY_READ,
            ) as key:
                value, _ = winreg.QueryValueEx(
                    key,
                    VALUE_NAME,
                )

            command = str(
                value
                or ""
            ).strip()

            return command or None

        except FileNotFoundError:
            return None

        except OSError as error:
            print("Could not check Windows startup:")
            print(error)
            return None

    @staticmethod
    def is_enabled() -> bool:
        return (
            StartupManager.registered_command()
            is not None
        )

    @staticmethod
    def set_enabled(
        enabled: bool,
        start_minimized: bool = True,
    ) -> bool:
        try:
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                if enabled:
                    command = StartupManager.build_command(
                        start_minimized
                    )

                    winreg.SetValueEx(
                        key,
                        VALUE_NAME,
                        0,
                        winreg.REG_SZ,
                        command,
                    )

                else:
                    try:
                        winreg.DeleteValue(
                            key,
                            VALUE_NAME,
                        )

                    except FileNotFoundError:
                        pass

            return True

        except OSError as error:
            print("Could not update Windows startup:")
            print(error)
            return False

    @staticmethod
    def build_command(
        start_minimized: bool,
    ) -> str:
        if getattr(
            sys,
            "frozen",
            False,
        ):
            arguments = [
                sys.executable
            ]

        else:
            python_executable = Path(
                sys.executable
            )

            pythonw_executable = (
                python_executable.with_name(
                    "pythonw.exe"
                )
            )

            if not pythonw_executable.exists():
                pythonw_executable = (
                    python_executable
                )

            arguments = [
                str(pythonw_executable),
                str(PROJECT_ROOT / "main.py"),
            ]

        if start_minimized:
            arguments.append(
                "--minimized"
            )

        return subprocess.list2cmdline(
            arguments
        )

    @staticmethod
    def command_starts_minimized(
        command: str,
    ) -> bool:
        return bool(
            MINIMIZED_ARGUMENT_PATTERN.search(
                str(
                    command
                    or ""
                )
            )
        )

    @staticmethod
    def repair_packaged_entry() -> bool:
        if not getattr(
            sys,
            "frozen",
            False,
        ):
            return False

        current_command = (
            StartupManager.registered_command()
        )

        if current_command is None:
            return False

        start_minimized = (
            StartupManager.command_starts_minimized(
                current_command
            )
        )

        expected_command = (
            StartupManager.build_command(
                start_minimized
            )
        )

        if (
            current_command.strip()
            == expected_command
        ):
            return False

        return StartupManager.set_enabled(
            True,
            start_minimized,
        )
