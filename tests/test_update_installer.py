from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from src.system.update_downloader import (
    UpdateDownloadResult,
    UpdateDownloadStatus,
)
from src.system.update_installer import (
    PreparedUpdateInstall,
    UpdateInstallError,
    UpdateInstallStatus,
    expected_installer_filename,
    launch_downloaded_update,
    launch_prepared_update,
    prepare_update_install,
)


VERSION = "2.7.0"

INSTALLER_NAME = (
    "03-37am-Presence-"
    "Setup-v2.7.0.exe"
)


def create_ready_result(
    root: str,
    *,
    content: bytes = b"MZ verified installer",
    filename: str = INSTALLER_NAME,
) -> tuple[
    UpdateDownloadResult,
    Path,
    str,
]:
    directory = Path(root) / "verified"

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    installer_path = (
        directory / filename
    )

    installer_path.write_bytes(
        content
    )

    digest = hashlib.sha256(
        content
    ).hexdigest()

    result = UpdateDownloadResult(
        status=(
            UpdateDownloadStatus.READY
        ),
        version=VERSION,
        message=(
            "The update is ready "
            "to install."
        ),
        download_directory=directory,
        installer_path=installer_path,
        checksum_path=(
            directory / "SHA256SUMS.txt"
        ),
        expected_sha256=digest,
        actual_sha256=digest,
        bytes_downloaded=len(
            content
        ),
    )

    return (
        result,
        installer_path,
        digest,
    )


