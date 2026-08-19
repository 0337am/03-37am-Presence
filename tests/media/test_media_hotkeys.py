from __future__ import annotations

import unittest

from src.system.global_hotkeys import (
    HotkeyBinding,
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
)
from src.system.media_hotkeys import (
    ACTION_NEXT,
    ACTION_PLAY_PAUSE,
    ACTION_PREVIOUS,
    ACTION_REPEAT,
    ACTION_SEEK_BACKWARD,
    ACTION_SEEK_FORWARD,
    ACTION_SHUFFLE,
    MediaHotkeyController,
)


class FakeMediaControls:
    def __init__(
        self,
    ):
        self.calls = []
        self.result = True
        self.error_action = None

    def _record(
        self,
        action,
        value=None,
    ):
        if self.error_action == action:
            raise RuntimeError(
                "simulated media failure"
            )

        if value is None:
            self.calls.append(
                action
            )
        else:
            self.calls.append(
                (
                    action,
                    value,
                )
            )

        return self.result

    def toggle_play_pause(
        self,
    ):
        return self._record(
            "play_pause"
        )

    def skip_next(
        self,
    ):
        return self._record(
            "next"
        )

    def skip_previous(
        self,
    ):
        return self._record(
            "previous"
        )

    def toggle_shuffle(
        self,
    ):
        return self._record(
            "shuffle"
        )

    def cycle_repeat_mode(
        self,
    ):
        return self._record(
            "repeat"
        )

    def seek_by_seconds(
        self,
        seconds,
    ):
        return self._record(
            "seek",
            float(seconds),
        )


class FakeRegistry:
    def __init__(
        self,
    ):
        self.registrations = {}
        self.register_calls = []
        self.unregister_calls = []

        self.fail_action = None
        self.unregister_result = True

        self._next_id = 1

    def register(
        self,
        action,
        binding,
        callback,
    ):
        self.register_calls.append(
            (
                action,
                binding,
                callback,
            )
        )

        if action == self.fail_action:
            return None

        registration = type(
            "Registration",
            (),
            {
                "action": action,
                "binding": binding,
                "hotkey_id": self._next_id,
            },
        )()

        self._next_id += 1

        self.registrations[
            action
        ] = (
            registration,
            callback,
        )

        return registration

    def unregister(
        self,
        action,
    ):
        self.unregister_calls.append(
            action
        )

        if not self.unregister_result:
            return False

        if action not in self.registrations:
            return False

        self.registrations.pop(
            action,
            None,
        )

        return True

    def fire(
        self,
        action,
    ):
        _registration, callback = (
            self.registrations[
                action
            ]
        )

        callback()


class FakeBridge:
    def __init__(
        self,
    ):
        self.install_calls = 0
        self.remove_calls = 0

        self.install_result = True
        self.remove_result = True

    def install(
        self,
    ):
        self.install_calls += 1
        return self.install_result

    def remove(
        self,
    ):
        self.remove_calls += 1
        return self.remove_result


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


