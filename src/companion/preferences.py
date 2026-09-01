from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = 1
PREFERENCES_FILENAME = "companion_preferences.json"

MAX_PREFERENCES_FILE_BYTES = 64 * 1024
MAX_ASSET_PATH_CHARS = 4096
MAX_SCREEN_NAME_CHARS = 512
MAX_POSITION_ABS = 1_000_000

MIN_SCALE_PERCENT = 25
MAX_SCALE_PERCENT = 400

MIN_OPACITY = 0.10
MAX_OPACITY = 1.0

MIN_ANIMATION_SPEED_PERCENT = 25
MAX_ANIMATION_SPEED_PERCENT = 400

SUPPORTED_ASSET_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
    }
)


@dataclass(frozen=True, slots=True)
class CompanionPreferences:
    enabled: bool = False
    asset_path: str = ""

    scale_percent: int = 100
    opacity: float = 1.0

    always_on_top: bool = True
    click_through: bool = True

    remember_position: bool = True
    position_x: int | None = None
    position_y: int | None = None
    screen_name: str = ""

    hide_in_fullscreen: bool = False
    animation_speed_percent: int = 100


def default_companion_preferences() -> CompanionPreferences:
    return CompanionPreferences()


def default_companion_preferences_path() -> Path:
    local_app_data = os.environ.get(
        "LOCALAPPDATA",
        "",
    )

    if local_app_data:
        base = Path(local_app_data)
    else:
        base = (
            Path.home()
            / "AppData"
            / "Local"
        )

    return (
        base
        / "0337am Presence"
        / PREFERENCES_FILENAME
    )


def _require_bool(
    value: Any,
    *,
    field_name: str,
) -> bool:
    if not isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a boolean."
        )

    return value


def _require_int(
    value: Any,
    *,
    field_name: str,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
    ):
        raise ValueError(
            f"{field_name} must be an integer."
        )

    if not minimum <= value <= maximum:
        raise ValueError(
            f"{field_name} must be between "
            f"{minimum} and {maximum}."
        )

    return value


def _require_float(
    value: Any,
    *,
    field_name: str,
    minimum: float,
    maximum: float,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise ValueError(
            f"{field_name} must be numeric."
        )

    result = float(value)

    if not minimum <= result <= maximum:
        raise ValueError(
            f"{field_name} must be between "
            f"{minimum} and {maximum}."
        )

    return result


def _require_string(
    value: Any,
    *,
    field_name: str,
    maximum_chars: int,
) -> str:
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string."
        )

    if len(value) > maximum_chars:
        raise ValueError(
            f"{field_name} is too long."
        )

    if "\x00" in value:
        raise ValueError(
            f"{field_name} contains a null character."
        )

    return value


def _require_asset_path(value: Any) -> str:
    result = _require_string(
        value,
        field_name="asset_path",
        maximum_chars=MAX_ASSET_PATH_CHARS,
    )

    if not result:
        return ""

    suffix = Path(result).suffix.lower()

    if suffix not in SUPPORTED_ASSET_SUFFIXES:
        supported = ", ".join(
            sorted(SUPPORTED_ASSET_SUFFIXES)
        )

        raise ValueError(
            "asset_path must use one of: "
            f"{supported}."
        )

    return result


def _require_position(
    value: Any,
    *,
    field_name: str,
) -> int | None:
    if value is None:
        return None

    return _require_int(
        value,
        field_name=field_name,
        minimum=-MAX_POSITION_ABS,
        maximum=MAX_POSITION_ABS,
    )


_PAYLOAD_KEYS = frozenset(
    {
        "schema_version",
        "enabled",
        "asset_path",
        "scale_percent",
        "opacity",
        "always_on_top",
        "click_through",
        "remember_position",
        "position_x",
        "position_y",
        "screen_name",
        "hide_in_fullscreen",
        "animation_speed_percent",
    }
)


