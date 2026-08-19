from __future__ import annotations

import unittest
from unittest.mock import patch

import main


class FakeSignal:
    def __init__(
        self,
    ):
        self.callbacks = []

    def connect(
        self,
        callback,
    ):
        self.callbacks.append(
            callback
        )


class FakeApp:
    def __init__(
        self,
    ):
        self.aboutToQuit = (
            FakeSignal()
        )


class FakeRuntime:
    start_result = True

    def __init__(
        self,
        *,
        app,
    ):
        self.app = app
        self.start_count = 0
        self.close_count = 0

    def start(
        self,
    ):
        self.start_count += 1

        return self.start_result

    def close(
        self,
    ):
        self.close_count += 1

        return True


class MediaHotkeyMainWiringTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        FakeRuntime.start_result = (
            True
        )

    def test_runtime_starts_and_shutdown_is_connected(
        self,
    ):
        app = FakeApp()

        with patch(
            "main.MediaHotkeyRuntime",
            FakeRuntime,
        ):
            runtime = (
                main.start_media_hotkey_runtime(
                    app
                )
            )

        self.assertIsInstance(
            runtime,
            FakeRuntime,
        )

        self.assertIs(
            runtime.app,
            app,
        )

        self.assertEqual(
            runtime.start_count,
            1,
        )

        self.assertEqual(
            len(
                app.aboutToQuit.callbacks
            ),
            1,
        )

        app.aboutToQuit.callbacks[
            0
        ]()

        self.assertEqual(
            runtime.close_count,
            1,
        )

    def test_start_failure_does_not_abort_application_wiring(
        self,
    ):
        app = FakeApp()

        FakeRuntime.start_result = (
            False
        )

        with patch(
            "main.MediaHotkeyRuntime",
            FakeRuntime,
        ):
            runtime = (
                main.start_media_hotkey_runtime(
                    app
                )
            )

        self.assertIsInstance(
            runtime,
            FakeRuntime,
        )

        self.assertEqual(
            runtime.start_count,
            1,
        )

        self.assertEqual(
            len(
                app.aboutToQuit.callbacks
            ),
            1,
        )

        app.aboutToQuit.callbacks[
            0
        ]()

        self.assertEqual(
            runtime.close_count,
            1,
        )

    def test_runtime_construction_failure_is_nonfatal(
        self,
    ):
        app = FakeApp()

        with patch(
            "main.MediaHotkeyRuntime",
            side_effect=RuntimeError(
                "simulated construction failure"
            ),
        ):
            runtime = (
                main.start_media_hotkey_runtime(
                    app
                )
            )

        self.assertIsNone(
            runtime
        )

        self.assertEqual(
            app.aboutToQuit.callbacks,
            [],
        )


if __name__ == "__main__":
    unittest.main()
