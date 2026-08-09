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
        playlist_id: str | None = None,
    ) -> None:
        super().__init__()

        self._service_factory = (
            service_factory
        )

        self._spotify_uri = (
            spotify_uri
        )

        self._playlist_id = (
            playlist_id
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

            method_name = (
                "play_playlist_track"
                if self._playlist_id is not None
                else "play_track"
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
                if self._playlist_id is None:
                    result = play_method(
                        self._spotify_uri
                    )

                else:
                    result = play_method(
                        self._playlist_id,
                        self._spotify_uri,
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
        playlist_id: str | None = None,
    ) -> None:
        checked_uri = (
            _validate_playback_uri(
                spotify_uri
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

        worker = _SpotifyPlaybackWorker(
            self._service_factory,
            checked_uri,
            playlist_id=playlist_id,
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

        self._thread = None
        self._worker = None
        self._active_uri = None

        self._set_busy(
            False
        )

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
