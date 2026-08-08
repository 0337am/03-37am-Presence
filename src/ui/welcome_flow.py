from __future__ import annotations

from collections.abc import Sequence

from src.ui.welcome import (
    ACTION_DISCORD_PRESENCE,
    ACTION_GET_STARTED,
    ACTION_MEDIA_HOTKEYS,
    ACTION_MEDIA_SOURCES,
    WELCOME_ACTIONS,
)


def command_line_starts_minimized(
    arguments: Sequence[object],
) -> bool:
    """
    Return True only when the actual process arguments contain
    the dedicated startup-minimized flag.
    """

    for argument in list(
        arguments
    )[1:]:
        if (
            str(
                argument
            ).strip().lower()
            == "--minimized"
        ):
            return True

    return False


def should_show_main_window(
    *,
    show_welcome: bool,
    start_minimized: bool,
) -> bool:
    """
    A pending first launch must always remain visible.

    Outside first-run onboarding, --minimized behaves normally
    and leaves the main window in the tray.
    """

    if show_welcome:
        return True

    return not start_minimized


class WelcomeFlow:
    """
    Connects WelcomeDialog actions to existing MainWindow
    navigation without changing unrelated settings.
    """

    def __init__(
        self,
        *,
        manager,
        main_window,
        dialog,
    ):
        self.manager = manager
        self.main_window = (
            main_window
        )
        self.dialog = dialog
        self.last_error = None

    def handle_action(
        self,
        action: str,
    ) -> None:
        action = str(
            action
            or ""
        ).strip()

        if action not in WELCOME_ACTIONS:
            raise ValueError(
                "Unsupported welcome action."
            )

        self.last_error = None

        if (
            action
            == ACTION_GET_STARTED
        ):
            self._complete_welcome()
            return

        self._show_main_window()

        if (
            action
            == ACTION_MEDIA_SOURCES
        ):
            self.main_window.open_settings_section(
                "media_sources"
            )

        elif (
            action
            == ACTION_DISCORD_PRESENCE
        ):
            self.main_window.switch_page(
                1
            )

        elif (
            action
            == ACTION_MEDIA_HOTKEYS
        ):
            self.main_window.open_settings_section(
                "media_hotkeys"
            )

        self.dialog.reject()

    def _complete_welcome(
        self,
    ) -> None:
        try:
            self.manager.mark_completed()
        except Exception as error:
            self.last_error = str(
                error
            )

            print(
                "First-run completion error:",
                error,
            )

            return

        self._show_main_window()

        self.main_window.switch_page(
            0
        )

        self.dialog.accept()

    def _show_main_window(
        self,
    ) -> None:
        self.main_window.showNormal()
        self.main_window.raise_()
        self.main_window.activateWindow()
