from __future__ import annotations

from dataclasses import replace
import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QWidget,
)

from src.ui.dashboard import (
    DashboardPage,
    dashboard_card_spec,
)
from src.ui.dashboard_layout import (
    available_presets,
    preset_layout,
    validate_layout,
)


class _LayoutStore:
    def __init__(self):
        self.saved = []

    def save(self, layout):
        result = validate_layout(
            layout
        )

        self.saved.append(
            result
        )

        return result


class _KeyboardStub(QWidget):
    create_dashboard_card_handles = (
        DashboardPage
        .create_dashboard_card_handles
    )
    sync_dashboard_card_handle_accessibility = (
        DashboardPage
        .sync_dashboard_card_handle_accessibility
    )
    reset_dashboard_keyboard_adjustment_state = (
        DashboardPage
        .reset_dashboard_keyboard_adjustment_state
    )
    begin_dashboard_keyboard_adjustment = (
        DashboardPage
        .begin_dashboard_keyboard_adjustment
    )
    update_dashboard_keyboard_adjustment = (
        DashboardPage
        .update_dashboard_keyboard_adjustment
    )
    finish_dashboard_keyboard_adjustment = (
        DashboardPage
        .finish_dashboard_keyboard_adjustment
    )
    cancel_dashboard_keyboard_adjustment = (
        DashboardPage
        .cancel_dashboard_keyboard_adjustment
    )
    handle_dashboard_keyboard_edit_event = (
        DashboardPage
        .handle_dashboard_keyboard_edit_event
    )
    dashboard_minimum_card_size = (
        DashboardPage
        .dashboard_minimum_card_size
    )
    apply_dashboard_layout = (
        DashboardPage
        .apply_dashboard_layout
    )

    def __init__(self):
        super().__init__()

        layout = replace(
            preset_layout(
                available_presets()[0]
            ),
            locked=False,
        )

        card_layout = next(
            item
            for item in layout.cards
            if (
                item.visible
                and dashboard_card_spec(
                    item.card_id
                ).resizable
            )
        )

        self.card_id = card_layout.card_id
        self.dashboard_layout_state = layout
        self.dashboard_layout_store = (
            _LayoutStore()
        )

        self.dashboard_canvas = QFrame(self)
        self.dashboard_canvas.setGeometry(
            0,
            0,
            1000,
            800,
        )

        self.card = QFrame(
            self.dashboard_canvas
        )
        self.card.setGeometry(
            100,
            80,
            300,
            200,
        )

        self.dashboard_cards = {
            self.card_id: self.card,
        }
        self.dashboard_drag_handles = {}
        self.dashboard_resize_handles = {}
        self.dashboard_action_handles = {}
        self.dashboard_delete_handles = {}
        self.custom_cards = {}

        self.layout_status_label = QLabel(self)
        self.dashboard_snap_grid_size = 24
        self.dashboard_snap_to_grid = True

        self._dashboard_drag_active = False
        self._dashboard_resize_active = False

        self._dashboard_keyboard_card_id = None
        self._dashboard_keyboard_mode = None
        self._dashboard_keyboard_active = False
        self._dashboard_keyboard_original_layout = None
        self._dashboard_keyboard_original_geometry = None

        self.history = []
        self.outline = None

        self.create_dashboard_card_handles(
            self.card_id,
            self.card,
        )

        self.move_handle = (
            self.dashboard_drag_handles[
                self.card_id
            ]
        )
        self.resize_handle = (
            self.dashboard_resize_handles[
                self.card_id
            ]
        )

    def record_dashboard_layout_history(
        self,
        layout,
        label,
    ):
        self.history.append(
            (
                label,
                layout,
            )
        )

    def clear_dashboard_layout_history(self):
        return None

    def invalidate_dashboard_layout_session(self):
        return None

    def sync_dashboard_layout_controls(self):
        return None

    def schedule_dashboard_geometry_refresh(self):
        return None

    def position_dashboard_drag_handles(self):
        return None

    def show_dashboard_editor_outline(
        self,
        card_id,
        mode,
    ):
        self.outline = (
            card_id,
            mode,
        )

    def hide_dashboard_editor_outline(self):
        self.outline = None


def key_event(
    key,
    modifiers=(
        Qt.KeyboardModifier.NoModifier
    ),
):
    return QKeyEvent(
        QEvent.Type.KeyPress,
        key,
        modifiers,
    )


class DashboardKeyboardEditingTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def build_widget(self):
        return _KeyboardStub()

    def send(
        self,
        widget,
        handle,
        key,
        modifiers=(
            Qt.KeyboardModifier.NoModifier
        ),
        *,
        move=True,
        resize=False,
    ):
        return (
            widget
            .handle_dashboard_keyboard_edit_event(
                handle,
                key_event(
                    key,
                    modifiers,
                ),
                move,
                resize,
                widget.card_id,
            )
        )

    def test_handles_are_focusable_and_described(
        self,
    ):
        widget = self.build_widget()

        self.assertEqual(
            widget.move_handle.focusPolicy(),
            Qt.FocusPolicy.StrongFocus,
        )
        self.assertEqual(
            widget.resize_handle.focusPolicy(),
            Qt.FocusPolicy.StrongFocus,
        )
        self.assertIn(
            "Position",
            widget.move_handle
            .accessibleDescription(),
        )
        self.assertIn(
            "Enter to save",
            widget.resize_handle
            .accessibleDescription(),
        )

    def test_arrow_and_shift_move(
        self,
    ):
        widget = self.build_widget()

        self.send(
            widget,
            widget.move_handle,
            Qt.Key.Key_Right,
        )
        self.send(
            widget,
            widget.move_handle,
            Qt.Key.Key_Down,
            Qt.KeyboardModifier.ShiftModifier,
        )

        self.assertEqual(
            widget.card.x(),
            101,
        )
        self.assertEqual(
            widget.card.y(),
            104,
        )

    def test_resize_handle_and_control_arrow(
        self,
    ):
        widget = self.build_widget()

        self.send(
            widget,
            widget.resize_handle,
            Qt.Key.Key_Right,
            move=False,
            resize=True,
        )

        self.assertEqual(
            widget.card.width(),
            301,
        )

        self.send(
            widget,
            widget.move_handle,
            Qt.Key.Key_Down,
            Qt.KeyboardModifier.ControlModifier,
        )

        self.assertEqual(
            widget.card.height(),
            201,
        )

    def test_enter_commits_one_history_entry(
        self,
    ):
        widget = self.build_widget()

        self.send(
            widget,
            widget.move_handle,
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.ShiftModifier,
        )
        self.send(
            widget,
            widget.move_handle,
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.ShiftModifier,
        )
        self.send(
            widget,
            widget.move_handle,
            Qt.Key.Key_Return,
        )

        self.assertFalse(
            widget._dashboard_keyboard_active
        )
        self.assertEqual(
            len(widget.history),
            1,
        )
        self.assertEqual(
            widget.history[0][0],
            "card move",
        )
        self.assertEqual(
            len(
                widget.dashboard_layout_store.saved
            ),
            1,
        )

    def test_escape_restores_geometry(
        self,
    ):
        widget = self.build_widget()

        original = widget.card.geometry()

        self.send(
            widget,
            widget.move_handle,
            Qt.Key.Key_Right,
            Qt.KeyboardModifier.ShiftModifier,
        )
        self.send(
            widget,
            widget.move_handle,
            Qt.Key.Key_Escape,
        )

        self.assertEqual(
            widget.card.geometry(),
            original,
        )
        self.assertEqual(
            widget.history,
            [],
        )
        self.assertEqual(
            widget.dashboard_layout_store.saved,
            [],
        )

    def test_focus_out_commits(
        self,
    ):
        widget = self.build_widget()

        self.send(
            widget,
            widget.move_handle,
            Qt.Key.Key_Down,
            Qt.KeyboardModifier.ShiftModifier,
        )

        event = QEvent(
            QEvent.Type.FocusOut
        )

        handled = (
            widget
            .handle_dashboard_keyboard_edit_event(
                widget.move_handle,
                event,
                True,
                False,
                widget.card_id,
            )
        )

        self.assertFalse(handled)
        self.assertEqual(
            len(widget.history),
            1,
        )

    def test_locked_layout_rejects_adjustment(
        self,
    ):
        widget = self.build_widget()

        widget.dashboard_layout_state = (
            replace(
                widget.dashboard_layout_state,
                locked=True,
            )
        )

        self.assertFalse(
            widget.begin_dashboard_keyboard_adjustment(
                widget.card_id,
                "move",
            )
        )


if __name__ == "__main__":
    unittest.main()
