from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.system.local_music_preferences import (
    MAX_LOCAL_MUSIC_FOLDERS,
    MAX_PREFERENCES_FILE_BYTES,
    LocalMusicPreferences,
    LocalMusicPreferencesStore,
    local_music_preferences_from_payload,
    local_music_preferences_to_payload,
)
from tests.repo_paths import REPO_ROOT


class LocalMusicPreferencesTests(
    unittest.TestCase
):
    def test_defaults_are_empty(
        self,
    ):
        preferences = (
            LocalMusicPreferences()
        )

        self.assertEqual(
            preferences.folders,
            (),
        )

    def test_constructor_normalizes_and_deduplicates(
        self,
    ):
        preferences = (
            LocalMusicPreferences(
                folders=(
                    r"C:\Music\Juice WRLD\\",
                    r"c:\music\juice wrld",
                )
            )
        )

        self.assertEqual(
            len(
                preferences.folders
            ),
            1,
        )

        self.assertEqual(
            preferences.folders[
                0
            ],
            r"C:\Music\Juice WRLD",
        )

    def test_relative_folder_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            LocalMusicPreferences(
                folders=(
                    "Music",
                )
            )

    def test_network_folder_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            LocalMusicPreferences(
                folders=(
                    r"\\server\Music",
                )
            )

    def test_folder_limit_is_enforced(
        self,
    ):
        folders = tuple(
            (
                r"C:\Music\Folder"
                + str(
                    index
                )
            )
            for index in range(
                MAX_LOCAL_MUSIC_FOLDERS
                + 1
            )
        )

        with self.assertRaises(
            ValueError
        ):
            LocalMusicPreferences(
                folders=folders
            )

    def test_payload_round_trip(
        self,
    ):
        preferences = (
            LocalMusicPreferences(
                folders=(
                    r"C:\Music",
                    r"D:\Local Files",
                )
            )
        )

        payload = (
            local_music_preferences_to_payload(
                preferences
            )
        )

        restored = (
            local_music_preferences_from_payload(
                payload
            )
        )

        self.assertEqual(
            restored,
            preferences,
        )

    def test_payload_rejects_wrong_schema(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            local_music_preferences_from_payload(
                {
                    "schema_version": 999,
                    "folders": [],
                }
            )

    def test_payload_requires_folder_list(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            local_music_preferences_from_payload(
                {
                    "schema_version": 1,
                    "folders": (
                        r"C:\Music",
                    ),
                }
            )

    def test_nonexistent_absolute_folder_can_be_remembered(
        self,
    ):
        preferences = (
            LocalMusicPreferences(
                folders=(
                    (
                        r"Z:\Temporarily "
                        r"Unavailable Music"
                    ),
                )
            )
        )

        self.assertEqual(
            preferences.folders,
            (
                (
                    r"Z:\Temporarily "
                    r"Unavailable Music"
                ),
            ),
        )


class LocalMusicPreferencesStoreTests(
    unittest.TestCase
):
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

    def store(
        self,
    ):
        return (
            LocalMusicPreferencesStore(
                self.root
                / "local_music_preferences.json"
            )
        )

    def test_store_uses_expected_localappdata_path(
        self,
    ):
        local_app_data = (
            self.root
            / "LocalAppData"
        )

        with patch.dict(
            os.environ,
            {
                "LOCALAPPDATA": str(
                    local_app_data
                ),
            },
            clear=False,
        ):
            store = (
                LocalMusicPreferencesStore()
            )

        self.assertEqual(
            store.file_path,
            (
                local_app_data
                / "0337am Presence"
                / "local_music_preferences.json"
            ),
        )

    def test_store_creates_default_file(
        self,
    ):
        store = self.store()

        self.assertTrue(
            store.file_path.is_file()
        )

        self.assertEqual(
            store.load(),
            LocalMusicPreferences(),
        )

    def test_save_and_load_round_trip(
        self,
    ):
        store = self.store()

        preferences = (
            LocalMusicPreferences(
                folders=(
                    r"C:\Music",
                    r"D:\Juice WRLD",
                )
            )
        )

        store.save(
            preferences
        )

        self.assertEqual(
            store.load(),
            preferences,
        )

    def test_add_folder_persists(
        self,
    ):
        store = self.store()

        updated = store.add_folder(
            r"C:\Music"
        )

        self.assertEqual(
            updated.folders,
            (
                r"C:\Music",
            ),
        )

        self.assertEqual(
            store.load(),
            updated,
        )

    def test_duplicate_add_is_deduplicated(
        self,
    ):
        store = self.store()

        store.add_folder(
            r"C:\Music"
        )

        updated = store.add_folder(
            r"c:\music\\"
        )

        self.assertEqual(
            updated.folders,
            (
                r"C:\Music",
            ),
        )

    def test_remove_folder_persists(
        self,
    ):
        store = self.store()

        store.save(
            LocalMusicPreferences(
                folders=(
                    r"C:\Music",
                    r"D:\Juice WRLD",
                )
            )
        )

        updated = store.remove_folder(
            r"C:\Music"
        )

        self.assertEqual(
            updated.folders,
            (
                r"D:\Juice WRLD",
            ),
        )

        self.assertEqual(
            store.load(),
            updated,
        )

    def test_remove_missing_folder_is_safe(
        self,
    ):
        store = self.store()

        original = store.add_folder(
            r"C:\Music"
        )

        updated = store.remove_folder(
            r"D:\Missing"
        )

        self.assertEqual(
            updated,
            original,
        )

    def test_invalid_json_is_quarantined_and_replaced(
        self,
    ):
        store = self.store()

        store.file_path.write_text(
            "{ definitely not json",
            encoding="utf-8",
        )

        preferences = store.load()

        self.assertEqual(
            preferences,
            LocalMusicPreferences(),
        )

        quarantined = list(
            store.file_path.parent.glob(
                (
                    "local_music_preferences"
                    ".invalid-*.json"
                )
            )
        )

        self.assertEqual(
            len(
                quarantined
            ),
            1,
        )

        self.assertTrue(
            store.file_path.is_file()
        )

    def test_invalid_schema_is_quarantined_and_replaced(
        self,
    ):
        store = self.store()

        store.file_path.write_text(
            json.dumps(
                {
                    "schema_version": 999,
                    "folders": [],
                }
            ),
            encoding="utf-8",
        )

        preferences = store.load()

        self.assertEqual(
            preferences,
            LocalMusicPreferences(),
        )

        quarantined = list(
            store.file_path.parent.glob(
                (
                    "local_music_preferences"
                    ".invalid-*.json"
                )
            )
        )

        self.assertEqual(
            len(
                quarantined
            ),
            1,
        )

    def test_oversized_file_is_quarantined(
        self,
    ):
        store = self.store()

        store.file_path.write_text(
            "x"
            * (
                MAX_PREFERENCES_FILE_BYTES
                + 1
            ),
            encoding="utf-8",
        )

        preferences = store.load()

        self.assertEqual(
            preferences,
            LocalMusicPreferences(),
        )

        quarantined = list(
            store.file_path.parent.glob(
                (
                    "local_music_preferences"
                    ".invalid-*.json"
                )
            )
        )

        self.assertEqual(
            len(
                quarantined
            ),
            1,
        )

    def test_save_leaves_no_temporary_file(
        self,
    ):
        store = self.store()

        store.save(
            LocalMusicPreferences(
                folders=(
                    r"C:\Music",
                )
            )
        )

        temporary = (
            store.file_path.with_name(
                store.file_path.name
                + ".tmp"
            )
        )

        self.assertFalse(
            temporary.exists()
        )

    def test_wrong_save_type_is_rejected(
        self,
    ):
        store = self.store()

        with self.assertRaises(
            TypeError
        ):
            store.save(
                object()
            )


class LocalMusicPreferencesBoundaryTests(
    unittest.TestCase
):
    def test_module_owns_no_qt_spotify_network_or_scanner(
        self,
    ):
        root = (
            REPO_ROOT
        )

        source = (
            root
            / "src"
            / "system"
            / "local_music_preferences.py"
        ).read_text(
            encoding="utf-8"
        )

        for forbidden in (
            "PyQt",
            "QSettings",
            "SpotifyCredentialStore",
            "SpotifySessionManager",
            "SpotifyTokenClient",
            "access_token",
            "refresh_token",
            "client_secret",
            "urllib",
            "requests.",
            "LocalMusicIndex",
            "tinytag",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    source,
                )

    def test_portable_settings_backup_does_not_export_local_music_paths(
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


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
