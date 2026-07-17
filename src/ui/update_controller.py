from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Callable

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)

from src.system.update_checker import (
    check_for_updates,
)
from src.version import APP_VERSION


DEFAULT_UPDATE_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class UpdatePresentation:
    headline: str
    detail: str
    update_available: bool
    is_error: bool
    available_version: str = ""
    release_name: str = ""


UpdateCheckerCallable = Callable[
    [str],
    object,
]


def _clean_text(
    value,
) -> str:
    return str(
        value or ""
    ).strip()


def _boolean_property(
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


def _release_value(
    release,
    *names: str,
) -> str:
    if release is None:
        return ""

    for name in names:
        value = _clean_text(
            getattr(
                release,
                name,
                "",
            )
        )

        if value:
            return value

    return ""


def describe_update_result(
    result,
    *,
    current_version: str = APP_VERSION,
) -> UpdatePresentation:
    current_version = _clean_text(
        current_version
    ).removeprefix("v")

    message = _clean_text(
        getattr(
            result,
            "message",
            "",
        )
    )

    release = getattr(
        result,
        "release",
        None,
    )

    available_version = _release_value(
        release,
        "version",
        "tag_name",
    )

    if not available_version:
        available_version = _clean_text(
            getattr(
                result,
                "available_version",
                "",
            )
            or getattr(
                result,
                "latest_version",
                "",
            )
        )

    available_version = (
        available_version
        .removeprefix("v")
    )

    release_name = _release_value(
        release,
        "name",
        "release_name",
        "title",
    )

    update_available = (
        _boolean_property(
            result,
            "update_available",
        )
    )

    is_error = _boolean_property(
        result,
        "is_error",
    )

    status = getattr(
        result,
        "status",
        "",
    )

    status_value = _clean_text(
        getattr(
            status,
            "value",
            status,
        )
    ).lower()

    error_code_value = _clean_text(
        getattr(
            result,
            "error_code",
            "",
        )
    ).lower()

    if update_available:
        headline = (
            "Update available"
            + (
                f": v{available_version}"
                if available_version
                else "."
            )
        )

        details = []

        if release_name:
            details.append(
                release_name
            )

        if message:
            details.append(
                message
            )

        detail = (
            " • ".join(details)
            or (
                "A newer verified release "
                "is available."
            )
        )

        return UpdatePresentation(
            headline=headline,
            detail=detail,
            update_available=True,
            is_error=False,
            available_version=(
                available_version
            ),
            release_name=release_name,
        )

    if (
        status_value in {
            "no_release",
            "no_releases",
        }
        or error_code_value in {
            "no_release",
            "no_releases",
        }
    ):
        return UpdatePresentation(
            headline=(
                "No public release is "
                "available yet."
            ),
            detail=(
                message
                or (
                    "The official release feed "
                    "does not contain a published "
                    "release."
                )
            ),
            update_available=False,
            is_error=False,
        )

    if is_error:
        return UpdatePresentation(
            headline=(
                "Could not check for updates."
            ),
            detail=(
                message
                or (
                    "Check your connection and "
                    "try again."
                )
            ),
            update_available=False,
            is_error=True,
        )

    if status_value in {
        "local_newer",
        "local_version_newer",
        "development_build",
    }:
        return UpdatePresentation(
            headline=(
                "This build is newer than "
                "the latest public release."
            ),
            detail=(
                message
                or (
                    "No downgrade will be "
                    "offered."
                )
            ),
            update_available=False,
            is_error=False,
        )

    return UpdatePresentation(
        headline=(
            f"You are up to date on "
            f"v{current_version}."
        ),
        detail=(
            message
            or (
                "No newer verified release "
                "was found."
            )
        ),
        update_available=False,
        is_error=False,
    )


def _default_checker(
    current_version: str,
):
    return check_for_updates(
        current_version,
        timeout_seconds=(
            DEFAULT_UPDATE_TIMEOUT_SECONDS
        ),
    )


class UpdateCheckController(QObject):
    busy_changed = pyqtSignal(bool)
    status_changed = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    finished = pyqtSignal()

    def __init__(
        self,
        parent=None,
        *,
        checker: UpdateCheckerCallable
        | None = None,
        current_version: str = APP_VERSION,
    ):
        super().__init__(parent)

        self.current_version = _clean_text(
            current_version
        )

        self._checker = (
            checker
            or _default_checker
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

    def start_check(self) -> bool:
        with self._state_lock:
            if self._busy:
                return False

            self._busy = True

        self.busy_changed.emit(True)
        self.status_changed.emit(
            "Checking the official "
            "release feed..."
        )

        thread = threading.Thread(
            target=self._run_check,
            name=(
                "0337am-update-check"
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

    def _run_check(self) -> None:
        try:
            result = self._checker(
                self.current_version
            )

        except Exception:
            self.status_changed.emit(
                "The update check failed "
                "unexpectedly."
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
