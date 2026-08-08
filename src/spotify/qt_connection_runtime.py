from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
from numbers import Real
import threading

from PyQt6.QtCore import (
    QObject,
    QThread,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QDesktopServices,
)

from src.spotify.connection_controller import (
    SpotifyConnectionController,
)
from src.spotify.connection_controller import (
    SpotifyConnectionError,
)
from src.spotify.connection_controller import (
    SpotifyConnectionResult,
)


DEFAULT_BROWSER_BRIDGE_TIMEOUT_SECONDS = 15.0

_ALLOWED_AUTHORIZATION_HOST = (
    "accounts.spotify.com"
)

_ALLOWED_AUTHORIZATION_PATH = (
    "/authorize"
)

_OPERATION_RESTORE = "restore"
_OPERATION_CONNECT = "connect"
_OPERATION_DISCONNECT = "disconnect"

_ALLOWED_OPERATIONS = frozenset(
    {
        _OPERATION_RESTORE,
        _OPERATION_CONNECT,
        _OPERATION_DISCONNECT,
    }
)


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyQtConnectionState:
    status: object
    message: str = ""

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.message,
            str,
        ):
            raise TypeError(
                "message must be a string"
            )

    @property
    def connected(
        self,
    ) -> bool:
        return bool(
            getattr(
                self.status,
                "value",
                "",
            )
            in {
                "connected",
                "refreshed",
            }
        )

    @property
    def refreshed(
        self,
    ) -> bool:
        return (
            getattr(
                self.status,
                "value",
                "",
            )
            == "refreshed"
        )

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            getattr(
                self.status,
                "value",
                "",
            )
            == "reauthorization_required"
        )

    @property
    def cancelled(
        self,
    ) -> bool:
        return (
            getattr(
                self.status,
                "value",
                "",
            )
            == "cancelled"
        )


class SpotifyQtConnectionRuntimeError(
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

        self.error_code = error_code
        self.message = message


def _validate_timeout(
    value: float,
) -> float:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            Real,
        )
    ):
        raise TypeError(
            "browser bridge timeout must be a number"
        )

    checked = float(
        value
    )

    if (
        not math.isfinite(
            checked
        )
        or checked <= 0
    ):
        raise ValueError(
            "browser bridge timeout must be a finite positive number"
        )

    return checked


def _authorization_qurl(
    url: str,
) -> QUrl | None:
    if not isinstance(
        url,
        str,
    ):
        return None

    checked = url.strip()

    if not checked:
        return None

    parsed = QUrl(
        checked
    )

    if not parsed.isValid():
        return None

    if (
        parsed.scheme().lower()
        != "https"
    ):
        return None

    if (
        parsed.host().lower()
        != _ALLOWED_AUTHORIZATION_HOST
    ):
        return None

    if (
        parsed.path()
        != _ALLOWED_AUTHORIZATION_PATH
    ):
        return None

    if (
        parsed.userName()
        or parsed.password()
    ):
        return None

    return parsed


def open_spotify_authorization_url(
    url: str,
    *,
    open_url: Callable[
        [QUrl],
        bool,
    ] = QDesktopServices.openUrl,
) -> bool:
    if not callable(
        open_url
    ):
        raise TypeError(
            "open_url must be callable"
        )

    parsed = _authorization_qurl(
        url
    )

    if parsed is None:
        return False

    try:
        return bool(
            open_url(
                parsed
            )
        )
    except Exception:
        return False


class _BrowserLaunchRequest:
    def __init__(
        self,
    ) -> None:
        self._event = (
            threading.Event()
        )
        self._lock = (
            threading.Lock()
        )
        self._completed = False
        self._result = False

    def complete(
        self,
        result: bool,
    ) -> None:
        with self._lock:
            if self._completed:
                return

            self._result = bool(
                result
            )
            self._completed = True
            self._event.set()

    def wait(
        self,
        timeout_seconds: float,
    ) -> bool:
        if not self._event.wait(
            timeout_seconds
        ):
            return False

        with self._lock:
            return bool(
                self._result
            )


