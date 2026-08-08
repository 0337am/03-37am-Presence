from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.system.first_run import (
    FIRST_RUN_STATE_FILENAME,
    FIRST_RUN_TEMP_FILENAME,
    INVALID_STATE_PREFIX,
    STATE_SCHEMA_VERSION,
    FirstRunManager,
    FirstRunState,
    FirstRunStateStore,
    WELCOME_STATE_COMPLETE,
    WELCOME_STATE_PENDING,
    WELCOME_VERSION,
)


class FirstRunManagerTests(
    unittest.TestCase
):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        self.root = Path(
            self.temporary_directory.name
        )

        self.app_data = (
            self.root
            / "0337am Presence"
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def manager(self):
        return FirstRunManager(
            app_data_directory=(
                self.app_data
            )
        )

    def state_payload(self):
        path = (
            self.app_data
            / FIRST_RUN_STATE_FILENAME
        )

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    def test_fresh_install_requests_welcome(
        self,
    ):
        manager = self.manager()

        decision = manager.evaluate()

        self.assertTrue(
            decision.show_welcome
        )

        self.assertFalse(
            decision.migrated_existing_install
        )

        self.assertEqual(
            decision.reason,
            "fresh_install",
        )

        payload = self.state_payload()

        self.assertEqual(
            payload["schema_version"],
            STATE_SCHEMA_VERSION,
        )

        self.assertEqual(
            payload["state"],
            WELCOME_STATE_PENDING,
        )

        self.assertEqual(
            payload["welcome_version"],
            0,
        )

    def test_pending_welcome_survives_new_app_data(
        self,
    ):
        manager = self.manager()

        first = manager.evaluate()

        self.assertTrue(
            first.show_welcome
        )

        (
            self.app_data
            / "library.db"
        ).write_bytes(
            b"created-after-detection"
        )

        second = (
            self.manager()
            .evaluate()
        )

        self.assertTrue(
            second.show_welcome
        )

        self.assertEqual(
            second.reason,
            "pending_welcome",
        )

    def test_existing_local_data_is_migrated_silently(
        self,
    ):
        self.app_data.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            self.app_data
            / "source_preferences.json"
        ).write_text(
            "{}",
            encoding="utf-8",
        )

        decision = (
            self.manager()
            .evaluate()
        )

        self.assertFalse(
            decision.show_welcome
        )

        self.assertTrue(
            decision.migrated_existing_install
        )

        self.assertEqual(
            decision.reason,
            "existing_install",
        )

        payload = self.state_payload()

        self.assertEqual(
            payload["state"],
            WELCOME_STATE_COMPLETE,
        )

        self.assertEqual(
            payload["welcome_version"],
            WELCOME_VERSION,
        )

    def test_empty_app_data_directory_is_fresh(
        self,
    ):
        self.app_data.mkdir(
            parents=True,
            exist_ok=True,
        )

        decision = (
            self.manager()
            .evaluate()
        )

        self.assertTrue(
            decision.show_welcome
        )

        self.assertEqual(
            decision.reason,
            "fresh_install",
        )

    def test_completed_welcome_is_not_shown_again(
        self,
    ):
        manager = self.manager()

        manager.mark_completed()

        decision = manager.evaluate()

        self.assertFalse(
            decision.show_welcome
        )

        self.assertFalse(
            decision.migrated_existing_install
        )

        self.assertEqual(
            decision.reason,
            "completed",
        )

    def test_mark_completed_finishes_pending_welcome(
        self,
    ):
        manager = self.manager()

        manager.mark_pending()

        self.assertFalse(
            manager.is_completed()
        )

        manager.mark_completed()

        self.assertTrue(
            manager.is_completed()
        )

    def test_old_completed_version_is_repaired_silently(
        self,
    ):
        store = FirstRunStateStore(
            app_data_directory=(
                self.app_data
            )
        )

        store.save(
            FirstRunState(
                state=(
                    WELCOME_STATE_COMPLETE
                ),
                welcome_version=0,
            )
        )

        decision = (
            FirstRunManager(
                store=store
            )
            .evaluate()
        )

        self.assertFalse(
            decision.show_welcome
        )

        payload = self.state_payload()

        self.assertEqual(
            payload["state"],
            WELCOME_STATE_COMPLETE,
        )

        self.assertEqual(
            payload["welcome_version"],
            WELCOME_VERSION,
        )

    def test_corrupt_state_on_fresh_install_is_quarantined(
        self,
    ):
        self.app_data.mkdir(
            parents=True,
            exist_ok=True,
        )

        state_path = (
            self.app_data
            / FIRST_RUN_STATE_FILENAME
        )

        state_path.write_text(
            "{broken",
            encoding="utf-8",
        )

        decision = (
            self.manager()
            .evaluate()
        )

        self.assertTrue(
            decision.show_welcome
        )

        self.assertEqual(
            decision.reason,
            "fresh_install",
        )

        invalid_files = list(
            self.app_data.glob(
                f"{INVALID_STATE_PREFIX}*.json"
            )
        )

        self.assertEqual(
            len(
                invalid_files
            ),
            1,
        )

        payload = self.state_payload()

        self.assertEqual(
            payload["state"],
            WELCOME_STATE_PENDING,
        )

    def test_corrupt_state_on_existing_install_migrates_silently(
        self,
    ):
        self.app_data.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            self.app_data
            / FIRST_RUN_STATE_FILENAME
        ).write_text(
            "{broken",
            encoding="utf-8",
        )

        existing_file = (
            self.app_data
            / "library.db"
        )

        existing_file.write_bytes(
            b"existing-library"
        )

        decision = (
            self.manager()
            .evaluate()
        )

        self.assertFalse(
            decision.show_welcome
        )

        self.assertTrue(
            decision.migrated_existing_install
        )

        self.assertEqual(
            existing_file.read_bytes(),
            b"existing-library",
        )

        payload = self.state_payload()

        self.assertEqual(
            payload["state"],
            WELCOME_STATE_COMPLETE,
        )

    def test_unsupported_schema_is_quarantined(
        self,
    ):
        self.app_data.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            self.app_data
            / FIRST_RUN_STATE_FILENAME
        ).write_text(
            json.dumps(
                {
                    "schema_version": 999,
                    "state": "complete",
                    "welcome_version": 1,
                }
            ),
            encoding="utf-8",
        )

        decision = (
            self.manager()
            .evaluate()
        )

        self.assertTrue(
            decision.show_welcome
        )

        invalid_files = list(
            self.app_data.glob(
                f"{INVALID_STATE_PREFIX}*.json"
            )
        )

        self.assertEqual(
            len(
                invalid_files
            ),
            1,
        )

    def test_first_run_artifacts_do_not_fake_existing_install(
        self,
    ):
        self.app_data.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            self.app_data
            / (
                f"{INVALID_STATE_PREFIX}"
                "old.json"
            )
        ).write_text(
            "{}",
            encoding="utf-8",
        )

        (
            self.app_data
            / FIRST_RUN_TEMP_FILENAME
        ).write_text(
            "",
            encoding="utf-8",
        )

        decision = (
            self.manager()
            .evaluate()
        )

        self.assertTrue(
            decision.show_welcome
        )

        self.assertEqual(
            decision.reason,
            "fresh_install",
        )

    def test_default_path_uses_localappdata(
        self,
    ):
        local_root = (
            self.root
            / "LocalAppData"
        )

        with patch.dict(
            os.environ,
            {
                "LOCALAPPDATA": str(
                    local_root
                )
            },
            clear=False,
        ):
            store = (
                FirstRunStateStore()
            )

        self.assertEqual(
            store.app_data_directory,
            (
                local_root
                / "0337am Presence"
            ),
        )

        self.assertEqual(
            store.file_path,
            (
                local_root
                / "0337am Presence"
                / FIRST_RUN_STATE_FILENAME
            ),
        )

    def test_save_is_atomic_and_leaves_no_temp_file(
        self,
    ):
        store = FirstRunStateStore(
            app_data_directory=(
                self.app_data
            )
        )

        store.save(
            FirstRunState(
                state=(
                    WELCOME_STATE_PENDING
                ),
                welcome_version=0,
            )
        )

        self.assertTrue(
            store.file_path.exists()
        )

        self.assertFalse(
            store.temp_path.exists()
        )

    def test_existing_user_data_is_not_modified(
        self,
    ):
        self.app_data.mkdir(
            parents=True,
            exist_ok=True,
        )

        existing_file = (
            self.app_data
            / "dashboard_layout.json"
        )

        original = (
            '{"layout":"existing"}'
        )

        existing_file.write_text(
            original,
            encoding="utf-8",
        )

        decision = (
            self.manager()
            .evaluate()
        )

        self.assertFalse(
            decision.show_welcome
        )

        self.assertEqual(
            existing_file.read_text(
                encoding="utf-8"
            ),
            original,
        )

    def test_first_run_module_has_no_qsettings_dependency(
        self,
    ):
        source_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "system"
            / "first_run.py"
        )

        source = source_path.read_text(
            encoding="utf-8-sig"
        )

        self.assertNotIn(
            "QSettings",
            source,
        )

        self.assertNotIn(
            "PyQt6",
            source,
        )


if __name__ == "__main__":
    unittest.main()
