"""Desktop Companion feature package."""

from src.companion.overlay import (
    ANIMATED_ASSET_SUFFIXES,
    STATIC_ASSET_SUFFIXES,
    CompanionOverlay,
)
from src.companion.preferences import (
    CompanionPreferences,
    CompanionPreferencesStore,
    default_companion_preferences,
    default_companion_preferences_path,
)

__all__ = [
    "ANIMATED_ASSET_SUFFIXES",
    "CompanionOverlay",
    "CompanionPreferences",
    "CompanionPreferencesStore",
    "STATIC_ASSET_SUFFIXES",
    "default_companion_preferences",
    "default_companion_preferences_path",
]