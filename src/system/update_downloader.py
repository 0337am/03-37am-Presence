from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import hmac
import os
from pathlib import Path
import re
import shutil
import socket
import tempfile
from typing import Any, Callable
import urllib.error
import urllib.request
from urllib.parse import urlparse

from src.system.update_checker import (
    RELEASE_DOWNLOAD_PREFIX,
    ReleaseAsset,
    ReleaseInfo,
)
from src.version import APP_VERSION


REQUEST_TIMEOUT_SECONDS = 30
DOWNLOAD_CHUNK_BYTES = 1024 * 1024

MAX_CHECKSUM_BYTES = 128 * 1024
MAX_INSTALLER_BYTES = 512 * 1024 * 1024

USER_AGENT = (
    f"03-37am-Presence/{APP_VERSION}"
)

_CHECKSUM_LINE_PATTERN = re.compile(
    r"^(?P<digest>[0-9a-fA-F]{64})"
    r"  "
    r"(?P<filename>[^\r\n]+)$"
)


class UpdateDownloadStatus(
    str,
    Enum,
):
    READY = "ready"
    ERROR = "error"


@dataclass(frozen=True)
class DownloadProgress:
    stage: str
    bytes_downloaded: int
    total_bytes: int
    message: str


@dataclass(frozen=True)
class UpdateDownloadResult:
    status: UpdateDownloadStatus
    version: str
    message: str
    error_code: str = ""
    download_directory: Path | None = None
    installer_path: Path | None = None
    checksum_path: Path | None = None
    expected_sha256: str = ""
    actual_sha256: str = ""
    bytes_downloaded: int = 0

    @property
    def ready(self) -> bool:
        return (
            self.status
            is UpdateDownloadStatus.READY
        )

    @property
    def is_error(self) -> bool:
        return (
            self.status
            is UpdateDownloadStatus.ERROR
        )


class UpdateDownloadError(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
    ):
        super().__init__(message)

        self.error_code = error_code
        self.message = message


ProgressCallback = Callable[
    [DownloadProgress],
    None,
]

UrlOpenCallable = Callable[..., Any]


def _safe_filename(
    filename: str,
) -> bool:
    if not isinstance(filename, str):
        return False

    filename = filename.strip()

    if not filename:
        return False

    if filename in (".", ".."):
        return False

    if "/" in filename or "\\" in filename:
        return False

    return Path(filename).name == filename


def _trusted_release_url(
    value: str,
) -> bool:
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        return False

    return (
        parsed.scheme == "https"
        and parsed.netloc.lower()
        == "github.com"
        and parsed.username is None
        and parsed.password is None
        and port in (None, 443)
        and parsed.path.startswith(
            RELEASE_DOWNLOAD_PREFIX
        )
    )


def _trusted_final_url(
    value: str,
) -> bool:
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        return False

    host = (
        parsed.hostname or ""
    ).lower()

    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        return False

    if host == "github.com":
        return parsed.path.startswith(
            RELEASE_DOWNLOAD_PREFIX
        )

    return host.endswith(
        ".githubusercontent.com"
    )


def parse_sha256sums(
    content: bytes,
    target_filename: str,
) -> str:
    if not isinstance(content, bytes):
        raise UpdateDownloadError(
            "invalid_checksum",
            (
                "The checksum file did not "
                "contain valid bytes."
            ),
        )

    if len(content) > MAX_CHECKSUM_BYTES:
        raise UpdateDownloadError(
            "checksum_too_large",
            (
                "The checksum file is larger "
                "than expected."
            ),
        )

    if not _safe_filename(target_filename):
        raise UpdateDownloadError(
            "unsafe_filename",
            (
                "The installer filename is "
                "not safe."
            ),
        )

    try:
        text = content.decode(
            "utf-8-sig"
        )
    except UnicodeDecodeError as error:
        raise UpdateDownloadError(
            "invalid_checksum",
            (
                "The checksum file is not "
                "valid UTF-8 text."
            ),
        ) from error

    checksums: dict[str, str] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        match = (
            _CHECKSUM_LINE_PATTERN
            .fullmatch(line)
        )

        if match is None:
            raise UpdateDownloadError(
                "invalid_checksum",
                (
                    "The checksum file contains "
                    "an invalid line."
                ),
            )

        filename = (
            match.group("filename")
            .strip()
        )

        if not _safe_filename(filename):
            raise UpdateDownloadError(
                "unsafe_filename",
                (
                    "The checksum file contains "
                    "an unsafe filename."
                ),
            )

        if filename in checksums:
            raise UpdateDownloadError(
                "duplicate_checksum",
                (
                    "The checksum file contains "
                    "a duplicate filename."
                ),
            )

        checksums[filename] = (
            match.group("digest")
            .lower()
        )

    expected = checksums.get(
        target_filename
    )

    if expected is None:
        raise UpdateDownloadError(
            "checksum_missing",
            (
                "The checksum file does not "
                "contain the installer hash."
            ),
        )

    return expected


