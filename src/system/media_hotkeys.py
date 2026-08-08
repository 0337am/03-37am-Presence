from __future__ import annotations

import math
from collections.abc import Mapping

from src.music.media_controls import (
    MediaControls,
)
from src.system.global_hotkeys import (
    GlobalHotkeyRegistry,
    HotkeyBinding,
)
from src.system.qt_hotkey_bridge import (
    QtHotkeyBridge,
)


ACTION_PLAY_PAUSE = "play_pause"
ACTION_NEXT = "next"
ACTION_PREVIOUS = "previous"
ACTION_SHUFFLE = "shuffle"
ACTION_REPEAT = "repeat"
ACTION_SEEK_FORWARD = "seek_forward"
ACTION_SEEK_BACKWARD = "seek_backward"

SUPPORTED_MEDIA_HOTKEY_ACTIONS = (
    ACTION_PLAY_PAUSE,
    ACTION_NEXT,
    ACTION_PREVIOUS,
    ACTION_SHUFFLE,
    ACTION_REPEAT,
    ACTION_SEEK_FORWARD,
    ACTION_SEEK_BACKWARD,
)

DEFAULT_SEEK_SECONDS = 10.0


class MediaHotkeyController:
    """
    Connects Windows global-hotkey registrations to MediaControls.

    This class owns the action routing but does not decide which
    shortcuts the user wants. Bindings are supplied by the caller so
    Settings can become the source of truth later.
    """

    def __init__(
        self,
        app=None,
        *,
        media_controls: MediaControls | None = None,
        registry: GlobalHotkeyRegistry | None = None,
        bridge: QtHotkeyBridge | None = None,
        seek_seconds: float = DEFAULT_SEEK_SECONDS,
    ):
        self.media_controls = (
            media_controls
            if media_controls is not None
            else MediaControls()
        )

        self.registry = (
            registry
            if registry is not None
            else GlobalHotkeyRegistry()
        )

        if bridge is None:
            if app is None:
                raise ValueError(
                    "A Qt application is required when "
                    "no hotkey bridge is supplied."
                )

            bridge = QtHotkeyBridge(
                app,
                self.registry,
            )

        self.bridge = bridge

        self.seek_seconds = (
            self._normalize_seek_seconds(
                seek_seconds
            )
        )

        self._started = False
        self._registered_actions: list[
            str
        ] = []

    @property
    def started(
        self,
    ) -> bool:
        return self._started

    @property
    def registered_actions(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            self._registered_actions
        )

    def start(
        self,
        bindings: Mapping[
            str,
            HotkeyBinding,
        ],
    ) -> bool:
        if self._started:
            return True

        normalized = (
            self._validate_bindings(
                bindings
            )
        )

        if normalized is None:
            return False

        if not self.bridge.install():
            return False

        registered: list[str] = []

        for action, binding in normalized.items():
            registration = (
                self.registry.register(
                    action,
                    binding,
                    self._callback_for(
                        action
                    ),
                )
            )

            if registration is None:
                self._rollback(
                    registered
                )

                self.bridge.remove()

                return False

            registered.append(
                action
            )

        self._registered_actions = (
            registered
        )

        self._started = True

        return True

    def stop(
        self,
    ) -> bool:
        success = True

        for action in reversed(
            tuple(
                self._registered_actions
            )
        ):
            if not self.registry.unregister(
                action
            ):
                success = False

        if success:
            self._registered_actions.clear()

        if not self.bridge.remove():
            success = False

        if success:
            self._started = False

        return success

    def trigger(
        self,
        action: str,
    ) -> bool:
        normalized = str(
            action
        ).strip()

        if (
            normalized
            not in SUPPORTED_MEDIA_HOTKEY_ACTIONS
        ):
            return False

        try:
            if (
                normalized
                == ACTION_PLAY_PAUSE
            ):
                return bool(
                    self.media_controls
                    .toggle_play_pause()
                )

            if normalized == ACTION_NEXT:
                return bool(
                    self.media_controls
                    .skip_next()
                )

            if (
                normalized
                == ACTION_PREVIOUS
            ):
                return bool(
                    self.media_controls
                    .skip_previous()
                )

            if (
                normalized
                == ACTION_SHUFFLE
            ):
                return bool(
                    self.media_controls
                    .toggle_shuffle()
                )

            if (
                normalized
                == ACTION_REPEAT
            ):
                return bool(
                    self.media_controls
                    .cycle_repeat_mode()
                )

            if (
                normalized
                == ACTION_SEEK_FORWARD
            ):
                return bool(
                    self.media_controls
                    .seek_by_seconds(
                        self.seek_seconds
                    )
                )

            if (
                normalized
                == ACTION_SEEK_BACKWARD
            ):
                return bool(
                    self.media_controls
                    .seek_by_seconds(
                        -self.seek_seconds
                    )
                )

        except Exception as error:
            print(
                "Media hotkey action error:",
                error,
            )

            return False

        return False

    def close(
        self,
    ) -> bool:
        if self._started:
            return self.stop()

        return self.bridge.remove()

    def _callback_for(
        self,
        action: str,
    ):
        def callback():
            result = self.trigger(
                action
            )

            if not result:
                print(
                    "Media hotkey action was not "
                    "completed:",
                    action,
                )

        return callback

    def _validate_bindings(
        self,
        bindings,
    ) -> dict[
        str,
        HotkeyBinding,
    ] | None:
        if not isinstance(
            bindings,
            Mapping,
        ):
            return None

        normalized: dict[
            str,
            HotkeyBinding,
        ] = {}

        seen_bindings: set[
            HotkeyBinding
        ] = set()

        for action, binding in bindings.items():
            normalized_action = str(
                action
            ).strip()

            if (
                normalized_action
                not in SUPPORTED_MEDIA_HOTKEY_ACTIONS
            ):
                return None

            if not isinstance(
                binding,
                HotkeyBinding,
            ):
                return None

            if (
                binding
                in seen_bindings
            ):
                return None

            seen_bindings.add(
                binding
            )

            normalized[
                normalized_action
            ] = binding

        return normalized

    def _rollback(
        self,
        actions,
    ) -> None:
        for action in reversed(
            tuple(
                actions
            )
        ):
            self.registry.unregister(
                action
            )

        self._registered_actions.clear()

        self._started = False

    def _normalize_seek_seconds(
        self,
        value,
    ) -> float:
        try:
            seconds = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            raise ValueError(
                "Seek amount must be a number."
            )

        if (
            not math.isfinite(
                seconds
            )
            or seconds <= 0
        ):
            raise ValueError(
                "Seek amount must be a positive "
                "finite number."
            )

        return seconds
