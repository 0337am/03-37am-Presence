from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QSettings


DEFAULT_DISCORD_APPLICATION_ID = (
    "1523801127962022070"
)

IDENTITY_MODE_DEFAULT = "default"
IDENTITY_MODE_CUSTOM = "custom"

VALID_IDENTITY_MODES = frozenset(
    {
        IDENTITY_MODE_DEFAULT,
        IDENTITY_MODE_CUSTOM,
    }
)

APPLICATION_ID_MIN_LENGTH = 15
APPLICATION_ID_MAX_LENGTH = 22

MODE_SETTING_KEY = (
    "discord_identity/mode"
)

CUSTOM_APPLICATION_ID_SETTING_KEY = (
    "discord_identity/custom_application_id"
)


def validate_discord_application_id(
    value,
) -> str:
    application_id = str(
        value or ""
    ).strip()

    if not application_id:
        raise ValueError(
            "Discord Application ID cannot be empty."
        )

    if not application_id.isascii():
        raise ValueError(
            "Discord Application ID must use ASCII digits."
        )

    if not application_id.isdigit():
        raise ValueError(
            "Discord Application ID must contain digits only."
        )

    if not (
        APPLICATION_ID_MIN_LENGTH
        <= len(application_id)
        <= APPLICATION_ID_MAX_LENGTH
    ):
        raise ValueError(
            "Discord Application ID must contain "
            f"{APPLICATION_ID_MIN_LENGTH} to "
            f"{APPLICATION_ID_MAX_LENGTH} digits."
        )

    return application_id


def safe_discord_application_id(
    value,
) -> str:
    try:
        return validate_discord_application_id(
            value
        )
    except (TypeError, ValueError):
        return DEFAULT_DISCORD_APPLICATION_ID


def normalize_identity_mode(
    value,
) -> str:
    mode = str(
        value or ""
    ).strip().lower()

    if mode not in VALID_IDENTITY_MODES:
        return IDENTITY_MODE_DEFAULT

    return mode


@dataclass(frozen=True)
class DiscordIdentityPreferences:
    mode: str = IDENTITY_MODE_DEFAULT
    custom_application_id: str = ""

    @property
    def normalized_mode(self) -> str:
        return normalize_identity_mode(
            self.mode
        )

    @property
    def resolved_application_id(self) -> str:
        if (
            self.normalized_mode
            != IDENTITY_MODE_CUSTOM
        ):
            return (
                DEFAULT_DISCORD_APPLICATION_ID
            )

        return safe_discord_application_id(
            self.custom_application_id
        )

    @property
    def is_custom(self) -> bool:
        return (
            self.normalized_mode
            == IDENTITY_MODE_CUSTOM
            and self.resolved_application_id
            != DEFAULT_DISCORD_APPLICATION_ID
        )


class DiscordIdentityPreferencesStore:
    """
    Stores the non-secret Discord Rich Presence identity.

    Only the public Discord Application ID is stored.
    Client secrets, bot tokens, and user tokens are never
    part of this preference model.
    """

    def __init__(
        self,
        settings: QSettings | None = None,
    ):
        self.settings = (
            settings
            if settings is not None
            else QSettings(
                "0337am",
                "Presence",
            )
        )

    def load(
        self,
    ) -> DiscordIdentityPreferences:
        mode = normalize_identity_mode(
            self.settings.value(
                MODE_SETTING_KEY,
                IDENTITY_MODE_DEFAULT,
            )
        )

        raw_custom_id = str(
            self.settings.value(
                CUSTOM_APPLICATION_ID_SETTING_KEY,
                "",
            )
            or ""
        ).strip()

        if raw_custom_id:
            try:
                custom_application_id = (
                    validate_discord_application_id(
                        raw_custom_id
                    )
                )
            except ValueError:
                custom_application_id = ""
        else:
            custom_application_id = ""

        if (
            mode == IDENTITY_MODE_CUSTOM
            and not custom_application_id
        ):
            mode = IDENTITY_MODE_DEFAULT

        return DiscordIdentityPreferences(
            mode=mode,
            custom_application_id=(
                custom_application_id
            ),
        )

    def save(
        self,
        preferences: DiscordIdentityPreferences,
    ) -> DiscordIdentityPreferences:
        if not isinstance(
            preferences,
            DiscordIdentityPreferences,
        ):
            raise TypeError(
                "preferences must be a "
                "DiscordIdentityPreferences instance."
            )

        mode = normalize_identity_mode(
            preferences.mode
        )

        raw_custom_id = str(
            preferences.custom_application_id
            or ""
        ).strip()

        if raw_custom_id:
            custom_application_id = (
                validate_discord_application_id(
                    raw_custom_id
                )
            )
        else:
            custom_application_id = ""

        if (
            mode == IDENTITY_MODE_CUSTOM
            and not custom_application_id
        ):
            raise ValueError(
                "Custom Discord identity requires "
                "an Application ID."
            )

        safe_preferences = (
            DiscordIdentityPreferences(
                mode=mode,
                custom_application_id=(
                    custom_application_id
                ),
            )
        )

        self.settings.setValue(
            MODE_SETTING_KEY,
            safe_preferences.mode,
        )

        self.settings.setValue(
            CUSTOM_APPLICATION_ID_SETTING_KEY,
            safe_preferences.custom_application_id,
        )

        self.settings.sync()

        if (
            self.settings.status()
            != QSettings.Status.NoError
        ):
            raise OSError(
                "Discord identity preferences "
                "could not be saved."
            )

        return safe_preferences

    def update(
        self,
        *,
        mode: str | None = None,
        custom_application_id: str | None = None,
    ) -> DiscordIdentityPreferences:
        current = self.load()

        updated = DiscordIdentityPreferences(
            mode=(
                current.mode
                if mode is None
                else mode
            ),
            custom_application_id=(
                current.custom_application_id
                if custom_application_id is None
                else custom_application_id
            ),
        )

        return self.save(
            updated
        )

    def reset(
        self,
    ) -> DiscordIdentityPreferences:
        return self.save(
            DiscordIdentityPreferences()
        )
