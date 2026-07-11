from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.ui.dashboard_layout import (
    DashboardLayout,
)


SCHEMA_VERSION = 1
MAX_LAYOUT_PROFILES = 20
MAX_PROFILE_NAME_LENGTH = 40


def normalise_profile_name(
    name: str,
) -> str:
    text = str(
        name or ""
    ).strip()

    if not text:
        raise ValueError(
            "Profile name cannot be empty."
        )

    if len(text) > MAX_PROFILE_NAME_LENGTH:
        raise ValueError(
            "Profile name is too long."
        )

    if any(
        ord(character) < 32
        for character in text
    ):
        raise ValueError(
            "Profile name cannot contain control characters."
        )

    reserved = {
        "custom",
        "default",
        "compact",
        "media focus",
        "library focus",
        "minimal",
    }

    if text.casefold() in reserved:
        raise ValueError(
            "Profile name cannot match a built-in layout name."
        )

    return text


def validate_profile_name(
    name: str,
) -> str:
    return normalise_profile_name(
        name
    )


@dataclass(frozen=True)
class DashboardLayoutProfile:
    name: str
    layout: DashboardLayout

    def __post_init__(self):
        object.__setattr__(
            self,
            "name",
            normalise_profile_name(
                self.name
            ),
        )

        if not isinstance(
            self.layout,
            DashboardLayout,
        ):
            raise TypeError(
                "Profile layout must be a DashboardLayout."
            )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "layout": self.layout.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        payload,
    ) -> "DashboardLayoutProfile":
        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Dashboard profile data must be an object."
            )

        return cls(
            name=normalise_profile_name(
                payload.get(
                    "name",
                    "",
                )
            ),
            layout=DashboardLayout.from_dict(
                payload.get(
                    "layout",
                    {},
                )
            ),
        )


def validate_profiles(
    profiles,
) -> tuple[DashboardLayoutProfile, ...]:
    if not isinstance(
        profiles,
        tuple,
    ):
        profiles = tuple(
            profiles
        )

    if len(profiles) > MAX_LAYOUT_PROFILES:
        raise ValueError(
            "There are too many dashboard layout profiles."
        )

    seen = set()
    validated = []

    for profile in profiles:
        if not isinstance(
            profile,
            DashboardLayoutProfile,
        ):
            raise TypeError(
                "Expected DashboardLayoutProfile."
            )

        normalized_key = (
            profile.name.casefold()
        )

        if normalized_key in seen:
            raise ValueError(
                "Dashboard layout profile names must be unique."
            )

        seen.add(
            normalized_key
        )
        validated.append(
            profile
        )

    return tuple(
        validated
    )


class DashboardLayoutProfileStore:
    def __init__(
        self,
        path: Path | str | None = None,
    ):
        self.path = (
            Path(path)
            if path is not None
            else self.default_path()
        )

    @staticmethod
    def default_path() -> Path:
        local_app_data = str(
            os.getenv(
                "LOCALAPPDATA",
                "",
            )
            or ""
        ).strip()

        if local_app_data:
            root = Path(
                local_app_data
            )
        else:
            root = (
                Path.home()
                / ".0337am-presence"
            )

        return (
            root
            / "0337am Presence"
            / "dashboard_layout_profiles.json"
        )

    def load(
        self,
    ) -> tuple[DashboardLayoutProfile, ...]:
        if not self.path.exists():
            return ()

        try:
            payload = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )

            return self._profiles_from_payload(
                payload
            )

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as error:
            self._quarantine_invalid_file()

            print(
                "Dashboard layout profiles were invalid "
                "and have been reset: "
                f"{error}"
            )

            return ()

    def save(
        self,
        profiles,
    ) -> tuple[DashboardLayoutProfile, ...]:
        validated = validate_profiles(
            profiles
        )

        payload = {
            "schema_version": SCHEMA_VERSION,
            "profiles": [
                profile.to_dict()
                for profile in validated
            ],
        }

        serialized = json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self.path.with_name(
            self.path.name
            + ".tmp"
        )

        try:
            with temporary_path.open(
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write(serialized)
                handle.write("\n")
                handle.flush()
                os.fsync(
                    handle.fileno()
                )

            os.replace(
                temporary_path,
                self.path,
            )

        except Exception:
            temporary_path.unlink(
                missing_ok=True
            )
            raise

        return validated

    def upsert(
        self,
        profile: DashboardLayoutProfile,
    ) -> tuple[DashboardLayoutProfile, ...]:
        validated_profile = DashboardLayoutProfile(
            name=profile.name,
            layout=profile.layout,
        )

        profiles = list(
            self.load()
        )

        replaced = False

        for index, existing in enumerate(
            profiles
        ):
            if (
                existing.name.casefold()
                == validated_profile.name.casefold()
            ):
                profiles[index] = validated_profile
                replaced = True
                break

        if not replaced:
            profiles.append(
                validated_profile
            )

        return self.save(
            tuple(
                profiles
            )
        )

    def delete(
        self,
        name: str,
    ) -> tuple[DashboardLayoutProfile, ...]:
        profile_name = normalise_profile_name(
            name
        )

        remaining = tuple(
            profile
            for profile in self.load()
            if (
                profile.name.casefold()
                != profile_name.casefold()
            )
        )

        return self.save(
            remaining
        )

    def get(
        self,
        name: str,
    ) -> DashboardLayoutProfile:
        profile_name = normalise_profile_name(
            name
        )

        for profile in self.load():
            if (
                profile.name.casefold()
                == profile_name.casefold()
            ):
                return profile

        raise KeyError(
            profile_name
        )

    @classmethod
    def _profiles_from_payload(
        cls,
        payload,
    ) -> tuple[DashboardLayoutProfile, ...]:
        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Dashboard profile storage must be an object."
            )

        schema_version = payload.get(
            "schema_version",
            1,
        )

        if (
            isinstance(
                schema_version,
                bool,
            )
            or not isinstance(
                schema_version,
                int,
            )
            or schema_version != SCHEMA_VERSION
        ):
            raise ValueError(
                "Unsupported dashboard profile storage version."
            )

        profiles_payload = payload.get(
            "profiles",
            [],
        )

        if not isinstance(
            profiles_payload,
            list,
        ):
            raise ValueError(
                "Dashboard profiles must be a list."
            )

        return validate_profiles(
            tuple(
                DashboardLayoutProfile.from_dict(
                    item
                )
                for item in profiles_payload
            )
        )

    def _quarantine_invalid_file(
        self,
    ):
        if not self.path.exists():
            return

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        quarantine_path = self.path.with_name(
            self.path.name
            + f".corrupt_{timestamp}"
        )

        try:
            os.replace(
                self.path,
                quarantine_path,
            )
        except OSError:
            pass
