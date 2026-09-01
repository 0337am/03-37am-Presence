from __future__ import annotations

import json
import os
import re

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SCHEMA_VERSION = 1

PREFERENCES_FILENAME = (
    "quick_access_preferences.json"
)

MAX_PREFERENCES_BYTES = 128 * 1024

MAX_ITEMS = 24
MAX_ITEM_ID_LENGTH = 64
MAX_TITLE_LENGTH = 64
MAX_DETAIL_LENGTH = 160
MAX_TARGET_LENGTH = 64
MAX_ICON_KEY_LENGTH = 32

SUPPORTED_ITEM_KINDS = frozenset(
    {
        "builtin",
        "presence_preset",
        "presence_mode",
        "launcher_card",
        "spotify_playlist",
    }
)

SUPPORTED_PRESENCE_MODE_TARGETS = frozenset(
    {
        "music",
        "sleep",
        "working",
        "disabled",
    }
)

SUPPORTED_BUILTIN_TARGETS = frozenset(
    {
        "afk",
        "custom",
        "presets",
        "settings",
        "presence",
        "library",
        "spotify",
        "about",
        "companion",
    }
)

_SLUG_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9._-]*$"
)

_LAUNCHER_CARD_TARGET_PATTERN = re.compile(
    r"^custom_launcher_[0-9a-f]{32}$"
)

_SPOTIFY_PLAYLIST_ID_MAX_LENGTH = 22


def spotify_playlist_quick_access_target(
    spotify_id,
) -> str:
    if not isinstance(
        spotify_id,
        str,
    ):
        raise TypeError(
            "Spotify playlist ID must be text."
        )

    checked = spotify_id.strip()

    if (
        checked != spotify_id
        or not checked
        or len(checked)
        > _SPOTIFY_PLAYLIST_ID_MAX_LENGTH
        or not checked.isascii()
        or not checked.isalnum()
    ):
        raise ValueError(
            "Spotify playlist ID must contain "
            "only ASCII letters and digits."
        )

    encoded = ["p"]

    for character in checked:
        if (
            "A"
            <= character
            <= "Z"
        ):
            encoded.append(
                "_"
            )
            encoded.append(
                character.lower()
            )
        else:
            encoded.append(
                character
            )

    return "".join(
        encoded
    )


def spotify_playlist_id_from_quick_access_target(
    target,
) -> str:
    if not isinstance(
        target,
        str,
    ):
        raise TypeError(
            "Spotify playlist Quick Access "
            "target must be text."
        )

    checked = target.strip()

    if (
        checked != target
        or checked != checked.casefold()
        or not checked.startswith("p")
    ):
        raise ValueError(
            "Invalid Spotify playlist "
            "Quick Access target."
        )

    payload = checked[1:]

    if not payload:
        raise ValueError(
            "Spotify playlist Quick Access "
            "target is empty."
        )

    decoded = []
    index = 0

    while index < len(
        payload
    ):
        character = payload[
            index
        ]

        if character == "_":
            index += 1

            if index >= len(
                payload
            ):
                raise ValueError(
                    "Invalid Spotify playlist "
                    "Quick Access target."
                )

            character = payload[
                index
            ]

            if not (
                "a"
                <= character
                <= "z"
            ):
                raise ValueError(
                    "Invalid Spotify playlist "
                    "Quick Access target."
                )

            decoded.append(
                character.upper()
            )

        elif (
            "a"
            <= character
            <= "z"
        ) or (
            "0"
            <= character
            <= "9"
        ):
            decoded.append(
                character
            )

        else:
            raise ValueError(
                "Invalid Spotify playlist "
                "Quick Access target."
            )

        index += 1

    spotify_id = "".join(
        decoded
    )

    if (
        not spotify_id
        or len(spotify_id)
        > _SPOTIFY_PLAYLIST_ID_MAX_LENGTH
        or not spotify_id.isascii()
        or not spotify_id.isalnum()
        or (
            spotify_playlist_quick_access_target(
                spotify_id
            )
            != checked
        )
    ):
        raise ValueError(
            "Invalid Spotify playlist "
            "Quick Access target."
        )

    return spotify_id


