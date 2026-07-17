from __future__ import annotations

from io import BytesIO
import json
import socket
import unittest
import urllib.error

from src.system.update_checker import (
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_VERSION,
    LATEST_RELEASE_API_URL,
    ReleaseInfo,
    SemanticVersion,
    UpdateChecker,
    UpdateStatus,
    check_for_updates,
)


def asset_payload(
    name: str,
    version: str = "2.7.0",
    *,
    download_url: str | None = None,
):
    if download_url is None:
        download_url = (
            "https://github.com/0337am/"
            "03-37am-Presence-Releases/releases/"
            f"download/v{version}/{name}"
        )

    return {
        "name": name,
        "browser_download_url": (
            download_url
        ),
        "size": 1024,
        "content_type": (
            "application/octet-stream"
        ),
        "state": "uploaded",
    }


def release_payload(
    version: str = "2.7.0",
    *,
    include_installer: bool = True,
    include_checksum: bool = True,
    include_standalone: bool = True,
):
    assets = []

    if include_installer:
        assets.append(
            asset_payload(
                (
                    "03-37am-Presence-"
                    f"Setup-v{version}.exe"
                ),
                version,
            )
        )

    if include_standalone:
        assets.append(
            asset_payload(
                (
                    "03-37am-Presence-"
                    f"v{version}.exe"
                ),
                version,
            )
        )

    if include_checksum:
        assets.append(
            asset_payload(
                "SHA256SUMS.txt",
                version,
            )
        )

    return {
        "tag_name": f"v{version}",
        "name": (
            f"03:37am Presence v{version}"
        ),
        "body": "Release notes",
        "html_url": (
            "https://github.com/0337am/"
            "03-37am-Presence-Releases/releases/"
            f"tag/v{version}"
        ),
        "published_at": (
            "2026-07-17T12:00:00Z"
        ),
        "draft": False,
        "prerelease": False,
        "assets": assets,
    }


class FakeResponse:
    def __init__(self, payload):
        if isinstance(payload, bytes):
            self.payload = payload
        else:
            self.payload = json.dumps(
                payload
            ).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(
        self,
        exception_type,
        exception,
        traceback,
    ):
        return False

    def read(self):
        return self.payload


class RecordingUrlOpen:
    def __init__(self, response):
        self.response = response
        self.request = None
        self.timeout = None
        self.calls = 0

    def __call__(
        self,
        request,
        *,
        timeout,
    ):
        self.calls += 1
        self.request = request
        self.timeout = timeout
        return self.response


class RaisingUrlOpen:
    def __init__(self, error):
        self.error = error

    def __call__(
        self,
        request,
        *,
        timeout,
    ):
        raise self.error


class SemanticVersionTests(
    unittest.TestCase
):
    def test_version_parser_accepts_tag_prefix(self):
        self.assertEqual(
            SemanticVersion.parse(
                "v2.7.0"
            ),
            SemanticVersion(
                2,
                7,
                0,
            ),
        )

    def test_version_comparison_is_numeric(self):
        self.assertGreater(
            SemanticVersion.parse(
                "2.10.0"
            ),
            SemanticVersion.parse(
                "2.9.9"
            ),
        )

    def test_invalid_version_is_rejected(self):
        for value in (
            "2.7",
            "2.7.0-beta",
            "version 2.7.0",
            "02.7.0",
        ):
            with self.subTest(value=value):
                with self.assertRaises(
                    ValueError
                ):
                    SemanticVersion.parse(
                        value
                    )


