from __future__ import annotations

import inspect
import unittest

from dataclasses import replace
from types import SimpleNamespace

from src.system.quick_access_preferences import (
    DEFAULT_QUICK_ACCESS_ITEMS,
    QuickAccessPreferences,
    default_quick_access_preferences,
)
from src.ui.dashboard import DashboardPage


class _EmptyGrid:
    def count(
        self,
    ):
        return 0


class _FakeSignal:
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


class _FakeQuickAccessStore:
    def __init__(
        self,
        preferences,
    ):
        self.preferences = preferences
        self.load_count = 0

    def load(
        self,
    ):
        self.load_count += 1
        return self.preferences


class _FakePresetStore:
    def __init__(
        self,
        presets=(),
    ):
        self.presets = tuple(
            presets
        )

    def pinned(
        self,
    ):
        return self.presets


class _DashboardStub:
    def __init__(
        self,
        preferences=None,
        presets=(),
    ):
        if preferences is None:
            preferences = (
                default_quick_access_preferences()
            )

        self.quick_access_grid = (
            _EmptyGrid()
        )

        self.quick_access_buttons = []

        self.quick_access_preferences_store = (
            _FakeQuickAccessStore(
                preferences
            )
        )

        self.presence_preset_store = (
            _FakePresetStore(
                presets
            )
        )

        self.navigate_requested = (
            _FakeSignal()
        )

        self.apply_presence_mode_requested = (
            _FakeSignal()
        )

        self.apply_presence_preset_requested = (
            _FakeSignal()
        )

        self.icon_refresh_count = 0
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
        self.icon_refresh_count += 1

    def update_quick_access_layout(
        self,
        force=False,
    ):
        self.layout_calls.append(
            force
        )


class DashboardQuickAccessPreferencesIntegrationTests(
    unittest.TestCase
):
    def test_dashboard_owns_quick_access_store(
        self,
    ):
        source = inspect.getsource(
            DashboardPage.__init__
        )

        self.assertIn(
            "QuickAccessPreferencesStore()",
            source,
        )

        self.assertIn(
            "quick_access_preferences_store",
            source,
        )

    def test_default_preferences_preserve_existing_button_order(
        self,
    ):
        dashboard = _DashboardStub()

        DashboardPage.refresh_quick_access_buttons(
            dashboard,
            force=True,
        )

        self.assertEqual(
            [
                item[
                    "title"
                ]
                for item
                in dashboard.quick_access_buttons
            ],
            [
                "AFK",
                "Custom",
                "Presets",
                "Settings",
            ],
        )

        self.assertEqual(
            [
                item[
                    "detail"
                ]
                for item
                in dashboard.quick_access_buttons
            ],
            [
                "Set AFK presence",
                "Create a presence",
                "Manage presence modes",
                "Configure application",
            ],
        )

        self.assertEqual(
            [
                item[
                    "icon_key"
                ]
                for item
                in dashboard.quick_access_buttons
            ],
            [
                "afk",
                "custom",
                "presets",
                "settings",
            ],
        )

        self.assertEqual(
            dashboard.quick_access_preferences_store.load_count,
            1,
        )

        self.assertEqual(
            dashboard.icon_refresh_count,
            1,
        )

        self.assertEqual(
            dashboard.layout_calls,
            [
                True,
            ],
        )

    def test_builtin_callbacks_preserve_routes_and_apply_afk(
        self,
    ):
        dashboard = _DashboardStub()

        DashboardPage.refresh_quick_access_buttons(
            dashboard
        )

        for item in dashboard.quick_access_buttons:
            item[
                "callback"
            ]()

        self.assertEqual(
            dashboard.apply_presence_mode_requested.calls,
            [
                (
                    "afk",
                ),
            ],
        )

        self.assertEqual(
            dashboard.navigate_requested.calls,
            [
                (1,),
                (1,),
                (3,),
            ],
        )


    def test_saved_order_and_visibility_are_honored(
        self,
    ):
        preferences = QuickAccessPreferences(
            items=(
                DEFAULT_QUICK_ACCESS_ITEMS[
                    3
                ],
                replace(
                    DEFAULT_QUICK_ACCESS_ITEMS[
                        0
                    ],
                    visible=False,
                ),
                DEFAULT_QUICK_ACCESS_ITEMS[
                    1
                ],
            )
        )

        dashboard = _DashboardStub(
            preferences=preferences
        )

        DashboardPage.refresh_quick_access_buttons(
            dashboard
        )

        self.assertEqual(
            [
                item[
                    "title"
                ]
                for item
                in dashboard.quick_access_buttons
            ],
            [
                "Settings",
                "Custom",
            ],
        )

        for item in dashboard.quick_access_buttons:
            item[
                "callback"
            ]()

        self.assertEqual(
            dashboard.navigate_requested.calls,
            [
                (3,),
                (1,),
            ],
        )

    def test_pinned_presence_presets_remain_appended(
        self,
    ):
        preset = SimpleNamespace(
            preset_id="preset-example",
            name="Pinned Example",
            mode="example",
        )

        dashboard = _DashboardStub(
            presets=(
                preset,
            )
        )

        DashboardPage.refresh_quick_access_buttons(
            dashboard
        )

        self.assertEqual(
            [
                item[
                    "title"
                ]
                for item
                in dashboard.quick_access_buttons
            ],
            [
                "AFK",
                "Custom",
                "Presets",
                "Settings",
                "Pinned Example",
            ],
        )

        pinned = (
            dashboard.quick_access_buttons[
                -1
            ]
        )

        self.assertEqual(
            pinned[
                "icon_key"
            ],
            "presets",
        )

        pinned[
            "callback"
        ]()

        self.assertEqual(
            dashboard.apply_presence_preset_requested.calls,
            [
                (
                    "preset-example",
                ),
            ],
        )

    def test_refresh_reloads_preferences_each_time(
        self,
    ):
        dashboard = _DashboardStub()

        DashboardPage.refresh_quick_access_buttons(
            dashboard
        )

        self.assertEqual(
            len(
                dashboard.quick_access_buttons
            ),
            4,
        )

        dashboard.quick_access_preferences_store.preferences = (
            QuickAccessPreferences(
                items=()
            )
        )

        DashboardPage.refresh_quick_access_buttons(
            dashboard
        )

        self.assertEqual(
            dashboard.quick_access_buttons,
            [],
        )

        self.assertEqual(
            dashboard.quick_access_preferences_store.load_count,
            2,
        )


if __name__ == "__main__":
    unittest.main()
