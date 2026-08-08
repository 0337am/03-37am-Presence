from __future__ import annotations

import ctypes
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

VALID_MODIFIER_MASK = (
    MOD_ALT
    | MOD_CONTROL
    | MOD_SHIFT
    | MOD_WIN
)

MIN_VIRTUAL_KEY = 0x01
MAX_VIRTUAL_KEY = 0xFE

MIN_HOTKEY_ID = 1
MAX_HOTKEY_ID = 0xBFFF


HotkeyCallback = Callable[[], None]


class HotkeyApi(Protocol):
    def register_hotkey(
        self,
        hotkey_id: int,
        modifiers: int,
        virtual_key: int,
    ) -> bool:
        ...

    def unregister_hotkey(
        self,
        hotkey_id: int,
    ) -> bool:
        ...


class WindowsHotkeyApi:
    """
    Thin wrapper around the Windows RegisterHotKey API.

    Hotkeys are registered against the current thread by passing a
    NULL window handle. WM_HOTKEY dispatch is connected separately by
    the Qt integration layer.
    """

    def __init__(
        self,
        user32=None,
    ):
        self._user32 = (
            user32
            if user32 is not None
            else ctypes.windll.user32
        )

    def register_hotkey(
        self,
        hotkey_id: int,
        modifiers: int,
        virtual_key: int,
    ) -> bool:
        result = self._user32.RegisterHotKey(
            None,
            int(hotkey_id),
            int(modifiers),
            int(virtual_key),
        )

        return bool(result)

    def unregister_hotkey(
        self,
        hotkey_id: int,
    ) -> bool:
        result = self._user32.UnregisterHotKey(
            None,
            int(hotkey_id),
        )

        return bool(result)


@dataclass(
    frozen=True,
    slots=True,
)
class HotkeyBinding:
    modifiers: int
    virtual_key: int

    def __post_init__(
        self,
    ):
        modifiers = int(
            self.modifiers
        )

        virtual_key = int(
            self.virtual_key
        )

        if modifiers < 0:
            raise ValueError(
                "Hotkey modifiers cannot be negative."
            )

        unsupported = (
            modifiers
            & ~VALID_MODIFIER_MASK
        )

        if unsupported:
            raise ValueError(
                "Hotkey modifiers contain unsupported flags."
            )

        if not (
            MIN_VIRTUAL_KEY
            <= virtual_key
            <= MAX_VIRTUAL_KEY
        ):
            raise ValueError(
                "Virtual key is outside the supported range."
            )

        object.__setattr__(
            self,
            "modifiers",
            modifiers,
        )

        object.__setattr__(
            self,
            "virtual_key",
            virtual_key,
        )

    @property
    def windows_modifiers(
        self,
    ) -> int:
        return (
            self.modifiers
            | MOD_NOREPEAT
        )


@dataclass(
    frozen=True,
    slots=True,
)
class HotkeyRegistration:
    action: str
    hotkey_id: int
    binding: HotkeyBinding


