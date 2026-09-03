from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY_ID,
    is_valid_user_entry_id,
)

from src.discord.presence_modes import (
    APP_DATA_DIRECTORY,
    DEFAULT_PARTY_CURRENT,
    DEFAULT_PARTY_MAXIMUM,
    MODE_DEFAULTS,
    PresenceMode,
    VALID_MODES,
)

from src.discord.presence_link_buttons import (
    PresenceLinkButton,
    PresenceLinkButtonError,
    normalize_presence_buttons,
)


PRESET_STORAGE_KIND = "0337am-presence-presets"
LEGACY_SCHEMA_VERSION = 1
SCHEMA_VERSION = 2
MAX_PRESETS = 60
MAX_PINNED_PRESETS = 8
MAX_NAME_LENGTH = 64
MAX_TEXT_LENGTH = 128

PRESENCE_PRESET_IMAGE_DIRECTORY = (
    APP_DATA_DIRECTORY / "presence_preset_images"
)
PRESENCE_PRESET_STORAGE_PATH = (
    APP_DATA_DIRECTORY / "presence_presets.json"
)

ALLOWED_IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


class PresencePresetError(ValueError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_mode(mode: str) -> str:
    normalized = str(
        mode or "custom"
    ).strip().lower()

    if normalized not in VALID_MODES:
        return "custom"

    return normalized


def normalize_application_entry_id(
    value,
) -> str | None:
    if value is None:
        return None

    entry_id = (
        str(
            value
        )
        .replace("\x00", "")
        .strip()
    )

    if not entry_id:
        return None

    if (
        entry_id
        == BUILTIN_APPLICATION_ENTRY_ID
    ):
        return entry_id

    if is_valid_user_entry_id(
        entry_id
    ):
        return entry_id

    raise PresencePresetError(
        "Preset Discord application reference is invalid."
    )


def clean_text(value: str, *, limit: int) -> str:
    text = str(value or "").replace("\x00", "").strip()

    if len(text) > limit:
        text = text[:limit].rstrip()

    return text


def clean_name(value: str) -> str:
    name = clean_text(
        value,
        limit=MAX_NAME_LENGTH,
    )

    if not name:
        return "Untitled Preset"

    return name


def make_preset_id() -> str:
    return f"presence_preset_{uuid.uuid4().hex[:16]}"


def is_valid_preset_id(value: str) -> bool:
    text = str(value or "")

    return (
        text.startswith("presence_preset_")
        and len(text) == len("presence_preset_") + 16
        and all(
            character in "0123456789abcdef"
            for character in text.removeprefix(
                "presence_preset_"
            )
        )
    )


def validate_image_path(value: str) -> str:
    path_text = str(value or "").replace("\x00", "").strip()

    if not path_text:
        return ""

    path = Path(path_text)
    suffix = path.suffix.lower()

    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        return ""

    return path_text


def display_title_for_mode(mode: str) -> str:
    normalized = normalize_mode(mode)
    defaults = MODE_DEFAULTS.get(
        normalized,
        {},
    )

    return str(
        defaults.get("title", "")
    )


def display_message_for_mode(mode: str) -> str:
    normalized = normalize_mode(mode)
    defaults = MODE_DEFAULTS.get(
        normalized,
        {},
    )

    return str(
        defaults.get("message", "")
    )


@dataclass(frozen=True)
class PresencePreset:
    preset_id: str
    name: str
    mode: str = "custom"
    title: str = ""
    message: str = ""
    image_path: str = ""
    show_elapsed: bool = False
    show_buttons: bool = False
    buttons: tuple[PresenceLinkButton, ...] = ()
    pinned: bool = False
    created_at: str = ""
    updated_at: str = ""
    show_loop_count: bool = False
    show_party: bool = False
    party_current: int = DEFAULT_PARTY_CURRENT
    party_maximum: int = DEFAULT_PARTY_MAXIMUM
    application_entry_id: str | None = None

    def normalized(self) -> "PresencePreset":
        now = utc_now_iso()

        preset_id = str(
            self.preset_id or ""
        ).strip()

        if not is_valid_preset_id(preset_id):
            preset_id = make_preset_id()

        mode = normalize_mode(self.mode)

        if mode == "disabled":
            application_entry_id = None
        else:
            application_entry_id = (
                normalize_application_entry_id(
                    self.application_entry_id
                )
            )

        title = clean_text(
            self.title,
            limit=MAX_TEXT_LENGTH,
        )

        message = clean_text(
            self.message,
            limit=MAX_TEXT_LENGTH,
        )

        if mode in {
            "music",
            "disabled",
        }:
            title = ""
            message = ""
            image_path = ""
            show_elapsed = False

        else:
            image_path = validate_image_path(
                self.image_path,
            )

            show_elapsed = bool(
                self.show_elapsed
            )

        show_loop_count = bool(
            self.show_loop_count
            if mode == "music"
            else False
        )

        party_mode = PresenceMode(
            mode=mode,
            show_party=self.show_party,
            party_current=self.party_current,
            party_maximum=self.party_maximum,
        )

        party_current, party_maximum = (
            party_mode.normalized_party_size()
        )

        show_party = party_mode.party_enabled()

        if mode == "disabled":
            show_buttons = False
            buttons = ()

        else:
            show_buttons = bool(
                self.show_buttons
            )

            try:
                buttons = normalize_presence_buttons(
                    self.buttons
                )

            except PresenceLinkButtonError as error:
                raise PresencePresetError(
                    str(error)
                ) from error

        return replace(
            self,
            preset_id=preset_id,
            name=clean_name(self.name),
            mode=mode,
            title=title,
            message=message,
            image_path=image_path,
            show_elapsed=show_elapsed,
            show_buttons=show_buttons,
            buttons=buttons,
            pinned=bool(self.pinned),
            show_loop_count=show_loop_count,
            show_party=show_party,
            party_current=party_current,
            party_maximum=party_maximum,
            application_entry_id=(
                application_entry_id
            ),
            created_at=str(
                self.created_at or now
            ),
            updated_at=str(
                self.updated_at or now
            ),
        )

    def to_presence_mode(self) -> PresenceMode:
        preset = self.normalized()

        return PresenceMode(
            mode=preset.mode,
            application_entry_id=(
                preset.application_entry_id
            ),
            title=preset.title,
            message=preset.message,
            image_path=preset.image_path,
            show_elapsed=preset.show_elapsed,
            show_buttons=preset.show_buttons,
            buttons=preset.buttons,
            show_loop_count=preset.show_loop_count,
            show_party=preset.show_party,
            party_current=preset.party_current,
            party_maximum=preset.party_maximum,
        )

    def to_dict(self) -> dict:
        preset = self.normalized()

        return {
            "id": preset.preset_id,
            "name": preset.name,
            "mode": preset.mode,
            "title": preset.title,
            "message": preset.message,
            "image_path": preset.image_path,
            "show_elapsed": preset.show_elapsed,
            "show_buttons": preset.show_buttons,
            "show_loop_count": preset.show_loop_count,
            "show_party": preset.show_party,
            "party_current": preset.party_current,
            "party_maximum": preset.party_maximum,
            "application_entry_id": (
                preset.application_entry_id
            ),
            "buttons": [
                button.to_dict()
                for button in preset.buttons
            ],
            "pinned": preset.pinned,
            "created_at": preset.created_at,
            "updated_at": preset.updated_at,
        }


@dataclass(frozen=True)
class PresencePresetStorage:
    presets: tuple[PresencePreset, ...]
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "kind": PRESET_STORAGE_KIND,
            "schema_version": self.schema_version,
            "presets": [
                preset.to_dict()
                for preset in self.presets
            ],
        }


