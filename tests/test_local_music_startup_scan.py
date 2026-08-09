from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.system.local_music_preferences import (
    LocalMusicPreferencesStore,
)
from src.ui.local_music_settings import (
    LocalMusicSettingsCard,
)
from src.ui.main_window import (
    MainWindow,
)


class FakeRuntime(
    QObject
):
    busy_changed = pyqtSignal(
        bool
    )

    result_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
    )

    scan_cancelled = pyqtSignal()

    def __init__(
        self,
    ):
        super().__init__()

        self.busy = False
        self.latest_result = None
        self.started = []
        self.clear_count = 0

    def start_scan(
        self,
        folders,
    ):
        self.started.append(
            folders
        )

    def clear_latest_result(
        self,
    ):
        self.latest_result = None
        self.clear_count += 1


class StartupScanCard(
    LocalMusicSettingsCard
):
    pass


class LocalMusicStartupScanTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication(
                []
            )
        )

    def setUp(
        self,
    ):
        self.temporary = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temporary.cleanup
        )

        self.root = Path(
            self.temporary.name
        )

        self.music = (
            self.root
            / "Music"
        )

        self.music.mkdir()

        self.store = (
            LocalMusicPreferencesStore(
                path=(
                    self.root
                    / "local_music_preferences.json"
                )
            )
        )

        self.runtime = (
            FakeRuntime()
        )

        self.card = (
            StartupScanCard(
                self.store,
                self.runtime,
            )
        )

        self.addCleanup(
            self.card.deleteLater
        )

    def test_startup_scan_starts_existing_runtime_for_configured_folder(
        self,
    ):
        self.store.add_folder(
            str(
                self.music
            )
        )

        self.assertTrue(
            self.card.scan_on_startup()
        )

        self.assertEqual(
            len(
                self.runtime.started
            ),
            1,
        )

        self.assertEqual(
            self.runtime.started[
                0
            ],
            (
                str(
                    self.music
                ),
            ),
        )

    def test_startup_scan_without_folders_is_passive(
        self,
    ):
        original_status = (
            self.card.status_label.text()
        )

        self.assertFalse(
            self.card.scan_on_startup()
        )

        self.assertEqual(
            self.runtime.started,
            [],
        )

        self.assertEqual(
            self.card.status_label.text(),
            original_status,
        )

    def test_startup_scan_does_not_duplicate_existing_result(
        self,
    ):
        self.store.add_folder(
            str(
                self.music
            )
        )

        self.runtime.latest_result = (
            object()
        )

        self.assertFalse(
            self.card.scan_on_startup()
        )

        self.assertEqual(
            self.runtime.started,
            [],
        )

    def test_main_window_schedules_scan_after_normal_startup_restore(
        self,
    ):
        init_source = (
            inspect.getsource(
                MainWindow.__init__
            )
        )

        schedule_source = (
            inspect.getsource(
                MainWindow
                ._schedule_local_music_startup_scan
            )
        )

        self.assertLess(
            init_source.index(
                "self.restore_last_page()"
            ),
            init_source.index(
                (
                    "self."
                    "_schedule_local_music_"
                    "startup_scan()"
                )
            ),
        )

        self.assertIn(
            "QTimer.singleShot",
            schedule_source,
        )

        self.assertIn(
            "_start_local_music_startup_scan",
            schedule_source,
        )

    def test_main_window_startup_handler_delegates_and_honors_shutdown(
        self,
    ):
        observed = []

        card = SimpleNamespace(
            scan_on_startup=(
                lambda:
                observed.append(
                    True
                )
                or True
            )
        )

        fake_window = SimpleNamespace(
            _shutting_down=False,
            settings_page=(
                SimpleNamespace(
                    local_music_card=card
                )
            ),
        )

        self.assertTrue(
            MainWindow
            ._start_local_music_startup_scan(
                fake_window
            )
        )

        self.assertEqual(
            observed,
            [
                True,
            ],
        )

        fake_window._shutting_down = True

        self.assertFalse(
            MainWindow
            ._start_local_music_startup_scan(
                fake_window
            )
        )

        self.assertEqual(
            observed,
            [
                True,
            ],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
