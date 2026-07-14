from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.ui.dashboard import DashboardPage
from tests import (
    test_dashboard_toolbar as dashboard_toolbar_tests,
)


CONTROL_NAMES = (
    "layout_lock_button",
    "layout_preset_combo",
    "layout_profiles_button",
    "layout_undo_button",
    "layout_redo_button",
    "layout_revert_session_button",
    "layout_snap_button",
    "layout_add_card_button",
    "layout_visibility_button",
    "layout_reset_button",
)


EXPECTED_ACCESSIBLE_NAMES = {
    "layout_preset_combo": (
        "Dashboard layout preset"
    ),
    "layout_profiles_button": (
        "Dashboard layout profiles"
    ),
    "layout_undo_button": (
        "Undo dashboard layout change"
    ),
    "layout_redo_button": (
        "Redo dashboard layout change"
    ),
    "layout_revert_session_button": (
        "Revert dashboard editing session"
    ),
    "layout_snap_button": (
        "Dashboard grid snapping"
    ),
    "layout_add_card_button": (
        "Add dashboard card"
    ),
    "layout_visibility_button": (
        "Dashboard card visibility"
    ),
    "layout_reset_button": (
        "Reset dashboard layout"
    ),
}


class DashboardAccessibilityTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def build_toolbar(self):
        case = (
            dashboard_toolbar_tests
            .DashboardToolbarTests(
                methodName=(
                    "test_toolbar_uses_two_control_zones"
                )
            )
        )

        return case.build_toolbar()

    def test_controls_have_accessible_metadata(
        self,
    ):
        widget = self.build_toolbar()

        self.assertEqual(
            widget.layout_toolbar.accessibleName(),
            "Dashboard layout controls",
        )
        self.assertTrue(
            widget.layout_toolbar
            .accessibleDescription()
        )
        self.assertEqual(
            widget.layout_status_label
            .accessibleName(),
            "Dashboard layout status",
        )

        self.assertEqual(
            widget.layout_lock_button
            .accessibleName(),
            "Edit dashboard layout",
        )

        for (
            attribute_name,
            expected_name,
        ) in EXPECTED_ACCESSIBLE_NAMES.items():
            control = getattr(
                widget,
                attribute_name,
            )

            self.assertEqual(
                control.accessibleName(),
                expected_name,
            )
            self.assertTrue(
                control.accessibleDescription()
            )
            self.assertEqual(
                control.statusTip(),
                control.accessibleDescription(),
            )
            self.assertEqual(
                control.focusPolicy(),
                Qt.FocusPolicy.StrongFocus,
            )

        self.assertEqual(
            widget.layout_profiles_menu
            .accessibleName(),
            "Dashboard layout profiles menu",
        )
        self.assertEqual(
            widget.layout_add_card_menu
            .accessibleName(),
            "Add dashboard card menu",
        )
        self.assertEqual(
            widget.layout_visibility_menu
            .accessibleName(),
            "Dashboard card visibility menu",
        )

        widget.close()

    def test_toolbar_uses_explicit_tab_order(
        self,
    ):
        widget = self.build_toolbar()

        expected_controls = [
            getattr(
                widget,
                attribute_name,
            )
            for attribute_name in CONTROL_NAMES
        ]

        expected_ids = {
            id(control)
            for control in expected_controls
        }

        discovered = []
        current = (
            widget.layout_lock_button
        )
        seen = set()

        for _index in range(80):
            identity = id(current)

            if identity in seen:
                break

            seen.add(identity)

            if identity in expected_ids:
                discovered.append(
                    current
                )

            current = (
                current.nextInFocusChain()
            )

        self.assertEqual(
            discovered,
            expected_controls,
        )

        widget.close()

    def test_dynamic_descriptions_follow_state(
        self,
    ):
        widget = self.build_toolbar()

        widget.dashboard_layout_state = replace(
            widget.dashboard_layout_state,
            locked=False,
        )

        widget._dashboard_layout_undo_stack = [
            (
                "card move",
                widget.dashboard_layout_state,
            )
        ]
        widget._dashboard_layout_redo_stack = []

        widget.update_dashboard_history_controls()

        self.assertEqual(
            widget.layout_undo_button
            .accessibleDescription(),
            widget.layout_undo_button.toolTip(),
        )
        self.assertIn(
            "card move",
            widget.layout_undo_button
            .accessibleDescription()
            .casefold(),
        )
        self.assertEqual(
            widget.layout_undo_button.cursor().shape(),
            Qt.CursorShape.PointingHandCursor,
        )
        self.assertEqual(
            widget.layout_redo_button.cursor().shape(),
            Qt.CursorShape.ArrowCursor,
        )

        widget.dashboard_snap_to_grid = True
        DashboardPage.update_dashboard_snap_button(
            widget
        )

        self.assertEqual(
            widget.layout_snap_button
            .accessibleDescription(),
            widget.layout_snap_button.toolTip(),
        )
        self.assertIn(
            "24px grid",
            widget.layout_snap_button
            .accessibleDescription(),
        )

        DashboardPage.sync_dashboard_layout_accessibility(
            widget
        )

        self.assertEqual(
            widget.layout_lock_button
            .accessibleName(),
            (
                "Finish dashboard layout "
                "editing"
            ),
        )
        self.assertIn(
            "being edited",
            widget.layout_toolbar
            .accessibleDescription()
            .casefold(),
        )

        widget.close()

    def test_compact_mode_keeps_full_names(
        self,
    ):
        widget = self.build_toolbar()

        original_names = {
            attribute_name: (
                getattr(
                    widget,
                    attribute_name,
                ).accessibleName()
            )
            for attribute_name in CONTROL_NAMES
        }

        widget.resize(
            760,
            500,
        )
        widget.update_dashboard_layout_toolbar_responsive_state()

        self.assertEqual(
            widget.layout_toolbar.property(
                "density"
            ),
            "compact",
        )

        compact_names = {
            attribute_name: (
                getattr(
                    widget,
                    attribute_name,
                ).accessibleName()
            )
            for attribute_name in CONTROL_NAMES
        }

        self.assertEqual(
            compact_names,
            original_names,
        )

        widget.resize(
            1200,
            500,
        )
        widget.update_dashboard_layout_toolbar_responsive_state()

        self.assertEqual(
            widget.layout_toolbar.property(
                "density"
            ),
            "standard",
        )

        standard_names = {
            attribute_name: (
                getattr(
                    widget,
                    attribute_name,
                ).accessibleName()
            )
            for attribute_name in CONTROL_NAMES
        }

        self.assertEqual(
            standard_names,
            original_names,
        )

        widget.close()

    def test_stylesheet_contains_focus_ring(
        self,
    ):
        dashboard_source = (
            Path(__file__)
            .parents[1]
            / "src"
            / "ui"
            / "dashboard.py"
        ).read_text(
            encoding="utf-8",
        )

        for selector in (
            (
                "QComboBox"
                "#layoutPresetCombo:focus"
            ),
            (
                "QPushButton"
                "#layoutControlButton:focus"
            ),
            (
                "QPushButton"
                "#layoutMenuButton:focus"
            ),
            (
                "QPushButton"
                "#layoutLockButton:focus"
            ),
        ):
            self.assertIn(
                selector,
                dashboard_source,
            )

        self.assertIn(
            (
                'border: 2px solid '
                '{theme["accent"]};'
            ),
            dashboard_source,
        )


if __name__ == "__main__":
    unittest.main()
