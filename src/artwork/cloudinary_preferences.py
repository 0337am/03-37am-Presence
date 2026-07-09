from __future__ import annotations

import json
import os
from dataclasses import (
    asdict,
    dataclass,
)
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class CloudinaryPreferences:
    enabled: bool = False
    cloud_name: str = ""
    upload_preset: str = ""

    @property
    def configured(self) -> bool:
        return bool(
            self.cloud_name
            and self.upload_preset
        )


class CloudinaryPreferencesStore:
    """
    Stores optional Bring Your Own Cloudinary settings.

    Only the user's cloud name and unsigned upload
    preset are stored. API keys and API secrets are
    deliberately unsupported.
    """

    def __init__(self):
        self.file_path = (
            self._get_file_path()
        )

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.file_path.exists():
            self.save(
                CloudinaryPreferences()
            )

    def _get_file_path(self) -> Path:
        local_app_data = os.getenv(
            "LOCALAPPDATA",
            "",
        ).strip()

        if local_app_data:
            data_directory = (
                Path(local_app_data)
                / "0337am Presence"
            )
        else:
            data_directory = (
                Path.home()
                / ".0337am-presence"
            )

        return (
            data_directory
            / "cloudinary_preferences.json"
        )

    def load(self) -> CloudinaryPreferences:
        try:
            with self.file_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            if not isinstance(
                data,
                dict,
            ):
                raise TypeError(
                    "Cloudinary preferences must "
                    "contain a JSON object."
                )

        except FileNotFoundError:
            preferences = (
                CloudinaryPreferences()
            )

            self.save(preferences)
            return preferences

        except (
            json.JSONDecodeError,
            OSError,
            TypeError,
        ):
            self._quarantine_invalid_file()

            preferences = (
                CloudinaryPreferences()
            )

            self.save(preferences)
            return preferences

        cloud_name = self._read_text(
            data.get("cloud_name"),
            maximum_length=128,
        )

        upload_preset = self._read_text(
            data.get("upload_preset"),
            maximum_length=255,
        )

        enabled = (
            self._read_bool(
                data.get("enabled"),
                default=False,
            )
            and bool(cloud_name)
            and bool(upload_preset)
        )

        return CloudinaryPreferences(
            enabled=enabled,
            cloud_name=cloud_name,
            upload_preset=upload_preset,
        )

    def save(
        self,
        preferences: CloudinaryPreferences,
    ):
        if not isinstance(
            preferences,
            CloudinaryPreferences,
        ):
            raise TypeError(
                "preferences must be a "
                "CloudinaryPreferences instance."
            )

        cloud_name = self._read_text(
            preferences.cloud_name,
            maximum_length=128,
        )

        upload_preset = self._read_text(
            preferences.upload_preset,
            maximum_length=255,
        )

        normalized = CloudinaryPreferences(
            enabled=(
                bool(preferences.enabled)
                and bool(cloud_name)
                and bool(upload_preset)
            ),
            cloud_name=cloud_name,
            upload_preset=upload_preset,
        )

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = (
            self.file_path.with_suffix(
                self.file_path.suffix
                + ".tmp"
            )
        )

        payload = asdict(
            normalized
        )

        try:
            with temporary_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    payload,
                    file,
                    indent=2,
                    sort_keys=True,
                )

                file.write("\n")
                file.flush()
                os.fsync(
                    file.fileno()
                )

            with temporary_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                verified_payload = (
                    json.load(file)
                )

            if verified_payload != payload:
                raise ValueError(
                    "Temporary Cloudinary preferences "
                    "failed validation."
                )

            temporary_path.replace(
                self.file_path
            )

        finally:
            temporary_path.unlink(
                missing_ok=True
            )

    def update(
        self,
        enabled: bool | None = None,
        cloud_name: str | None = None,
        upload_preset: str | None = None,
    ) -> CloudinaryPreferences:
        current = self.load()

        updated_cloud_name = (
            current.cloud_name
            if cloud_name is None
            else self._read_text(
                cloud_name,
                maximum_length=128,
            )
        )

        updated_upload_preset = (
            current.upload_preset
            if upload_preset is None
            else self._read_text(
                upload_preset,
                maximum_length=255,
            )
        )

        requested_enabled = (
            current.enabled
            if enabled is None
            else bool(enabled)
        )

        updated = CloudinaryPreferences(
            enabled=(
                requested_enabled
                and bool(updated_cloud_name)
                and bool(updated_upload_preset)
            ),
            cloud_name=updated_cloud_name,
            upload_preset=updated_upload_preset,
        )

        self.save(updated)
        return updated

    def disconnect(self) -> CloudinaryPreferences:
        preferences = CloudinaryPreferences()

        self.save(preferences)
        return preferences

    def configured(self) -> bool:
        return self.load().configured

    def enabled(self) -> bool:
        return self.load().enabled

    def _quarantine_invalid_file(
        self,
    ) -> Path | None:
        if not self.file_path.exists():
            return None

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        invalid_path = (
            self.file_path.with_name(
                f"{self.file_path.stem}"
                f".invalid_{timestamp}"
                f"{self.file_path.suffix}"
            )
        )

        try:
            self.file_path.replace(
                invalid_path
            )

        except OSError:
            return None

        return invalid_path

    @staticmethod
    def _read_bool(
        value,
        default: bool,
    ) -> bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            normalized = (
                value.strip().lower()
            )

            if normalized in {
                "true",
                "1",
                "yes",
                "on",
            }:
                return True

            if normalized in {
                "false",
                "0",
                "no",
                "off",
            }:
                return False

        if isinstance(value, int):
            return value != 0

        return default

    @staticmethod
    def _read_text(
        value,
        maximum_length: int,
    ) -> str:
        if not isinstance(value, str):
            return ""

        normalized = value.strip()

        if not normalized:
            return ""

        if len(normalized) > maximum_length:
            return ""

        if any(
            ord(character) < 32
            or ord(character) == 127
            for character in normalized
        ):
            return ""

        return normalized