def preset_from_dict(data: dict) -> PresencePreset:
    if not isinstance(data, dict):
        raise PresencePresetError(
            "Preset entry must be an object."
        )

    preset = PresencePreset(
        preset_id=str(
            data.get("id")
            or data.get("preset_id")
            or ""
        ),
        name=str(
            data.get("name")
            or "Untitled Preset"
        ),
        mode=str(
            data.get("mode")
            or "custom"
        ),
        title=str(
            data.get("title")
            or ""
        ),
        message=str(
            data.get("message")
            or ""
        ),
        image_path=str(
            data.get("image_path")
            or ""
        ),
        show_elapsed=bool(
            data.get("show_elapsed", False)
        ),
        show_loop_count=bool(
            data.get(
                "show_loop_count",
                False,
            )
        ),
        show_party=bool(
            data.get(
                "show_party",
                False,
            )
        ),
        party_current=data.get(
            "party_current",
            DEFAULT_PARTY_CURRENT,
        ),
        party_maximum=data.get(
            "party_maximum",
            DEFAULT_PARTY_MAXIMUM,
        ),
        application_entry_id=(
            data.get(
                "application_entry_id"
            )
        ),
        show_buttons=bool(
            data.get("show_buttons", False)
        ),
        buttons=data.get(
            "buttons",
            (),
        ),
        pinned=bool(
            data.get("pinned", False)
        ),
        created_at=str(
            data.get("created_at")
            or ""
        ),
        updated_at=str(
            data.get("updated_at")
            or ""
        ),
    )

    return preset.normalized()


