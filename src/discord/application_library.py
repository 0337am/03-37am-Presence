from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.discord.identity_preferences import (
    DEFAULT_DISCORD_APPLICATION_ID,
    validate_discord_application_id,
)
from src.discord.presence_modes import (
    APP_DATA_DIRECTORY,
)


APPLICATION_LIBRARY_STORAGE_KIND = (
    "0337am-discord-application-library"
)

SCHEMA_VERSION = 1

APPLICATION_LIBRARY_STORAGE_PATH = (
    APP_DATA_DIRECTORY
    / "discord_applications.json"
)

MAX_APPLICATIONS = 64
MAX_APPLICATION_NAME_LENGTH = 64
MAX_STORAGE_FILE_BYTES = 64 * 1024

USER_ENTRY_ID_PREFIX = "discord_app_"
USER_ENTRY_ID_HEX_LENGTH = 16

BUILTIN_APPLICATION_ENTRY_ID = (
    "builtin.0337am"
)

BUILTIN_APPLICATION_NAME = (
    "03:37am Music"
)

LEGACY_IMPORTED_APPLICATION_NAME = (
    "Imported Discord Application"
)


class DiscordApplicationLibraryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DiscordApplicationEntry:
    entry_id: str
    name: str
    application_id: str
    builtin: bool = False


@dataclass(frozen=True, slots=True)
class DiscordApplicationLibraryStorage:
    applications: tuple[
        DiscordApplicationEntry,
        ...
    ] = ()
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "kind": (
                APPLICATION_LIBRARY_STORAGE_KIND
            ),
            "schema_version": (
                self.schema_version
            ),
            "applications": [
                application_entry_to_dict(
                    entry
                )
                for entry
                in self.applications
            ],
        }


BUILTIN_APPLICATION_ENTRY = (
    DiscordApplicationEntry(
        entry_id=(
            BUILTIN_APPLICATION_ENTRY_ID
        ),
        name=(
            BUILTIN_APPLICATION_NAME
        ),
        application_id=(
            DEFAULT_DISCORD_APPLICATION_ID
        ),
        builtin=True,
    )
)


def _clean_text(value: object) -> str:
    return (
        str(value or "")
        .replace("\x00", "")
        .strip()
    )


def validate_application_name(
    value: object,
) -> str:
    name = _clean_text(value)

    if not name:
        raise DiscordApplicationLibraryError(
            "Discord application name "
            "cannot be empty."
        )

    if (
        len(name)
        > MAX_APPLICATION_NAME_LENGTH
    ):
        raise DiscordApplicationLibraryError(
            "Discord application name cannot "
            f"exceed {MAX_APPLICATION_NAME_LENGTH} "
            "characters."
        )

    return name


def _normalize_application_id(
    value: object,
) -> str:
    application_id = _clean_text(
        value
    )

    try:
        validate_discord_application_id(
            application_id
        )
    except ValueError as error:
        raise DiscordApplicationLibraryError(
            str(error)
        ) from error

    return application_id


def make_application_entry_id() -> str:
    return (
        USER_ENTRY_ID_PREFIX
        + uuid.uuid4().hex[
            :USER_ENTRY_ID_HEX_LENGTH
        ]
    )


def is_valid_user_entry_id(
    value: object,
) -> bool:
    entry_id = _clean_text(
        value
    )

    if not entry_id.startswith(
        USER_ENTRY_ID_PREFIX
    ):
        return False

    suffix = entry_id[
        len(USER_ENTRY_ID_PREFIX):
    ]

    if (
        len(suffix)
        != USER_ENTRY_ID_HEX_LENGTH
    ):
        return False

    return all(
        character
        in "0123456789abcdef"
        for character in suffix
    )


def application_entry_to_dict(
    entry: DiscordApplicationEntry,
) -> dict:
    if not isinstance(
        entry,
        DiscordApplicationEntry,
    ):
        raise TypeError(
            "entry must be a "
            "DiscordApplicationEntry."
        )

    if entry.builtin:
        raise DiscordApplicationLibraryError(
            "Built-in Discord applications "
            "are not persisted in the user "
            "Application Library."
        )

    entry_id = _clean_text(
        entry.entry_id
    )

    if not is_valid_user_entry_id(
        entry_id
    ):
        raise DiscordApplicationLibraryError(
            "Discord application entry ID "
            "is invalid."
        )

    return {
        "id": entry_id,
        "name": validate_application_name(
            entry.name
        ),
        "application_id": (
            _normalize_application_id(
                entry.application_id
            )
        ),
    }


