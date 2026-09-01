"""Desktop Companion feature package."""

from src.companion.preferences import (
    CompanionPreferences,
    CompanionPreferencesStore,
    default_companion_preferences,
    default_companion_preferences_path,
)

__all__ = [
    "CompanionPreferences",
    "CompanionPreferencesStore",
    "default_companion_preferences",
    "default_companion_preferences_path",
]