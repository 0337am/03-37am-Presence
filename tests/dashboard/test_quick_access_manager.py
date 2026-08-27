from __future__ import annotations

import inspect
import sys
import unittest

from unittest.mock import Mock, patch

from PyQt6.QtWidgets import QApplication

from src.system.quick_access_preferences import (
    DEFAULT_QUICK_ACCESS_ITEMS,
    QuickAccessPreferences,
)
from src.ui.dashboard import DashboardPage
from src.ui.quick_access_manager import (
    QuickAccessManagerDialog,
)


class _Store:
    def __init__(
        self,
        preferences,
    ):
        self.loaded = preferences
        self.saved = []

    def load(
        self,
    ):
        return self.loaded

    def save(
        self,
        preferences,
    ):
        self.saved.append(
            preferences
        )

        return preferences


class _DashboardStub:
    def __init__(
        self,
        preferences,
    ):
        self.quick_access_preferences_store = (
            _Store(
                preferences
            )
        )

        self.theme_manager = Mock()
        self.theme_manager.theme.return_value = {
            "background": "#180b10",
            "card": "#3b1d2a",
            "card_alt": "#251018",
            "accent": "#ff7fa8",
            "text": "#fff5f8",
            "muted": "#d8aab9",
            "border": "#6b354a",
        }

        self.refresh_calls = []

    def refresh_quick_access_buttons(
        self,
        force=False,
    ):
        self.refresh_calls.append(
            force
        )


