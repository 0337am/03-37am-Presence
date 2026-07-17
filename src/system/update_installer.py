from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hmac
import os
from pathlib import Path
import re
from typing import Callable

from src.system.update_checker import (
    SemanticVersion,
)
from src.system.update_downloader import (
    UpdateDownloadResult,
    calculate_sha256,
)


INSTALLER_FILENAME_TEMPLATE = (
    "03-37am-Presence-"
    "Setup-v{version}.exe"
)

_SHA256_PATTERN = re.compile(
    r"^[0-9a-f]{64}$"
)


class UpdateInstallStatus(
    str,
    Enum,
):
    LAUNCHED = "launched"
    ERROR = "error"


@dataclass(frozen=True)
class PreparedUpdateInstall:
    version: str
    installer_path: Path
    download_directory: Path
    sha256: str


@dataclass(frozen=True)
class UpdateInstallResult:
    status: UpdateInstallStatus
    version: str
    message: str
    error_code: str = ""
    installer_path: Path | None = None
    quit_requested: bool = False

    @property
    def launched(self) -> bool:
        return (
            self.status
            is UpdateInstallStatus.LAUNCHED
        )

    @property
    def is_error(self) -> bool:
        return (
            self.status
            is UpdateInstallStatus.ERROR
        )


class UpdateInstallError(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
    ):
        super().__init__(message)

        self.error_code = error_code
        self.message = message


InstallerOpener = Callable[
    [str],
    object,
]

QuitCallback = Callable[
    [],
    object,
]


def expected_installer_filename(
    version: str,
) -> str:
    parsed_version = SemanticVersion.parse(
        version
    )

    return INSTALLER_FILENAME_TEMPLATE.format(
        version=str(parsed_version)
    )


def _normalise_digest(
    value: str,
    *,
    error_code: str,
    message: str,
) -> str:
    digest = str(
        value or ""
    ).strip().lower()

    if _SHA256_PATTERN.fullmatch(
        digest
    ) is None:
        raise UpdateInstallError(
            error_code,
            message,
        )

    return digest


def _resolve_directory(
    path: Path,
) -> Path:
    try:
        resolved = path.resolve(
            strict=True
        )
    except (
        OSError,
        RuntimeError,
    ) as error:
        raise UpdateInstallError(
            "download_missing",
            (
                "The verified update folder "
                "no longer exists."
            ),
        ) from error

    if not resolved.is_dir():
        raise UpdateInstallError(
            "invalid_download_directory",
            (
                "The verified update folder "
                "is not a directory."
            ),
        )

    return resolved


def _resolve_installer(
    path: Path,
) -> Path:
    try:
        resolved = path.resolve(
            strict=True
        )
    except (
        OSError,
        RuntimeError,
    ) as error:
        raise UpdateInstallError(
            "installer_missing",
            (
                "The verified installer "
                "no longer exists."
            ),
        ) from error

    if not resolved.is_file():
        raise UpdateInstallError(
            "installer_missing",
            (
                "The verified installer "
                "is not a file."
            ),
        )

    try:
        size_bytes = resolved.stat().st_size
    except OSError as error:
        raise UpdateInstallError(
            "installer_unreadable",
            (
                "The verified installer "
                "could not be inspected."
            ),
        ) from error

    if size_bytes <= 0:
        raise UpdateInstallError(
            "empty_installer",
            (
                "The verified installer "
                "is empty."
            ),
        )

    return resolved


def _validate_location(
    installer_path: Path,
    download_directory: Path,
) -> None:
    if installer_path.parent != download_directory:
        raise UpdateInstallError(
            "unsafe_installer_location",
            (
                "The verified installer moved "
                "outside its update folder."
            ),
        )


def _validate_filename(
    installer_path: Path,
    version: str,
) -> None:
    expected_name = (
        expected_installer_filename(
            version
        )
    )

    if installer_path.name != expected_name:
        raise UpdateInstallError(
            "unexpected_filename",
            (
                "The update installer has an "
                "unexpected filename."
            ),
        )

    if (
        installer_path.suffix.lower()
        != ".exe"
    ):
        raise UpdateInstallError(
            "invalid_installer_type",
            (
                "The update installer is not "
                "a Windows executable."
            ),
        )


