from __future__ import annotations

from pathlib import Path
import threading
import time
import unittest

from PyQt6.QtCore import (
    QCoreApplication,
)

from src.ui.update_download_controller import (
    UpdateDownloadController,
    describe_download_progress,
    describe_download_result,
    format_download_bytes,
)


class FakeProgress:
    def __init__(
        self,
        *,
        stage="installer",
        bytes_downloaded=0,
        total_bytes=0,
        message="",
    ):
        self.stage = stage
        self.bytes_downloaded = (
            bytes_downloaded
        )
        self.total_bytes = total_bytes
        self.message = message


class FakeDownloadResult:
    def __init__(
        self,
        *,
        ready=False,
        is_error=False,
        message="",
        installer_path=None,
    ):
        self.ready = ready
        self.is_error = is_error
        self.message = message
        self.installer_path = (
            installer_path
        )


class MethodDownloadResult:
    message = (
        "Installer verified."
    )
    installer_path = Path(
        "03-37am-Presence-Setup-v2.7.0.exe"
    )

    def ready(self):
        return True

    def is_error(self):
        return False


class UpdateDownloadControllerTests(
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

    def test_byte_formatting(self):
        self.assertEqual(
            format_download_bytes(0),
            "0 B",
        )

        self.assertEqual(
            format_download_bytes(1024),
            "1.0 KB",
        )

        self.assertEqual(
            format_download_bytes(
                1024 * 1024
            ),
            "1.0 MB",
        )

    def test_determinate_progress(self):
        presentation = (
            describe_download_progress(
                FakeProgress(
                    bytes_downloaded=50,
                    total_bytes=100,
                    message=(
                        "Downloading installer..."
                    ),
                )
            )
        )

        self.assertFalse(
            presentation.indeterminate
        )

        self.assertEqual(
            presentation.value,
            50,
        )

        self.assertEqual(
            presentation.maximum,
            100,
        )

        self.assertIn(
            "50%",
            presentation.text,
        )

    def test_indeterminate_progress(self):
        presentation = (
            describe_download_progress(
                FakeProgress(
                    bytes_downloaded=2048,
                )
            )
        )

        self.assertTrue(
            presentation.indeterminate
        )

        self.assertEqual(
            presentation.maximum,
            0,
        )

    def test_ready_result_presentation(self):
        presentation = (
            describe_download_result(
                MethodDownloadResult()
            )
        )

        self.assertTrue(
            presentation.ready
        )

        self.assertFalse(
            presentation.is_error
        )

        self.assertIn(
            "downloaded and verified",
            presentation.headline,
        )

        self.assertIn(
            "v2.7.0",
            presentation.installer_name,
        )

    def test_error_result_presentation(self):
        presentation = (
            describe_download_result(
                FakeDownloadResult(
                    is_error=True,
                    message=(
                        "Checksum mismatch."
                    ),
                )
            )
        )

        self.assertTrue(
            presentation.is_error
        )

        self.assertIn(
            "Checksum mismatch",
            presentation.detail,
        )

    def test_missing_release_is_refused(self):
        controller = (
            UpdateDownloadController(
                downloader=(
                    lambda release,
                    progress_callback:
                    FakeDownloadResult()
                )
            )
        )

        messages = []

        controller.status_changed.connect(
            messages.append
        )

        self.assertFalse(
            controller.start_download(None)
        )

        self.assertFalse(
            controller.is_busy
        )

        self.assertIn(
            "No verified release",
            " ".join(messages),
        )

    def test_controller_runs_downloader(self):
        release = object()

        expected_result = (
            FakeDownloadResult(
                ready=True,
                message="Verified.",
                installer_path=Path(
                    "03-37am-Presence-"
                    "Setup-v2.7.0.exe"
                ),
            )
        )

        expected_progress = (
            FakeProgress(
                bytes_downloaded=50,
                total_bytes=100,
            )
        )

        seen_release = []
        seen_results = []
        seen_progress = []
        finished = []

        def downloader(
            selected_release,
            *,
            progress_callback,
        ):
            seen_release.append(
                selected_release
            )

            progress_callback(
                expected_progress
            )

            return expected_result

        controller = (
            UpdateDownloadController(
                downloader=downloader
            )
        )

        controller.progress_changed.connect(
            seen_progress.append
        )

        controller.result_ready.connect(
            seen_results.append
        )

        controller.finished.connect(
            lambda: finished.append(True)
        )

        self.assertTrue(
            controller.start_download(
                release
            )
        )

        self.assertTrue(
            controller.wait(2.0)
        )

        self.process_events_until(
            lambda: bool(finished)
        )

        self.assertEqual(
            seen_release,
            [release],
        )

        self.assertEqual(
            seen_progress,
            [expected_progress],
        )

        self.assertEqual(
            seen_results,
            [expected_result],
        )

        self.assertFalse(
            controller.is_busy
        )

    def test_duplicate_download_is_blocked(self):
        release_download = (
            threading.Event()
        )

        def downloader(
            release,
            *,
            progress_callback,
        ):
            release_download.wait(2.0)

            return FakeDownloadResult(
                ready=True
            )

        controller = (
            UpdateDownloadController(
                downloader=downloader
            )
        )

        self.assertTrue(
            controller.start_download(
                object()
            )
        )

        self.assertFalse(
            controller.start_download(
                object()
            )
        )

        release_download.set()

        self.assertTrue(
            controller.wait(2.0)
        )

    def test_downloader_exception_is_friendly(self):
        def downloader(
            release,
            *,
            progress_callback,
        ):
            raise RuntimeError(
                "private download detail"
            )

        controller = (
            UpdateDownloadController(
                downloader=downloader
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
            controller.start_download(
                object()
            )
        )

        self.assertTrue(
            controller.wait(2.0)
        )

        self.process_events_until(
            lambda: bool(finished)
        )

        joined = " ".join(messages)

        self.assertIn(
            "failed unexpectedly",
            joined,
        )

        self.assertNotIn(
            "private download detail",
            joined,
        )

    def test_worker_thread_is_daemon(self):
        release_download = (
            threading.Event()
        )

        def downloader(
            release,
            *,
            progress_callback,
        ):
            release_download.wait(2.0)

            return FakeDownloadResult(
                ready=True
            )

        controller = (
            UpdateDownloadController(
                downloader=downloader
            )
        )

        self.assertTrue(
            controller.start_download(
                object()
            )
        )

        with controller._state_lock:
            thread = controller._thread

        self.assertIsNotNone(thread)
        self.assertTrue(thread.daemon)

        release_download.set()

        self.assertTrue(
            controller.wait(2.0)
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