class GlobalHotkeyRegistry:
    """
    Owns Windows global-hotkey registrations.

    This class deliberately does not depend on Qt. A later integration
    layer will forward WM_HOTKEY IDs into dispatch().
    """

    def __init__(
        self,
        api: HotkeyApi | None = None,
    ):
        self._api = (
            api
            if api is not None
            else WindowsHotkeyApi()
        )

        self._registrations_by_action: dict[
            str,
            HotkeyRegistration,
        ] = {}

        self._registrations_by_id: dict[
            int,
            HotkeyRegistration,
        ] = {}

        self._callbacks_by_id: dict[
            int,
            HotkeyCallback,
        ] = {}

        self._binding_to_action: dict[
            HotkeyBinding,
            str,
        ] = {}

        self._next_hotkey_id = (
            MIN_HOTKEY_ID
        )

    @property
    def actions(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            self._registrations_by_action
        )

    def registration_for(
        self,
        action: str,
    ) -> HotkeyRegistration | None:
        normalized = self._normalize_action(
            action
        )

        return (
            self._registrations_by_action
            .get(
                normalized
            )
        )

    def action_for_binding(
        self,
        binding: HotkeyBinding,
    ) -> str | None:
        return self._binding_to_action.get(
            binding
        )

    def register(
        self,
        action: str,
        binding: HotkeyBinding,
        callback: HotkeyCallback,
    ) -> HotkeyRegistration | None:
        normalized = self._normalize_action(
            action
        )

        if not callable(callback):
            raise TypeError(
                "Hotkey callback must be callable."
            )

        if (
            normalized
            in self._registrations_by_action
        ):
            return None

        if binding in self._binding_to_action:
            return None

        hotkey_id = self._allocate_id()

        if hotkey_id is None:
            return None

        registered = (
            self._api.register_hotkey(
                hotkey_id,
                binding.windows_modifiers,
                binding.virtual_key,
            )
        )

        if not registered:
            return None

        registration = HotkeyRegistration(
            action=normalized,
            hotkey_id=hotkey_id,
            binding=binding,
        )

        self._registrations_by_action[
            normalized
        ] = registration

        self._registrations_by_id[
            hotkey_id
        ] = registration

        self._callbacks_by_id[
            hotkey_id
        ] = callback

        self._binding_to_action[
            binding
        ] = normalized

        return registration

    def unregister(
        self,
        action: str,
    ) -> bool:
        normalized = self._normalize_action(
            action
        )

        registration = (
            self._registrations_by_action
            .get(
                normalized
            )
        )

        if registration is None:
            return False

        unregistered = (
            self._api.unregister_hotkey(
                registration.hotkey_id
            )
        )

        if not unregistered:
            return False

        self._remove_registration(
            registration
        )

        return True

    def unregister_all(
        self,
    ) -> bool:
        success = True

        for registration in list(
            self._registrations_by_action.values()
        ):
            unregistered = (
                self._api.unregister_hotkey(
                    registration.hotkey_id
                )
            )

            if unregistered:
                self._remove_registration(
                    registration
                )
            else:
                success = False

        return success

    def dispatch(
        self,
        hotkey_id: int,
    ) -> bool:
        try:
            normalized_id = int(
                hotkey_id
            )
        except (
            TypeError,
            ValueError,
        ):
            return False

        callback = (
            self._callbacks_by_id
            .get(
                normalized_id
            )
        )

        if callback is None:
            return False

        try:
            callback()

        except Exception as error:
            print(
                "Global hotkey callback error:",
                error,
            )
            return False

        return True

    def close(
        self,
    ) -> bool:
        return self.unregister_all()

    def _remove_registration(
        self,
        registration: HotkeyRegistration,
    ) -> None:
        self._registrations_by_action.pop(
            registration.action,
            None,
        )

        self._registrations_by_id.pop(
            registration.hotkey_id,
            None,
        )

        self._callbacks_by_id.pop(
            registration.hotkey_id,
            None,
        )

        self._binding_to_action.pop(
            registration.binding,
            None,
        )

    def _allocate_id(
        self,
    ) -> int | None:
        if len(
            self._registrations_by_id
        ) >= MAX_HOTKEY_ID:
            return None

        start = self._next_hotkey_id

        while True:
            hotkey_id = (
                self._next_hotkey_id
            )

            self._next_hotkey_id += 1

            if (
                self._next_hotkey_id
                > MAX_HOTKEY_ID
            ):
                self._next_hotkey_id = (
                    MIN_HOTKEY_ID
                )

            if (
                hotkey_id
                not in self._registrations_by_id
            ):
                return hotkey_id

            if (
                self._next_hotkey_id
                == start
            ):
                return None

    def _normalize_action(
        self,
        action: str,
    ) -> str:
        normalized = str(
            action
        ).strip()

        if not normalized:
            raise ValueError(
                "Hotkey action cannot be empty."
            )

        return normalized
