from __future__ import annotations

import inspect
import unittest

from src.ui.main_window import MainWindow


class _FakePresenceController:
    def __init__(
        self,
    ):
        self.load_calls = []
        self.apply_calls = []
        self.loaded_mode = object()

    def load_mode(
        self,
        mode,
    ):
        self.load_calls.append(
            mode
        )

        return self.loaded_mode

    def apply_mode(
        self,
        presence_mode,
    ):
        self.apply_calls.append(
            presence_mode
        )


class _FakePresencePage:
    def __init__(
        self,
    ):
        self.load_active_mode_calls = 0

    def load_active_mode(
        self,
    ):
        self.load_active_mode_calls += 1


class _FakeDashboardPage:
    def __init__(
        self,
    ):
        self.refresh_calls = []

    def refresh_quick_access_buttons(
        self,
        force=False,
    ):
        self.refresh_calls.append(
            force
        )


class _MainWindowStub:
    def __init__(
        self,
    ):
        self.presence_controller = (
            _FakePresenceController()
        )

        self.presence_page = (
            _FakePresencePage()
        )

        self.dashboard_page = (
            _FakeDashboardPage()
        )

        self.discord_status_refreshes = 0

    def refresh_discord_status(
        self,
    ):
        self.discord_status_refreshes += 1


class DashboardQuickAccessAfkSemanticsTests(
    unittest.TestCase
):
    def test_manual_afk_handler_applies_saved_afk_mode(
        self,
    ):
        window = _MainWindowStub()

        MainWindow.apply_presence_mode_from_dashboard(
            window,
            " AFK ",
        )

        self.assertEqual(
            window.presence_controller.load_calls,
            [
                "afk",
            ],
        )

        self.assertEqual(
            window.presence_controller.apply_calls,
            [
                window.presence_controller.loaded_mode,
            ],
        )

        self.assertEqual(
            window.presence_page.load_active_mode_calls,
            1,
        )

        self.assertEqual(
            window.dashboard_page.refresh_calls,
            [
                True,
            ],
        )

        self.assertEqual(
            window.discord_status_refreshes,
            1,
        )

    def test_manual_afk_handler_rejects_other_targets(
        self,
    ):
        window = _MainWindowStub()

        MainWindow.apply_presence_mode_from_dashboard(
            window,
            "custom",
        )

        self.assertEqual(
            window.presence_controller.load_calls,
            [],
        )

        self.assertEqual(
            window.presence_controller.apply_calls,
            [],
        )

        self.assertEqual(
            window.presence_page.load_active_mode_calls,
            0,
        )

        self.assertEqual(
            window.dashboard_page.refresh_calls,
            [],
        )

        self.assertEqual(
            window.discord_status_refreshes,
            0,
        )

    def test_dashboard_afk_bridge_does_not_use_auto_afk(
        self,
    ):
        handler_source = inspect.getsource(
            MainWindow.apply_presence_mode_from_dashboard
        )

        connect_source = inspect.getsource(
            MainWindow.connect_services
        )

        self.assertIn(
            "presence_controller.load_mode",
            handler_source,
        )

        self.assertIn(
            "presence_controller.apply_mode",
            handler_source,
        )

        self.assertNotIn(
            "enter_auto_afk",
            handler_source,
        )

        self.assertIn(
            "apply_presence_mode_requested.connect",
            connect_source,
        )

        self.assertIn(
            "apply_presence_mode_from_dashboard",
            connect_source,
        )


if __name__ == "__main__":
    unittest.main()