def storage_from_dict(data: dict) -> PresencePresetStorage:
    if not isinstance(data, dict):
        raise PresencePresetError(
            "Preset storage must be an object."
        )

    kind = data.get("kind")

    if kind != PRESET_STORAGE_KIND:
        raise PresencePresetError(
            "Preset storage kind is invalid."
        )

    schema_version = int(
        data.get("schema_version", 0)
    )

    if schema_version not in {
        LEGACY_SCHEMA_VERSION,
        SCHEMA_VERSION,
    }:
        raise PresencePresetError(
            "Preset storage schema is not supported."
        )

    raw_presets = data.get("presets", [])

    if not isinstance(raw_presets, list):
        raise PresencePresetError(
            "Preset list is invalid."
        )

    if len(raw_presets) > MAX_PRESETS:
        raise PresencePresetError(
            "Preset list is too large."
        )

    presets = []
    seen_ids: set[str] = set()

    for raw_preset in raw_presets:
        preset = preset_from_dict(raw_preset)

        if preset.preset_id in seen_ids:
            raise PresencePresetError(
                "Preset IDs must be unique."
            )

        seen_ids.add(preset.preset_id)
        presets.append(preset)

    pinned_count = sum(
        1
        for preset in presets
        if preset.pinned
    )

    if pinned_count > MAX_PINNED_PRESETS:
        presets = _limit_pinned_presets(presets)

    return PresencePresetStorage(
        presets=tuple(presets),
        schema_version=SCHEMA_VERSION,
    )


def _limit_pinned_presets(
    presets: Iterable[PresencePreset],
) -> list[PresencePreset]:
    result = []
    pinned_count = 0

    for preset in presets:
        if preset.pinned:
            pinned_count += 1

            if pinned_count > MAX_PINNED_PRESETS:
                preset = replace(
                    preset,
                    pinned=False,
                )

        result.append(preset)

    return result


def unique_copy_name(
    existing_names: Iterable[str],
    base_name: str,
) -> str:
    existing = {
        str(name).strip().lower()
        for name in existing_names
    }

    candidate = clean_name(
        f"{base_name} Copy"
    )

    if candidate.lower() not in existing:
        return candidate

    for index in range(2, 100):
        candidate = clean_name(
            f"{base_name} Copy {index}"
        )

        if candidate.lower() not in existing:
            return candidate

    return clean_name(
        f"{base_name} Copy {uuid.uuid4().hex[:4]}"
    )


