from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtCore import QSettings

from src.discord.presence_presets import (
    MAX_PRESETS as PRESENCE_PRESET_MAX_PRESETS,
    SCHEMA_VERSION as PRESENCE_PRESET_STORAGE_SCHEMA_VERSION,
    PresencePresetStore,
    preset_from_dict,
)
from src.artwork.cloudinary_preferences import (
    CloudinaryPreferences,
    CloudinaryPreferencesStore,
)
from src.music.source_preferences import (
    SourcePreferences,
    SourcePreferencesStore,
)
from src.system.afk_preferences import (
    AfkPreferences,
    AfkPreferencesStore,
)
from src.system.startup import StartupManager
from src.ui.custom_cards import (
    SCHEMA_VERSION as CUSTOM_CARD_STORAGE_SCHEMA_VERSION,
    CustomCardStore,
    LauncherCardData,
    custom_card_from_dict,
    validate_custom_cards,
)
from src.ui.dashboard_layout import (
    DashboardLayout,
    DashboardLayoutStore,
    is_custom_dashboard_card_id,
)
from src.ui.dashboard_profiles import (
    MAX_LAYOUT_PROFILES as DASHBOARD_LAYOUT_PROFILE_MAX_PROFILES,
    SCHEMA_VERSION as DASHBOARD_LAYOUT_PROFILE_STORAGE_SCHEMA_VERSION,
    DashboardLayoutProfile,
    DashboardLayoutProfileStore,
    validate_profiles,
)
from src.ui.theme import (
    ATMOSPHERE_RANGES,
    DEFAULT_ATMOSPHERE,
    DEFAULT_BRANDING,
    DEFAULT_THEME,
    THEME_PRESETS,
)

from src.system.media_hotkey_preferences import (
    MediaHotkeyPreferencesStore,
    media_hotkey_preferences_from_payload,
    media_hotkey_preferences_to_payload,
)


BACKUP_KIND = "0337am-presence-settings"
MEDIA_HOTKEY_BACKUP_INTRODUCED_SCHEMA_VERSION = 6
BACKUP_SCHEMA_VERSION = 6
MAX_BACKUP_BYTES = 1024 * 1024

_COLOUR_PATTERN = re.compile(
    r"^#[0-9a-fA-F]{6}$"
)


class SettingsBackupError(Exception):
    """Base error for settings backup operations."""


class SettingsBackupValidationError(
    SettingsBackupError
):
    """Raised when a backup file is unsafe or invalid."""


@dataclass(frozen=True)
class SettingsBackupPreview:
    created_at: str
    includes_artwork_hosting: bool
    includes_media_hotkeys: bool = False


@dataclass(frozen=True)
class SettingsRestoreResult:
    safety_backup_path: Path
    restored_artwork_hosting: bool
    restored_media_hotkeys: bool = False


