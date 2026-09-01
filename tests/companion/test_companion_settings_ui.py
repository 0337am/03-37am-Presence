from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from src.companion.preferences import (
    CompanionPreferences,
    default_companion_preferences,
)
from src.ui.companion_settings import (
    CompanionSettingsCard,
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
        self.callbacks = []

    def connect(
        self,
        callback,
    ):
        self.callbacks.append(
            callback
        )

    def disconnect(
        self,
        callback,
    ):
        self.callbacks.remove(
            callback
        )

    def emit(
        self,
        value,
    ):
        for callback in list(
            self.callbacks
        ):
            callback(
                value
            )


class _FakeRuntime:
    def __init__(
        self,
        preferences=None,
    ):
        self.preferences = (
            preferences
            or CompanionPreferences()
        )

        self.last_error = ""
        self.updates = []
        self.preferences_changed = _Signal()
        self.fail_updates = False

    def update_preferences(
        self,
        **changes,
    ):
        if self.fail_updates:
            raise OSError(
                "synthetic save failure"
            )

        self.updates.append(
            dict(
                changes
            )
        )

        self.preferences = replace(
            self.preferences,
            **changes,
        )

        self.preferences_changed.emit(
            self.preferences
        )

        return self.preferences


class CompanionSettingsCardTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def setUp(
        self,
    ):
        self.card = CompanionSettingsCard()

    def tearDown(
        self,
    ):
        self.card.close()
        self.card.deleteLater()
        self.app.processEvents()

    def test_card_starts_disabled_without_runtime(
        self,
    ):
        self.assertFalse(
            self.card.enabled_box.isEnabled()
        )

        self.assertIsNone(
            self.card.runtime
        )

    def test_set_runtime_loads_controls(
        self,
    ):
        runtime = _FakeRuntime(
            CompanionPreferences(
                enabled=True,
                asset_path=r"C:\Art\friend.gif",
                scale_percent=135,
                opacity=0.72,
                always_on_top=False,
                click_through=False,
                remember_position=True,
                position_x=120,
                position_y=240,
                screen_name="DISPLAY-B",
                hide_in_fullscreen=True,
                animation_speed_percent=125,
            )
        )

        self.card.set_runtime(
            runtime
        )

        self.assertTrue(
            self.card.enabled_box.isChecked()
        )

        self.assertEqual(
            self.card.scale_spin.value(),
            135,
        )

        self.assertEqual(
            self.card.opacity_spin.value(),
            72,
        )

        self.assertEqual(
            self.card.animation_speed_spin.value(),
            125,
        )

        self.assertIn(
            "DISPLAY-B",
            self.card.position_label.text(),
        )

    def test_enabled_toggle_updates_runtime(
        self,
    ):
        runtime = _FakeRuntime()

        self.card.set_runtime(
            runtime
        )

        self.card.enabled_box.setChecked(
            True
        )

        self.assertTrue(
            runtime.preferences.enabled
        )

        self.assertEqual(
            runtime.updates[-1],
            {
                "enabled": True,
            },
        )

    def test_numeric_controls_update_runtime(
        self,
    ):
        runtime = _FakeRuntime()

        self.card.set_runtime(
            runtime
        )

        self.card.scale_spin.setValue(
            145
        )

        self.card.opacity_spin.setValue(
            64
        )

        self.card.animation_speed_spin.setValue(
            150
        )

        self.assertEqual(
            runtime.preferences.scale_percent,
            145,
        )

        self.assertEqual(
            runtime.preferences.opacity,
            0.64,
        )

        self.assertEqual(
            runtime.preferences.animation_speed_percent,
            150,
        )

    def test_boolean_controls_update_runtime(
        self,
    ):
        runtime = _FakeRuntime()

        self.card.set_runtime(
            runtime
        )

        self.card.always_on_top_box.setChecked(
            False
        )

        self.card.click_through_box.setChecked(
            False
        )

        self.card.remember_position_box.setChecked(
            False
        )

        self.card.hide_in_fullscreen_box.setChecked(
            True
        )

        self.assertFalse(
            runtime.preferences.always_on_top
        )

        self.assertFalse(
            runtime.preferences.click_through
        )

        self.assertFalse(
            runtime.preferences.remember_position
        )

        self.assertTrue(
            runtime.preferences.hide_in_fullscreen
        )

    def test_choose_asset_updates_runtime(
        self,
    ):
        runtime = _FakeRuntime()

        self.card.set_runtime(
            runtime
        )

        with patch(
            "src.ui.companion_settings."
            "QFileDialog.getOpenFileName",
            return_value=(
                r"C:\Art\friend.gif",
                "",
            ),
        ):
            self.card.choose_asset()

        self.assertEqual(
            runtime.preferences.asset_path,
            r"C:\Art\friend.gif",
        )

    def test_clear_asset_disables_companion(
        self,
    ):
        runtime = _FakeRuntime(
            CompanionPreferences(
                enabled=True,
                asset_path=r"C:\Art\friend.png",
            )
        )

        self.card.set_runtime(
            runtime
        )

        self.card.clear_asset()

        self.assertFalse(
            runtime.preferences.enabled
        )

        self.assertEqual(
            runtime.preferences.asset_path,
            "",
        )

    def test_reset_position_clears_coordinates_and_monitor(
        self,
    ):
        runtime = _FakeRuntime(
            CompanionPreferences(
                position_x=100,
                position_y=200,
                screen_name="DISPLAY-B",
            )
        )

        self.card.set_runtime(
            runtime
        )

        self.card.reset_saved_position()

        self.assertIsNone(
            runtime.preferences.position_x
        )

        self.assertIsNone(
            runtime.preferences.position_y
        )

        self.assertEqual(
            runtime.preferences.screen_name,
            "",
        )

    def test_reset_defaults_restores_safe_defaults(
        self,
    ):
        runtime = _FakeRuntime(
            CompanionPreferences(
                enabled=True,
                asset_path=r"C:\Art\friend.gif",
                scale_percent=200,
                opacity=0.4,
                click_through=False,
                hide_in_fullscreen=True,
            )
        )

        self.card.set_runtime(
            runtime
        )

        self.card.reset_defaults()

        self.assertEqual(
            runtime.preferences,
            default_companion_preferences(),
        )

    def test_runtime_signal_refreshes_controls(
        self,
    ):
        runtime = _FakeRuntime()

        self.card.set_runtime(
            runtime
        )

        runtime.preferences = replace(
            runtime.preferences,
            scale_percent=180,
        )

        runtime.preferences_changed.emit(
            runtime.preferences
        )

        self.assertEqual(
            self.card.scale_spin.value(),
            180,
        )

    def test_runtime_error_is_displayed(
        self,
    ):
        runtime = _FakeRuntime()

        self.card.set_runtime(
            runtime
        )

        runtime.last_error = (
            "image could not be decoded"
        )

        self.card.refresh_from_runtime()

        self.assertIn(
            "image could not be decoded",
            self.card.status_label.text(),
        )

    def test_update_failure_is_nonfatal_and_visible(
        self,
    ):
        runtime = _FakeRuntime()

        self.card.set_runtime(
            runtime
        )

        runtime.fail_updates = True

        self.card.scale_spin.setValue(
            160
        )

        self.assertIn(
            "synthetic save failure",
            self.card.status_label.text(),
        )


class CompanionSettingsWiringTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.source = (
            REPO_ROOT
            / "src"
            / "ui"
            / "settings.py"
        ).read_text(
            encoding="utf-8"
        )

    def test_settings_page_wires_companion_card_and_runtime(
        self,
    ):
        self.assertIn(
            "from src.ui.companion_settings import (",
            self.source,
        )

        self.assertIn(
            "self.companion_settings_card = (",
            self.source,
        )

        self.assertIn(
            "def set_companion_runtime(",
            self.source,
        )

        self.assertIn(
            "self.companion_settings_card.set_runtime(",
            self.source,
        )

    def test_settings_registers_customization_and_deep_link(
        self,
    ):
        self.assertIn(
            '"desktop_companion"',
            self.source,
        )

        self.assertIn(
            "self.settings_category_cards",
            self.source,
        )

        self.assertIn(
            "_register_companion_settings_card",
            self.source,
        )


if __name__ == "__main__":
    unittest.main()
