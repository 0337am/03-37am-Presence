from __future__ import annotations

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY_ID,
    DiscordApplicationEntry,
    DiscordApplicationLibraryError,
    is_valid_user_entry_id,
)
from src.discord.identity_preferences import (
    IDENTITY_MODE_CUSTOM,
    DiscordIdentityPreferences,
)


def migrate_legacy_discord_identity_to_library(
    preferences: DiscordIdentityPreferences,
    application_library_store,
) -> DiscordApplicationEntry | None:
    """
    Preserve a pre-v3.4 custom Discord Application ID
    inside the v3.4 Application Library.

    Migration is intentionally non-destructive:
    - legacy identity preference values are not changed;
    - the currently active Discord identity is not changed;
    - an inactive-but-retained custom ID is still preserved;
    - migration failure must never block application startup.
    """

    if not isinstance(
        preferences,
        DiscordIdentityPreferences,
    ):
        raise TypeError(
            "preferences must be a "
            "DiscordIdentityPreferences instance."
        )

    migrate = getattr(
        application_library_store,
        "migrate_legacy_application_id",
        None,
    )

    if not callable(migrate):
        raise TypeError(
            "application_library_store must expose "
            "migrate_legacy_application_id()."
        )

    legacy_application_id = str(
        preferences.custom_application_id
        or ""
    ).strip()

    if not legacy_application_id:
        return None

    try:
        migrated = migrate(
            legacy_application_id
        )
    except (
        DiscordApplicationLibraryError,
        OSError,
    ):
        return None

    if (
        migrated is not None
        and not isinstance(
            migrated,
            DiscordApplicationEntry,
        )
    ):
        return None

    return migrated


LEGACY_ASSIGNABLE_PRESENCE_MODES = (
    "music",
    "afk",
    "sleep",
    "working",
    "custom",
)


def migrate_legacy_discord_identity_to_presence_assignments(
    preferences: DiscordIdentityPreferences,
    migrated_application: DiscordApplicationEntry | None,
    presence_settings_store,
) -> tuple[str, ...]:
    """
    Fill missing per-Presence application assignments from an
    actively selected pre-v3.4 global custom Discord identity.

    This bridge is deliberately non-destructive:
    - inactive retained custom IDs remain library-only;
    - an existing per-mode assignment is never overwritten;
    - Disabled never receives an application assignment;
    - legacy identity preferences are never modified;
    - Discord RPC identity/lifecycle is never modified;
    - storage failures must not block application startup.
    """

    if not isinstance(
        preferences,
        DiscordIdentityPreferences,
    ):
        raise TypeError(
            "preferences must be a "
            "DiscordIdentityPreferences instance."
        )

    if migrated_application is None:
        return ()

    if not isinstance(
        migrated_application,
        DiscordApplicationEntry,
    ):
        return ()

    if (
        preferences.normalized_mode
        != IDENTITY_MODE_CUSTOM
    ):
        return ()

    entry_id = str(
        migrated_application.entry_id
        or ""
    ).strip()

    if (
        entry_id
        != BUILTIN_APPLICATION_ENTRY_ID
        and not is_valid_user_entry_id(
            entry_id
        )
    ):
        return ()

    contains = getattr(
        presence_settings_store,
        "contains",
        None,
    )

    set_value = getattr(
        presence_settings_store,
        "setValue",
        None,
    )

    sync = getattr(
        presence_settings_store,
        "sync",
        None,
    )

    if not callable(contains):
        raise TypeError(
            "presence_settings_store must expose "
            "contains()."
        )

    if not callable(set_value):
        raise TypeError(
            "presence_settings_store must expose "
            "setValue()."
        )

    if not callable(sync):
        raise TypeError(
            "presence_settings_store must expose "
            "sync()."
        )

    migrated_modes = []

    for mode in LEGACY_ASSIGNABLE_PRESENCE_MODES:
        key = (
            f"presence/{mode}/"
            "application_entry_id"
        )

        try:
            already_assigned = bool(
                contains(key)
            )
        except (
            OSError,
            RuntimeError,
        ):
            return tuple(
                migrated_modes
            )

        if already_assigned:
            continue

        try:
            set_value(
                key,
                entry_id,
            )
        except (
            OSError,
            RuntimeError,
        ):
            return tuple(
                migrated_modes
            )

        migrated_modes.append(
            mode
        )

    if migrated_modes:
        try:
            sync()
        except (
            OSError,
            RuntimeError,
        ):
            pass

    return tuple(
        migrated_modes
    )
