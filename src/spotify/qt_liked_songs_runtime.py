from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import (
    QObject,
    QThread,
    pyqtSignal,
    pyqtSlot,
)

from src.spotify.liked_songs_service import (
    SpotifyLikedSongsServiceResult,
)


DEFAULT_SPOTIFY_LIKED_SONGS_SHUTDOWN_WAIT_MS = 5000


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

    if value < 0:
        raise ValueError(
            (
                "shutdown_wait_ms cannot "
                "be negative"
            )
        )

    return value


class SpotifyQtLikedSongsRuntimeError(
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
        ).strip()

        self.message = str(
            message
        ).strip()


class _SpotifyLikedSongsWorker(
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
    ) -> None:
        super().__init__()

        self._service_factory = (
            service_factory
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
                        "Liked Songs could not "
                        "be prepared."
                    ),
                )
                return

            operation = getattr(
                service,
                "get_summary",
                None,
            )

            if not callable(
                operation
            ):
                self._fail(
                    "runtime_setup_failed",
                    (
                        "Liked Songs could not "
                        "be prepared."
                    ),
                )
                return

            try:
                result = operation()

            except Exception:
                self._fail(
                    "operation_failed",
                    (
                        "Liked Songs could not "
                        "be loaded."
                    ),
                )
                return

            if not isinstance(
                result,
                SpotifyLikedSongsServiceResult,
            ):
                self._fail(
                    "invalid_result",
                    (
                        "Liked Songs returned "
                        "an invalid result."
                    ),
                )
                return

            self.result_ready.emit(
                result
            )

        finally:
            self.finished.emit()


class _SpotifyLikedSongsTracksWorker(
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
        *,
        limit: int,
        offset: int,
        include_context: bool,
    ) -> None:
        super().__init__()

        self._service_factory = (
            service_factory
        )

        self._limit = limit
        self._offset = offset
        self._include_context = (
            include_context
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
                        "Liked Songs could not "
                        "be prepared."
                    ),
                )
                return

            operation = getattr(
                service,
                "get_tracks_page",
                None,
            )

            if not callable(
                operation
            ):
                self._fail(
                    "runtime_setup_failed",
                    (
                        "Liked Songs tracks could "
                        "not be prepared."
                    ),
                )
                return

            try:
                if self._include_context:
                    result = operation(
                        limit=self._limit,
                        offset=self._offset,
                        include_context=True,
                    )

                else:
                    result = operation(
                        limit=self._limit,
                        offset=self._offset,
                    )

            except Exception:
                self._fail(
                    "operation_failed",
                    (
                        "Liked Songs tracks could "
                        "not be loaded."
                    ),
                )
                return

            if not isinstance(
                result,
                SpotifyLikedSongsServiceResult,
            ):
                self._fail(
                    "invalid_result",
                    (
                        "Liked Songs returned "
                        "an invalid result."
                    ),
                )
                return

            self.result_ready.emit(
                result
            )

        finally:
            self.finished.emit()


class SpotifyQtLikedSongsRuntime(
    QObject
):
    summary_ready = pyqtSignal(
        object
    )

    tracks_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
    )

    busy_changed = pyqtSignal(
        bool
    )

    operation_started = pyqtSignal()
    operation_finished = pyqtSignal()

    def __init__(
        self,
        service_factory: Callable,
        *,
        shutdown_wait_ms: int = (
            DEFAULT_SPOTIFY_LIKED_SONGS_SHUTDOWN_WAIT_MS
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
        self._shutting_down = False

    @property
    def busy(
        self,
    ) -> bool:
        return self._busy

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

    def load_summary(
        self,
    ) -> None:
        if self._shutting_down:
            raise SpotifyQtLikedSongsRuntimeError(
                "shutting_down",
                (
                    "Liked Songs is shutting "
                    "down."
                ),
            )

        if self._busy:
            raise SpotifyQtLikedSongsRuntimeError(
                "busy",
                (
                    "A Liked Songs request is "
                    "already running."
                ),
            )

        thread = QThread()

        worker = _SpotifyLikedSongsWorker(
            self._service_factory
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

        self._set_busy(
            True
        )

        self.operation_started.emit()

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

            raise SpotifyQtLikedSongsRuntimeError(
                "thread_start_failed",
                (
                    "Liked Songs could not "
                    "start."
                ),
            ) from error


    def load_tracks_page(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        include_context: bool = False,
    ) -> None:
        if not isinstance(
            include_context,
            bool,
        ):
            raise TypeError(
                (
                    "include_context must be "
                    "a boolean"
                )
            )

        if (
            isinstance(
                limit,
                bool,
            )
            or not isinstance(
                limit,
                int,
            )
        ):
            raise TypeError(
                "limit must be an integer"
            )

        if (
            limit < 1
            or limit > 50
        ):
            raise ValueError(
                (
                    "limit must be between "
                    "1 and 50"
                )
            )

        if (
            isinstance(
                offset,
                bool,
            )
            or not isinstance(
                offset,
                int,
            )
        ):
            raise TypeError(
                "offset must be an integer"
            )

        if offset < 0:
            raise ValueError(
                "offset cannot be negative"
            )

        if self._shutting_down:
            raise SpotifyQtLikedSongsRuntimeError(
                "shutting_down",
                (
                    "Liked Songs is shutting "
                    "down."
                ),
            )

        if self._busy:
            raise SpotifyQtLikedSongsRuntimeError(
                "busy",
                (
                    "A Liked Songs request is "
                    "already running."
                ),
            )

        thread = QThread()

        worker = _SpotifyLikedSongsTracksWorker(
            self._service_factory,
            limit=limit,
            offset=offset,
            include_context=(
                include_context
            ),
        )

        worker.moveToThread(
            thread
        )

        thread.started.connect(
            worker.run
        )

        worker.result_ready.connect(
            self._handle_tracks_worker_result
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

        self._set_busy(
            True
        )

        self.operation_started.emit()

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

            raise SpotifyQtLikedSongsRuntimeError(
                "thread_start_failed",
                (
                    "Liked Songs could not "
                    "start."
                ),
            ) from error

    def _handle_worker_result(
        self,
        result,
    ) -> None:
        if self._shutting_down:
            return

        self.summary_ready.emit(
            result
        )

    def _handle_tracks_worker_result(
        self,
        result,
    ) -> None:
        if self._shutting_down:
            return

        self.tracks_ready.emit(
            result
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
        if self._thread is not thread:
            return

        self._thread = None
        self._worker = None

        self._set_busy(
            False
        )

        self.operation_finished.emit()

    def shutdown(
        self,
    ) -> bool:
        self._shutting_down = True

        thread = self._thread

        if thread is None:
            self._worker = None

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
