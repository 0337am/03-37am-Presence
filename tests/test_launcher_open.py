from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.system.launcher_open import (
    PreparedLauncherTarget,
    is_script_target,
    open_prepared_launcher_target,
    prepare_launcher_target,
)
from src.ui.custom_cards import (
    LAUNCHER_TARGET_APPLICATION,
    LAUNCHER_TARGET_FILE,
    LAUNCHER_TARGET_FOLDER,
    create_launcher_card,
)


class LauncherOpeningTests(
    unittest.TestCase
):
    def test_prepares_existing_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            card = create_launcher_card(
                target=directory,
                target_kind=(
                    LAUNCHER_TARGET_FOLDER
                ),
                title="Projects",
            )

            prepared = (
                prepare_launcher_target(
                    card
                )
            )

            self.assertEqual(
                prepared.path,
                Path(directory),
            )
            self.assertEqual(
                prepared.target_kind,
                LAUNCHER_TARGET_FOLDER,
            )
            self.assertFalse(
                prepared
                .requires_script_confirmation
            )

    def test_prepares_existing_application(self):
        with tempfile.TemporaryDirectory() as directory:
            target = (
                Path(directory)
                / "example.exe"
            )
            target.write_bytes(b"MZ")

            card = create_launcher_card(
                target=str(target),
                target_kind=(
                    LAUNCHER_TARGET_APPLICATION
                ),
                title="Example",
            )

            prepared = (
                prepare_launcher_target(
                    card
                )
            )

            self.assertEqual(
                prepared.path,
                target,
            )
            self.assertFalse(
                prepared
                .requires_script_confirmation
            )

    def test_script_detection_is_case_insensitive(self):
        self.assertTrue(
            is_script_target(
                r"C:\Tools\Example.PS1"
            )
        )
        self.assertTrue(
            is_script_target(
                r"C:\Tools\Example.CmD"
            )
        )
        self.assertFalse(
            is_script_target(
                r"C:\Tools\Example.exe"
            )
        )

    def test_script_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = (
                Path(directory)
                / "example.cmd"
            )
            target.write_text(
                "@echo off\n",
                encoding="utf-8",
            )

            card = create_launcher_card(
                target=str(target),
                target_kind=(
                    LAUNCHER_TARGET_APPLICATION
                ),
                title="Example script",
            )

            prepared = (
                prepare_launcher_target(
                    card
                )
            )

            self.assertTrue(
                prepared
                .requires_script_confirmation
            )

    def test_missing_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = (
                Path(directory)
                / "missing.txt"
            )

            card = create_launcher_card(
                target=str(target),
                target_kind=(
                    LAUNCHER_TARGET_FILE
                ),
                title="Missing",
            )

            with self.assertRaises(
                FileNotFoundError
            ):
                prepare_launcher_target(
                    card
                )

    def test_file_cannot_be_opened_as_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            target = (
                Path(directory)
                / "example.txt"
            )
            target.write_text(
                "hello",
                encoding="utf-8",
            )

            card = create_launcher_card(
                target=str(target),
                target_kind=(
                    LAUNCHER_TARGET_FOLDER
                ),
                title="Wrong kind",
            )

            with self.assertRaises(
                ValueError
            ):
                prepare_launcher_target(
                    card
                )

    def test_folder_cannot_be_opened_as_file(self):
        with tempfile.TemporaryDirectory() as directory:
            card = create_launcher_card(
                target=directory,
                target_kind=(
                    LAUNCHER_TARGET_FILE
                ),
                title="Wrong kind",
            )

            with self.assertRaises(
                ValueError
            ):
                prepare_launcher_target(
                    card
                )

    def test_open_uses_only_validated_path(self):
        with tempfile.TemporaryDirectory() as directory:
            target = (
                Path(directory)
                / "example.txt"
            )
            target.write_text(
                "hello",
                encoding="utf-8",
            )

            card = create_launcher_card(
                target=str(target),
                target_kind=(
                    LAUNCHER_TARGET_FILE
                ),
                title="Example",
            )

            prepared = (
                prepare_launcher_target(
                    card
                )
            )

            opened = []

            open_prepared_launcher_target(
                prepared,
                opener=opened.append,
            )

            self.assertEqual(
                opened,
                [str(target)],
            )

    def test_target_is_checked_again_before_open(self):
        with tempfile.TemporaryDirectory() as directory:
            target = (
                Path(directory)
                / "vanishing.txt"
            )
            target.write_text(
                "hello",
                encoding="utf-8",
            )

            prepared = PreparedLauncherTarget(
                path=target,
                target_kind=(
                    LAUNCHER_TARGET_FILE
                ),
                requires_script_confirmation=False,
            )

            target.unlink()
            opened = []

            with self.assertRaises(
                FileNotFoundError
            ):
                open_prepared_launcher_target(
                    prepared,
                    opener=opened.append,
                )

            self.assertEqual(
                opened,
                []
            )

    def test_invalid_prepared_object_is_rejected(self):
        with self.assertRaises(TypeError):
            open_prepared_launcher_target(
                object(),
                opener=lambda target: None,
            )


if __name__ == "__main__":
    unittest.main()
