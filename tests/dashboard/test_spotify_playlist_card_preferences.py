from __future__ import annotations

import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from src.system.spotify_playlist_card_preferences import (
    MAX_CARDS,
    SCHEMA_VERSION,
    SpotifyPlaylistCardConfig,
    SpotifyPlaylistCardPreferences,
    SpotifyPlaylistCardPreferencesError,
    SpotifyPlaylistCardPreferencesStore,
    default_spotify_playlist_card_preferences_path,
    new_spotify_playlist_card_id,
    normalise_spotify_playlist_id,
    spotify_playlist_uri,
)


class SpotifyPlaylistCardPreferencesTests(
    unittest.TestCase
):
    def test_playlist_id_normalises_whitespace(self):
        self.assertEqual(
            normalise_spotify_playlist_id(
                "  AbC123  "
            ),
            "AbC123",
        )

    def test_playlist_id_rejects_unsafe_values(self):
        for value in (
            "",
            "playlist/123",
            "spotify:playlist:abc",
            "../abc",
            "abc def",
        ):
            with self.subTest(value=value):
                with self.assertRaises(
                    SpotifyPlaylistCardPreferencesError
                ):
                    normalise_spotify_playlist_id(
                        value
                    )

    def test_playlist_uri_is_derived_from_id(self):
        self.assertEqual(
            spotify_playlist_uri(
                "AbC123"
            ),
            "spotify:playlist:AbC123",
        )

    def test_generated_card_id_is_safe_and_unique(self):
        first = (
            new_spotify_playlist_card_id()
        )

        second = (
            new_spotify_playlist_card_id()
        )

        self.assertNotEqual(
            first,
            second,
        )

        self.assertTrue(
            first.startswith(
                "spotify_playlist_card."
            )
        )

    def test_config_factory_builds_exact_uri(self):
        config = (
            SpotifyPlaylistCardConfig
            .for_playlist(
                "AbC123",
                card_id="card.one",
            )
        )

        self.assertEqual(
            config.card_id,
            "card.one",
        )

        self.assertEqual(
            config.playlist_id,
            "AbC123",
        )

        self.assertEqual(
            config.playlist_uri,
            "spotify:playlist:AbC123",
        )

    def test_config_rejects_mismatched_uri(self):
        with self.assertRaises(
            SpotifyPlaylistCardPreferencesError
        ):
            SpotifyPlaylistCardConfig(
                card_id="card.one",
                playlist_id="AbC123",
                playlist_uri=(
                    "spotify:playlist:Wrong"
                ),
            )

    def test_config_rejects_unsafe_card_id(self):
        with self.assertRaises(
            SpotifyPlaylistCardPreferencesError
        ):
            SpotifyPlaylistCardConfig.for_playlist(
                "AbC123",
                card_id="../card",
            )

    def test_config_is_frozen(self):
        config = (
            SpotifyPlaylistCardConfig
            .for_playlist(
                "AbC123",
                card_id="card.one",
            )
        )

        with self.assertRaises(
            dataclasses.FrozenInstanceError
        ):
            config.playlist_id = "Other"

    def test_config_payload_round_trip(self):
        config = (
            SpotifyPlaylistCardConfig
            .for_playlist(
                "AbC123",
                card_id="card.one",
            )
        )

        self.assertEqual(
            SpotifyPlaylistCardConfig
            .from_payload(
                config.to_payload()
            ),
            config,
        )

    def test_config_payload_rejects_extra_fields(self):
        with self.assertRaises(
            SpotifyPlaylistCardPreferencesError
        ):
            SpotifyPlaylistCardConfig.from_payload(
                {
                    "card_id": "card.one",
                    "playlist_id": "AbC123",
                    "playlist_uri": (
                        "spotify:playlist:AbC123"
                    ),
                    "access_token": "must-not-store",
                }
            )

    def test_preferences_reject_duplicate_card_ids(self):
        first = (
            SpotifyPlaylistCardConfig
            .for_playlist(
                "Playlist1",
                card_id="same",
            )
        )

        second = (
            SpotifyPlaylistCardConfig
            .for_playlist(
                "Playlist2",
                card_id="same",
            )
        )

        with self.assertRaises(
            SpotifyPlaylistCardPreferencesError
        ):
            SpotifyPlaylistCardPreferences(
                (
                    first,
                    second,
                )
            )

    def test_preferences_enforce_card_limit(self):
        cards = tuple(
            SpotifyPlaylistCardConfig
            .for_playlist(
                f"Playlist{index}",
                card_id=f"card.{index}",
            )
            for index in range(
                MAX_CARDS + 1
            )
        )

        with self.assertRaises(
            SpotifyPlaylistCardPreferencesError
        ):
            SpotifyPlaylistCardPreferences(
                cards
            )

    def test_preferences_upsert_and_get(self):
        preferences = (
            SpotifyPlaylistCardPreferences()
        )

        first = (
            SpotifyPlaylistCardConfig
            .for_playlist(
                "Playlist1",
                card_id="card.one",
            )
        )

        preferences = (
            preferences.with_card(
                first
            )
        )

        self.assertEqual(
            preferences.get(
                "card.one"
            ),
            first,
        )

        replacement = (
            SpotifyPlaylistCardConfig
            .for_playlist(
                "Playlist2",
                card_id="card.one",
            )
        )

        preferences = (
            preferences.with_card(
                replacement
            )
        )

        self.assertEqual(
            len(preferences.cards),
            1,
        )

        self.assertEqual(
            preferences.get(
                "card.one"
            ),
            replacement,
        )

    def test_preferences_remove_is_idempotent(self):
        preferences = (
            SpotifyPlaylistCardPreferences(
                (
                    SpotifyPlaylistCardConfig
                    .for_playlist(
                        "Playlist1",
                        card_id="card.one",
                    ),
                )
            )
        )

        removed = (
            preferences.without_card(
                "card.one"
            )
        )

        self.assertEqual(
            removed.cards,
            (),
        )

        self.assertEqual(
            removed.without_card(
                "card.one"
            ),
            removed,
        )

    def test_preferences_payload_round_trip(self):
        preferences = (
            SpotifyPlaylistCardPreferences(
                (
                    SpotifyPlaylistCardConfig
                    .for_playlist(
                        "Playlist1",
                        card_id="card.one",
                    ),
                    SpotifyPlaylistCardConfig
                    .for_playlist(
                        "Playlist2",
                        card_id="card.two",
                    ),
                )
            )
        )

        payload = (
            preferences.to_payload()
        )

        self.assertEqual(
            payload["schema_version"],
            SCHEMA_VERSION,
        )

        self.assertEqual(
            SpotifyPlaylistCardPreferences
            .from_payload(payload),
            preferences,
        )

    def test_preferences_reject_wrong_schema(self):
        with self.assertRaises(
            SpotifyPlaylistCardPreferencesError
        ):
            SpotifyPlaylistCardPreferences.from_payload(
                {
                    "schema_version": 999,
                    "cards": [],
                }
            )

    def test_default_path_uses_local_app_data(self):
        path = (
            default_spotify_playlist_card_preferences_path(
                local_app_data=(
                    r"C:\ExampleLocalAppData"
                )
            )
        )

        self.assertEqual(
            path,
            (
                Path(
                    r"C:\ExampleLocalAppData"
                )
                / "03-37am Presence"
                / "spotify_playlist_cards.json"
            ),
        )

    def test_store_creates_default_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(root)
                / "spotify_playlist_cards.json"
            )

            store = (
                SpotifyPlaylistCardPreferencesStore(
                    path
                )
            )

            preferences = store.load()

            self.assertEqual(
                preferences.cards,
                (),
            )

            self.assertTrue(
                path.is_file()
            )

            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                payload,
                {
                    "cards": [],
                    "schema_version": (
                        SCHEMA_VERSION
                    ),
                },
            )

    def test_store_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(root)
                / "spotify_playlist_cards.json"
            )

            store = (
                SpotifyPlaylistCardPreferencesStore(
                    path
                )
            )

            expected = (
                SpotifyPlaylistCardPreferences(
                    (
                        SpotifyPlaylistCardConfig
                        .for_playlist(
                            "AbC123",
                            card_id="card.one",
                        ),
                    )
                )
            )

            store.save(
                expected
            )

            self.assertEqual(
                store.load(),
                expected,
            )

    def test_store_upsert_and_remove(self):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(root)
                / "spotify_playlist_cards.json"
            )

            store = (
                SpotifyPlaylistCardPreferencesStore(
                    path
                )
            )

            config = (
                SpotifyPlaylistCardConfig
                .for_playlist(
                    "AbC123",
                    card_id="card.one",
                )
            )

            saved = store.upsert(
                config
            )

            self.assertEqual(
                saved.get(
                    "card.one"
                ),
                config,
            )

            removed = store.remove(
                "card.one"
            )

            self.assertEqual(
                removed.cards,
                (),
            )

            self.assertEqual(
                store.load().cards,
                (),
            )

    def test_store_save_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            path = (
                root_path
                / "spotify_playlist_cards.json"
            )

            store = (
                SpotifyPlaylistCardPreferencesStore(
                    path
                )
            )

            store.save(
                SpotifyPlaylistCardPreferences()
            )

            names = {
                item.name
                for item in root_path.iterdir()
            }

            self.assertEqual(
                names,
                {
                    "spotify_playlist_cards.json",
                },
            )

    def test_invalid_json_is_quarantined_and_reset(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            path = (
                root_path
                / "spotify_playlist_cards.json"
            )

            path.write_text(
                "{broken",
                encoding="utf-8",
            )

            store = (
                SpotifyPlaylistCardPreferencesStore(
                    path
                )
            )

            preferences = store.load()

            self.assertEqual(
                preferences.cards,
                (),
            )

            quarantined = list(
                root_path.glob(
                    "spotify_playlist_cards.json.corrupt-*"
                )
            )

            self.assertEqual(
                len(quarantined),
                1,
            )

            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                payload["schema_version"],
                SCHEMA_VERSION,
            )

    def test_store_reset_clears_assignments(self):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(root)
                / "spotify_playlist_cards.json"
            )

            store = (
                SpotifyPlaylistCardPreferencesStore(
                    path
                )
            )

            store.upsert(
                SpotifyPlaylistCardConfig
                .for_playlist(
                    "AbC123",
                    card_id="card.one",
                )
            )

            result = store.reset()

            self.assertEqual(
                result.cards,
                (),
            )

            self.assertEqual(
                store.load().cards,
                (),
            )

    def test_module_has_no_qt_network_auth_or_credentials(self):
        source = (
            Path(
                "src/system/"
                "spotify_playlist_card_preferences.py"
            )
            .read_text(
                encoding="utf-8"
            )
            .lower()
        )

        forbidden = (
            "pyqt6",
            "qsettings",
            "urllib",
            "requests",
            "web_api",
            "session_manager",
            "oauth",
            "access_token",
            "refresh_token",
            "client_secret",
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
