from __future__ import annotations

from collections.abc import (
    Callable,
    Iterable,
)

from PyQt6.QtCore import (
    QObject,
    QThread,
    pyqtSignal,
    pyqtSlot,
)

from src.spotify.search_models import (
    SpotifySearchItemType,
)
from src.spotify.search_service import (
    DEFAULT_SPOTIFY_SEARCH_LIMIT,
    SpotifySearchServiceResult,
)


DEFAULT_SPOTIFY_SEARCH_SHUTDOWN_WAIT_MS = 11000


class SpotifyQtSearchRuntimeError(
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
    value: int,
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
                "shutdown_wait_ms must "
                "be an integer"
            )
        )

    if not 1 <= value <= 60000:
        raise ValueError(
            (
                "shutdown_wait_ms must be "
                "between 1 and 60000"
            )
        )

    return value


class _SpotifySearchWorker(
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
        query,
        *,
        types,
        limit,
        offset,
        market,
    ) -> None:
        super().__init__()

        self._service_factory = (
            service_factory
        )

        self._query = query

        self._types = types

        self._limit = limit

        self._offset = offset

        self._market = market

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
                self.failed.emit(
                    "runtime_setup_failed",
                    (
                        "Spotify Search could not "
                        "be prepared."
                    ),
                )

                return

            search = getattr(
                service,
                "search",
                None,
            )

            if not callable(
                search
            ):
                self.failed.emit(
                    "runtime_setup_failed",
                    (
                        "Spotify Search could not "
                        "be prepared."
                    ),
                )

                return

            try:
                result = search(
                    self._query,
                    types=self._types,
                    limit=self._limit,
                    offset=self._offset,
                    market=self._market,
                )

            except (
                TypeError,
                ValueError,
            ):
                self.failed.emit(
                    "invalid_request",
                    (
                        "The Spotify Search request "
                        "is invalid."
                    ),
                )

                return

            except Exception:
                self.failed.emit(
                    "operation_failed",
                    (
                        "Spotify Search could not "
                        "be completed."
                    ),
                )

                return

            if not isinstance(
                result,
                SpotifySearchServiceResult,
            ):
                self.failed.emit(
                    "invalid_result",
                    (
                        "Spotify Search returned "
                        "an invalid result."
                    ),
                )

                return

            self.result_ready.emit(
                result
            )

        finally:
            self.finished.emit()


class SpotifyQtSearchRuntime(
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

    search_started = pyqtSignal(
        str
    )

    search_finished = pyqtSignal(
        str
    )

    def __init__(
        self,
        service_factory: Callable,
        *,
        shutdown_wait_ms: int = (
            DEFAULT_SPOTIFY_SEARCH_SHUTDOWN_WAIT_MS
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

        self._active_query = None

        self._shutting_down = False

    @property
    def busy(
        self,
    ) -> bool:
        return self._busy

    @property
    def active_query(
        self,
    ) -> str | None:
        return self._active_query

    @property
    def shutting_down(
        self,
    ) -> bool:
        return self._shutting_down

    def _set_busy(
        self,
        busy: bool,
    ) -> None:
        busy = bool(
            busy
        )

        if busy == self._busy:
            return

        self._busy = busy

        self.busy_changed.emit(
            busy
        )

    @staticmethod
    def _display_query(
        query,
    ) -> str:
        if not isinstance(
            query,
            str,
        ):
            return ""

        return query.strip()

    def search(
        self,
        query,
        *,
        types: Iterable[
            SpotifySearchItemType | str
        ] | None = None,
        limit: int = (
            DEFAULT_SPOTIFY_SEARCH_LIMIT
        ),
        offset: int = 0,
        market: str | None = None,
    ) -> None:
        if self._shutting_down:
            raise SpotifyQtSearchRuntimeError(
                "shutting_down",
                (
                    "Spotify Search is shutting "
                    "down."
                ),
            )

        if self._busy:
            raise SpotifyQtSearchRuntimeError(
                "busy",
                (
                    "Spotify Search is already "
                    "running."
                ),
            )

        display_query = (
            self._display_query(
                query
            )
        )

        thread = QThread()

        worker = _SpotifySearchWorker(
            self._service_factory,
            query,
            types=types,
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

        self._active_query = (
            display_query
        )

        self._set_busy(
            True
        )

        self.search_started.emit(
            display_query
        )

        try:
            thread.start()

        except Exception as error:
            self._thread = None
            self._worker = None
            self._active_query = None

            self._set_busy(
                False
            )

            raise SpotifyQtSearchRuntimeError(
                "thread_start_failed",
                (
                    "Spotify Search could not "
                    "start."
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

        if not isinstance(
            result,
            SpotifySearchServiceResult,
        ):
            self.failed.emit(
                "invalid_result",
                (
                    "Spotify Search returned "
                    "an invalid result."
                ),
            )

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

        safe_code = str(
            error_code
            or "operation_failed"
        ).strip()

        safe_message = str(
            message
            or (
                "Spotify Search could not "
                "be completed."
            )
        ).strip()

        self.failed.emit(
            safe_code,
            safe_message,
        )

    def _complete_thread(
        self,
        thread,
    ) -> None:
        if (
            thread is None
            or thread is not self._thread
        ):
            return

        finished_query = (
            self._active_query
            or ""
        )

        self._thread = None
        self._worker = None

        self._active_query = None

        self._set_busy(
            False
        )

        self.search_finished.emit(
            finished_query
        )

    @pyqtSlot()
    def _handle_thread_finished(
        self,
    ) -> None:
        thread = self.sender()

        self._complete_thread(
            thread
        )

    def shutdown(
        self,
    ) -> bool:
        self._shutting_down = True

        thread = self._thread

        if thread is None:
            self._worker = None
            self._active_query = None

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
