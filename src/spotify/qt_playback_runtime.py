from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import (
    QObject,
    QThread,
    pyqtSignal,
    pyqtSlot,
)

from src.spotify.playback_service import (
    SpotifyPlaybackServiceResult,
)


DEFAULT_SPOTIFY_PLAYBACK_SHUTDOWN_WAIT_MS = 5000

SPOTIFY_PLAYBACK_CONTROL_METHODS = (
    "resume_playback",
    "pause_playback",
    "skip_next",
    "skip_previous",
    "seek_to_seconds",
    "set_shuffle",
    "set_repeat_mode",
)


class SpotifyQtPlaybackRuntimeError(
    RuntimeError
):
    def __init__(
        self,
        error_code: str,
        message: str,
    ) -> None:
        super().__init__(
            message
        )

        self.error_code = str(
            error_code
        )

        self.message = str(
            message
        )


def _validate_shutdown_wait_ms(
    value,
) -> int:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
    ):
        raise TypeError(
            (
                "shutdown_wait_ms must be "
                "an integer"
            )
        )

    if value <= 0:
        raise ValueError(
            (
                "shutdown_wait_ms must be "
                "greater than zero"
            )
        )

    return value


def _validate_playback_uri(
    value,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "spotify_uri must be a string"
        )

    checked = value.strip()

    if not checked:
        raise ValueError(
            "spotify_uri cannot be empty"
        )

    return checked


class _SpotifyPlaybackWorker(
    QObject
):
    result_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
    )

    finished = pyqtSignal()

    def __init__(
        self,
        service_factory: Callable,
        spotify_uri: str,
        *,
        album_id: str | None = None,
        playlist_id: str | None = None,
        playlist_position: int | None = None,
    ) -> None:
        super().__init__()

        self._service_factory = (
            service_factory
        )

        self._spotify_uri = (
            spotify_uri
        )

        self._album_id = (
            album_id
        )

        self._playlist_id = (
            playlist_id
        )

        self._playlist_position = (
            playlist_position
        )

    def _fail(
        self,
        error_code: str,
        message: str,
    ) -> None:
        self.failed.emit(
            error_code,
            message,
        )

    @pyqtSlot()
    def run(
        self,
    ) -> None:
        try:
            try:
                service = (
                    self._service_factory()
                )

            except Exception:
                self._fail(
                    "runtime_setup_failed",
                    (
                        "Spotify playback could "
                        "not be prepared."
                    ),
                )
                return

            if self._playlist_position is not None:
                method_name = (
                    "play_playlist_position"
                )

            elif self._album_id is not None:
                method_name = (
                    "play_album_track"
                )

            elif self._playlist_id is not None:
                method_name = (
                    "play_playlist_track"
                )

            else:
                method_name = (
                    "play_track"
                )

            play_method = getattr(
                service,
                method_name,
                None,
            )

            if not callable(
                play_method
            ):
                self._fail(
                    "invalid_service",
                    (
                        "Spotify playback service "
                        "is unavailable."
                    ),
                )
                return

            try:
                if self._playlist_position is not None:
                    result = play_method(
                        self._playlist_id,
                        self._playlist_position,
                    )

                elif self._album_id is not None:
                    result = play_method(
                        self._album_id,
                        self._spotify_uri,
                    )

                elif self._playlist_id is not None:
                    result = play_method(
                        self._playlist_id,
                        self._spotify_uri,
                    )

                else:
                    result = play_method(
                        self._spotify_uri
                    )

            except Exception:
                self._fail(
                    "playback_failed",
                    (
                        "Spotify playback could "
                        "not be started."
                    ),
                )
                return

            if not isinstance(
                result,
                SpotifyPlaybackServiceResult,
            ):
                self._fail(
                    "invalid_service_result",
                    (
                        "Spotify playback returned "
                        "an invalid result."
                    ),
                )
                return

            self.result_ready.emit(
                result
            )

        finally:
            self.finished.emit()



