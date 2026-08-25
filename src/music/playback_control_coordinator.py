from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import (
    QObject,
    QThread,
    pyqtSignal,
)

from winsdk.windows.media import (
    MediaPlaybackAutoRepeatMode,
)

from src.music.media_controls import (
    MediaControls,
)


ACTION_PREVIOUS = "previous"
ACTION_TOGGLE_PLAY_PAUSE = "toggle_play_pause"
ACTION_NEXT = "next"
ACTION_SEEK = "seek"
ACTION_SHUFFLE = "shuffle"
ACTION_REPEAT = "repeat"

PLAYBACK_CONTROL_ACTIONS = (
    ACTION_PREVIOUS,
    ACTION_TOGGLE_PLAY_PAUSE,
    ACTION_NEXT,
)

MEDIA_CONTROL_METHODS = {
    ACTION_PREVIOUS: "skip_previous",
    ACTION_TOGGLE_PLAY_PAUSE: "toggle_play_pause",
    ACTION_NEXT: "skip_next",
    ACTION_SEEK: "seek_to_seconds",
    ACTION_SHUFFLE: "set_shuffle",
    ACTION_REPEAT: "set_repeat_mode",
}

SPOTIFY_TRANSPORT_METHODS = {
    ACTION_PREVIOUS: "skip_previous",
    ACTION_NEXT: "skip_next",
}
MEDIA_REPEAT_MODES = {
    "off": MediaPlaybackAutoRepeatMode.NONE,
    "context": MediaPlaybackAutoRepeatMode.LIST,
    "track": MediaPlaybackAutoRepeatMode.TRACK,
}


DEFAULT_PLAYBACK_CONTROL_SHUTDOWN_WAIT_MS = 5000


