from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import re
import socket
from typing import Any, Callable
import urllib.error
import urllib.request
from urllib.parse import urlparse

from src.version import APP_VERSION


GITHUB_OWNER = "0337am"
GITHUB_REPOSITORY = "03-37am-Presence-Releases"

GITHUB_API_VERSION = "2026-03-10"
GITHUB_ACCEPT_HEADER = "application/vnd.github+json"

LATEST_RELEASE_API_URL = (
    "https://api.github.com/repos/"
    f"{GITHUB_OWNER}/{GITHUB_REPOSITORY}"
    "/releases/latest"
)

RELEASE_PAGE_PREFIX = (
    f"/{GITHUB_OWNER}/"
    f"{GITHUB_REPOSITORY}/releases/"
)

RELEASE_DOWNLOAD_PREFIX = (
    f"/{GITHUB_OWNER}/"
    f"{GITHUB_REPOSITORY}/releases/download/"
)

REQUEST_TIMEOUT_SECONDS = 10

_VERSION_PATTERN = re.compile(
    r"^v?"
    r"(?P<major>0|[1-9][0-9]*)\."
    r"(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)$"
)


class UpdateStatus(str, Enum):
    UPDATE_AVAILABLE = "update_available"
    UP_TO_DATE = "up_to_date"
    LOCAL_VERSION_NEWER = "local_version_newer"
    ERROR = "error"


@dataclass(
    frozen=True,
    order=True,
)
class SemanticVersion:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(
        cls,
        value: str,
    ) -> "SemanticVersion":
        if not isinstance(value, str):
            raise ValueError(
                "Version must be text."
            )

        match = _VERSION_PATTERN.fullmatch(
            value.strip()
        )

        if match is None:
            raise ValueError(
                "Version must use major.minor.patch."
            )

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
        )

    def __str__(self) -> str:
        return (
            f"{self.major}."
            f"{self.minor}."
            f"{self.patch}"
        )


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str
    size_bytes: int
    content_type: str = ""


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag_name: str
    title: str
    notes: str
    page_url: str
    published_at: str
    assets: tuple[ReleaseAsset, ...]

    @property
    def installer_filename(self) -> str:
        return (
            "03-37am-Presence-Setup-v"
            f"{self.version}.exe"
        )

    @property
    def standalone_filename(self) -> str:
        return (
            "03-37am-Presence-v"
            f"{self.version}.exe"
        )

    @property
    def checksum_filename(self) -> str:
        return "SHA256SUMS.txt"

    def find_asset(
        self,
        name: str,
    ) -> ReleaseAsset | None:
        for asset in self.assets:
            if asset.name == name:
                return asset

        return None

    @property
    def installer_asset(
        self,
    ) -> ReleaseAsset | None:
        return self.find_asset(
            self.installer_filename
        )

    @property
    def standalone_asset(
        self,
    ) -> ReleaseAsset | None:
        return self.find_asset(
            self.standalone_filename
        )

    @property
    def checksum_asset(
        self,
    ) -> ReleaseAsset | None:
        return self.find_asset(
            self.checksum_filename
        )

    @property
    def missing_required_assets(
        self,
    ) -> tuple[str, ...]:
        missing: list[str] = []

        if self.installer_asset is None:
            missing.append(
                self.installer_filename
            )

        if self.checksum_asset is None:
            missing.append(
                self.checksum_filename
            )

        return tuple(missing)

    @property
    def required_assets_available(
        self,
    ) -> bool:
        return not self.missing_required_assets


@dataclass(frozen=True)
class UpdateCheckResult:
    status: UpdateStatus
    current_version: str
    latest_version: str = ""
    release: ReleaseInfo | None = None
    message: str = ""
    error_code: str = ""

    @property
    def update_available(self) -> bool:
        return (
            self.status
            is UpdateStatus.UPDATE_AVAILABLE
        )

    @property
    def is_error(self) -> bool:
        return (
            self.status
            is UpdateStatus.ERROR
        )

    @property
    def can_download_update(self) -> bool:
        return bool(
            self.update_available
            and self.release is not None
            and self.release
            .required_assets_available
        )


UrlOpenCallable = Callable[..., Any]