class SettingsBackupManager:
    """
    Exports and restores the app's portable settings.

    Listening history, artwork caches, OAuth tokens,
    diagnostics, local file paths, custom sidebar
    images, and custom atmosphere backgrounds are
    deliberately excluded.
    """

    def __init__(
        self,
        settings: QSettings | None = None,
        source_store: SourcePreferencesStore | None = None,
        afk_store: AfkPreferencesStore | None = None,
        cloudinary_store: CloudinaryPreferencesStore | None = None,
        dashboard_store: DashboardLayoutStore | None = None,
        dashboard_profile_store: DashboardLayoutProfileStore | None = None,
        custom_card_store: CustomCardStore | None = None,
        presence_preset_store: PresencePresetStore | None = None,
        media_hotkey_store: MediaHotkeyPreferencesStore | None = None,
    ):
        self.settings = (
            settings
            or QSettings(
                "0337am",
                "Presence",
            )
        )

        self.source_store = (
            source_store
            or SourcePreferencesStore()
        )

        self.afk_store = (
            afk_store
            or AfkPreferencesStore()
        )

        self.cloudinary_store = (
            cloudinary_store
            or CloudinaryPreferencesStore()
        )

        self.dashboard_store = (
            dashboard_store
            or DashboardLayoutStore()
        )

        self.dashboard_profile_store = (
            dashboard_profile_store
            or DashboardLayoutProfileStore()
        )

        self.custom_card_store = (
            custom_card_store
            or CustomCardStore()
        )

        self.presence_preset_store = (
            presence_preset_store
            or PresencePresetStore()
        )

        self.media_hotkey_store = (
            media_hotkey_store
            or MediaHotkeyPreferencesStore()
        )

    @staticmethod
    def suggested_filename() -> str:
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        return (
            "03-37am-presence-settings-"
            f"{timestamp}.json"
        )

    def capture(
        self,
        include_artwork_hosting: bool = False,
    ) -> dict:
        source = self.source_store.load()
        afk = self.afk_store.load()
        cloudinary = self.cloudinary_store.load()
        dashboard = self.dashboard_store.load()
        dashboard_profiles = (
            self.dashboard_profile_store.load()
        )

        artwork_hosting = {
            "included": bool(
                include_artwork_hosting
            ),
        }

        if include_artwork_hosting:
            artwork_hosting.update(
                {
                    "enabled": bool(
                        cloudinary.enabled
                    ),
                    "cloud_name": (
                        cloudinary.cloud_name
                    ),
                    "upload_preset": (
                        cloudinary.upload_preset
                    ),
                }
            )

        contains_identifiers = bool(
            include_artwork_hosting
            and (
                cloudinary.cloud_name
                or cloudinary.upload_preset
            )
        )

        payload = {
            "kind": BACKUP_KIND,
            "schema_version": (
                BACKUP_SCHEMA_VERSION
            ),
            "created_at": (
                datetime.now(
                    timezone.utc
                )
                .isoformat(
                    timespec="seconds"
                )
            ),
            "privacy": {
                "contains_artwork_hosting_identifiers": (
                    contains_identifiers
                ),
                "excluded": [
                    "listening_history",
                    "artwork_cache",
                    "link_card_icon_cache",
                    "launcher_card_images",
                    "presence_preset_images",
                    "oauth_tokens",
                    "api_credentials",
                    "diagnostics",
                    "local_file_paths",
                    "custom_sidebar_image",
                    "custom_atmosphere_background",
                ],
            },
            "settings": {
                "theme": self._capture_theme(),
                "atmosphere": (
                    self._capture_atmosphere()
                ),
                "branding": (
                    self._capture_branding()
                ),
                "window": {
                    "show_yuno_portrait": (
                        self.settings.value(
                            "show_yuno_portrait",
                            True,
                            type=bool,
                        )
                    ),
                    "always_on_top": (
                        self.settings.value(
                            "always_on_top",
                            False,
                            type=bool,
                        )
                    ),
                    "start_minimized": (
                        self.settings.value(
                            "start_minimized",
                            True,
                            type=bool,
                        )
                    ),
                },
                "windows_startup": {
                    "enabled": bool(
                        StartupManager.is_enabled()
                    ),
                },
                "media_sources": {
                    "spotify_enabled": (
                        source.spotify_enabled
                    ),
                    "browser_enabled": (
                        source.browser_enabled
                    ),
                },
                "auto_afk": {
                    "enabled": afk.enabled,
                    "timeout_minutes": (
                        afk.timeout_minutes
                    ),
                },
                "media_hotkeys": (
                    self._capture_media_hotkeys()
                ),
                "dashboard_layout": (
                    dashboard.to_dict()
                ),
                "dashboard_layout_profiles": (
                    self._capture_dashboard_layout_profiles(
                        dashboard_profiles
                    )
                ),
                "custom_cards": (
                    self._capture_custom_cards()
                ),
                "presence_presets": (
                    self._capture_presence_presets()
                ),
                "artwork_hosting": (
                    artwork_hosting
                ),
            },
        }

        return self.validate_payload(
            payload
        )

    def export_backup(
        self,
        destination: Path | str,
        include_artwork_hosting: bool = False,
    ) -> Path:
        payload = self.capture(
            include_artwork_hosting=(
                include_artwork_hosting
            )
        )

        destination_path = Path(
            destination
        )

        if (
            destination_path.suffix.lower()
            != ".json"
        ):
            destination_path = (
                destination_path.with_suffix(
                    ".json"
                )
            )

        self._write_payload(
            destination_path,
            payload,
        )

        return destination_path

    def preview_backup(
        self,
        source: Path | str,
    ) -> SettingsBackupPreview:
        payload = self.read_backup(
            source
        )

        artwork_hosting = (
            payload["settings"][
                "artwork_hosting"
            ]
        )

        return SettingsBackupPreview(
            created_at=payload[
                "created_at"
            ],
            includes_artwork_hosting=bool(
                artwork_hosting[
                    "included"
                ]
            ),
            includes_media_hotkeys=bool(
                payload["settings"][
                    "media_hotkeys"
                ]["included"]
            ),
        )

    def restore_backup(
        self,
        source: Path | str,
    ) -> SettingsRestoreResult:
        payload = self.read_backup(
            source
        )

        current_payload = self.capture(
            include_artwork_hosting=True
        )

        safety_path = (
            self._automatic_backup_directory()
            / (
                "before_restore_"
                + datetime.now().strftime(
                    "%Y%m%d_%H%M%S_%f"
                )
                + ".json"
            )
        )

        self._write_payload(
            safety_path,
            current_payload,
        )

        try:
            self._apply_payload(
                payload
            )

        except Exception as error:
            rollback_error = None

            try:
                self._apply_payload(
                    current_payload
                )

            except Exception as caught:
                rollback_error = caught

            if rollback_error is not None:
                raise SettingsBackupError(
                    "The restore failed and the "
                    "automatic rollback also failed. "
                    "Your safety backup is stored at "
                    f"{safety_path}."
                ) from rollback_error

            raise SettingsBackupError(
                "The restore failed. Previous "
                "settings were restored automatically."
            ) from error

        return SettingsRestoreResult(
            safety_backup_path=safety_path,
            restored_artwork_hosting=bool(
                payload["settings"][
                    "artwork_hosting"
                ]["included"]
            ),
            restored_media_hotkeys=bool(
                payload["settings"][
                    "media_hotkeys"
                ]["included"]
            ),
        )

    def read_backup(
        self,
        source: Path | str,
    ) -> dict:
        source_path = Path(
            source
        )

        try:
            size = source_path.stat().st_size

        except OSError as error:
            raise SettingsBackupValidationError(
                "The backup file could not be read."
            ) from error

        if size <= 0:
            raise SettingsBackupValidationError(
                "The backup file is empty."
            )

        if size > MAX_BACKUP_BYTES:
            raise SettingsBackupValidationError(
                "The backup file is too large."
            )

        try:
            raw_text = source_path.read_text(
                encoding="utf-8"
            )

            payload = json.loads(
                raw_text
            )

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as error:
            raise SettingsBackupValidationError(
                "The selected file is not a valid "
                "03:37am Presence settings backup."
            ) from error

        return self.validate_payload(
            payload
        )

    @classmethod
    def validate_payload(
        cls,
        payload,
    ) -> dict:
        if not isinstance(
            payload,
            dict,
        ):
            raise SettingsBackupValidationError(
                "The backup must contain a JSON object."
            )

        if payload.get("kind") != BACKUP_KIND:
            raise SettingsBackupValidationError(
                "This file is not a 03:37am Presence "
                "settings backup."
            )

        schema_version = cls._require_integer(
            payload.get(
                "schema_version"
            ),
            "schema_version",
            minimum=1,
            maximum=BACKUP_SCHEMA_VERSION,
        )

        created_at = cls._require_text(
            payload.get(
                "created_at"
            ),
            "created_at",
            maximum_length=64,
            allow_empty=False,
        )

        settings = cls._require_object(
            payload.get(
                "settings"
            ),
            "settings",
        )

        theme = cls._validate_theme(
            settings.get(
                "theme"
            )
        )

        branding = cls._validate_branding(
            settings.get(
                "branding"
            )
        )

        atmosphere = cls._validate_atmosphere(
            settings.get(
                "atmosphere"
            )
        )

        window = cls._validate_window(
            settings.get(
                "window"
            )
        )

        windows_startup = (
            cls._validate_windows_startup(
                settings.get(
                    "windows_startup"
                )
            )
        )

        media_sources = (
            cls._validate_media_sources(
                settings.get(
                    "media_sources"
                )
            )
        )

        auto_afk = cls._validate_auto_afk(
            settings.get(
                "auto_afk"
            )
        )

        media_hotkeys = (
            cls._validate_media_hotkeys(
                settings.get(
                    "media_hotkeys"
                ),
                required=(
                    schema_version
                    >= MEDIA_HOTKEY_BACKUP_INTRODUCED_SCHEMA_VERSION
                ),
            )
        )

        dashboard_layout_payload = (
            cls._require_object(
                settings.get(
                    "dashboard_layout"
                ),
                "dashboard_layout",
            )
        )

        try:
            dashboard_layout = (
                DashboardLayout.from_dict(
                    dashboard_layout_payload
                )
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise SettingsBackupValidationError(
                "The dashboard layout in the "
                "backup is invalid."
            ) from error

        custom_cards = (
            cls._validate_custom_cards(
                settings.get(
                    "custom_cards"
                )
            )
        )

        dashboard_layout_profiles = (
            cls._validate_dashboard_layout_profiles(
                settings.get(
                    "dashboard_layout_profiles"
                )
            )
        )

        presence_presets = (
            cls._validate_presence_presets(
                settings.get(
                    "presence_presets"
                )
            )
        )

        cls._validate_custom_layout_membership(
            dashboard_layout,
            custom_cards,
        )

        for profile_payload in dashboard_layout_profiles[
            "profiles"
        ]:
            cls._validate_custom_layout_membership(
                DashboardLayout.from_dict(
                    profile_payload[
                        "layout"
                    ]
                ),
                custom_cards,
            )

        artwork_hosting = (
            cls._validate_artwork_hosting(
                settings.get(
                    "artwork_hosting"
                )
            )
        )

        return {
            "kind": BACKUP_KIND,
            "schema_version": (
                BACKUP_SCHEMA_VERSION
            ),
            "created_at": created_at,
            "privacy": {
                "contains_artwork_hosting_identifiers": (
                    bool(
                        artwork_hosting[
                            "included"
                        ]
                        and (
                            artwork_hosting.get(
                                "cloud_name"
                            )
                            or artwork_hosting.get(
                                "upload_preset"
                            )
                        )
                    )
                ),
                "excluded": [
                    "listening_history",
                    "artwork_cache",
                    "link_card_icon_cache",
                    "launcher_card_images",
                    "presence_preset_images",
                    "oauth_tokens",
                    "api_credentials",
                    "diagnostics",
                    "local_file_paths",
                    "custom_sidebar_image",
                    "custom_atmosphere_background",
                ],
            },
            "settings": {
                "theme": theme,
                "atmosphere": atmosphere,
                "branding": branding,
                "window": window,
                "windows_startup": (
                    windows_startup
                ),
                "media_sources": (
                    media_sources
                ),
                "auto_afk": auto_afk,
                "media_hotkeys": (
                    media_hotkeys
                ),
                "dashboard_layout": (
                    dashboard_layout.to_dict()
                ),
                "dashboard_layout_profiles": (
                    dashboard_layout_profiles
                ),
                "custom_cards": (
                    custom_cards
                ),
                "presence_presets": (
                    presence_presets
                ),
                "artwork_hosting": (
                    artwork_hosting
                ),
            },
        }

    def _capture_media_hotkeys(
        self,
    ) -> dict:
        return {
            "included": True,
            "preferences": (
                media_hotkey_preferences_to_payload(
                    self.media_hotkey_store.load()
                )
            ),
        }

    def _capture_dashboard_layout_profiles(
        self,
        profiles,
    ) -> dict:
        validated = validate_profiles(
            profiles
        )

        return {
            "schema_version": (
                DASHBOARD_LAYOUT_PROFILE_STORAGE_SCHEMA_VERSION
            ),
            "profiles": [
                profile.to_dict()
                for profile in validated
            ],
        }

    def _capture_custom_cards(
        self,
    ) -> dict:
        cards = self.custom_card_store.load()
        portable_cards = []

        for card in cards:
            data = card.to_dict()

            # Launcher targets and image assets are
            # device-local. They can contain private
            # file-system information or reference
            # files that are not exported.
            if isinstance(
                card,
                LauncherCardData,
            ):
                data["target"] = ""
                data["image_asset"] = ""

            portable_cards.append(data)

        return {
            "schema_version": (
                CUSTOM_CARD_STORAGE_SCHEMA_VERSION
            ),
            "cards": portable_cards,
        }


    def _capture_presence_presets(
        self,
    ) -> dict:
        presets = []

        for preset in self.presence_preset_store.load():
            data = preset.to_dict()

            # Presence preset image files and local image paths
            # are deliberately excluded from portable backups.
            data["image_path"] = ""
            presets.append(data)

        return {
            "schema_version": (
                PRESENCE_PRESET_STORAGE_SCHEMA_VERSION
            ),
            "images_included": False,
            "presets": presets,
        }

    def _capture_theme(self) -> dict:
        values = {}

        for key, default in (
            DEFAULT_THEME.items()
        ):
            if key == "compact":
                values[key] = (
                    self.settings.value(
                        f"theme/{key}",
                        default,
                        type=bool,
                    )
                )
            else:
                values[key] = str(
                    self.settings.value(
                        f"theme/{key}",
                        default,
                    )
                )

        if values.get("preset") == "Yuno":
            values["preset"] = "Custom"

        return values

    def _capture_atmosphere(self) -> dict:
        values = {
            "background_image_included": False,
            "enabled": self.settings.value(
                "atmosphere/enabled",
                DEFAULT_ATMOSPHERE["enabled"],
                type=bool,
            ),
        }

        for key in ATMOSPHERE_RANGES:
            values[key] = self.settings.value(
                f"atmosphere/{key}",
                DEFAULT_ATMOSPHERE[key],
            )

        return self._validate_atmosphere(
            values
        )

    def _capture_branding(self) -> dict:
        values = {}

        boolean_keys = {
            "show_title",
            "show_subtitle",
            "show_footer",
        }

        for key, default in (
            DEFAULT_BRANDING.items()
        ):
            if key == "image_path":
                continue

            if key == "footer":
                values[key] = default
                continue

            if key in boolean_keys:
                values[key] = (
                    self.settings.value(
                        f"branding/{key}",
                        default,
                        type=bool,
                    )
                )
            else:
                values[key] = str(
                    self.settings.value(
                        f"branding/{key}",
                        default,
                    )
                    or ""
                )

        return values

    def _apply_payload(
        self,
        payload: dict,
    ):
        normalized = self.validate_payload(
            payload
        )

        settings = normalized[
            "settings"
        ]

        for key, value in (
            settings["theme"].items()
        ):
            self.settings.setValue(
                f"theme/{key}",
                value,
            )

        for key, value in (
            settings["branding"].items()
        ):
            if key == "footer":
                self.settings.remove(
                    "branding/footer"
                )
                continue

            self.settings.setValue(
                f"branding/{key}",
                value,
            )

        # Atmosphere background images are local-only and
        # are deliberately not exported. Restore visual
        # tuning, but clear the image path and leave the
        # feature disabled until the user chooses a new
        # background on this device.
        for key in ATMOSPHERE_RANGES:
            self.settings.setValue(
                f"atmosphere/{key}",
                settings["atmosphere"][key],
            )

        self.settings.setValue(
            "atmosphere/image_path",
            "",
        )
        self.settings.setValue(
            "atmosphere/enabled",
            False,
        )

        for key, value in (
            settings["window"].items()
        ):
            self.settings.setValue(
                key,
                value,
            )

        self.settings.sync()

        if (
            self.settings.status()
            != QSettings.Status.NoError
        ):
            raise OSError(
                "Qt settings could not be saved."
            )

        self.source_store.save(
            SourcePreferences(
                spotify_enabled=(
                    settings[
                        "media_sources"
                    ]["spotify_enabled"]
                ),
                browser_enabled=(
                    settings[
                        "media_sources"
                    ]["browser_enabled"]
                ),
            )
        )

        self.afk_store.save(
            AfkPreferences(
                enabled=(
                    settings[
                        "auto_afk"
                    ]["enabled"]
                ),
                timeout_minutes=(
                    settings[
                        "auto_afk"
                    ]["timeout_minutes"]
                ),
            )
        )

        media_hotkeys = (
            settings[
                "media_hotkeys"
            ]
        )

        if media_hotkeys[
            "included"
        ]:
            self.media_hotkey_store.save(
                media_hotkey_preferences_from_payload(
                    media_hotkeys[
                        "preferences"
                    ]
                )
            )

        custom_cards = tuple(
            custom_card_from_dict(
                item
            )
            for item in settings[
                "custom_cards"
            ]["cards"]
        )

        self.custom_card_store.save(
            custom_cards
        )

        presence_presets = tuple(
            preset_from_dict(
                item
            )
            for item in settings[
                "presence_presets"
            ]["presets"]
        )

        self.presence_preset_store.save(
            presence_presets
        )

        self.dashboard_store.save(
            DashboardLayout.from_dict(
                settings[
                    "dashboard_layout"
                ]
            )
        )

        dashboard_profiles = tuple(
            DashboardLayoutProfile.from_dict(
                item
            )
            for item in settings[
                "dashboard_layout_profiles"
            ]["profiles"]
        )

        self.dashboard_profile_store.save(
            dashboard_profiles
        )

        artwork_hosting = (
            settings[
                "artwork_hosting"
            ]
        )

        if artwork_hosting[
            "included"
        ]:
            self.cloudinary_store.save(
                CloudinaryPreferences(
                    enabled=(
                        artwork_hosting[
                            "enabled"
                        ]
                    ),
                    cloud_name=(
                        artwork_hosting[
                            "cloud_name"
                        ]
                    ),
                    upload_preset=(
                        artwork_hosting[
                            "upload_preset"
                        ]
                    ),
                )
            )

        startup_ok = (
            StartupManager.set_enabled(
                settings[
                    "windows_startup"
                ]["enabled"],
                settings[
                    "window"
                ]["start_minimized"],
            )
        )

        if not startup_ok:
            raise OSError(
                "Windows startup settings could "
                "not be restored."
            )

    def _automatic_backup_directory(
        self,
    ) -> Path:
        directory = (
            self.dashboard_store
            .path
            .parent
            / "settings_restore_backups"
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return directory

    @classmethod
    def _write_payload(
        cls,
        destination: Path,
        payload: dict,
    ):
        normalized = cls.validate_payload(
            payload
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = (
            destination.with_name(
                destination.name
                + ".tmp"
            )
        )

        text = json.dumps(
            normalized,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )

        encoded_size = len(
            text.encode(
                "utf-8"
            )
        )

        if encoded_size > MAX_BACKUP_BYTES:
            raise SettingsBackupError(
                "The settings backup is too large."
            )

        try:
            with temporary_path.open(
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write(
                    text
                )
                handle.write(
                    "\n"
                )
                handle.flush()
                os.fsync(
                    handle.fileno()
                )

            verification = json.loads(
                temporary_path.read_text(
                    encoding="utf-8"
                )
            )

            cls.validate_payload(
                verification
            )

            os.replace(
                temporary_path,
                destination,
            )

        except Exception:
            temporary_path.unlink(
                missing_ok=True
            )
            raise

    @classmethod
    def _validate_atmosphere(
        cls,
        payload,
    ) -> dict:
        if payload is None:
            payload = {}

        payload = cls._require_object(
            payload,
            "atmosphere",
        )

        enabled = payload.get(
            "enabled",
            DEFAULT_ATMOSPHERE["enabled"],
        )

        if not isinstance(
            enabled,
            bool,
        ):
            raise SettingsBackupValidationError(
                "Atmosphere enabled must be true or false."
            )

        background_image_included = payload.get(
            "background_image_included",
            False,
        )

        if background_image_included is not False:
            raise SettingsBackupValidationError(
                "Atmosphere background images are not "
                "supported in portable backups."
            )

        if "image_path" in payload:
            raise SettingsBackupValidationError(
                "Atmosphere image paths are not "
                "allowed in portable backups."
            )

        values = {
            "enabled": enabled,
            "background_image_included": False,
        }

        for key, (
            minimum,
            maximum,
        ) in ATMOSPHERE_RANGES.items():
            values[key] = cls._require_integer(
                payload.get(
                    key,
                    DEFAULT_ATMOSPHERE[key],
                ),
                f"atmosphere.{key}",
                minimum=minimum,
                maximum=maximum,
            )

        return values


    @classmethod
    def _validate_theme(
        cls,
        payload,
    ) -> dict:
        data = cls._require_object(
            payload,
            "theme",
        )

        preset = cls._require_text(
            data.get("preset"),
            "theme.preset",
            maximum_length=40,
            allow_empty=False,
        )

        if preset == "Yuno":
            preset = "Custom"

        if (
            preset not in THEME_PRESETS
            and preset != "Custom"
        ):
            raise SettingsBackupValidationError(
                "The theme preset is invalid."
            )

        normalized = {
            "preset": preset,
        }

        for key in (
            "background",
            "sidebar",
            "card",
            "card_alt",
            "accent",
            "text",
            "muted",
            "border",
        ):
            colour = cls._require_text(
                data.get(key),
                f"theme.{key}",
                maximum_length=7,
                allow_empty=False,
            )

            if not _COLOUR_PATTERN.fullmatch(
                colour
            ):
                raise SettingsBackupValidationError(
                    f"The theme colour '{key}' "
                    "is invalid."
                )

            normalized[key] = (
                colour.lower()
            )

        normalized["compact"] = (
            cls._require_boolean(
                data.get(
                    "compact"
                ),
                "theme.compact",
            )
        )

        return normalized

    @classmethod
    def _validate_branding(
        cls,
        payload,
    ) -> dict:
        data = cls._require_object(
            payload,
            "branding",
        )

        normalized = {}

        for key in (
            "title",
            "subtitle",
        ):
            normalized[key] = (
                cls._require_text(
                    data.get(key),
                    f"branding.{key}",
                    maximum_length=80,
                    allow_empty=True,
                )
            )

        # Schema v1 backups include a footer field.
        # Validate it for compatibility, then replace it
        # with the fixed product copy so restores cannot
        # customise the About-page thank-you text.
        cls._require_text(
            data.get("footer"),
            "branding.footer",
            maximum_length=80,
            allow_empty=True,
        )

        normalized["footer"] = (
            DEFAULT_BRANDING["footer"]
        )

        for key in (
            "show_title",
            "show_subtitle",
            "show_footer",
        ):
            normalized[key] = (
                cls._require_boolean(
                    data.get(key),
                    f"branding.{key}",
                )
            )

        return normalized

    @classmethod
    def _validate_window(
        cls,
        payload,
    ) -> dict:
        data = cls._require_object(
            payload,
            "window",
        )

        return {
            key: cls._require_boolean(
                data.get(key),
                f"window.{key}",
            )
            for key in (
                "show_yuno_portrait",
                "always_on_top",
                "start_minimized",
            )
        }

    @classmethod
    def _validate_windows_startup(
        cls,
        payload,
    ) -> dict:
        data = cls._require_object(
            payload,
            "windows_startup",
        )

        return {
            "enabled": cls._require_boolean(
                data.get("enabled"),
                "windows_startup.enabled",
            )
        }

    @classmethod
    def _validate_media_sources(
        cls,
        payload,
    ) -> dict:
        data = cls._require_object(
            payload,
            "media_sources",
        )

        return {
            "spotify_enabled": (
                cls._require_boolean(
                    data.get(
                        "spotify_enabled"
                    ),
                    "media_sources.spotify_enabled",
                )
            ),
            "browser_enabled": (
                cls._require_boolean(
                    data.get(
                        "browser_enabled"
                    ),
                    "media_sources.browser_enabled",
                )
            ),
        }

    @classmethod
    def _validate_auto_afk(
        cls,
        payload,
    ) -> dict:
        data = cls._require_object(
            payload,
            "auto_afk",
        )

        return {
            "enabled": cls._require_boolean(
                data.get("enabled"),
                "auto_afk.enabled",
            ),
            "timeout_minutes": (
                cls._require_integer(
                    data.get(
                        "timeout_minutes"
                    ),
                    "auto_afk.timeout_minutes",
                    minimum=1,
                    maximum=240,
                )
            ),
        }

    @classmethod
    def _validate_media_hotkeys(
        cls,
        value,
        *,
        required: bool = False,
    ) -> dict:
        if value is None:
            if required:
                raise SettingsBackupValidationError(
                    "This settings backup is missing "
                    "its global media hotkey settings."
                )

            return {
                "included": False,
            }

        data = cls._require_object(
            value,
            "media_hotkeys",
        )

        included = cls._require_boolean(
            data.get(
                "included"
            ),
            "media_hotkeys.included",
        )

        if not included:
            return {
                "included": False,
            }

        preferences_payload = (
            data.get(
                "preferences"
            )
        )

        try:
            preferences = (
                media_hotkey_preferences_from_payload(
                    preferences_payload
                )
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise SettingsBackupValidationError(
                "The global media hotkeys "
                "in the backup are invalid."
            ) from error

        return {
            "included": True,
            "preferences": (
                media_hotkey_preferences_to_payload(
                    preferences
                )
            ),
        }

    @classmethod
    def _validate_custom_cards(
        cls,
        value,
    ) -> dict:
        if value is None:
            value = {
                "schema_version": (
                    CUSTOM_CARD_STORAGE_SCHEMA_VERSION
                ),
                "cards": [],
            }

        payload = cls._require_object(
            value,
            "custom_cards",
        )

        schema_version = cls._require_integer(
            payload.get(
                "schema_version"
            ),
            "custom_cards.schema_version",
            minimum=1,
            maximum=(
                CUSTOM_CARD_STORAGE_SCHEMA_VERSION
            ),
        )

        # Earlier schemas remain valid and are
        # normalised to the current version.
        cards_payload = payload.get(
            "cards",
            [],
        )

        if not isinstance(
            cards_payload,
            list,
        ):
            raise SettingsBackupValidationError(
                "Custom cards must be a list."
            )

        try:
            cards = validate_custom_cards(
                tuple(
                    custom_card_from_dict(
                        item
                    )
                    for item in cards_payload
                )
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise SettingsBackupValidationError(
                "The custom cards in the "
                "backup are invalid."
            ) from error

        for card in cards:
            if not isinstance(
                card,
                LauncherCardData,
            ):
                continue

            if card.target:
                raise SettingsBackupValidationError(
                    "Launcher card target paths "
                    "are local-only and cannot "
                    "be restored from a settings "
                    "backup."
                )

            if card.image_asset:
                raise SettingsBackupValidationError(
                    "Launcher card images are "
                    "local-only and cannot be "
                    "restored from a settings "
                    "backup."
                )

        return {
            "schema_version": (
                CUSTOM_CARD_STORAGE_SCHEMA_VERSION
            ),
            "cards": [
                card.to_dict()
                for card in cards
            ],
        }


    @classmethod
    def _validate_presence_presets(
        cls,
        value,
    ) -> dict:
        if value is None:
            value = {
                "schema_version": (
                    PRESENCE_PRESET_STORAGE_SCHEMA_VERSION
                ),
                "images_included": False,
                "presets": [],
            }

        payload = cls._require_object(
            value,
            "presence_presets",
        )

        schema_version = cls._require_integer(
            payload.get(
                "schema_version"
            ),
            "presence_presets.schema_version",
            minimum=1,
            maximum=PRESENCE_PRESET_STORAGE_SCHEMA_VERSION,
        )

        if (
            schema_version
            != PRESENCE_PRESET_STORAGE_SCHEMA_VERSION
        ):
            raise SettingsBackupValidationError(
                "The presence preset backup "
                "version is not supported."
            )

        if "images_included" in payload:
            images_included = cls._require_boolean(
                payload.get("images_included"),
                "presence_presets.images_included",
            )
        else:
            images_included = False

        if images_included:
            raise SettingsBackupValidationError(
                "Presence preset image backups are "
                "not supported yet."
            )

        presets_payload = payload.get(
            "presets",
            [],
        )

        if not isinstance(
            presets_payload,
            list,
        ):
            raise SettingsBackupValidationError(
                "Presence presets must be a list."
            )

        if len(presets_payload) > PRESENCE_PRESET_MAX_PRESETS:
            raise SettingsBackupValidationError(
                "The backup contains too many "
                "presence presets."
            )

        presets = []

        try:
            for item in presets_payload:
                if not isinstance(item, dict):
                    raise TypeError(
                        "Presence preset entries "
                        "must be objects."
                    )

                if str(
                    item.get(
                        "image_path",
                        "",
                    )
                    or ""
                ).strip():
                    raise ValueError(
                        "Presence preset backups "
                        "cannot contain local "
                        "image paths."
                    )

                safe_item = dict(item)
                safe_item["image_path"] = ""
                presets.append(
                    preset_from_dict(
                        safe_item
                    )
                )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise SettingsBackupValidationError(
                "The presence presets in the "
                "backup are invalid."
            ) from error

        return {
            "schema_version": (
                PRESENCE_PRESET_STORAGE_SCHEMA_VERSION
            ),
            "images_included": False,
            "presets": [
                preset.to_dict()
                for preset in presets
            ],
        }

    @classmethod
    def _validate_dashboard_layout_profiles(
        cls,
        value,
    ) -> dict:
        if value is None:
            value = {
                "schema_version": (
                    DASHBOARD_LAYOUT_PROFILE_STORAGE_SCHEMA_VERSION
                ),
                "profiles": [],
            }

        payload = cls._require_object(
            value,
            "dashboard_layout_profiles",
        )

        schema_version = cls._require_integer(
            payload.get(
                "schema_version"
            ),
            "dashboard_layout_profiles.schema_version",
            minimum=1,
            maximum=DASHBOARD_LAYOUT_PROFILE_STORAGE_SCHEMA_VERSION,
        )

        if (
            schema_version
            != DASHBOARD_LAYOUT_PROFILE_STORAGE_SCHEMA_VERSION
        ):
            raise SettingsBackupValidationError(
                "The dashboard layout profile "
                "backup version is not supported."
            )

        profiles_payload = payload.get(
            "profiles",
            [],
        )

        if not isinstance(
            profiles_payload,
            list,
        ):
            raise SettingsBackupValidationError(
                "Dashboard layout profiles must be a list."
            )

        if len(profiles_payload) > DASHBOARD_LAYOUT_PROFILE_MAX_PROFILES:
            raise SettingsBackupValidationError(
                "The backup contains too many "
                "dashboard layout profiles."
            )

        try:
            profiles = validate_profiles(
                tuple(
                    DashboardLayoutProfile.from_dict(
                        item
                    )
                    for item in profiles_payload
                )
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise SettingsBackupValidationError(
                "The dashboard layout profiles in "
                "the backup are invalid."
            ) from error

        return {
            "schema_version": (
                DASHBOARD_LAYOUT_PROFILE_STORAGE_SCHEMA_VERSION
            ),
            "profiles": [
                profile.to_dict()
                for profile in profiles
            ],
        }

    @classmethod
    def _validate_custom_layout_membership(
        cls,
        dashboard_layout: DashboardLayout,
        custom_cards: dict,
    ):
        card_ids = {
            str(
                card.get(
                    "id",
                    "",
                )
            )
            for card in custom_cards[
                "cards"
            ]
        }

        orphan_layout_ids = [
            card.card_id
            for card in dashboard_layout.cards
            if (
                is_custom_dashboard_card_id(
                    card.card_id
                )
                and card.card_id not in card_ids
            )
        ]

        if orphan_layout_ids:
            raise SettingsBackupValidationError(
                "The backup has custom-card layout "
                "entries without matching Link cards."
            )

    @classmethod
    def _validate_artwork_hosting(
        cls,
        payload,
    ) -> dict:
        data = cls._require_object(
            payload,
            "artwork_hosting",
        )

        included = cls._require_boolean(
            data.get("included"),
            "artwork_hosting.included",
        )

        if not included:
            return {
                "included": False,
            }

        enabled = cls._require_boolean(
            data.get("enabled"),
            "artwork_hosting.enabled",
        )

        cloud_name = cls._require_text(
            data.get("cloud_name"),
            "artwork_hosting.cloud_name",
            maximum_length=128,
            allow_empty=True,
        )

        upload_preset = cls._require_text(
            data.get(
                "upload_preset"
            ),
            "artwork_hosting.upload_preset",
            maximum_length=255,
            allow_empty=True,
        )

        if (
            enabled
            and (
                not cloud_name
                or not upload_preset
            )
        ):
            raise SettingsBackupValidationError(
                "Artwork hosting cannot be enabled "
                "without both account fields."
            )

        return {
            "included": True,
            "enabled": enabled,
            "cloud_name": cloud_name,
            "upload_preset": upload_preset,
        }

    @staticmethod
    def _require_object(
        value,
        name: str,
    ) -> dict:
        if not isinstance(
            value,
            dict,
        ):
            raise SettingsBackupValidationError(
                f"'{name}' must be a JSON object."
            )

        return value

    @staticmethod
    def _require_boolean(
        value,
        name: str,
    ) -> bool:
        if not isinstance(
            value,
            bool,
        ):
            raise SettingsBackupValidationError(
                f"'{name}' must be true or false."
            )

        return value

    @staticmethod
    def _require_integer(
        value,
        name: str,
        minimum: int,
        maximum: int,
    ) -> int:
        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                int,
            )
            or value < minimum
            or value > maximum
        ):
            raise SettingsBackupValidationError(
                f"'{name}' must be an integer "
                f"between {minimum} and {maximum}."
            )

        return value

    @staticmethod
    def _require_text(
        value,
        name: str,
        maximum_length: int,
        allow_empty: bool,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise SettingsBackupValidationError(
                f"'{name}' must be text."
            )

        if (
            not allow_empty
            and not value
        ):
            raise SettingsBackupValidationError(
                f"'{name}' cannot be empty."
            )

        if len(value) > maximum_length:
            raise SettingsBackupValidationError(
                f"'{name}' is too long."
            )

        if any(
            ord(character) < 32
            or ord(character) == 127
            for character in value
        ):
            raise SettingsBackupValidationError(
                f"'{name}' contains invalid characters."
            )

        return value
