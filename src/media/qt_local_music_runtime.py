from __future__ import annotations

import threading
from collections.abc import Callable

from PyQt6.QtCore import (
    QObject,
    QThread,
    pyqtSignal,
    pyqtSlot,
)

from src.media.local_music_index import (
    LocalMusicIndex,
    LocalMusicIndexError,
    LocalMusicScanCancelled,
    LocalMusicScanResult,
)


DEFAULT_LOCAL_MUSIC_SHUTDOWN_WAIT_MS = (
    20000
)


class LocalMusicQtRuntimeError(
    RuntimeError
):
    def __init__(
        self,
        error_code: str,
        message: str,
    ) -> None:
        checked_code = str(
            error_code
            or "operation_failed"
        ).strip()

        checked_message = str(
            message
            or (
                "The Local Music operation "
                "could not be completed."
            )
        ).strip()

        super().__init__(
            checked_message
        )

        self.error_code = (
            checked_code
        )

        self.message = (
            checked_message
        )


def _checked_folders(
    folders,
) -> tuple[
    str,
    ...,
]:
    if not isinstance(
        folders,
        tuple,
    ):
        raise TypeError(
            (
                "folders must be a tuple "
                "of absolute folder paths"
            )
        )

    checked = []

    for folder in folders:
        if not isinstance(
            folder,
            str,
        ):
            raise TypeError(
                (
                    "folders must contain "
                    "strings"
                )
            )

        value = folder.strip()

        if not value:
            raise ValueError(
                (
                    "Local Music folder paths "
                    "cannot be empty."
                )
            )

        checked.append(
            value
        )

    return tuple(
        checked
    )


class LocalMusicScanWorker(
    QObject
):
    result_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
    )

    cancelled = pyqtSignal()

    finished = pyqtSignal()

    def __init__(
        self,
        *,
        folders: tuple[
            str,
            ...,
        ],
        index_factory: Callable = (
            LocalMusicIndex
        ),
    ) -> None:
        super().__init__()

        self._folders = (
            _checked_folders(
                folders
            )
        )

        if not callable(
            index_factory
        ):
            raise TypeError(
                (
                    "index_factory must "
                    "be callable"
                )
            )

        self._index_factory = (
            index_factory
        )

        self._cancel_event = (
            threading.Event()
        )

    @pyqtSlot()
    def request_cancel(
        self,
    ) -> None:
        self._cancel_event.set()

    @pyqtSlot()
    def run(
        self,
    ) -> None:
        try:
            if self._cancel_event.is_set():
                raise LocalMusicScanCancelled(
                    (
                        "Local music scan "
                        "cancelled."
                    )
                )

            index = (
                self._index_factory()
            )

            scan = getattr(
                index,
                "scan",
                None,
            )

            if not callable(
                scan
            ):
                raise LocalMusicQtRuntimeError(
                    "index_unavailable",
                    (
                        "The Local Music index "
                        "is unavailable."
                    ),
                )

            result = scan(
                self._folders,
                cancel_requested=(
                    self._cancel_event.is_set
                ),
            )

            if not isinstance(
                result,
                LocalMusicScanResult,
            ):
                raise LocalMusicQtRuntimeError(
                    "invalid_result",
                    (
                        "The Local Music index "
                        "returned an invalid result."
                    ),
                )

        except LocalMusicScanCancelled:
            self.cancelled.emit()

        except LocalMusicQtRuntimeError as error:
            self.failed.emit(
                error.error_code,
                error.message,
            )

        except LocalMusicIndexError:
            self.failed.emit(
                "scan_failed",
                (
                    "Local Music could not "
                    "scan the selected folders."
                ),
            )

        except Exception:
            self.failed.emit(
                "scan_failed",
                (
                    "Local Music could not "
                    "scan the selected folders."
                ),
            )

        else:
            self.result_ready.emit(
                result
            )

        finally:
            self.finished.emit()


