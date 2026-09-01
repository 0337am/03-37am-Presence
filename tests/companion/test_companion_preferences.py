import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from src.companion.preferences import (
    MAX_PREFERENCES_FILE_BYTES,
    CompanionPreferences,
    CompanionPreferencesStore,
    companion_preferences_from_payload,
    companion_preferences_to_payload,
    default_companion_preferences,
    default_companion_preferences_path,
)


class CompanionPreferencesTests(unittest.TestCase):
    def test_defaults_are_safe_and_disabled(self):
        prefs = default_companion_preferences()

        self.assertFalse(prefs.enabled)
        self.assertEqual(prefs.asset_path, "")
        self.assertEqual(prefs.scale_percent, 100)
        self.assertEqual(prefs.opacity, 1.0)
        self.assertTrue(prefs.always_on_top)
        self.assertTrue(prefs.click_through)
        self.assertTrue(prefs.remember_position)
        self.assertIsNone(prefs.position_x)
        self.assertIsNone(prefs.position_y)
        self.assertEqual(prefs.screen_name, "")
        self.assertFalse(prefs.hide_in_fullscreen)
        self.assertEqual(
            prefs.animation_speed_percent,
            100,
        )

    def test_default_path_uses_localappdata(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.dict(
                os.environ,
                {"LOCALAPPDATA": root},
                clear=False,
            ):
                path = (
                    default_companion_preferences_path()
                )

        self.assertEqual(
            path,
            (
                Path(root)
                / "0337am Presence"
                / "companion_preferences.json"
            ),
        )

    def test_payload_round_trip(self):
        expected = CompanionPreferences(
            enabled=True,
            asset_path=r"C:\Companion\friend.gif",
            scale_percent=135,
            opacity=0.75,
            always_on_top=False,
            click_through=False,
            remember_position=True,
            position_x=-420,
            position_y=780,
            screen_name=r"\\.\DISPLAY2",
            hide_in_fullscreen=True,
            animation_speed_percent=125,
        )

        payload = companion_preferences_to_payload(
            expected
        )

        self.assertEqual(
            companion_preferences_from_payload(
                payload
            ),
            expected,
        )

    def test_supported_asset_formats(self):
        for suffix in (
            ".PNG",
            ".JPG",
            ".JPEG",
            ".WEBP",
            ".GIF",
        ):
            with self.subTest(suffix=suffix):
                path = (
                    r"C:\Companion\asset"
                    + suffix
                )

                payload = (
                    companion_preferences_to_payload(
                        CompanionPreferences(
                            asset_path=path
                        )
                    )
                )

                restored = (
                    companion_preferences_from_payload(
                        payload
                    )
                )

                self.assertEqual(
                    restored.asset_path,
                    path,
                )

    def test_unsupported_asset_format_rejected(self):
        with self.assertRaises(ValueError):
            companion_preferences_to_payload(
                CompanionPreferences(
                    asset_path=(
                        r"C:\Companion\asset.exe"
                    )
                )
            )

    def test_numeric_bounds_are_validated(self):
        cases = (
            ("scale_percent", 24),
            ("scale_percent", 401),
            ("opacity", 0.09),
            ("opacity", 1.01),
            ("animation_speed_percent", 24),
            ("animation_speed_percent", 401),
        )

        for field_name, value in cases:
            with self.subTest(
                field_name=field_name,
                value=value,
            ):
                invalid = replace(
                    default_companion_preferences(),
                    **{field_name: value},
                )

                with self.assertRaises(ValueError):
                    companion_preferences_to_payload(
                        invalid
                    )

    def test_boolean_is_not_integer_setting(self):
        for field_name in (
            "scale_percent",
            "animation_speed_percent",
        ):
            with self.subTest(
                field_name=field_name
            ):
                invalid = replace(
                    default_companion_preferences(),
                    **{field_name: True},
                )

                with self.assertRaises(ValueError):
                    companion_preferences_to_payload(
                        invalid
                    )

    def test_position_coordinates_are_paired(self):
        with self.assertRaises(ValueError):
            companion_preferences_to_payload(
                CompanionPreferences(
                    position_x=10,
                    position_y=None,
                )
            )

        with self.assertRaises(ValueError):
            companion_preferences_to_payload(
                CompanionPreferences(
                    position_x=None,
                    position_y=10,
                )
            )

    def test_missing_store_returns_defaults(self):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(root)
                / "companion_preferences.json"
            )

            store = CompanionPreferencesStore(
                path
            )

            self.assertEqual(
                store.load(),
                default_companion_preferences(),
            )

            self.assertFalse(path.exists())

    def test_store_round_trip_is_atomic(self):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(root)
                / "nested"
                / "companion_preferences.json"
            )

            store = CompanionPreferencesStore(
                path
            )

            expected = CompanionPreferences(
                enabled=True,
                asset_path=r"C:\Companion\friend.webp",
                scale_percent=120,
                opacity=0.8,
                position_x=100,
                position_y=200,
                animation_speed_percent=110,
            )

            self.assertEqual(
                store.save(expected),
                expected,
            )

            self.assertEqual(
                store.load(),
                expected,
            )

            temp_files = list(
                path.parent.glob(
                    ".companion_preferences.json.*.tmp"
                )
            )

            self.assertEqual(
                temp_files,
                [],
            )

            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                payload["schema_version"],
                1,
            )

    def test_corrupt_and_oversized_store_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(root)
                / "companion_preferences.json"
            )

            store = CompanionPreferencesStore(
                path
            )

            path.write_text(
                "{broken",
                encoding="utf-8",
            )

            self.assertEqual(
                store.load(),
                default_companion_preferences(),
            )

            path.write_bytes(
                b"x"
                * (
                    MAX_PREFERENCES_FILE_BYTES
                    + 1
                )
            )

            self.assertEqual(
                store.load(),
                default_companion_preferences(),
            )

    def test_update_validates_and_persists(self):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(root)
                / "companion_preferences.json"
            )

            store = CompanionPreferencesStore(
                path
            )

            updated = store.update(
                enabled=True,
                asset_path=r"C:\Companion\friend.gif",
                opacity=0.65,
                animation_speed_percent=125,
            )

            self.assertEqual(
                store.load(),
                updated,
            )

            invalid = replace(
                updated,
                scale_percent=999,
            )

            with self.assertRaises(ValueError):
                store.save(invalid)

            self.assertEqual(
                store.load(),
                updated,
            )


if __name__ == "__main__":
    unittest.main()