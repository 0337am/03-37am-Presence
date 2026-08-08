from __future__ import annotations

import unittest

from src.system.global_hotkeys import (
    HotkeyBinding,
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
)
from src.system.media_hotkey_preferences import (
    MediaHotkeyPreferences,
)
from src.system.media_hotkey_runtime import (
    MediaHotkeyRuntime,
)
from src.system.media_hotkeys import (
    ACTION_NEXT,
    ACTION_PLAY_PAUSE,
)


def binding(
    key,
):
    return HotkeyBinding(
        modifiers=(
            MOD_CONTROL
            | MOD_ALT
            | MOD_SHIFT
        ),
        virtual_key=key,
    )


class FakePreferenceStore:
    def __init__(
        self,
        preferences=None,
    ):
        self.preferences = (
            preferences
            if preferences is not None
            else MediaHotkeyPreferences()
        )

        self.load_count = 0

        self.error = None

    def load(
        self,
    ):
        self.load_count += 1

        if self.error is not None:
            raise self.error

        return self.preferences


class FakeController:
    def __init__(
        self,
        *,
        start_result=True,
        close_result=True,
    ):
        self.start_result = (
            start_result
        )

        self.close_result = (
            close_result
        )

        self.started = False

        self.start_calls = []

        self.close_count = 0

        self.registered_actions = ()

    def start(
        self,
        bindings,
    ):
        self.start_calls.append(
            dict(
                bindings
            )
        )

        if self.start_result:
            self.started = True

            self.registered_actions = (
                tuple(
                    bindings
                )
            )

        return self.start_result

    def close(
        self,
    ):
        self.close_count += 1

        if self.close_result:
            self.started = False

            self.registered_actions = ()

        return self.close_result


class FakeControllerFactory:
    def __init__(
        self,
    ):
        self.controllers = []

        self.seek_values = []

        self.start_results = []

        self.close_results = []

    def __call__(
        self,
        *,
        seek_seconds,
    ):
        self.seek_values.append(
            seek_seconds
        )

        start_result = (
            self.start_results.pop(0)
            if self.start_results
            else True
        )

        close_result = (
            self.close_results.pop(0)
            if self.close_results
            else True
        )

        controller = FakeController(
            start_result=start_result,
            close_result=close_result,
        )

        self.controllers.append(
            controller
        )

        return controller


