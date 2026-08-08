from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.system.global_hotkeys import (
    HotkeyBinding,
)
from src.system.media_hotkeys import (
    DEFAULT_SEEK_SECONDS,
    SUPPORTED_MEDIA_HOTKEY_ACTIONS,
)


SCHEMA_VERSION = 1

FILE_NAME = (
    "media_hotkey_preferences.json"
)

_UNSET = object()


def _validated_seek_seconds(
    value,
) -> float:
    try:
        seconds = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        raise ValueError(
            "Seek amount must be a number."
        )

    if (
        not math.isfinite(
            seconds
        )
        or seconds <= 0
    ):
        raise ValueError(
            "Seek amount must be a positive "
            "finite number."
        )

    return seconds


def _validated_bindings(
    bindings,
) -> dict[
    str,
    HotkeyBinding,
]:
    if not isinstance(
        bindings,
        dict,
    ):
        raise TypeError(
            "Media hotkey bindings must be a dictionary."
        )

    normalized: dict[
        str,
        HotkeyBinding,
    ] = {}

    seen_bindings: set[
        HotkeyBinding
    ] = set()

    for action, binding in bindings.items():
        normalized_action = str(
            action
        ).strip()

        if (
            normalized_action
            not in SUPPORTED_MEDIA_HOTKEY_ACTIONS
        ):
            raise ValueError(
                "Unsupported media hotkey action: "
                f"{normalized_action}"
            )

        if not isinstance(
            binding,
            HotkeyBinding,
        ):
            raise TypeError(
                "Media hotkey bindings must contain "
                "HotkeyBinding values."
            )

        if binding in seen_bindings:
            raise ValueError(
                "The same global shortcut cannot be "
                "assigned to multiple media actions."
            )

        seen_bindings.add(
            binding
        )

        normalized[
            normalized_action
        ] = binding

    return normalized


@dataclass(
    frozen=True,
    slots=True,
)
class MediaHotkeyPreferences:
    enabled: bool = False

    seek_seconds: float = (
        DEFAULT_SEEK_SECONDS
    )

    bindings: dict[
        str,
        HotkeyBinding,
    ] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ):
        if not isinstance(
            self.enabled,
            bool,
        ):
            raise TypeError(
                "Media hotkey enabled state must "
                "be a boolean."
            )

        object.__setattr__(
            self,
            "seek_seconds",
            _validated_seek_seconds(
                self.seek_seconds
            ),
        )

        object.__setattr__(
            self,
            "bindings",
            _validated_bindings(
                dict(
                    self.bindings
                )
            ),
        )

    def controller_bindings(
        self,
    ) -> dict[
        str,
        HotkeyBinding,
    ]:
        if not self.enabled:
            return {}

        return dict(
            self.bindings
        )


def media_hotkey_preferences_to_payload(
    preferences: MediaHotkeyPreferences,
) -> dict[
    str,
    Any,
]:
    if not isinstance(
        preferences,
        MediaHotkeyPreferences,
    ):
        raise TypeError(
            "preferences must be a "
            "MediaHotkeyPreferences instance."
        )

    safe_preferences = (
        MediaHotkeyPreferences(
            enabled=(
                preferences.enabled
            ),
            seek_seconds=(
                preferences.seek_seconds
            ),
            bindings=dict(
                preferences.bindings
            ),
        )
    )

    bindings = {}

    for action in (
        SUPPORTED_MEDIA_HOTKEY_ACTIONS
    ):
        binding = (
            safe_preferences.bindings.get(
                action
            )
        )

        if binding is None:
            continue

        bindings[
            action
        ] = {
            "modifiers": (
                binding.modifiers
            ),
            "virtual_key": (
                binding.virtual_key
            ),
        }

    return {
        "schema_version": (
            SCHEMA_VERSION
        ),
        "enabled": (
            safe_preferences.enabled
        ),
        "seek_seconds": (
            safe_preferences.seek_seconds
        ),
        "bindings": bindings,
    }