def _clean_text(
    value,
    *,
    field_name: str,
    maximum_length: int,
    allow_empty: bool = False,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be text."
        )

    cleaned = value.strip()

    if not allow_empty and not cleaned:
        raise ValueError(
            f"{field_name} must not be empty."
        )

    if len(cleaned) > maximum_length:
        raise ValueError(
            f"{field_name} is too long."
        )

    return cleaned


def _clean_slug(
    value,
    *,
    field_name: str,
    maximum_length: int,
) -> str:
    cleaned = _clean_text(
        value,
        field_name=field_name,
        maximum_length=maximum_length,
    ).casefold()

    if not _SLUG_PATTERN.fullmatch(
        cleaned
    ):
        raise ValueError(
            f"{field_name} contains unsupported characters."
        )

    return cleaned


@dataclass(frozen=True)
class QuickAccessItem:
    item_id: str
    kind: str
    target: str
    title: str
    detail: str
    icon_key: str
    visible: bool = True

    def __post_init__(self) -> None:
        item_id = _clean_slug(
            self.item_id,
            field_name="Quick Access item ID",
            maximum_length=MAX_ITEM_ID_LENGTH,
        )

        kind = _clean_slug(
            self.kind,
            field_name="Quick Access item kind",
            maximum_length=32,
        )

        target = _clean_slug(
            self.target,
            field_name="Quick Access target",
            maximum_length=MAX_TARGET_LENGTH,
        )

        title = _clean_text(
            self.title,
            field_name="Quick Access title",
            maximum_length=MAX_TITLE_LENGTH,
        )

        detail = _clean_text(
            self.detail,
            field_name="Quick Access detail",
            maximum_length=MAX_DETAIL_LENGTH,
            allow_empty=True,
        )

        icon_key = _clean_slug(
            self.icon_key,
            field_name="Quick Access icon key",
            maximum_length=MAX_ICON_KEY_LENGTH,
        )

        if kind not in SUPPORTED_ITEM_KINDS:
            raise ValueError(
                "Unsupported Quick Access item kind: "
                f"{kind}"
            )

        if kind == "builtin":
            if target not in SUPPORTED_BUILTIN_TARGETS:
                raise ValueError(
                    "Unsupported built-in Quick Access target: "
                    f"{target}"
                )

        if kind == "presence_preset":
            expected_item_id = (
                "presence_preset."
                + target
            )

            if item_id != expected_item_id:
                raise ValueError(
                    "Presence preset Quick Access item_id "
                    "must match its target."
                )

            if icon_key != "presets":
                raise ValueError(
                    "Presence preset Quick Access items "
                    "must use the presets icon."
                )


        if kind == "presence_mode":
            if target not in SUPPORTED_PRESENCE_MODE_TARGETS:
                raise ValueError(
                    "Unsupported Presence mode Quick Access target: "
                    f"{target}"
                )

            expected_item_id = (
                "presence_mode."
                + target
            )

            if item_id != expected_item_id:
                raise ValueError(
                    "Presence mode Quick Access item_id "
                    "must match its target."
                )

            if icon_key != "presets":
                raise ValueError(
                    "Presence mode Quick Access items "
                    "must use the presets icon."
                )

        if kind == "launcher_card":
            if not _LAUNCHER_CARD_TARGET_PATTERN.fullmatch(
                target
            ):
                raise ValueError(
                    "Launcher Quick Access target must "
                    "be a stable Launcher card ID."
                )

            expected_item_id = (
                "launcher_card."
                + target
            )

            if item_id != expected_item_id:
                raise ValueError(
                    "Launcher Quick Access item_id "
                    "must match its target."
                )

            if icon_key != "launcher":
                raise ValueError(
                    "Launcher Quick Access items "
                    "must use the launcher icon."
                )

        if kind == "spotify_playlist":
            try:
                spotify_id = (
                    spotify_playlist_id_from_quick_access_target(
                        target
                    )
                )
            except (
                TypeError,
                ValueError,
            ) as error:
                raise ValueError(
                    "Invalid Spotify playlist "
                    "Quick Access target."
                ) from error

            expected_target = (
                spotify_playlist_quick_access_target(
                    spotify_id
                )
            )

            expected_item_id = (
                "spotify_playlist."
                + expected_target
            )

            if item_id != expected_item_id:
                raise ValueError(
                    "Spotify playlist Quick Access "
                    "item ID must match its target."
                )

            if icon_key != "spotify":
                raise ValueError(
                    "Spotify playlist Quick Access "
                    "items must use the Spotify icon."
                )

        if type(self.visible) is not bool:
            raise TypeError(
                "Quick Access visibility must be a boolean."
            )

        object.__setattr__(
            self,
            "item_id",
            item_id,
        )

        object.__setattr__(
            self,
            "kind",
            kind,
        )

        object.__setattr__(
            self,
            "target",
            target,
        )

        object.__setattr__(
            self,
            "title",
            title,
        )

        object.__setattr__(
            self,
            "detail",
            detail,
        )

        object.__setattr__(
            self,
            "icon_key",
            icon_key,
        )


