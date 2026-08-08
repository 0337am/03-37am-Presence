from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtCore import (
    Qt,
)
from PyQt6.QtGui import (
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.system.global_hotkeys import (
    HotkeyBinding,
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_WIN,
)
from src.system.media_hotkey_preferences import (
    MediaHotkeyPreferences,
)
from src.system.media_hotkeys import (
    ACTION_NEXT,
    ACTION_PLAY_PAUSE,
    ACTION_SEEK_FORWARD,
)
from src.ui.hotkey_sequence import (
    binding_from_sequence,
    binding_text,
    sequence_from_binding,
)
from src.ui.main_window import (
    MainWindow,
)
from src.ui.media_hotkey_settings import (
    MediaHotkeySettingsCard,
)
from src.ui.settings import (
    SettingsPage,
)


class FakeStore:
    def __init__(
        self,
        preferences=None,
    ):
        self.preferences = (
            preferences
            if preferences is not None
            else MediaHotkeyPreferences()
        )

        self.saved = []

    def load(
        self,
    ):
        return self.preferences

    def save(
        self,
        preferences,
    ):
        self.preferences = (
            preferences
        )

        self.saved.append(
            preferences
        )


class HotkeySequenceTests(
    unittest.TestCase
):
    def test_ctrl_alt_shift_digit_round_trip(
        self,
    ):
        sequence = QKeySequence(
            "Ctrl+Alt+Shift+9"
        )

        binding = (
            binding_from_sequence(
                sequence
            )
        )

        self.assertEqual(
            binding,
            HotkeyBinding(
                modifiers=(
                    MOD_CONTROL
                    | MOD_ALT
                    | MOD_SHIFT
                ),
                virtual_key=0x39,
            ),
        )

        self.assertEqual(
            binding_text(
                binding
            ),
            "Ctrl+Alt+Shift+9",
        )

    def test_letter_uses_windows_virtual_key(
        self,
    ):
        binding = (
            binding_from_sequence(
                QKeySequence(
                    "Ctrl+N"
                )
            )
        )

        self.assertEqual(
            binding.virtual_key,
            0x4E,
        )

    def test_navigation_key_maps_to_windows_vk(
        self,
    ):
        binding = (
            binding_from_sequence(
                QKeySequence(
                    "Ctrl+Right"
                )
            )
        )

        self.assertEqual(
            binding.virtual_key,
            0x27,
        )

    def test_function_key_maps_to_windows_vk(
        self,
    ):
        binding = (
            binding_from_sequence(
                QKeySequence(
                    "Ctrl+F12"
                )
            )
        )

        self.assertEqual(
            binding.virtual_key,
            0x7B,
        )

    def test_empty_sequence_means_unbound(
        self,
    ):
        self.assertIsNone(
            binding_from_sequence(
                QKeySequence()
            )
        )

    def test_unmodified_key_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            binding_from_sequence(
                QKeySequence(
                    "9"
                )
            )

    def test_unsupported_punctuation_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            binding_from_sequence(
                QKeySequence(
                    "Ctrl+["
                )
            )

    def test_win_modifier_round_trip(
        self,
    ):
        binding = HotkeyBinding(
            modifiers=(
                MOD_WIN
                | MOD_SHIFT
            ),
            virtual_key=0x39,
        )

        sequence = (
            sequence_from_binding(
                binding
            )
        )

        loaded = (
            binding_from_sequence(
                sequence
            )
        )

        self.assertEqual(
            loaded,
            binding,
        )


class MediaHotkeySettingsCardTests(
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

    def make_card(
        self,
        preferences=None,
    ):
        store = FakeStore(
            preferences
        )

        statuses = []

        card = (
            MediaHotkeySettingsCard(
                preference_store=store,
                status_callback=(
                    statuses.append
                ),
            )
        )

        return (
            card,
            store,
            statuses,
        )

    def test_card_loads_saved_preferences(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                seek_seconds=15.0,
                bindings={
                    ACTION_PLAY_PAUSE:
                        HotkeyBinding(
                            modifiers=(
                                MOD_CONTROL
                                | MOD_ALT
                            ),
                            virtual_key=0x39,
                        ),
                },
            )
        )

        card, store, statuses = (
            self.make_card(
                preferences
            )
        )

        self.assertTrue(
            card.enabled_box.isChecked()
        )

        self.assertEqual(
            card.seek_seconds_box.value(),
            15,
        )

        self.assertEqual(
            card.editors[
                ACTION_PLAY_PAUSE
            ].keySequence().toString(
                QKeySequence
                .SequenceFormat
                .PortableText
            ),
            "Ctrl+Alt+9",
        )

    def test_apply_saves_and_reloads_runtime(
        self,
    ):
        card, store, statuses = (
            self.make_card()
        )

        reload_count = {
            "value": 0
        }

        def reload_runtime():
            reload_count[
                "value"
            ] += 1

            return True

        card.set_reload_callback(
            reload_runtime
        )

        card.enabled_box.setChecked(
            True
        )

        card.seek_seconds_box.setValue(
            20
        )

        card.editors[
            ACTION_PLAY_PAUSE
        ].setKeySequence(
            QKeySequence(
                "Ctrl+Alt+Shift+9"
            )
        )

        self.assertTrue(
            card.apply_changes()
        )

        self.assertEqual(
            reload_count[
                "value"
            ],
            1,
        )

        self.assertTrue(
            store.preferences.enabled
        )

        self.assertEqual(
            store.preferences.seek_seconds,
            20.0,
        )

        self.assertIn(
            ACTION_PLAY_PAUSE,
            store.preferences.bindings,
        )

    def test_duplicate_shortcuts_are_rejected(
        self,
    ):
        card, store, statuses = (
            self.make_card()
        )

        duplicate = QKeySequence(
            "Ctrl+Alt+9"
        )

        card.editors[
            ACTION_PLAY_PAUSE
        ].setKeySequence(
            duplicate
        )

        card.editors[
            ACTION_NEXT
        ].setKeySequence(
            duplicate
        )

        self.assertFalse(
            card.apply_changes()
        )

        self.assertEqual(
            store.saved,
            [],
        )

    def test_unmodified_shortcut_is_rejected(
        self,
    ):
        card, store, statuses = (
            self.make_card()
        )

        card.editors[
            ACTION_PLAY_PAUSE
        ].setKeySequence(
            QKeySequence(
                "9"
            )
        )

        self.assertFalse(
            card.apply_changes()
        )

        self.assertEqual(
            store.saved,
            [],
        )

    def test_reload_failure_rolls_back_preferences(
        self,
    ):
        original = (
            MediaHotkeyPreferences()
        )

        card, store, statuses = (
            self.make_card(
                original
            )
        )

        results = [
            False,
            True,
        ]

        def reload_runtime():
            return results.pop(
                0
            )

        card.set_reload_callback(
            reload_runtime
        )

        card.enabled_box.setChecked(
            True
        )

        card.editors[
            ACTION_PLAY_PAUSE
        ].setKeySequence(
            QKeySequence(
                "Ctrl+9"
            )
        )

        self.assertFalse(
            card.apply_changes()
        )

        self.assertEqual(
            store.preferences,
            original,
        )

        self.assertFalse(
            card.enabled_box.isChecked()
        )

    def test_clear_action_only_clears_selected_field(
        self,
    ):
        card, store, statuses = (
            self.make_card()
        )

        card.editors[
            ACTION_PLAY_PAUSE
        ].setKeySequence(
            QKeySequence(
                "Ctrl+9"
            )
        )

        card.editors[
            ACTION_NEXT
        ].setKeySequence(
            QKeySequence(
                "Ctrl+N"
            )
        )

        self.assertTrue(
            card.clear_action_field(
                ACTION_PLAY_PAUSE
            )
        )

        self.assertEqual(
            card.editors[
                ACTION_PLAY_PAUSE
            ].keySequence().count(),
            0,
        )

        self.assertEqual(
            card.editors[
                ACTION_NEXT
            ].keySequence().count(),
            1,
        )

    def test_clear_all_fields_does_not_save_automatically(
        self,
    ):
        card, store, statuses = (
            self.make_card()
        )

        card.editors[
            ACTION_PLAY_PAUSE
        ].setKeySequence(
            QKeySequence(
                "Ctrl+9"
            )
        )

        card.editors[
            ACTION_SEEK_FORWARD
        ].setKeySequence(
            QKeySequence(
                "Ctrl+Right"
            )
        )

        card.clear_all_fields()

        self.assertTrue(
            all(
                editor.keySequence().count()
                == 0
                for editor
                in card.editors.values()
            )
        )

        self.assertEqual(
            store.saved,
            [],
        )

    def test_reset_preferences_restores_safe_defaults(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                seek_seconds=30.0,
                bindings={
                    ACTION_PLAY_PAUSE:
                        HotkeyBinding(
                            modifiers=(
                                MOD_CONTROL
                            ),
                            virtual_key=0x39,
                        ),
                },
            )
        )

        card, store, statuses = (
            self.make_card(
                preferences
            )
        )

        card.set_reload_callback(
            lambda: True
        )

        self.assertTrue(
            card.reset_preferences()
        )

        self.assertEqual(
            store.preferences,
            MediaHotkeyPreferences(),
        )