class QuickAccessManagerTests(
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

    def test_dialog_reflects_default_order_and_visibility(
        self,
    ):
        preferences = QuickAccessPreferences(
            items=DEFAULT_QUICK_ACCESS_ITEMS
        )

        dialog = QuickAccessManagerDialog(
            preferences
        )

        self.assertEqual(
            [
                row[
                    "item_id"
                ]
                for row in dialog._rows
            ],
            [
                item.item_id
                for item in DEFAULT_QUICK_ACCESS_ITEMS
            ],
        )

        self.assertTrue(
            all(
                row[
                    "visible"
                ].isChecked()
                for row in dialog._rows
            )
        )

    def test_visibility_changes_are_returned(
        self,
    ):
        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=DEFAULT_QUICK_ACCESS_ITEMS
            )
        )

        dialog._rows[
            1
        ][
            "visible"
        ].setChecked(
            False
        )

        preferences = (
            dialog.preferences()
        )

        self.assertFalse(
            preferences.items[
                1
            ].visible
        )

    def test_move_down_changes_order(
        self,
    ):
        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=DEFAULT_QUICK_ACCESS_ITEMS
            )
        )

        first_id = (
            DEFAULT_QUICK_ACCESS_ITEMS[
                0
            ].item_id
        )

        dialog._move_item(
            0,
            1,
        )

        preferences = (
            dialog.preferences()
        )

        self.assertEqual(
            preferences.items[
                1
            ].item_id,
            first_id,
        )

    def test_move_up_changes_order(
        self,
    ):
        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=DEFAULT_QUICK_ACCESS_ITEMS
            )
        )

        second_id = (
            DEFAULT_QUICK_ACCESS_ITEMS[
                1
            ].item_id
        )

        dialog._move_item(
            1,
            -1,
        )

        preferences = (
            dialog.preferences()
        )

        self.assertEqual(
            preferences.items[
                0
            ].item_id,
            second_id,
        )

    def test_reset_restores_default_items(
        self,
    ):
        custom = QuickAccessPreferences(
            items=(
                DEFAULT_QUICK_ACCESS_ITEMS[
                    3
                ],
                DEFAULT_QUICK_ACCESS_ITEMS[
                    0
                ],
            )
        )

        dialog = QuickAccessManagerDialog(
            custom
        )

        dialog._reset_defaults()

        self.assertEqual(
            dialog.preferences(),
            QuickAccessPreferences(
                items=DEFAULT_QUICK_ACCESS_ITEMS
            ),
        )

    def test_dashboard_save_persists_and_refreshes(
        self,
    ):
        initial = QuickAccessPreferences(
            items=DEFAULT_QUICK_ACCESS_ITEMS
        )

        updated = QuickAccessPreferences(
            items=tuple(
                reversed(
                    DEFAULT_QUICK_ACCESS_ITEMS
                )
            )
        )

        dashboard = _DashboardStub(
            initial
        )

        dialog = Mock()
        dialog.exec.return_value = 1
        dialog.preferences.return_value = (
            updated
        )

        with patch(
            "src.ui.dashboard."
            "QuickAccessManagerDialog",
            return_value=dialog,
        ) as constructor:
            DashboardPage.open_quick_access_manager(
                dashboard
            )

        constructor.assert_called_once_with(
            initial,
            theme=dashboard.theme_manager.theme(),
            parent=dashboard,
        )

        self.assertEqual(
            dashboard.quick_access_preferences_store.saved,
            [
                updated,
            ],
        )

        self.assertEqual(
            dashboard.refresh_calls,
            [
                True,
            ],
        )

    def test_dashboard_cancel_does_not_save(
        self,
    ):
        initial = QuickAccessPreferences(
            items=DEFAULT_QUICK_ACCESS_ITEMS
        )

        dashboard = _DashboardStub(
            initial
        )

        dialog = Mock()
        dialog.exec.return_value = 0

        with patch(
            "src.ui.dashboard."
            "QuickAccessManagerDialog",
            return_value=dialog,
        ):
            DashboardPage.open_quick_access_manager(
                dashboard
            )

        self.assertEqual(
            dashboard.quick_access_preferences_store.saved,
            [],
        )

        self.assertEqual(
            dashboard.refresh_calls,
            [],
        )

    def test_quick_access_card_exposes_manage_action(
        self,
    ):
        source = inspect.getsource(
            DashboardPage.build_quick_access_card
        )

        self.assertIn(
            '"Manage"',
            source,
        )

        self.assertIn(
            "open_quick_access_manager",
            source,
        )

        self.assertIn(
            '"textButton"',
            source,
        )


    def test_dashboard_manager_is_bound_instance_method(
        self,
    ):
        descriptor = inspect.getattr_static(
            DashboardPage,
            "open_quick_access_manager",
        )

        self.assertFalse(
            isinstance(
                descriptor,
                staticmethod,
            )
        )

        self.assertTrue(
            inspect.isfunction(
                descriptor
            )
        )

        dashboard = _DashboardStub(
            QuickAccessPreferences(
                items=DEFAULT_QUICK_ACCESS_ITEMS
            )
        )

        bound = descriptor.__get__(
            dashboard,
            DashboardPage,
        )

        self.assertEqual(
            str(
                inspect.signature(
                    bound
                )
            ),
            "()",
        )

    def test_dialog_applies_theme_and_semantic_button_roles(
        self,
    ):
        theme = {
            "background": "#180b10",
            "card": "#3b1d2a",
            "card_alt": "#251018",
            "accent": "#ff7fa8",
            "text": "#fff5f8",
            "muted": "#d8aab9",
            "border": "#6b354a",
        }

        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=DEFAULT_QUICK_ACCESS_ITEMS
            ),
            theme=theme,
        )

        style = dialog.styleSheet()

        self.assertIn(
            "#ff7fa8",
            style,
        )

        self.assertIn(
            "#d8aab9",
            style,
        )

        self.assertIn(
            "#3b1d2a",
            style,
        )

        self.assertEqual(
            dialog.save_button.objectName(),
            "primaryButton",
        )

        self.assertEqual(
            dialog.cancel_button.objectName(),
            "secondaryButton",
        )

        self.assertEqual(
            dialog.reset_button.objectName(),
            "secondaryButton",
        )

        self.assertEqual(
            dialog._rows[
                0
            ][
                "up"
            ].objectName(),
            "secondaryButton",
        )

        self.assertEqual(
            dialog._rows[
                0
            ][
                "visible"
            ]._theme[
                "accent"
            ],
            "#ff7fa8",
        )


if __name__ == "__main__":
    unittest.main()
