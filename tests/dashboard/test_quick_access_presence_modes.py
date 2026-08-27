from __future__ import annotations

import sys
from types import SimpleNamespace
import unittest

from PyQt6.QtWidgets import QApplication

from src.system.quick_access_preferences import (
    DEFAULT_QUICK_ACCESS_ITEMS,
    QuickAccessItem,
    QuickAccessPreferences,
    quick_access_preferences_from_payload,
    quick_access_preferences_to_payload,
)
from src.ui.dashboard import DashboardPage
from src.ui.main_window import MainWindow
from src.ui.quick_access_manager import (
    QuickAccessManagerDialog,
)
from src.ui.quick_access_picker import (
    QuickAccessPickerDialog,
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


class _PreferenceStore:
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
    def load(
        self,
    ):
        return ()

    def pinned(
        self,
    ):
        return ()


class _DashboardStub:
    def __init__(
        self,
        preferences,
    ):
        self.quick_access_grid = _Grid()
        self.quick_access_buttons = []

        self.quick_access_preferences_store = (
            _PreferenceStore(
                preferences
            )
        )

        self.presence_preset_store = (
            _PresetStore()
        )

        self.navigate_requested = _Signal()
        self.apply_presence_mode_requested = _Signal()
        self.apply_presence_preset_requested = _Signal()

    def _make_quick_access_button(
        self,
        *,
        icon_key,
        title,
        detail,
        callback,
    ):
        return {
            "button": None,
            "icon_key": icon_key,
            "title": title,
            "detail": detail,
            "callback": callback,
        }

    def _refresh_quick_access_icons(
        self,
        theme=None,
    ):
        del theme

    def update_quick_access_layout(
        self,
        force=False,
    ):
        del force


class _FakeController:
    def __init__(
        self,
    ):
        self.loaded = []
        self.applied = []

    def load_mode(
        self,
        mode,
    ):
        self.loaded.append(
            mode
        )

        return SimpleNamespace(
            mode=mode
        )

    def apply_mode(
        self,
        presence_mode,
    ):
        self.applied.append(
            presence_mode.mode
        )


class _Recorder:
    def __init__(
        self,
    ):
        self.calls = []

    def __call__(
        self,
        *args,
        **kwargs,
    ):
        self.calls.append(
            (
                args,
                kwargs,
            )
        )


class _MainWindowStub:
    def __init__(
        self,
    ):
        self.presence_controller = (
            _FakeController()
        )

        self.presence_page = (
            SimpleNamespace(
                load_active_mode=(
                    _Recorder()
                )
            )
        )

        self.dashboard_page = (
            SimpleNamespace(
                refresh_quick_access_buttons=(
                    _Recorder()
                )
            )
        )

        self.refresh_discord_status = (
            _Recorder()
        )


class QuickAccessPresenceModeTests(
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

    @staticmethod
    def mode_items():
        return (
            DashboardPage
            ._presence_mode_quick_access_items(
                object()
            )
        )

    def test_presence_mode_round_trip(
        self,
    ):
        item = QuickAccessItem(
            item_id="presence_mode.sleep",
            kind="presence_mode",
            target="sleep",
            title="Sleep",
            detail="Apply Sleep presence",
            icon_key="presets",
            visible=False,
        )

        original = QuickAccessPreferences(
            items=(
                item,
            )
        )

        restored = (
            quick_access_preferences_from_payload(
                quick_access_preferences_to_payload(
                    original
                )
            )
        )

        self.assertEqual(
            restored,
            original,
        )

    def test_presence_mode_item_id_must_match_target(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id="presence_mode.music",
                kind="presence_mode",
                target="sleep",
                title="Sleep",
                detail="Apply Sleep presence",
                icon_key="presets",
            )

    def test_afk_is_not_a_dynamic_presence_mode(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id="presence_mode.afk",
                kind="presence_mode",
                target="afk",
                title="AFK",
                detail="Apply AFK presence",
                icon_key="presets",
            )

    def test_presence_mode_icon_is_constrained(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id="presence_mode.sleep",
                kind="presence_mode",
                target="sleep",
                title="Sleep",
                detail="Apply Sleep presence",
                icon_key="settings",
            )

    def test_dashboard_exposes_expected_presence_modes(
        self,
    ):
        items = self.mode_items()

        self.assertEqual(
            [
                item.target
                for item in items
            ],
            [
                "music",
                "sleep",
                "working",
                "disabled",
            ],
        )

        self.assertEqual(
            [
                item.title
                for item in items
            ],
            [
                "Music",
                "Sleep",
                "Working",
                "Disabled",
            ],
        )

    def test_picker_lists_presence_modes(
        self,
    ):
        dialog = QuickAccessPickerDialog(
            [
                item.item_id
                for item
                in DEFAULT_QUICK_ACCESS_ITEMS
            ],
            dynamic_items=(
                self.mode_items()
            ),
        )

        self.addCleanup(
            dialog.close
        )

        ids = [
            row[
                "item_id"
            ]
            for row in dialog._rows
        ]

        for item_id in (
            "presence_mode.music",
            "presence_mode.sleep",
            "presence_mode.working",
            "presence_mode.disabled",
        ):
            self.assertIn(
                item_id,
                ids,
            )

    def test_manager_can_add_remove_and_readd_sleep(
        self,
    ):
        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=DEFAULT_QUICK_ACCESS_ITEMS
            ),
            dynamic_items=(
                self.mode_items()
            ),
        )

        self.addCleanup(
            dialog.close
        )

        self.assertTrue(
            dialog._add_item(
                "presence_mode.sleep"
            )
        )

        index = next(
            index
            for index, item
            in enumerate(
                dialog._items
            )
            if (
                item.item_id
                == "presence_mode.sleep"
            )
        )

        self.assertTrue(
            dialog._remove_item(
                index
            )
        )

        self.assertTrue(
            dialog._add_item(
                "presence_mode.sleep"
            )
        )

    def test_dashboard_sleep_uses_presence_mode_signal(
        self,
    ):
        item = QuickAccessItem(
            item_id="presence_mode.sleep",
            kind="presence_mode",
            target="sleep",
            title="Old title",
            detail="Old detail",
            icon_key="presets",
            visible=True,
        )

        dashboard = _DashboardStub(
            QuickAccessPreferences(
                items=(
                    item,
                )
            )
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
            "Sleep",
        )

        button[
            "callback"
        ]()

        self.assertEqual(
            dashboard
            .apply_presence_mode_requested
            .calls,
            [
                (
                    "sleep",
                ),
            ],
        )

        self.assertEqual(
            dashboard
            .apply_presence_preset_requested
            .calls,
            [],
        )

    def test_main_window_applies_sleep_through_existing_controller(
        self,
    ):
        window = _MainWindowStub()

        MainWindow.apply_presence_mode_from_dashboard(
            window,
            "sleep",
        )

        self.assertEqual(
            window.presence_controller.loaded,
            [
                "sleep",
            ],
        )

        self.assertEqual(
            window.presence_controller.applied,
            [
                "sleep",
            ],
        )

        self.assertEqual(
            len(
                window
                .presence_page
                .load_active_mode
                .calls
            ),
            1,
        )

        self.assertEqual(
            window
            .dashboard_page
            .refresh_quick_access_buttons
            .calls,
            [
                (
                    (),
                    {
                        "force": True,
                    },
                ),
            ],
        )

        self.assertEqual(
            len(
                window
                .refresh_discord_status
                .calls
            ),
            1,
        )

    def test_main_window_rejects_custom_direct_apply(
        self,
    ):
        window = _MainWindowStub()

        MainWindow.apply_presence_mode_from_dashboard(
            window,
            "custom",
        )

        self.assertEqual(
            window.presence_controller.loaded,
            [],
        )

        self.assertEqual(
            window.presence_controller.applied,
            [],
        )

        self.assertEqual(
            window
            .presence_page
            .load_active_mode
            .calls,
            [],
        )


if __name__ == "__main__":
    unittest.main()
