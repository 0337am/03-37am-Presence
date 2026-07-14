from __future__ import annotations

from dataclasses import replace
import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTextEdit,
    QWidget,
)

from src.ui.dashboard import DashboardPage
from src.ui.dashboard_layout import (
    available_presets,
    preset_layout,
)


class _ShortcutStub(QWidget):
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

    def __init__(self):
        super().__init__()

        self.dashboard_layout_state = replace(
            preset_layout(
                available_presets()[0]
            ),
            locked=False,
        )

        self._dashboard_layout_undo_stack = []
        self._dashboard_layout_redo_stack = []

        self.undo_count = 0
        self.redo_count = 0

        self.setup_dashboard_history_shortcuts()

    def undo_dashboard_layout(self):
        self.undo_count += 1
        return True

    def redo_dashboard_layout(self):
        self.redo_count += 1
        return True


class DashboardShortcutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_shortcuts_use_expected_sequences(
        self,
    ):
        widget = _ShortcutStub()

        self.assertEqual(
            widget.dashboard_undo_shortcut
            .key()
            .toString(),
            "Ctrl+Z",
        )
        self.assertEqual(
            widget.dashboard_redo_shortcut
            .key()
            .toString(),
            "Ctrl+Y",
        )
        self.assertEqual(
            widget.dashboard_alternate_redo_shortcut
            .key()
            .toString(),
            "Ctrl+Shift+Z",
        )

        for shortcut in (
            widget.dashboard_undo_shortcut,
            widget.dashboard_redo_shortcut,
            widget.dashboard_alternate_redo_shortcut,
        ):
            self.assertEqual(
                shortcut.context(),
                (
                    Qt.ShortcutContext
                    .WidgetWithChildrenShortcut
                ),
            )
            self.assertFalse(
                shortcut.autoRepeat()
            )

        widget.close()

    def test_shortcuts_follow_history_and_lock_state(
        self,
    ):
        widget = _ShortcutStub()

        self.assertFalse(
            widget.dashboard_undo_shortcut.isEnabled()
        )
        self.assertFalse(
            widget.dashboard_redo_shortcut.isEnabled()
        )
        self.assertFalse(
            widget
            .dashboard_alternate_redo_shortcut
            .isEnabled()
        )

        snapshot = (
            widget.dashboard_layout_state
        )

        widget._dashboard_layout_undo_stack.append(
            (
                "card move",
                snapshot,
            )
        )
        widget._dashboard_layout_redo_stack.append(
            (
                "card resize",
                snapshot,
            )
        )

        neutral_focus = QWidget()

        widget.update_dashboard_history_shortcut_state(
            neutral_focus
        )

        self.assertTrue(
            widget.dashboard_undo_shortcut.isEnabled()
        )
        self.assertTrue(
            widget.dashboard_redo_shortcut.isEnabled()
        )
        self.assertTrue(
            widget
            .dashboard_alternate_redo_shortcut
            .isEnabled()
        )

        widget.dashboard_layout_state = replace(
            widget.dashboard_layout_state,
            locked=True,
        )

        widget.update_dashboard_history_shortcut_state(
            neutral_focus
        )

        self.assertFalse(
            widget.dashboard_undo_shortcut.isEnabled()
        )
        self.assertFalse(
            widget.dashboard_redo_shortcut.isEnabled()
        )
        self.assertFalse(
            widget
            .dashboard_alternate_redo_shortcut
            .isEnabled()
        )

        neutral_focus.close()
        widget.close()

    def test_text_entry_widgets_block_shortcuts(
        self,
    ):
        widget = _ShortcutStub()

        editable_combo = QComboBox()
        editable_combo.setEditable(True)

        blocked_widgets = (
            QLineEdit(),
            QTextEdit(),
            QPlainTextEdit(),
            QSpinBox(),
            editable_combo,
        )

        for focused_widget in blocked_widgets:
            self.assertTrue(
                widget
                .dashboard_history_focus_blocks_shortcuts(
                    focused_widget
                )
            )

            focused_widget.close()

        selection_combo = QComboBox()
        selection_combo.setEditable(False)

        self.assertFalse(
            widget
            .dashboard_history_focus_blocks_shortcuts(
                selection_combo
            )
        )

        selection_combo.close()
        widget.close()

    def test_shortcut_router_calls_history_actions(
        self,
    ):
        widget = _ShortcutStub()
        neutral_focus = QWidget()

        self.assertTrue(
            widget.trigger_dashboard_history_shortcut(
                "undo",
                neutral_focus,
            )
        )
        self.assertTrue(
            widget.trigger_dashboard_history_shortcut(
                "redo",
                neutral_focus,
            )
        )

        self.assertEqual(
            widget.undo_count,
            1,
        )
        self.assertEqual(
            widget.redo_count,
            1,
        )

        self.assertFalse(
            widget.trigger_dashboard_history_shortcut(
                "unknown",
                neutral_focus,
            )
        )

        neutral_focus.close()
        widget.close()

    def test_shortcut_router_ignores_text_focus(
        self,
    ):
        widget = _ShortcutStub()
        line_edit = QLineEdit()

        self.assertFalse(
            widget.trigger_dashboard_history_shortcut(
                "undo",
                line_edit,
            )
        )
        self.assertFalse(
            widget.trigger_dashboard_history_shortcut(
                "redo",
                line_edit,
            )
        )

        self.assertEqual(
            widget.undo_count,
            0,
        )
        self.assertEqual(
            widget.redo_count,
            0,
        )

        line_edit.close()
        widget.close()


if __name__ == "__main__":
    unittest.main()