DEFAULT_QUICK_ACCESS_ITEMS = (
    QuickAccessItem(
        item_id="builtin.afk",
        kind="builtin",
        target="afk",
        title="AFK",
        detail="Set AFK presence",
        icon_key="afk",
    ),
    QuickAccessItem(
        item_id="builtin.custom",
        kind="builtin",
        target="custom",
        title="Custom",
        detail="Create a presence",
        icon_key="custom",
    ),
    QuickAccessItem(
        item_id="builtin.presets",
        kind="builtin",
        target="presets",
        title="Presets",
        detail="Manage presence modes",
        icon_key="presets",
    ),
    QuickAccessItem(
        item_id="builtin.settings",
        kind="builtin",
        target="settings",
        title="Settings",
        detail="Configure application",
        icon_key="settings",
    ),
)


@dataclass(frozen=True)
class QuickAccessPreferences:
    items: tuple[QuickAccessItem, ...] = (
        DEFAULT_QUICK_ACCESS_ITEMS
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.items,
            tuple,
        ):
            raise TypeError(
                "Quick Access items must be a tuple."
            )

        if len(self.items) > MAX_ITEMS:
            raise ValueError(
                "Too many Quick Access items."
            )

        item_ids = []

        for item in self.items:
            if not isinstance(
                item,
                QuickAccessItem,
            ):
                raise TypeError(
                    "Quick Access preferences contain "
                    "an unsupported item."
                )

            item_ids.append(
                item.item_id
            )

        if len(item_ids) != len(set(item_ids)):
            raise ValueError(
                "Quick Access preferences contain "
                "duplicate item IDs."
            )


def default_quick_access_preferences(
) -> QuickAccessPreferences:
    return QuickAccessPreferences(
        items=DEFAULT_QUICK_ACCESS_ITEMS
    )


def quick_access_item_to_payload(
    item: QuickAccessItem,
) -> dict:
    if not isinstance(
        item,
        QuickAccessItem,
    ):
        raise TypeError(
            "item must be a QuickAccessItem."
        )

    return {
        "item_id": item.item_id,
        "kind": item.kind,
        "target": item.target,
        "title": item.title,
        "detail": item.detail,
        "icon_key": item.icon_key,
        "visible": item.visible,
    }


def quick_access_item_from_payload(
    payload,
) -> QuickAccessItem:
    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "Quick Access item data must be an object."
        )

    expected_fields = {
        "item_id",
        "kind",
        "target",
        "title",
        "detail",
        "icon_key",
        "visible",
    }

    if set(payload) != expected_fields:
        raise ValueError(
            "Quick Access item fields are invalid."
        )

    visible = payload[
        "visible"
    ]

    if type(visible) is not bool:
        raise ValueError(
            "Quick Access item visibility "
            "must be a boolean."
        )

    try:
        return QuickAccessItem(
            item_id=payload[
                "item_id"
            ],
            kind=payload[
                "kind"
            ],
            target=payload[
                "target"
            ],
            title=payload[
                "title"
            ],
            detail=payload[
                "detail"
            ],
            icon_key=payload[
                "icon_key"
            ],
            visible=visible,
        )

    except (TypeError, ValueError) as error:
        raise ValueError(
            "Quick Access item data is invalid."
        ) from error


