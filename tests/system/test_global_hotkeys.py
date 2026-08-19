from __future__ import annotations

import unittest

from src.system.global_hotkeys import (
    GlobalHotkeyRegistry,
    HotkeyBinding,
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    MOD_SHIFT,
)


class FakeHotkeyApi:
    def __init__(
        self,
    ):
        self.register_calls = []
        self.unregister_calls = []

        self.register_result = True
        self.unregister_result = True

    def register_hotkey(
        self,
        hotkey_id,
        modifiers,
        virtual_key,
    ):
        self.register_calls.append(
            (
                hotkey_id,
                modifiers,
                virtual_key,
            )
        )

        return self.register_result

    def unregister_hotkey(
        self,
        hotkey_id,
    ):
        self.unregister_calls.append(
            hotkey_id
        )

        return self.unregister_result


class GlobalHotkeyRegistryTests(
    unittest.TestCase
):
    def test_binding_adds_norepeat_for_windows(
        self,
    ):
        binding = HotkeyBinding(
            modifiers=(
                MOD_CONTROL
                | MOD_ALT
            ),
            virtual_key=0x20,
        )

        self.assertEqual(
            binding.windows_modifiers,
            (
                MOD_CONTROL
                | MOD_ALT
                | MOD_NOREPEAT
            ),
        )

    def test_binding_rejects_invalid_virtual_key(
        self,
    ):
        for value in (
            0,
            -1,
            0xFF,
            9999,
        ):
            with self.assertRaises(
                ValueError
            ):
                HotkeyBinding(
                    modifiers=MOD_CONTROL,
                    virtual_key=value,
                )

    def test_binding_rejects_unknown_modifier(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            HotkeyBinding(
                modifiers=0x1000,
                virtual_key=0x41,
            )

    def test_register_calls_windows_api(
        self,
    ):
        api = FakeHotkeyApi()

        registry = GlobalHotkeyRegistry(
            api=api
        )

        binding = HotkeyBinding(
            modifiers=(
                MOD_CONTROL
                | MOD_SHIFT
            ),
            virtual_key=0x41,
        )

        called = []

        registration = registry.register(
            "play_pause",
            binding,
            lambda: called.append(
                True
            ),
        )

        self.assertIsNotNone(
            registration
        )

        self.assertEqual(
            api.register_calls,
            [
                (
                    registration.hotkey_id,
                    binding.windows_modifiers,
                    0x41,
                )
            ],
        )

    def test_register_failure_does_not_store_binding(
        self,
    ):
        api = FakeHotkeyApi()
        api.register_result = False

        registry = GlobalHotkeyRegistry(
            api=api
        )

        binding = HotkeyBinding(
            modifiers=MOD_CONTROL,
            virtual_key=0x41,
        )

        result = registry.register(
            "play_pause",
            binding,
            lambda: None,
        )

        self.assertIsNone(
            result
        )

        self.assertEqual(
            registry.actions,
            (),
        )

        self.assertIsNone(
            registry.action_for_binding(
                binding
            )
        )

    def test_duplicate_action_is_rejected(
        self,
    ):
        api = FakeHotkeyApi()

        registry = GlobalHotkeyRegistry(
            api=api
        )

        first = HotkeyBinding(
            modifiers=MOD_CONTROL,
            virtual_key=0x41,
        )

        second = HotkeyBinding(
            modifiers=MOD_CONTROL,
            virtual_key=0x42,
        )

        self.assertIsNotNone(
            registry.register(
                "play_pause",
                first,
                lambda: None,
            )
        )

        self.assertIsNone(
            registry.register(
                "play_pause",
                second,
                lambda: None,
            )
        )

        self.assertEqual(
            len(api.register_calls),
            1,
        )

    def test_duplicate_binding_is_rejected(
        self,
    ):
        api = FakeHotkeyApi()

        registry = GlobalHotkeyRegistry(
            api=api
        )

        binding = HotkeyBinding(
            modifiers=MOD_ALT,
            virtual_key=0x4E,
        )

        self.assertIsNotNone(
            registry.register(
                "next",
                binding,
                lambda: None,
            )
        )

        self.assertIsNone(
            registry.register(
                "previous",
                binding,
                lambda: None,
            )
        )

        self.assertEqual(
            registry.action_for_binding(
                binding
            ),
            "next",
        )

    def test_dispatch_runs_matching_callback(
        self,
    ):
        api = FakeHotkeyApi()

        registry = GlobalHotkeyRegistry(
            api=api
        )

        calls = []

        registration = registry.register(
            "next",
            HotkeyBinding(
                modifiers=MOD_ALT,
                virtual_key=0x4E,
            ),
            lambda: calls.append(
                "next"
            ),
        )

        self.assertTrue(
            registry.dispatch(
                registration.hotkey_id
            )
        )

        self.assertEqual(
            calls,
            ["next"],
        )

    def test_dispatch_unknown_id_fails_safely(
        self,
    ):
        registry = GlobalHotkeyRegistry(
            api=FakeHotkeyApi()
        )

        self.assertFalse(
            registry.dispatch(
                999
            )
        )

    def test_callback_exception_fails_safely(
        self,
    ):
        registry = GlobalHotkeyRegistry(
            api=FakeHotkeyApi()
        )

        def broken_callback():
            raise RuntimeError(
                "simulated callback failure"
            )

        registration = registry.register(
            "broken",
            HotkeyBinding(
                modifiers=MOD_CONTROL,
                virtual_key=0x42,
            ),
            broken_callback,
        )

        self.assertFalse(
            registry.dispatch(
                registration.hotkey_id
            )
        )

    def test_unregister_removes_registration(
        self,
    ):
        api = FakeHotkeyApi()

        registry = GlobalHotkeyRegistry(
            api=api
        )

        binding = HotkeyBinding(
            modifiers=MOD_SHIFT,
            virtual_key=0x43,
        )

        registration = registry.register(
            "shuffle",
            binding,
            lambda: None,
        )

        self.assertTrue(
            registry.unregister(
                "shuffle"
            )
        )

        self.assertEqual(
            api.unregister_calls,
            [
                registration.hotkey_id
            ],
        )

        self.assertEqual(
            registry.actions,
            (),
        )

        self.assertIsNone(
            registry.action_for_binding(
                binding
            )
        )

        self.assertFalse(
            registry.dispatch(
                registration.hotkey_id
            )
        )

    def test_unregister_failure_keeps_registration(
        self,
    ):
        api = FakeHotkeyApi()

        registry = GlobalHotkeyRegistry(
            api=api
        )

        registration = registry.register(
            "repeat",
            HotkeyBinding(
                modifiers=MOD_CONTROL,
                virtual_key=0x52,
            ),
            lambda: None,
        )

        api.unregister_result = False

        self.assertFalse(
            registry.unregister(
                "repeat"
            )
        )

        self.assertIsNotNone(
            registry.registration_for(
                "repeat"
            )
        )

        self.assertEqual(
            registry.registration_for(
                "repeat"
            ).hotkey_id,
            registration.hotkey_id,
        )

    def test_unregister_all_cleans_every_binding(
        self,
    ):
        api = FakeHotkeyApi()

        registry = GlobalHotkeyRegistry(
            api=api
        )

        first = registry.register(
            "next",
            HotkeyBinding(
                modifiers=MOD_CONTROL,
                virtual_key=0x4E,
            ),
            lambda: None,
        )

        second = registry.register(
            "previous",
            HotkeyBinding(
                modifiers=MOD_CONTROL,
                virtual_key=0x50,
            ),
            lambda: None,
        )

        self.assertTrue(
            registry.unregister_all()
        )

        self.assertEqual(
            api.unregister_calls,
            [
                first.hotkey_id,
                second.hotkey_id,
            ],
        )

        self.assertEqual(
            registry.actions,
            (),
        )

    def test_close_is_safe_when_empty(
        self,
    ):
        api = FakeHotkeyApi()

        registry = GlobalHotkeyRegistry(
            api=api
        )

        self.assertTrue(
            registry.close()
        )

        self.assertEqual(
            api.unregister_calls,
            [],
        )

    def test_action_is_trimmed(
        self,
    ):
        registry = GlobalHotkeyRegistry(
            api=FakeHotkeyApi()
        )

        registration = registry.register(
            "  play_pause  ",
            HotkeyBinding(
                modifiers=MOD_CONTROL,
                virtual_key=0x20,
            ),
            lambda: None,
        )

        self.assertEqual(
            registration.action,
            "play_pause",
        )

        self.assertEqual(
            registry.actions,
            (
                "play_pause",
            ),
        )

    def test_empty_action_is_rejected(
        self,
    ):
        registry = GlobalHotkeyRegistry(
            api=FakeHotkeyApi()
        )

        with self.assertRaises(
            ValueError
        ):
            registry.register(
                "   ",
                HotkeyBinding(
                    modifiers=MOD_CONTROL,
                    virtual_key=0x20,
                ),
                lambda: None,
            )

    def test_non_callable_callback_is_rejected(
        self,
    ):
        registry = GlobalHotkeyRegistry(
            api=FakeHotkeyApi()
        )

        with self.assertRaises(
            TypeError
        ):
            registry.register(
                "play_pause",
                HotkeyBinding(
                    modifiers=MOD_CONTROL,
                    virtual_key=0x20,
                ),
                None,
            )


if __name__ == "__main__":
    unittest.main()