class SpotifyConnectionWorker(
    QObject
):
    browser_requested = pyqtSignal(
        str,
        object,
    )

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
        *,
        operation: str,
        client_id: str,
        controller_factory: Callable = (
            SpotifyConnectionController
        ),
        browser_bridge_timeout_seconds: float = (
            DEFAULT_BROWSER_BRIDGE_TIMEOUT_SECONDS
        ),
    ) -> None:
        super().__init__()

        if (
            not isinstance(
                operation,
                str,
            )
            or operation
            not in _ALLOWED_OPERATIONS
        ):
            raise ValueError(
                "Unsupported Spotify connection operation."
            )

        if not isinstance(
            client_id,
            str,
        ):
            raise TypeError(
                "Spotify client ID must be a string"
            )

        checked_client_id = (
            client_id.strip()
        )

        if not checked_client_id:
            raise ValueError(
                "Spotify client ID cannot be empty"
            )

        if not callable(
            controller_factory
        ):
            raise TypeError(
                "controller_factory must be callable"
            )

        self._operation = operation
        self._client_id = checked_client_id
        self._controller_factory = (
            controller_factory
        )
        self._browser_bridge_timeout_seconds = (
            _validate_timeout(
                browser_bridge_timeout_seconds
            )
        )
        self._cancel_event = (
            threading.Event()
        )

    @property
    def operation(
        self,
    ) -> str:
        return self._operation

    def _request_browser_open(
        self,
        url: str,
    ) -> bool:
        request = (
            _BrowserLaunchRequest()
        )

        self.browser_requested.emit(
            url,
            request,
        )

        return request.wait(
            self._browser_bridge_timeout_seconds
        )

    def _build_controller(
        self,
    ):
        return self._controller_factory(
            self._client_id,
            browser_opener=(
                self._request_browser_open
            ),
        )

    @pyqtSlot()
    def request_cancel(
        self,
    ) -> None:
        self._cancel_event.set()


    def run(
        self,
    ) -> None:
        try:
            controller = (
                self._build_controller()
            )
            set_cancel_requested = getattr(
                controller,
                "set_cancel_requested",
                None,
            )

            if callable(
                set_cancel_requested
            ):
                set_cancel_requested(
                    self._cancel_event.is_set
                )

            operation_method = getattr(
                controller,
                self._operation,
                None,
            )

            if not callable(
                operation_method
            ):
                raise SpotifyQtConnectionRuntimeError(
                    "operation_unavailable",
                    (
                        "The requested Spotify operation "
                        "is unavailable."
                    ),
                )

            result = (
                operation_method()
            )

            if not isinstance(
                result,
                SpotifyConnectionResult,
            ):
                raise SpotifyQtConnectionRuntimeError(
                    "invalid_result",
                    (
                        "Spotify returned an invalid "
                        "connection result."
                    ),
                )

        except SpotifyConnectionError as error:
            self.failed.emit(
                error.error_code,
                error.message,
            )

        except SpotifyQtConnectionRuntimeError as error:
            self.failed.emit(
                error.error_code,
                error.message,
            )

        except Exception:
            self.failed.emit(
                "operation_failed",
                (
                    "The Spotify connection operation "
                    "could not be completed."
                ),
            )

        else:
            safe_result = SpotifyQtConnectionState(
                status=result.status,
                message=result.message,
            )

            self.result_ready.emit(
                safe_result
            )

        finally:
            self.finished.emit()