def media_hotkey_preferences_from_payload(
    payload,
) -> MediaHotkeyPreferences:
    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "Media hotkey preference payload "
            "must be an object."
        )

    schema_version = (
        payload.get(
            "schema_version"
        )
    )

    if (
        type(
            schema_version
        )
        is not int
        or schema_version
        != SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported media hotkey "
            "preference schema."
        )

    enabled = payload.get(
        "enabled"
    )

    if not isinstance(
        enabled,
        bool,
    ):
        raise ValueError(
            "Media hotkey enabled state "
            "must be a boolean."
        )

    seek_seconds = (
        _validated_seek_seconds(
            payload.get(
                "seek_seconds"
            )
        )
    )

    raw_bindings = payload.get(
        "bindings"
    )

    if not isinstance(
        raw_bindings,
        dict,
    ):
        raise ValueError(
            "Media hotkey bindings must "
            "be an object."
        )

    bindings: dict[
        str,
        HotkeyBinding,
    ] = {}

    for (
        action,
        raw_binding,
    ) in raw_bindings.items():
        normalized_action = str(
            action
        ).strip()

        if (
            normalized_action
            not in SUPPORTED_MEDIA_HOTKEY_ACTIONS
        ):
            raise ValueError(
                "Unsupported media hotkey action: "
                f"{normalized_action}"
            )

        if not isinstance(
            raw_binding,
            dict,
        ):
            raise ValueError(
                "Each media hotkey binding "
                "must be an object."
            )

        modifiers = raw_binding.get(
            "modifiers"
        )

        virtual_key = (
            raw_binding.get(
                "virtual_key"
            )
        )

        if type(
            modifiers
        ) is not int:
            raise ValueError(
                "Hotkey modifiers must "
                "be an integer."
            )

        if type(
            virtual_key
        ) is not int:
            raise ValueError(
                "Hotkey virtual key must "
                "be an integer."
            )

        bindings[
            normalized_action
        ] = HotkeyBinding(
            modifiers=modifiers,
            virtual_key=virtual_key,
        )

    return MediaHotkeyPreferences(
        enabled=enabled,
        seek_seconds=seek_seconds,
        bindings=bindings,
    )


