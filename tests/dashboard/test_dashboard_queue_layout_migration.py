from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.ui.dashboard_layout import (
    CARD_ORDER,
    CARD_SPECS,
    PRESET_LAYOUTS,
    SCHEMA_VERSION,
    DashboardLayout,
    DashboardLayoutStore,
    preset_layout,
)
from src.ui.dashboard_profiles import (
    DashboardLayoutProfile,
)


def v2_payload():
    payload = (
        preset_layout(
            "Default"
        )
        .to_dict()
    )

    payload[
        "schema_version"
    ] = 2

    payload[
        "locked"
    ] = False

    payload[
        "preset"
    ] = "Custom"

    payload[
        "cards"
    ] = [
        dict(card)
        for card in payload[
            "cards"
        ]
        if card[
            "card_id"
        ] != "queue"
    ]

    return payload


def v1_custom_payload():
    return {
        "schema_version": 1,
        "locked": False,
        "preset": "Custom",
        "cards": [
            {
                "card_id": "now_playing",
                "row": 0,
                "column": 0,
                "column_span": 7,
                "row_span": 1,
                "visible": True,
            },
            {
                "card_id": "discord_preview",
                "row": 0,
                "column": 7,
                "column_span": 5,
                "row_span": 1,
                "visible": True,
            },
            {
                "card_id": "recently_played",
                "row": 1,
                "column": 0,
                "column_span": 4,
                "row_span": 1,
                "visible": True,
            },
            {
                "card_id": "quick_access",
                "row": 1,
                "column": 4,
                "column_span": 4,
                "row_span": 1,
                "visible": True,
            },
            {
                "card_id": "library_status",
                "row": 1,
                "column": 8,
                "column_span": 4,
                "row_span": 1,
                "visible": True,
            },
            {
                "card_id": "discord_status",
                "row": 2,
                "column": 0,
                "column_span": 4,
                "row_span": 1,
                "visible": True,
            },
            {
                "card_id": "music_status",
                "row": 2,
                "column": 4,
                "column_span": 4,
                "row_span": 1,
                "visible": True,
            },
            {
                "card_id": "auto_afk",
                "row": 2,
                "column": 8,
                "column_span": 4,
                "row_span": 1,
                "visible": True,
            },
        ],
    }


class RecordingLayoutStore(
    DashboardLayoutStore
):

    def __init__(
        self,
        path,
    ):
        self.path = Path(
            path
        )

        self.backups = 0
        self.saved = []

    def _backup_legacy_file(
        self,
    ):
        self.backups += 1

    def save(
        self,
        layout,
    ):
        self.saved.append(
            layout
        )

        return layout