def calculate_sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(
                DOWNLOAD_CHUNK_BYTES
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


class UpdateDownloader:
    def __init__(
        self,
        *,
        urlopen: UrlOpenCallable | None = None,
        timeout_seconds: int = (
            REQUEST_TIMEOUT_SECONDS
        ),
        temporary_root: Path | str | None = None,
        progress_callback: (
            ProgressCallback | None
        ) = None,
        maximum_installer_bytes: int = (
            MAX_INSTALLER_BYTES
        ),
    ):
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be positive."
            )

        if maximum_installer_bytes <= 0:
            raise ValueError(
                (
                    "maximum_installer_bytes "
                    "must be positive."
                )
            )

        self._urlopen = (
            urlopen
            or urllib.request.urlopen
        )

        self._timeout_seconds = (
            timeout_seconds
        )

        self._progress_callback = (
            progress_callback
        )

        self._maximum_installer_bytes = (
            maximum_installer_bytes
        )

        if temporary_root is None:
            self._temporary_root = (
                Path(tempfile.gettempdir())
                / "03-37am Presence"
                / "updates"
            )
        else:
            self._temporary_root = Path(
                temporary_root
            )

    def download(
        self,
        release: ReleaseInfo,
    ) -> UpdateDownloadResult:
        version = ""

        if isinstance(release, ReleaseInfo):
            version = release.version

        working_directory: Path | None = None

        try:
            if not isinstance(
                release,
                ReleaseInfo,
            ):
                raise UpdateDownloadError(
                    "invalid_release",
                    (
                        "The update release "
                        "information is invalid."
                    ),
                )

            installer_asset = (
                release.installer_asset
            )

            checksum_asset = (
                release.checksum_asset
            )

            if installer_asset is None:
                raise UpdateDownloadError(
                    "installer_missing",
                    (
                        "The release does not "
                        "include its installer."
                    ),
                )

            if checksum_asset is None:
                raise UpdateDownloadError(
                    "checksum_missing",
                    (
                        "The release does not "
                        "include SHA256SUMS.txt."
                    ),
                )

            self._validate_asset(
                installer_asset,
                expected_name=(
                    release
                    .installer_filename
                ),
            )

            self._validate_asset(
                checksum_asset,
                expected_name=(
                    release
                    .checksum_filename
                ),
            )

            if (
                installer_asset.size_bytes
                > self
                ._maximum_installer_bytes
            ):
                raise UpdateDownloadError(
                    "installer_too_large",
                    (
                        "The installer is larger "
                        "than the allowed limit."
                    ),
                )

            self._temporary_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            working_directory = Path(
                tempfile.mkdtemp(
                    prefix=(
                        "03-37am-Presence-"
                        f"update-v{release.version}-"
                    ),
                    dir=str(
                        self._temporary_root
                    ),
                )
            )

            checksum_path = (
                working_directory
                / checksum_asset.name
            )

            installer_path = (
                working_directory
                / installer_asset.name
            )

            self._download_asset(
                checksum_asset,
                checksum_path,
                maximum_bytes=(
                    MAX_CHECKSUM_BYTES
                ),
                stage="checksum",
            )

            checksum_content = (
                checksum_path.read_bytes()
            )

            expected_sha256 = (
                parse_sha256sums(
                    checksum_content,
                    installer_asset.name,
                )
            )

            installer_bytes = (
                self._download_asset(
                    installer_asset,
                    installer_path,
                    maximum_bytes=(
                        self
                        ._maximum_installer_bytes
                    ),
                    stage="installer",
                )
            )

            actual_sha256 = (
                calculate_sha256(
                    installer_path
                )
            )

            if not hmac.compare_digest(
                expected_sha256,
                actual_sha256,
            ):
                raise UpdateDownloadError(
                    "hash_mismatch",
                    (
                        "The downloaded installer "
                        "failed SHA-256 verification."
                    ),
                )

            self._emit_progress(
                stage="complete",
                bytes_downloaded=(
                    installer_bytes
                ),
                total_bytes=(
                    installer_bytes
                ),
                message=(
                    "The update is downloaded "
                    "and verified."
                ),
            )

            return UpdateDownloadResult(
                status=(
                    UpdateDownloadStatus.READY
                ),
                version=release.version,
                message=(
                    "The update is ready "
                    "to install."
                ),
                download_directory=(
                    working_directory
                ),
                installer_path=(
                    installer_path
                ),
                checksum_path=(
                    checksum_path
                ),
                expected_sha256=(
                    expected_sha256
                ),
                actual_sha256=(
                    actual_sha256
                ),
                bytes_downloaded=(
                    installer_bytes
                ),
            )

        except UpdateDownloadError as error:
            self._cleanup(
                working_directory
            )

            return self._error_result(
                version=version,
                error_code=(
                    error.error_code
                ),
                message=error.message,
            )

        except urllib.error.HTTPError as error:
            status_code = error.code

            try:
                error.close()
            except Exception:
                pass

            self._cleanup(
                working_directory
            )

            return self._error_result(
                version=version,
                error_code="http_error",
                message=(
                    "GitHub could not download "
                    "the update "
                    f"(HTTP {status_code})."
                ),
            )

        except urllib.error.URLError:
            self._cleanup(
                working_directory
            )

            return self._error_result(
                version=version,
                error_code="offline",
                message=(
                    "The update could not be "
                    "downloaded. Check your "
                    "internet connection."
                ),
            )

        except (
            TimeoutError,
            socket.timeout,
        ):
            self._cleanup(
                working_directory
            )

            return self._error_result(
                version=version,
                error_code="timeout",
                message=(
                    "The update download timed "
                    "out. Please try again."
                ),
            )

        except OSError:
            self._cleanup(
                working_directory
            )

            return self._error_result(
                version=version,
                error_code="file_error",
                message=(
                    "The update could not be "
                    "saved to the temporary "
                    "folder."
                ),
            )

    def _download_asset(
        self,
        asset: ReleaseAsset,
        destination: Path,
        *,
        maximum_bytes: int,
        stage: str,
    ) -> int:
        if (
            asset.size_bytes > 0
            and asset.size_bytes
            > maximum_bytes
        ):
            raise UpdateDownloadError(
                f"{stage}_too_large",
                (
                    f"The {stage} file is larger "
                    "than the allowed limit."
                ),
            )

        request = urllib.request.Request(
            asset.download_url,
            headers={
                "Accept": (
                    "application/octet-stream"
                ),
                "User-Agent": USER_AGENT,
            },
            method="GET",
        )

        partial_path = destination.with_name(
            destination.name + ".part"
        )

        with self._urlopen(
            request,
            timeout=(
                self._timeout_seconds
            ),
        ) as response:
            final_url_getter = getattr(
                response,
                "geturl",
                None,
            )

            final_url = (
                final_url_getter()
                if callable(
                    final_url_getter
                )
                else asset.download_url
            )

            if not _trusted_final_url(
                final_url
            ):
                raise UpdateDownloadError(
                    "untrusted_redirect",
                    (
                        "GitHub redirected the "
                        "download to an untrusted "
                        "location."
                    ),
                )

            content_length = (
                self._content_length(
                    response
                )
            )

            if (
                content_length is not None
                and content_length
                > maximum_bytes
            ):
                raise UpdateDownloadError(
                    f"{stage}_too_large",
                    (
                        f"The {stage} file is "
                        "larger than the allowed "
                        "limit."
                    ),
                )

            if (
                content_length is not None
                and asset.size_bytes > 0
                and content_length
                != asset.size_bytes
            ):
                raise UpdateDownloadError(
                    "size_mismatch",
                    (
                        "GitHub reported an "
                        "unexpected file size."
                    ),
                )

            expected_total = (
                content_length
                if content_length
                is not None
                else asset.size_bytes
            )

            downloaded = 0

            self._emit_progress(
                stage=stage,
                bytes_downloaded=0,
                total_bytes=(
                    expected_total
                ),
                message=(
                    f"Downloading {asset.name}"
                ),
            )

            with partial_path.open(
                "xb"
            ) as output:
                while True:
                    chunk = response.read(
                        DOWNLOAD_CHUNK_BYTES
                    )

                    if not chunk:
                        break

                    if not isinstance(
                        chunk,
                        bytes,
                    ):
                        raise (
                            UpdateDownloadError(
                                "invalid_response",
                                (
                                    "The download "
                                    "returned invalid "
                                    "data."
                                ),
                            )
                        )

                    downloaded += len(chunk)

                    if (
                        downloaded
                        > maximum_bytes
                    ):
                        raise (
                            UpdateDownloadError(
                                (
                                    f"{stage}"
                                    "_too_large"
                                ),
                                (
                                    f"The {stage} "
                                    "file exceeded "
                                    "the allowed "
                                    "limit."
                                ),
                            )
                        )

                    output.write(chunk)

                    self._emit_progress(
                        stage=stage,
                        bytes_downloaded=(
                            downloaded
                        ),
                        total_bytes=(
                            expected_total
                        ),
                        message=(
                            f"Downloading "
                            f"{asset.name}"
                        ),
                    )

        if downloaded <= 0:
            raise UpdateDownloadError(
                "empty_download",
                (
                    "GitHub returned an empty "
                    "download."
                ),
            )

        if (
            content_length is not None
            and downloaded
            != content_length
        ):
            raise UpdateDownloadError(
                "partial_download",
                (
                    "The download ended before "
                    "the complete file arrived."
                ),
            )

        if (
            asset.size_bytes > 0
            and downloaded
            != asset.size_bytes
        ):
            raise UpdateDownloadError(
                "size_mismatch",
                (
                    "The downloaded file size "
                    "does not match the release."
                ),
            )

        os.replace(
            partial_path,
            destination,
        )

        return downloaded

    @staticmethod
    def _validate_asset(
        asset: ReleaseAsset,
        *,
        expected_name: str,
    ) -> None:
        if asset.name != expected_name:
            raise UpdateDownloadError(
                "unexpected_filename",
                (
                    "The release contains an "
                    "unexpected update filename."
                ),
            )

        if not _safe_filename(
            asset.name
        ):
            raise UpdateDownloadError(
                "unsafe_filename",
                (
                    "The release contains an "
                    "unsafe update filename."
                ),
            )

        if not _trusted_release_url(
            asset.download_url
        ):
            raise UpdateDownloadError(
                "untrusted_url",
                (
                    "The release contains an "
                    "untrusted update URL."
                ),
            )

    @staticmethod
    def _content_length(
        response: Any,
    ) -> int | None:
        headers = getattr(
            response,
            "headers",
            None,
        )

        if headers is None:
            return None

        getter = getattr(
            headers,
            "get",
            None,
        )

        if not callable(getter):
            return None

        value = getter(
            "Content-Length"
        )

        if value in (None, ""):
            return None

        try:
            result = int(value)
        except (
            TypeError,
            ValueError,
        ) as error:
            raise UpdateDownloadError(
                "invalid_response",
                (
                    "GitHub returned an invalid "
                    "Content-Length header."
                ),
            ) from error

        if result < 0:
            raise UpdateDownloadError(
                "invalid_response",
                (
                    "GitHub returned an invalid "
                    "Content-Length header."
                ),
            )

        return result

    def _emit_progress(
        self,
        *,
        stage: str,
        bytes_downloaded: int,
        total_bytes: int,
        message: str,
    ) -> None:
        callback = (
            self._progress_callback
        )

        if callback is None:
            return

        try:
            callback(
                DownloadProgress(
                    stage=stage,
                    bytes_downloaded=(
                        bytes_downloaded
                    ),
                    total_bytes=max(
                        0,
                        total_bytes,
                    ),
                    message=message,
                )
            )
        except Exception:
            return

    @staticmethod
    def _cleanup(
        directory: Path | None,
    ) -> None:
        if directory is None:
            return

        shutil.rmtree(
            directory,
            ignore_errors=True,
        )

    @staticmethod
    def _error_result(
        *,
        version: str,
        error_code: str,
        message: str,
    ) -> UpdateDownloadResult:
        return UpdateDownloadResult(
            status=(
                UpdateDownloadStatus.ERROR
            ),
            version=version,
            message=message,
            error_code=error_code,
        )


def download_update(
    release: ReleaseInfo,
    *,
    urlopen: UrlOpenCallable | None = None,
    timeout_seconds: int = (
        REQUEST_TIMEOUT_SECONDS
    ),
    temporary_root: (
        Path | str | None
    ) = None,
    progress_callback: (
        ProgressCallback | None
    ) = None,
) -> UpdateDownloadResult:
    downloader = UpdateDownloader(
        urlopen=urlopen,
        timeout_seconds=timeout_seconds,
        temporary_root=temporary_root,
        progress_callback=(
            progress_callback
        ),
    )

    return downloader.download(
        release
    )
