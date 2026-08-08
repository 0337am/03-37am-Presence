from __future__ import annotations

import ctypes
import unittest
from ctypes import wintypes

from PyQt6 import sip

from src.system.qt_hotkey_bridge import (
    QtHotkeyBridge,
    QtHotkeyNativeEventFilter,
    WINDOWS_DISPATCHER_EVENT,
    WINDOWS_GENERIC_EVENT,
    WM_HOTKEY,
)


class FakeRegistry:
    def __init__(
        self,
        *,
        dispatch_result=True,
    ):
        self.dispatch_result = (
            dispatch_result
        )

        self.dispatch_calls = []

    def dispatch(
        self,
        hotkey_id,
    ):
        self.dispatch_calls.append(
            hotkey_id
        )

        return self.dispatch_result


class FakeApplication:
    def __init__(
        self,
    ):
        self.install_calls = []
        self.remove_calls = []

        self.install_error = None
        self.remove_error = None

    def installNativeEventFilter(
        self,
        filter_object,
    ):
        if self.install_error is not None:
            raise self.install_error

        self.install_calls.append(
            filter_object
        )

    def removeNativeEventFilter(
        self,
        filter_object,
    ):
        if self.remove_error is not None:
            raise self.remove_error

        self.remove_calls.append(
            filter_object
        )


def native_message_pointer(
    *,
    message_type,
    w_param=0,
):
    message = wintypes.MSG()

    message.hWnd = None
    message.message = int(
        message_type
    )

    message.wParam = int(
        w_param
    )

    message.lParam = 0
    message.time = 0

    pointer = sip.voidptr(
        ctypes.addressof(
            message
        )
    )

    return (
        message,
        pointer,
    )


class QtHotkeyNativeEventFilterTests(
    unittest.TestCase
):
    def test_dispatcher_hotkey_dispatches_registry(
        self,
    ):
        registry = FakeRegistry()

        event_filter = (
            QtHotkeyNativeEventFilter(
                registry
            )
        )

        message, pointer = (
            native_message_pointer(
                message_type=WM_HOTKEY,
                w_param=42,
            )
        )

        handled, result = (
            event_filter.nativeEventFilter(
                WINDOWS_DISPATCHER_EVENT,
                pointer,
            )
        )

        self.assertTrue(
            handled
        )

        self.assertEqual(
            registry.dispatch_calls,
            [42],
        )

        self.assertEqual(
            int(result),
            0,
        )

        self.assertEqual(
            message.message,
            WM_HOTKEY,
        )

    def test_generic_hotkey_is_also_supported(
        self,
    ):
        registry = FakeRegistry()

        event_filter = (
            QtHotkeyNativeEventFilter(
                registry
            )
        )

        _message, pointer = (
            native_message_pointer(
                message_type=WM_HOTKEY,
                w_param=7,
            )
        )

        handled, _result = (
            event_filter.nativeEventFilter(
                WINDOWS_GENERIC_EVENT,
                pointer,
            )
        )

        self.assertTrue(
            handled
        )

        self.assertEqual(
            registry.dispatch_calls,
            [7],
        )

    def test_non_hotkey_message_is_ignored(
        self,
    ):
        registry = FakeRegistry()

        event_filter = (
            QtHotkeyNativeEventFilter(
                registry
            )
        )

        _message, pointer = (
            native_message_pointer(
                message_type=0x0100,
                w_param=9,
            )
        )

        handled, _result = (
            event_filter.nativeEventFilter(
                WINDOWS_DISPATCHER_EVENT,
                pointer,
            )
        )

        self.assertFalse(
            handled
        )

        self.assertEqual(
            registry.dispatch_calls,
            [],
        )

    def test_unrelated_event_type_is_ignored(
        self,
    ):
        registry = FakeRegistry()

        event_filter = (
            QtHotkeyNativeEventFilter(
                registry
            )
        )

        _message, pointer = (
            native_message_pointer(
                message_type=WM_HOTKEY,
                w_param=10,
            )
        )

        handled, _result = (
            event_filter.nativeEventFilter(
                b"something_else",
                pointer,
            )
        )

        self.assertFalse(
            handled
        )

        self.assertEqual(
            registry.dispatch_calls,
            [],
        )

    def test_null_message_pointer_is_safe(
        self,
    ):
        registry = FakeRegistry()

        event_filter = (
            QtHotkeyNativeEventFilter(
                registry
            )
        )

        handled, result = (
            event_filter.nativeEventFilter(
                WINDOWS_DISPATCHER_EVENT,
                sip.voidptr(0),
            )
        )

        self.assertFalse(
            handled
        )

        self.assertEqual(
            registry.dispatch_calls,
            [],
        )

        self.assertEqual(
            int(result),
            0,
        )

    def test_unknown_hotkey_id_is_not_consumed(
        self,
    ):
        registry = FakeRegistry(
            dispatch_result=False
        )

        event_filter = (
            QtHotkeyNativeEventFilter(
                registry
            )
        )

        _message, pointer = (
            native_message_pointer(
                message_type=WM_HOTKEY,
                w_param=999,
            )
        )

        handled, _result = (
            event_filter.nativeEventFilter(
                WINDOWS_DISPATCHER_EVENT,
                pointer,
            )
        )

        self.assertFalse(
            handled
        )

        self.assertEqual(
            registry.dispatch_calls,
            [999],
        )