class DashboardQueueLayoutMigrationTests(
    unittest.TestCase
):

    def test_queue_is_registered_as_hidden_built_in_card(
        self,
    ):
        self.assertEqual(
            SCHEMA_VERSION,
            3,
        )

        self.assertIn(
            "queue",
            CARD_SPECS,
        )

        self.assertEqual(
            CARD_SPECS[
                "queue"
            ].title,
            "Spotify Queue",
        )

        self.assertEqual(
            CARD_ORDER[-1],
            "queue",
        )

    def test_all_presets_include_queue_hidden(
        self,
    ):
        for (
            name,
            layout,
        ) in PRESET_LAYOUTS.items():
            with self.subTest(
                preset=name
            ):
                queue = layout.card(
                    "queue"
                )

                self.assertFalse(
                    queue.visible
                )

                self.assertEqual(
                    layout.schema_version,
                    SCHEMA_VERSION,
                )

    def test_v2_migration_preserves_existing_card_layout(
        self,
    ):
        payload = v2_payload()

        expected = {
            card[
                "card_id"
            ]:
            dict(card)
            for card in payload[
                "cards"
            ]
        }

        migrated = (
            DashboardLayout
            .from_dict(
                payload
            )
        )

        actual = {
            card.card_id:
            card.to_dict()
            for card
            in migrated.cards
            if (
                card.card_id
                != "queue"
            )
        }

        self.assertEqual(
            actual,
            expected,
        )

        self.assertFalse(
            migrated.locked
        )

        self.assertEqual(
            migrated.preset,
            "Custom",
        )

        self.assertEqual(
            migrated.schema_version,
            3,
        )

    def test_v2_migration_adds_stable_hidden_queue_geometry(
        self,
    ):
        migrated = (
            DashboardLayout
            .from_dict(
                v2_payload()
            )
        )

        queue = migrated.card(
            "queue"
        )

        self.assertEqual(
            (
                queue.x,
                queue.y,
                queue.width,
                queue.height,
            ),
            (
                0,
                3600,
                4900,
                4300,
            ),
        )

        self.assertFalse(
            queue.visible
        )

        non_queue_z = [
            card.z_index
            for card
            in migrated.cards
            if (
                card.card_id
                != "queue"
            )
        ]

        self.assertGreater(
            queue.z_index,
            max(
                non_queue_z
            ),
        )

    def test_layout_store_resaves_v2_migration(
        self,
    ):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(root)
                / "dashboard_layout.json"
            )

            path.write_text(
                json.dumps(
                    v2_payload()
                ),
                encoding="utf-8",
            )

            store = (
                RecordingLayoutStore(
                    path
                )
            )

            migrated = store.load()

        self.assertEqual(
            store.backups,
            1,
        )

        self.assertEqual(
            len(
                store.saved
            ),
            1,
        )

        self.assertIs(
            store.saved[0],
            migrated,
        )

        self.assertEqual(
            migrated.schema_version,
            3,
        )

        self.assertFalse(
            migrated.card(
                "queue"
            ).visible
        )

    def test_profile_embedded_v2_layout_migrates(
        self,
    ):
        profile = (
            DashboardLayoutProfile
            .from_dict(
                {
                    "name": "My Layout",
                    "layout": (
                        v2_payload()
                    ),
                }
            )
        )

        self.assertEqual(
            profile.layout.schema_version,
            3,
        )

        self.assertFalse(
            profile.layout.card(
                "queue"
            ).visible
        )

        self.assertEqual(
            profile.layout.preset,
            "Custom",
        )

    def test_v1_custom_layout_also_gains_hidden_queue(
        self,
    ):
        migrated = (
            DashboardLayout
            .from_dict(
                v1_custom_payload()
            )
        )

        self.assertEqual(
            migrated.schema_version,
            3,
        )

        self.assertEqual(
            migrated.preset,
            "Custom",
        )

        self.assertFalse(
            migrated.locked
        )

        self.assertEqual(
            {
                card.card_id
                for card
                in migrated.cards
            },
            set(
                CARD_ORDER
            ),
        )

        self.assertFalse(
            migrated.card(
                "queue"
            ).visible
        )

    def test_v1_preset_migration_keeps_queue_hidden(
        self,
    ):
        migrated = (
            DashboardLayout
            .from_dict(
                {
                    "schema_version": 1,
                    "locked": False,
                    "preset": "Default",
                }
            )
        )

        self.assertEqual(
            migrated.schema_version,
            3,
        )

        self.assertFalse(
            migrated.locked
        )

        self.assertEqual(
            migrated.preset,
            "Default",
        )

        self.assertFalse(
            migrated.card(
                "queue"
            ).visible
        )

    def test_current_schema_still_requires_queue_card(
        self,
    ):
        payload = (
            preset_layout(
                "Default"
            )
            .to_dict()
        )

        payload[
            "cards"
        ] = [
            card
            for card
            in payload[
                "cards"
            ]
            if card[
                "card_id"
            ] != "queue"
        ]

        with self.assertRaises(
            ValueError
        ):
            DashboardLayout.from_dict(
                payload
            )


if __name__ == "__main__":
    unittest.main()
