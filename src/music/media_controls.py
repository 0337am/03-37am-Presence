from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from winsdk.windows.media import (
    MediaPlaybackAutoRepeatMode,
)
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
)

from src.music.windows_media import WindowsMedia


ManagerRequest = Callable[[], Awaitable[Any]]
SleepRequest = Callable[[float], Awaitable[Any]]

TICKS_PER_SECOND = 10_000_000

STATE_CONFIRM_ATTEMPTS = 20
STATE_CONFIRM_DELAY_SECONDS = 0.05
SEEK_CONFIRM_TOLERANCE_SECONDS = 1.5

_REPEAT_SEQUENCE = (
    MediaPlaybackAutoRepeatMode.NONE,
    MediaPlaybackAutoRepeatMode.LIST,
    MediaPlaybackAutoRepeatMode.TRACK,
)

_REPEAT_VALUES = {
    int(MediaPlaybackAutoRepeatMode.NONE):
        MediaPlaybackAutoRepeatMode.NONE,
    int(MediaPlaybackAutoRepeatMode.TRACK):
        MediaPlaybackAutoRepeatMode.TRACK,
    int(MediaPlaybackAutoRepeatMode.LIST):
        MediaPlaybackAutoRepeatMode.LIST,
}


class MediaControls:
    """
    Reusable controls for the same Windows media session selected by
    03:37am Presence.

    Commands return True only when the media session reports success.
    Missing sessions, unsupported commands, invalid values, and WinRT
    errors fail safely and return False.
    """

    def __init__(
        self,
        media: WindowsMedia | None = None,
        manager_request: ManagerRequest | None = None,
        sleep_request: SleepRequest | None = None,
    ):
        self.media = media or WindowsMedia()

        self._manager_request = (
            manager_request
            or GlobalSystemMediaTransportControlsSessionManager.request_async
        )

        self._sleep_request = (
            sleep_request
            or asyncio.sleep
        )

    def play(self) -> bool:
        return self._run_command(
            "try_play_async"
        )

    def pause(self) -> bool:
        return self._run_command(
            "try_pause_async"
        )

    def toggle_play_pause(self) -> bool:
        return self._run_command(
            "try_toggle_play_pause_async"
        )

    def skip_next(self) -> bool:
        return self._run_command(
            "try_skip_next_async"
        )

    def skip_previous(self) -> bool:
        return self._run_command(
            "try_skip_previous_async"
        )

    def set_shuffle(
        self,
        active: bool,
    ) -> bool:
        return self._run_operation(
            lambda: self._set_shuffle_async(
                bool(active)
            )
        )

    def toggle_shuffle(self) -> bool:
        return self._run_operation(
            self._toggle_shuffle_async
        )

    def set_repeat_mode(
        self,
        mode: MediaPlaybackAutoRepeatMode | int,
    ) -> bool:
        normalized = self._normalize_repeat_mode(
            mode
        )

        if normalized is None:
            return False

        return self._run_operation(
            lambda: self._set_repeat_mode_async(
                normalized
            )
        )

    def cycle_repeat_mode(self) -> bool:
        """
        Cycle repeat in the UI-friendly order:

        Off -> Playlist -> Track -> Off
        """
        return self._run_operation(
            self._cycle_repeat_mode_async
        )

    def seek_to_seconds(
        self,
        seconds: float,
    ) -> bool:
        try:
            position = float(seconds)
        except (TypeError, ValueError):
            return False

        if not math.isfinite(position):
            return False

        return self._run_operation(
            lambda: self._seek_to_seconds_async(
                position
            )
        )

    def seek_by_seconds(
        self,
        seconds: float,
    ) -> bool:
        try:
            offset = float(seconds)
        except (TypeError, ValueError):
            return False

        if not math.isfinite(offset):
            return False

        return self._run_operation(
            lambda: self._seek_by_seconds_async(
                offset
            )
        )

    def _run_command(
        self,
        method_name: str,
    ) -> bool:
        return self._run_operation(
            lambda: self._run_command_async(
                method_name
            )
        )

    def _run_operation(
        self,
        operation: Callable[
            [],
            Awaitable[bool],
        ],
    ) -> bool:
        try:
            return bool(
                asyncio.run(
                    operation()
                )
            )

        except Exception as error:
            print(
                "Media control error:",
                error,
            )
            return False

    async def _run_command_async(
        self,
        method_name: str,
    ) -> bool:
        session = await self._selected_session_async()

        if session is None:
            return False

        command = getattr(
            session,
            method_name,
            None,
        )

        if command is None:
            return False

        try:
            result = await command()

        except Exception as error:
            print(
                "Media control command error:",
                error,
            )
            return False

        return bool(result)

    async def _set_shuffle_async(
        self,
        active: bool,
    ) -> bool:
        session = await self._selected_session_async()

        if session is None:
            return False

        info = self._playback_info(
            session
        )

        if info is None:
            return False

        if not self._control_enabled(
            info,
            "is_shuffle_enabled",
        ):
            return False

        command = getattr(
            session,
            "try_change_shuffle_active_async",
            None,
        )

        if command is None:
            return False

        try:
            accepted = bool(
                await command(
                    bool(active)
                )
            )

            if not accepted:
                return False

            return await self._wait_for_shuffle_state_async(
                session,
                bool(active),
            )

        except Exception as error:
            print(
                "Media control shuffle error:",
                error,
            )
            return False

    async def _toggle_shuffle_async(
        self,
    ) -> bool:
        session = await self._selected_session_async()

        if session is None:
            return False

        info = self._playback_info(
            session
        )

        if info is None:
            return False

        if not self._control_enabled(
            info,
            "is_shuffle_enabled",
        ):
            return False

        current = bool(
            getattr(
                info,
                "is_shuffle_active",
                False,
            )
        )

        command = getattr(
            session,
            "try_change_shuffle_active_async",
            None,
        )

        if command is None:
            return False

        expected = not current

        try:
            accepted = bool(
                await command(
                    expected
                )
            )

            if not accepted:
                return False

            return await self._wait_for_shuffle_state_async(
                session,
                expected,
            )

        except Exception as error:
            print(
                "Media control shuffle error:",
                error,
            )
            return False

    async def _set_repeat_mode_async(
        self,
        mode: MediaPlaybackAutoRepeatMode,
    ) -> bool:
        session = await self._selected_session_async()

        if session is None:
            return False

        info = self._playback_info(
            session
        )

        if info is None:
            return False

        if not self._control_enabled(
            info,
            "is_repeat_enabled",
        ):
            return False

        command = getattr(
            session,
            "try_change_auto_repeat_mode_async",
            None,
        )

        if command is None:
            return False

        try:
            accepted = bool(
                await command(
                    mode
                )
            )

            if not accepted:
                return False

            return await self._wait_for_repeat_state_async(
                session,
                mode,
            )

        except Exception as error:
            print(
                "Media control repeat error:",
                error,
            )
            return False

    async def _cycle_repeat_mode_async(
        self,
    ) -> bool:
        session = await self._selected_session_async()

        if session is None:
            return False

        info = self._playback_info(
            session
        )

        if info is None:
            return False

        if not self._control_enabled(
            info,
            "is_repeat_enabled",
        ):
            return False

        current = self._normalize_repeat_mode(
            getattr(
                info,
                "auto_repeat_mode",
                MediaPlaybackAutoRepeatMode.NONE,
            )
        )

        if current is None:
            current = (
                MediaPlaybackAutoRepeatMode.NONE
            )

        try:
            index = _REPEAT_SEQUENCE.index(
                current
            )
        except ValueError:
            index = 0

        next_mode = _REPEAT_SEQUENCE[
            (index + 1)
            % len(_REPEAT_SEQUENCE)
        ]

        command = getattr(
            session,
            "try_change_auto_repeat_mode_async",
            None,
        )

        if command is None:
            return False

        try:
            accepted = bool(
                await command(
                    next_mode
                )
            )

            if not accepted:
                return False

            return await self._wait_for_repeat_state_async(
                session,
                next_mode,
            )

        except Exception as error:
            print(
                "Media control repeat error:",
                error,
            )
            return False

    async def _seek_to_seconds_async(
        self,
        seconds: float,
    ) -> bool:
        session = await self._selected_session_async()

        if session is None:
            return False

        return await self._seek_selected_session_async(
            session,
            seconds,
        )

    async def _seek_by_seconds_async(
        self,
        seconds: float,
    ) -> bool:
        session = await self._selected_session_async()

        if session is None:
            return False

        info = self._playback_info(
            session
        )

        if info is None:
            return False

        if not self._control_enabled(
            info,
            "is_playback_position_enabled",
        ):
            return False

        timeline = self._timeline(
            session
        )

        if timeline is None:
            return False

        current = self._seconds_from_timedelta(
            getattr(
                timeline,
                "position",
                None,
            )
        )

        if current is None:
            return False

        return await self._seek_selected_session_async(
            session,
            current + seconds,
            timeline=timeline,
            playback_info=info,
        )

    async def _seek_selected_session_async(
        self,
        session,
        seconds: float,
        *,
        timeline=None,
        playback_info=None,
    ) -> bool:
        info = (
            playback_info
            if playback_info is not None
            else self._playback_info(
                session
            )
        )

        if info is None:
            return False

        if not self._control_enabled(
            info,
            "is_playback_position_enabled",
        ):
            return False

        current_timeline = (
            timeline
            if timeline is not None
            else self._timeline(
                session
            )
        )

        if current_timeline is None:
            return False

        minimum = self._seconds_from_timedelta(
            getattr(
                current_timeline,
                "min_seek_time",
                None,
            )
        )

        maximum = self._seconds_from_timedelta(
            getattr(
                current_timeline,
                "max_seek_time",
                None,
            )
        )

        if minimum is None:
            minimum = 0.0

        if maximum is None:
            maximum = self._seconds_from_timedelta(
                getattr(
                    current_timeline,
                    "end_time",
                    None,
                )
            )

        target = max(
            float(seconds),
            minimum,
        )

        if maximum is not None:
            target = min(
                target,
                maximum,
            )

        command = getattr(
            session,
            "try_change_playback_position_async",
            None,
        )

        if command is None:
            return False

        ticks = int(
            round(
                target
                * TICKS_PER_SECOND
            )
        )

        try:
            accepted = bool(
                await command(
                    ticks
                )
            )

            if not accepted:
                return False

            return await self._wait_for_seek_position_async(
                session,
                target,
            )

        except Exception as error:
            print(
                "Media control seek error:",
                error,
            )
            return False

    async def _wait_for_shuffle_state_async(
        self,
        session,
        expected: bool,
    ) -> bool:
        for attempt in range(
            STATE_CONFIRM_ATTEMPTS
        ):
            info = self._playback_info(
                session
            )

            if info is not None:
                try:
                    current = bool(
                        info.is_shuffle_active
                    )
                except Exception:
                    current = None

                if current == expected:
                    return True

            if (
                attempt
                < STATE_CONFIRM_ATTEMPTS - 1
            ):
                await self._sleep_request(
                    STATE_CONFIRM_DELAY_SECONDS
                )

        print(
            "Media control state confirmation timed out: "
            "shuffle"
        )

        return False

    async def _wait_for_repeat_state_async(
        self,
        session,
        expected: MediaPlaybackAutoRepeatMode,
    ) -> bool:
        for attempt in range(
            STATE_CONFIRM_ATTEMPTS
        ):
            info = self._playback_info(
                session
            )

            if info is not None:
                current = self._normalize_repeat_mode(
                    getattr(
                        info,
                        "auto_repeat_mode",
                        None,
                    )
                )

                if current == expected:
                    return True

            if (
                attempt
                < STATE_CONFIRM_ATTEMPTS - 1
            ):
                await self._sleep_request(
                    STATE_CONFIRM_DELAY_SECONDS
                )

        print(
            "Media control state confirmation timed out: "
            "repeat"
        )

        return False

    async def _wait_for_seek_position_async(
        self,
        session,
        expected_seconds: float,
    ) -> bool:
        for attempt in range(
            STATE_CONFIRM_ATTEMPTS
        ):
            timeline = self._timeline(
                session
            )

            if timeline is not None:
                current = self._seconds_from_timedelta(
                    getattr(
                        timeline,
                        "position",
                        None,
                    )
                )

                if (
                    current is not None
                    and abs(
                        current
                        - expected_seconds
                    )
                    <= SEEK_CONFIRM_TOLERANCE_SECONDS
                ):
                    return True

            if (
                attempt
                < STATE_CONFIRM_ATTEMPTS - 1
            ):
                await self._sleep_request(
                    STATE_CONFIRM_DELAY_SECONDS
                )

        print(
            "Media control state confirmation timed out: "
            "seek"
        )

        return False

    async def _selected_session_async(
        self,
    ):
        preferences = (
            self.media.preference_store.load()
        )

        if not (
            preferences.spotify_enabled
            or preferences.browser_enabled
        ):
            return None

        try:
            manager = await self._manager_request()

            sessions = list(
                manager.get_sessions()
            )

            current_session = (
                manager.get_current_session()
            )

            return self.media._select_session(
                sessions=sessions,
                current_session=current_session,
                preferences=preferences,
            )

        except Exception as error:
            print(
                "Media control session error:",
                error,
            )
            return None

    def _playback_info(
        self,
        session,
    ):
        try:
            return session.get_playback_info()

        except Exception as error:
            print(
                "Media control playback info error:",
                error,
            )
            return None

    def _timeline(
        self,
        session,
    ):
        try:
            return (
                session.get_timeline_properties()
            )

        except Exception as error:
            print(
                "Media control timeline error:",
                error,
            )
            return None

    def _control_enabled(
        self,
        playback_info,
        property_name: str,
    ) -> bool:
        try:
            controls = playback_info.controls

            return bool(
                getattr(
                    controls,
                    property_name,
                    False,
                )
            )

        except Exception:
            return False

    def _normalize_repeat_mode(
        self,
        mode,
    ):
        try:
            value = int(mode)

        except (
            TypeError,
            ValueError,
        ):
            return None

        return _REPEAT_VALUES.get(
            value
        )

    def _seconds_from_timedelta(
        self,
        value,
    ) -> float | None:
        if not isinstance(
            value,
            timedelta,
        ):
            return None

        return float(
            value.total_seconds()
        )