def quick_access_preferences_to_payload(
    preferences: QuickAccessPreferences,
) -> dict:
    if not isinstance(
        preferences,
        QuickAccessPreferences,
    ):
        raise TypeError(
            "preferences must be "
            "QuickAccessPreferences."
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "items": [
            quick_access_item_to_payload(
                item
            )
            for item in preferences.items
        ],
    }


def quick_access_preferences_from_payload(
    payload,
) -> QuickAccessPreferences:
    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "Quick Access preferences "
            "must contain an object."
        )

    expected_fields = {
        "schema_version",
        "items",
    }

    if set(payload) != expected_fields:
        raise ValueError(
            "Quick Access preference fields are invalid."
        )

    schema_version = payload[
        "schema_version"
    ]

    if type(schema_version) is not int:
        raise ValueError(
            "Quick Access schema version must be an integer."
        )

    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            "Unsupported Quick Access preference schema."
        )

    items = payload[
        "items"
    ]

    if not isinstance(
        items,
        list,
    ):
        raise ValueError(
            "Quick Access items must be a list."
        )

    try:
        return QuickAccessPreferences(
            items=tuple(
                quick_access_item_from_payload(
                    item
                )
                for item in items
            )
        )

    except (TypeError, ValueError) as error:
        raise ValueError(
            "Quick Access preferences are invalid."
        ) from error


class QuickAccessPreferencesStore:
    def __init__(
        self,
        file_path: Path | str | None = None,
    ):
        if file_path is None:
            self.file_path = self.default_path()
        else:
            self.file_path = Path(
                file_path
            )

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.file_path.exists():
            self.save(
                default_quick_access_preferences()
            )

    @staticmethod
    def default_path() -> Path:
        local_app_data = os.environ.get(
            "LOCALAPPDATA"
        )

        if local_app_data:
            root = (
                Path(local_app_data)
                / "0337am Presence"
            )
        else:
            root = (
                Path.home()
                / ".0337am-presence"
            )

        return (
            root
            / PREFERENCES_FILENAME
        )

    def load(
        self,
    ) -> QuickAccessPreferences:
        if not self.file_path.exists():
            defaults = (
                default_quick_access_preferences()
            )

            self.save(
                defaults
            )

            return defaults

        try:
            size = self.file_path.stat().st_size

            if size > MAX_PREFERENCES_BYTES:
                raise ValueError(
                    "Quick Access preference file "
                    "is too large."
                )

            text = self.file_path.read_text(
                encoding="utf-8"
            )

            payload = json.loads(
                text
            )

            return (
                quick_access_preferences_from_payload(
                    payload
                )
            )

        except (
            UnicodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            self._quarantine_invalid_file()

            defaults = (
                default_quick_access_preferences()
            )

            self.save(
                defaults
            )

            return defaults

    def save(
        self,
        preferences: QuickAccessPreferences,
    ) -> QuickAccessPreferences:
        if not isinstance(
            preferences,
            QuickAccessPreferences,
        ):
            raise TypeError(
                "preferences must be "
                "QuickAccessPreferences."
            )

        payload = (
            quick_access_preferences_to_payload(
                preferences
            )
        )

        text = json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )

        encoded_size = len(
            text.encode(
                "utf-8"
            )
        )

        if encoded_size > MAX_PREFERENCES_BYTES:
            raise ValueError(
                "Quick Access preferences are too large."
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
                file.write(
                    text
                )

                file.write(
                    "\n"
                )

            verification_payload = json.loads(
                temporary_path.read_text(
                    encoding="utf-8"
                )
            )

            quick_access_preferences_from_payload(
                verification_payload
            )

            os.replace(
                temporary_path,
                self.file_path,
            )

        finally:
            temporary_path.unlink(
                missing_ok=True
            )

        return preferences

    def reset(
        self,
    ) -> QuickAccessPreferences:
        defaults = (
            default_quick_access_preferences()
        )

        return self.save(
            defaults
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
                self.file_path.name
                + ".invalid_"
                + timestamp
            )
        )

        suffix = 1

        while quarantine_path.exists():
            quarantine_path = (
                self.file_path.with_name(
                    self.file_path.name
                    + ".invalid_"
                    + timestamp
                    + f"_{suffix}"
                )
            )

            suffix += 1

        os.replace(
            self.file_path,
            quarantine_path,
        )

        return quarantine_path
