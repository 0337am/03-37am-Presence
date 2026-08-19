from __future__ import annotations

import threading
import time
import unittest

from PyQt6.QtCore import (
    QCoreApplication,
)

from src.ui.update_controller import (
    UpdateCheckController,
    describe_update_result,
)


class FakeRelease:
    def __init__(
        self,
        *,
        version="2.7.0",
        name="Updates & Distribution",
    ):
        self.version = version
        self.name = name


class FakeResult:
    def __init__(
        self,
        *,
        update_available=False,
        is_error=False,
        message="",
        status="up_to_date",
        release=None,
    ):
        self.update_available = (
            update_available
        )
        self.is_error = is_error
        self.message = message
        self.status = status
        self.release = release


class UpdateControllerTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QCoreApplication.instance()
            or QCoreApplication([])
        )

    def process_events_until(
        self,
        condition,
        *,
        timeout=2.0,
    ):
        deadline = (
            time.monotonic()
            + timeout
        )

        while (
            not condition()
            and time.monotonic()
            < deadline
        ):
            self.app.processEvents()
            time.sleep(0.005)

        self.app.processEvents()

    def test_method_based_result_is_classified(self):
        class MethodResult:
            status = "error"
            error_code = "no_release"
            message = (
                "No published app release "
                "was found on GitHub."
            )
            release = None

            def update_available(self):
                return False

            def is_error(self):
                return True

        presentation = (
            describe_update_result(
                MethodResult()
            )
        )

        self.assertFalse(
            presentation.update_available
        )

        self.assertFalse(
            presentation.is_error
        )

        self.assertIn(
            "No public release",
            presentation.headline,
        )

        self.assertNotIn(
            "Could not check",
            presentation.headline,
        )

    def test_update_available_presentation(self):
        result = FakeResult(
            update_available=True,
            message=(
                "A newer release is ready."
            ),
            release=FakeRelease(),
        )

        presentation = (
            describe_update_result(
                result,
                current_version="2.6.0",
            )
        )

        self.assertTrue(
            presentation.update_available
        )
        self.assertFalse(
            presentation.is_error
        )
        self.assertEqual(
            presentation.available_version,
            "2.7.0",
        )
        self.assertIn(
            "v2.7.0",
            presentation.headline,
        )
        self.assertIn(
            "Updates & Distribution",
            presentation.detail,
        )

    def test_up_to_date_presentation(self):
        result = FakeResult(
            message=(
                "No newer release was found."
            )
        )

        presentation = (
            describe_update_result(
                result,
                current_version="2.6.0",
            )
        )

        self.assertFalse(
            presentation.update_available
        )
        self.assertIn(
            "v2.6.0",
            presentation.headline,
        )

    def test_error_presentation(self):
        result = FakeResult(
            is_error=True,
            message="Network unavailable.",
            status="error",
        )

        presentation = (
            describe_update_result(
                result
            )
        )

        self.assertTrue(
            presentation.is_error
        )
        self.assertIn(
            "Network unavailable",
            presentation.detail,
        )

    def test_no_release_presentation(self):
        result = FakeResult(
            status="no_release",
            message=(
                "No published release exists."
            ),
        )

        presentation = (
            describe_update_result(
                result
            )
        )

        self.assertIn(
            "No public release",
            presentation.headline,
        )

    def test_newer_local_build_presentation(self):
        result = FakeResult(
            status=(
                "local_version_newer"
            ),
        )

        presentation = (
            describe_update_result(
                result
            )
        )

        self.assertIn(
            "newer than",
            presentation.headline,
        )

    def test_controller_runs_checker(self):
        expected = FakeResult(
            message="Complete."
        )

        controller = (
            UpdateCheckController(
                checker=(
                    lambda version:
                    expected
                ),
                current_version="2.6.0",
            )
        )

        results = []
        finished = []

        controller.result_ready.connect(
            results.append
        )

        controller.finished.connect(
            lambda: finished.append(True)
        )

        self.assertTrue(
            controller.start_check()
        )

        self.assertTrue(
            controller.wait(2.0)
        )

        self.process_events_until(
            lambda: bool(finished)
        )

        self.assertEqual(
            results,
            [expected],
        )
        self.assertFalse(
            controller.is_busy
        )

    def test_duplicate_check_is_blocked(self):
        release_checker = (
            threading.Event()
        )

        def checker(version):
            release_checker.wait(2.0)
            return FakeResult()

        controller = (
            UpdateCheckController(
                checker=checker
            )
        )

        self.assertTrue(
            controller.start_check()
        )

        self.assertFalse(
            controller.start_check()
        )

        release_checker.set()

        self.assertTrue(
            controller.wait(2.0)
        )

    def test_checker_exception_is_friendly(self):
        def checker(version):
            raise RuntimeError(
                "private internal detail"
            )

        controller = (
            UpdateCheckController(
                checker=checker
            )
        )

        messages = []
        finished = []

        controller.status_changed.connect(
            messages.append
        )

        controller.finished.connect(
            lambda: finished.append(True)
        )

        self.assertTrue(
            controller.start_check()
        )

        self.assertTrue(
            controller.wait(2.0)
        )

        self.process_events_until(
            lambda: bool(finished)
        )

        self.assertIn(
            (
                "The update check failed "
                "unexpectedly."
            ),
            messages,
        )

        self.assertNotIn(
            "private internal detail",
            " ".join(messages),
        )

    def test_worker_thread_is_daemon(self):
        release_checker = (
            threading.Event()
        )

        def checker(version):
            release_checker.wait(2.0)
            return FakeResult()

        controller = (
            UpdateCheckController(
                checker=checker
            )
        )

        self.assertTrue(
            controller.start_check()
        )

        with controller._state_lock:
            thread = controller._thread

        self.assertIsNotNone(thread)
        self.assertTrue(thread.daemon)

        release_checker.set()

        self.assertTrue(
            controller.wait(2.0)
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
