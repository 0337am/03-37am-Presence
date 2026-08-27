from __future__ import annotations

import inspect
import unittest

from src.system.quick_access_catalogue import (
    QuickAccessCatalogueEntry,
    addable_quick_access_catalogue,
    default_quick_access_catalogue,
    optional_quick_access_catalogue,
    quick_access_catalogue,
    quick_access_catalogue_entry,
    quick_access_catalogue_entry_for_target,
)
from src.system.quick_access_preferences import (
    DEFAULT_QUICK_ACCESS_ITEMS,
)


class QuickAccessCatalogueTests(
    unittest.TestCase
):
    def test_catalogue_has_expected_stable_order(
        self,
    ):
        self.assertEqual(
            [
                entry.item_id
                for entry in quick_access_catalogue()
            ],
            [
                "builtin.afk",
                "builtin.custom",
                "builtin.presets",
                "builtin.settings",
                "builtin.presence",
                "builtin.library",
                "builtin.spotify",
                "builtin.about",
            ],
        )

    def test_default_catalogue_preserves_accepted_four(
        self,
    ):
        self.assertEqual(
            [
                entry.item_id
                for entry in default_quick_access_catalogue()
            ],
            [
                "builtin.afk",
                "builtin.custom",
                "builtin.presets",
                "builtin.settings",
            ],
        )

    def test_optional_catalogue_contains_safe_internal_destinations(
        self,
    ):
        self.assertEqual(
            [
                entry.item_id
                for entry in optional_quick_access_catalogue()
            ],
            [
                "builtin.presence",
                "builtin.library",
                "builtin.spotify",
                "builtin.about",
            ],
        )

    def test_default_metadata_matches_existing_preferences(
        self,
    ):
        catalogue = default_quick_access_catalogue()

        actual = [
            (
                entry.item_id,
                entry.kind,
                entry.target,
                entry.title,
                entry.detail,
                entry.icon_key,
            )
            for entry in catalogue
        ]

        expected = [
            (
                item.item_id,
                item.kind,
                item.target,
                item.title,
                item.detail,
                item.icon_key,
            )
            for item in DEFAULT_QUICK_ACCESS_ITEMS
        ]

        self.assertEqual(
            actual,
            expected,
        )

    def test_catalogue_item_ids_are_unique(
        self,
    ):
        item_ids = [
            entry.item_id
            for entry in quick_access_catalogue()
        ]

        self.assertEqual(
            len(item_ids),
            len(set(item_ids)),
        )

    def test_catalogue_targets_are_unique(
        self,
    ):
        targets = [
            entry.target
            for entry in quick_access_catalogue()
        ]

        self.assertEqual(
            len(targets),
            len(set(targets)),
        )

    def test_lookup_by_item_id_is_normalized(
        self,
    ):
        entry = quick_access_catalogue_entry(
            "  BUILTIN.LIBRARY  "
        )

        self.assertIsNotNone(
            entry
        )

        self.assertEqual(
            entry.target,
            "library",
        )

    def test_lookup_by_target_is_normalized(
        self,
    ):
        entry = (
            quick_access_catalogue_entry_for_target(
                "  SPOTIFY "
            )
        )

        self.assertIsNotNone(
            entry
        )

        self.assertEqual(
            entry.item_id,
            "builtin.spotify",
        )

    def test_unknown_lookup_is_safe(
        self,
    ):
        self.assertIsNone(
            quick_access_catalogue_entry(
                "builtin.unknown"
            )
        )

        self.assertIsNone(
            quick_access_catalogue_entry_for_target(
                "unknown"
            )
        )

    def test_addable_catalogue_filters_existing_ids_and_preserves_order(
        self,
    ):
        addable = addable_quick_access_catalogue(
            [
                " BUILTIN.AFK ",
                "builtin.library",
                "builtin.spotify",
            ]
        )

        self.assertEqual(
            [
                entry.item_id
                for entry in addable
            ],
            [
                "builtin.custom",
                "builtin.presets",
                "builtin.settings",
                "builtin.presence",
                "builtin.about",
            ],
        )

    def test_entry_normalizes_safe_fields(
        self,
    ):
        entry = QuickAccessCatalogueEntry(
            item_id=" BUILTIN.LIBRARY ",
            kind=" BUILTIN ",
            target=" LIBRARY ",
            title=" Library ",
            detail=" Open music library ",
            icon_key=" LIBRARY ",
            included_by_default=False,
        )

        self.assertEqual(
            entry.item_id,
            "builtin.library",
        )

        self.assertEqual(
            entry.kind,
            "builtin",
        )

        self.assertEqual(
            entry.target,
            "library",
        )

        self.assertEqual(
            entry.title,
            "Library",
        )

        self.assertEqual(
            entry.detail,
            "Open music library",
        )

        self.assertEqual(
            entry.icon_key,
            "library",
        )

    def test_entry_rejects_mismatched_builtin_id(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessCatalogueEntry(
                item_id="builtin.spotify",
                kind="builtin",
                target="library",
                title="Library",
                detail="Open music library",
                icon_key="library",
            )

    def test_catalogue_module_has_no_ui_spotify_network_launcher_or_process_dependency(
        self,
    ):
        module = __import__(
            "src.system.quick_access_catalogue",
            fromlist=[
                "quick_access_catalogue",
            ],
        )

        source = inspect.getsource(
            module
        )

        forbidden = (
            "PyQt",
            "src.ui",
            "src.spotify",
            "launcher",
            "requests",
            "urllib",
            "socket",
            "subprocess",
            "os.startfile",
            "QDesktopServices",
        )

        for token in forbidden:
            with self.subTest(
                token=token
            ):
                self.assertNotIn(
                    token,
                    source,
                )


if __name__ == "__main__":
    unittest.main()