def companion_preferences_to_payload(
    preferences: CompanionPreferences,
) -> dict[str, Any]:
    if not isinstance(preferences, CompanionPreferences):
        raise TypeError(
            "preferences must be a "
            "CompanionPreferences instance."
        )

    position_x = _require_position(
        preferences.position_x,
        field_name="position_x",
    )

    position_y = _require_position(
        preferences.position_y,
        field_name="position_y",
    )

    if (position_x is None) != (position_y is None):
        raise ValueError(
            "position_x and position_y must both "
            "be set or both be null."
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "enabled": _require_bool(
            preferences.enabled,
            field_name="enabled",
        ),
        "asset_path": _require_asset_path(
            preferences.asset_path
        ),
        "scale_percent": _require_int(
            preferences.scale_percent,
            field_name="scale_percent",
            minimum=MIN_SCALE_PERCENT,
            maximum=MAX_SCALE_PERCENT,
        ),
        "opacity": _require_float(
            preferences.opacity,
            field_name="opacity",
            minimum=MIN_OPACITY,
            maximum=MAX_OPACITY,
        ),
        "always_on_top": _require_bool(
            preferences.always_on_top,
            field_name="always_on_top",
        ),
        "click_through": _require_bool(
            preferences.click_through,
            field_name="click_through",
        ),
        "remember_position": _require_bool(
            preferences.remember_position,
            field_name="remember_position",
        ),
        "position_x": position_x,
        "position_y": position_y,
        "screen_name": _require_string(
            preferences.screen_name,
            field_name="screen_name",
            maximum_chars=MAX_SCREEN_NAME_CHARS,
        ),
        "hide_in_fullscreen": _require_bool(
            preferences.hide_in_fullscreen,
            field_name="hide_in_fullscreen",
        ),
        "animation_speed_percent": _require_int(
            preferences.animation_speed_percent,
            field_name="animation_speed_percent",
            minimum=MIN_ANIMATION_SPEED_PERCENT,
            maximum=MAX_ANIMATION_SPEED_PERCENT,
        ),
    }


def companion_preferences_from_payload(
    payload: Mapping[str, Any],
) -> CompanionPreferences:
    if not isinstance(payload, Mapping):
        raise ValueError(
            "Companion preferences must be an object."
        )

    if frozenset(payload.keys()) != _PAYLOAD_KEYS:
        raise ValueError(
            "Companion preference fields are invalid."
        )

    schema_version = payload["schema_version"]

    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
    ):
        raise ValueError(
            "Companion schema version must be an integer."
        )

    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            "Unsupported Companion preference schema."
        )

    candidate = CompanionPreferences(
        enabled=payload["enabled"],
        asset_path=payload["asset_path"],
        scale_percent=payload["scale_percent"],
        opacity=payload["opacity"],
        always_on_top=payload["always_on_top"],
        click_through=payload["click_through"],
        remember_position=payload["remember_position"],
        position_x=payload["position_x"],
        position_y=payload["position_y"],
        screen_name=payload["screen_name"],
        hide_in_fullscreen=payload["hide_in_fullscreen"],
        animation_speed_percent=payload[
            "animation_speed_percent"
        ],
    )

    normalized = companion_preferences_to_payload(
        candidate
    )

    return CompanionPreferences(
        enabled=normalized["enabled"],
        asset_path=normalized["asset_path"],
        scale_percent=normalized["scale_percent"],
        opacity=normalized["opacity"],
        always_on_top=normalized["always_on_top"],
        click_through=normalized["click_through"],
        remember_position=normalized["remember_position"],
        position_x=normalized["position_x"],
        position_y=normalized["position_y"],
        screen_name=normalized["screen_name"],
        hide_in_fullscreen=normalized["hide_in_fullscreen"],
        animation_speed_percent=normalized[
            "animation_speed_percent"
        ],
    )


class CompanionPreferencesStore:
    def __init__(
        self,
        path: Path | str | None = None,
    ) -> None:
        self.path = (
            Path(path)
            if path is not None
            else default_companion_preferences_path()
        )

    def load(self) -> CompanionPreferences:
        if not self.path.exists():
            return default_companion_preferences()

        try:
            if (
                self.path.stat().st_size
                > MAX_PREFERENCES_FILE_BYTES
            ):
                return default_companion_preferences()

            raw = self.path.read_bytes()

            if len(raw) > MAX_PREFERENCES_FILE_BYTES:
                return default_companion_preferences()

            payload = json.loads(
                raw.decode("utf-8")
            )

            return companion_preferences_from_payload(
                payload
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            return default_companion_preferences()

    def save(
        self,
        preferences: CompanionPreferences,
    ) -> CompanionPreferences:
        payload = companion_preferences_to_payload(
            preferences
        )

        verified = companion_preferences_from_payload(
            payload
        )

        encoded = (
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")

        if len(encoded) > MAX_PREFERENCES_FILE_BYTES:
            raise ValueError(
                "Companion preferences are too large."
            )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self.path.with_name(
            "."
            + self.path.name
            + "."
            + str(os.getpid())
            + "."
            + uuid.uuid4().hex
            + ".tmp"
        )

        try:
            with temporary_path.open("xb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(
                temporary_path,
                self.path,
            )
        finally:
            try:
                temporary_path.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

        return verified

    def update(
        self,
        **changes: Any,
    ) -> CompanionPreferences:
        updated = replace(
            self.load(),
            **changes,
        )

        return self.save(updated)