def application_entry_from_dict(
    data: dict,
) -> DiscordApplicationEntry:
    if not isinstance(
        data,
        dict,
    ):
        raise DiscordApplicationLibraryError(
            "Discord application entry "
            "must be an object."
        )

    entry_id = _clean_text(
        data.get("id")
        or data.get("entry_id")
    )

    if not is_valid_user_entry_id(
        entry_id
    ):
        raise DiscordApplicationLibraryError(
            "Discord application entry ID "
            "is invalid."
        )

    return DiscordApplicationEntry(
        entry_id=entry_id,
        name=validate_application_name(
            data.get("name")
        ),
        application_id=(
            _normalize_application_id(
                data.get(
                    "application_id"
                )
            )
        ),
        builtin=False,
    )


def _validate_unique_entries(
    entries: Iterable[
        DiscordApplicationEntry
    ],
) -> tuple[
    DiscordApplicationEntry,
    ...
]:
    normalized = []

    seen_entry_ids = {
        BUILTIN_APPLICATION_ENTRY.entry_id
    }

    seen_names = {
        BUILTIN_APPLICATION_ENTRY
        .name
        .casefold()
    }

    seen_application_ids = {
        BUILTIN_APPLICATION_ENTRY
        .application_id
    }

    for raw_entry in entries:
        if not isinstance(
            raw_entry,
            DiscordApplicationEntry,
        ):
            raise TypeError(
                "Application Library entries "
                "must be DiscordApplicationEntry "
                "instances."
            )

        if raw_entry.builtin:
            raise DiscordApplicationLibraryError(
                "The built-in 03:37am Discord "
                "application cannot be stored "
                "as a user application."
            )

        entry = (
            application_entry_from_dict(
                application_entry_to_dict(
                    raw_entry
                )
            )
        )

        if (
            entry.entry_id
            in seen_entry_ids
        ):
            raise DiscordApplicationLibraryError(
                "Discord application entry IDs "
                "must be unique."
            )

        folded_name = (
            entry.name.casefold()
        )

        if folded_name in seen_names:
            raise DiscordApplicationLibraryError(
                "Discord application names "
                "must be unique."
            )

        if (
            entry.application_id
            in seen_application_ids
        ):
            raise DiscordApplicationLibraryError(
                "Discord Application IDs "
                "must be unique."
            )

        seen_entry_ids.add(
            entry.entry_id
        )

        seen_names.add(
            folded_name
        )

        seen_application_ids.add(
            entry.application_id
        )

        normalized.append(
            entry
        )

    if len(normalized) > MAX_APPLICATIONS:
        raise DiscordApplicationLibraryError(
            "Too many Discord applications."
        )

    return tuple(
        normalized
    )


