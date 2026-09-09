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


def legacy_v3_payload():
    payload = (
        preset_layout(
            "Default"
        )
        .to_dict()
    )

    payload[
        "schema_version"
    ] = 3

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
        ] != "spotify_playlist"
    ]

    return payload


class DashboardSpotifyPlaylistLayoutMigrationTests(
    unittest.TestCase
):

    def test_playlist_card_is_registered_in_schema_four(
        self,
    ):
        self.assertEqual(
            SCHEMA_VERSION,
            4,
        )

        self.assertIn(
            "spotify_playlist",
            CARD_SPECS,
        )

        self.assertEqual(
            CARD_SPECS[
                "spotify_playlist"
            ].title,
            "Spotify Playlist",
        )

        self.assertEqual(
            CARD_ORDER[-2:],
            (
                "queue",
                "spotify_playlist",
            ),
        )

    def test_all_presets_include_playlist_card_hidden(
        self,
    ):
        for (
            name,
            layout,
        ) in PRESET_LAYOUTS.items():
            with self.subTest(
                preset=name
            ):
                playlist = layout.card(
                    "spotify_playlist"
                )

                self.assertFalse(
                    playlist.visible
                )

                self.assertEqual(
                    layout.schema_version,
                    SCHEMA_VERSION,
                )

    def test_v3_migration_preserves_existing_cards(
        self,
    ):
        payload = legacy_v3_payload()

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
            for card in migrated.cards
            if card.card_id
            != "spotify_playlist"
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
            4,
        )

    def test_v3_migration_adds_stable_hidden_geometry(
        self,
    ):
        migrated = (
            DashboardLayout
            .from_dict(
                legacy_v3_payload()
            )
        )

        playlist = migrated.card(
            "spotify_playlist"
        )

        self.assertEqual(
            (
                playlist.x,
                playlist.y,
                playlist.width,
                playlist.height,
            ),
            (
                5100,
                3600,
                4900,
                5200,
            ),
        )

        self.assertFalse(
            playlist.visible
        )

        self.assertGreater(
            playlist.z_index,
            migrated.card(
                "queue"
            ).z_index,
        )

    def test_layout_store_resaves_schema_three(
        self,
    ):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(root)
                / "dashboard_layout.json"
            )

            path.write_text(
                json.dumps(
                    legacy_v3_payload()
                ),
                encoding="utf-8",
            )

            store = DashboardLayoutStore(
                path
            )

            migrated = store.load()

            persisted = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(
            migrated.schema_version,
            4,
        )

        self.assertEqual(
            persisted[
                "schema_version"
            ],
            4,
        )

        self.assertTrue(
            any(
                card[
                    "card_id"
                ]
                == "spotify_playlist"
                for card in persisted[
                    "cards"
                ]
            )
        )

    def test_embedded_profile_schema_three_migrates(
        self,
    ):
        profile = (
            DashboardLayoutProfile
            .from_dict(
                {
                    "name": "Playlist Layout",
                    "layout": (
                        legacy_v3_payload()
                    ),
                }
            )
        )

        self.assertEqual(
            profile.layout.schema_version,
            4,
        )

        self.assertFalse(
            profile.layout.card(
                "spotify_playlist"
            ).visible
        )

    def test_current_schema_requires_playlist_card(
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
            for card in payload[
                "cards"
            ]
            if card[
                "card_id"
            ]
            != "spotify_playlist"
        ]

        with self.assertRaises(
            ValueError
        ):
            DashboardLayout.from_dict(
                payload
            )

    def test_v2_migration_also_contains_playlist_card(
        self,
    ):
        payload = legacy_v3_payload()

        payload[
            "schema_version"
        ] = 2

        payload[
            "cards"
        ] = [
            card
            for card in payload[
                "cards"
            ]
            if card[
                "card_id"
            ]
            != "queue"
        ]

        migrated = (
            DashboardLayout
            .from_dict(
                payload
            )
        )

        self.assertEqual(
            migrated.schema_version,
            4,
        )

        self.assertFalse(
            migrated.card(
                "queue"
            ).visible
        )

        self.assertFalse(
            migrated.card(
                "spotify_playlist"
            ).visible
        )


if __name__ == "__main__":
    unittest.main()