class PresencePresetStore:
    def __init__(
        self,
        storage_path: Path | None = None,
        image_directory: Path | None = None,
    ):
        self.storage_path = Path(
            storage_path or PRESENCE_PRESET_STORAGE_PATH
        )
        self.image_directory = Path(
            image_directory or PRESENCE_PRESET_IMAGE_DIRECTORY
        )

    def load_storage(self) -> PresencePresetStorage:
        if not self.storage_path.exists():
            return PresencePresetStorage(
                presets=(),
            )

        try:
            data = json.loads(
                self.storage_path.read_text(
                    encoding="utf-8"
                )
            )

            return storage_from_dict(data)

        except Exception as error:
            self._quarantine_corrupt_storage(error)
            return PresencePresetStorage(
                presets=(),
            )

    def load(self) -> list[PresencePreset]:
        return list(
            self.load_storage().presets
        )

    def save(
        self,
        presets: Iterable[PresencePreset],
    ) -> PresencePresetStorage:
        normalized = [
            preset.normalized()
            for preset in presets
        ]

        if len(normalized) > MAX_PRESETS:
            raise PresencePresetError(
                "Too many presence presets."
            )

        seen: set[str] = set()

        for preset in normalized:
            if preset.preset_id in seen:
                raise PresencePresetError(
                    "Preset IDs must be unique."
                )

            seen.add(preset.preset_id)

        normalized = _limit_pinned_presets(
            normalized
        )

        storage = PresencePresetStorage(
            presets=tuple(normalized),
        )

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self.storage_path.with_suffix(
            self.storage_path.suffix + ".tmp"
        )

        temporary_path.write_text(
            json.dumps(
                storage.to_dict(),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(
            self.storage_path
        )

        return storage

    def get(
        self,
        preset_id: str,
    ) -> PresencePreset | None:
        for preset in self.load():
            if preset.preset_id == preset_id:
                return preset

        return None

    def create(
        self,
        *,
        name: str,
        presence_mode: PresenceMode,
        pinned: bool = False,
    ) -> PresencePreset:
        now = utc_now_iso()
        preset = PresencePreset(
            preset_id=make_preset_id(),
            name=name,
            mode=presence_mode.mode,
            title=presence_mode.title,
            message=presence_mode.message,
            image_path=presence_mode.image_path,
            show_elapsed=presence_mode.show_elapsed,
            show_buttons=presence_mode.show_buttons,
            buttons=presence_mode.buttons,
            show_loop_count=presence_mode.show_loop_count,
            show_party=presence_mode.show_party,
            party_current=presence_mode.party_current,
            party_maximum=presence_mode.party_maximum,
            application_entry_id=(
                presence_mode
                .normalized_application_entry_id()
            ),
            pinned=pinned,
            created_at=now,
            updated_at=now,
        ).normalized()

        presets = self.load()
        presets.append(preset)
        self.save(presets)

        return preset

    def upsert(
        self,
        preset: PresencePreset,
    ) -> PresencePreset:
        normalized = replace(
            preset.normalized(),
            updated_at=utc_now_iso(),
        ).normalized()

        presets = self.load()
        replaced = False

        for index, existing in enumerate(presets):
            if existing.preset_id == normalized.preset_id:
                presets[index] = normalized
                replaced = True
                break

        if not replaced:
            presets.append(normalized)

        self.save(presets)
        return normalized

    def update_from_mode(
        self,
        preset_id: str,
        *,
        name: str,
        presence_mode: PresenceMode,
        pinned: bool | None = None,
    ) -> PresencePreset:
        existing = self.get(preset_id)

        if existing is None:
            raise PresencePresetError(
                "Presence preset was not found."
            )

        requested_application_entry_id = (
            presence_mode
            .normalized_application_entry_id()
        )

        application_entry_id = (
            existing.application_entry_id
            if requested_application_entry_id
            is None
            else requested_application_entry_id
        )

        updated = replace(
            existing,
            name=name,
            mode=presence_mode.mode,
            title=presence_mode.title,
            message=presence_mode.message,
            image_path=presence_mode.image_path,
            show_elapsed=presence_mode.show_elapsed,
            show_buttons=presence_mode.show_buttons,
            buttons=presence_mode.buttons,
            show_loop_count=presence_mode.show_loop_count,
            show_party=presence_mode.show_party,
            party_current=presence_mode.party_current,
            party_maximum=presence_mode.party_maximum,
            application_entry_id=(
                application_entry_id
            ),
            pinned=(
                existing.pinned
                if pinned is None
                else bool(pinned)
            ),
            updated_at=utc_now_iso(),
        )

        return self.upsert(updated)

    def duplicate(
        self,
        preset_id: str,
    ) -> PresencePreset:
        source = self.get(preset_id)

        if source is None:
            raise PresencePresetError(
                "Presence preset was not found."
            )

        now = utc_now_iso()
        presets = self.load()
        new_id = make_preset_id()
        image_path = self.copy_image_for_preset(
            source.image_path,
            new_id,
        )

        duplicate = replace(
            source,
            preset_id=new_id,
            name=unique_copy_name(
                [preset.name for preset in presets],
                source.name,
            ),
            image_path=image_path or source.image_path,
            pinned=False,
            created_at=now,
            updated_at=now,
        ).normalized()

        presets.append(duplicate)
        self.save(presets)

        return duplicate

    def delete(
        self,
        preset_id: str,
    ) -> bool:
        presets = self.load()
        remaining = [
            preset
            for preset in presets
            if preset.preset_id != preset_id
        ]

        if len(remaining) == len(presets):
            return False

        self.remove_images_for_preset(
            preset_id,
        )
        self.save(remaining)

        return True

    def pinned(self) -> list[PresencePreset]:
        return [
            preset
            for preset in self.load()
            if preset.pinned
        ][:MAX_PINNED_PRESETS]

    def set_pinned(
        self,
        preset_id: str,
        pinned: bool,
    ) -> PresencePreset:
        preset = self.get(preset_id)

        if preset is None:
            raise PresencePresetError(
                "Presence preset was not found."
            )

        return self.upsert(
            replace(
                preset,
                pinned=bool(pinned),
            )
        )

    def copy_image_for_preset(
        self,
        source_path: str,
        preset_id: str,
    ) -> str:
        source_text = validate_image_path(
            source_path,
        )

        if not source_text:
            return ""

        source = Path(source_text)

        if not source.exists() or not source.is_file():
            return ""

        suffix = source.suffix.lower()

        if suffix not in ALLOWED_IMAGE_SUFFIXES:
            suffix = ".png"

        self.image_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.remove_images_for_preset(
            preset_id,
        )

        destination = (
            self.image_directory
            / f"{preset_id}{suffix}"
        )

        try:
            shutil.copy2(
                source,
                destination,
            )

            return str(destination)

        except OSError:
            return ""

    def remove_images_for_preset(
        self,
        preset_id: str,
    ):
        if not is_valid_preset_id(
            preset_id,
        ):
            return

        if not self.image_directory.exists():
            return

        for candidate in self.image_directory.glob(
            f"{preset_id}.*"
        ):
            if candidate.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
                continue

            try:
                candidate.unlink()
            except OSError:
                pass

    def _quarantine_corrupt_storage(
        self,
        error: Exception,
    ):
        if not self.storage_path.exists():
            return

        stamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )
        quarantine_path = self.storage_path.with_name(
            f"{self.storage_path.stem}.corrupt-{stamp}{self.storage_path.suffix}"
        )

        try:
            self.storage_path.replace(
                quarantine_path
            )
            quarantine_path.with_suffix(
                quarantine_path.suffix + ".error.txt"
            ).write_text(
                str(error),
                encoding="utf-8",
            )

        except OSError:
            pass
