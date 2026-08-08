from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Protocol

from PyQt6 import sip
from PyQt6.QtCore import (
    QAbstractNativeEventFilter,
)

from src.system.global_hotkeys import (
    GlobalHotkeyRegistry,
)


WM_HOTKEY = 0x0312

WINDOWS_GENERIC_EVENT = (
    b"windows_generic_MSG"
)

WINDOWS_DISPATCHER_EVENT = (
    b"windows_dispatcher_MSG"
)

WINDOWS_EVENT_TYPES = frozenset(
    (
        WINDOWS_GENERIC_EVENT,
        WINDOWS_DISPATCHER_EVENT,
    )
)


class NativeFilterApplication(
    Protocol
):
    def installNativeEventFilter(
        self,
        filter_object,
    ) -> None:
        ...

    def removeNativeEventFilter(
        self,
        filter_object,
    ) -> None:
        ...


class QtHotkeyNativeEventFilter(
    QAbstractNativeEventFilter
):
    """
    Converts Qt's native Windows MSG events into hotkey-registry
    dispatches.

    RegisterHotKey messages are normally delivered by Qt as
    windows_dispatcher_MSG because they are system-wide dispatcher
    messages. windows_generic_MSG is accepted as well so the bridge
    remains tolerant of Windows/Qt delivery differences.
    """

    def __init__(
        self,
        registry: GlobalHotkeyRegistry,
    ):
        super().__init__()

        self.registry = registry

    def nativeEventFilter(
        self,
        event_type,
        message,
    ):
        result = sip.voidptr(
            0
        )

        normalized_event_type = (
            self._normalize_event_type(
                event_type
            )
        )

        if (
            normalized_event_type
            not in WINDOWS_EVENT_TYPES
        ):
            return (
                False,
                result,
            )

        windows_message = (
            self._message_from_pointer(
                message
            )
        )

        if windows_message is None:
            return (
                False,
                result,
            )

        if (
            int(
                windows_message.message
            )
            != WM_HOTKEY
        ):
            return (
                False,
                result,
            )

        hotkey_id = int(
            windows_message.wParam
        )

        handled = bool(
            self.registry.dispatch(
                hotkey_id
            )
        )

        return (
            handled,
            result,
        )

    def _normalize_event_type(
        self,
        event_type,
    ) -> bytes:
        try:
            return bytes(
                event_type
            )

        except Exception:
            return b""

    def _message_from_pointer(
        self,
        message,
    ):
        try:
            address = int(
                message
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if not address:
            return None

        try:
            pointer = ctypes.cast(
                address,
                ctypes.POINTER(
                    wintypes.MSG
                ),
            )

            return pointer.contents

        except (
            TypeError,
            ValueError,
            OSError,
        ):
            return None


class QtHotkeyBridge:
    """
    Owns installation of the native event filter on the Qt application.

    The hotkey registry remains independently owned. This bridge only
    forwards WM_HOTKEY messages and manages the Qt filter lifecycle.
    """

    def __init__(
        self,
        app: NativeFilterApplication,
        registry: GlobalHotkeyRegistry,
    ):
        self.app = app
        self.registry = registry

        self.native_filter = (
            QtHotkeyNativeEventFilter(
                registry
            )
        )

        self._installed = False

    @property
    def installed(
        self,
    ) -> bool:
        return self._installed

    def install(
        self,
    ) -> bool:
        if self._installed:
            return True

        try:
            self.app.installNativeEventFilter(
                self.native_filter
            )

        except Exception as error:
            print(
                "Global hotkey native filter "
                "install error:",
                error,
            )
            return False

        self._installed = True

        return True

    def remove(
        self,
    ) -> bool:
        if not self._installed:
            return True

        try:
            self.app.removeNativeEventFilter(
                self.native_filter
            )

        except Exception as error:
            print(
                "Global hotkey native filter "
                "remove error:",
                error,
            )
            return False

        self._installed = False

        return True

    def close(
        self,
    ) -> bool:
        return self.remove()
