from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import (
    QObject,
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.media.local_music_index import (
    LocalMusicScanResult,
)
from src.media.qt_local_music_runtime import (
    LocalMusicQtRuntimeError,
)
from src.system.local_music_preferences import (
    LocalMusicPreferences,
    LocalMusicPreferencesStore,
)
from src.ui.local_music_settings import (
    LocalMusicSettingsCard,
)
from tests.repo_paths import REPO_ROOT


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

        self.start_error = None

    def start_scan(
        self,
        folders,
    ):
        if self.start_error is not None:
            raise self.start_error

        self.started.append(
            folders
        )

    def clear_latest_result(
        self,
    ):
        self.latest_result = None
        self.clear_count += 1


def scan_result(
    *,
    indexed=0,
    skipped=0,
    limit_reached=False,
    roots=(),
):
    return LocalMusicScanResult(
        candidates=(),
        roots=tuple(
            roots
        ),
        scanned_files=(
            indexed
            + skipped
        ),
        indexed_files=indexed,
        skipped_files=skipped,
        limit_reached=(
            limit_reached
        ),
    )


class LocalMusicSettingsBoundaryTests(
    unittest.TestCase
):
    def test_ui_owns_no_spotify_network_playback_or_credentials(
        self,
    ):
        root = (
            REPO_ROOT
        )

        source = (
            root
            / "src"
            / "ui"
            / "local_music_settings.py"
        ).read_text(
            encoding="utf-8"
        )

        for forbidden in (
            "SpotifyCredentialStore",
            "SpotifySessionManager",
            "SpotifyTokenClient",
            "access_token",
            "refresh_token",
            "client_secret",
            "urllib",
            "requests.",
            "webbrowser",
            "playback",
            "QSettings",
            "tinytag",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    source,
                )

    def test_settings_page_wires_local_music_components(
        self,
    ):
        root = (
            REPO_ROOT
        )

        source = (
            root
            / "src"
            / "ui"
            / "settings.py"
        ).read_text(
            encoding="utf-8"
        )

        for marker in (
            "LocalMusicPreferencesStore",
            "LocalMusicQtScanRuntime",
            "LocalMusicSettingsCard",
            "self.local_music_preferences_store",
            "self.local_music_runtime",
            "self.local_music_card",
            '"local_music"',
            "shutdown_local_music",
        ):
            with self.subTest(
                marker=marker
            ):
                self.assertIn(
                    marker,
                    source,
                )

    def test_portable_backup_still_excludes_local_music_paths(
        self,
    ):
        root = (
            REPO_ROOT
        )

        source = (
            root
            / "src"
            / "system"
            / "settings_backup.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "LocalMusicPreferencesStore",
            source,
        )

        self.assertNotIn(
            "local_music_preferences",
            source,
        )

    def test_main_window_shutdown_closes_local_music_runtime(
        self,
    ):
        root = (
            REPO_ROOT
        )

        source = (
            root
            / "src"
            / "ui"
            / "main_window.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "shutdown_local_music",
            source,
        )

        self.assertIn(
            "self.settings_page",
            source,
        )


class LocalMusicSettingsCardTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def setUp(
        self,
    ):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp.cleanup
        )

        self.root = Path(
            self.temp.name
        ).resolve()

        self.store = (
            LocalMusicPreferencesStore(
                self.root
                / "preferences.json"
            )
        )

        self.runtime = (
            FakeRuntime()
        )

        self.card = (
            LocalMusicSettingsCard(
                self.store,
                self.runtime,
            )
        )

        self.addCleanup(
            self.card.deleteLater
        )

    def test_card_loads_saved_folders(
        self,
    ):
        music = (
            self.root
            / "Music"
        )

        music.mkdir()

        self.store.save(
            LocalMusicPreferences(
                folders=(
                    str(
                        music
                    ),
                )
            )
        )

        self.card.refresh_from_store()

        self.assertEqual(
            self.card.folder_list.count(),
            1,
        )

        self.assertEqual(
            self.card.folder_list.item(
                0
            ).text(),
            str(
                music
            ),
        )

    def test_add_folder_persists_and_invalidates_index(
        self,
    ):
        music = (
            self.root
            / "Music"
        )

        music.mkdir()

        self.runtime.latest_result = (
            scan_result(
                indexed=3
            )
        )

        with patch(
            "src.ui.local_music_settings."
            "QFileDialog.getExistingDirectory",
            return_value=str(
                music
            ),
        ):
            self.assertTrue(
                self.card.add_folder()
            )

        preferences = (
            self.store.load()
        )

        self.assertIn(
            str(
                music
            ),
            preferences.folders,
        )

        self.assertEqual(
            self.runtime.clear_count,
            1,
        )

        self.assertIsNone(
            self.runtime.latest_result
        )

    def test_cancelled_add_does_not_change_preferences(
        self,
    ):
        with patch(
            "src.ui.local_music_settings."
            "QFileDialog.getExistingDirectory",
            return_value="",
        ):
            self.assertFalse(
                self.card.add_folder()
            )

        self.assertEqual(
            self.store.load().folders,
            (),
        )

    def test_remove_selected_folder_persists_and_invalidates_index(
        self,
    ):
        music = (
            self.root
            / "Music"
        )

        music.mkdir()

        self.store.add_folder(
            str(
                music
            )
        )

        self.card.refresh_from_store()

        self.card.folder_list.setCurrentRow(
            0
        )

        self.assertTrue(
            self.card.remove_selected_folder()
        )

        self.assertEqual(
            self.store.load().folders,
            (),
        )

        self.assertEqual(
            self.runtime.clear_count,
            1,
        )

    def test_remove_without_selection_is_safe(
        self,
    ):
        self.assertFalse(
            self.card.remove_selected_folder()
        )

    def test_rescan_requires_configured_folders(
        self,
    ):
        self.assertFalse(
            self.card.rescan()
        )

        self.assertEqual(
            self.runtime.started,
            [],
        )

        self.assertIn(
            "Add a Local Music folder",
            self.card.status_label.text(),
        )

    def test_rescan_forwards_only_available_folders(
        self,
    ):
        available = (
            self.root
            / "Music"
        )

        available.mkdir()

        unavailable = (
            self.root
            / "Missing"
        )

        self.store.save(
            LocalMusicPreferences(
                folders=(
                    str(
                        available
                    ),
                    str(
                        unavailable
                    ),
                )
            )
        )

        self.assertTrue(
            self.card.rescan()
        )

        self.assertEqual(
            self.runtime.started,
            [
                (
                    str(
                        available
                    ),
                ),
            ],
        )

        self.assertIn(
            "1 configured folder is unavailable",
            self.card.status_label.text(),
        )

    def test_rescan_with_only_unavailable_folders_is_safe(
        self,
    ):
        missing = (
            self.root
            / "Missing"
        )

        self.store.add_folder(
            str(
                missing
            )
        )

        self.assertFalse(
            self.card.rescan()
        )

        self.assertEqual(
            self.runtime.started,
            [],
        )

        self.assertIn(
            "currently available",
            self.card.status_label.text(),
        )

    def test_busy_state_disables_controls(
        self,
    ):
        music = (
            self.root
            / "Music"
        )

        music.mkdir()

        self.store.add_folder(
            str(
                music
            )
        )

        self.card.refresh_from_store()

        self.card.folder_list.setCurrentRow(
            0
        )

        self.runtime.busy_changed.emit(
            True
        )

        QApplication.processEvents()

        self.assertFalse(
            self.card.add_button.isEnabled()
        )

        self.assertFalse(
            self.card.remove_button.isEnabled()
        )

        self.assertFalse(
            self.card.rescan_button.isEnabled()
        )

        self.assertFalse(
            self.card.folder_list.isEnabled()
        )

        self.runtime.busy_changed.emit(
            False
        )

        QApplication.processEvents()

        self.assertTrue(
            self.card.add_button.isEnabled()
        )

    def test_successful_result_updates_status(
        self,
    ):
        self.runtime.result_ready.emit(
            scan_result(
                indexed=143,
                skipped=2,
            )
        )

        QApplication.processEvents()

        text = (
            self.card.status_label.text()
        )

        self.assertIn(
            "143 tracks indexed",
            text,
        )

        self.assertIn(
            "2 files skipped",
            text,
        )

    def test_failure_is_user_safe(
        self,
    ):
        self.runtime.failed.emit(
            "scan_failed",
            (
                "Local Music could not scan "
                "the selected folders."
            ),
        )

        QApplication.processEvents()

        self.assertEqual(
            self.card.status_label.text(),
            (
                "Local Music could not scan "
                "the selected folders."
            ),
        )

    def test_cancelled_scan_updates_status(
        self,
    ):
        self.runtime.scan_cancelled.emit()

        QApplication.processEvents()

        self.assertEqual(
            self.card.status_label.text(),
            "Local Music scan cancelled.",
        )

    def test_runtime_start_error_is_user_safe(
        self,
    ):
        music = (
            self.root
            / "Music"
        )

        music.mkdir()

        self.store.add_folder(
            str(
                music
            )
        )

        self.runtime.start_error = (
            LocalMusicQtRuntimeError(
                "busy",
                (
                    "A Local Music scan is "
                    "already running."
                ),
            )
        )

        self.assertFalse(
            self.card.rescan()
        )

        self.assertEqual(
            self.card.status_label.text(),
            (
                "A Local Music scan is "
                "already running."
            ),
        )

    def test_refresh_from_store_updates_list(
        self,
    ):
        first = (
            self.root
            / "One"
        )

        second = (
            self.root
            / "Two"
        )

        first.mkdir()
        second.mkdir()

        self.store.save(
            LocalMusicPreferences(
                folders=(
                    str(
                        first
                    ),
                    str(
                        second
                    ),
                )
            )
        )

        self.assertTrue(
            self.card.refresh_from_store()
        )

        self.assertEqual(
            self.card.folder_list.count(),
            2,
        )

        self.assertEqual(
            self.card.folder_summary.text(),
            "2 folders configured",
        )

    def test_folder_paths_are_kept_as_item_data(
        self,
    ):
        music = (
            self.root
            / "Music"
        )

        music.mkdir()

        self.store.add_folder(
            str(
                music
            )
        )

        self.card.refresh_from_store()

        item = (
            self.card.folder_list.item(
                0
            )
        )

        self.assertEqual(
            item.data(
                Qt.ItemDataRole.UserRole
            ),
            str(
                music
            ),
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