class UpdateInstallerTests(
    unittest.TestCase
):
    def test_expected_filename_is_versioned(self):
        self.assertEqual(
            expected_installer_filename(
                "v2.7.0"
            ),
            INSTALLER_NAME,
        )

    def test_ready_download_is_prepared(self):
        with tempfile.TemporaryDirectory() as root:
            (
                result,
                installer_path,
                digest,
            ) = create_ready_result(
                root
            )

            prepared = (
                prepare_update_install(
                    result
                )
            )

            self.assertEqual(
                prepared.version,
                VERSION,
            )
            self.assertEqual(
                prepared.installer_path,
                installer_path.resolve(),
            )
            self.assertEqual(
                prepared.sha256,
                digest,
            )

    def test_invalid_download_result_is_rejected(self):
        with self.assertRaises(
            UpdateInstallError
        ) as context:
            prepare_update_install(
                object()
            )

        self.assertEqual(
            context.exception.error_code,
            "invalid_download_result",
        )

    def test_unverified_download_is_rejected(self):
        result = UpdateDownloadResult(
            status=(
                UpdateDownloadStatus.ERROR
            ),
            version=VERSION,
            message="Failed",
            error_code="offline",
        )

        with self.assertRaises(
            UpdateInstallError
        ) as context:
            prepare_update_install(
                result
            )

        self.assertEqual(
            context.exception.error_code,
            "download_not_ready",
        )

    def test_unexpected_filename_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            result, _, _ = create_ready_result(
                root,
                filename="unexpected.exe",
            )

            with self.assertRaises(
                UpdateInstallError
            ) as context:
                prepare_update_install(
                    result
                )

            self.assertEqual(
                context.exception.error_code,
                "unexpected_filename",
            )

    def test_installer_outside_folder_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            result, _, digest = (
                create_ready_result(
                    root
                )
            )

            outside = (
                Path(root)
                / INSTALLER_NAME
            )

            outside.write_bytes(
                b"MZ verified installer"
            )

            result = UpdateDownloadResult(
                status=result.status,
                version=result.version,
                message=result.message,
                download_directory=(
                    result
                    .download_directory
                ),
                installer_path=outside,
                checksum_path=(
                    result.checksum_path
                ),
                expected_sha256=digest,
                actual_sha256=digest,
                bytes_downloaded=(
                    result.bytes_downloaded
                ),
            )

            with self.assertRaises(
                UpdateInstallError
            ) as context:
                prepare_update_install(
                    result
                )

            self.assertEqual(
                context.exception.error_code,
                "unsafe_installer_location",
            )

    def test_recorded_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            result, _, _ = create_ready_result(
                root
            )

            result = UpdateDownloadResult(
                status=result.status,
                version=result.version,
                message=result.message,
                download_directory=(
                    result.download_directory
                ),
                installer_path=(
                    result.installer_path
                ),
                checksum_path=(
                    result.checksum_path
                ),
                expected_sha256=(
                    result.expected_sha256
                ),
                actual_sha256="f" * 64,
                bytes_downloaded=(
                    result.bytes_downloaded
                ),
            )

            with self.assertRaises(
                UpdateInstallError
            ) as context:
                prepare_update_install(
                    result
                )

            self.assertEqual(
                context.exception.error_code,
                "recorded_hash_mismatch",
            )

    def test_tampering_before_prepare_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            result, installer_path, _ = (
                create_ready_result(
                    root
                )
            )

            installer_path.write_bytes(
                b"tampered"
            )

            with self.assertRaises(
                UpdateInstallError
            ) as context:
                prepare_update_install(
                    result
                )

            self.assertEqual(
                context.exception.error_code,
                "hash_mismatch",
            )

    def test_launch_requires_explicit_approval(self):
        with tempfile.TemporaryDirectory() as root:
            result, _, _ = create_ready_result(
                root
            )

            prepared = (
                prepare_update_install(
                    result
                )
            )

            opened = []
            quit_calls = []

            launch_result = (
                launch_prepared_update(
                    prepared,
                    user_approved=False,
                    opener=opened.append,
                    quit_callback=(
                        lambda: quit_calls.append(
                            True
                        )
                    ),
                )
            )

            self.assertEqual(
                launch_result.error_code,
                "approval_required",
            )
            self.assertEqual(
                opened,
                [],
            )
            self.assertEqual(
                quit_calls,
                [],
            )

    def test_launch_uses_plain_path_then_quits(self):
        with tempfile.TemporaryDirectory() as root:
            result, installer_path, _ = (
                create_ready_result(
                    root
                )
            )

            prepared = (
                prepare_update_install(
                    result
                )
            )

            events = []

            def opener(path):
                events.append(
                    ("open", path)
                )

            def quit_callback():
                events.append(
                    ("quit", None)
                )

            launch_result = (
                launch_prepared_update(
                    prepared,
                    user_approved=True,
                    opener=opener,
                    quit_callback=(
                        quit_callback
                    ),
                )
            )

            self.assertEqual(
                launch_result.status,
                UpdateInstallStatus.LAUNCHED,
            )
            self.assertTrue(
                launch_result.launched
            )
            self.assertTrue(
                launch_result.quit_requested
            )
            self.assertEqual(
                events,
                [
                    (
                        "open",
                        os.fspath(
                            installer_path
                            .resolve()
                        ),
                    ),
                    ("quit", None),
                ],
            )

    def test_tampering_after_prepare_blocks_launch(self):
        with tempfile.TemporaryDirectory() as root:
            result, installer_path, _ = (
                create_ready_result(
                    root
                )
            )

            prepared = (
                prepare_update_install(
                    result
                )
            )

            installer_path.write_bytes(
                b"changed after prepare"
            )

            opened = []

            launch_result = (
                launch_prepared_update(
                    prepared,
                    user_approved=True,
                    opener=opened.append,
                )
            )

            self.assertEqual(
                launch_result.error_code,
                "hash_mismatch",
            )
            self.assertEqual(
                opened,
                [],
            )

    def test_missing_file_after_prepare_blocks_launch(self):
        with tempfile.TemporaryDirectory() as root:
            result, installer_path, _ = (
                create_ready_result(
                    root
                )
            )

            prepared = (
                prepare_update_install(
                    result
                )
            )

            installer_path.unlink()
            opened = []

            launch_result = (
                launch_prepared_update(
                    prepared,
                    user_approved=True,
                    opener=opened.append,
                )
            )

            self.assertEqual(
                launch_result.error_code,
                "installer_missing",
            )
            self.assertEqual(
                opened,
                [],
            )

    def test_invalid_prepared_object_is_rejected(self):
        opened = []

        launch_result = (
            launch_prepared_update(
                object(),
                user_approved=True,
                opener=opened.append,
            )
        )

        self.assertEqual(
            launch_result.error_code,
            "invalid_prepared_update",
        )
        self.assertEqual(
            opened,
            [],
        )

    def test_opener_failure_does_not_request_quit(self):
        with tempfile.TemporaryDirectory() as root:
            result, _, _ = create_ready_result(
                root
            )

            prepared = (
                prepare_update_install(
                    result
                )
            )

            quit_calls = []

            def opener(path):
                raise OSError(
                    "blocked"
                )

            launch_result = (
                launch_prepared_update(
                    prepared,
                    user_approved=True,
                    opener=opener,
                    quit_callback=(
                        lambda: quit_calls.append(
                            True
                        )
                    ),
                )
            )

            self.assertEqual(
                launch_result.error_code,
                "launch_failed",
            )
            self.assertEqual(
                quit_calls,
                [],
            )

    def test_quit_failure_preserves_launched_state(self):
        with tempfile.TemporaryDirectory() as root:
            result, installer_path, _ = (
                create_ready_result(
                    root
                )
            )

            prepared = (
                prepare_update_install(
                    result
                )
            )

            opened = []

            def quit_callback():
                raise RuntimeError(
                    "window already closing"
                )

            launch_result = (
                launch_prepared_update(
                    prepared,
                    user_approved=True,
                    opener=opened.append,
                    quit_callback=(
                        quit_callback
                    ),
                )
            )

            self.assertTrue(
                launch_result.launched
            )
            self.assertEqual(
                launch_result.error_code,
                "quit_failed",
            )
            self.assertFalse(
                launch_result.quit_requested
            )
            self.assertEqual(
                opened,
                [
                    os.fspath(
                        installer_path
                        .resolve()
                    )
                ],
            )

    def test_convenience_function(self):
        with tempfile.TemporaryDirectory() as root:
            result, installer_path, _ = (
                create_ready_result(
                    root
                )
            )

            opened = []

            launch_result = (
                launch_downloaded_update(
                    result,
                    user_approved=True,
                    opener=opened.append,
                )
            )

            self.assertTrue(
                launch_result.launched
            )
            self.assertEqual(
                opened,
                [
                    os.fspath(
                        installer_path
                        .resolve()
                    )
                ],
            )

    def test_module_has_no_command_runner(self):
        source_path = (
            Path(__file__)
            .resolve()
            .parents[1]
            / "src"
            / "system"
            / "update_installer.py"
        )

        source = source_path.read_text(
            encoding="utf-8-sig"
        ).lower()

        forbidden_values = (
            "subprocess",
            "shell=true",
            "popen(",
            "os.system",
            "/verysilent",
            "/silent",
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