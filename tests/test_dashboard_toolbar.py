from __future__ import annotations

from dataclasses import replace
import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
)

from src.ui.dashboard import DashboardPage
from src.ui.dashboard_layout import (
    available_presets,
    preset_layout,
)


class _ToolbarStub(QWidget):
    setup_dashboard_history_shortcuts = (
        DashboardPage
        .setup_dashboard_history_shortcuts
    )

    dashboard_history_focus_blocks_shortcuts = (
        DashboardPage
        .dashboard_history_focus_blocks_shortcuts
    )

    update_dashboard_history_shortcut_state = (
        DashboardPage
        .update_dashboard_history_shortcut_state
    )

    handle_dashboard_history_focus_changed = (
        DashboardPage
        .handle_dashboard_history_focus_changed
    )

    trigger_dashboard_history_shortcut = (
        DashboardPage
        .trigger_dashboard_history_shortcut
    )

    trigger_dashboard_undo_shortcut = (
        DashboardPage
        .trigger_dashboard_undo_shortcut
    )

    trigger_dashboard_redo_shortcut = (
        DashboardPage
        .trigger_dashboard_redo_shortcut
    )
    update_dashboard_layout_toolbar_responsive_state = (
        DashboardPage
        .update_dashboard_layout_toolbar_responsive_state
    )

    def __init__(self):
        super().__init__()

        self.custom_cards = {}
        self.dashboard_layout_state = replace(
            preset_layout(
                available_presets()[0]
            ),
            locked=True,
        )
        self._dashboard_layout_undo_stack = []
        self._dashboard_layout_redo_stack = []

    def apply_dashboard_preset(self, *_):
        pass

    def populate_dashboard_profiles_menu(self):
        pass

    def set_dashboard_snap_enabled(self, *_):
        pass

    def update_dashboard_snap_button(self):
        checked = bool(
            self.layout_snap_button.isChecked()
        )

        self.layout_snap_button.setText(
            "Snap: On"
            if checked
            else "Snap: Off"
        )

    def add_link_card(self):
        pass

    def add_launcher_card(self):
        pass

    def reset_dashboard_layout(self):
        pass

    def toggle_dashboard_layout_lock(self):
        pass

    def sync_dashboard_drag_handles(self):
        pass

    def undo_dashboard_layout(self):
        pass

    def redo_dashboard_layout(self):
        pass

    def update_dashboard_history_controls(self):
        DashboardPage.update_dashboard_history_controls(
            self
        )

    def register_dashboard_visibility_action(
        self,
        card_id,
        title,
    ):
        action = QAction(
            title,
            self.layout_visibility_menu,
        )
        action.setCheckable(True)

        self.layout_visibility_menu.addAction(
            action
        )
        self.layout_visibility_actions[
            card_id
        ] = action

        return action


class DashboardToolbarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def build_toolbar(self):
        widget = _ToolbarStub()
        widget.resize(
            1200,
            700,
        )

        DashboardPage.build_dashboard_layout_toolbar(
            widget
        )

        return widget

    def test_toolbar_uses_two_control_zones(self):
        widget = self.build_toolbar()

        self.assertEqual(
            widget.layout_toolbar.objectName(),
            "dashboardLayoutToolbar",
        )
        self.assertEqual(
            widget.layout_toolbar_layout.count(),
            2,
        )
        self.assertEqual(
            widget.layout_primary_group.objectName(),
            "layoutToolbarGroup",
        )
        self.assertEqual(
            widget.layout_secondary_group.objectName(),
            "layoutToolbarGroup",
        )
        self.assertEqual(
            widget.layout_primary_group.property(
                "groupRole"
            ),
            "layout",
        )
        self.assertEqual(
            widget.layout_secondary_group.property(
                "groupRole"
            ),
            "editing",
        )
        self.assertEqual(
            widget.layout_primary_group_layout.indexOf(
                widget.layout_snap_button
            ),
            -1,
        )
        self.assertGreaterEqual(
            widget.layout_secondary_group_layout.indexOf(
                widget.layout_snap_button
            ),
            0,
        )
        self.assertEqual(
            widget.layout_profiles_button.text(),
            "Profiles",
        )
        self.assertEqual(
            widget.layout_add_card_button.text(),
            "Add card",
        )
        self.assertEqual(
            widget.layout_visibility_button.text(),
            "Cards",
        )
        self.assertEqual(
            widget.layout_toolbar_title.text(),
            "CONTROL ROOM",
        )

        widget.close()

    def test_toolbar_includes_history_controls(
        self,
    ):
        widget = self.build_toolbar()

        undo_index = (
            widget.layout_secondary_group_layout.indexOf(
                widget.layout_undo_button
            )
        )

        redo_index = (
            widget.layout_secondary_group_layout.indexOf(
                widget.layout_redo_button
            )
        )

        revert_index = (
            widget.layout_secondary_group_layout.indexOf(
                widget.layout_revert_session_button
            )
        )

        snap_index = (
            widget.layout_secondary_group_layout.indexOf(
                widget.layout_snap_button
            )
        )

        self.assertGreaterEqual(
            undo_index,
            0,
        )
        self.assertEqual(
            redo_index,
            undo_index + 1,
        )
        self.assertEqual(
            revert_index,
            redo_index + 1,
        )
        self.assertEqual(
            snap_index,
            revert_index + 1,
        )

        self.assertEqual(
            widget.layout_undo_button.text(),
            "Undo",
        )
        self.assertEqual(
            widget.layout_redo_button.text(),
            "Redo",
        )
        self.assertEqual(
            widget.layout_revert_session_button.text(),
            "Revert",
        )

        self.assertFalse(
            widget.layout_undo_button.isEnabled()
        )
        self.assertFalse(
            widget.layout_redo_button.isEnabled()
        )

        widget.dashboard_layout_state = replace(
            widget.dashboard_layout_state,
            locked=False,
        )

        widget._dashboard_layout_undo_stack.append(
            (
                "card move",
                widget.dashboard_layout_state,
            )
        )

        DashboardPage.update_dashboard_history_controls(
            widget
        )

        self.assertTrue(
            widget.layout_undo_button.isEnabled()
        )
        self.assertFalse(
            widget.layout_redo_button.isEnabled()
        )
        self.assertEqual(
            widget.layout_undo_button.toolTip(),
            "Undo card move (Ctrl+Z)",
        )

        widget.close()

    def test_toolbar_compacts_at_narrow_width(self):
        widget = self.build_toolbar()

        widget.resize(
            800,
            700,
        )
        DashboardPage.update_dashboard_layout_toolbar_responsive_state(
            widget
        )

        self.assertEqual(
            widget.layout_toolbar.property(
                "density"
            ),
            "compact",
        )
        self.assertEqual(
            widget.layout_toolbar_title.text(),
            "LAYOUT",
        )
        self.assertTrue(
            widget.layout_toolbar_hint.isHidden()
        )
        self.assertEqual(
            widget.layout_profiles_button.text(),
            "Profiles",
        )
        self.assertEqual(
            widget.layout_add_card_button.text(),
            "Add",
        )
        self.assertEqual(
            widget.layout_lock_button.text(),
            "Edit",
        )

        widget.resize(
            1200,
            700,
        )
        DashboardPage.update_dashboard_layout_toolbar_responsive_state(
            widget
        )

        self.assertEqual(
            widget.layout_toolbar.property(
                "density"
            ),
            "standard",
        )
        self.assertFalse(
            widget.layout_toolbar_hint.isHidden()
        )
        self.assertEqual(
            widget.layout_lock_button.text(),
            "Edit layout",
        )
        self.assertEqual(
            widget.layout_profiles_button.text(),
            "Profiles",
        )
        self.assertEqual(
            widget.layout_add_card_button.text(),
            "Add card",
        )
        self.assertEqual(
            widget.layout_visibility_button.text(),
            "Cards",
        )

        for button in (
            widget.layout_profiles_button,
            widget.layout_add_card_button,
            widget.layout_visibility_button,
        ):
            self.assertNotIn(
                "?",
                button.text(),
            )

        widget.close()

    def test_sync_distinguishes_locked_and_editing(self):
        widget = self.build_toolbar()

        DashboardPage.sync_dashboard_layout_controls(
            widget
        )

        self.assertEqual(
            widget.layout_status_label.text(),
            "LOCKED",
        )
        self.assertEqual(
            widget.layout_toolbar.property(
                "layoutState"
            ),
            "locked",
        )
        self.assertFalse(
            widget.layout_preset_combo.isEnabled()
        )
        self.assertEqual(
            widget.layout_lock_button.text(),
            "Edit layout",
        )

        widget.dashboard_layout_state = replace(
            widget.dashboard_layout_state,
            locked=False,
        )

        DashboardPage.sync_dashboard_layout_controls(
            widget
        )

        self.assertEqual(
            widget.layout_status_label.text(),
            "EDITING",
        )
        self.assertEqual(
            widget.layout_status_label.property(
                "layoutState"
            ),
            "editing",
        )
        self.assertTrue(
            widget.layout_preset_combo.isEnabled()
        )
        self.assertEqual(
            widget.layout_lock_button.text(),
            "Finish editing",
        )
        self.assertIn(
            "Drag, resize",
            widget.layout_toolbar_hint.text(),
        )

        widget.close()


if __name__ == "__main__":
    unittest.main()
