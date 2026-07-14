from __future__ import annotations

from dataclasses import replace
import unittest

from src.ui.dashboard import DashboardPage
from src.ui.dashboard_layout import (
    available_presets,
    preset_layout,
    validate_layout,
)


class _ButtonStub:
    def __init__(self):
        self.enabled = True
        self.tooltip = ""

    def setEnabled(
        self,
        enabled,
    ):
        self.enabled = bool(enabled)

    def setToolTip(
        self,
        tooltip,
    ):
        self.tooltip = str(tooltip)


class _LayoutStore:
    def __init__(self):
        self.saved = []

    def save(
        self,
        layout,
    ):
        validated = validate_layout(
            layout
        )

        self.saved.append(
            validated
        )

        return validated


class _SessionStub:
    dashboard_layout_session_card_ids = (
        DashboardPage
        .dashboard_layout_session_card_ids
    )

    begin_dashboard_layout_session = (
        DashboardPage
        .begin_dashboard_layout_session
    )

    end_dashboard_layout_session = (
        DashboardPage
        .end_dashboard_layout_session
    )

    invalidate_dashboard_layout_session = (
        DashboardPage
        .invalidate_dashboard_layout_session
    )

    dashboard_layout_session_is_safe = (
        DashboardPage
        .dashboard_layout_session_is_safe
    )

    dashboard_layout_session_has_changes = (
        DashboardPage
        .dashboard_layout_session_has_changes
    )

    update_dashboard_layout_session_controls = (
        DashboardPage
        .update_dashboard_layout_session_controls
    )

    revert_dashboard_layout_session = (
        DashboardPage
        .revert_dashboard_layout_session
    )

    toggle_dashboard_layout_lock = (
        DashboardPage
        .toggle_dashboard_layout_lock
    )

    def __init__(self):
        self.dashboard_layout_state = replace(
            preset_layout(
                available_presets()[0]
            ),
            locked=True,
        )

        self.dashboard_layout_store = (
            _LayoutStore()
        )

        self.layout_revert_session_button = (
            _ButtonStub()
        )

        self._dashboard_layout_undo_stack = []
        self._dashboard_layout_redo_stack = []

        self._dashboard_layout_session_baseline = None
        self._dashboard_layout_session_card_ids = (
            frozenset()
        )
        self._dashboard_layout_session_valid = False

        self._dashboard_drag_active = False
        self._dashboard_resize_active = False

        self.recorded_history = []

        self.update_dashboard_layout_session_controls()

    def apply_dashboard_layout(
        self,
        layout,
        *,
        persist=False,
        sync_controls=True,
        record_history=False,
        history_label="change",
    ):
        previous_layout = (
            self.dashboard_layout_state
        )

        validated = validate_layout(
            layout
        )

        if persist:
            validated = (
                self.dashboard_layout_store.save(
                    validated
                )
            )

        if (
            record_history
            and validated != previous_layout
        ):
            self.recorded_history.append(
                (
                    history_label,
                    previous_layout,
                )
            )

        self.dashboard_layout_state = (
            validated
        )

        if sync_controls:
            self.sync_dashboard_layout_controls()

        return validated

    def sync_dashboard_layout_controls(
        self,
    ):
        self.update_dashboard_layout_session_controls()

    def cancel_dashboard_live_drag(
        self,
    ):
        self._dashboard_drag_active = False

    def cancel_dashboard_live_resize(
        self,
    ):
        self._dashboard_resize_active = False


def changed_layout(
    layout,
):
    return replace(
        layout,
        preset="Custom",
    )


