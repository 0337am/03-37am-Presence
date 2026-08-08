from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import (
    QObject,
    QThread,
    pyqtSignal,
    pyqtSlot,
)

from src.spotify.playlist_service import (
    SpotifyPlaylistServiceResult,
)
from src.spotify.resolved_playlist_service import (
    SpotifyResolvedPlaylistServiceResult,
)


DEFAULT_SPOTIFY_PLAYLIST_RUNTIME_LIMIT = 50
DEFAULT_SPOTIFY_PLAYLIST_SHUTDOWN_WAIT_MS = 5000

OPERATION_PLAYLISTS = "playlists"
OPERATION_PLAYLIST_ITEMS = "playlist_items"


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
            "shutdown_wait_ms must be an integer"
        )

    if value < 0:
        raise ValueError(
            "shutdown_wait_ms cannot be negative"
        )

    return value


def _validate_playlist_id(
    value,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "playlist_id must be a string"
        )

    checked = value.strip()

    if not checked:
        raise ValueError(
            "playlist_id cannot be empty"
        )

    return checked


class SpotifyQtPlaylistRuntimeError(
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


class _SpotifyPlaylistWorker(
    QObject
):
    result_ready = pyqtSignal(
        str,
        str,
        object,
    )

    failed = pyqtSignal(
        str,
        str,
        str,
        str,
    )

    finished = pyqtSignal()

    def __init__(
        self,
        service_factory: Callable,
        operation: str,
        target: str,
        *,
        limit,
        offset,
        market,
    ) -> None:
        super().__init__()

        self._service_factory = (
            service_factory
        )

        self._operation = str(
            operation
        )

        self._target = str(
            target
        )

        self._limit = limit
        self._offset = offset
        self._market = market

    def _fail(
        self,
        error_code: str,
        message: str,
    ) -> None:
        self.failed.emit(
            self._operation,
            self._target,
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
                        "Spotify playlists could "
                        "not be prepared."
                    ),
                )
                return

            if (
                self._operation
                == OPERATION_PLAYLISTS
            ):
                method_name = (
                    "get_current_playlists"
                )

                expected_type = (
                    SpotifyPlaylistServiceResult
                )

            elif (
                self._operation
                == OPERATION_PLAYLIST_ITEMS
            ):
                method_name = (
                    "get_playlist_items"
                )

                expected_type = (
                    SpotifyResolvedPlaylistServiceResult
                )

            else:
                self._fail(
                    "invalid_operation",
                    (
                        "The Spotify playlist "
                        "operation is invalid."
                    ),
                )
                return

            operation = getattr(
                service,
                method_name,
                None,
            )

            if not callable(
                operation
            ):
                self._fail(
                    "runtime_setup_failed",
                    (
                        "Spotify playlists could "
                        "not be prepared."
                    ),
                )
                return

            try:
                if (
                    self._operation
                    == OPERATION_PLAYLISTS
                ):
                    result = operation(
                        limit=self._limit,
                        offset=self._offset,
                    )

                else:
                    result = operation(
                        self._target,
                        limit=self._limit,
                        offset=self._offset,
                        market=self._market,
                    )

            except (
                TypeError,
                ValueError,
            ):
                self._fail(
                    "invalid_request",
                    (
                        "The Spotify playlist "
                        "request is invalid."
                    ),
                )
                return

            except Exception:
                self._fail(
                    "operation_failed",
                    (
                        "Spotify playlists could "
                        "not be loaded."
                    ),
                )
                return

            if not isinstance(
                result,
                expected_type,
            ):
                self._fail(
                    "invalid_result",
                    (
                        "Spotify playlists returned "
                        "an invalid result."
                    ),
                )
                return

            self.result_ready.emit(
                self._operation,
                self._target,
                result,
            )

        finally:
            self.finished.emit()


