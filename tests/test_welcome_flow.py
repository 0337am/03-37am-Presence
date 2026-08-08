from __future__ import annotations

import ast
import unittest
from pathlib import Path

from src.ui.welcome import (
    ACTION_DISCORD_PRESENCE,
    ACTION_GET_STARTED,
    ACTION_MEDIA_HOTKEYS,
    ACTION_MEDIA_SOURCES,
)

from src.ui.welcome_flow import (
    WelcomeFlow,
    command_line_starts_minimized,
    should_show_main_window,
)


class FakeManager:
    def __init__(
        self,
        *,
        fail=False,
    ):
        self.fail = fail
        self.completed = 0

    def mark_completed(
        self,
    ):
        if self.fail:
            raise OSError(
                "state file unavailable"
            )

        self.completed += 1


class FakeWindow:
    def __init__(
        self,
    ):
        self.show_normal_calls = 0
        self.raise_calls = 0
        self.activate_calls = 0
        self.pages = []
        self.settings_sections = []

    def showNormal(
        self,
    ):
        self.show_normal_calls += 1

    def raise_(
        self,
    ):
        self.raise_calls += 1

    def activateWindow(
        self,
    ):
        self.activate_calls += 1

    def switch_page(
        self,
        page_index,
    ):
        self.pages.append(
            page_index
        )

    def open_settings_section(
        self,
        section_name,
    ):
        self.settings_sections.append(
            section_name
        )


class FakeDialog:
    def __init__(
        self,
    ):
        self.accept_calls = 0
        self.reject_calls = 0

    def accept(
        self,
    ):
        self.accept_calls += 1

    def reject(
        self,
    ):
        self.reject_calls += 1


