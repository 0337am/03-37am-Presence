from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from PyQt6.QtCore import QCoreApplication

from src.companion.preferences import (
    CompanionPreferences,
)
from src.companion.runtime import (
    CompanionRuntime,
)


REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


class _Signal:
    def __init__(
        self,
    ):
        self._callbacks = []

    def connect(
        self,
        callback,
    ):
        self._callbacks.append(
            callback
        )

    def disconnect(
        self,
        callback,
    ):
        self._callbacks.remove(
            callback
        )

    def emit(
        self,
        *args,
    ):
        for callback in list(
            self._callbacks
        ):
            callback(
                *args
            )


class _FakeStore:
    def __init__(
        self,
        preferences=None,
    ):
        self.current = (
            preferences
            or CompanionPreferences()
        )

        self.updates = []
        self.fail_updates = False

    def load(
        self,
    ):
        return self.current

    def update(
        self,
        **changes,
    ):
        if self.fail_updates:
            raise OSError(
                "synthetic store failure"
            )

        self.updates.append(
            dict(
                changes
            )
        )

        self.current = replace(
            self.current,
            **changes,
        )

        return self.current


class _FakeOverlay:
    def __init__(
        self,
        *,
        screen_name="TEST-SCREEN",
        fail_asset=False,
    ):
        self.position_changed = _Signal()
        self.current_screen_name = screen_name
        self.fail_asset = fail_asset
        self.applied = []
        self.close_count = 0

    def apply_preferences(
        self,
        preferences,
    ):
        self.applied.append(
            preferences
        )

        if (
            self.fail_asset
            and preferences.asset_path
        ):
            raise FileNotFoundError(
                preferences.asset_path
            )

    def close(
        self,
    ):
        self.close_count += 1


class _FakeFullscreenController:
    def __init__(
        self,
    ):
        self.enabled_values = []
        self.stop_count = 0

    def set_enabled(
        self,
        enabled,
    ):
        self.enabled_values.append(
            bool(
                enabled
            )
        )

    def stop(
        self,
    ):
        self.stop_count += 1


class CompanionRuntimeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QCoreApplication.instance()
            or QCoreApplication([])
        )

    def make_runtime(
        self,
        *,
        preferences=None,
        screen_name="TEST-SCREEN",
        fail_asset=False,
    ):
        store = _FakeStore(
            preferences
        )

        overlay = _FakeOverlay(
            screen_name=screen_name,
            fail_asset=fail_asset,
        )

        fullscreen = (
            _FakeFullscreenController()
        )

        runtime = CompanionRuntime(
            store=store,
            overlay=overlay,
            fullscreen_controller=fullscreen,
        )

        return (
            runtime,
            store,
            overlay,
            fullscreen,
        )

    def test_start_loads_and_applies_preferences(
        self,
    ):
        preferences = CompanionPreferences(
            enabled=True,
            asset_path=r"C:\Companion\friend.png",
            hide_in_fullscreen=True,
        )

        (
            runtime,
            _store,
            overlay,
            fullscreen,
        ) = self.make_runtime(
            preferences=preferences
        )

        try:
            self.assertEqual(
                runtime.preferences,
                preferences,
            )

            self.assertEqual(
                overlay.applied,
                [
                    preferences,
                ],
            )

            self.assertEqual(
                fullscreen.enabled_values,
                [
                    True,
                ],
            )
        finally:
            runtime.shutdown()

    def test_fullscreen_requires_enabled_companion(
        self,
    ):
        (
            runtime,
            _store,
            _overlay,
            fullscreen,
        ) = self.make_runtime(
            preferences=CompanionPreferences(
                enabled=False,
                hide_in_fullscreen=True,
            )
        )

        try:
            self.assertEqual(
                fullscreen.enabled_values,
                [
                    False,
                ],
            )
        finally:
            runtime.shutdown()

    def test_update_preferences_persists_and_reapplies(
        self,
    ):
        (
            runtime,
            store,
            overlay,
            fullscreen,
        ) = self.make_runtime()

        try:
            updated = (
                runtime.update_preferences(
                    enabled=True,
                    asset_path=r"C:\Companion\friend.png",
                    hide_in_fullscreen=True,
                )
            )

            self.assertTrue(
                updated.enabled
            )

            self.assertEqual(
                store.current,
                updated,
            )

            self.assertEqual(
                overlay.applied[-1],
                updated,
            )

            self.assertTrue(
                fullscreen.enabled_values[-1]
            )
        finally:
            runtime.shutdown()

    def test_refresh_reloads_store(
        self,
    ):
        (
            runtime,
            store,
            overlay,
            _fullscreen,
        ) = self.make_runtime()

        try:
            store.current = replace(
                store.current,
                opacity=0.5,
            )

            refreshed = runtime.refresh()

            self.assertEqual(
                refreshed.opacity,
                0.5,
            )

            self.assertEqual(
                overlay.applied[-1],
                refreshed,
            )
        finally:
            runtime.shutdown()

    def test_drag_persists_position_and_screen_name(
        self,
    ):
        (
            runtime,
            store,
            overlay,
            _fullscreen,
        ) = self.make_runtime(
            preferences=CompanionPreferences(
                remember_position=True,
            ),
            screen_name="DISPLAY-B",
        )

        try:
            overlay.position_changed.emit(
                123,
                -456,
            )

            self.assertEqual(
                store.current.position_x,
                123,
            )

            self.assertEqual(
                store.current.position_y,
                -456,
            )

            self.assertEqual(
                store.current.screen_name,
                "DISPLAY-B",
            )

            self.assertEqual(
                runtime.preferences,
                store.current,
            )
        finally:
            runtime.shutdown()

    def test_drag_not_saved_when_remember_position_disabled(
        self,
    ):
        (
            runtime,
            store,
            overlay,
            _fullscreen,
        ) = self.make_runtime(
            preferences=CompanionPreferences(
                remember_position=False,
            )
        )

        try:
            overlay.position_changed.emit(
                111,
                222,
            )

            self.assertEqual(
                store.updates,
                [],
            )
        finally:
            runtime.shutdown()

    def test_drag_store_failure_is_fail_safe(
        self,
    ):
        (
            runtime,
            store,
            overlay,
            _fullscreen,
        ) = self.make_runtime(
            preferences=CompanionPreferences(
                remember_position=True,
            )
        )

        try:
            store.fail_updates = True

            overlay.position_changed.emit(
                10,
                20,
            )

            self.assertIsNone(
                runtime.preferences.position_x
            )

            self.assertFalse(
                runtime.is_shutdown
            )
        finally:
            runtime.shutdown()

    def test_invalid_asset_fails_closed_without_overwriting_store(
        self,
    ):
        preferences = CompanionPreferences(
            enabled=True,
            asset_path=r"C:\Missing\friend.gif",
            hide_in_fullscreen=True,
        )

        (
            runtime,
            store,
            overlay,
            fullscreen,
        ) = self.make_runtime(
            preferences=preferences,
            fail_asset=True,
        )

        try:
            self.assertEqual(
                store.current,
                preferences,
            )

            self.assertEqual(
                runtime.preferences,
                preferences,
            )

            self.assertTrue(
                runtime.last_error
            )

            fallback = (
                overlay.applied[-1]
            )

            self.assertFalse(
                fallback.enabled
            )

            self.assertEqual(
                fallback.asset_path,
                "",
            )

            self.assertFalse(
                fullscreen.enabled_values[-1]
            )
        finally:
            runtime.shutdown()

    def test_shutdown_stops_controller_and_overlay(
        self,
    ):
        (
            runtime,
            _store,
            overlay,
            fullscreen,
        ) = self.make_runtime()

        runtime.shutdown()

        self.assertTrue(
            runtime.is_shutdown
        )

        self.assertEqual(
            fullscreen.stop_count,
            1,
        )

        self.assertEqual(
            overlay.close_count,
            1,
        )

    def test_shutdown_is_idempotent(
        self,
    ):
        (
            runtime,
            _store,
            overlay,
            fullscreen,
        ) = self.make_runtime()

        runtime.shutdown()
        runtime.shutdown()

        self.assertEqual(
            fullscreen.stop_count,
            1,
        )

        self.assertEqual(
            overlay.close_count,
            1,
        )

    def test_updates_rejected_after_shutdown(
        self,
    ):
        (
            runtime,
            _store,
            _overlay,
            _fullscreen,
        ) = self.make_runtime()

        runtime.shutdown()

        with self.assertRaises(
            RuntimeError
        ):
            runtime.update_preferences(
                enabled=True
            )


class CompanionProductionWiringTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.main_source = (
            REPO_ROOT
            / "main.py"
        ).read_text(
            encoding="utf-8"
        )

        cls.window_source = (
            REPO_ROOT
            / "src"
            / "ui"
            / "main_window.py"
        ).read_text(
            encoding="utf-8"
        )

    def test_main_preserves_native_stage_adjacency(
        self,
    ):
        expected = (
            "install_startup_native_stage(\n"
            "        MainWindow\n"
            "    )\n\n"
            "    window = MainWindow()"
        )

        self.assertIn(
            expected,
            self.main_source,
        )

    def test_main_starts_runtime_after_window(
        self,
    ):
        window_index = (
            self.main_source.index(
                "    window = MainWindow()"
            )
        )

        runtime_index = (
            self.main_source.index(
                "    companion_runtime = "
                "start_companion_runtime("
            )
        )

        self.assertLess(
            window_index,
            runtime_index,
        )

    def test_main_helper_is_fail_safe_and_hooks_about_to_quit(
        self,
    ):
        self.assertIn(
            "def start_companion_runtime(",
            self.main_source,
        )

        self.assertIn(
            "app.aboutToQuit.connect(\n"
            "            runtime.shutdown\n"
            "        )",
            self.main_source,
        )

        self.assertIn(
            '"Desktop Companion runtime "\n'
            '            "could not start:"',
            self.main_source,
        )

    def test_main_window_has_forwarding_and_shutdown_seams(
        self,
    ):
        self.assertIn(
            "def set_companion_runtime(",
            self.window_source,
        )

        self.assertIn(
            '"set_companion_runtime"',
            self.window_source,
        )

        self.assertIn(
            "companion_shutdown()",
            self.window_source,
        )


if __name__ == "__main__":
    unittest.main()