def _verify_installer_hash(
    installer_path: Path,
    expected_sha256: str,
) -> str:
    try:
        actual_sha256 = calculate_sha256(
            installer_path
        )
    except OSError as error:
        raise UpdateInstallError(
            "installer_unreadable",
            (
                "The verified installer "
                "could not be read."
            ),
        ) from error

    if not hmac.compare_digest(
        expected_sha256,
        actual_sha256,
    ):
        raise UpdateInstallError(
            "hash_mismatch",
            (
                "The installer changed after "
                "it was downloaded."
            ),
        )

    return actual_sha256


def prepare_update_install(
    download_result: UpdateDownloadResult,
) -> PreparedUpdateInstall:
    if not isinstance(
        download_result,
        UpdateDownloadResult,
    ):
        raise UpdateInstallError(
            "invalid_download_result",
            (
                "The update download result "
                "is invalid."
            ),
        )

    if not download_result.ready:
        raise UpdateInstallError(
            "download_not_ready",
            (
                "The update has not been "
                "downloaded and verified."
            ),
        )

    try:
        version = str(
            SemanticVersion.parse(
                download_result.version
            )
        )
    except ValueError as error:
        raise UpdateInstallError(
            "invalid_version",
            (
                "The update version is "
                "invalid."
            ),
        ) from error

    if (
        download_result.download_directory
        is None
    ):
        raise UpdateInstallError(
            "download_missing",
            (
                "The verified update folder "
                "is missing."
            ),
        )

    if (
        download_result.installer_path
        is None
    ):
        raise UpdateInstallError(
            "installer_missing",
            (
                "The verified installer "
                "is missing."
            ),
        )

    download_directory = (
        _resolve_directory(
            Path(
                download_result
                .download_directory
            )
        )
    )

    installer_path = (
        _resolve_installer(
            Path(
                download_result
                .installer_path
            )
        )
    )

    _validate_location(
        installer_path,
        download_directory,
    )

    _validate_filename(
        installer_path,
        version,
    )

    expected_sha256 = (
        _normalise_digest(
            download_result
            .expected_sha256,
            error_code=(
                "invalid_expected_hash"
            ),
            message=(
                "The expected installer "
                "hash is invalid."
            ),
        )
    )

    claimed_actual_sha256 = (
        _normalise_digest(
            download_result
            .actual_sha256,
            error_code=(
                "invalid_actual_hash"
            ),
            message=(
                "The recorded installer "
                "hash is invalid."
            ),
        )
    )

    if not hmac.compare_digest(
        expected_sha256,
        claimed_actual_sha256,
    ):
        raise UpdateInstallError(
            "recorded_hash_mismatch",
            (
                "The recorded installer "
                "hashes do not match."
            ),
        )

    actual_sha256 = (
        _verify_installer_hash(
            installer_path,
            expected_sha256,
        )
    )

    return PreparedUpdateInstall(
        version=version,
        installer_path=installer_path,
        download_directory=(
            download_directory
        ),
        sha256=actual_sha256,
    )


def _revalidate_prepared_install(
    prepared: PreparedUpdateInstall,
) -> Path:
    if not isinstance(
        prepared,
        PreparedUpdateInstall,
    ):
        raise UpdateInstallError(
            "invalid_prepared_update",
            (
                "The prepared update "
                "information is invalid."
            ),
        )

    try:
        version = str(
            SemanticVersion.parse(
                prepared.version
            )
        )
    except ValueError as error:
        raise UpdateInstallError(
            "invalid_version",
            (
                "The prepared update version "
                "is invalid."
            ),
        ) from error

    expected_sha256 = (
        _normalise_digest(
            prepared.sha256,
            error_code=(
                "invalid_expected_hash"
            ),
            message=(
                "The prepared installer "
                "hash is invalid."
            ),
        )
    )

    resolved_directory = (
        _resolve_directory(
            prepared.download_directory
        )
    )

    resolved_installer = (
        _resolve_installer(
            prepared.installer_path
        )
    )

    if (
        resolved_directory
        != prepared.download_directory
        or resolved_installer
        != prepared.installer_path
    ):
        raise UpdateInstallError(
            "installer_path_changed",
            (
                "The prepared installer path "
                "changed before launch."
            ),
        )

    _validate_location(
        resolved_installer,
        resolved_directory,
    )

    _validate_filename(
        resolved_installer,
        version,
    )

    _verify_installer_hash(
        resolved_installer,
        expected_sha256,
    )

    return resolved_installer


