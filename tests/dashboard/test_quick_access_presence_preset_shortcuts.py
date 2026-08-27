from __future__ import annotations

from dataclasses import replace
import sys
from types import SimpleNamespace
import unittest

from PyQt6.QtWidgets import QApplication

from src.system.quick_access_catalogue import (
    quick_access_catalogue,
)
from src.system.quick_access_preferences import (
    DEFAULT_QUICK_ACCESS_ITEMS,
    MAX_ITEMS,
    QuickAccessItem,
    QuickAccessPreferences,
    quick_access_preferences_from_payload,
    quick_access_preferences_to_payload,
)
from src.ui.dashboard import DashboardPage
from src.ui.quick_access_manager import (
    QuickAccessManagerDialog,
)
from src.ui.quick_access_picker import (
    QuickAccessPickerDialog,
)


def _dynamic_item(
    preset_id="preset-one",
    *,
    title="Preset One",
    detail="Apply Custom",
    visible=True,
):
    return QuickAccessItem(
        item_id=(
            "presence_preset."
            + preset_id
        ),
        kind="presence_preset",
        target=preset_id,
        title=title,
        detail=detail,
        icon_key="presets",
        visible=visible,
    )


def _preset(
    preset_id="preset-one",
    *,
    name="Preset One",
    mode="custom",
    pinned=False,
):
    return SimpleNamespace(
        preset_id=preset_id,
        name=name,
        mode=mode,
        pinned=pinned,
    )


class _Signal:
    def __init__(
        self,
    ):
        self.calls = []

    def emit(
        self,
        *args,
    ):
        self.calls.append(
            args
        )


class _Grid:
    def count(
        self,
    ):
        return 0


class _PreferencesStore:
    def __init__(
        self,
        preferences,
    ):
        self.preferences = preferences

    def load(
        self,
    ):
        return self.preferences


class _PresetStore:
    def __init__(
        self,
        presets=(),
    ):
        self.presets = tuple(
            presets
        )

    def load(
        self,
    ):
        return list(
            self.presets
        )

    def get(
        self,
        preset_id,
    ):
        for preset in self.presets:
            if (
                preset.preset_id
                == preset_id
            ):
                return preset

        return None

    def pinned(
        self,
    ):
        return tuple(
            preset
            for preset in self.presets
            if bool(
                preset.pinned
            )
        )


class _DashboardStub:
    def __init__(
        self,
        preferences,
        presets=(),
    ):
        self.quick_access_grid = _Grid()
        self.quick_access_buttons = []

        self.quick_access_preferences_store = (
            _PreferencesStore(
                preferences
            )
        )

        self.presence_preset_store = (
            _PresetStore(
                presets
            )
        )

        self.navigate_requested = _Signal()
        self.apply_presence_mode_requested = _Signal()
        self.apply_presence_preset_requested = _Signal()

        self.layout_calls = []

    def _make_quick_access_button(
        self,
        *,
        icon_key,
        title,
        detail,
        callback,
    ):
        return {
            "icon_key": icon_key,
            "title": title,
            "detail": detail,
            "callback": callback,
            "button": None,
        }

    def _refresh_quick_access_icons(
        self,
    ):
        return None

    def update_quick_access_layout(
        self,
        force=False,
    ):
        self.layout_calls.append(
            bool(
                force
            )
        )