class DashboardSessionTests(unittest.TestCase):
    def test_editing_lifecycle_captures_and_clears_snapshot(
        self,
    ):
        page = _SessionStub()

        initial = replace(
            page.dashboard_layout_state,
            locked=False,
        )

        page.toggle_dashboard_layout_lock()

        self.assertFalse(
            page.dashboard_layout_state.locked
        )
        self.assertEqual(
            page._dashboard_layout_session_baseline,
            initial,
        )
        self.assertTrue(
            page._dashboard_layout_session_valid
        )
        self.assertFalse(
            page.layout_revert_session_button.enabled
        )

        page.apply_dashboard_layout(
            changed_layout(
                page.dashboard_layout_state
            ),
            persist=True,
        )

        self.assertTrue(
            page.layout_revert_session_button.enabled
        )

        page.toggle_dashboard_layout_lock()

        self.assertTrue(
            page.dashboard_layout_state.locked
        )
        self.assertIsNone(
            page._dashboard_layout_session_baseline
        )
        self.assertFalse(
            page._dashboard_layout_session_valid
        )
        self.assertFalse(
            page.layout_revert_session_button.enabled
        )

    def test_revert_restores_baseline_and_records_history(
        self,
    ):
        page = _SessionStub()

        page.toggle_dashboard_layout_lock()

        baseline = (
            page._dashboard_layout_session_baseline
        )

        changed = changed_layout(
            page.dashboard_layout_state
        )

        page.apply_dashboard_layout(
            changed,
            persist=True,
        )

        self.assertTrue(
            page.revert_dashboard_layout_session()
        )

        self.assertEqual(
            page.dashboard_layout_state,
            baseline,
        )
        self.assertFalse(
            page.dashboard_layout_state.locked
        )
        self.assertEqual(
            page.dashboard_layout_store.saved[-1],
            baseline,
        )
        self.assertEqual(
            page.recorded_history[-1][0],
            "session revert",
        )
        self.assertEqual(
            page.recorded_history[-1][1],
            changed,
        )
        self.assertFalse(
            page.layout_revert_session_button.enabled
        )

    def test_revert_rejects_locked_or_unchanged_layout(
        self,
    ):
        page = _SessionStub()

        self.assertFalse(
            page.revert_dashboard_layout_session()
        )

        page.toggle_dashboard_layout_lock()

        self.assertFalse(
            page.revert_dashboard_layout_session()
        )
        self.assertEqual(
            page.recorded_history,
            [],
        )

    def test_card_id_mismatch_blocks_revert(
        self,
    ):
        page = _SessionStub()

        page.toggle_dashboard_layout_lock()

        page.apply_dashboard_layout(
            changed_layout(
                page.dashboard_layout_state
            ),
            persist=True,
        )

        page._dashboard_layout_session_card_ids = (
            frozenset(
                {
                    "missing-card",
                }
            )
        )

        page.update_dashboard_layout_session_controls()

        self.assertFalse(
            page.dashboard_layout_session_is_safe()
        )
        self.assertFalse(
            page.layout_revert_session_button.enabled
        )
        self.assertFalse(
            page.revert_dashboard_layout_session()
        )

    def test_structural_invalidation_disables_session(
        self,
    ):
        page = _SessionStub()

        page.toggle_dashboard_layout_lock()

        page.apply_dashboard_layout(
            changed_layout(
                page.dashboard_layout_state
            ),
            persist=True,
        )

        self.assertTrue(
            page.layout_revert_session_button.enabled
        )

        page.invalidate_dashboard_layout_session()

        self.assertFalse(
            page._dashboard_layout_session_valid
        )
        self.assertFalse(
            page.layout_revert_session_button.enabled
        )
        self.assertIn(
            "adding",
            page.layout_revert_session_button
            .tooltip
            .casefold(),
        )

    def test_reentering_edit_mode_starts_fresh_session(
        self,
    ):
        page = _SessionStub()

        page.toggle_dashboard_layout_lock()

        page.apply_dashboard_layout(
            changed_layout(
                page.dashboard_layout_state
            ),
            persist=True,
        )

        page.toggle_dashboard_layout_lock()

        locked_layout = (
            page.dashboard_layout_state
        )

        page.toggle_dashboard_layout_lock()

        expected_baseline = replace(
            locked_layout,
            locked=False,
        )

        self.assertEqual(
            page._dashboard_layout_session_baseline,
            expected_baseline,
        )
        self.assertTrue(
            page._dashboard_layout_session_valid
        )
        self.assertFalse(
            page.dashboard_layout_session_has_changes()
        )
        self.assertFalse(
            page.layout_revert_session_button.enabled
        )


if __name__ == "__main__":
    unittest.main()