class MediaHotkeySettingsWiringTests(
    unittest.TestCase
):
    def test_settings_page_forwards_reload_callback(
        self,
    ):
        received = []

        fake_card = SimpleNamespace(
            set_reload_callback=(
                received.append
            )
        )

        fake_settings = (
            SimpleNamespace(
                media_hotkeys_card=fake_card
            )
        )

        callback = lambda: True

        SettingsPage.set_media_hotkey_reload_callback(
            fake_settings,
            callback,
        )

        self.assertEqual(
            received,
            [
                callback
            ],
        )

    def test_main_window_forwards_reload_callback(
        self,
    ):
        received = []

        fake_settings = SimpleNamespace(
            set_media_hotkey_reload_callback=(
                received.append
            )
        )

        fake_window = SimpleNamespace(
            settings_page=fake_settings
        )

        callback = lambda: True

        MainWindow.set_media_hotkey_reload_callback(
            fake_window,
            callback,
        )

        self.assertEqual(
            received,
            [
                callback
            ],
        )

    def test_main_connects_runtime_reload_to_window(
        self,
    ):
        source = Path(
            "main.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "window.set_media_hotkey_reload_callback(",
            source,
        )

        self.assertIn(
            "media_hotkey_runtime.reload",
            source,
        )


if __name__ == "__main__":
    unittest.main()
