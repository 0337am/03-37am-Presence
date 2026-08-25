from __future__ import annotations

import inspect
import unittest
from pathlib import Path

from src.ui.dashboard import (
    DashboardPage,
)
from src.ui.main_window import (
    MainWindow,
)


class QueueRuntimeStub:

    def __init__(
        self,
    ):
        self.load_calls = 0

    def load_queue(
        self,
    ):
        self.load_calls += 1


class DashboardQueueRuntimeWiringTests(
    unittest.TestCase
):

    def test_dashboard_accepts_queue_runtime(
        self,
    ):
        harness = type(
            "DashboardHarness",
            (),
            {},
        )()

        runtime = QueueRuntimeStub()

        DashboardPage.set_spotify_queue_runtime(
            harness,
            runtime,
        )

        self.assertIs(
            harness.spotify_queue_runtime,
            runtime,
        )

        self.assertEqual(
            runtime.load_calls,
            0,
        )

    def test_dashboard_rejects_invalid_queue_runtime(
        self,
    ):
        harness = type(
            "DashboardHarness",
            (),
            {},
        )()

        with self.assertRaises(
            TypeError
        ):
            DashboardPage.set_spotify_queue_runtime(
                harness,
                object(),
            )

        self.assertFalse(
            hasattr(
                harness,
                "spotify_queue_runtime",
            )
        )

    def test_main_window_imports_queue_service_and_runtime(
        self,
    ):
        source_path = Path(
            inspect.getsourcefile(
                MainWindow
            )
        )

        source = source_path.read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            (
                "from src.spotify.queue_service "
                "import"
            ),
            source,
        )

        self.assertIn(
            "SpotifyQueueService",
            source,
        )

        self.assertIn(
            (
                "from src.spotify.qt_queue_runtime "
                "import"
            ),
            source,
        )

        self.assertIn(
            "SpotifyQtQueueRuntime",
            source,
        )

    def test_build_pages_uses_shared_session_manager_for_queue(
        self,
    ):
        source = inspect.getsource(
            MainWindow.build_pages
        )

        self.assertEqual(
            source.count(
                "SpotifySessionManager("
            ),
            1,
        )

        self.assertIn(
            (
                "lambda manager="
                "spotify_session_manager"
            ),
            source,
        )

        self.assertIn(
            "SpotifyQueueService(",
            source,
        )

    def test_build_pages_owns_queue_runtime(
        self,
    ):
        source = inspect.getsource(
            MainWindow.build_pages
        )

        self.assertIn(
            "self.spotify_queue_runtime",
            source,
        )

        self.assertIn(
            "SpotifyQtQueueRuntime(",
            source,
        )

        self.assertIn(
            "parent=self",
            source,
        )

    def test_build_pages_injects_queue_runtime_into_dashboard(
        self,
    ):
        source = inspect.getsource(
            MainWindow.build_pages
        )

        self.assertIn(
            (
                "DashboardPage."
                "set_spotify_queue_runtime"
            ),
            source,
        )

        self.assertIn(
            "self.dashboard_page",
            source,
        )

        self.assertIn(
            "self.spotify_queue_runtime",
            source,
        )

    def test_build_pages_does_not_eagerly_load_queue(
        self,
    ):
        source = inspect.getsource(
            MainWindow.build_pages
        )

        self.assertNotIn(
            ".load_queue(",
            source,
        )

    def test_shutdown_includes_queue_runtime(
        self,
    ):
        source = inspect.getsource(
            MainWindow.shutdown
        )

        self.assertEqual(
            source.count(
                '"spotify_queue_runtime"'
            ),
            1,
        )

        queue_index = source.index(
            '"spotify_queue_runtime"'
        )

        playback_index = source.index(
            '"spotify_playback_runtime"'
        )

        self.assertLess(
            queue_index,
            playback_index,
        )


if __name__ == "__main__":
    unittest.main()
