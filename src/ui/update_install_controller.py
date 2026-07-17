from __future__ import annotations

from typing import (
    Any,
    Callable,
)

from src.system.update_installer import (
    launch_downloaded_update,
)


InstallLauncher = Callable[..., Any]
InstallerOpener = Callable[[str], Any]
QuitCallback = Callable[[], Any]


class UpdateInstallController:
    def __init__(
        self,
        *,
        launcher: InstallLauncher = (
            launch_downloaded_update
        ),
        opener: InstallerOpener | None = None,
    ):
        self._launcher = launcher
        self._opener = opener
        self._quit_callback = None

    @property
    def quit_callback_available(self) -> bool:
        return callable(
            self._quit_callback
        )

    def set_quit_callback(
        self,
        callback: QuitCallback | None,
    ) -> None:
        self._quit_callback = (
            callback
            if callable(callback)
            else None
        )

    def launch(
        self,
        download_result,
        *,
        user_approved: bool,
    ):
        return self._launcher(
            download_result,
            user_approved=bool(
                user_approved
            ),
            opener=self._opener,
            quit_callback=(
                self._quit_callback
            ),
        )