class QtHotkeyBridgeTests(
    unittest.TestCase
):
    def test_install_registers_native_filter(
        self,
    ):
        app = FakeApplication()
        registry = FakeRegistry()

        bridge = QtHotkeyBridge(
            app,
            registry,
        )

        self.assertTrue(
            bridge.install()
        )

        self.assertTrue(
            bridge.installed
        )

        self.assertEqual(
            app.install_calls,
            [
                bridge.native_filter
            ],
        )

    def test_install_is_idempotent(
        self,
    ):
        app = FakeApplication()
        registry = FakeRegistry()

        bridge = QtHotkeyBridge(
            app,
            registry,
        )

        self.assertTrue(
            bridge.install()
        )

        self.assertTrue(
            bridge.install()
        )

        self.assertEqual(
            len(
                app.install_calls
            ),
            1,
        )

    def test_remove_unregisters_native_filter(
        self,
    ):
        app = FakeApplication()
        registry = FakeRegistry()

        bridge = QtHotkeyBridge(
            app,
            registry,
        )

        self.assertTrue(
            bridge.install()
        )

        self.assertTrue(
            bridge.remove()
        )

        self.assertFalse(
            bridge.installed
        )

        self.assertEqual(
            app.remove_calls,
            [
                bridge.native_filter
            ],
        )

    def test_remove_is_safe_when_not_installed(
        self,
    ):
        app = FakeApplication()
        registry = FakeRegistry()

        bridge = QtHotkeyBridge(
            app,
            registry,
        )

        self.assertTrue(
            bridge.remove()
        )

        self.assertEqual(
            app.remove_calls,
            [],
        )

    def test_install_exception_fails_safely(
        self,
    ):
        app = FakeApplication()

        app.install_error = RuntimeError(
            "simulated install failure"
        )

        bridge = QtHotkeyBridge(
            app,
            FakeRegistry(),
        )

        self.assertFalse(
            bridge.install()
        )

        self.assertFalse(
            bridge.installed
        )

    def test_remove_exception_keeps_installed_state(
        self,
    ):
        app = FakeApplication()

        bridge = QtHotkeyBridge(
            app,
            FakeRegistry(),
        )

        self.assertTrue(
            bridge.install()
        )

        app.remove_error = RuntimeError(
            "simulated remove failure"
        )

        self.assertFalse(
            bridge.remove()
        )

        self.assertTrue(
            bridge.installed
        )

    def test_close_removes_filter(
        self,
    ):
        app = FakeApplication()

        bridge = QtHotkeyBridge(
            app,
            FakeRegistry(),
        )

        self.assertTrue(
            bridge.install()
        )

        self.assertTrue(
            bridge.close()
        )

        self.assertFalse(
            bridge.installed
        )


if __name__ == "__main__":
    unittest.main()