class _SpotifyPlaybackControlWorker(
    QObject
):
    result_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
    )

    finished = pyqtSignal()

    def __init__(
        self,
        service_factory: Callable,
        control_name: str,
        *,
        control_argument=None,
    ) -> None:
        super().__init__()

        self._service_factory = (
            service_factory
        )

        self._control_name = (
            control_name
        )

        self._control_argument = (
            control_argument
        )

    def _fail(
        self,
        error_code: str,
        message: str,
    ) -> None:
        self.failed.emit(
            error_code,
            message,
        )

    @pyqtSlot()
    def run(
        self,
    ) -> None:
        try:
            try:
                service = (
                    self._service_factory()
                )

            except Exception:
                self._fail(
                    "runtime_setup_failed",
                    (
                        "Spotify playback control "
                        "could not be prepared."
                    ),
                )
                return

            control_method = getattr(
                service,
                self._control_name,
                None,
            )

            if not callable(
                control_method
            ):
                self._fail(
                    "invalid_service",
                    (
                        "Spotify playback service "
                        "controls are unavailable."
                    ),
                )
                return

            try:
                if self._control_argument is None:
                    result = control_method()
                else:
                    result = control_method(
                        self._control_argument
                    )

            except Exception:
                self._fail(
                    "playback_failed",
                    (
                        "Spotify playback control "
                        "failed."
                    ),
                )
                return

            if not isinstance(
                result,
                SpotifyPlaybackServiceResult,
            ):
                self._fail(
                    "invalid_service_result",
                    (
                        "Spotify playback control "
                        "returned an invalid result."
                    ),
                )
                return

            self.result_ready.emit(
                result
            )

        finally:
            self.finished.emit()


