from __future__ import annotations

import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
)

from src.ui.main_window import MainWindow
from src.ui.tray import TrayController


class _FakeSignal:
    def __init__(self):
        self._slots = []

    def connect(self, slot):
        if slot not in self._slots:
            self._slots.append(slot)

    def disconnect(self, slot):
        if slot not in self._slots:
            raise TypeError(
                "Slot not connected."
            )

        self._slots.remove(slot)

    def emit(self, *args):
        for slot in tuple(self._slots):
            slot(*args)

    @property
    def connection_count(self):
        return len(self._slots)


class _FakeRuntime:
    def __init__(
        self,
        *,
        enabled=False,
        fail_updates=False,
    ):
        self.preferences_changed = (
            _FakeSignal()
        )

        self.preferences = (
            SimpleNamespace(
                enabled=bool(enabled)
            )
        )

        self.is_shutdown = False
        self.fail_updates = fail_updates
        self.update_calls = []

    def update_preferences(
        self,
        **changes,
    ):
        self.update_calls.append(
            dict(changes)
        )

        if self.fail_updates:
            raise RuntimeError(
                "simulated failure"
            )

        self.preferences = (
            SimpleNamespace(
                enabled=bool(
                    changes["enabled"]
                )
            )
        )

        self.preferences_changed.emit(
            self.preferences
        )

        return self.preferences


class _FakeTray:
    def __init__(self):
        self.calls = []

    def set_companion_runtime(
        self,
        runtime,
    ):
        self.calls.append(runtime)


class CompanionTrayTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def make_controller(self):
        window = QWidget()

        with patch.object(
            TrayController,
            "create_tray_icon",
            autospec=True,
        ), patch.object(
            TrayController,
            "connect_presence_controller",
            autospec=True,
        ):
            controller = TrayController(
                self.app,
                window,
            )

        self.addCleanup(
            controller.deleteLater
        )

        self.addCleanup(
            window.deleteLater
        )

        return controller

    def test_action_is_checkable_and_disabled_without_runtime(
        self,
    ):
        controller = self.make_controller()
        action = controller.companion_action

        self.assertEqual(
            action.text(),
            "Desktop Companion",
        )

        self.assertTrue(
            action.isCheckable()
        )

        self.assertFalse(
            action.isEnabled()
        )

        self.assertFalse(
            action.isChecked()
        )

    def test_tray_does_not_own_companion_store(
        self,
    ):
        source = Path(
            "src/ui/tray.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertNotIn(
            "CompanionPreferencesStore",
            source,
        )

        self.assertNotIn(
            "src.companion.preferences",
            source,
        )

    def test_tray_does_not_create_companion_runtime(
        self,
    ):
        source = Path(
            "src/ui/tray.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertNotIn(
            "CompanionRuntime(",
            source,
        )

    def test_runtime_binding_syncs_initial_state(
        self,
    ):
        controller = self.make_controller()
        runtime = _FakeRuntime(
            enabled=True
        )

        controller.set_companion_runtime(
            runtime
        )

        self.assertTrue(
            controller
            .companion_action
            .isEnabled()
        )

        self.assertTrue(
            controller
            .companion_action
            .isChecked()
        )

        self.assertEqual(
            runtime
            .preferences_changed
            .connection_count,
            1,
        )

    def test_tray_toggle_updates_runtime_both_directions(
        self,
    ):
        controller = self.make_controller()
        runtime = _FakeRuntime(
            enabled=False
        )

        controller.set_companion_runtime(
            runtime
        )

        controller.companion_action.trigger()

        self.assertEqual(
            runtime.update_calls,
            [
                {"enabled": True}
            ],
        )

        self.assertTrue(
            controller
            .companion_action
            .isChecked()
        )

        controller.companion_action.trigger()

        self.assertEqual(
            runtime.update_calls[-1],
            {"enabled": False},
        )

        self.assertFalse(
            controller
            .companion_action
            .isChecked()
        )

    def test_runtime_signal_updates_checkmark(
        self,
    ):
        controller = self.make_controller()
        runtime = _FakeRuntime()

        controller.set_companion_runtime(
            runtime
        )

        runtime.preferences = (
            SimpleNamespace(
                enabled=True
            )
        )

        runtime.preferences_changed.emit(
            runtime.preferences
        )

        self.assertTrue(
            controller
            .companion_action
            .isChecked()
        )

        runtime.preferences = (
            SimpleNamespace(
                enabled=False
            )
        )

        runtime.preferences_changed.emit(
            runtime.preferences
        )

        self.assertFalse(
            controller
            .companion_action
            .isChecked()
        )

    def test_replacing_runtime_disconnects_previous_signal(
        self,
    ):
        controller = self.make_controller()

        first = _FakeRuntime()
        second = _FakeRuntime()

        controller.set_companion_runtime(
            first
        )

        controller.set_companion_runtime(
            second
        )

        self.assertEqual(
            first
            .preferences_changed
            .connection_count,
            0,
        )

        self.assertEqual(
            second
            .preferences_changed
            .connection_count,
            1,
        )

    def test_failed_update_and_shutdown_are_safe(
        self,
    ):
        controller = self.make_controller()

        runtime = _FakeRuntime(
            fail_updates=True
        )

        controller.set_companion_runtime(
            runtime
        )

        controller.on_companion_action_triggered(
            True
        )

        self.assertFalse(
            controller
            .companion_action
            .isChecked()
        )

        runtime.is_shutdown = True

        controller.sync_companion_action()

        self.assertFalse(
            controller
            .companion_action
            .isEnabled()
        )

        self.assertFalse(
            controller
            .companion_action
            .isChecked()
        )

    def test_main_window_tray_setter_forwards_existing_runtime(
        self,
    ):
        runtime = object()
        tray = _FakeTray()

        host = SimpleNamespace(
            companion_runtime=runtime
        )

        MainWindow.set_tray_controller(
            host,
            tray,
        )

        self.assertIs(
            host.tray_controller,
            tray,
        )

        self.assertEqual(
            tray.calls,
            [runtime],
        )

    def test_main_window_companion_setter_forwards_to_settings_and_tray(
        self,
    ):
        settings_calls = []
        tray = _FakeTray()
        runtime = object()

        host = SimpleNamespace(
            settings_page=SimpleNamespace(
                set_companion_runtime=(
                    lambda value:
                    settings_calls.append(
                        value
                    )
                )
            ),
            tray_controller=tray,
        )

        MainWindow.set_companion_runtime(
            host,
            runtime,
        )

        self.assertIs(
            host.companion_runtime,
            runtime,
        )

        self.assertEqual(
            settings_calls,
            [runtime],
        )

        self.assertEqual(
            tray.calls,
            [runtime],
        )

    def test_main_attaches_tray_controller_after_creation(
        self,
    ):
        source = Path(
            "main.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        tree = ast.parse(source)

        functions = [
            node
            for node in tree.body
            if (
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and node.name == "main"
            )
        ]

        self.assertEqual(
            len(functions),
            1,
        )

        function = functions[0]

        tray_line = None
        attach_line = None

        for statement in function.body:
            if isinstance(
                statement,
                ast.Assign,
            ):
                if any(
                    isinstance(
                        target,
                        ast.Name,
                    )
                    and target.id
                    == "tray_controller"
                    for target in statement.targets
                ):
                    tray_line = statement.lineno

            for node in ast.walk(
                statement
            ):
                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue

                function_node = node.func

                if (
                    isinstance(
                        function_node,
                        ast.Attribute,
                    )
                    and isinstance(
                        function_node.value,
                        ast.Name,
                    )
                    and function_node.value.id
                    == "window"
                    and function_node.attr
                    == "set_tray_controller"
                ):
                    attach_line = node.lineno

        self.assertIsNotNone(
            tray_line
        )

        self.assertIsNotNone(
            attach_line
        )

        self.assertGreater(
            attach_line,
            tray_line,
        )


if __name__ == "__main__":
    unittest.main()
