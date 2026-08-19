from __future__ import annotations

from io import BytesIO
import unittest
import urllib.error


from src.system.update_checker import (
    LATEST_RELEASE_API_URL,
)
from src.system.update_checker import (
    UpdateChecker,
)


class RaisingUrlOpen:
    def __init__(
        self,
        error,
    ):
        self.error = error
        self.calls = []

    def __call__(
        self,
        request,
        *,
        timeout,
    ):
        self.calls.append(
            {
                "request": request,
                "timeout": timeout,
            }
        )

        raise self.error


class UpdateCheckerHttpCleanupTests(
    unittest.TestCase
):
    def _assert_http_error_stream_closed(
        self,
        *,
        status_code: int,
        reason: str,
        expected_error_code: str,
    ):
        body = BytesIO(
            b"{}"
        )

        error = urllib.error.HTTPError(
            LATEST_RELEASE_API_URL,
            status_code,
            reason,
            None,
            body,
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
            expected_error_code,
        )

        self.assertTrue(
            body.closed,
            (
                "UpdateChecker left the HTTPError "
                f"response stream open for HTTP {status_code}."
            ),
        )

    def test_404_http_error_stream_is_closed(
        self,
    ):
        self._assert_http_error_stream_closed(
            status_code=404,
            reason="Not Found",
            expected_error_code="no_release",
        )

    def test_403_http_error_stream_is_closed(
        self,
    ):
        self._assert_http_error_stream_closed(
            status_code=403,
            reason="Rate Limited",
            expected_error_code="rate_limited",
        )

    def test_429_http_error_stream_is_closed(
        self,
    ):
        self._assert_http_error_stream_closed(
            status_code=429,
            reason="Rate Limited",
            expected_error_code="rate_limited",
        )

    def test_410_http_error_stream_is_closed(
        self,
    ):
        self._assert_http_error_stream_closed(
            status_code=410,
            reason="Gone",
            expected_error_code=(
                "api_version_unsupported"
            ),
        )


if __name__ == "__main__":
    unittest.main()