class MediaHotkeyControllerTests(
    unittest.TestCase
):
    def make_controller(
        self,
        *,
        seek_seconds=10.0,
    ):
        media = FakeMediaControls()
        registry = FakeRegistry()
        bridge = FakeBridge()

        controller = MediaHotkeyController(
            media_controls=media,
            registry=registry,
            bridge=bridge,
            seek_seconds=seek_seconds,
        )

        return (
            controller,
            media,
            registry,
            bridge,
        )

    def test_play_pause_routes_to_media_controls(
        self,
    ):
        controller, media, *_ = (
            self.make_controller()
        )

        self.assertTrue(
            controller.trigger(
                ACTION_PLAY_PAUSE
            )
        )

        self.assertEqual(
            media.calls,
            ["play_pause"],
        )

    def test_next_routes_to_media_controls(
        self,
    ):
        controller, media, *_ = (
            self.make_controller()
        )

        self.assertTrue(
            controller.trigger(
                ACTION_NEXT
            )
        )

        self.assertEqual(
            media.calls,
            ["next"],
        )

    def test_previous_routes_to_media_controls(
        self,
    ):
        controller, media, *_ = (
            self.make_controller()
        )

        self.assertTrue(
            controller.trigger(
                ACTION_PREVIOUS
            )
        )

        self.assertEqual(
            media.calls,
            ["previous"],
        )

    def test_shuffle_routes_to_media_controls(
        self,
    ):
        controller, media, *_ = (
            self.make_controller()
        )

        self.assertTrue(
            controller.trigger(
                ACTION_SHUFFLE
            )
        )

        self.assertEqual(
            media.calls,
            ["shuffle"],
        )

    def test_repeat_routes_to_media_controls(
        self,
    ):
        controller, media, *_ = (
            self.make_controller()
        )

        self.assertTrue(
            controller.trigger(
                ACTION_REPEAT
            )
        )

        self.assertEqual(
            media.calls,
            ["repeat"],
        )

    def test_seek_forward_uses_configured_amount(
        self,
    ):
        controller, media, *_ = (
            self.make_controller(
                seek_seconds=15.0
            )
        )

        self.assertTrue(
            controller.trigger(
                ACTION_SEEK_FORWARD
            )
        )

        self.assertEqual(
            media.calls,
            [
                (
                    "seek",
                    15.0,
                )
            ],
        )

    def test_seek_backward_uses_negative_amount(
        self,
    ):
        controller, media, *_ = (
            self.make_controller(
                seek_seconds=12.5
            )
        )

        self.assertTrue(
            controller.trigger(
                ACTION_SEEK_BACKWARD
            )
        )

        self.assertEqual(
            media.calls,
            [
                (
                    "seek",
                    -12.5,
                )
            ],
        )

    def test_unknown_action_fails_safely(
        self,
    ):
        controller, media, *_ = (
            self.make_controller()
        )

        self.assertFalse(
            controller.trigger(
                "launch_moon"
            )
        )

        self.assertEqual(
            media.calls,
            [],
        )

    def test_media_exception_fails_safely(
        self,
    ):
        controller, media, *_ = (
            self.make_controller()
        )

        media.error_action = "shuffle"

        self.assertFalse(
            controller.trigger(
                ACTION_SHUFFLE
            )
        )

    def test_start_installs_bridge_and_registers_bindings(
        self,
    ):
        (
            controller,
            _media,
            registry,
            bridge,
        ) = self.make_controller()

        bindings = {
            ACTION_PLAY_PAUSE:
                binding(0x31),
            ACTION_NEXT:
                binding(0x32),
        }

        self.assertTrue(
            controller.start(
                bindings
            )
        )

        self.assertTrue(
            controller.started
        )

        self.assertEqual(
            bridge.install_calls,
            1,
        )

        self.assertEqual(
            controller.registered_actions,
            (
                ACTION_PLAY_PAUSE,
                ACTION_NEXT,
            ),
        )

        self.assertEqual(
            set(
                registry.registrations
            ),
            {
                ACTION_PLAY_PAUSE,
                ACTION_NEXT,
            },
        )

    def test_registered_callback_triggers_media_action(
        self,
    ):
        (
            controller,
            media,
            registry,
            _bridge,
        ) = self.make_controller()

        self.assertTrue(
            controller.start(
                {
                    ACTION_PLAY_PAUSE:
                        binding(0x31),
                }
            )
        )

        registry.fire(
            ACTION_PLAY_PAUSE
        )

        self.assertEqual(
            media.calls,
            ["play_pause"],
        )

    def test_start_is_idempotent(
        self,
    ):
        (
            controller,
            _media,
            registry,
            bridge,
        ) = self.make_controller()

        bindings = {
            ACTION_NEXT:
                binding(0x32),
        }

        self.assertTrue(
            controller.start(
                bindings
            )
        )

        self.assertTrue(
            controller.start(
                bindings
            )
        )

        self.assertEqual(
            bridge.install_calls,
            1,
        )

        self.assertEqual(
            len(
                registry.register_calls
            ),
            1,
        )

    def test_invalid_action_is_rejected_before_install(
        self,
    ):
        (
            controller,
            _media,
            registry,
            bridge,
        ) = self.make_controller()

        self.assertFalse(
            controller.start(
                {
                    "invalid_action":
                        binding(0x31),
                }
            )
        )

        self.assertEqual(
            bridge.install_calls,
            0,
        )

        self.assertEqual(
            registry.register_calls,
            [],
        )

    def test_duplicate_binding_is_rejected_before_install(
        self,
    ):
        (
            controller,
            _media,
            registry,
            bridge,
        ) = self.make_controller()

        duplicate = binding(
            0x31
        )

        self.assertFalse(
            controller.start(
                {
                    ACTION_PLAY_PAUSE:
                        duplicate,
                    ACTION_NEXT:
                        duplicate,
                }
            )
        )

        self.assertEqual(
            bridge.install_calls,
            0,
        )

        self.assertEqual(
            registry.register_calls,
            [],
        )

    def test_registration_failure_rolls_back(
        self,
    ):
        (
            controller,
            _media,
            registry,
            bridge,
        ) = self.make_controller()

        registry.fail_action = (
            ACTION_NEXT
        )

        self.assertFalse(
            controller.start(
                {
                    ACTION_PLAY_PAUSE:
                        binding(0x31),
                    ACTION_NEXT:
                        binding(0x32),
                }
            )
        )

        self.assertEqual(
            registry.unregister_calls,
            [
                ACTION_PLAY_PAUSE
            ],
        )

        self.assertEqual(
            bridge.remove_calls,
            1,
        )

        self.assertFalse(
            controller.started
        )

    def test_bridge_install_failure_registers_nothing(
        self,
    ):
        (
            controller,
            _media,
            registry,
            bridge,
        ) = self.make_controller()

        bridge.install_result = False

        self.assertFalse(
            controller.start(
                {
                    ACTION_PLAY_PAUSE:
                        binding(0x31),
                }
            )
        )

        self.assertEqual(
            registry.register_calls,
            [],
        )

    def test_stop_unregisters_actions_and_bridge(
        self,
    ):
        (
            controller,
            _media,
            registry,
            bridge,
        ) = self.make_controller()

        self.assertTrue(
            controller.start(
                {
                    ACTION_PLAY_PAUSE:
                        binding(0x31),
                    ACTION_NEXT:
                        binding(0x32),
                }
            )
        )

        self.assertTrue(
            controller.stop()
        )

        self.assertFalse(
            controller.started
        )

        self.assertEqual(
            registry.unregister_calls,
            [
                ACTION_NEXT,
                ACTION_PLAY_PAUSE,
            ],
        )

        self.assertEqual(
            bridge.remove_calls,
            1,
        )

        self.assertEqual(
            controller.registered_actions,
            (),
        )

    def test_invalid_seek_amount_is_rejected(
        self,
    ):
        for value in (
            0,
            -10,
            float("inf"),
            float("-inf"),
            float("nan"),
            "nope",
        ):
            with self.assertRaises(
                ValueError
            ):
                MediaHotkeyController(
                    media_controls=(
                        FakeMediaControls()
                    ),
                    registry=FakeRegistry(),
                    bridge=FakeBridge(),
                    seek_seconds=value,
                )

    def test_app_required_without_injected_bridge(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            MediaHotkeyController(
                app=None,
                media_controls=(
                    FakeMediaControls()
                ),
                registry=FakeRegistry(),
            )


if __name__ == "__main__":
    unittest.main()