class SpotifyQtPlaybackRuntime(
    QObject
):
    result_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
    )

    busy_changed = pyqtSignal(
        bool
    )

    playback_started = pyqtSignal(
        str
    )

    playback_finished = pyqtSignal(
        str
    )

    control_started = pyqtSignal(
        str
    )

    control_finished = pyqtSignal(
        str
    )

    def __init__(
        self,
        service_factory: Callable,
        *,
        shutdown_wait_ms: int = (
            DEFAULT_SPOTIFY_PLAYBACK_SHUTDOWN_WAIT_MS
        ),
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        if not callable(
            service_factory
        ):
            raise TypeError(
                (
                    "service_factory must "
                    "be callable"
                )
            )

        self._service_factory = (
            service_factory
        )

        self._shutdown_wait_ms = (
            _validate_shutdown_wait_ms(
                shutdown_wait_ms
            )
        )

        self._thread = None
        self._worker = None

        self._busy = False
        self._active_uri = None
        self._active_control = None
        self._shutting_down = False

    @property
    def busy(
        self,
    ) -> bool:
        return self._busy

    @property
    def active_uri(
        self,
    ) -> str | None:
        return self._active_uri

    @property
    def shutting_down(
        self,
    ) -> bool:
        return self._shutting_down

    def _set_busy(
        self,
        busy: bool,
    ) -> None:
        checked = bool(
            busy
        )

        if checked == self._busy:
            return

        self._busy = checked

        self.busy_changed.emit(
            checked
        )

    def resume_playback(
        self,
    ) -> None:
        self._start_control(
            "resume_playback"
        )

    def pause_playback(
        self,
    ) -> None:
        self._start_control(
            "pause_playback"
        )

    def skip_next(
        self,
    ) -> None:
        self._start_control(
            "skip_next"
        )

    def skip_previous(
        self,
    ) -> None:
        self._start_control(
            "skip_previous"
        )

    def seek_to_seconds(
        self,
        seconds,
    ) -> None:
        if isinstance(
            seconds,
            bool,
        ):
            raise TypeError(
                "seconds must be a number"
            )

        try:
            from math import isfinite

            checked_seconds = float(
                seconds
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise TypeError(
                "seconds must be a number"
            ) from error

        if (
            not isfinite(
                checked_seconds
            )
            or checked_seconds < 0
        ):
            raise ValueError(
                "seconds must be finite and non-negative"
            )

        self._start_control(
            "seek_to_seconds",
            control_argument=checked_seconds,
        )

    def set_shuffle(
        self,
        enabled,
    ) -> None:
        if not isinstance(
            enabled,
            bool,
        ):
            raise TypeError(
                "enabled must be a boolean"
            )

        self._start_control(
            "set_shuffle",
            control_argument=enabled,
        )

    def set_repeat_mode(
        self,
        mode,
    ) -> None:
        if not isinstance(
            mode,
            str,
        ):
            raise TypeError(
                "mode must be a string"
            )

        checked = mode.strip()

        if (
            checked != mode
            or checked
            not in {
                "off",
                "context",
                "track",
            }
        ):
            raise ValueError(
                (
                    "mode must be off, "
                    "context, or track"
                )
            )

        self._start_control(
            "set_repeat_mode",
            control_argument=checked,
        )

    def _start_control(
        self,
        control_name: str,
        *,
        control_argument=None,
    ) -> None:
        if not isinstance(
            control_name,
            str,
        ):
            raise TypeError(
                (
                    "control_name must "
                    "be a string"
                )
            )

        checked_control = (
            control_name.strip()
        )

        if (
            checked_control
            not in SPOTIFY_PLAYBACK_CONTROL_METHODS
        ):
            raise ValueError(
                (
                    "Unsupported Spotify "
                    "playback control."
                )
            )

        if self._shutting_down:
            raise SpotifyQtPlaybackRuntimeError(
                "shutting_down",
                (
                    "Spotify playback is shutting "
                    "down."
                ),
            )

        if self._busy:
            raise SpotifyQtPlaybackRuntimeError(
                "busy",
                (
                    "A Spotify playback request "
                    "is already running."
                ),
            )

        thread = QThread()

        worker = (
            _SpotifyPlaybackControlWorker(
                self._service_factory,
                checked_control,
                control_argument=(
                    control_argument
                ),
            )
        )

        worker.moveToThread(
            thread
        )

        thread.started.connect(
            worker.run
        )

        worker.result_ready.connect(
            self._handle_worker_result
        )

        worker.failed.connect(
            self._handle_worker_failure
        )

        worker.finished.connect(
            thread.quit
        )

        worker.finished.connect(
            worker.deleteLater
        )

        thread.finished.connect(
            self._handle_thread_finished
        )

        thread.finished.connect(
            thread.deleteLater
        )

        self._thread = thread
        self._worker = worker
        self._active_uri = None
        self._active_control = (
            checked_control
        )

        self._set_busy(
            True
        )

        self.control_started.emit(
            checked_control
        )

        try:
            thread.start()

        except Exception as error:
            self._complete_thread(
                thread
            )

            try:
                thread.deleteLater()

            except Exception:
                pass

            raise SpotifyQtPlaybackRuntimeError(
                "thread_start_failed",
                (
                    "Spotify playback control "
                    "could not start."
                ),
            ) from error

    def play_playlist_position(
        self,
        playlist_id,
        position,
    ) -> None:
        if not isinstance(
            playlist_id,
            str,
        ):
            raise TypeError(
                "playlist_id must be a string"
            )

        checked_playlist_id = (
            playlist_id.strip()
        )

        if not checked_playlist_id:
            raise ValueError(
                "playlist_id cannot be empty"
            )

        if (
            isinstance(
                position,
                bool,
            )
            or not isinstance(
                position,
                int,
            )
        ):
            raise TypeError(
                (
                    "playlist position must "
                    "be an integer"
                )
            )

        if position < 0:
            raise ValueError(
                (
                    "playlist position cannot "
                    "be negative"
                )
            )

        context_uri = (
            "spotify:playlist:"
            + checked_playlist_id
        )

        self._start_playback(
            context_uri,
            playlist_id=(
                checked_playlist_id
            ),
            playlist_position=position,
        )

    def play_playlist_track(
        self,
        playlist_id,
        spotify_uri,
    ) -> None:
        if not isinstance(
            playlist_id,
            str,
        ):
            raise TypeError(
                "playlist_id must be a string"
            )

        checked_playlist_id = (
            playlist_id.strip()
        )

        if not checked_playlist_id:
            raise ValueError(
                "playlist_id cannot be empty"
            )

        self._start_playback(
            spotify_uri,
            playlist_id=(
                checked_playlist_id
            ),
        )

    def play_album_track(
        self,
        album_id,
        spotify_uri,
    ) -> None:
        if not isinstance(
            album_id,
            str,
        ):
            raise TypeError(
                "album_id must be a string"
            )

        checked_album_id = (
            album_id.strip()
        )

        if (
            not checked_album_id
            or not checked_album_id.isascii()
            or not checked_album_id.isalnum()
        ):
            raise ValueError(
                "album_id is invalid"
            )

        self._start_playback(
            spotify_uri,
            album_id=checked_album_id,
        )

    def play_track(
        self,
        spotify_uri,
    ) -> None:
        self._start_playback(
            spotify_uri
        )

    def _start_playback(
        self,
        spotify_uri,
        *,
        album_id: str | None = None,
        playlist_id: str | None = None,
        playlist_position: int | None = None,
    ) -> None:
        if playlist_position is None:
            checked_uri = (
                _validate_playback_uri(
                    spotify_uri
                )
            )

        else:
            if playlist_id is None:
                raise ValueError(
                    (
                        "playlist position playback "
                        "requires a playlist ID"
                    )
                )

            checked_uri = spotify_uri

        if self._shutting_down:
            raise SpotifyQtPlaybackRuntimeError(
                "shutting_down",
                (
                    "Spotify playback is shutting "
                    "down."
                ),
            )

        if self._busy:
            raise SpotifyQtPlaybackRuntimeError(
                "busy",
                (
                    "A Spotify playback request "
                    "is already running."
                ),
            )

        thread = QThread()

        worker = _SpotifyPlaybackWorker(
            self._service_factory,
            checked_uri,
            album_id=album_id,
            playlist_id=playlist_id,
            playlist_position=(
                playlist_position
            ),
        )

        worker.moveToThread(
            thread
        )

        thread.started.connect(
            worker.run
        )

        worker.result_ready.connect(
            self._handle_worker_result
        )

        worker.failed.connect(
            self._handle_worker_failure
        )

        worker.finished.connect(
            thread.quit
        )

        worker.finished.connect(
            worker.deleteLater
        )

        thread.finished.connect(
            self._handle_thread_finished
        )

        thread.finished.connect(
            thread.deleteLater
        )

        self._thread = thread
        self._worker = worker
        self._active_control = None
        self._active_uri = checked_uri

        self._set_busy(
            True
        )

        self.playback_started.emit(
            checked_uri
        )

        try:
            thread.start()

        except Exception as error:
            self._complete_thread(
                thread
            )

            try:
                thread.deleteLater()
            except Exception:
                pass

            raise SpotifyQtPlaybackRuntimeError(
                "thread_start_failed",
                (
                    "Spotify playback could "
                    "not start."
                ),
            ) from error


    @pyqtSlot(
        object
    )
    def _handle_worker_result(
        self,
        result,
    ) -> None:
        if self._shutting_down:
            return

        self.result_ready.emit(
            result
        )

    @pyqtSlot(
        str,
        str,
    )
    def _handle_worker_failure(
        self,
        error_code: str,
        message: str,
    ) -> None:
        if self._shutting_down:
            return

        self.failed.emit(
            error_code,
            message,
        )

    @pyqtSlot()
    def _handle_thread_finished(
        self,
    ) -> None:
        thread = self._thread

        if thread is None:
            return

        self._complete_thread(
            thread
        )

    def _complete_thread(
        self,
        thread,
    ) -> None:
        if (
            self._thread
            is not thread
        ):
            return

        spotify_uri = (
            self._active_uri
            or ""
        )

        control_name = (
            self._active_control
            or ""
        )

        self._thread = None
        self._worker = None
        self._active_uri = None
        self._active_control = None

        self._set_busy(
            False
        )

        if control_name:
            self.control_finished.emit(
                control_name
            )
            return

        self.playback_finished.emit(
            spotify_uri
        )

    def shutdown(
        self,
    ) -> bool:
        self._shutting_down = True

        thread = self._thread

        if thread is None:
            self._worker = None
            self._active_uri = None
            self._active_control = None

            self._set_busy(
                False
            )

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
            self._complete_thread(
                thread
            )

        return stopped
