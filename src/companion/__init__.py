"""Desktop Companion feature package."""

from src.companion.overlay import (
    CompanionOverlay,
    STATIC_ASSET_SUFFIXES,
)
from src.companion.preferences import (
    CompanionPreferences,
    CompanionPreferencesStore,
    default_companion_preferences,
    default_companion_preferences_path,
)

__all__ = [
    "CompanionOverlay",
    "CompanionPreferences",
    "CompanionPreferencesStore",
    "STATIC_ASSET_SUFFIXES",
    "default_companion_preferences",
    "default_companion_preferences_path",
]