def storage_from_dict(
    data: dict,
) -> DiscordApplicationLibraryStorage:
    if not isinstance(
        data,
        dict,
    ):
        raise DiscordApplicationLibraryError(
            "Discord Application Library "
            "storage must be an object."
        )

    if (
        data.get("kind")
        != APPLICATION_LIBRARY_STORAGE_KIND
    ):
        raise DiscordApplicationLibraryError(
            "Discord Application Library "
            "storage kind is invalid."
        )

    try:
        schema_version = int(
            data.get(
                "schema_version",
                0,
            )
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise DiscordApplicationLibraryError(
            "Discord Application Library "
            "schema is invalid."
        ) from error

    if schema_version != SCHEMA_VERSION:
        raise DiscordApplicationLibraryError(
            "Discord Application Library "
            "schema is not supported."
        )

    raw_applications = data.get(
        "applications",
        [],
    )

    if not isinstance(
        raw_applications,
        list,
    ):
        raise DiscordApplicationLibraryError(
            "Discord Application Library "
            "application list is invalid."
        )

    if (
        len(raw_applications)
        > MAX_APPLICATIONS
    ):
        raise DiscordApplicationLibraryError(
            "Too many Discord applications."
        )

    applications = (
        _validate_unique_entries(
            application_entry_from_dict(
                item
            )
            for item
            in raw_applications
        )
    )

    return DiscordApplicationLibraryStorage(
        applications=applications,
        schema_version=schema_version,
    )


def _unique_available_name(
    entries: Iterable[
        DiscordApplicationEntry
    ],
    base_name: str,
) -> str:
    base = validate_application_name(
        base_name
    )

    existing = {
        entry.name.casefold()
        for entry in entries
    }

    if base.casefold() not in existing:
        return base

    for number in range(
        2,
        MAX_APPLICATIONS + 3,
    ):
        suffix = f" {number}"

        maximum_base = (
            MAX_APPLICATION_NAME_LENGTH
            - len(suffix)
        )

        candidate = (
            base[:maximum_base]
            .rstrip()
            + suffix
        )

        if (
            candidate.casefold()
            not in existing
        ):
            return candidate

    raise DiscordApplicationLibraryError(
        "Could not create a unique "
        "Discord application name."
    )


class DiscordApplicationLibraryStore:
    def __init__(
        self,
        storage_path: Path | str | None = None,
    ) -> None:
        self.storage_path = (
            Path(storage_path)
            if storage_path is not None
            else APPLICATION_LIBRARY_STORAGE_PATH
        )

    def load_storage(
        self,
    ) -> DiscordApplicationLibraryStorage:
        if not self.storage_path.exists():
            return (
                DiscordApplicationLibraryStorage()
            )

        try:
            if (
                self.storage_path
                .stat()
                .st_size
                > MAX_STORAGE_FILE_BYTES
            ):
                raise DiscordApplicationLibraryError(
                    "Discord Application Library "
                    "storage is too large."
                )

            raw = (
                self.storage_path
                .read_bytes()
            )

            if (
                len(raw)
                > MAX_STORAGE_FILE_BYTES
            ):
                raise DiscordApplicationLibraryError(
                    "Discord Application Library "
                    "storage is too large."
                )

            payload = json.loads(
                raw.decode("utf-8")
            )

            return storage_from_dict(
                payload
            )

        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            self._quarantine_corrupt_storage()

            return (
                DiscordApplicationLibraryStorage()
            )

    def user_entries(
        self,
    ) -> list[
        DiscordApplicationEntry
    ]:
        return list(
            self.load_storage()
            .applications
        )

    def list_entries(
        self,
    ) -> list[
        DiscordApplicationEntry
    ]:
        return [
            BUILTIN_APPLICATION_ENTRY,
            *self.user_entries(),
        ]

    def get(
        self,
        entry_id: str,
    ) -> DiscordApplicationEntry | None:
        normalized_id = _clean_text(
            entry_id
        )

        if (
            normalized_id
            == BUILTIN_APPLICATION_ENTRY_ID
        ):
            return BUILTIN_APPLICATION_ENTRY

        for entry in self.user_entries():
            if (
                entry.entry_id
                == normalized_id
            ):
                return entry

        return None

    def find_by_application_id(
        self,
        application_id: str,
    ) -> DiscordApplicationEntry | None:
        try:
            normalized_id = (
                _normalize_application_id(
                    application_id
                )
            )
        except DiscordApplicationLibraryError:
            return None

        for entry in self.list_entries():
            if (
                entry.application_id
                == normalized_id
            ):
                return entry

        return None

    def save(
        self,
        entries: Iterable[
            DiscordApplicationEntry
        ],
    ) -> DiscordApplicationLibraryStorage:
        normalized = (
            _validate_unique_entries(
                entries
            )
        )

        storage = (
            DiscordApplicationLibraryStorage(
                applications=normalized,
            )
        )

        encoded = (
            json.dumps(
                storage.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode(
            "utf-8"
        )

        if (
            len(encoded)
            > MAX_STORAGE_FILE_BYTES
        ):
            raise DiscordApplicationLibraryError(
                "Discord Application Library "
                "storage is too large."
            )

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = (
            self.storage_path.with_name(
                "."
                + self.storage_path.name
                + "."
                + str(os.getpid())
                + "."
                + uuid.uuid4().hex
                + ".tmp"
            )
        )

        try:
            with temporary_path.open(
                "xb"
            ) as handle:
                handle.write(
                    encoded
                )

                handle.flush()

                os.fsync(
                    handle.fileno()
                )

            os.replace(
                temporary_path,
                self.storage_path,
            )

        finally:
            try:
                temporary_path.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

        return storage

    def create(
        self,
        *,
        name: str,
        application_id: str,
    ) -> DiscordApplicationEntry:
        entries = self.user_entries()

        entry_id = (
            make_application_entry_id()
        )

        existing_ids = {
            entry.entry_id
            for entry in entries
        }

        while entry_id in existing_ids:
            entry_id = (
                make_application_entry_id()
            )

        entry = DiscordApplicationEntry(
            entry_id=entry_id,
            name=validate_application_name(
                name
            ),
            application_id=(
                _normalize_application_id(
                    application_id
                )
            ),
        )

        self.save(
            [
                *entries,
                entry,
            ]
        )

        return entry

    def update(
        self,
        entry_id: str,
        *,
        name: str | None = None,
        application_id: str | None = None,
    ) -> DiscordApplicationEntry:
        normalized_id = _clean_text(
            entry_id
        )

        if (
            normalized_id
            == BUILTIN_APPLICATION_ENTRY_ID
        ):
            raise DiscordApplicationLibraryError(
                "The built-in 03:37am "
                "application cannot be edited."
            )

        entries = self.user_entries()

        index = next(
            (
                position
                for position, entry
                in enumerate(entries)
                if (
                    entry.entry_id
                    == normalized_id
                )
            ),
            None,
        )

        if index is None:
            raise DiscordApplicationLibraryError(
                "Discord application "
                "was not found."
            )

        current = entries[index]

        updated = replace(
            current,
            name=(
                current.name
                if name is None
                else validate_application_name(
                    name
                )
            ),
            application_id=(
                current.application_id
                if application_id is None
                else _normalize_application_id(
                    application_id
                )
            ),
        )

        entries[index] = updated

        self.save(
            entries
        )

        return updated

    def delete(
        self,
        entry_id: str,
    ) -> bool:
        normalized_id = _clean_text(
            entry_id
        )

        if (
            normalized_id
            == BUILTIN_APPLICATION_ENTRY_ID
        ):
            raise DiscordApplicationLibraryError(
                "The built-in 03:37am "
                "application cannot be deleted."
            )

        entries = self.user_entries()

        remaining = [
            entry
            for entry in entries
            if (
                entry.entry_id
                != normalized_id
            )
        ]

        if (
            len(remaining)
            == len(entries)
        ):
            return False

        self.save(
            remaining
        )

        return True

    def reset_user_entries(
        self,
    ) -> None:
        try:
            self.storage_path.unlink(
                missing_ok=True
            )
        except OSError as error:
            raise DiscordApplicationLibraryError(
                "Discord Application Library "
                "could not be reset."
            ) from error

    def migrate_legacy_application_id(
        self,
        application_id: str,
        *,
        name: str = (
            LEGACY_IMPORTED_APPLICATION_NAME
        ),
    ) -> DiscordApplicationEntry | None:
        raw_id = _clean_text(
            application_id
        )

        if not raw_id:
            return None

        try:
            normalized_id = (
                _normalize_application_id(
                    raw_id
                )
            )
        except DiscordApplicationLibraryError:
            return None

        existing = (
            self.find_by_application_id(
                normalized_id
            )
        )

        if existing is not None:
            return existing

        migration_name = (
            _unique_available_name(
                self.list_entries(),
                name,
            )
        )

        return self.create(
            name=migration_name,
            application_id=normalized_id,
        )

    def _quarantine_corrupt_storage(
        self,
    ) -> Path | None:
        if not self.storage_path.exists():
            return None

        timestamp = (
            datetime.now(
                timezone.utc
            )
            .strftime(
                "%Y%m%dT%H%M%SZ"
            )
        )

        quarantine_path = (
            self.storage_path.with_name(
                self.storage_path.name
                + ".corrupt-"
                + timestamp
                + "-"
                + uuid.uuid4().hex[:8]
            )
        )

        try:
            os.replace(
                self.storage_path,
                quarantine_path,
            )
        except OSError:
            return None

        return quarantine_path
