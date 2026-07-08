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
class AfkPreferences:
    enabled: bool = False
    timeout_minutes: int = 10


class AfkPreferencesStore:
    """
    Saves Auto AFK settings between app restarts.
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
                AfkPreferences()
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
            / "afk_preferences.json"
        )

    def load(self) -> AfkPreferences:
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
                    "AFK preferences must "
                    "contain a JSON object."
                )

        except FileNotFoundError:
            preferences = AfkPreferences()

            self.save(preferences)
            return preferences

        except (
            json.JSONDecodeError,
            OSError,
            TypeError,
        ):
            self._quarantine_invalid_file()

            preferences = AfkPreferences()

            self.save(preferences)
            return preferences

        return AfkPreferences(
            enabled=self._read_bool(
                data.get("enabled"),
                default=False,
            ),
            timeout_minutes=(
                self._safe_timeout(
                    data.get(
                        "timeout_minutes",
                        10,
                    )
                )
            ),
        )

    def save(
        self,
        preferences: AfkPreferences,
    ):
        if not isinstance(
            preferences,
            AfkPreferences,
        ):
            raise TypeError(
                "preferences must be an "
                "AfkPreferences instance."
            )

        safe_preferences = AfkPreferences(
            enabled=bool(
                preferences.enabled
            ),
            timeout_minutes=(
                self._safe_timeout(
                    preferences.timeout_minutes
                )
            ),
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
            safe_preferences
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
                verified_payload = (
                    json.load(file)
                )

            if verified_payload != payload:
                raise ValueError(
                    "Temporary AFK preferences "
                    "failed validation."
                )

            temporary_path.replace(
                self.file_path
            )

        finally:
            temporary_path.unlink(
                missing_ok=True
            )

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

    def update(
        self,
        enabled: bool | None = None,
        timeout_minutes: int | None = None,
    ) -> AfkPreferences:
        current = self.load()

        updated = AfkPreferences(
            enabled=(
                current.enabled
                if enabled is None
                else bool(enabled)
            ),
            timeout_minutes=(
                current.timeout_minutes
                if timeout_minutes is None
                else self._safe_timeout(
                    timeout_minutes
                )
            ),
        )

        self.save(updated)
        return updated

    @staticmethod
    def _safe_timeout(
        value,
    ) -> int:
        try:
            minutes = int(value)

        except (
            TypeError,
            ValueError,
        ):
            return 10

        return max(
            1,
            min(minutes, 240),
        )

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