class UpdateChecker:
    def __init__(
        self,
        *,
        urlopen: UrlOpenCallable | None = None,
        timeout_seconds: int = (
            REQUEST_TIMEOUT_SECONDS
        ),
        api_url: str = (
            LATEST_RELEASE_API_URL
        ),
    ):
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be positive."
            )

        self._urlopen = (
            urlopen
            or urllib.request.urlopen
        )

        self._timeout_seconds = (
            timeout_seconds
        )

        self._api_url = api_url

    def check(
        self,
        current_version: str = APP_VERSION,
    ) -> UpdateCheckResult:
        try:
            local_version = (
                SemanticVersion.parse(
                    current_version
                )
            )
        except ValueError:
            return self._error_result(
                current_version=str(
                    current_version
                ),
                error_code=(
                    "invalid_local_version"
                ),
                message=(
                    "The installed app version "
                    "could not be understood."
                ),
            )

        request = urllib.request.Request(
            self._api_url,
            headers={
                "Accept": (
                    GITHUB_ACCEPT_HEADER
                ),
                "User-Agent": (
                    "03-37am-Presence/"
                    f"{local_version}"
                ),
                "X-GitHub-Api-Version": (
                    GITHUB_API_VERSION
                ),
            },
            method="GET",
        )

        try:
            with self._urlopen(
                request,
                timeout=(
                    self._timeout_seconds
                ),
            ) as response:
                response_bytes = response.read()

            payload = json.loads(
                response_bytes.decode("utf-8")
            )

            release = self._parse_release(
                payload
            )

            latest_version = (
                SemanticVersion.parse(
                    release.version
                )
            )

        except urllib.error.HTTPError as error:
            return self._http_error_result(
                current_version=(
                    str(local_version)
                ),
                error=error,
            )

        except urllib.error.URLError:
            return self._error_result(
                current_version=(
                    str(local_version)
                ),
                error_code="offline",
                message=(
                    "The update server could not "
                    "be reached. Check your "
                    "internet connection."
                ),
            )

        except (
            TimeoutError,
            socket.timeout,
        ):
            return self._error_result(
                current_version=(
                    str(local_version)
                ),
                error_code="timeout",
                message=(
                    "The update check timed out. "
                    "Please try again."
                ),
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return self._error_result(
                current_version=(
                    str(local_version)
                ),
                error_code="invalid_response",
                message=(
                    "GitHub returned an unreadable "
                    "update response."
                ),
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            return self._error_result(
                current_version=(
                    str(local_version)
                ),
                error_code="invalid_release",
                message=(
                    "The latest GitHub release "
                    "does not contain valid update "
                    "information."
                ),
            )

        except OSError:
            return self._error_result(
                current_version=(
                    str(local_version)
                ),
                error_code="network_error",
                message=(
                    "A network error interrupted "
                    "the update check."
                ),
            )

        normalised_local = str(
            local_version
        )

        normalised_latest = str(
            latest_version
        )

        if latest_version > local_version:
            message = (
                f"Version {normalised_latest} "
                "is available."
            )

            if (
                not release
                .required_assets_available
            ):
                message = (
                    f"Version {normalised_latest} "
                    "is published, but its update "
                    "files are incomplete."
                )

            return UpdateCheckResult(
                status=(
                    UpdateStatus
                    .UPDATE_AVAILABLE
                ),
                current_version=(
                    normalised_local
                ),
                latest_version=(
                    normalised_latest
                ),
                release=release,
                message=message,
            )

        if latest_version == local_version:
            return UpdateCheckResult(
                status=(
                    UpdateStatus.UP_TO_DATE
                ),
                current_version=(
                    normalised_local
                ),
                latest_version=(
                    normalised_latest
                ),
                release=release,
                message=(
                    "You are using the latest "
                    "version."
                ),
            )

        return UpdateCheckResult(
            status=(
                UpdateStatus
                .LOCAL_VERSION_NEWER
            ),
            current_version=(
                normalised_local
            ),
            latest_version=(
                normalised_latest
            ),
            release=release,
            message=(
                "This app build is newer than "
                "the latest published release."
            ),
        )

    def _parse_release(
        self,
        payload: Any,
    ) -> ReleaseInfo:
        if not isinstance(payload, dict):
            raise TypeError(
                "Release payload must be an object."
            )

        if payload.get("draft") is True:
            raise ValueError(
                "Draft releases are not valid."
            )

        if payload.get("prerelease") is True:
            raise ValueError(
                "Prereleases are not valid."
            )

        tag_name = self._required_text(
            payload,
            "tag_name",
        )

        version = str(
            SemanticVersion.parse(
                tag_name
            )
        )

        page_url = self._required_text(
            payload,
            "html_url",
        )

        if not self._is_release_page_url(
            page_url
        ):
            raise ValueError(
                "Release page URL is not trusted."
            )

        title = payload.get("name")

        if not isinstance(title, str):
            title = ""

        title = title.strip() or tag_name

        notes = payload.get("body")

        if not isinstance(notes, str):
            notes = ""

        published_at = payload.get(
            "published_at"
        )

        if not isinstance(
            published_at,
            str,
        ):
            published_at = ""

        raw_assets = payload.get(
            "assets",
            [],
        )

        if not isinstance(raw_assets, list):
            raise TypeError(
                "Release assets must be a list."
            )

        assets: list[ReleaseAsset] = []

        for raw_asset in raw_assets:
            asset = self._parse_asset(
                raw_asset
            )

            if asset is not None:
                assets.append(asset)

        return ReleaseInfo(
            version=version,
            tag_name=tag_name,
            title=title,
            notes=notes,
            page_url=page_url,
            published_at=(
                published_at.strip()
            ),
            assets=tuple(assets),
        )

    def _parse_asset(
        self,
        payload: Any,
    ) -> ReleaseAsset | None:
        if not isinstance(payload, dict):
            return None

        if payload.get("state") not in (
            None,
            "uploaded",
        ):
            return None

        name = payload.get("name")
        download_url = payload.get(
            "browser_download_url"
        )

        if not isinstance(name, str):
            return None

        if not isinstance(
            download_url,
            str,
        ):
            return None

        name = name.strip()
        download_url = (
            download_url.strip()
        )

        if not name:
            return None

        if not self._is_release_asset_url(
            download_url
        ):
            return None

        size_bytes = payload.get(
            "size",
            0,
        )

        if (
            isinstance(size_bytes, bool)
            or not isinstance(
                size_bytes,
                int,
            )
            or size_bytes < 0
        ):
            size_bytes = 0

        content_type = payload.get(
            "content_type",
            "",
        )

        if not isinstance(
            content_type,
            str,
        ):
            content_type = ""

        return ReleaseAsset(
            name=name,
            download_url=download_url,
            size_bytes=size_bytes,
            content_type=(
                content_type.strip()
            ),
        )

    def _http_error_result(
        self,
        *,
        current_version: str,
        error: urllib.error.HTTPError,
    ) -> UpdateCheckResult:
        if error.code == 404:
            return self._error_result(
                current_version=(
                    current_version
                ),
                error_code="no_release",
                message=(
                    "No published app release "
                    "was found on GitHub."
                ),
            )

        if error.code in (403, 429):
            return self._error_result(
                current_version=(
                    current_version
                ),
                error_code="rate_limited",
                message=(
                    "GitHub temporarily limited "
                    "update checks. Please try "
                    "again later."
                ),
            )

        if error.code == 410:
            return self._error_result(
                current_version=(
                    current_version
                ),
                error_code=(
                    "api_version_unsupported"
                ),
                message=(
                    "The app's GitHub API version "
                    "needs to be updated."
                ),
            )

        return self._error_result(
            current_version=current_version,
            error_code="http_error",
            message=(
                "GitHub could not complete the "
                f"update check (HTTP {error.code})."
            ),
        )

    @staticmethod
    def _error_result(
        *,
        current_version: str,
        error_code: str,
        message: str,
    ) -> UpdateCheckResult:
        return UpdateCheckResult(
            status=UpdateStatus.ERROR,
            current_version=(
                current_version
            ),
            message=message,
            error_code=error_code,
        )

    @staticmethod
    def _required_text(
        payload: dict[str, Any],
        key: str,
    ) -> str:
        value = payload.get(key)

        if not isinstance(value, str):
            raise TypeError(
                f"{key} must be text."
            )

        value = value.strip()

        if not value:
            raise ValueError(
                f"{key} must not be empty."
            )

        return value

    @staticmethod
    def _is_release_page_url(
        value: str,
    ) -> bool:
        parsed = urlparse(value)

        return (
            parsed.scheme == "https"
            and parsed.netloc.lower()
            == "github.com"
            and parsed.path.startswith(
                RELEASE_PAGE_PREFIX
            )
        )

    @staticmethod
    def _is_release_asset_url(
        value: str,
    ) -> bool:
        parsed = urlparse(value)

        return (
            parsed.scheme == "https"
            and parsed.netloc.lower()
            == "github.com"
            and parsed.path.startswith(
                RELEASE_DOWNLOAD_PREFIX
            )
        )


def check_for_updates(
    current_version: str = APP_VERSION,
    *,
    urlopen: UrlOpenCallable | None = None,
    timeout_seconds: int = (
        REQUEST_TIMEOUT_SECONDS
    ),
) -> UpdateCheckResult:
    checker = UpdateChecker(
        urlopen=urlopen,
        timeout_seconds=timeout_seconds,
    )

    return checker.check(
        current_version=current_version
    )
