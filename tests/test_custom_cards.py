from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.system.settings_backup import (
    SettingsBackupManager,
    SettingsBackupValidationError,
)
from src.ui.custom_cards import (
    LAUNCHER_TARGET_APPLICATION,
    LAUNCHER_TARGET_FILE,
    LAUNCHER_TARGET_FOLDER,
    SCHEMA_VERSION,
    CustomCardStore,
    LauncherCardData,
    create_launcher_card,
    create_link_card,
    custom_card_from_dict,
    validate_custom_cards,
)


class _CardStoreStub:
    def __init__(self, cards):
        self._cards = tuple(cards)

    def load(self):
        return self._cards


class CustomCardModelTests(unittest.TestCase):
    def test_link_card_round_trip_is_unchanged(self):
        card = create_link_card(
            url="https://example.com/path",
            title="Example",
            icon="??",
            description="Example site",
        )

        restored = custom_card_from_dict(
            card.to_dict()
        )

        self.assertEqual(restored, card)
        self.assertEqual(restored.card_type, "link")

    def test_launcher_card_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "Example.exe"
            target.write_bytes(b"example")

            card = create_launcher_card(
                target=str(target),
                target_kind=(
                    LAUNCHER_TARGET_APPLICATION
                ),
                title="Example App",
                icon="??",
                description="Open Example",
            )

            restored = custom_card_from_dict(
                card.to_dict()
            )

            self.assertIsInstance(
                restored,
                LauncherCardData,
            )
            self.assertEqual(restored, card)
            self.assertTrue(restored.is_configured)
            self.assertTrue(restored.target_exists)
            self.assertEqual(
                restored.display_target,
                target.name,
            )

    def test_launcher_card_requires_absolute_target(self):
        with self.assertRaises(ValueError):
            create_launcher_card(
                target="relative-file.txt",
                target_kind=LAUNCHER_TARGET_FILE,
            )

    def test_launcher_card_rejects_network_target(self):
        with self.assertRaises(ValueError):
            create_launcher_card(
                target=r"\\server\share\file.txt",
                target_kind=LAUNCHER_TARGET_FILE,
            )

    def test_launcher_card_rejects_unknown_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                create_launcher_card(
                    target=str(Path(directory)),
                    target_kind="command",
                )

    def test_disconnected_launcher_can_be_restored(self):
        payload = {
            "id": (
                "custom_launcher_"
                "0123456789abcdef0123456789abcdef"
            ),
            "type": "launcher",
            "title": "Restored Launcher",
            "target": "",
            "target_kind": (
                LAUNCHER_TARGET_FOLDER
            ),
            "icon": "??",
            "description": "",
            "button_label": "Open",
            "accent": "",
        }

        card = custom_card_from_dict(payload)

        self.assertIsInstance(
            card,
            LauncherCardData,
        )
        self.assertFalse(card.is_configured)
        self.assertFalse(card.target_exists)
        self.assertEqual(
            card.display_target,
            "Target not selected",
        )

    def test_mixed_card_collection_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            cards = (
                create_link_card(
                    url="https://example.com",
                ),
                create_launcher_card(
                    target=str(Path(directory)),
                    target_kind=(
                        LAUNCHER_TARGET_FOLDER
                    ),
                ),
            )

            validated = validate_custom_cards(
                cards
            )

            self.assertEqual(
                len(validated),
                2,
            )

    def test_schema_one_storage_remains_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            storage_path = (
                Path(directory)
                / "custom_cards.json"
            )
            link = create_link_card(
                url="https://example.com",
                title="Legacy Link",
            )

            storage_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "cards": [
                            link.to_dict()
                        ],
                    }
                ),
                encoding="utf-8",
            )

            store = CustomCardStore(storage_path)
            loaded = store.load()

            self.assertEqual(
                loaded,
                (link,),
            )

            store.save(loaded)

            saved_payload = json.loads(
                storage_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                saved_payload["schema_version"],
                SCHEMA_VERSION,
            )

    def test_mixed_storage_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            storage_path = (
                root
                / "custom_cards.json"
            )
            target = root / "notes.txt"
            target.write_text(
                "notes",
                encoding="utf-8",
            )

            cards = (
                create_link_card(
                    url="https://example.com",
                ),
                create_launcher_card(
                    target=str(target),
                    target_kind=LAUNCHER_TARGET_FILE,
                ),
            )

            store = CustomCardStore(storage_path)
            saved = store.save(cards)
            loaded = store.load()

            self.assertEqual(saved, loaded)
            self.assertEqual(
                json.loads(
                    storage_path.read_text(
                        encoding="utf-8"
                    )
                )["schema_version"],
                SCHEMA_VERSION,
            )

    def test_upsert_accepts_launcher_card(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = CustomCardStore(
                root / "custom_cards.json"
            )
            target = root / "tool.exe"
            target.write_bytes(b"tool")

            card = create_launcher_card(
                target=str(target),
                target_kind=(
                    LAUNCHER_TARGET_APPLICATION
                ),
            )

            saved = store.upsert(card)

            self.assertEqual(saved, (card,))
            self.assertEqual(
                store.load(),
                (card,),
            )


class CustomCardBackupTests(unittest.TestCase):
    def test_capture_blanks_launcher_target(self):
        with tempfile.TemporaryDirectory() as directory:
            launcher = create_launcher_card(
                target=str(Path(directory)),
                target_kind=(
                    LAUNCHER_TARGET_FOLDER
                ),
                title="Local Folder",
            )

            manager = object.__new__(
                SettingsBackupManager
            )
            manager.custom_card_store = (
                _CardStoreStub((launcher,))
            )

            payload = (
                manager._capture_custom_cards()
            )

            self.assertEqual(
                payload["schema_version"],
                SCHEMA_VERSION,
            )
            self.assertEqual(
                payload["cards"][0]["target"],
                "",
            )
            self.assertEqual(
                payload["cards"][0]["title"],
                "Local Folder",
            )

    def test_validation_accepts_schema_one_links(self):
        link = create_link_card(
            url="https://example.com",
        )

        validated = (
            SettingsBackupManager
            ._validate_custom_cards(
                {
                    "schema_version": 1,
                    "cards": [
                        link.to_dict()
                    ],
                }
            )
        )

        self.assertEqual(
            validated["schema_version"],
            SCHEMA_VERSION,
        )
        self.assertEqual(
            validated["cards"],
            [link.to_dict()],
        )

    def test_validation_accepts_sanitized_launcher(self):
        payload = {
            "id": (
                "custom_launcher_"
                "fedcba9876543210fedcba9876543210"
            ),
            "type": "launcher",
            "title": "Portable Launcher",
            "target": "",
            "target_kind": (
                LAUNCHER_TARGET_FOLDER
            ),
            "icon": "??",
            "description": "",
            "button_label": "Open",
            "accent": "",
        }

        validated = (
            SettingsBackupManager
            ._validate_custom_cards(
                {
                    "schema_version": (
                        SCHEMA_VERSION
                    ),
                    "cards": [payload],
                }
            )
        )

        self.assertEqual(
            validated["cards"][0]["target"],
            "",
        )

    def test_validation_rejects_launcher_path(self):
        with tempfile.TemporaryDirectory() as directory:
            launcher = create_launcher_card(
                target=str(Path(directory)),
                target_kind=(
                    LAUNCHER_TARGET_FOLDER
                ),
            )

            with self.assertRaises(
                SettingsBackupValidationError
            ):
                (
                    SettingsBackupManager
                    ._validate_custom_cards(
                        {
                            "schema_version": (
                                SCHEMA_VERSION
                            ),
                            "cards": [
                                launcher.to_dict()
                            ],
                        }
                    )
                )


if __name__ == "__main__":
    unittest.main()
