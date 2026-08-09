from __future__ import annotations

import json
import ntpath
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


LEGACY_SCHEMA_VERSION = 1
SCHEMA_VERSION = 2

FILE_NAME = (
    "local_music_preferences.json"
)

MAX_LOCAL_MUSIC_FOLDERS = 64

MAX_PREFERENCES_FILE_BYTES = (
    128
    * 1024
)


def _is_network_path(
    value: str,
) -> bool:
    return (
        value.startswith(
            "\\\\"
        )
        or value.startswith(
            "//"
        )
    )


def _normalize_folder_path(
    value,
) -> str:
    if isinstance(
        value,
        os.PathLike,
    ):
        value = os.fspath(
            value
        )

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            (
                "Local music folder paths "
                "must be strings."
            )
        )

    checked = value.strip()

    if not checked:
        raise ValueError(
            (
                "Local music folder paths "
                "cannot be empty."
            )
        )

    if "\x00" in checked:
        raise ValueError(
            (
                "Local music folder paths "
                "cannot contain null bytes."
            )
        )

    if len(
        checked
    ) > 32767:
        raise ValueError(
            (
                "Local music folder path "
                "is too long."
            )
        )

    if _is_network_path(
        checked
    ):
        raise ValueError(
            (
                "Network music folders "
                "are not supported."
            )
        )

    windows_absolute = (
        ntpath.isabs(
            checked
        )
    )

    native_absolute = (
        os.path.isabs(
            checked
        )
    )

    if not (
        windows_absolute
        or native_absolute
    ):
        raise ValueError(
            (
                "Local music folders "
                "must use absolute paths."
            )
        )

    if windows_absolute:
        normalized = (
            ntpath.normpath(
                checked
            )
        )

    else:
        normalized = (
            os.path.normpath(
                checked
            )
        )

    if not normalized:
        raise ValueError(
            (
                "Local music folder path "
                "is invalid."
            )
        )

    return normalized


def _folder_key(
    value: str,
) -> str:
    if ntpath.isabs(
        value
    ):
        return (
            ntpath.normcase(
                value
            )
            .casefold()
        )

    return (
        os.path.normcase(
            value
        )
        .casefold()
    )


def _normalize_folders(
    folders,
) -> tuple[
    str,
    ...,
]:
    if not isinstance(
        folders,
        tuple,
    ):
        raise TypeError(
            "folders must be a tuple"
        )

    if len(
        folders
    ) > MAX_LOCAL_MUSIC_FOLDERS:
        raise ValueError(
            (
                "Too many local music "
                "folders are configured."
            )
        )

    normalized = []
    seen = set()

    for folder in folders:
        checked = (
            _normalize_folder_path(
                folder
            )
        )

        key = _folder_key(
            checked
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        normalized.append(
            checked
        )

    return tuple(
        normalized
    )


@dataclass(
    frozen=True,
    slots=True,
)
class LocalMusicPreferences:
    folders: tuple[
        str,
        ...,
    ] = ()

    scan_on_startup: bool = True

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "folders",
            _normalize_folders(
                self.folders
            ),
        )

        if not isinstance(
            self.scan_on_startup,
            bool,
        ):
            raise TypeError(
                (
                    "scan_on_startup must "
                    "be a boolean"
                )
            )


def local_music_preferences_to_payload(
    preferences: LocalMusicPreferences,
) -> dict:
    if not isinstance(
        preferences,
        LocalMusicPreferences,
    ):
        raise TypeError(
            (
                "preferences must be a "
                "LocalMusicPreferences instance."
            )
        )

    return {
        "schema_version": (
            SCHEMA_VERSION
        ),
        "folders": list(
            preferences.folders
        ),
        "scan_on_startup": (
            preferences.scan_on_startup
        ),
    }


def local_music_preferences_from_payload(
    payload,
) -> LocalMusicPreferences:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            (
                "Local music preferences "
                "must contain a JSON object."
            )
        )

    schema_version = payload.get(
        "schema_version"
    )

    if (
        isinstance(
            schema_version,
            bool,
        )
        or schema_version
        not in (
            LEGACY_SCHEMA_VERSION,
            SCHEMA_VERSION,
        )
    ):
        raise ValueError(
            (
                "Unsupported local music "
                "preference schema."
            )
        )

    folders = payload.get(
        "folders"
    )

    if not isinstance(
        folders,
        list,
    ):
        raise TypeError(
            (
                "Local music preference "
                "folders must be a list."
            )
        )

    if (
        schema_version
        == LEGACY_SCHEMA_VERSION
    ):
        scan_on_startup = True

    else:
        scan_on_startup = payload.get(
            "scan_on_startup"
        )

        if not isinstance(
            scan_on_startup,
            bool,
        ):
            raise TypeError(
                (
                    "Local music startup scan "
                    "preference must be a boolean."
                )
            )

    return LocalMusicPreferences(
        folders=tuple(
            folders
        ),
        scan_on_startup=(
            scan_on_startup
        ),
    )


