from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtWidgets import QApplication

from src.ui.custom_cards import (
    LAUNCHER_TARGET_APPLICATION,
    LAUNCHER_TARGET_FILE,
    LAUNCHER_TARGET_FOLDER,
    LauncherCardData,
)
from src.ui.launcher_cards import (
    LauncherCardDialog,
    LauncherCardWidget,
)


_APP = QApplication.instance()

if _APP is None:
    _APP = QApplication([])


class LauncherCardDialogTests(unittest.TestCase):
    def test_dialog_builds_application_card(self):
        with tempfile.TemporaryDirectory() as directory:
            target = (
                Path(directory)
                / "Example.exe"
            )
            target.write_bytes(b"example")

            dialog = LauncherCardDialog()

            index = (
                dialog
                .target_kind_combo
                .findData(
                    LAUNCHER_TARGET_APPLICATION
                )
            )
            dialog.target_kind_combo.setCurrentIndex(
                index
            )
            dialog.target_edit.setText(
                str(target)
            )
            dialog.title_edit.setText(
                "Example App"
            )
            dialog.icon_edit.setText(
                "??"
            )

            card = dialog.validated_card()

            self.assertIsInstance(
                card,
                LauncherCardData,
            )
            self.assertEqual(
                card.target,
                str(target),
            )
            self.assertEqual(
                card.target_kind,
                LAUNCHER_TARGET_APPLICATION,
            )
            self.assertEqual(
                card.title,
                "Example App",
            )

            dialog.close()

    def test_dialog_accepts_windows_copy_as_path(self):
        with tempfile.TemporaryDirectory() as directory:
            target = (
                Path(directory)
                / "Copied App.exe"
            )
            target.write_bytes(b"example")

            dialog = LauncherCardDialog()

            index = (
                dialog
                .target_kind_combo
                .findData(
                    LAUNCHER_TARGET_APPLICATION
                )
            )
            dialog.target_kind_combo.setCurrentIndex(
                index
            )

            dialog.target_edit.setText(
                f'"{target}"'
            )

            self.assertIn(
                "Ready:",
                dialog.target_status.text(),
            )

            card = dialog.validated_card()

            self.assertEqual(
                card.target,
                str(target),
            )

            dialog.close()

    def test_dialog_builds_folder_card(self):
        with tempfile.TemporaryDirectory() as directory:
            dialog = LauncherCardDialog()

            index = (
                dialog
                .target_kind_combo
                .findData(
                    LAUNCHER_TARGET_FOLDER
                )
            )
            dialog.target_kind_combo.setCurrentIndex(
                index
            )
            dialog.target_edit.setText(
                directory
            )

            card = dialog.validated_card()

            self.assertEqual(
                card.target_kind,
                LAUNCHER_TARGET_FOLDER,
            )
            self.assertEqual(
                card.target,
                directory,
            )

            dialog.close()

    def test_dialog_rejects_missing_target(self):
        dialog = LauncherCardDialog()

        index = (
            dialog
            .target_kind_combo
            .findData(
                LAUNCHER_TARGET_FILE
            )
        )
        dialog.target_kind_combo.setCurrentIndex(
            index
        )
        dialog.target_edit.setText(
            str(
                Path.home()
                / "definitely-missing-0337.file"
            )
        )

        with self.assertRaises(ValueError):
            dialog.validated_card()

        dialog.close()

    def test_dialog_rejects_file_as_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            target = (
                Path(directory)
                / "notes.txt"
            )
            target.write_text(
                "notes",
                encoding="utf-8",
            )

            dialog = LauncherCardDialog()

            index = (
                dialog
                .target_kind_combo
                .findData(
                    LAUNCHER_TARGET_FOLDER
                )
            )
            dialog.target_kind_combo.setCurrentIndex(
                index
            )
            dialog.target_edit.setText(
                str(target)
            )

            with self.assertRaises(ValueError):
                dialog.validated_card()

            dialog.close()


class LauncherCardWidgetTests(unittest.TestCase):
    def test_widget_is_safe_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            card = LauncherCardData.from_dict(
                {
                    "id": (
                        "custom_launcher_"
                        "0123456789abcdef"
                        "0123456789abcdef"
                    ),
                    "type": "launcher",
                    "title": "Documents",
                    "target": str(target),
                    "target_kind": (
                        LAUNCHER_TARGET_FOLDER
                    ),
                    "icon": "??",
                    "description": "Local files",
                    "button_label": "Open",
                    "accent": "",
                }
            )

            widget = LauncherCardWidget(card)

            self.assertFalse(
                widget.launch_enabled
            )
            self.assertFalse(
                widget.open_button.isEnabled()
            )
            self.assertIn(
                "Folder:",
                widget.target_label.text(),
            )

            widget.close()

    def test_widget_reports_missing_target(self):
        card = LauncherCardData.from_dict(
            {
                "id": (
                    "custom_launcher_"
                    "fedcba9876543210"
                    "fedcba9876543210"
                ),
                "type": "launcher",
                "title": "Disconnected",
                "target": "",
                "target_kind": (
                    LAUNCHER_TARGET_FILE
                ),
                "icon": "",
                "description": "",
                "button_label": "Open",
                "accent": "",
            }
        )

        widget = LauncherCardWidget(card)

        self.assertIn(
            "target not selected",
            widget.target_label.text(),
        )
        self.assertFalse(
            widget.open_button.isEnabled()
        )

        widget.close()

    def test_widget_can_be_enabled_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            target = (
                Path(directory)
                / "notes.txt"
            )
            target.write_text(
                "notes",
                encoding="utf-8",
            )

            card = LauncherCardData.from_dict(
                {
                    "id": (
                        "custom_launcher_"
                        "aaaaaaaaaaaaaaaa"
                        "aaaaaaaaaaaaaaaa"
                    ),
                    "type": "launcher",
                    "title": "Notes",
                    "target": str(target),
                    "target_kind": (
                        LAUNCHER_TARGET_FILE
                    ),
                    "icon": "??",
                    "description": "",
                    "button_label": "Open",
                    "accent": "",
                }
            )

            widget = LauncherCardWidget(card)
            emitted = []

            widget.launch_requested.connect(
                emitted.append
            )

            widget.set_launch_enabled(True)

            self.assertTrue(
                widget.open_button.isEnabled()
            )

            widget.open_button.click()
            QApplication.processEvents()

            self.assertEqual(
                emitted,
                [str(target)],
            )

            widget.close()

    def test_widget_responsive_states(self):
        with tempfile.TemporaryDirectory() as directory:
            card = LauncherCardData.from_dict(
                {
                    "id": (
                        "custom_launcher_"
                        "bbbbbbbbbbbbbbbb"
                        "bbbbbbbbbbbbbbbb"
                    ),
                    "type": "launcher",
                    "title": "Folder",
                    "target": directory,
                    "target_kind": (
                        LAUNCHER_TARGET_FOLDER
                    ),
                    "icon": "",
                    "description": "Description",
                    "button_label": "Open",
                    "accent": "",
                }
            )

            widget = LauncherCardWidget(card)

            widget.resize(300, 180)
            QApplication.processEvents()
            widget._apply_responsive_state()

            self.assertEqual(
                widget.responsive_state,
                "large",
            )

            widget.resize(120, 75)
            QApplication.processEvents()
            widget._apply_responsive_state()

            self.assertEqual(
                widget.responsive_state,
                "compact",
            )
            self.assertFalse(
                widget.description_label.isVisible()
            )

            widget.close()


if __name__ == "__main__":
    unittest.main()
