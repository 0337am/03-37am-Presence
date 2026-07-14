from __future__ import annotations

from dataclasses import replace
import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
)

from src.ui.dashboard import DashboardPage
from src.ui.dashboard_layout import (
    available_presets,
    move_card_freeform,
    preset_layout,
    validate_layout,
)


class _LayoutStore:
    def __init__(self):
        self.saved = []

    def save(self, layout):
        validated = validate_layout(
            layout
        )

        self.saved.append(
            validated
        )

        return validated


def _moved_layout(
    layout,
    distance=1,
):
    for card in layout.cards:
        for horizontal_change in (
            distance,
            -distance,
        ):
            try:
                return move_card_freeform(
                    layout,
                    card.card_id,
                    card.x
                    + horizontal_change,
                    card.y,
                )
            except ValueError:
                continue

    raise AssertionError(
        "No movable dashboard card "
        "was available for the test."
    )


class _HistoryStub(QWidget):
    clear_dashboard_layout_history = (
        DashboardPage
        .clear_dashboard_layout_history
    )

    record_dashboard_layout_history = (
        DashboardPage
        .record_dashboard_layout_history
    )

    update_dashboard_history_controls = (
        DashboardPage
        .update_dashboard_history_controls
    )

    undo_dashboard_layout = (
        DashboardPage
        .undo_dashboard_layout
    )

    redo_dashboard_layout = (
        DashboardPage
        .redo_dashboard_layout
    )

    apply_dashboard_layout = (
        DashboardPage
        .apply_dashboard_layout
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

        self.dashboard_layout_store = (
            _LayoutStore()
        )

        self._dashboard_drag_active = False
        self._dashboard_resize_active = False

        self.sync_count = 0
        self.refresh_count = 0

    def sync_dashboard_layout_controls(self):
        self.sync_count += 1
        self.update_dashboard_history_controls()

    def schedule_dashboard_geometry_refresh(self):
        self.refresh_count += 1

    def cancel_dashboard_live_drag(self):
        self._dashboard_drag_active = False

    def cancel_dashboard_live_resize(self):
        self._dashboard_resize_active = False


class DashboardHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_recorded_edit_can_undo_and_redo(
        self,
    ):
        widget = _HistoryStub()

        original = (
            widget.dashboard_layout_state
        )

        changed = _moved_layout(
            original
        )

        widget.apply_dashboard_layout(
            changed,
            persist=True,
            record_history=True,
            history_label="card move",
        )

        self.assertEqual(
            len(
                widget
                ._dashboard_layout_undo_stack
            ),
            1,
        )
        self.assertFalse(
            widget._dashboard_layout_redo_stack
        )

        self.assertTrue(
            widget.undo_dashboard_layout()
        )
        self.assertEqual(
            widget.dashboard_layout_state,
            original,
        )
        self.assertEqual(
            len(
                widget
                ._dashboard_layout_redo_stack
            ),
            1,
        )

        self.assertTrue(
            widget.redo_dashboard_layout()
        )
        self.assertEqual(
            widget.dashboard_layout_state,
            changed,
        )
        self.assertFalse(
            widget._dashboard_layout_redo_stack
        )

        widget.close()

    def test_new_edit_clears_redo_stack(
        self,
    ):
        widget = _HistoryStub()

        original = (
            widget.dashboard_layout_state
        )

        first_change = _moved_layout(
            original,
            1,
        )

        widget.apply_dashboard_layout(
            first_change,
            persist=True,
            record_history=True,
            history_label="first move",
        )

        self.assertTrue(
            widget.undo_dashboard_layout()
        )
        self.assertTrue(
            widget._dashboard_layout_redo_stack
        )

        second_change = _moved_layout(
            widget.dashboard_layout_state,
            2,
        )

        widget.apply_dashboard_layout(
            second_change,
            persist=True,
            record_history=True,
            history_label="second move",
        )

        self.assertFalse(
            widget._dashboard_layout_redo_stack
        )

        widget.close()

    def test_history_is_bounded_to_fifty_entries(
        self,
    ):
        widget = _HistoryStub()

        snapshot = (
            widget.dashboard_layout_state
        )

        for index in range(55):
            widget.record_dashboard_layout_history(
                snapshot,
                f"change {index}",
            )

        self.assertEqual(
            len(
                widget
                ._dashboard_layout_undo_stack
            ),
            50,
        )
        self.assertEqual(
            widget
            ._dashboard_layout_undo_stack[0][0],
            "change 5",
        )
        self.assertEqual(
            widget
            ._dashboard_layout_undo_stack[-1][0],
            "change 54",
        )

        widget.close()

    def test_locked_layout_blocks_navigation(
        self,
    ):
        widget = _HistoryStub()

        original = (
            widget.dashboard_layout_state
        )

        changed = _moved_layout(
            original
        )

        widget.dashboard_layout_state = replace(
            changed,
            locked=True,
        )

        widget._dashboard_layout_undo_stack.append(
            (
                "card move",
                original,
            )
        )

        self.assertFalse(
            widget.undo_dashboard_layout()
        )
        self.assertEqual(
            len(
                widget
                ._dashboard_layout_undo_stack
            ),
            1,
        )
        self.assertTrue(
            widget.dashboard_layout_state.locked
        )

        widget.close()

    def test_undo_preserves_current_editing_state(
        self,
    ):
        widget = _HistoryStub()

        locked_snapshot = preset_layout(
            available_presets()[0]
        )

        current = _moved_layout(
            replace(
                locked_snapshot,
                locked=False,
            )
        )

        widget.dashboard_layout_state = (
            current
        )

        widget._dashboard_layout_undo_stack.append(
            (
                "preset",
                locked_snapshot,
            )
        )

        self.assertTrue(
            widget.undo_dashboard_layout()
        )
        self.assertFalse(
            widget.dashboard_layout_state.locked
        )
        self.assertEqual(
            widget.dashboard_layout_state.cards,
            locked_snapshot.cards,
        )

        widget.close()


if __name__ == "__main__":
    unittest.main()