class QuickAccessPresencePresetShortcutTests(
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

    def test_preference_round_trip_preserves_dynamic_preset(
        self,
    ):
        item = _dynamic_item()

        original = QuickAccessPreferences(
            items=(
                item,
            )
        )

        payload = (
            quick_access_preferences_to_payload(
                original
            )
        )

        restored = (
            quick_access_preferences_from_payload(
                payload
            )
        )

        self.assertEqual(
            restored,
            original,
        )

    def test_presence_preset_item_id_must_match_target(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id=(
                    "presence_preset."
                    "different"
                ),
                kind="presence_preset",
                target="preset-one",
                title="Preset One",
                detail="Apply Custom",
                icon_key="presets",
            )

    def test_presence_preset_icon_is_constrained(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id=(
                    "presence_preset."
                    "preset-one"
                ),
                kind="presence_preset",
                target="preset-one",
                title="Preset One",
                detail="Apply Custom",
                icon_key="custom",
            )

    def test_picker_lists_dynamic_presence_preset(
        self,
    ):
        item = _dynamic_item()

        dialog = QuickAccessPickerDialog(
            [
                entry.item_id
                for entry
                in DEFAULT_QUICK_ACCESS_ITEMS
            ],
            dynamic_items=(
                item,
            ),
        )

        self.assertEqual(
            dialog._rows[
                -1
            ][
                "item_id"
            ],
            item.item_id,
        )

        dialog._choose(
            item.item_id
        )

        self.assertEqual(
            dialog.selected_item_id(),
            item.item_id,
        )

    def test_picker_filters_existing_dynamic_presence_preset(
        self,
    ):
        item = _dynamic_item()

        existing = [
            entry.item_id
            for entry
            in quick_access_catalogue()
        ]

        existing.append(
            item.item_id
        )

        dialog = QuickAccessPickerDialog(
            existing,
            dynamic_items=(
                item,
            ),
        )

        self.assertEqual(
            dialog._rows,
            [],
        )

    def test_manager_adds_and_reoffers_removed_dynamic_item(
        self,
    ):
        item = _dynamic_item()

        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=DEFAULT_QUICK_ACCESS_ITEMS
            ),
            dynamic_items=(
                item,
            ),
        )

        self.assertTrue(
            dialog._add_item(
                item.item_id
            )
        )

        self.assertEqual(
            dialog.preferences().items[
                -1
            ].item_id,
            item.item_id,
        )

        index = (
            len(
                dialog._items
            )
            - 1
        )

        self.assertTrue(
            dialog._remove_item(
                index
            )
        )

        self.assertIn(
            item.item_id,
            [
                entry.item_id
                for entry
                in dialog._addable_entries()
            ],
        )

    def test_manager_refreshes_live_metadata_and_preserves_visibility(
        self,
    ):
        saved = _dynamic_item(
            title="Old Name",
            detail="Apply Custom",
            visible=False,
        )

        live = _dynamic_item(
            title="Renamed Preset",
            detail="Apply Working",
            visible=True,
        )

        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=(
                    saved,
                )
            ),
            dynamic_items=(
                live,
            ),
        )

        restored = (
            dialog.preferences().items[
                0
            ]
        )

        self.assertEqual(
            restored.title,
            "Renamed Preset",
        )

        self.assertEqual(
            restored.detail,
            "Apply Working",
        )

        self.assertFalse(
            restored.visible
        )

    def test_manager_keeps_stale_saved_dynamic_item(
        self,
    ):
        stale = _dynamic_item(
            title="Deleted Preset",
        )

        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=(
                    stale,
                )
            )
        )

        self.assertEqual(
            dialog.preferences().items,
            (
                stale,
            ),
        )

        self.assertTrue(
            dialog._remove_item(
                0
            )
        )

        self.assertEqual(
            dialog.preferences().items,
            (),
        )

    def test_manager_respects_max_item_limit(
        self,
    ):
        existing = tuple(
            _dynamic_item(
                f"preset-{index:02d}",
                title=(
                    f"Preset {index:02d}"
                ),
            )
            for index in range(
                MAX_ITEMS
            )
        )

        extra = _dynamic_item(
            "preset-extra",
            title="Extra",
        )

        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=existing
            ),
            dynamic_items=(
                existing
                + (
                    extra,
                )
            ),
        )

        self.assertEqual(
            dialog._addable_entries(),
            (),
        )

        self.assertFalse(
            dialog._add_item(
                extra.item_id
            )
        )

    def test_dashboard_dynamic_items_use_live_preset_metadata(
        self,
    ):
        dashboard = _DashboardStub(
            QuickAccessPreferences(
                items=()
            ),
            presets=(
                _preset(
                    name="Renamed Preset",
                    mode="working",
                ),
            ),
        )

        items = (
            DashboardPage
            ._presence_preset_quick_access_items(
                dashboard
            )
        )

        self.assertEqual(
            len(
                items
            ),
            1,
        )

        self.assertEqual(
            items[
                0
            ].title,
            "Renamed Preset",
        )

        self.assertEqual(
            items[
                0
            ].detail,
            "Apply Working",
        )

        self.assertEqual(
            items[
                0
            ].target,
            "preset-one",
        )

    def test_dashboard_managed_preset_uses_trusted_callback_and_suppresses_pin(
        self,
    ):
        item = _dynamic_item(
            title="Saved Snapshot",
        )

        preset = _preset(
            name="Live Name",
            mode="working",
            pinned=True,
        )

        dashboard = _DashboardStub(
            QuickAccessPreferences(
                items=(
                    item,
                )
            ),
            presets=(
                preset,
            ),
        )

        DashboardPage.refresh_quick_access_buttons(
            dashboard,
            force=True,
        )

        self.assertEqual(
            len(
                dashboard.quick_access_buttons
            ),
            1,
        )

        button = (
            dashboard.quick_access_buttons[
                0
            ]
        )

        self.assertEqual(
            button[
                "title"
            ],
            "Live Name",
        )

        self.assertEqual(
            button[
                "detail"
            ],
            "Apply Working",
        )

        button[
            "callback"
        ]()

        self.assertEqual(
            dashboard.apply_presence_preset_requested.calls,
            [
                (
                    "preset-one",
                ),
            ],
        )

    def test_dashboard_hidden_managed_preset_suppresses_pin(
        self,
    ):
        item = replace(
            _dynamic_item(),
            visible=False,
        )

        dashboard = _DashboardStub(
            QuickAccessPreferences(
                items=(
                    item,
                )
            ),
            presets=(
                _preset(
                    pinned=True,
                ),
            ),
        )

        DashboardPage.refresh_quick_access_buttons(
            dashboard
        )

        self.assertEqual(
            dashboard.quick_access_buttons,
            [],
        )

    def test_dashboard_stale_preset_fails_closed(
        self,
    ):
        dashboard = _DashboardStub(
            QuickAccessPreferences(
                items=(
                    _dynamic_item(
                        "deleted-preset"
                    ),
                )
            ),
            presets=(),
        )

        DashboardPage.refresh_quick_access_buttons(
            dashboard
        )

        self.assertEqual(
            dashboard.quick_access_buttons,
            [],
        )


if __name__ == "__main__":
    unittest.main()
