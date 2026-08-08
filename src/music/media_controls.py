from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
)

from src.music.windows_media import WindowsMedia


ManagerRequest = Callable[[], Awaitable[Any]]


class MediaControls:
    """
    Reusable controls for the same Windows media session selected by
    03:37am Presence.

    Commands return True only when the media session reports success.
    Missing sessions, unsupported commands, and WinRT errors fail safely
    and return False.
    """

    def __init__(
        self,
        media: WindowsMedia | None = None,
        manager_request: ManagerRequest | None = None,
    ):
        self.media = media or WindowsMedia()

        self._manager_request = (
            manager_request
            or GlobalSystemMediaTransportControlsSessionManager.request_async
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

    def _run_command(
        self,
        method_name: str,
    ) -> bool:
        try:
            return bool(
                asyncio.run(
                    self._run_command_async(
                        method_name
                    )
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
