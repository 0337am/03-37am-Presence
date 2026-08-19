from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.system.local_music_preferences import (
    SCHEMA_VERSION,
    LocalMusicPreferences,
    LocalMusicPreferencesStore,
    local_music_preferences_from_payload,
    local_music_preferences_to_payload,
)
from src.ui.local_music_settings import (
    LocalMusicSettingsCard,
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


class LocalMusicStartupPreferenceTests(
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
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp.cleanup
        )

        self.root = Path(
            self.temp.name
        ).resolve()

        self.music_one = (
            self.root
            / "Music One"
        )

        self.music_two = (
            self.root
            / "Music Two"
        )

        self.music_one.mkdir()
        self.music_two.mkdir()

        self.preference_path = (
            self.root
            / "local_music_preferences.json"
        )

        self.store = (
            LocalMusicPreferencesStore(
                self.preference_path
            )
        )

    def make_card(
        self,
    ):
        runtime = (
            FakeRuntime()
        )

        card = (
            LocalMusicSettingsCard(
                self.store,
                runtime,
            )
        )

        self.addCleanup(
            card.deleteLater
        )

        return (
            card,
            runtime,
        )

    def test_defaults_enable_startup_scan(
        self,
    ):
        preferences = (
            LocalMusicPreferences()
        )

        self.assertTrue(
            preferences.scan_on_startup
        )

    def test_v2_payload_round_trip_preserves_disabled_setting(
        self,
    ):
        preferences = (
            LocalMusicPreferences(
                folders=(
                    str(
                        self.music_one
                    ),
                ),
                scan_on_startup=False,
            )
        )

        payload = (
            local_music_preferences_to_payload(
                preferences
            )
        )

        self.assertEqual(
            payload[
                "schema_version"
            ],
            SCHEMA_VERSION,
        )

        self.assertFalse(
            payload[
                "scan_on_startup"
            ]
        )

        self.assertEqual(
            local_music_preferences_from_payload(
                payload
            ),
            preferences,
        )

    def test_v1_payload_defaults_startup_scan_to_enabled(
        self,
    ):
        restored = (
            local_music_preferences_from_payload(
                {
                    "schema_version": 1,
                    "folders": [
                        str(
                            self.music_one
                        ),
                    ],
                }
            )
        )

        self.assertTrue(
            restored.scan_on_startup
        )

        self.assertEqual(
            restored.folders,
            (
                str(
                    self.music_one
                ),
            ),
        )

    def test_v2_payload_rejects_non_boolean_startup_flag(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            local_music_preferences_from_payload(
                {
                    "schema_version": 2,
                    "folders": [],
                    "scan_on_startup": "yes",
                }
            )

    def test_store_load_migrates_v1_file_to_v2(
        self,
    ):
        self.preference_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "folders": [
                        str(
                            self.music_one
                        ),
                    ],
                }
            ),
            encoding="utf-8",
        )

        preferences = (
            self.store.load()
        )

        self.assertTrue(
            preferences.scan_on_startup
        )

        self.assertEqual(
            preferences.folders,
            (
                str(
                    self.music_one
                ),
            ),
        )

        migrated = json.loads(
            self.preference_path.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            migrated[
                "schema_version"
            ],
            2,
        )

        self.assertTrue(
            migrated[
                "scan_on_startup"
            ]
        )

        self.assertFalse(
            (
                self.preference_path
                .with_name(
                    self.preference_path.name
                    + ".tmp"
                )
            ).exists()
        )

    def test_store_toggle_persists_and_preserves_folders(
        self,
    ):
        self.store.add_folder(
            str(
                self.music_one
            )
        )

        updated = (
            self.store.set_scan_on_startup(
                False
            )
        )

        self.assertFalse(
            updated.scan_on_startup
        )

        self.assertEqual(
            updated.folders,
            (
                str(
                    self.music_one
                ),
            ),
        )

        self.assertFalse(
            self.store.load().scan_on_startup
        )

    def test_add_folder_preserves_disabled_setting(
        self,
    ):
        self.store.set_scan_on_startup(
            False
        )

        self.store.add_folder(
            str(
                self.music_one
            )
        )

        preferences = (
            self.store.load()
        )

        self.assertFalse(
            preferences.scan_on_startup
        )

        self.assertEqual(
            preferences.folders,
            (
                str(
                    self.music_one
                ),
            ),
        )

    def test_remove_folder_preserves_disabled_setting(
        self,
    ):
        self.store.add_folder(
            str(
                self.music_one
            )
        )

        self.store.add_folder(
            str(
                self.music_two
            )
        )

        self.store.set_scan_on_startup(
            False
        )

        self.store.remove_folder(
            str(
                self.music_one
            )
        )

        preferences = (
            self.store.load()
        )

        self.assertFalse(
            preferences.scan_on_startup
        )

        self.assertEqual(
            preferences.folders,
            (
                str(
                    self.music_two
                ),
            ),
        )

    def test_card_checkbox_tracks_and_persists_preference(
        self,
    ):
        card, _runtime = (
            self.make_card()
        )

        self.assertTrue(
            card.startup_scan_box.isChecked()
        )

        card.startup_scan_box.setChecked(
            False
        )

        self.assertFalse(
            self.store.load().scan_on_startup
        )

        card.refresh_from_store()

        self.assertFalse(
            card.startup_scan_box.isChecked()
        )

    def test_disabled_preference_blocks_auto_scan_but_manual_rescan_works(
        self,
    ):
        self.store.add_folder(
            str(
                self.music_one
            )
        )

        self.store.set_scan_on_startup(
            False
        )

        card, runtime = (
            self.make_card()
        )

        self.assertFalse(
            card.scan_on_startup()
        )

        self.assertEqual(
            runtime.started,
            [],
        )

        self.assertTrue(
            card.rescan()
        )

        self.assertEqual(
            runtime.started,
            [
                (
                    str(
                        self.music_one
                    ),
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
