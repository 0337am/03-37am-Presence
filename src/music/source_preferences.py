from __future__ import annotations

import json
import os
from dataclasses import (
    asdict,
    dataclass,
)
from pathlib import Path


@dataclass(frozen=True)
class SourcePreferences:
    spotify_enabled: bool = True
    browser_enabled: bool = False


class SourcePreferencesStore:
    """
    Saves enabled media sources between app restarts.

    Browser media is disabled by default so the app
    keeps its existing Spotify-only behavior until
    the user enables Chrome / SoundCloud support.
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
                SourcePreferences()
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
            / "source_preferences.json"
        )

    def load(self) -> SourcePreferences:
        try:
            with self.file_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except (
            FileNotFoundError,
            json.JSONDecodeError,
            OSError,
            TypeError,
        ):
            preferences = (
                SourcePreferences()
            )

            self.save(preferences)
            return preferences

        return SourcePreferences(
            spotify_enabled=self._read_bool(
                data.get(
                    "spotify_enabled"
                ),
                default=True,
            ),
            browser_enabled=self._read_bool(
                data.get(
                    "browser_enabled"
                ),
                default=False,
            ),
        )

    def save(
        self,
        preferences: SourcePreferences,
    ):
        temporary_path = (
            self.file_path.with_suffix(
                ".tmp"
            )
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                asdict(preferences),
                file,
                indent=2,
            )

        temporary_path.replace(
            self.file_path
        )

    def update(
        self,
        spotify_enabled: bool | None = None,
        browser_enabled: bool | None = None,
    ) -> SourcePreferences:
        current = self.load()

        updated = SourcePreferences(
            spotify_enabled=(
                current.spotify_enabled
                if spotify_enabled is None
                else bool(spotify_enabled)
            ),
            browser_enabled=(
                current.browser_enabled
                if browser_enabled is None
                else bool(browser_enabled)
            ),
        )

        self.save(updated)
        return updated

    def spotify_enabled(self) -> bool:
        return (
            self.load().spotify_enabled
        )

    def browser_enabled(self) -> bool:
        return (
            self.load().browser_enabled
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