class MediaHotkeyRuntimeTests(
    unittest.TestCase
):
    def make_runtime(
        self,
        preferences=None,
    ):
        store = FakePreferenceStore(
            preferences
        )

        factory = (
            FakeControllerFactory()
        )

        runtime = MediaHotkeyRuntime(
            app=object(),
            preference_store=store,
            controller_factory=factory,
        )

        return (
            runtime,
            store,
            factory,
        )

    def test_app_is_required(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            MediaHotkeyRuntime(
                app=None
            )

    def test_controller_factory_must_be_callable(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            MediaHotkeyRuntime(
                app=object(),
                preference_store=FakePreferenceStore(),
                controller_factory=123,
            )

    def test_disabled_preferences_start_without_controller(
        self,
    ):
        runtime, store, factory = (
            self.make_runtime()
        )

        self.assertTrue(
            runtime.start()
        )

        self.assertTrue(
            runtime.started
        )

        self.assertFalse(
            runtime.active
        )

        self.assertIsNone(
            runtime.controller
        )

        self.assertEqual(
            factory.controllers,
            [],
        )

    def test_enabled_without_bindings_starts_without_controller(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={},
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        self.assertTrue(
            runtime.start()
        )

        self.assertTrue(
            runtime.started
        )

        self.assertFalse(
            runtime.active
        )

        self.assertEqual(
            factory.controllers,
            [],
        )

    def test_enabled_bindings_create_controller(
        self,
    ):
        play_pause = binding(
            0x39
        )

        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                seek_seconds=15.0,
                bindings={
                    ACTION_PLAY_PAUSE:
                        play_pause,
                },
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        self.assertTrue(
            runtime.start()
        )

        self.assertTrue(
            runtime.active
        )

        self.assertEqual(
            factory.seek_values,
            [15.0],
        )

        self.assertEqual(
            factory.controllers[
                0
            ].start_calls,
            [
                {
                    ACTION_PLAY_PAUSE:
                        play_pause,
                }
            ],
        )

    def test_registered_actions_are_exposed(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding(
                            0x39
                        ),
                    ACTION_NEXT:
                        binding(
                            0x4E
                        ),
                },
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        self.assertTrue(
            runtime.start()
        )

        self.assertEqual(
            runtime.registered_actions,
            (
                ACTION_PLAY_PAUSE,
                ACTION_NEXT,
            ),
        )

    def test_start_is_idempotent(
        self,
    ):
        runtime, store, factory = (
            self.make_runtime()
        )

        self.assertTrue(
            runtime.start()
        )

        self.assertTrue(
            runtime.start()
        )

        self.assertEqual(
            store.load_count,
            1,
        )

    def test_preference_load_failure_fails_safely(
        self,
    ):
        runtime, store, factory = (
            self.make_runtime()
        )

        store.error = RuntimeError(
            "simulated load failure"
        )

        self.assertFalse(
            runtime.start()
        )

        self.assertFalse(
            runtime.started
        )

        self.assertEqual(
            factory.controllers,
            [],
        )

    def test_controller_start_failure_is_cleaned_up(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding(
                            0x39
                        ),
                },
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        factory.start_results = [
            False
        ]

        self.assertFalse(
            runtime.start()
        )

        self.assertEqual(
            len(
                factory.controllers
            ),
            1,
        )

        controller = (
            factory.controllers[
                0
            ]
        )

        self.assertEqual(
            controller.close_count,
            1,
        )

        self.assertIsNone(
            runtime.controller
        )

    def test_stop_closes_controller(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding(
                            0x39
                        ),
                },
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        self.assertTrue(
            runtime.start()
        )

        controller = (
            runtime.controller
        )

        self.assertTrue(
            runtime.stop()
        )

        self.assertEqual(
            controller.close_count,
            1,
        )

        self.assertFalse(
            runtime.started
        )

        self.assertFalse(
            runtime.active
        )

    def test_stop_without_controller_is_safe(
        self,
    ):
        runtime, store, factory = (
            self.make_runtime()
        )

        self.assertTrue(
            runtime.start()
        )

        self.assertTrue(
            runtime.stop()
        )

        self.assertFalse(
            runtime.started
        )

    def test_stop_failure_preserves_runtime_state(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding(
                            0x39
                        ),
                },
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        factory.close_results = [
            False
        ]

        self.assertTrue(
            runtime.start()
        )

        self.assertFalse(
            runtime.stop()
        )

        self.assertTrue(
            runtime.started
        )

        self.assertIsNotNone(
            runtime.controller
        )

    def test_reload_can_enable_hotkeys(
        self,
    ):
        runtime, store, factory = (
            self.make_runtime()
        )

        self.assertTrue(
            runtime.start()
        )

        store.preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                seek_seconds=20.0,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding(
                            0x39
                        ),
                },
            )
        )

        self.assertTrue(
            runtime.reload()
        )

        self.assertTrue(
            runtime.active
        )

        self.assertEqual(
            factory.seek_values,
            [20.0],
        )

    def test_reload_can_disable_hotkeys(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding(
                            0x39
                        ),
                },
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        self.assertTrue(
            runtime.start()
        )

        old_controller = (
            runtime.controller
        )

        store.preferences = (
            MediaHotkeyPreferences()
        )

        self.assertTrue(
            runtime.reload()
        )

        self.assertFalse(
            runtime.active
        )

        self.assertEqual(
            old_controller.close_count,
            1,
        )

    def test_reload_replaces_seek_distance(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                seek_seconds=10.0,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding(
                            0x39
                        ),
                },
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        self.assertTrue(
            runtime.start()
        )

        store.preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                seek_seconds=30.0,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding(
                            0x39
                        ),
                },
            )
        )

        self.assertTrue(
            runtime.reload()
        )

        self.assertEqual(
            factory.seek_values,
            [
                10.0,
                30.0,
            ],
        )

    def test_reload_replaces_bindings(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding(
                            0x39
                        ),
                },
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        self.assertTrue(
            runtime.start()
        )

        store.preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_NEXT:
                        binding(
                            0x4E
                        ),
                },
            )
        )

        self.assertTrue(
            runtime.reload()
        )

        self.assertEqual(
            runtime.registered_actions,
            (
                ACTION_NEXT,
            ),
        )

    def test_reload_start_failure_restores_old_controller(
        self,
    ):
        old_binding = binding(
            0x39
        )

        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        old_binding,
                },
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        self.assertTrue(
            runtime.start()
        )

        old_controller = (
            runtime.controller
        )

        store.preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_NEXT:
                        binding(
                            0x4E
                        ),
                },
            )
        )

        factory.start_results = [
            False
        ]

        self.assertFalse(
            runtime.reload()
        )

        self.assertIs(
            runtime.controller,
            old_controller,
        )

        self.assertTrue(
            old_controller.started
        )

        self.assertEqual(
            old_controller.start_calls[
                -1
            ],
            {
                ACTION_PLAY_PAUSE:
                    old_binding,
            },
        )

    def test_reload_load_failure_preserves_old_state(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding(
                            0x39
                        ),
                },
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        self.assertTrue(
            runtime.start()
        )

        old_controller = (
            runtime.controller
        )

        store.error = RuntimeError(
            "simulated reload failure"
        )

        self.assertFalse(
            runtime.reload()
        )

        self.assertIs(
            runtime.controller,
            old_controller,
        )

        self.assertTrue(
            runtime.active
        )

    def test_close_aliases_stop(
        self,
    ):
        preferences = (
            MediaHotkeyPreferences(
                enabled=True,
                bindings={
                    ACTION_PLAY_PAUSE:
                        binding(
                            0x39
                        ),
                },
            )
        )

        runtime, store, factory = (
            self.make_runtime(
                preferences
            )
        )

        self.assertTrue(
            runtime.start()
        )

        controller = (
            runtime.controller
        )

        self.assertTrue(
            runtime.close()
        )

        self.assertEqual(
            controller.close_count,
            1,
        )


if __name__ == "__main__":
    unittest.main()
