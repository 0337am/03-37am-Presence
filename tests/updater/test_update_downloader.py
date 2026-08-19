from __future__ import annotations

from io import BytesIO
import hashlib
from pathlib import Path
import socket
import tempfile
import unittest
import urllib.error

from src.system.update_checker import (
    ReleaseAsset,
    ReleaseInfo,
)
from src.system.update_downloader import (
    MAX_CHECKSUM_BYTES,
    UpdateDownloadError,
    UpdateDownloader,
    UpdateDownloadStatus,
    calculate_sha256,
    download_update,
    parse_sha256sums,
)
from tests.repo_paths import REPO_ROOT


RELEASE_BASE = (
    "https://github.com/0337am/"
    "03-37am-Presence-Releases/"
    "releases/download/v2.7.0/"
)

INSTALLER_NAME = (
    "03-37am-Presence-"
    "Setup-v2.7.0.exe"
)

CHECKSUM_NAME = "SHA256SUMS.txt"


class FakeResponse:
    def __init__(
        self,
        content: bytes,
        *,
        final_url: str,
        content_length: (
            int | str | None
        ) = None,
    ):
        self._content = content
        self._position = 0
        self._final_url = final_url

        if content_length is None:
            content_length = len(content)

        self.headers = {
            "Content-Length": str(
                content_length
            )
        }

    def __enter__(self):
        return self

    def __exit__(
        self,
        exception_type,
        exception,
        traceback,
    ):
        return False

    def read(
        self,
        size: int = -1,
    ) -> bytes:
        if self._position >= len(
            self._content
        ):
            return b""

        if size < 0:
            end = len(self._content)
        else:
            end = min(
                self._position + size,
                len(self._content),
            )

        result = self._content[
            self._position:end
        ]

        self._position = end

        return result

    def geturl(self) -> str:
        return self._final_url


class MappingUrlOpen:
    def __init__(
        self,
        responses,
    ):
        self.responses = dict(
            responses
        )
        self.requests = []
        self.timeouts = []

    def __call__(
        self,
        request,
        *,
        timeout,
    ):
        self.requests.append(request)
        self.timeouts.append(timeout)

        value = self.responses[
            request.full_url
        ]

        if isinstance(
            value,
            BaseException,
        ):
            raise value

        return value


def build_release(
    installer_content: bytes = (
        b"verified installer"
    ),
    *,
    expected_digest: str | None = None,
    installer_url: str | None = None,
    checksum_url: str | None = None,
    installer_size: int | None = None,
    checksum_content: bytes | None = None,
):
    if expected_digest is None:
        expected_digest = (
            hashlib.sha256(
                installer_content
            ).hexdigest()
        )

    if checksum_content is None:
        checksum_content = (
            f"{expected_digest}  "
            f"{INSTALLER_NAME}\n"
        ).encode("utf-8")

    if installer_url is None:
        installer_url = (
            RELEASE_BASE
            + INSTALLER_NAME
        )

    if checksum_url is None:
        checksum_url = (
            RELEASE_BASE
            + CHECKSUM_NAME
        )

    if installer_size is None:
        installer_size = len(
            installer_content
        )

    release = ReleaseInfo(
        version="2.7.0",
        tag_name="v2.7.0",
        title=(
            "03:37am Presence v2.7.0"
        ),
        notes="Release notes",
        page_url=(
            "https://github.com/0337am/"
            "03-37am-Presence-Releases/"
            "releases/tag/v2.7.0"
        ),
        published_at=(
            "2026-07-17T12:00:00Z"
        ),
        assets=(
            ReleaseAsset(
                name=INSTALLER_NAME,
                download_url=(
                    installer_url
                ),
                size_bytes=(
                    installer_size
                ),
            ),
            ReleaseAsset(
                name=CHECKSUM_NAME,
                download_url=(
                    checksum_url
                ),
                size_bytes=len(
                    checksum_content
                ),
            ),
        ),
    )

    responses = {
        checksum_url: FakeResponse(
            checksum_content,
            final_url=(
                "https://release-assets."
                "githubusercontent.com/"
                "checksum"
            ),
        ),
        installer_url: FakeResponse(
            installer_content,
            final_url=(
                "https://release-assets."
                "githubusercontent.com/"
                "installer"
            ),
        ),
    }

    return (
        release,
        responses,
        expected_digest,
        checksum_content,
    )


