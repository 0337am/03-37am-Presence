from __future__ import annotations

import sys
import unittest

from PyQt6.QtWidgets import QApplication

from src.system.quick_access_catalogue import (
    quick_access_catalogue,
)
from src.system.quick_access_preferences import (
    DEFAULT_QUICK_ACCESS_ITEMS,
)
from src.ui.quick_access_picker import (
    QuickAccessPickerDialog,
)


class QuickAccessPickerTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication(
                sys.argv[:1]
            )
        )

    def test_default_items_leave_four_optional_destinations(
        self,
    ):
        dialog = QuickAccessPickerDialog(
            [
                item.item_id
                for item in DEFAULT_QUICK_ACCESS_ITEMS
            ]
        )

        self.assertEqual(
            [
                row[
                    "item_id"
                ]
                for row in dialog._rows
            ],
            [
                "builtin.presence",
                "builtin.library",
                "builtin.spotify",
                "builtin.about",
            ],
        )

    def test_choose_returns_selected_catalogue_item(
        self,
    ):
        dialog = QuickAccessPickerDialog(
            [
                item.item_id
                for item in DEFAULT_QUICK_ACCESS_ITEMS
            ]
        )

        dialog._choose(
            "builtin.library"
        )

        self.assertEqual(
            dialog.selected_item_id(),
            "builtin.library",
        )

    def test_all_catalogue_items_show_empty_state(
        self,
    ):
        dialog = QuickAccessPickerDialog(
            [
                entry.item_id
                for entry in quick_access_catalogue()
            ]
        )

        self.assertEqual(
            dialog._rows,
            [],
        )

        self.assertFalse(
            dialog.empty_label.isHidden()
        )


if __name__ == "__main__":
    unittest.main()
