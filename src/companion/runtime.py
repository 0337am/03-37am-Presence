from __future__ import annotations

from dataclasses import replace
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from src.companion.fullscreen import (
    CompanionFullscreenController,
)
from src.companion.overlay import (
    CompanionOverlay,
)
from src.companion.preferences import (
    CompanionPreferences,
    CompanionPreferencesStore,
)


class CompanionRuntime(QObject):
    """
    Own the production Desktop Companion lifecycle.

    The runtime owns preferences, the independent overlay,
    fullscreen policy, live preference application,
    drag-position persistence, and clean shutdown.
    """

    preferences_changed = pyqtSignal(
        object
    )

    def __init__(
        self,
        *,
        store=None,
        overlay=None,
        fullscreen_controller=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(
            parent
        )

        self.store = (
            store
            if store is not None
            else CompanionPreferencesStore()
        )

        self.overlay = (
            overlay
            if overlay is not None
            else CompanionOverlay()
        )

        self.fullscreen_controller = (
            fullscreen_controller
            if fullscreen_controller is not None
            else CompanionFullscreenController(
                self.overlay,
                parent=self,
            )
        )

        self._preferences = (
            CompanionPreferences()
        )

        self._last_error = ""
        self._shutdown = False

        position_signal = getattr(
            self.overlay,
            "position_changed",
            None,
        )

        if (
            position_signal is None
            or not hasattr(
                position_signal,
                "connect",
            )
        ):
            raise TypeError(
                "overlay must expose position_changed."
            )

        if not hasattr(
            self.overlay,
            "apply_preferences",
        ):
            raise TypeError(
                "overlay must provide apply_preferences()."
            )

        if not hasattr(
            self.overlay,
            "close",
        ):
            raise TypeError(
                "overlay must provide close()."
            )

        if not hasattr(
            self.fullscreen_controller,
            "set_enabled",
        ):
            raise TypeError(
                "fullscreen_controller must provide "
                "set_enabled()."
            )

        if not hasattr(
            self.fullscreen_controller,
            "stop",
        ):
            raise TypeError(
                "fullscreen_controller must provide stop()."
            )

        self.overlay.position_changed.connect(
            self._handle_position_changed
        )

        self.refresh()

    @property
    def preferences(
        self,
    ) -> CompanionPreferences:
        return self._preferences

    @property
    def last_error(
        self,
    ) -> str:
        return self._last_error

    @property
    def is_shutdown(
        self,
    ) -> bool:
        return self._shutdown

    def refresh(
        self,
    ) -> CompanionPreferences:
        self._ensure_active()

        preferences = self.store.load()

        if not isinstance(
            preferences,
            CompanionPreferences,
        ):
            raise TypeError(
                "Companion store returned invalid preferences."
            )

        self._apply_preferences(
            preferences
        )

        return preferences

    def update_preferences(
        self,
        **changes: Any,
    ) -> CompanionPreferences:
        self._ensure_active()

        preferences = self.store.update(
            **changes
        )

        if not isinstance(
            preferences,
            CompanionPreferences,
        ):
            raise TypeError(
                "Companion store returned invalid preferences."
            )

        self._apply_preferences(
            preferences
        )

        return preferences

    def shutdown(
        self,
    ) -> None:
        if self._shutdown:
            return

        self._shutdown = True

        try:
            self.fullscreen_controller.stop()
        finally:
            position_signal = getattr(
                self.overlay,
                "position_changed",
                None,
            )

            if (
                position_signal is not None
                and hasattr(
                    position_signal,
                    "disconnect",
                )
            ):
                try:
                    position_signal.disconnect(
                        self._handle_position_changed
                    )
                except (
                    TypeError,
                    RuntimeError,
                ):
                    pass

            self.overlay.close()

    def _apply_preferences(
        self,
        preferences: CompanionPreferences,
    ) -> None:
        self._preferences = preferences
        self._last_error = ""

        overlay_preferences = preferences

        try:
            self.overlay.apply_preferences(
                overlay_preferences
            )
        except (
            FileNotFoundError,
            OSError,
            ValueError,
        ) as error:
            self._last_error = str(
                error
            )

            overlay_preferences = replace(
                preferences,
                enabled=False,
                asset_path="",
            )

            self.overlay.apply_preferences(
                overlay_preferences
            )

        fullscreen_enabled = bool(
            preferences.enabled
            and preferences.hide_in_fullscreen
            and not self._last_error
        )

        self.fullscreen_controller.set_enabled(
            fullscreen_enabled
        )

        self.preferences_changed.emit(
            preferences
        )

    def _handle_position_changed(
        self,
        x: int,
        y: int,
    ) -> None:
        if self._shutdown:
            return

        preferences = self._preferences

        if not preferences.remember_position:
            return

        try:
            screen_name = str(
                getattr(
                    self.overlay,
                    "current_screen_name",
                    "",
                )
                or ""
            )

            updated = self.store.update(
                position_x=int(
                    x
                ),
                position_y=int(
                    y
                ),
                screen_name=screen_name,
            )
        except (
            OSError,
            TypeError,
            ValueError,
        ):
            return

        if not isinstance(
            updated,
            CompanionPreferences,
        ):
            return

        self._preferences = updated

        self.preferences_changed.emit(
            updated
        )

    def _ensure_active(
        self,
    ) -> None:
        if self._shutdown:
            raise RuntimeError(
                "Companion runtime is shut down."
            )
