from __future__ import annotations

from typing import Callable

from src.system.media_hotkey_preferences import (
    MediaHotkeyPreferences,
    MediaHotkeyPreferencesStore,
)
from src.system.media_hotkeys import (
    MediaHotkeyController,
)


class MediaHotkeyRuntime:
    def __init__(
        self,
        *,
        app,
        preference_store=None,
        controller_factory=None,
    ):
        if app is None:
            raise ValueError(
                "A Qt application instance is required."
            )

        self.app = app

        self.preference_store = (
            preference_store
            if preference_store is not None
            else MediaHotkeyPreferencesStore()
        )

        self.controller_factory = (
            controller_factory
            if controller_factory is not None
            else self._default_controller_factory
        )

        if not callable(
            self.controller_factory
        ):
            raise TypeError(
                "controller_factory must be callable."
            )

        self._controller = None

        self._preferences = (
            MediaHotkeyPreferences()
        )

        self._started = False

    @property
    def started(
        self,
    ) -> bool:
        return self._started

    @property
    def controller(
        self,
    ):
        return self._controller

    @property
    def preferences(
        self,
    ) -> MediaHotkeyPreferences:
        return self._preferences

    @property
    def active(
        self,
    ) -> bool:
        return (
            self._controller is not None
            and self._controller.started
        )

    @property
    def registered_actions(
        self,
    ) -> tuple[str, ...]:
        if self._controller is None:
            return ()

        return tuple(
            self._controller.registered_actions
        )

    def _default_controller_factory(
        self,
        *,
        seek_seconds: float,
    ):
        return MediaHotkeyController(
            app=self.app,
            seek_seconds=seek_seconds,
        )

    def _create_controller(
        self,
        preferences: MediaHotkeyPreferences,
    ):
        return self.controller_factory(
            seek_seconds=(
                preferences.seek_seconds
            ),
        )

    def start(
        self,
    ) -> bool:
        if self._started:
            return True

        try:
            preferences = (
                self.preference_store.load()
            )

        except Exception as error:
            print(
                "Media hotkey preference load error:",
                error,
            )

            return False

        self._preferences = preferences
        self._started = True

        if not preferences.enabled:
            return True

        bindings = (
            preferences.controller_bindings()
        )

        if not bindings:
            return True

        controller = None

        try:
            controller = (
                self._create_controller(
                    preferences
                )
            )

            if controller is None:
                raise RuntimeError(
                    "Media hotkey controller factory "
                    "returned no controller."
                )

            if not controller.start(
                bindings
            ):
                controller.close()

                return False

        except Exception as error:
            print(
                "Media hotkey runtime start error:",
                error,
            )

            if controller is not None:
                try:
                    controller.close()
                except Exception:
                    pass

            return False

        self._controller = controller

        return True

    def stop(
        self,
    ) -> bool:
        controller = (
            self._controller
        )

        if controller is None:
            self._started = False

            return True

        try:
            result = controller.close()

        except Exception as error:
            print(
                "Media hotkey runtime stop error:",
                error,
            )

            return False

        if result is False:
            return False

        self._controller = None
        self._started = False

        return True

    def reload(
        self,
    ) -> bool:
        try:
            new_preferences = (
                self.preference_store.load()
            )

        except Exception as error:
            print(
                "Media hotkey preference reload error:",
                error,
            )

            return False

        old_preferences = (
            self._preferences
        )

        old_controller = (
            self._controller
        )

        old_started = (
            self._started
        )

        new_controller = None

        try:
            if (
                new_preferences.enabled
                and new_preferences.controller_bindings()
            ):
                new_controller = (
                    self._create_controller(
                        new_preferences
                    )
                )

                if new_controller is None:
                    raise RuntimeError(
                        "Media hotkey controller factory "
                        "returned no controller."
                    )

                if old_controller is not None:
                    if not old_controller.close():
                        new_controller.close()

                        return False

                    self._controller = None

                if not new_controller.start(
                    new_preferences.controller_bindings()
                ):
                    new_controller.close()

                    if old_controller is not None:
                        try:
                            old_controller.start(
                                old_preferences.controller_bindings()
                            )

                            self._controller = (
                                old_controller
                            )
                        except Exception:
                            self._controller = None

                    return False

                self._controller = (
                    new_controller
                )

            else:
                if old_controller is not None:
                    if not old_controller.close():
                        return False

                self._controller = None

        except Exception as error:
            print(
                "Media hotkey runtime reload error:",
                error,
            )

            if new_controller is not None:
                try:
                    new_controller.close()
                except Exception:
                    pass

            if (
                old_controller is not None
                and self._controller is None
            ):
                try:
                    old_controller.start(
                        old_preferences.controller_bindings()
                    )

                    self._controller = (
                        old_controller
                    )
                except Exception:
                    pass

            self._preferences = (
                old_preferences
            )

            self._started = (
                old_started
            )

            return False

        self._preferences = (
            new_preferences
        )

        self._started = True

        return True

    def close(
        self,
    ) -> bool:
        return self.stop()
