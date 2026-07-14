from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PyQt6.QtGui import (
    QColor,
    QImage,
)

from src.system.settings_backup import (
    SettingsBackupManager,
    SettingsBackupValidationError,
)
from src.ui.custom_cards import (
    LAUNCHER_TARGET_FOLDER,
    SCHEMA_VERSION,
    CustomCardStore,
    create_launcher_card,
    normalize_launcher_image_asset,
)
from src.ui.launcher_card_images import (
    cached_launcher_card_image_path,
    import_launcher_card_image,
    launcher_card_image_file,
    prune_launcher_card_images,
)


class LauncherCardImageTests(
    unittest.TestCase
):
    @staticmethod
    def _create_image(
        path: Path,
        *,
        width: int = 96,
        height: int = 64,
    ):
        image = QImage(
            width,
            height,
            QImage.Format.Format_ARGB32,
        )
        image.fill(
            QColor("#a970ff")
        )

        saved = image.save(
            str(path)
        )

        if not saved:
            raise RuntimeError(
                "Test image could not be created."
            )

    def test_import_normalises_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            managed = root / "managed"

            self._create_image(source)

            first = import_launcher_card_image(
                source,
                managed,
            )
            second = import_launcher_card_image(
                source,
                managed,
            )

            self.assertEqual(
                first,
                second,
            )
            self.assertEqual(
                len(first),
                64,
            )
            self.assertEqual(
                normalize_launcher_image_asset(
                    first.upper()
                ),
                first,
            )

            cached = (
                cached_launcher_card_image_path(
                    first,
                    managed,
                )
            )

            self.assertIsNotNone(cached)
            self.assertTrue(
                cached.is_file()
            )
            self.assertEqual(
                cached.suffix,
                ".png",
            )

    def test_large_image_is_scaled(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "large.png"
            managed = root / "managed"

            self._create_image(
                source,
                width=900,
                height=700,
            )

            asset = import_launcher_card_image(
                source,
                managed,
            )

            path = launcher_card_image_file(
                asset,
                managed,
            )

            image = QImage(
                str(path)
            )

            self.assertFalse(
                image.isNull()
            )
            self.assertLessEqual(
                image.width(),
                512,
            )
            self.assertLessEqual(
                image.height(),
                512,
            )

    def test_corrupt_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "broken.png"
            source.write_bytes(
                b"not an image"
            )

            with self.assertRaises(
                ValueError
            ):
                import_launcher_card_image(
                    source,
                    root / "managed",
                )

    def test_unsupported_extension_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "image.bmp"

            self._create_image(source)

            with self.assertRaises(
                ValueError
            ):
                import_launcher_card_image(
                    source,
                    root / "managed",
                )

    def test_prune_removes_only_unreferenced_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            managed = root / "managed"

            first_source = root / "first.png"
            second_source = root / "second.png"

            self._create_image(
                first_source,
                width=80,
                height=80,
            )
            self._create_image(
                second_source,
                width=81,
                height=80,
            )

            first = import_launcher_card_image(
                first_source,
                managed,
            )
            second = import_launcher_card_image(
                second_source,
                managed,
            )

            removed = prune_launcher_card_images(
                {first},
                managed,
            )

            self.assertEqual(
                len(removed),
                1,
            )
            self.assertIsNotNone(
                cached_launcher_card_image_path(
                    first,
                    managed,
                )
            )
            self.assertIsNone(
                cached_launcher_card_image_path(
                    second,
                    managed,
                )
            )

    def test_launcher_model_round_trip(self):
        asset = "a" * 64

        card = create_launcher_card(
            target=str(
                Path.cwd()
            ),
            target_kind=(
                LAUNCHER_TARGET_FOLDER
            ),
            title="Images",
            image_asset=asset,
        )

        restored = type(card).from_dict(
            card.to_dict()
        )

        self.assertEqual(
            restored.image_asset,
            asset,
        )

    def test_schema_two_storage_remains_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "custom_cards.json"

            card = create_launcher_card(
                target=str(root),
                target_kind=(
                    LAUNCHER_TARGET_FOLDER
                ),
                title="Legacy launcher",
            )

            payload = card.to_dict()
            payload.pop(
                "image_asset",
                None,
            )

            path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "cards": [payload],
                    }
                ),
                encoding="utf-8",
            )

            loaded = CustomCardStore(
                path
            ).load()

            self.assertEqual(
                len(loaded),
                1,
            )
            self.assertEqual(
                loaded[0].image_asset,
                "",
            )
            self.assertEqual(
                SCHEMA_VERSION,
                3,
            )

    def test_backup_capture_blanks_local_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = CustomCardStore(
                root / "custom_cards.json"
            )

            card = create_launcher_card(
                target=str(root),
                target_kind=(
                    LAUNCHER_TARGET_FOLDER
                ),
                title="Private launcher",
                image_asset=(
                    "b" * 64
                ),
            )

            store.save((card,))

            manager = object.__new__(
                SettingsBackupManager
            )
            manager.custom_card_store = store

            payload = (
                manager._capture_custom_cards()
            )
            portable = payload["cards"][0]

            self.assertEqual(
                portable["target"],
                "",
            )
            self.assertEqual(
                portable["image_asset"],
                "",
            )

    def test_backup_validation_rejects_image_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            card = create_launcher_card(
                target=str(root),
                target_kind=(
                    LAUNCHER_TARGET_FOLDER
                ),
                title="Private launcher",
                image_asset=(
                    "c" * 64
                ),
            )

            payload = card.to_dict()
            payload["target"] = ""

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
                            "cards": [payload],
                        }
                    )
                )

    def test_invalid_asset_identifier_is_rejected(self):
        for value in [
            "../private.png",
            "not-a-hash",
            "g" * 64,
            "a" * 63,
        ]:
            with self.subTest(value=value):
                with self.assertRaises(
                    ValueError
                ):
                    normalize_launcher_image_asset(
                        value
                    )

    def test_dashboard_wires_image_cleanup(self):
        dashboard_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "ui"
            / "dashboard.py"
        )

        source = dashboard_path.read_text(
            encoding="utf-8",
        )

        self.assertIn(
            "def prune_unused_launcher_card_images",
            source,
        )
        self.assertIn(
            "prune_launcher_card_images(",
            source,
        )
        self.assertGreaterEqual(
            source.count(
                "self.prune_unused_launcher_card_images("
            ),
            8,
        )
        self.assertIn(
            "previous_cards",
            source,
        )



if __name__ == "__main__":
    unittest.main()