def _error_result(
    *,
    version: str,
    error_code: str,
    message: str,
    installer_path: Path | None = None,
) -> UpdateInstallResult:
    return UpdateInstallResult(
        status=UpdateInstallStatus.ERROR,
        version=version,
        message=message,
        error_code=error_code,
        installer_path=installer_path,
        quit_requested=False,
    )


def launch_prepared_update(
    prepared: PreparedUpdateInstall,
    *,
    user_approved: bool,
    opener: InstallerOpener | None = None,
    quit_callback: QuitCallback | None = None,
) -> UpdateInstallResult:
    version = str(
        getattr(
            prepared,
            "version",
            "",
        )
        or ""
    )

    installer_path = getattr(
        prepared,
        "installer_path",
        None,
    )

    if user_approved is not True:
        return _error_result(
            version=version,
            error_code=(
                "approval_required"
            ),
            message=(
                "The installer was not "
                "launched because approval "
                "was not provided."
            ),
            installer_path=(
                installer_path
                if isinstance(
                    installer_path,
                    Path,
                )
                else None
            ),
        )

    try:
        validated_installer = (
            _revalidate_prepared_install(
                prepared
            )
        )
    except UpdateInstallError as error:
        return _error_result(
            version=version,
            error_code=(
                error.error_code
            ),
            message=error.message,
            installer_path=(
                installer_path
                if isinstance(
                    installer_path,
                    Path,
                )
                else None
            ),
        )

    selected_opener = opener

    if selected_opener is None:
        selected_opener = getattr(
            os,
            "startfile",
            None,
        )

    if selected_opener is None:
        return _error_result(
            version=version,
            error_code=(
                "unsupported_platform"
            ),
            message=(
                "Update installers can only "
                "be launched on Windows."
            ),
            installer_path=(
                validated_installer
            ),
        )

    try:
        selected_opener(
            os.fspath(
                validated_installer
            )
        )
    except OSError:
        return _error_result(
            version=version,
            error_code="launch_failed",
            message=(
                "Windows could not launch "
                "the verified installer."
            ),
            installer_path=(
                validated_installer
            ),
        )
    except Exception:
        return _error_result(
            version=version,
            error_code="launch_failed",
            message=(
                "The verified installer "
                "could not be launched."
            ),
            installer_path=(
                validated_installer
            ),
        )

    quit_requested = False

    if quit_callback is not None:
        try:
            quit_callback()
            quit_requested = True
        except Exception:
            return UpdateInstallResult(
                status=(
                    UpdateInstallStatus
                    .LAUNCHED
                ),
                version=version,
                message=(
                    "The installer started, "
                    "but the app could not "
                    "close automatically."
                ),
                error_code="quit_failed",
                installer_path=(
                    validated_installer
                ),
                quit_requested=False,
            )

    return UpdateInstallResult(
        status=(
            UpdateInstallStatus.LAUNCHED
        ),
        version=version,
        message=(
            "The verified installer "
            "was launched."
        ),
        installer_path=(
            validated_installer
        ),
        quit_requested=(
            quit_requested
        ),
    )


def launch_downloaded_update(
    download_result: UpdateDownloadResult,
    *,
    user_approved: bool,
    opener: InstallerOpener | None = None,
    quit_callback: QuitCallback | None = None,
) -> UpdateInstallResult:
    try:
        prepared = prepare_update_install(
            download_result
        )
    except UpdateInstallError as error:
        version = str(
            getattr(
                download_result,
                "version",
                "",
            )
            or ""
        )

        return _error_result(
            version=version,
            error_code=error.error_code,
            message=error.message,
        )

    return launch_prepared_update(
        prepared,
        user_approved=user_approved,
        opener=opener,
        quit_callback=quit_callback,
    )