class ChecksumTests(
    unittest.TestCase
):
    def test_valid_checksum_is_parsed(self):
        digest = "a" * 64

        result = parse_sha256sums(
            (
                f"{digest}  "
                f"{INSTALLER_NAME}\n"
            ).encode("utf-8"),
            INSTALLER_NAME,
        )

        self.assertEqual(
            result,
            digest,
        )

    def test_utf8_bom_and_crlf_are_supported(self):
        digest = "b" * 64

        result = parse_sha256sums(
            (
                "\ufeff"
                f"{digest}  "
                f"{INSTALLER_NAME}\r\n"
            ).encode("utf-8"),
            INSTALLER_NAME,
        )

        self.assertEqual(
            result,
            digest,
        )

    def test_malformed_line_is_rejected(self):
        with self.assertRaises(
            UpdateDownloadError
        ) as context:
            parse_sha256sums(
                (
                    b"not-a-valid-"
                    b"checksum-line"
                ),
                INSTALLER_NAME,
            )

        self.assertEqual(
            context.exception.error_code,
            "invalid_checksum",
        )

    def test_duplicate_filename_is_rejected(self):
        digest = "c" * 64

        content = (
            f"{digest}  "
            f"{INSTALLER_NAME}\n"
            f"{digest}  "
            f"{INSTALLER_NAME}\n"
        ).encode("utf-8")

        with self.assertRaises(
            UpdateDownloadError
        ) as context:
            parse_sha256sums(
                content,
                INSTALLER_NAME,
            )

        self.assertEqual(
            context.exception.error_code,
            "duplicate_checksum",
        )

    def test_missing_installer_hash_is_rejected(self):
        with self.assertRaises(
            UpdateDownloadError
        ) as context:
            parse_sha256sums(
                (
                    ("d" * 64)
                    + "  other.exe\n"
                ).encode("utf-8"),
                INSTALLER_NAME,
            )

        self.assertEqual(
            context.exception.error_code,
            "checksum_missing",
        )

    def test_unsafe_checksum_filename_is_rejected(self):
        with self.assertRaises(
            UpdateDownloadError
        ) as context:
            parse_sha256sums(
                (
                    ("e" * 64)
                    + "  ..\\installer.exe\n"
                ).encode("utf-8"),
                INSTALLER_NAME,
            )

        self.assertEqual(
            context.exception.error_code,
            "unsafe_filename",
        )

    def test_oversized_checksum_is_rejected(self):
        content = (
            b"x"
            * (
                MAX_CHECKSUM_BYTES
                + 1
            )
        )

        with self.assertRaises(
            UpdateDownloadError
        ) as context:
            parse_sha256sums(
                content,
                INSTALLER_NAME,
            )

        self.assertEqual(
            context.exception.error_code,
            "checksum_too_large",
        )