class MediaHotkeyPreferencesStore:
    def __init__(
        self,
    ):
        self.file_path = (
            self._get_file_path()
        )

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.file_path.exists():
            self.save(
                MediaHotkeyPreferences()
            )

    def _get_file_path(
        self,
    ) -> Path:
        local_app_data = os.getenv(
            "LOCALAPPDATA",
            "",
        ).strip()

        if local_app_data:
            data_directory = (
                Path(
                    local_app_data
                )
                / "0337am Presence"
            )

        else:
            data_directory = (
                Path.home()
                / ".0337am-presence"
            )

        return (
            data_directory
            / FILE_NAME
        )

    def load(
        self,
    ) -> MediaHotkeyPreferences:
        try:
            with self.file_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(
                    file
                )

            return self._preferences_from_payload(
                data
            )

        except Exception as error:
            print(
                "Media hotkey preferences "
                "load error:",
                error,
            )

            self._quarantine_invalid_file()

            preferences = (
                MediaHotkeyPreferences()
            )

            self.save(
                preferences
            )

            return preferences

    def save(
        self,
        preferences: MediaHotkeyPreferences,
    ) -> None:
        if not isinstance(
            preferences,
            MediaHotkeyPreferences,
        ):
            raise TypeError(
                "preferences must be a "
                "MediaHotkeyPreferences instance."
            )

        safe_preferences = (
            MediaHotkeyPreferences(
                enabled=(
                    preferences.enabled
                ),
                seek_seconds=(
                    preferences.seek_seconds
                ),
                bindings=dict(
                    preferences.bindings
                ),
            )
        )

        payload = self._payload_from_preferences(
            safe_preferences
        )

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = (
            self.file_path.with_name(
                self.file_path.name
                + ".tmp"
            )
        )

        try:
            with temporary_path.open(
                "w",
                encoding="utf-8",
                newline="\n",
            ) as file:
                json.dump(
                    payload,
                    file,
                    indent=2,
                    sort_keys=True,
                )

                file.write(
                    "\n"
                )

                file.flush()

                os.fsync(
                    file.fileno()
                )

            with temporary_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                verification_payload = (
                    json.load(
                        file
                    )
                )

            self._preferences_from_payload(
                verification_payload
            )

            temporary_path.replace(
                self.file_path
            )

        except Exception:
            try:
                temporary_path.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

            raise

    def update(
        self,
        *,
        enabled=_UNSET,
        seek_seconds=_UNSET,
        bindings=_UNSET,
    ) -> MediaHotkeyPreferences:
        current = self.load()

        updated = (
            MediaHotkeyPreferences(
                enabled=(
                    current.enabled
                    if enabled is _UNSET
                    else enabled
                ),
                seek_seconds=(
                    current.seek_seconds
                    if seek_seconds is _UNSET
                    else seek_seconds
                ),
                bindings=(
                    current.bindings
                    if bindings is _UNSET
                    else bindings
                ),
            )
        )

        self.save(
            updated
        )

        return updated

    def set_binding(
        self,
        action: str,
        binding: HotkeyBinding,
    ) -> MediaHotkeyPreferences:
        current = self.load()

        bindings = dict(
            current.bindings
        )

        normalized_action = str(
            action
        ).strip()

        if (
            normalized_action
            not in SUPPORTED_MEDIA_HOTKEY_ACTIONS
        ):
            raise ValueError(
                "Unsupported media hotkey action: "
                f"{normalized_action}"
            )

        if not isinstance(
            binding,
            HotkeyBinding,
        ):
            raise TypeError(
                "binding must be a HotkeyBinding."
            )

        for (
            existing_action,
            existing_binding,
        ) in bindings.items():
            if (
                existing_action
                != normalized_action
                and existing_binding
                == binding
            ):
                raise ValueError(
                    "The shortcut is already assigned "
                    "to another media action."
                )

        bindings[
            normalized_action
        ] = binding

        updated = (
            MediaHotkeyPreferences(
                enabled=current.enabled,
                seek_seconds=(
                    current.seek_seconds
                ),
                bindings=bindings,
            )
        )

        self.save(
            updated
        )

        return updated

    def clear_binding(
        self,
        action: str,
    ) -> MediaHotkeyPreferences:
        current = self.load()

        bindings = dict(
            current.bindings
        )

        normalized_action = str(
            action
        ).strip()

        if (
            normalized_action
            not in SUPPORTED_MEDIA_HOTKEY_ACTIONS
        ):
            raise ValueError(
                "Unsupported media hotkey action: "
                f"{normalized_action}"
            )

        bindings.pop(
            normalized_action,
            None,
        )

        updated = (
            MediaHotkeyPreferences(
                enabled=current.enabled,
                seek_seconds=(
                    current.seek_seconds
                ),
                bindings=bindings,
            )
        )

        self.save(
            updated
        )

        return updated

    def clear_bindings(
        self,
    ) -> MediaHotkeyPreferences:
        current = self.load()

        updated = (
            MediaHotkeyPreferences(
                enabled=current.enabled,
                seek_seconds=(
                    current.seek_seconds
                ),
                bindings={},
            )
        )

        self.save(
            updated
        )

        return updated

    def _payload_from_preferences(
        self,
        preferences: MediaHotkeyPreferences,
    ) -> dict[
        str,
        Any,
    ]:
        return media_hotkey_preferences_to_payload(
            preferences
        )

    def _preferences_from_payload(
        self,
        payload,
    ) -> MediaHotkeyPreferences:
        return media_hotkey_preferences_from_payload(
            payload
        )

    def _quarantine_invalid_file(
        self,
    ) -> Path | None:
        if not self.file_path.exists():
            return None

        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )

        quarantine_path = (
            self.file_path.with_name(
                self.file_path.stem
                + ".invalid-"
                + timestamp
                + self.file_path.suffix
            )
        )

        counter = 1

        while quarantine_path.exists():
            quarantine_path = (
                self.file_path.with_name(
                    self.file_path.stem
                    + ".invalid-"
                    + timestamp
                    + "-"
                    + str(
                        counter
                    )
                    + self.file_path.suffix
                )
            )

            counter += 1

        try:
            self.file_path.replace(
                quarantine_path
            )

            print(
                "Invalid media hotkey "
                "preferences quarantined:",
                quarantine_path,
            )

            return quarantine_path

        except Exception as error:
            print(
                "Media hotkey preferences "
                "quarantine error:",
                error,
            )

            return None