class _MediaControlThread(
    QThread
):
    completed = pyqtSignal(
        str,
        bool,
    )

    failed = pyqtSignal(
        str,
        str,
    )

    def __init__(
        self,
        controls_factory: Callable[[], object],
        action: str,
        control_argument=None,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        self._controls_factory = (
            controls_factory
        )

        self._action = action

        self._control_argument = (
            control_argument
        )

    def run(
        self,
    ) -> None:
        if self.isInterruptionRequested():
            return

        method_name = (
            MEDIA_CONTROL_METHODS[
                self._action
            ]
        )

        try:
            controls = (
                self._controls_factory()
            )

        except Exception:
            self.failed.emit(
                self._action,
                (
                    "Media controls could "
                    "not be prepared."
                ),
            )
            return

        method = getattr(
            controls,
            method_name,
            None,
        )

        if not callable(
            method
        ):
            self.failed.emit(
                self._action,
                (
                    "The current media source "
                    "does not expose this control."
                ),
            )
            return

        try:
            if (
                self._control_argument
                is None
            ):
                result = bool(
                    method()
                )

            else:
                result = bool(
                    method(
                        self._control_argument
                    )
                )

        except Exception:
            self.failed.emit(
                self._action,
                (
                    "The media control "
                    "request failed."
                ),
            )
            return

        self.completed.emit(
            self._action,
            result,
        )


class PlaybackControlCoordinator(
    QObject
):
    """
    Route Dashboard transport controls without
    foregrounding, activating, or automating
    another application's user interface.

    Spotify sessions use the official asynchronous
    Spotify playback runtime.

    Other media sessions use MediaControls/GSMTC
    on a worker thread so its asyncio bridge never
    blocks the Qt GUI thread.
    """

    control_dispatched = pyqtSignal(
        str,
        str,
    )

    control_completed = pyqtSignal(
        str,
        bool,
    )

    control_failed = pyqtSignal(
        str,
        str,
    )

    def __init__(
        self,
        spotify_runtime,
        *,
        media_controls_factory=MediaControls,
        shutdown_wait_ms: int = (
            DEFAULT_PLAYBACK_CONTROL_SHUTDOWN_WAIT_MS
        ),
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        required_spotify_methods = (
            "resume_playback",
            "pause_playback",
            "skip_next",
            "skip_previous",
        )

        missing = [
            method_name
            for method_name
            in required_spotify_methods
            if not callable(
                getattr(
                    spotify_runtime,
                    method_name,
                    None,
                )
            )
        ]

        if missing:
            raise TypeError(
                (
                    "spotify_runtime is missing "
                    "required transport controls: "
                    + ", ".join(
                        missing
                    )
                )
            )

        if not callable(
            media_controls_factory
        ):
            raise TypeError(
                (
                    "media_controls_factory "
                    "must be callable"
                )
            )

        if (
            isinstance(
                shutdown_wait_ms,
                bool,
            )
            or not isinstance(
                shutdown_wait_ms,
                int,
            )
            or shutdown_wait_ms <= 0
        ):
            raise ValueError(
                (
                    "shutdown_wait_ms must be "
                    "a positive integer"
                )
            )

        self._spotify_runtime = (
            spotify_runtime
        )

        self._media_controls_factory = (
            media_controls_factory
        )

        self._shutdown_wait_ms = (
            shutdown_wait_ms
        )

        self._media_thread = None
        self._shutting_down = False

    @staticmethod
    def _is_spotify_source(
        source_app,
    ) -> bool:
        normalized = str(
            source_app
            or ""
        ).strip().casefold()

        return (
            "spotify"
            in normalized
        )

    @property
    def shutting_down(
        self,
    ) -> bool:
        return self._shutting_down

    @property
    def media_busy(
        self,
    ) -> bool:
        thread = (
            self._media_thread
        )

        return bool(
            thread is not None
            and thread.isRunning()
        )

    def request(
        self,
        action,
        source_app,
        playing,
    ) -> bool:
        if self._shutting_down:
            return False

        normalized_action = str(
            action
            or ""
        ).strip().casefold()

        if (
            normalized_action
            not in PLAYBACK_CONTROL_ACTIONS
        ):
            return False

        if self._is_spotify_source(
            source_app
        ):
            return (
                self._dispatch_spotify(
                    normalized_action,
                    bool(
                        playing
                    ),
                )
            )

        return (
            self._dispatch_media(
                normalized_action
            )
        )


    def request_seek(
        self,
        seconds,
        source_app,
    ) -> bool:
        if self._shutting_down:
            return False

        if isinstance(
            seconds,
            bool,
        ):
            return False

        try:
            from math import isfinite

            checked_seconds = float(
                seconds
            )

        except (
            TypeError,
            ValueError,
        ):
            return False

        if (
            not isfinite(
                checked_seconds
            )
            or checked_seconds < 0
        ):
            return False

        if self._is_spotify_source(
            source_app
        ):
            method = getattr(
                self._spotify_runtime,
                "seek_to_seconds",
                None,
            )

            if not callable(
                method
            ):
                self.control_failed.emit(
                    ACTION_SEEK,
                    (
                        "Spotify seek control "
                        "is unavailable."
                    ),
                )
                return False

            try:
                result = method(
                    checked_seconds
                )

            except Exception:
                self.control_failed.emit(
                    ACTION_SEEK,
                    (
                        "Spotify seek control "
                        "could not be dispatched."
                    ),
                )
                return False

            if result is False:
                self.control_failed.emit(
                    ACTION_SEEK,
                    (
                        "Spotify seek control "
                        "was not accepted."
                    ),
                )
                return False

            self.control_dispatched.emit(
                ACTION_SEEK,
                "spotify",
            )

            return True

        return self._dispatch_media(
            ACTION_SEEK,
            control_argument=checked_seconds,
        )

    def request_shuffle(
        self,
        enabled,
        source_app,
    ) -> bool:
        if self._shutting_down:
            return False

        if not isinstance(
            enabled,
            bool,
        ):
            return False

        if self._is_spotify_source(
            source_app
        ):
            return (
                self._dispatch_spotify_argument(
                    ACTION_SHUFFLE,
                    "set_shuffle",
                    enabled,
                )
            )

        return self._dispatch_media(
            ACTION_SHUFFLE,
            control_argument=enabled,
        )

    def request_repeat_mode(
        self,
        mode,
        source_app,
    ) -> bool:
        if self._shutting_down:
            return False

        if not isinstance(
            mode,
            str,
        ):
            return False

        checked_mode = mode.strip()

        if (
            checked_mode != mode
            or checked_mode
            not in MEDIA_REPEAT_MODES
        ):
            return False

        if self._is_spotify_source(
            source_app
        ):
            return (
                self._dispatch_spotify_argument(
                    ACTION_REPEAT,
                    "set_repeat_mode",
                    checked_mode,
                )
            )

        return self._dispatch_media(
            ACTION_REPEAT,
            control_argument=(
                MEDIA_REPEAT_MODES[
                    checked_mode
                ]
            ),
        )

    def _dispatch_spotify_argument(
        self,
        action: str,
        method_name: str,
        control_argument,
    ) -> bool:
        method = getattr(
            self._spotify_runtime,
            method_name,
            None,
        )

        if not callable(
            method
        ):
            self.control_failed.emit(
                action,
                (
                    "Spotify "
                    + action
                    + " control is unavailable."
                ),
            )

            return False

        try:
            result = method(
                control_argument
            )

        except Exception:
            self.control_failed.emit(
                action,
                (
                    "Spotify "
                    + action
                    + " control could not "
                    + "be dispatched."
                ),
            )

            return False

        # Spotify Qt request methods normally
        # return None after successful dispatch.
        # Only an explicit False means rejection.
        if result is False:
            self.control_failed.emit(
                action,
                (
                    "Spotify "
                    + action
                    + " control was not accepted."
                ),
            )

            return False

        self.control_dispatched.emit(
            action,
            "spotify",
        )

        return True

    def _dispatch_spotify(
        self,
        action: str,
        playing: bool,
    ) -> bool:
        if (
            action
            == ACTION_TOGGLE_PLAY_PAUSE
        ):
            method_name = (
                "pause_playback"
                if playing
                else "resume_playback"
            )

        else:
            method_name = (
                SPOTIFY_TRANSPORT_METHODS[
                    action
                ]
            )

        method = getattr(
            self._spotify_runtime,
            method_name,
            None,
        )

        if not callable(
            method
        ):
            self.control_failed.emit(
                action,
                (
                    "Spotify transport control "
                    "is unavailable."
                ),
            )
            return False

        try:
            result = method()

        except Exception:
            self.control_failed.emit(
                action,
                (
                    "Spotify transport control "
                    "could not be dispatched."
                ),
            )
            return False

        # Some compatible request-style runtimes
        # return None on successful dispatch.
        # Only an explicit False is rejection.
        if result is False:
            self.control_failed.emit(
                action,
                (
                    "Spotify transport control "
                    "was not accepted."
                ),
            )
            return False

        self.control_dispatched.emit(
            action,
            "spotify",
        )

        return True

    def _dispatch_media(
        self,
        action: str,
        *,
        control_argument=None,
    ) -> bool:
        thread = (
            self._media_thread
        )

        if (
            thread is not None
            and not thread.isRunning()
        ):
            self._media_thread = None
            thread = None

        if (
            thread is not None
            and thread.isRunning()
        ):
            return False

        thread = _MediaControlThread(
            self._media_controls_factory,
            action,
            control_argument=control_argument,
            parent=self,
        )

        thread.completed.connect(
            self._media_control_completed
        )

        thread.failed.connect(
            self._media_control_failed
        )

        thread.finished.connect(
            self._media_thread_finished
        )

        thread.finished.connect(
            thread.deleteLater
        )

        self._media_thread = thread

        try:
            thread.start()

        except Exception:
            self._media_thread = None

            self.control_failed.emit(
                action,
                (
                    "Media control worker "
                    "could not start."
                ),
            )

            return False

        self.control_dispatched.emit(
            action,
            "windows_media",
        )

        return True

    def _media_control_completed(
        self,
        action: str,
        success: bool,
    ) -> None:
        if self._shutting_down:
            return

        self.control_completed.emit(
            action,
            bool(
                success
            ),
        )

    def _media_control_failed(
        self,
        action: str,
        message: str,
    ) -> None:
        if self._shutting_down:
            return

        self.control_failed.emit(
            action,
            message,
        )

    def _media_thread_finished(
        self,
    ) -> None:
        thread = self.sender()

        if (
            self._media_thread
            is thread
        ):
            self._media_thread = None

    def shutdown(
        self,
    ) -> bool:
        self._shutting_down = True

        thread = (
            self._media_thread
        )

        if thread is None:
            return True

        if not thread.isRunning():
            self._media_thread = None
            return True

        if (
            QThread.currentThread()
            is thread
        ):
            return False

        try:
            thread.requestInterruption()

        except Exception:
            pass

        try:
            thread.quit()

        except Exception:
            pass

        try:
            stopped = bool(
                thread.wait(
                    self._shutdown_wait_ms
                )
            )

        except Exception:
            return False

        if stopped:
            self._media_thread = None

        return stopped
