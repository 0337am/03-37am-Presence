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
    create_launcher_card,
)
from src.ui.launcher_cards import (
    LauncherCardDialog,
    LauncherCardWidget,
)

from PyQt6.QtGui import (
    QColor,
    QImage,
)

from src.ui.launcher_card_images import (
    cached_launcher_card_image_path,
    import_launcher_card_image,
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

    def test_dialog_imports_selected_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            managed = root / "managed"
            source = root / "card.png"

            image = QImage(
                80,
                60,
                QImage.Format.Format_ARGB32,
            )
            image.fill(
                QColor("#a970ff")
            )

            self.assertTrue(
                image.save(str(source))
            )

            dialog = LauncherCardDialog(
                image_root=managed,
            )
            dialog.target_kind_combo.setCurrentIndex(
                dialog.target_kind_combo.findData(
                    LAUNCHER_TARGET_FOLDER
                )
            )
            dialog.target_edit.setText(
                str(root)
            )
            dialog.title_edit.setText(
                "Image card"
            )
            dialog.icon_edit.setText(
                "FB"
            )
            dialog._pending_image_path = (
                str(source)
            )
            dialog._refresh_image_preview()

            card = dialog.validated_card()

            self.assertTrue(
                card.image_asset
            )
            self.assertEqual(
                card.icon,
                "FB",
            )
            self.assertIsNotNone(
                cached_launcher_card_image_path(
                    card.image_asset,
                    managed,
                )
            )
            self.assertFalse(
                dialog.image_preview
                .pixmap()
                .isNull()
            )

            dialog.close()

    def test_dialog_can_remove_existing_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            managed = root / "managed"
            source = root / "card.png"

            image = QImage(
                48,
                48,
                QImage.Format.Format_ARGB32,
            )
            image.fill(
                QColor("#ffffff")
            )

            self.assertTrue(
                image.save(str(source))
            )

            asset = import_launcher_card_image(
                source,
                managed,
            )

            card = create_launcher_card(
                target=str(root),
                target_kind=(
                    LAUNCHER_TARGET_FOLDER
                ),
                title="Remove image",
                image_asset=asset,
            )

            dialog = LauncherCardDialog(
                card=card,
                image_root=managed,
            )

            dialog._remove_card_image()
            updated = dialog.validated_card()

            self.assertEqual(
                updated.image_asset,
                ""
            )
            self.assertFalse(
                dialog.remove_image_button
                .isEnabled()
            )

            dialog.close()

    def test_cancelled_selection_creates_no_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            managed = root / "managed"
            source = root / "card.png"

            image = QImage(
                32,
                32,
                QImage.Format.Format_ARGB32,
            )
            image.fill(
                QColor("#ff77bb")
            )

            self.assertTrue(
                image.save(str(source))
            )

            dialog = LauncherCardDialog(
                image_root=managed,
            )
            dialog._pending_image_path = (
                str(source)
            )
            dialog._refresh_image_preview()
            dialog.reject()

            self.assertFalse(
                managed.exists()
            )

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

    def test_widget_uses_image_then_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            managed = root / "managed"
            source = root / "card.png"

            image = QImage(
                72,
                72,
                QImage.Format.Format_ARGB32,
            )
            image.fill(
                QColor("#ff77bb")
            )

            self.assertTrue(
                image.save(str(source))
            )

            asset = import_launcher_card_image(
                source,
                managed,
            )

            card = create_launcher_card(
                target=str(root),
                target_kind=(
                    LAUNCHER_TARGET_FOLDER
                ),
                title="Rendered image",
                icon="FB",
                image_asset=asset,
            )

            widget = LauncherCardWidget(
                card,
                image_root=managed,
            )

            pixmap = (
                widget.icon_label.pixmap()
            )

            self.assertIsNotNone(pixmap)
            self.assertFalse(
                pixmap.isNull()
            )
            self.assertEqual(
                widget.icon_label.text(),
                "",
            )

            cached_path = (
                cached_launcher_card_image_path(
                    asset,
                    managed,
                )
            )

            self.assertIsNotNone(
                cached_path
            )

            cached_path.unlink()
            widget.update_card(card)

            fallback_pixmap = (
                widget.icon_label.pixmap()
            )

            self.assertIsNotNone(
                fallback_pixmap
            )
            self.assertTrue(
                fallback_pixmap.isNull()
            )
            self.assertEqual(
                widget.icon_label.text(),
                "FB",
            )

            widget.close()



if __name__ == "__main__":
    unittest.main()