class LocalMusicQtScanRuntime(
    QObject
):
    scan_started = pyqtSignal(
        object
    )

    result_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
    )

    scan_cancelled = pyqtSignal()

    scan_finished = pyqtSignal(
        object
    )

    busy_changed = pyqtSignal(
        bool
    )

    def __init__(
        self,
        *,
        index_factory: Callable = (
            LocalMusicIndex
        ),
        shutdown_wait_ms: int = (
            DEFAULT_LOCAL_MUSIC_SHUTDOWN_WAIT_MS
        ),
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        if not callable(
            index_factory
        ):
            raise TypeError(
                (
                    "index_factory must "
                    "be callable"
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
        ):
            raise TypeError(
                (
                    "shutdown_wait_ms must "
                    "be an integer"
                )
            )

        if shutdown_wait_ms < 1:
            raise ValueError(
                (
                    "shutdown_wait_ms must "
                    "be at least 1"
                )
            )

        self._index_factory = (
            index_factory
        )

        self._shutdown_wait_ms = (
            shutdown_wait_ms
        )

        self._thread = None
        self._worker = None

        self._active_folders = None

        self._latest_result = None

        self._shutting_down = False

    @property
    def busy(
        self,
    ) -> bool:
        return (
            self._thread is not None
        )

    @property
    def active_folders(
        self,
    ) -> tuple[
        str,
        ...,
    ] | None:
        return self._active_folders

    @property
    def latest_result(
        self,
    ) -> LocalMusicScanResult | None:
        return self._latest_result

    def start_scan(
        self,
        folders,
    ) -> None:
        if self._shutting_down:
            raise LocalMusicQtRuntimeError(
                "closed",
                (
                    "The Local Music scanner "
                    "is shutting down."
                ),
            )

        checked_folders = (
            _checked_folders(
                folders
            )
        )

        if self.busy:
            raise LocalMusicQtRuntimeError(
                "busy",
                (
                    "A Local Music scan is "
                    "already running."
                ),
            )

        thread = QThread(
            self
        )

        worker = LocalMusicScanWorker(
            folders=checked_folders,
            index_factory=(
                self._index_factory
            ),
        )

        worker.moveToThread(
            thread
        )

        thread.started.connect(
            worker.run
        )

        worker.result_ready.connect(
            self._handle_result
        )

        worker.failed.connect(
            self._handle_failure
        )

        worker.cancelled.connect(
            self._handle_cancelled
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

        self._active_folders = (
            checked_folders
        )

        self.busy_changed.emit(
            True
        )

        self.scan_started.emit(
            checked_folders
        )

        try:
            thread.start()

        except Exception as error:
            self._thread = None
            self._worker = None
            self._active_folders = None

            self.busy_changed.emit(
                False
            )

            raise LocalMusicQtRuntimeError(
                "thread_start_failed",
                (
                    "Local Music could not "
                    "start scanning."
                ),
            ) from error

    def cancel_scan(
        self,
    ) -> bool:
        worker = self._worker

        if worker is None:
            return False

        request_cancel = getattr(
            worker,
            "request_cancel",
            None,
        )

        if not callable(
            request_cancel
        ):
            return False

        try:
            request_cancel()

        except Exception:
            return False

        return True

    @pyqtSlot(
        object
    )
    def _handle_result(
        self,
        result,
    ) -> None:
        if self._shutting_down:
            return

        if not isinstance(
            result,
            LocalMusicScanResult,
        ):
            self.failed.emit(
                "invalid_result",
                (
                    "Local Music returned "
                    "an invalid scan result."
                ),
            )

            return

        self._latest_result = (
            result
        )

        self.result_ready.emit(
            result
        )

    @pyqtSlot(
        str,
        str,
    )
    def _handle_failure(
        self,
        error_code: str,
        message: str,
    ) -> None:
        if self._shutting_down:
            return

        safe_code = str(
            error_code
            or "scan_failed"
        ).strip()

        safe_message = str(
            message
            or (
                "Local Music could not "
                "scan the selected folders."
            )
        ).strip()

        self.failed.emit(
            safe_code,
            safe_message,
        )

    @pyqtSlot()
    def _handle_cancelled(
        self,
    ) -> None:
        if self._shutting_down:
            return

        self.scan_cancelled.emit()

    def _complete_thread(
        self,
        thread,
    ) -> None:
        if (
            thread is None
            or thread
            is not self._thread
        ):
            return

        finished_folders = (
            self._active_folders
            or ()
        )

        self._thread = None
        self._worker = None
        self._active_folders = None

        self.busy_changed.emit(
            False
        )

        self.scan_finished.emit(
            finished_folders
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

        worker = self._worker
        thread = self._thread

        if worker is not None:
            request_cancel = getattr(
                worker,
                "request_cancel",
                None,
            )

            if callable(
                request_cancel
            ):
                try:
                    request_cancel()
                except Exception:
                    pass

        if thread is None:
            self._worker = None
            self._active_folders = None
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