class UpdateDownloaderTests(
    unittest.TestCase
):
    def test_successful_download_is_verified(self):
        (
            release,
            responses,
            expected_digest,
            _,
        ) = build_release()

        progress = []

        with tempfile.TemporaryDirectory() as root:
            urlopen = MappingUrlOpen(
                responses
            )

            downloader = UpdateDownloader(
                urlopen=urlopen,
                temporary_root=root,
                progress_callback=(
                    progress.append
                ),
            )

            result = downloader.download(
                release
            )

            self.assertEqual(
                result.status,
                UpdateDownloadStatus.READY,
            )
            self.assertTrue(result.ready)
            self.assertFalse(
                result.is_error
            )
            self.assertTrue(
                result.installer_path
                .is_file()
            )
            self.assertTrue(
                result.checksum_path
                .is_file()
            )
            self.assertEqual(
                result.expected_sha256,
                expected_digest,
            )
            self.assertEqual(
                result.actual_sha256,
                expected_digest,
            )
            self.assertEqual(
                calculate_sha256(
                    result.installer_path
                ),
                expected_digest,
            )
            self.assertEqual(
                len(urlopen.requests),
                2,
            )
            self.assertEqual(
                [
                    item.stage
                    for item in progress
                ][-1],
                "complete",
            )

    def test_requests_use_expected_headers(self):
        release, responses, _, _ = (
            build_release()
        )

        with tempfile.TemporaryDirectory() as root:
            urlopen = MappingUrlOpen(
                responses
            )

            result = UpdateDownloader(
                urlopen=urlopen,
                temporary_root=root,
            ).download(release)

            self.assertTrue(result.ready)

            for request in urlopen.requests:
                headers = {
                    key.lower(): value
                    for key, value
                    in request.header_items()
                }

                self.assertEqual(
                    headers["accept"],
                    (
                        "application/"
                        "octet-stream"
                    ),
                )
                self.assertTrue(
                    headers[
                        "user-agent"
                    ].startswith(
                        "03-37am-Presence/"
                    )
                )
                self.assertEqual(
                    request.method,
                    "GET",
                )

    def test_hash_mismatch_removes_download(self):
        (
            release,
            responses,
            _,
            _,
        ) = build_release(
            expected_digest="f" * 64
        )

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    responses
                ),
                temporary_root=root,
            ).download(release)

            self.assertEqual(
                result.error_code,
                "hash_mismatch",
            )
            self.assertEqual(
                list(Path(root).iterdir()),
                [],
            )

    def test_missing_installer_is_rejected(self):
        release, _, _, _ = (
            build_release()
        )

        release = ReleaseInfo(
            version=release.version,
            tag_name=release.tag_name,
            title=release.title,
            notes=release.notes,
            page_url=release.page_url,
            published_at=(
                release.published_at
            ),
            assets=(
                release.assets[1],
            ),
        )

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    {}
                ),
                temporary_root=root,
            ).download(release)

            self.assertEqual(
                result.error_code,
                "installer_missing",
            )

    def test_missing_checksum_is_rejected(self):
        release, _, _, _ = (
            build_release()
        )

        release = ReleaseInfo(
            version=release.version,
            tag_name=release.tag_name,
            title=release.title,
            notes=release.notes,
            page_url=release.page_url,
            published_at=(
                release.published_at
            ),
            assets=(
                release.assets[0],
            ),
        )

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    {}
                ),
                temporary_root=root,
            ).download(release)

            self.assertEqual(
                result.error_code,
                "checksum_missing",
            )

    def test_untrusted_initial_url_is_rejected(self):
        (
            release,
            responses,
            _,
            _,
        ) = build_release(
            installer_url=(
                "https://example.com/"
                + INSTALLER_NAME
            )
        )

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    responses
                ),
                temporary_root=root,
            ).download(release)

            self.assertEqual(
                result.error_code,
                "untrusted_url",
            )

    def test_untrusted_redirect_is_rejected(self):
        (
            release,
            responses,
            _,
            checksum_content,
        ) = build_release()

        responses[
            RELEASE_BASE + CHECKSUM_NAME
        ] = FakeResponse(
            checksum_content,
            final_url=(
                "https://example.com/"
                "SHA256SUMS.txt"
            ),
        )

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    responses
                ),
                temporary_root=root,
            ).download(release)

            self.assertEqual(
                result.error_code,
                "untrusted_redirect",
            )
            self.assertEqual(
                list(Path(root).iterdir()),
                [],
            )

    def test_partial_download_is_rejected(self):
        (
            release,
            responses,
            _,
            checksum_content,
        ) = build_release()

        checksum_url = (
            RELEASE_BASE + CHECKSUM_NAME
        )

        responses[
            checksum_url
        ] = FakeResponse(
            checksum_content[:-1],
            final_url=(
                "https://release-assets."
                "githubusercontent.com/"
                "checksum"
            ),
            content_length=len(
                checksum_content
            ),
        )

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    responses
                ),
                temporary_root=root,
            ).download(release)

            self.assertEqual(
                result.error_code,
                "partial_download",
            )

    def test_release_size_mismatch_is_rejected(self):
        (
            release,
            responses,
            _,
            _,
        ) = build_release(
            installer_size=999
        )

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    responses
                ),
                temporary_root=root,
            ).download(release)

            self.assertEqual(
                result.error_code,
                "size_mismatch",
            )

    def test_installer_limit_is_enforced(self):
        (
            release,
            responses,
            _,
            _,
        ) = build_release(
            installer_content=b"123456"
        )

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    responses
                ),
                temporary_root=root,
                maximum_installer_bytes=5,
            ).download(release)

            self.assertEqual(
                result.error_code,
                "installer_too_large",
            )

    def test_invalid_content_length_is_rejected(self):
        (
            release,
            responses,
            _,
            checksum_content,
        ) = build_release()

        responses[
            RELEASE_BASE + CHECKSUM_NAME
        ] = FakeResponse(
            checksum_content,
            final_url=(
                "https://release-assets."
                "githubusercontent.com/"
                "checksum"
            ),
            content_length="invalid",
        )

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    responses
                ),
                temporary_root=root,
            ).download(release)

            self.assertEqual(
                result.error_code,
                "invalid_response",
            )

    def test_offline_error_is_friendly(self):
        (
            release,
            responses,
            _,
            _,
        ) = build_release()

        responses[
            RELEASE_BASE + CHECKSUM_NAME
        ] = urllib.error.URLError(
            "offline"
        )

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    responses
                ),
                temporary_root=root,
            ).download(release)

            self.assertEqual(
                result.error_code,
                "offline",
            )

    def test_timeout_error_is_friendly(self):
        for error in (
            TimeoutError(),
            socket.timeout(),
        ):
            with self.subTest(
                error=type(error).__name__
            ):
                (
                    release,
                    responses,
                    _,
                    _,
                ) = build_release()

                responses[
                    RELEASE_BASE
                    + CHECKSUM_NAME
                ] = error

                with tempfile.TemporaryDirectory() as root:
                    result = (
                        UpdateDownloader(
                            urlopen=(
                                MappingUrlOpen(
                                    responses
                                )
                            ),
                            temporary_root=root,
                        ).download(release)
                    )

                    self.assertEqual(
                        result.error_code,
                        "timeout",
                    )

    def test_http_error_is_friendly(self):
        (
            release,
            responses,
            _,
            _,
        ) = build_release()

        http_error = urllib.error.HTTPError(
            (
                RELEASE_BASE
                + CHECKSUM_NAME
            ),
            404,
            "Not Found",
            None,
            BytesIO(b""),
        )

        responses[
            RELEASE_BASE + CHECKSUM_NAME
        ] = http_error

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    responses
                ),
                temporary_root=root,
            ).download(release)

            self.assertEqual(
                result.error_code,
                "http_error",
            )
            self.assertIn(
                "404",
                result.message,
            )
            self.assertTrue(
                http_error.fp is None
                or http_error.fp.closed
            )

    def test_progress_callback_failure_is_ignored(self):
        release, responses, _, _ = (
            build_release()
        )

        def callback(progress):
            raise RuntimeError(
                "UI closed"
            )

        with tempfile.TemporaryDirectory() as root:
            result = UpdateDownloader(
                urlopen=MappingUrlOpen(
                    responses
                ),
                temporary_root=root,
                progress_callback=callback,
            ).download(release)

            self.assertTrue(result.ready)

    def test_convenience_function(self):
        release, responses, _, _ = (
            build_release()
        )

        with tempfile.TemporaryDirectory() as root:
            result = download_update(
                release,
                urlopen=MappingUrlOpen(
                    responses
                ),
                temporary_root=root,
            )

            self.assertTrue(result.ready)

    def test_module_has_no_installer_launch_code(self):
        source_path = (
            REPO_ROOT
            / "src"
            / "system"
            / "update_downloader.py"
        )

        source = source_path.read_text(
            encoding="utf-8-sig"
        ).lower()

        forbidden_values = (
            "subprocess",
            "os.startfile",
            "shellexecute",
            "popen(",
        )

        for forbidden_value in forbidden_values:
            self.assertNotIn(
                forbidden_value,
                source,
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
