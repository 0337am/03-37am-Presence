from __future__ import annotations

from src.discord.application_library import (
    DiscordApplicationEntry,
    DiscordApplicationLibraryError,
)
from src.discord.identity_preferences import (
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
