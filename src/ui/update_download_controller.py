from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Callable

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)

from src.system.update_downloader import (
    download_update,
)


DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class DownloadPresentation:
    headline: str
    detail: str
    ready: bool
    is_error: bool
    installer_name: str = ""


@dataclass(frozen=True)
class DownloadProgressPresentation:
    text: str
    value: int
    maximum: int
    indeterminate: bool


DownloadCallable = Callable[
    ...,
    object,
]


def _clean_text(
    value,
) -> str:
    return str(
        value or ""
    ).strip()


def _result_boolean(
    value,
    name: str,
) -> bool:
    selected = getattr(
        value,
        name,
        False,
    )

    if callable(selected):
        try:
            selected = selected()
        except TypeError:
            return False

    return bool(selected)


def _integer_value(
    value,
    name: str,
) -> int:
    try:
        return max(
            0,
            int(
                getattr(
                    value,
                    name,
                    0,
                )
                or 0
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0


def format_download_bytes(
    byte_count: int,
) -> str:
    value = float(
        max(
            0,
            int(byte_count),
        )
    )

    units = (
        "B",
        "KB",
        "MB",
        "GB",
    )

    for unit in units:
        if (
            value < 1024
            or unit == units[-1]
        ):
            if unit == "B":
                return (
                    f"{int(value)} {unit}"
                )

            return (
                f"{value:.1f} {unit}"
            )

        value /= 1024

    return "0 B"


def describe_download_progress(
    progress,
) -> DownloadProgressPresentation:
    downloaded = _integer_value(
        progress,
        "bytes_downloaded",
    )

    total = _integer_value(
        progress,
        "total_bytes",
    )

    message = _clean_text(
        getattr(
            progress,
            "message",
            "",
        )
    )

    stage = _clean_text(
        getattr(
            progress,
            "stage",
            "",
        )
    )

    if total > 0:
        percentage = min(
            100,
            int(
                round(
                    downloaded
                    * 100
                    / total
                )
            ),
        )

        size_text = (
            f"{format_download_bytes(downloaded)} "
            f"of {format_download_bytes(total)} "
            f"({percentage}%)"
        )

        text = (
            f"{message} {size_text}".strip()
            if message
            else (
                f"Downloading update... "
                f"{size_text}"
            )
        )

        return DownloadProgressPresentation(
            text=text,
            value=percentage,
            maximum=100,
            indeterminate=False,
        )

    downloaded_text = (
        format_download_bytes(
            downloaded
        )
    )

    fallback = (
        "Downloading update..."
        if stage != "checksum"
        else (
            "Downloading and checking "
            "SHA256SUMS.txt..."
        )
    )

    text = (
        message
        or (
            f"{fallback} "
            f"{downloaded_text}"
        )
    )

    return DownloadProgressPresentation(
        text=text,
        value=0,
        maximum=0,
        indeterminate=True,
    )


def describe_download_result(
    result,
) -> DownloadPresentation:
    ready = _result_boolean(
        result,
        "ready",
    )

    is_error = _result_boolean(
        result,
        "is_error",
    )

    message = _clean_text(
        getattr(
            result,
            "message",
            "",
        )
    )

    installer_path = getattr(
        result,
        "installer_path",
        None,
    )

    installer_name = ""

    if installer_path is not None:
        try:
            installer_name = Path(
                installer_path
            ).name
        except (
            TypeError,
            ValueError,
        ):
            installer_name = ""

    if ready:
        detail = (
            message
            or (
                "The installer passed its "
                "published SHA-256 check."
            )
        )

        if installer_name:
            detail = (
                f"{detail} "
                f"Saved as {installer_name}."
            )

        return DownloadPresentation(
            headline=(
                "Update downloaded and verified."
            ),
            detail=detail,
            ready=True,
            is_error=False,
            installer_name=installer_name,
        )

    if is_error:
        return DownloadPresentation(
            headline=(
                "The update could not be downloaded."
            ),
            detail=(
                message
                or (
                    "No installer was kept. "
                    "Try again later."
                )
            ),
            ready=False,
            is_error=True,
            installer_name=installer_name,
        )

    return DownloadPresentation(
        headline=(
            "The update download did not finish."
        ),
        detail=(
            message
            or (
                "No verified installer "
                "is ready."
            )
        ),
        ready=False,
        is_error=False,
        installer_name=installer_name,
    )


def _default_downloader(
    release,
    *,
    progress_callback,
):
    return download_update(
        release,
        timeout_seconds=(
            DEFAULT_DOWNLOAD_TIMEOUT_SECONDS
        ),
        progress_callback=(
            progress_callback
        ),
    )


class UpdateDownloadController(QObject):
    busy_changed = pyqtSignal(bool)
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(object)
    result_ready = pyqtSignal(object)
    finished = pyqtSignal()

    def __init__(
        self,
        parent=None,
        *,
        downloader: DownloadCallable
        | None = None,
    ):
        super().__init__(parent)

        self._downloader = (
            downloader
            or _default_downloader
        )

        self._state_lock = (
            threading.Lock()
        )

        self._busy = False
        self._thread = None

    @property
    def is_busy(self) -> bool:
        with self._state_lock:
            return self._busy

    def start_download(
        self,
        release,
    ) -> bool:
        if release is None:
            self.status_changed.emit(
                "No verified release is "
                "available to download."
            )
            return False

        with self._state_lock:
            if self._busy:
                return False

            self._busy = True

        self.busy_changed.emit(True)
        self.status_changed.emit(
            "Preparing the verified "
            "update download..."
        )

        thread = threading.Thread(
            target=self._run_download,
            args=(release,),
            name=(
                "0337am-update-download"
            ),
            daemon=True,
        )

        with self._state_lock:
            self._thread = thread

        thread.start()
        return True

    def wait(
        self,
        timeout: float | None = None,
    ) -> bool:
        with self._state_lock:
            thread = self._thread

        if thread is None:
            return True

        thread.join(timeout)

        return not thread.is_alive()

    def _emit_progress(
        self,
        progress,
    ) -> None:
        self.progress_changed.emit(
            progress
        )

    def _run_download(
        self,
        release,
    ) -> None:
        try:
            result = self._downloader(
                release,
                progress_callback=(
                    self._emit_progress
                ),
            )

        except Exception:
            self.status_changed.emit(
                "The update download failed "
                "unexpectedly. No installer "
                "was kept."
            )

        else:
            self.result_ready.emit(
                result
            )

        finally:
            with self._state_lock:
                self._busy = False
                self._thread = None

            self.busy_changed.emit(False)
            self.finished.emit()
