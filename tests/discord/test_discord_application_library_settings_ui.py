from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
)

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY_ID,
    DiscordApplicationLibraryStore,
)
from src.ui.discord_application_library_card import (
    DiscordApplicationEditorDialog,
    DiscordApplicationLibrarySettingsCard,
)


APPLICATION_ID_A = (
    "1096663809097203752"
)

APPLICATION_ID_B = (
    "123456789012345678"
)


class DiscordApplicationEditorDialogTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_add_dialog_has_expected_fields_and_copy(
        self,
    ):
        dialog = (
            DiscordApplicationEditorDialog()
        )

        self.addCleanup(
            dialog.deleteLater
        )

        self.assertEqual(
            dialog.windowTitle(),
            "Add Discord application",
        )

        self.assertEqual(
            dialog.save_button.text(),
            "Add application",
        )

        self.assertIn(
            "Sword Art Online",
            dialog.name_edit.placeholderText(),
        )

        self.assertIn(
            "123456789012345678",
            (
                dialog.application_id_edit
                .placeholderText()
            ),
        )

    def test_edit_dialog_prepopulates_entry(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            store = (
                DiscordApplicationLibraryStore(
                    Path(temp)
                    / "applications.json"
                )
            )

            entry = store.create(
                name="Sword Art Online",
                application_id=(
                    APPLICATION_ID_A
                ),
            )

            dialog = (
                DiscordApplicationEditorDialog(
                    entry=entry
                )
            )

            self.addCleanup(
                dialog.deleteLater
            )

            self.assertEqual(
                dialog.windowTitle(),
                "Edit Discord application",
            )

            self.assertEqual(
                dialog.save_button.text(),
                "Save changes",
            )

            self.assertEqual(
                dialog.name_edit.text(),
                "Sword Art Online",
            )

            self.assertEqual(
                dialog.application_id_edit.text(),
                APPLICATION_ID_A,
            )

    def test_validated_values_accept_public_id(
        self,
    ):
        dialog = (
            DiscordApplicationEditorDialog()
        )

        self.addCleanup(
            dialog.deleteLater
        )

        dialog.name_edit.setText(
            "Sword Art Online"
        )

        dialog.application_id_edit.setText(
            APPLICATION_ID_A
        )

        self.assertEqual(
            dialog.validated_values(),
            (
                "Sword Art Online",
                APPLICATION_ID_A,
            ),
        )

    def test_validated_values_reject_invalid_id(
        self,
    ):
        dialog = (
            DiscordApplicationEditorDialog()
        )

        self.addCleanup(
            dialog.deleteLater
        )

        dialog.name_edit.setText(
            "Sword Art Online"
        )

        dialog.application_id_edit.setText(
            "not-an-id"
        )

        with self.assertRaises(
            ValueError
        ):
            dialog.validated_values()

    def test_validated_values_reject_empty_name(
        self,
    ):
        dialog = (
            DiscordApplicationEditorDialog()
        )

        self.addCleanup(
            dialog.deleteLater
        )

        dialog.application_id_edit.setText(
            APPLICATION_ID_A
        )

        with self.assertRaises(
            ValueError
        ):
            dialog.validated_values()


class DiscordApplicationLibrarySettingsCardTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def setUp(self):
        self.temporary = (
            tempfile.TemporaryDirectory()
        )

        self.store = (
            DiscordApplicationLibraryStore(
                Path(
                    self.temporary.name
                )
                / "applications.json"
            )
        )

        self.card = (
            DiscordApplicationLibrarySettingsCard(
                application_store=(
                    self.store
                )
            )
        )

        self.messages = []
        self.change_count = 0

        self.card.message_changed.connect(
            self.messages.append
        )

        self.card.entries_changed.connect(
            self._record_change
        )

        self.app.processEvents()

    def tearDown(self):
        self.card.close()
        self.card.deleteLater()

        self.app.processEvents()

        self.temporary.cleanup()

    def _record_change(self):
        self.change_count += 1

    def test_card_initially_shows_builtin_only(
        self,
    ):
        self.assertEqual(
            set(
                self.card.entry_rows
            ),
            {
                BUILTIN_APPLICATION_ENTRY_ID
            },
        )

        row = (
            self.card.entry_rows[
                BUILTIN_APPLICATION_ENTRY_ID
            ]
        )

        self.assertEqual(
            row.name_label.text(),
            "03:37am Music",
        )

    def test_builtin_row_is_protected(
        self,
    ):
        row = (
            self.card.entry_rows[
                BUILTIN_APPLICATION_ENTRY_ID
            ]
        )

        self.assertIsNotNone(
            row.builtin_label
        )

        self.assertIsNone(
            row.edit_button
        )

        self.assertIsNone(
            row.delete_button
        )

    def test_create_entry_refreshes_and_emits(
        self,
    ):
        entry = self.card.create_entry(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        self.assertIsNotNone(
            entry
        )

        self.assertIn(
            entry.entry_id,
            self.card.entry_rows,
        )

        self.assertEqual(
            self.change_count,
            1,
        )

        self.assertIn(
            "added",
            self.messages[-1],
        )

    def test_duplicate_create_fails_without_corrupting_rows(
        self,
    ):
        first = self.card.create_entry(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        before = set(
            self.card.entry_rows
        )

        duplicate = (
            self.card.create_entry(
                name="Another name",
                application_id=(
                    APPLICATION_ID_A
                ),
            )
        )

        self.assertIsNone(
            duplicate
        )

        self.assertEqual(
            set(
                self.card.entry_rows
            ),
            before,
        )

        self.assertIn(
            first.entry_id,
            self.card.entry_rows,
        )

        self.assertEqual(
            self.change_count,
            1,
        )

    def test_update_entry_preserves_stable_id(
        self,
    ):
        entry = self.card.create_entry(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        updated = self.card.update_entry(
            entry.entry_id,
            name="SAO",
            application_id=(
                APPLICATION_ID_B
            ),
        )

        self.assertIsNotNone(
            updated
        )

        self.assertEqual(
            updated.entry_id,
            entry.entry_id,
        )

        self.assertEqual(
            updated.name,
            "SAO",
        )

        row = (
            self.card.entry_rows[
                entry.entry_id
            ]
        )

        self.assertEqual(
            row.name_label.text(),
            "SAO",
        )

        self.assertEqual(
            row.application_id_label.text(),
            APPLICATION_ID_B,
        )

        self.assertEqual(
            self.change_count,
            2,
        )

    def test_delete_user_entry_refreshes_and_emits(
        self,
    ):
        entry = self.card.create_entry(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        result = self.card.delete_entry(
            entry.entry_id
        )

        self.assertTrue(
            result
        )

        self.assertNotIn(
            entry.entry_id,
            self.card.entry_rows,
        )

        self.assertEqual(
            self.change_count,
            2,
        )

    def test_delete_builtin_is_rejected(
        self,
    ):
        result = self.card.delete_entry(
            BUILTIN_APPLICATION_ENTRY_ID
        )

        self.assertFalse(
            result
        )

        self.assertIn(
            BUILTIN_APPLICATION_ENTRY_ID,
            self.card.entry_rows,
        )

        self.assertEqual(
            self.change_count,
            0,
        )

        self.assertIn(
            "cannot be deleted",
            self.messages[-1],
        )

    def test_refresh_reflects_external_store_change(
        self,
    ):
        entry = self.store.create(
            name="Sword Art Online",
            application_id=(
                APPLICATION_ID_A
            ),
        )

        self.assertNotIn(
            entry.entry_id,
            self.card.entry_rows,
        )

        self.card.refresh_from_store()

        self.assertIn(
            entry.entry_id,
            self.card.entry_rows,
        )

    def test_warning_rejects_secret_credentials(
        self,
    ):
        text = " ".join(
            label.text()
            for label
            in self.card.findChildren(
                QLabel
            )
        ).lower()

        self.assertIn(
            "client secret",
            text,
        )

        self.assertIn(
            "bot token",
            text,
        )

        self.assertIn(
            "user token",
            text,
        )

    def test_ui_source_owns_no_rpc_or_network_runtime(
        self,
    ):
        source = inspect.getsource(
            __import__(
                (
                    "src.ui."
                    "discord_application_library_card"
                ),
                fromlist=["*"],
            )
        ).lower()

        forbidden = (
            "pypresence",
            "extendeddiscordpresence",
            "request_client_id",
            "urllib",
            "requests.",
            "aiohttp",
            "socket.",
            "client_secret",
            "bot_token",
            "user_token",
        )

        for token in forbidden:
            self.assertNotIn(
                token,
                source,
            )


if __name__ == "__main__":
    unittest.main()