class SpotifyQtPlaylistRuntime(
    QObject
):
    playlists_ready = pyqtSignal(
        object
    )

    playlist_items_ready = pyqtSignal(
        str,
        object,
    )

    failed = pyqtSignal(
        str,
        str,
        str,
        str,
    )

    busy_changed = pyqtSignal(
        bool
    )

    operation_started = pyqtSignal(
        str,
        str,
    )

    operation_finished = pyqtSignal(
        str,
        str,
    )

    def __init__(
        self,
        playlist_service_factory: Callable,
        resolved_service_factory: Callable,
        *,
        shutdown_wait_ms: int = (
            DEFAULT_SPOTIFY_PLAYLIST_SHUTDOWN_WAIT_MS
        ),
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        if not callable(
            playlist_service_factory
        ):
            raise TypeError(
                (
                    "playlist_service_factory must "
                    "be callable"
                )
            )

        if not callable(
            resolved_service_factory
        ):
            raise TypeError(
                (
                    "resolved_service_factory must "
                    "be callable"
                )
            )

        self._playlist_service_factory = (
            playlist_service_factory
        )

        self._resolved_service_factory = (
            resolved_service_factory
        )

        self._shutdown_wait_ms = (
            _validate_shutdown_wait_ms(
                shutdown_wait_ms
            )
        )

        self._thread = None
        self._worker = None

        self._busy = False
        self._active_operation = None
        self._active_target = None
        self._shutting_down = False

    @property
    def busy(
        self,
    ) -> bool:
        return self._busy

    @property
    def active_operation(
        self,
    ) -> str | None:
        return self._active_operation

    @property
    def active_target(
        self,
    ) -> str | None:
        return self._active_target

    @property
    def shutting_down(
        self,
    ) -> bool:
        return self._shutting_down

    def _set_busy(
        self,
        value: bool,
    ) -> None:
        value = bool(
            value
        )

        if value == self._busy:
            return

        self._busy = value

        self.busy_changed.emit(
            value
        )

    def load_playlists(
        self,
        *,
        limit: int = (
            DEFAULT_SPOTIFY_PLAYLIST_RUNTIME_LIMIT
        ),
        offset: int = 0,
    ) -> None:
        self._start_operation(
            OPERATION_PLAYLISTS,
            "",
            self._playlist_service_factory,
            limit=limit,
            offset=offset,
            market=None,
        )

    def load_playlist_items(
        self,
        playlist_id,
        *,
        limit: int = (
            DEFAULT_SPOTIFY_PLAYLIST_RUNTIME_LIMIT
        ),
        offset: int = 0,
        market: str | None = None,
    ) -> None:
        checked_playlist_id = (
            _validate_playlist_id(
                playlist_id
            )
        )

        self._start_operation(
            OPERATION_PLAYLIST_ITEMS,
            checked_playlist_id,
            self._resolved_service_factory,
            limit=limit,
            offset=offset,
            market=market,
        )

    def _start_operation(
        self,
        operation: str,
        target: str,
        service_factory: Callable,
        *,
        limit,
        offset,
        market,
    ) -> None:
        if self._shutting_down:
            raise SpotifyQtPlaylistRuntimeError(
                "shutting_down",
                (
                    "Spotify playlists are shutting "
                    "down."
                ),
            )

        if self._busy:
            raise SpotifyQtPlaylistRuntimeError(
                "busy",
                (
                    "A Spotify playlist request is "
                    "already running."
                ),
            )

        thread = QThread()

        worker = _SpotifyPlaylistWorker(
            service_factory,
            operation,
            target,
            limit=limit,
            offset=offset,
            market=market,
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

        self._active_operation = (
            operation
        )

        self._active_target = (
            target
        )

        self._set_busy(
            True
        )

        self.operation_started.emit(
            operation,
            target,
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

            raise SpotifyQtPlaylistRuntimeError(
                "thread_start_failed",
                (
                    "Spotify playlists could "
                    "not start."
                ),
            ) from error

    @pyqtSlot(
        str,
        str,
        object,
    )
    def _handle_worker_result(
        self,
        operation: str,
        target: str,
        result,
    ) -> None:
        if self._shutting_down:
            return

        if (
            operation
            == OPERATION_PLAYLISTS
        ):
            self.playlists_ready.emit(
                result
            )
            return

        if (
            operation
            == OPERATION_PLAYLIST_ITEMS
        ):
            self.playlist_items_ready.emit(
                target,
                result,
            )

    @pyqtSlot(
        str,
        str,
        str,
        str,
    )
    def _handle_worker_failure(
        self,
        operation: str,
        target: str,
        error_code: str,
        message: str,
    ) -> None:
        if self._shutting_down:
            return

        self.failed.emit(
            operation,
            target,
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

        operation = (
            self._active_operation
            or ""
        )

        target = (
            self._active_target
            or ""
        )

        self._thread = None
        self._worker = None

        self._active_operation = None
        self._active_target = None

        self._set_busy(
            False
        )

        self.operation_finished.emit(
            operation,
            target,
        )

    def shutdown(
        self,
    ) -> bool:
        self._shutting_down = True

        thread = self._thread

        if thread is None:
            self._worker = None
            self._active_operation = None
            self._active_target = None

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
