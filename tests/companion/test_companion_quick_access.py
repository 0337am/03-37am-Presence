from __future__ import annotations

import inspect
import unittest
from types import SimpleNamespace

from src.system.quick_access_catalogue import (
    addable_quick_access_catalogue,
)
from src.system.quick_access_preferences import (
    DEFAULT_QUICK_ACCESS_ITEMS,
    QuickAccessItem,
    SUPPORTED_BUILTIN_TARGETS,
)
from src.ui.dashboard import DashboardPage
from src.ui.main_window import MainWindow


class _Runtime:
    def __init__(
        self,
        *,
        enabled=False,
        shutdown=False,
        fail=False,
    ):
        self.preferences = SimpleNamespace(
            enabled=bool(enabled)
        )

        self.is_shutdown = bool(
            shutdown
        )

        self.fail = bool(
            fail
        )

        self.calls = []

    def update_preferences(
        self,
        **changes,
    ):
        self.calls.append(
            dict(changes)
        )

        if self.fail:
            raise RuntimeError(
                "simulated update failure"
            )

        self.preferences = SimpleNamespace(
            enabled=bool(
                changes["enabled"]
            )
        )

        return self.preferences


class CompanionQuickAccessTests(
    unittest.TestCase
):
    def test_companion_is_supported_builtin_target(
        self,
    ):
        self.assertIn(
            "companion",
            SUPPORTED_BUILTIN_TARGETS,
        )

    def test_companion_catalogue_entry_is_optional(
        self,
    ):
        matches = [
            entry
            for entry in (
                addable_quick_access_catalogue(
                    ()
                )
            )
            if entry.item_id
            == "builtin.companion"
        ]

        self.assertEqual(
            len(matches),
            1,
        )

        entry = matches[0]

        self.assertEqual(
            entry.target,
            "companion",
        )

        self.assertEqual(
            entry.title,
            "Desktop Companion",
        )

        self.assertEqual(
            entry.detail,
            "Show or hide Desktop Companion",
        )

        self.assertEqual(
            entry.icon_key,
            "presence",
        )

        self.assertFalse(
            entry.included_by_default
        )

    def test_companion_is_filtered_after_add(
        self,
    ):
        ids = {
            entry.item_id
            for entry in (
                addable_quick_access_catalogue(
                    (
                        "builtin.companion",
                    )
                )
            )
        }

        self.assertNotIn(
            "builtin.companion",
            ids,
        )

    def test_existing_default_four_are_unchanged(
        self,
    ):
        ids = [
            item.item_id
            for item in (
                DEFAULT_QUICK_ACCESS_ITEMS
            )
        ]

        self.assertEqual(
            ids,
            [
                "builtin.afk",
                "builtin.custom",
                "builtin.presets",
                "builtin.settings",
            ],
        )

    def test_companion_builtin_item_validates(
        self,
    ):
        item = QuickAccessItem(
            item_id="builtin.companion",
            kind="builtin",
            target="companion",
            title="Desktop Companion",
            detail="Show or hide Desktop Companion",
            icon_key="presence",
        )

        self.assertEqual(
            item.item_id,
            "builtin.companion",
        )

        self.assertEqual(
            item.target,
            "companion",
        )

    def test_dashboard_declares_dedicated_signal(
        self,
    ):
        source = inspect.getsource(
            DashboardPage
        )

        self.assertIn(
            "companion_toggle_requested = "
            "pyqtSignal()",
            source,
        )

    def test_dashboard_route_is_signal_only(
        self,
    ):
        source = inspect.getsource(
            DashboardPage
            .refresh_quick_access_buttons
        )

        self.assertIn(
            'quick_access_item.target == "companion"',
            source,
        )

        self.assertIn(
            "self.companion_toggle_requested.emit()",
            source,
        )

        self.assertNotIn(
            "CompanionRuntime(",
            source,
        )

        self.assertNotIn(
            "update_preferences(",
            source,
        )

    def test_main_window_toggle_enables_companion(
        self,
    ):
        runtime = _Runtime(
            enabled=False
        )

        host = SimpleNamespace(
            companion_runtime=runtime
        )

        MainWindow.toggle_companion_from_dashboard(
            host
        )

        self.assertEqual(
            runtime.calls,
            [
                {
                    "enabled": True
                }
            ],
        )

    def test_main_window_toggle_disables_companion(
        self,
    ):
        runtime = _Runtime(
            enabled=True
        )

        host = SimpleNamespace(
            companion_runtime=runtime
        )

        MainWindow.toggle_companion_from_dashboard(
            host
        )

        self.assertEqual(
            runtime.calls,
            [
                {
                    "enabled": False
                }
            ],
        )

    def test_missing_runtime_is_safe(
        self,
    ):
        host = SimpleNamespace()

        MainWindow.toggle_companion_from_dashboard(
            host
        )

    def test_shutdown_and_update_failure_are_safe(
        self,
    ):
        shutdown_runtime = _Runtime(
            enabled=True,
            shutdown=True,
        )

        host = SimpleNamespace(
            companion_runtime=shutdown_runtime
        )

        MainWindow.toggle_companion_from_dashboard(
            host
        )

        self.assertEqual(
            shutdown_runtime.calls,
            [],
        )

        failed_runtime = _Runtime(
            enabled=False,
            fail=True,
        )

        host.companion_runtime = (
            failed_runtime
        )

        MainWindow.toggle_companion_from_dashboard(
            host
        )

        self.assertEqual(
            failed_runtime.calls,
            [
                {
                    "enabled": True
                }
            ],
        )

    def test_connect_services_wires_companion_signal(
        self,
    ):
        source = inspect.getsource(
            MainWindow.connect_services
        )

        self.assertIn(
            "dashboard_page."
            "companion_toggle_requested.connect",
            source,
        )

        self.assertIn(
            "self.toggle_companion_from_dashboard",
            source,
        )


if __name__ == "__main__":
    unittest.main()
