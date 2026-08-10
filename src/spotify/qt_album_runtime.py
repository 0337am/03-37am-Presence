from collections.abc import Callable

from PyQt6.QtCore import (
    QObject,
    QThread,
    pyqtSignal,
    pyqtSlot,
)

from src.spotify.album_service import (
    DEFAULT_SPOTIFY_ALBUM_LIMIT,
    SpotifyAlbumServiceResult,
    _validate_album_id,
    _validate_limit,
    _validate_market,
    _validate_offset,
)


OPERATION_ALBUM = "album"
OPERATION_ALBUM_TRACKS = "album_tracks"

DEFAULT_SPOTIFY_ALBUM_RUNTIME_LIMIT = (
    DEFAULT_SPOTIFY_ALBUM_LIMIT
)

DEFAULT_SPOTIFY_ALBUM_SHUTDOWN_WAIT_MS = 2000


class SpotifyQtAlbumRuntimeError(
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
            or "album_runtime_error"
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
        or value < 0
    ):
        raise ValueError(
            (
                "shutdown_wait_ms must be "
                "zero or greater."
            )
        )

    return value


class _SpotifyAlbumWorker(
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
        limit: int,
        offset: int,
        market: str,
    ) -> None:
        super().__init__()

        self._service_factory = (
            service_factory
        )

        self._operation = operation
        self._target = target

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
                    "service_error",
                    (
                        "Spotify albums could "
                        "not start."
                    ),
                )
                return

            try:
                if (
                    self._operation
                    == OPERATION_ALBUM
                ):
                    result = (
                        service.get_album(
                            self._target,
                            market=(
                                self._market
                                or None
                            ),
                        )
                    )

                elif (
                    self._operation
                    == OPERATION_ALBUM_TRACKS
                ):
                    result = (
                        service.get_album_tracks(
                            self._target,
                            limit=self._limit,
                            offset=self._offset,
                            market=(
                                self._market
                                or None
                            ),
                        )
                    )

                else:
                    self._fail(
                        "invalid_operation",
                        (
                            "Spotify album request "
                            "was invalid."
                        ),
                    )
                    return

            except Exception:
                self._fail(
                    "runtime_error",
                    (
                        "Spotify album data could "
                        "not be loaded."
                    ),
                )
                return

            if not isinstance(
                result,
                SpotifyAlbumServiceResult,
            ):
                self._fail(
                    "invalid_result",
                    (
                        "Spotify albums returned "
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


class SpotifyQtAlbumRuntime(
    QObject
):
    album_ready = pyqtSignal(
        str,
        object,
    )

    album_tracks_ready = pyqtSignal(
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
        album_service_factory: Callable,
        *,
        shutdown_wait_ms: int = (
            DEFAULT_SPOTIFY_ALBUM_SHUTDOWN_WAIT_MS
        ),
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        if not callable(
            album_service_factory
        ):
            raise TypeError(
                (
                    "album_service_factory must "
                    "be callable"
                )
            )

        self._album_service_factory = (
            album_service_factory
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

    def load_album(
        self,
        album_id,
        *,
        market: str | None = None,
    ) -> None:
        checked_album_id = (
            _validate_album_id(
                album_id
            )
        )

        checked_market = (
            _validate_market(
                market
            )
        )

        self._start_operation(
            OPERATION_ALBUM,
            checked_album_id,
            limit=(
                DEFAULT_SPOTIFY_ALBUM_RUNTIME_LIMIT
            ),
            offset=0,
            market=checked_market,
        )

    def load_album_tracks(
        self,
        album_id,
        *,
        limit: int = (
            DEFAULT_SPOTIFY_ALBUM_RUNTIME_LIMIT
        ),
        offset: int = 0,
        market: str | None = None,
    ) -> None:
        checked_album_id = (
            _validate_album_id(
                album_id
            )
        )

        checked_limit = (
            _validate_limit(
                limit
            )
        )

        checked_offset = (
            _validate_offset(
                offset
            )
        )

        checked_market = (
            _validate_market(
                market
            )
        )

        self._start_operation(
            OPERATION_ALBUM_TRACKS,
            checked_album_id,
            limit=checked_limit,
            offset=checked_offset,
            market=checked_market,
        )

    def _start_operation(
        self,
        operation: str,
        target: str,
        *,
        limit: int,
        offset: int,
        market: str,
    ) -> None:
        if self._shutting_down:
            raise SpotifyQtAlbumRuntimeError(
                "shutting_down",
                (
                    "Spotify albums are shutting "
                    "down."
                ),
            )

        if self._busy:
            raise SpotifyQtAlbumRuntimeError(
                "busy",
                (
                    "A Spotify album request is "
                    "already running."
                ),
            )

        thread = QThread()

        worker = _SpotifyAlbumWorker(
            self._album_service_factory,
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

            raise SpotifyQtAlbumRuntimeError(
                "thread_start_failed",
                (
                    "Spotify albums could "
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

        if operation == OPERATION_ALBUM:
            self.album_ready.emit(
                target,
                result,
            )

            return

        if (
            operation
            == OPERATION_ALBUM_TRACKS
        ):
            self.album_tracks_ready.emit(
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
        thread = self.sender()

        if (
            thread is not None
            and thread is not self._thread
        ):
            return

        self._complete_thread(
            self._thread
        )

    def _complete_thread(
        self,
        thread,
    ) -> None:
        if (
            thread is not None
            and self._thread is not thread
        ):
            return

        operation = (
            self._active_operation
        )

        target = (
            self._active_target
        )

        self._thread = None
        self._worker = None

        self._active_operation = None
        self._active_target = None

        self._set_busy(
            False
        )

        if (
            operation is not None
            and target is not None
        ):
            self.operation_finished.emit(
                operation,
                target,
            )

    def shutdown(
        self,
    ) -> None:
        if self._shutting_down:
            return

        self._shutting_down = True

        thread = self._thread

        if thread is None:
            self._complete_thread(
                None
            )
            return

        try:
            thread.quit()

        except Exception:
            pass

        try:
            if thread.isRunning():
                thread.wait(
                    self._shutdown_wait_ms
                )

        except Exception:
            pass

        try:
            running = (
                thread.isRunning()
            )

        except Exception:
            running = False

        if not running:
            self._complete_thread(
                thread
            )