class WelcomeFlowTests(
    unittest.TestCase
):
    def make_flow(
        self,
        *,
        fail_completion=False,
    ):
        manager = FakeManager(
            fail=fail_completion
        )

        window = FakeWindow()
        dialog = FakeDialog()

        flow = WelcomeFlow(
            manager=manager,
            main_window=window,
            dialog=dialog,
        )

        return (
            flow,
            manager,
            window,
            dialog,
        )

    def test_minimized_argument_is_detected(
        self,
    ):
        self.assertTrue(
            command_line_starts_minimized(
                [
                    "03-37am Presence.exe",
                    "--minimized",
                ]
            )
        )

    def test_minimized_argument_is_case_insensitive(
        self,
    ):
        self.assertTrue(
            command_line_starts_minimized(
                [
                    "app.exe",
                    "--MINIMIZED",
                ]
            )
        )

    def test_normal_launch_is_not_minimized(
        self,
    ):
        self.assertFalse(
            command_line_starts_minimized(
                [
                    "app.exe",
                ]
            )
        )

    def test_executable_name_does_not_count_as_argument(
        self,
    ):
        self.assertFalse(
            command_line_starts_minimized(
                [
                    r"C:\--minimized\app.exe",
                ]
            )
        )

    def test_normal_launch_shows_main_window(
        self,
    ):
        self.assertTrue(
            should_show_main_window(
                show_welcome=False,
                start_minimized=False,
            )
        )

    def test_existing_minimized_launch_stays_hidden(
        self,
    ):
        self.assertFalse(
            should_show_main_window(
                show_welcome=False,
                start_minimized=True,
            )
        )

    def test_welcome_overrides_minimized_launch(
        self,
    ):
        self.assertTrue(
            should_show_main_window(
                show_welcome=True,
                start_minimized=True,
            )
        )

    def test_music_sources_routes_without_completion(
        self,
    ):
        (
            flow,
            manager,
            window,
            dialog,
        ) = self.make_flow()

        flow.handle_action(
            ACTION_MEDIA_SOURCES
        )

        self.assertEqual(
            manager.completed,
            0,
        )

        self.assertEqual(
            window.settings_sections,
            [
                "media_sources"
            ],
        )

        self.assertEqual(
            dialog.reject_calls,
            1,
        )

        self.assertEqual(
            window.show_normal_calls,
            1,
        )

    def test_discord_presence_routes_without_completion(
        self,
    ):
        (
            flow,
            manager,
            window,
            dialog,
        ) = self.make_flow()

        flow.handle_action(
            ACTION_DISCORD_PRESENCE
        )

        self.assertEqual(
            manager.completed,
            0,
        )

        self.assertEqual(
            window.pages,
            [
                1
            ],
        )

        self.assertEqual(
            dialog.reject_calls,
            1,
        )

    def test_hotkeys_route_without_completion(
        self,
    ):
        (
            flow,
            manager,
            window,
            dialog,
        ) = self.make_flow()

        flow.handle_action(
            ACTION_MEDIA_HOTKEYS
        )

        self.assertEqual(
            manager.completed,
            0,
        )

        self.assertEqual(
            window.settings_sections,
            [
                "media_hotkeys"
            ],
        )

        self.assertEqual(
            dialog.reject_calls,
            1,
        )

    def test_get_started_completes_and_opens_dashboard(
        self,
    ):
        (
            flow,
            manager,
            window,
            dialog,
        ) = self.make_flow()

        flow.handle_action(
            ACTION_GET_STARTED
        )

        self.assertEqual(
            manager.completed,
            1,
        )

        self.assertEqual(
            window.pages,
            [
                0
            ],
        )

        self.assertEqual(
            dialog.accept_calls,
            1,
        )

        self.assertEqual(
            dialog.reject_calls,
            0,
        )

        self.assertEqual(
            window.show_normal_calls,
            1,
        )

        self.assertEqual(
            window.raise_calls,
            1,
        )

        self.assertEqual(
            window.activate_calls,
            1,
        )

    def test_completion_failure_keeps_welcome_open(
        self,
    ):
        (
            flow,
            manager,
            window,
            dialog,
        ) = self.make_flow(
            fail_completion=True
        )

        flow.handle_action(
            ACTION_GET_STARTED
        )

        self.assertEqual(
            manager.completed,
            0,
        )

        self.assertEqual(
            window.pages,
            [],
        )

        self.assertEqual(
            dialog.accept_calls,
            0,
        )

        self.assertEqual(
            dialog.reject_calls,
            0,
        )

        self.assertEqual(
            flow.last_error,
            "state file unavailable",
        )

    def test_unknown_action_is_rejected(
        self,
    ):
        (
            flow,
            manager,
            window,
            dialog,
        ) = self.make_flow()

        with self.assertRaises(
            ValueError
        ):
            flow.handle_action(
                "enable_everything"
            )

        self.assertEqual(
            manager.completed,
            0,
        )

        self.assertEqual(
            window.pages,
            [],
        )

        self.assertEqual(
            dialog.accept_calls,
            0,
        )

        self.assertEqual(
            dialog.reject_calls,
            0,
        )

    def test_main_evaluates_first_run_before_main_window(
        self,
    ):
        source = (
            Path(__file__)
            .resolve()
            .parents[1]
            / "main.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        evaluation = source.find(
            "first_run_manager.evaluate()"
        )

        main_window = source.find(
            "window = MainWindow()"
        )

        self.assertGreaterEqual(
            evaluation,
            0,
        )

        self.assertGreaterEqual(
            main_window,
            0,
        )

        self.assertLess(
            evaluation,
            main_window,
        )

    def test_first_run_evaluation_precedes_single_instance_lock(
        self,
    ):
        source = (
            Path(__file__)
            .resolve()
            .parents[1]
            / "main.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        tree = ast.parse(
            source
        )

        main_node = None

        for node in tree.body:
            if (
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and node.name == "main"
            ):
                main_node = node
                break

        self.assertIsNotNone(
            main_node
        )

        def call_lines(
            target_name: str,
        ) -> list[int]:
            matches = []

            for node in ast.walk(
                main_node
            ):
                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue

                if isinstance(
                    node.func,
                    ast.Name,
                ):
                    name = (
                        node.func.id
                    )

                elif isinstance(
                    node.func,
                    ast.Attribute,
                ):
                    name = (
                        node.func.attr
                    )

                else:
                    continue

                if name == target_name:
                    matches.append(
                        node.lineno
                    )

            return matches

        evaluation_lines = (
            call_lines(
                "evaluate"
            )
        )

        lock_lines = (
            call_lines(
                "acquire_single_instance_lock"
            )
        )

        main_window_lines = (
            call_lines(
                "MainWindow"
            )
        )

        self.assertEqual(
            len(
                evaluation_lines
            ),
            1,
        )

        self.assertEqual(
            len(
                lock_lines
            ),
            1,
        )

        self.assertEqual(
            len(
                main_window_lines
            ),
            1,
        )

        evaluation = (
            evaluation_lines[0]
        )

        instance_lock = (
            lock_lines[0]
        )

        main_window = (
            main_window_lines[0]
        )

        self.assertLess(
            evaluation,
            instance_lock,
        )

        self.assertLess(
            instance_lock,
            main_window,
        )

    def test_main_contains_welcome_and_minimized_wiring(
        self,
    ):
        source = (
            Path(__file__)
            .resolve()
            .parents[1]
            / "main.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        required = (
            "command_line_starts_minimized(",
            "should_show_main_window(",
            "WelcomeDialog(",
            "WelcomeFlow(",
            "welcome_dialog.action_requested.connect(",
        )

        for marker in required:
            self.assertIn(
                marker,
                source,
            )


if __name__ == "__main__":
    unittest.main()
