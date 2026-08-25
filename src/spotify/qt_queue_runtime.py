from __future__ import annotations

from PyQt6.QtCore import (
    QObject,
    QThread,
    pyqtSignal,
)

from src.spotify.queue_service import (
    SpotifyQueueServiceResult,
)


class SpotifyQtQueueRuntimeError(
    RuntimeError
):
    def __init__(
        self,
        error_code: str,
        message: str,
    ) -> None:
        self.error_code = str(
            error_code
            or "queue_runtime_error"
        )

        super().__init__(
            str(
                message
                or "Spotify Queue runtime error."
            )
        )


class _SpotifyQueueWorker(
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
        service_factory,
    ) -> None:
        super().__init__()

        self._service_factory = (
            service_factory
        )

    def run(
        self,
    ) -> None:
        try:
            service = (
                self._service_factory()
            )

        except Exception:
            self.failed.emit(
                "service_error",
                (
                    "Spotify Queue runtime could "
                    "not create its service."
                ),
            )

            self.finished.emit()
            return

        getter = getattr(
            service,
            "get_queue",
            None,
        )

        if not callable(
            getter
        ):
            self.failed.emit(
                "invalid_service",
                (
                    "Spotify Queue service is "
                    "unavailable."
                ),
            )

            self.finished.emit()
            return

        try:
            result = getter()

        except Exception:
            self.failed.emit(
                "service_error",
                (
                    "Spotify Queue could not "
                    "be loaded."
                ),
            )

            self.finished.emit()
            return

        if not isinstance(
            result,
            SpotifyQueueServiceResult,
        ):
            self.failed.emit(
                "invalid_result",
                (
                    "Spotify Queue service returned "
                    "an invalid result."
                ),
            )

            self.finished.emit()
            return

        self.result_ready.emit(
            result
        )

        self.finished.emit()


class SpotifyQtQueueRuntime(
    QObject
):
    queue_ready = pyqtSignal(
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
        service_factory,
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        if not callable(
            service_factory
        ):
            raise TypeError(
                "service_factory must be callable"
            )

        self._service_factory = (
            service_factory
        )

        self._busy = False
        self._shutting_down = False

        self._thread = None
        self._worker = None

    @property
    def busy(
        self,
    ) -> bool:
        return self._busy

    @property
    def shutting_down(
        self,
    ) -> bool:
        return self._shutting_down

    def load_queue(
        self,
    ) -> None:
        if self._shutting_down:
            raise SpotifyQtQueueRuntimeError(
                "shutting_down",
                (
                    "Spotify Queue runtime is "
                    "shutting down."
                ),
            )

        if self._busy:
            raise SpotifyQtQueueRuntimeError(
                "busy",
                (
                    "Spotify Queue runtime is "
                    "already busy."
                ),
            )

        thread = QThread(
            self
        )

        worker = _SpotifyQueueWorker(
            self._service_factory
        )

        worker.moveToThread(
            thread
        )

        worker.result_ready.connect(
            self.queue_ready.emit
        )

        worker.failed.connect(
            self.failed.emit
        )

        worker.finished.connect(
            thread.quit
        )

        worker.finished.connect(
            worker.deleteLater
        )

        thread.started.connect(
            worker.run
        )

        thread.finished.connect(
            self._thread_finished
        )

        self._thread = thread
        self._worker = worker

        self._set_busy(
            True
        )

        self.operation_started.emit()

        thread.start()

    def _set_busy(
        self,
        busy: bool,
    ) -> None:
        checked = bool(
            busy
        )

        if self._busy == checked:
            return

        self._busy = checked

        self.busy_changed.emit(
            checked
        )

    def _thread_finished(
        self,
    ) -> None:
        thread = self._thread

        self._thread = None
        self._worker = None

        if thread is not None:
            thread.deleteLater()

        if not self._busy:
            return

        self._set_busy(
            False
        )

        self.operation_finished.emit()

    def shutdown(
        self,
        timeout_ms: int = 3000,
    ) -> bool:
        if (
            isinstance(
                timeout_ms,
                bool,
            )
            or not isinstance(
                timeout_ms,
                int,
            )
        ):
            raise TypeError(
                "timeout_ms must be an integer"
            )

        if timeout_ms < 0:
            raise ValueError(
                "timeout_ms cannot be negative"
            )

        self._shutting_down = True

        thread = self._thread

        if (
            thread is None
            or not thread.isRunning()
        ):
            if self._busy:
                self._thread_finished()

            return True

        thread.requestInterruption()
        thread.quit()

        completed = thread.wait(
            timeout_ms
        )

        if not completed:
            return False

        if self._thread is thread:
            self._thread_finished()

        return True
