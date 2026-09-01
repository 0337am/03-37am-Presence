from __future__ import annotations

import ast
import json
import os
import tempfile
import unittest

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from src.system.quick_access_preferences import (
    DEFAULT_QUICK_ACCESS_ITEMS,
    MAX_ITEMS,
    MAX_PREFERENCES_BYTES,
    PREFERENCES_FILENAME,
    SCHEMA_VERSION,
    QuickAccessItem,
    QuickAccessPreferences,
    QuickAccessPreferencesStore,
    default_quick_access_preferences,
    quick_access_preferences_from_payload,
    quick_access_preferences_to_payload,
)


class QuickAccessPreferencesTests(
    unittest.TestCase
):
    def test_defaults_match_existing_dashboard_actions(
        self,
    ):
        preferences = (
            default_quick_access_preferences()
        )

        values = [
            (
                item.item_id,
                item.kind,
                item.target,
                item.title,
                item.detail,
                item.icon_key,
                item.visible,
            )
            for item in preferences.items
        ]

        self.assertEqual(
            values,
            [
                (
                    "builtin.afk",
                    "builtin",
                    "afk",
                    "AFK",
                    "Set AFK presence",
                    "afk",
                    True,
                ),
                (
                    "builtin.custom",
                    "builtin",
                    "custom",
                    "Custom",
                    "Create a presence",
                    "custom",
                    True,
                ),
                (
                    "builtin.presets",
                    "builtin",
                    "presets",
                    "Presets",
                    "Manage presence modes",
                    "presets",
                    True,
                ),
                (
                    "builtin.settings",
                    "builtin",
                    "settings",
                    "Settings",
                    "Configure application",
                    "settings",
                    True,
                ),
            ],
        )

        self.assertEqual(
            preferences.items,
            DEFAULT_QUICK_ACCESS_ITEMS,
        )

    def test_item_normalizes_safe_fields(
        self,
    ):
        item = QuickAccessItem(
            item_id="  Builtin.AFK  ",
            kind="  BUILTIN ",
            target=" AFK ",
            title="  AFK  ",
            detail=" Set AFK presence ",
            icon_key=" AFK ",
        )

        self.assertEqual(
            item.item_id,
            "builtin.afk",
        )

        self.assertEqual(
            item.kind,
            "builtin",
        )

        self.assertEqual(
            item.target,
            "afk",
        )

        self.assertEqual(
            item.title,
            "AFK",
        )

        self.assertEqual(
            item.detail,
            "Set AFK presence",
        )

        self.assertEqual(
            item.icon_key,
            "afk",
        )

    def test_unknown_kind_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id="example.item",
                kind="launcher",
                target="settings",
                title="Example",
                detail="",
                icon_key="settings",
            )

    def test_unknown_builtin_target_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id="builtin.unknown",
                kind="builtin",
                target="unknown",
                title="Unknown",
                detail="",
                icon_key="settings",
            )

    def test_visibility_requires_boolean(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            QuickAccessItem(
                item_id="builtin.afk",
                kind="builtin",
                target="afk",
                title="AFK",
                detail="",
                icon_key="afk",
                visible=1,
            )

    def test_duplicate_item_ids_are_rejected(
        self,
    ):
        item = (
            DEFAULT_QUICK_ACCESS_ITEMS[
                0
            ]
        )

        with self.assertRaises(
            ValueError
        ):
            QuickAccessPreferences(
                items=(
                    item,
                    item,
                )
            )

    def test_item_limit_is_enforced(
        self,
    ):
        items = tuple(
            QuickAccessItem(
                item_id=f"builtin.item-{index}",
                kind="builtin",
                target="afk",
                title=f"Item {index}",
                detail="",
                icon_key="afk",
            )
            for index in range(
                MAX_ITEMS + 1
            )
        )

        with self.assertRaises(
            ValueError
        ):
            QuickAccessPreferences(
                items=items
            )

    def test_payload_round_trip_preserves_order(
        self,
    ):
        original = QuickAccessPreferences(
            items=(
                replace(
                    DEFAULT_QUICK_ACCESS_ITEMS[
                        3
                    ],
                    visible=False,
                ),
                DEFAULT_QUICK_ACCESS_ITEMS[
                    0
                ],
            )
        )

        payload = (
            quick_access_preferences_to_payload(
                original
            )
        )

        self.assertEqual(
            payload[
                "schema_version"
            ],
            SCHEMA_VERSION,
        )

        restored = (
            quick_access_preferences_from_payload(
                payload
            )
        )

        self.assertEqual(
            restored,
            original,
        )

    def test_empty_preferences_round_trip(
        self,
    ):
        original = QuickAccessPreferences(
            items=()
        )

        payload = (
            quick_access_preferences_to_payload(
                original
            )
        )

        restored = (
            quick_access_preferences_from_payload(
                payload
            )
        )

        self.assertEqual(
            restored.items,
            (),
        )

    def test_payload_rejects_wrong_schema(
        self,
    ):
        payload = (
            quick_access_preferences_to_payload(
                default_quick_access_preferences()
            )
        )

        payload[
            "schema_version"
        ] = SCHEMA_VERSION + 1

        with self.assertRaises(
            ValueError
        ):
            quick_access_preferences_from_payload(
                payload
            )

    def test_payload_requires_items_list(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            quick_access_preferences_from_payload(
                {
                    "schema_version": (
                        SCHEMA_VERSION
                    ),
                    "items": (),
                }
            )

    def test_payload_requires_boolean_visibility(
        self,
    ):
        payload = (
            quick_access_preferences_to_payload(
                default_quick_access_preferences()
            )
        )

        payload[
            "items"
        ][0][
            "visible"
        ] = 1

        with self.assertRaises(
            ValueError
        ):
            quick_access_preferences_from_payload(
                payload
            )

    def test_store_uses_expected_localappdata_path(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            )

            with patch.dict(
                os.environ,
                {
                    "LOCALAPPDATA": str(
                        root
                    )
                },
                clear=False,
            ):
                path = (
                    QuickAccessPreferencesStore
                    .default_path()
                )

            self.assertEqual(
                path,
                (
                    root
                    / "0337am Presence"
                    / PREFERENCES_FILENAME
                ),
            )

    def test_store_creates_default_file(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / PREFERENCES_FILENAME
            )

            store = (
                QuickAccessPreferencesStore(
                    path
                )
            )

            self.assertTrue(
                path.is_file()
            )

            self.assertEqual(
                store.load(),
                default_quick_access_preferences(),
            )

            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                payload[
                    "schema_version"
                ],
                SCHEMA_VERSION,
            )

    def test_save_and_load_preserves_order_and_visibility(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / PREFERENCES_FILENAME
            )

            store = (
                QuickAccessPreferencesStore(
                    path
                )
            )

            expected = QuickAccessPreferences(
                items=(
                    replace(
                        DEFAULT_QUICK_ACCESS_ITEMS[
                            2
                        ],
                        visible=False,
                    ),
                    DEFAULT_QUICK_ACCESS_ITEMS[
                        0
                    ],
                )
            )

            store.save(
                expected
            )

            self.assertEqual(
                store.load(),
                expected,
            )

    def test_reset_restores_defaults(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / PREFERENCES_FILENAME
            )

            store = (
                QuickAccessPreferencesStore(
                    path
                )
            )

            store.save(
                QuickAccessPreferences(
                    items=()
                )
            )

            restored = store.reset()

            self.assertEqual(
                restored,
                default_quick_access_preferences(),
            )

            self.assertEqual(
                store.load(),
                default_quick_access_preferences(),
            )

    def test_invalid_json_is_quarantined_and_replaced(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            )

            path = (
                root
                / PREFERENCES_FILENAME
            )

            path.write_text(
                "{not-json",
                encoding="utf-8",
            )

            store = (
                QuickAccessPreferencesStore(
                    path
                )
            )

            restored = store.load()

            self.assertEqual(
                restored,
                default_quick_access_preferences(),
            )

            quarantined = list(
                root.glob(
                    PREFERENCES_FILENAME
                    + ".invalid_*"
                )
            )

            self.assertEqual(
                len(quarantined),
                1,
            )

            self.assertTrue(
                path.is_file()
            )

    def test_invalid_schema_is_quarantined_and_replaced(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            )

            path = (
                root
                / PREFERENCES_FILENAME
            )

            path.write_text(
                json.dumps(
                    {
                        "schema_version": 999,
                        "items": [],
                    }
                ),
                encoding="utf-8",
            )

            store = (
                QuickAccessPreferencesStore(
                    path
                )
            )

            restored = store.load()

            self.assertEqual(
                restored,
                default_quick_access_preferences(),
            )

            quarantined = list(
                root.glob(
                    PREFERENCES_FILENAME
                    + ".invalid_*"
                )
            )

            self.assertEqual(
                len(quarantined),
                1,
            )

    def test_oversized_file_is_quarantined(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            )

            path = (
                root
                / PREFERENCES_FILENAME
            )

            path.write_bytes(
                b"x"
                * (
                    MAX_PREFERENCES_BYTES
                    + 1
                )
            )

            store = (
                QuickAccessPreferencesStore(
                    path
                )
            )

            restored = store.load()

            self.assertEqual(
                restored,
                default_quick_access_preferences(),
            )

            quarantined = list(
                root.glob(
                    PREFERENCES_FILENAME
                    + ".invalid_*"
                )
            )

            self.assertEqual(
                len(quarantined),
                1,
            )

    def test_save_leaves_no_temporary_file(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            path = (
                Path(temporary)
                / PREFERENCES_FILENAME
            )

            store = (
                QuickAccessPreferencesStore(
                    path
                )
            )

            store.save(
                default_quick_access_preferences()
            )

            temporary_path = (
                path.with_name(
                    path.name + ".tmp"
                )
            )

            self.assertFalse(
                temporary_path.exists()
            )

    def test_wrong_save_type_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            store = (
                QuickAccessPreferencesStore(
                    Path(temporary)
                    / PREFERENCES_FILENAME
                )
            )

            with self.assertRaises(
                TypeError
            ):
                store.save(
                    object()
                )

    def test_module_has_no_qt_spotify_network_or_launcher_dependency(
        self,
    ):
        module_path = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "system"
            / "quick_access_preferences.py"
        )

        tree = ast.parse(
            module_path.read_text(
                encoding="utf-8-sig"
            )
        )

        imports = set()

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                for alias in node.names:
                    imports.add(
                        alias.name
                    )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                imports.add(
                    node.module or ""
                )

        forbidden_prefixes = (
            "PyQt6",
            "src.spotify",
            "src.system.launcher_open",
            "requests",
            "urllib",
            "socket",
            "subprocess",
        )

        for imported in imports:
            for prefix in forbidden_prefixes:
                self.assertFalse(
                    imported.startswith(
                        prefix
                    ),
                    imported,
                )

    def test_optional_builtin_targets_are_supported(
        self,
    ):
        for target in (
            "presence",
            "library",
            "spotify",
            "about",
            "companion",
        ):
            with self.subTest(
                target=target
            ):
                item = QuickAccessItem(
                    item_id=(
                        "builtin."
                        + target
                    ),
                    kind="builtin",
                    target=target,
                    title=target.title(),
                    detail=(
                        "Open "
                        + target.title()
                    ),
                    icon_key=target,
                )

                self.assertEqual(
                    item.target,
                    target,
                )

    def test_optional_builtin_items_round_trip(
        self,
    ):
        original = QuickAccessPreferences(
            items=tuple(
                QuickAccessItem(
                    item_id=(
                        "builtin."
                        + target
                    ),
                    kind="builtin",
                    target=target,
                    title=target.title(),
                    detail=(
                        "Open "
                        + target.title()
                    ),
                    icon_key=target,
                )
                for target in (
                    "presence",
                    "library",
                    "spotify",
                    "about",
                )
            )
        )

        payload = (
            quick_access_preferences_to_payload(
                original
            )
        )

        restored = (
            quick_access_preferences_from_payload(
                payload
            )
        )

        self.assertEqual(
            restored,
            original,
        )


if __name__ == "__main__":
    unittest.main()