class LocalMusicPreferencesStore:
    def __init__(
        self,
        path: Path | str | None = None,
    ) -> None:
        self.file_path = (
            Path(
                path
            )
            if path is not None
            else self.default_path()
        )

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.file_path.exists():
            self.save(
                LocalMusicPreferences()
            )

    @staticmethod
    def default_path(
    ) -> Path:
        local_app_data = str(
            os.getenv(
                "LOCALAPPDATA",
                "",
            )
            or ""
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
    ) -> LocalMusicPreferences:
        if not self.file_path.exists():
            preferences = (
                LocalMusicPreferences()
            )

            self.save(
                preferences
            )

            return preferences

        try:
            size = (
                self.file_path
                .stat()
                .st_size
            )

            if (
                size
                > MAX_PREFERENCES_FILE_BYTES
            ):
                raise ValueError(
                    (
                        "Local music preference "
                        "file is too large."
                    )
                )

            raw_text = (
                self.file_path
                .read_text(
                    encoding="utf-8"
                )
            )

            payload = json.loads(
                raw_text
            )

            preferences = (
                local_music_preferences_from_payload(
                    payload
                )
            )

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as error:
            print(
                (
                    "Local music preferences "
                    "load error:"
                ),
                error,
            )

            quarantined = (
                self._quarantine_invalid_file()
            )

            if quarantined is not None:
                print(
                    (
                        "Invalid local music "
                        "preferences quarantined:"
                    ),
                    quarantined,
                )

            preferences = (
                LocalMusicPreferences()
            )

            self.save(
                preferences
            )

            return preferences

        if (
            payload.get(
                "schema_version"
            )
            == LEGACY_SCHEMA_VERSION
        ):
            try:
                self.save(
                    preferences
                )

            except (
                OSError,
                UnicodeError,
                TypeError,
                ValueError,
            ) as error:
                print(
                    (
                        "Local music preferences "
                        "migration error:"
                    ),
                    error,
                )

        return preferences

    def save(
        self,
        preferences: LocalMusicPreferences,
    ) -> LocalMusicPreferences:
        if not isinstance(
            preferences,
            LocalMusicPreferences,
        ):
            raise TypeError(
                (
                    "preferences must be a "
                    "LocalMusicPreferences instance."
                )
            )

        payload = (
            local_music_preferences_to_payload(
                preferences
            )
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
                    ensure_ascii=False,
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

            verified_payload = (
                json.loads(
                    temporary_path.read_text(
                        encoding="utf-8"
                    )
                )
            )

            verified = (
                local_music_preferences_from_payload(
                    verified_payload
                )
            )

            if verified != preferences:
                raise ValueError(
                    (
                        "Temporary local music "
                        "preferences failed "
                        "validation."
                    )
                )

            temporary_path.replace(
                self.file_path
            )

        finally:
            try:
                temporary_path.unlink(
                    missing_ok=True
                )

            except OSError:
                pass

        return preferences

    def set_scan_on_startup(
        self,
        enabled: bool,
    ) -> LocalMusicPreferences:
        if not isinstance(
            enabled,
            bool,
        ):
            raise TypeError(
                (
                    "enabled must be "
                    "a boolean"
                )
            )

        current = self.load()

        if (
            current.scan_on_startup
            == enabled
        ):
            return current

        return self.save(
            LocalMusicPreferences(
                folders=(
                    current.folders
                ),
                scan_on_startup=(
                    enabled
                ),
            )
        )

    def add_folder(
        self,
        folder,
    ) -> LocalMusicPreferences:
        checked = (
            _normalize_folder_path(
                folder
            )
        )

        current = self.load()

        updated = LocalMusicPreferences(
            folders=(
                current.folders
                + (
                    checked,
                )
            ),
            scan_on_startup=(
                current.scan_on_startup
            ),
        )

        if updated == current:
            return current

        return self.save(
            updated
        )

    def remove_folder(
        self,
        folder,
    ) -> LocalMusicPreferences:
        checked = (
            _normalize_folder_path(
                folder
            )
        )

        target_key = (
            _folder_key(
                checked
            )
        )

        current = self.load()

        remaining = tuple(
            value
            for value
            in current.folders
            if _folder_key(
                value
            )
            != target_key
        )

        if remaining == current.folders:
            return current

        return self.save(
            LocalMusicPreferences(
                folders=remaining,
                scan_on_startup=(
                    current.scan_on_startup
                ),
            )
        )

    def clear(
        self,
    ) -> LocalMusicPreferences:
        return self.save(
            LocalMusicPreferences()
        )

    def _quarantine_invalid_file(
        self,
    ) -> Path | None:
        if not self.file_path.exists():
            return None

        timestamp = (
            datetime.now()
            .astimezone()
            .strftime(
                "%Y%m%d-%H%M%S-%f"
            )
        )

        invalid_path = (
            self.file_path.with_name(
                (
                    self.file_path.stem
                    + ".invalid-"
                    + timestamp
                    + self.file_path.suffix
                )
            )
        )

        try:
            self.file_path.replace(
                invalid_path
            )

        except OSError:
            return None

        return invalid_path