class SpotifyQtConnectionRuntime(
    QObject
):
    operation_started = pyqtSignal(
        str
    )

    result_ready = pyqtSignal(
        str,
        object,
    )

    failed = pyqtSignal(
        str,
        str,
        str,
    )

    operation_finished = pyqtSignal(
        str
    )

    busy_changed = pyqtSignal(
        bool
    )

    def __init__(
        self,
        client_id: str,
        *,
        controller_factory: Callable = (
            SpotifyConnectionController
        ),
        browser_launcher: Callable[
            [str],
            bool,
        ] = open_spotify_authorization_url,
        browser_bridge_timeout_seconds: float = (
            DEFAULT_BROWSER_BRIDGE_TIMEOUT_SECONDS
        ),
        parent=None,
    ) -> None:
        super().__init__(
            parent
        )

        if not isinstance(
            client_id,
            str,
        ):
            raise TypeError(
                "Spotify client ID must be a string"
            )

        checked_client_id = (
            client_id.strip()
        )

        if not checked_client_id:
            raise ValueError(
                "Spotify client ID cannot be empty"
            )

        if not callable(
            controller_factory
        ):
            raise TypeError(
                "controller_factory must be callable"
            )

        if not callable(
            browser_launcher
        ):
            raise TypeError(
                "browser_launcher must be callable"
            )

        self._client_id = (
            checked_client_id
        )
        self._controller_factory = (
            controller_factory
        )
        self._browser_launcher = (
            browser_launcher
        )
        self._browser_bridge_timeout_seconds = (
            _validate_timeout(
                browser_bridge_timeout_seconds
            )
        )

        self._thread = None
        self._worker = None
        self._operation = None
        self._shutting_down = False

    @property
    def busy(
        self,
    ) -> bool:
        return (
            self._thread is not None
        )

    @property
    def active_operation(
        self,
    ) -> str | None:
        return self._operation

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
            self._operation = None
            return True

        try:
            running = bool(
                thread.isRunning()
            )
        except Exception:
            running = False

        if not running:
            self._worker = None
            self._thread = None
            self._operation = None
            return True

        try:
            thread.quit()
        except Exception:
            pass

        try:
            finished = bool(
                thread.wait(
                    20000
                )
            )
        except Exception:
            finished = False

        if finished:
            self._worker = None
            self._thread = None
            self._operation = None

        return finished


    def restore(
        self,
    ) -> None:
        self._start_operation(
            _OPERATION_RESTORE
        )

    def connect_spotify(
        self,
    ) -> None:
        self._start_operation(
            _OPERATION_CONNECT
        )

    def disconnect(
        self,
    ) -> None:
        self._start_operation(
            _OPERATION_DISCONNECT
        )

    def _start_operation(
        self,
        operation: str,
    ) -> None:
        if self._shutting_down:
            raise SpotifyQtConnectionRuntimeError(
                "closed",
                (
                    "The Spotify connection runtime "
                    "is shutting down."
                ),
            )

        if self.busy:
            raise SpotifyQtConnectionRuntimeError(
                "busy",
                (
                    "A Spotify connection operation "
                    "is already running."
                ),
            )

        thread = QThread(
            self
        )

        worker = SpotifyConnectionWorker(
            operation=operation,
            client_id=(
                self._client_id
            ),
            controller_factory=(
                self._controller_factory
            ),
            browser_bridge_timeout_seconds=(
                self._browser_bridge_timeout_seconds
            ),
        )

        worker.moveToThread(
            thread
        )

        thread.started.connect(
            worker.run
        )

        worker.browser_requested.connect(
            self._handle_browser_request
        )

        worker.result_ready.connect(
            self._handle_result
        )

        worker.failed.connect(
            self._handle_failure
        )

        worker.finished.connect(
            thread.quit
        )

        worker.finished.connect(
            worker.deleteLater
        )

        thread.finished.connect(
            self._thread_finished
        )

        thread.finished.connect(
            thread.deleteLater
        )

        self._thread = thread
        self._worker = worker
        self._operation = operation

        self.busy_changed.emit(
            True
        )

        self.operation_started.emit(
            operation
        )

        thread.start()

    @pyqtSlot(
        str,
        object,
    )
    def _handle_browser_request(
        self,
        url: str,
        request,
    ) -> None:
        if self._shutting_down:
            complete = getattr(
                request,
                "complete",
                None,
            )

            if callable(
                complete
            ):
                complete(
                    False
                )

            return

        result = False

        try:
            result = bool(
                self._browser_launcher(
                    url
                )
            )
        except Exception:
            result = False

        complete = getattr(
            request,
            "complete",
            None,
        )

        if callable(
            complete
        ):
            complete(
                result
            )

    @pyqtSlot(
        object,
    )
    def _handle_result(
        self,
        result,
    ) -> None:
        if self._shutting_down:
            return

        operation = (
            self._operation
            or ""
        )

        self.result_ready.emit(
            operation,
            result,
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

        operation = (
            self._operation
            or ""
        )

        self.failed.emit(
            operation,
            error_code,
            message,
        )

    @pyqtSlot()
    def _thread_finished(
        self,
    ) -> None:
        operation = (
            self._operation
            or ""
        )

        self._worker = None
        self._thread = None
        self._operation = None

        self.busy_changed.emit(
            False
        )

        self.operation_finished.emit(
            operation
        )