class UpdateCheckerTests(
    unittest.TestCase
):
    def build_checker(
        self,
        payload,
        *,
        timeout=10,
    ):
        urlopen = RecordingUrlOpen(
            FakeResponse(payload)
        )

        checker = UpdateChecker(
            urlopen=urlopen,
            timeout_seconds=timeout,
        )

        return checker, urlopen

    def test_update_available_with_required_assets(self):
        checker, _ = self.build_checker(
            release_payload("2.7.0")
        )

        result = checker.check("2.6.0")

        self.assertEqual(
            result.status,
            UpdateStatus.UPDATE_AVAILABLE,
        )
        self.assertTrue(
            result.update_available
        )
        self.assertTrue(
            result.can_download_update
        )
        self.assertEqual(
            result.latest_version,
            "2.7.0",
        )
        self.assertIsInstance(
            result.release,
            ReleaseInfo,
        )
        self.assertEqual(
            result.release.notes,
            "Release notes",
        )
        self.assertEqual(
            result.release
            .installer_asset.name,
            (
                "03-37am-Presence-"
                "Setup-v2.7.0.exe"
            ),
        )
        self.assertEqual(
            result.release
            .checksum_asset.name,
            "SHA256SUMS.txt",
        )
        self.assertEqual(
            result.release
            .standalone_asset.name,
            (
                "03-37am-Presence-"
                "v2.7.0.exe"
            ),
        )

    def test_up_to_date_result(self):
        checker, _ = self.build_checker(
            release_payload("2.6.0")
        )

        result = checker.check("2.6.0")

        self.assertEqual(
            result.status,
            UpdateStatus.UP_TO_DATE,
        )
        self.assertFalse(
            result.update_available
        )
        self.assertFalse(
            result.is_error
        )

    def test_local_build_can_be_newer(self):
        checker, _ = self.build_checker(
            release_payload("2.6.0")
        )

        result = checker.check("2.7.0")

        self.assertEqual(
            result.status,
            (
                UpdateStatus
                .LOCAL_VERSION_NEWER
            ),
        )

    def test_missing_checksum_blocks_download(self):
        checker, _ = self.build_checker(
            release_payload(
                "2.7.0",
                include_checksum=False,
            )
        )

        result = checker.check("2.6.0")

        self.assertEqual(
            result.status,
            UpdateStatus.UPDATE_AVAILABLE,
        )
        self.assertFalse(
            result.can_download_update
        )
        self.assertEqual(
            result.release
            .missing_required_assets,
            ("SHA256SUMS.txt",),
        )
        self.assertIn(
            "incomplete",
            result.message,
        )

    def test_standalone_asset_is_optional(self):
        checker, _ = self.build_checker(
            release_payload(
                "2.7.0",
                include_standalone=False,
            )
        )

        result = checker.check("2.6.0")

        self.assertTrue(
            result.can_download_update
        )
        self.assertIsNone(
            result.release
            .standalone_asset
        )

    def test_request_uses_expected_api_contract(self):
        checker, urlopen = self.build_checker(
            release_payload("2.7.0"),
            timeout=12,
        )

        checker.check("2.6.0")

        headers = {
            key.lower(): value
            for key, value
            in urlopen.request.header_items()
        }

        self.assertEqual(
            urlopen.request.full_url,
            LATEST_RELEASE_API_URL,
        )
        self.assertEqual(
            urlopen.request.method,
            "GET",
        )
        self.assertEqual(
            urlopen.timeout,
            12,
        )
        self.assertEqual(
            headers["accept"],
            GITHUB_ACCEPT_HEADER,
        )
        self.assertEqual(
            headers[
                "x-github-api-version"
            ],
            GITHUB_API_VERSION,
        )
        self.assertEqual(
            headers["user-agent"],
            "03-37am-Presence/2.6.0",
        )

    def test_invalid_local_version_skips_network(self):
        urlopen = RecordingUrlOpen(
            FakeResponse(
                release_payload("2.7.0")
            )
        )

        checker = UpdateChecker(
            urlopen=urlopen
        )

        result = checker.check(
            "development"
        )

        self.assertEqual(
            result.status,
            UpdateStatus.ERROR,
        )
        self.assertEqual(
            result.error_code,
            "invalid_local_version",
        )
        self.assertEqual(
            urlopen.calls,
            0,
        )

    def test_malformed_json_is_friendly_error(self):
        checker, _ = self.build_checker(
            b"{not-json"
        )

        result = checker.check("2.6.0")

        self.assertEqual(
            result.status,
            UpdateStatus.ERROR,
        )
        self.assertEqual(
            result.error_code,
            "invalid_response",
        )

    def test_404_reports_no_release(self):
        error = urllib.error.HTTPError(
            LATEST_RELEASE_API_URL,
            404,
            "Not Found",
            None,
            BytesIO(b"{}"),
        )

        checker = UpdateChecker(
            urlopen=RaisingUrlOpen(error)
        )

        result = checker.check("2.6.0")

        self.assertEqual(
            result.error_code,
            "no_release",
        )

    def test_rate_limit_is_friendly_error(self):
        for status_code in (403, 429):
            with self.subTest(
                status_code=status_code
            ):
                error = (
                    urllib.error.HTTPError(
                        LATEST_RELEASE_API_URL,
                        status_code,
                        "Rate Limited",
                        None,
                        BytesIO(b"{}"),
                    )
                )

                checker = UpdateChecker(
                    urlopen=RaisingUrlOpen(
                        error
                    )
                )

                result = checker.check(
                    "2.6.0"
                )

                self.assertEqual(
                    result.error_code,
                    "rate_limited",
                )

    def test_api_version_error_is_friendly(self):
        error = urllib.error.HTTPError(
            LATEST_RELEASE_API_URL,
            410,
            "Gone",
            None,
            BytesIO(b"{}"),
        )

        checker = UpdateChecker(
            urlopen=RaisingUrlOpen(error)
        )

        result = checker.check("2.6.0")

        self.assertEqual(
            result.error_code,
            "api_version_unsupported",
        )

    def test_offline_error_is_friendly(self):
        checker = UpdateChecker(
            urlopen=RaisingUrlOpen(
                urllib.error.URLError(
                    "offline"
                )
            )
        )

        result = checker.check("2.6.0")

        self.assertEqual(
            result.error_code,
            "offline",
        )

    def test_timeout_is_friendly(self):
        for error in (
            TimeoutError(),
            socket.timeout(),
        ):
            with self.subTest(
                error=type(error).__name__
            ):
                checker = UpdateChecker(
                    urlopen=RaisingUrlOpen(
                        error
                    )
                )

                result = checker.check(
                    "2.6.0"
                )

                self.assertEqual(
                    result.error_code,
                    "timeout",
                )

    def test_draft_and_prerelease_are_rejected(self):
        for key in (
            "draft",
            "prerelease",
        ):
            with self.subTest(key=key):
                payload = release_payload(
                    "2.7.0"
                )
                payload[key] = True

                checker, _ = (
                    self.build_checker(
                        payload
                    )
                )

                result = checker.check(
                    "2.6.0"
                )

                self.assertEqual(
                    result.error_code,
                    "invalid_release",
                )

    def test_untrusted_asset_url_is_ignored(self):
        payload = release_payload(
            "2.7.0"
        )

        for asset in payload["assets"]:
            if (
                asset["name"]
                == "SHA256SUMS.txt"
            ):
                asset[
                    "browser_download_url"
                ] = (
                    "https://example.com/"
                    "SHA256SUMS.txt"
                )

        checker, _ = self.build_checker(
            payload
        )

        result = checker.check("2.6.0")

        self.assertFalse(
            result.can_download_update
        )
        self.assertEqual(
            result.release
            .missing_required_assets,
            ("SHA256SUMS.txt",),
        )

    def test_untrusted_release_page_is_rejected(self):
        payload = release_payload(
            "2.7.0"
        )

        payload["html_url"] = (
            "https://example.com/"
            "releases/tag/v2.7.0"
        )

        checker, _ = self.build_checker(
            payload
        )

        result = checker.check("2.6.0")

        self.assertEqual(
            result.error_code,
            "invalid_release",
        )

    def test_convenience_function_uses_injected_urlopen(self):
        urlopen = RecordingUrlOpen(
            FakeResponse(
                release_payload("2.7.0")
            )
        )

        result = check_for_updates(
            "2.6.0",
            urlopen=urlopen,
        )

        self.assertEqual(
            result.status,
            UpdateStatus.UPDATE_AVAILABLE,
        )
        self.assertEqual(
            urlopen.calls,
            1,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
