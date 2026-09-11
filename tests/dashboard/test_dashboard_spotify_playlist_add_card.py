from __future__ import annotations

import inspect
import unittest
from dataclasses import replace
from unittest.mock import patch

from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.playlist_models import (
    SpotifyPlaylistSummary,
)
from src.system.spotify_playlist_card_preferences import (
    SpotifyPlaylistCardPreferences,
)
from src.ui.dashboard import (
    DashboardPage,
    SPOTIFY_PLAYLIST_DASHBOARD_CARD_CONFIG_ID,
)
from src.ui.dashboard_layout import (
    preset_layout,
)
from src.ui.spotify_playlist_dashboard_card import (
    SpotifyPlaylistDashboardCard,
)


def playlist_layout(
    *,
    visible=False,
    locked=False,
):
    base = preset_layout(
        "Default"
    )

    cards = tuple(
        replace(
            card,
            visible=bool(
                visible
            ),
        )
        if card.card_id
        == "spotify_playlist"
        else card
        for card in base.cards
    )

    return replace(
        base,
        cards=cards,
        locked=bool(
            locked
        ),
        preset="Custom",
    )


def playlist_summary(
    spotify_id="AbC123",
):
    return SpotifyPlaylistSummary(
        spotify_id=spotify_id,
        name="Late Night Files",
        spotify_uri=(
            "spotify:playlist:"
            + spotify_id
        ),
        owner_name="03:37am",
        total_items=37,
    )


class FakeThemeManager:

    def theme(
        self,
    ):
        return {
            "background": "#101014",
            "card": "#18181f",
            "card_alt": "#202028",
            "border": "#34343e",
            "accent": "#ff4f91",
            "text": "#f4f4f6",
            "muted": "#a6a6b1",
        }


class FakeAction:

    def __init__(
        self,
    ):
        self.visible = None
        self.enabled = None

    def setVisible(
        self,
        value,
    ):
        self.visible = bool(
            value
        )

    def setEnabled(
        self,
        value,
    ):
        self.enabled = bool(
            value
        )


class FakePlaylistCard:

    def __init__(
        self,
    ):
        self.snapshot = None
        self.clear_calls = 0

    def set_snapshot(
        self,
        snapshot,
    ):
        self.snapshot = snapshot

    def clear_snapshot(
        self,
    ):
        self.clear_calls += 1
        self.snapshot = None


class FakeStore:

    def __init__(
        self,
    ):
        self.preferences = (
            SpotifyPlaylistCardPreferences()
        )

        self.upserts = []

    def load(
        self,
    ):
        return self.preferences

    def upsert(
        self,
        card,
    ):
        self.upserts.append(
            card
        )

        self.preferences = (
            self.preferences
            .with_card(
                card
            )
        )

        return self.preferences


class ConfigureHarness:

    def __init__(
        self,
        *,
        visible=False,
        locked=False,
    ):
        self.dashboard_layout_state = (
            playlist_layout(
                visible=visible,
                locked=locked,
            )
        )

        self.spotify_playlist_card = (
            FakePlaylistCard()
        )

        self.spotify_playlist_card_preferences_store = (
            FakeStore()
        )

        summary = playlist_summary()

        self._spotify_quick_access_playlists = {
            summary.spotify_id:
            summary
        }

        self.visibility_calls = []
        self.sync_calls = 0
        self.theme_manager = (
            FakeThemeManager()
        )

    def set_dashboard_card_visibility(
        self,
        card_id,
        visible,
    ):
        self.visibility_calls.append(
            (
                card_id,
                bool(
                    visible
                ),
            )
        )

    def sync_dashboard_layout_controls(
        self,
    ):
        self.sync_calls += 1


class SyncHarness:

    def __init__(
        self,
        *,
        visible=False,
        locked=False,
    ):
        self.dashboard_layout_state = (
            playlist_layout(
                visible=visible,
                locked=locked,
            )
        )

        self.layout_add_spotify_playlist_action = (
            FakeAction()
        )


class DashboardSpotifyPlaylistAddCardTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
        app = QApplication.instance()

        if app is None:
            app = QApplication([])

        cls.app = app

    def test_builder_creates_accepted_static_card(
        self,
    ):
        harness = type(
            "Harness",
            (),
            {
                "theme_manager":
                FakeThemeManager(),
                "dashboard_layout_state":
                playlist_layout(
                    visible=False
                ),
            },
        )()

        DashboardPage.build_spotify_playlist_card(
            harness
        )

        self.addCleanup(
            harness
            .spotify_playlist_card
            .deleteLater
        )

        self.assertIsInstance(
            harness.spotify_playlist_card,
            SpotifyPlaylistDashboardCard,
        )

        self.assertFalse(
            harness
            .spotify_playlist_card
            .play_button
            .isEnabled()
        )

        self.assertFalse(
            hasattr(
                harness.spotify_playlist_card,
                "previous_button",
            )
        )

        self.assertFalse(
            hasattr(
                harness.spotify_playlist_card,
                "next_button",
            )
        )

    def test_dashboard_build_ui_registers_playlist_card(
        self,
    ):
        source = inspect.getsource(
            DashboardPage.build_ui
        )

        self.assertIn(
            "self.build_spotify_playlist_card()",
            source,
        )

        self.assertIn(
            '"spotify_playlist"',
            source,
        )

        self.assertIn(
            "self.spotify_playlist_card",
            source,
        )

    def test_add_card_menu_wires_spotify_playlist_action(
        self,
    ):
        source = inspect.getsource(
            DashboardPage
            .build_dashboard_layout_toolbar
        )

        self.assertIn(
            "layout_add_spotify_playlist_action",
            source,
        )

        self.assertIn(
            '"Spotify Playlist"',
            source,
        )

        self.assertIn(
            "DashboardPage.add_spotify_playlist_card",
            source,
        )

    def test_add_action_is_available_only_when_hidden(
        self,
    ):
        hidden = SyncHarness(
            visible=False,
            locked=False,
        )

        DashboardPage.sync_dashboard_add_spotify_playlist_action(
            hidden
        )

        self.assertTrue(
            hidden
            .layout_add_spotify_playlist_action
            .visible
        )

        self.assertTrue(
            hidden
            .layout_add_spotify_playlist_action
            .enabled
        )

        visible = SyncHarness(
            visible=True,
            locked=False,
        )

        DashboardPage.sync_dashboard_add_spotify_playlist_action(
            visible
        )

        self.assertFalse(
            visible
            .layout_add_spotify_playlist_action
            .visible
        )

        self.assertFalse(
            visible
            .layout_add_spotify_playlist_action
            .enabled
        )

    def test_add_action_respects_layout_lock(
        self,
    ):
        harness = SyncHarness(
            visible=False,
            locked=True,
        )

        DashboardPage.sync_dashboard_add_spotify_playlist_action(
            harness
        )

        self.assertTrue(
            harness
            .layout_add_spotify_playlist_action
            .visible
        )

        self.assertFalse(
            harness
            .layout_add_spotify_playlist_action
            .enabled
        )

    def test_configure_persists_selection_and_reveals_card(
        self,
    ):
        harness = ConfigureHarness()

        result = (
            DashboardPage
            .configure_spotify_playlist_dashboard_card(
                harness,
                "AbC123",
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            len(
                harness
                .spotify_playlist_card_preferences_store
                .upserts
            ),
            1,
        )

        config = (
            harness
            .spotify_playlist_card_preferences_store
            .upserts[0]
        )

        self.assertEqual(
            config.card_id,
            SPOTIFY_PLAYLIST_DASHBOARD_CARD_CONFIG_ID,
        )

        self.assertEqual(
            config.playlist_id,
            "AbC123",
        )

        self.assertEqual(
            harness.visibility_calls,
            [
                (
                    "spotify_playlist",
                    True,
                )
            ],
        )

    def test_refresh_uses_live_playlist_header_metadata(
        self,
    ):
        harness = ConfigureHarness()

        DashboardPage.configure_spotify_playlist_dashboard_card(
            harness,
            "AbC123",
        )

        snapshot = (
            harness
            .spotify_playlist_card
            .snapshot
        )

        self.assertIsNotNone(
            snapshot
        )

        self.assertEqual(
            snapshot.playlist_id,
            "AbC123",
        )

        self.assertEqual(
            snapshot.title,
            "Late Night Files",
        )

        self.assertEqual(
            snapshot.owner,
            "03:37am",
        )

        self.assertEqual(
            snapshot.track_count,
            37,
        )

        self.assertEqual(
            snapshot.tracks,
            (),
        )

    def test_saved_selection_restores_without_live_metadata(
        self,
    ):
        harness = ConfigureHarness()

        DashboardPage.configure_spotify_playlist_dashboard_card(
            harness,
            "AbC123",
        )

        harness._spotify_quick_access_playlists = {}

        result = (
            DashboardPage
            .refresh_spotify_playlist_dashboard_card(
                harness
            )
        )

        self.assertTrue(
            result
        )

        snapshot = (
            harness
            .spotify_playlist_card
            .snapshot
        )

        self.assertEqual(
            snapshot.playlist_id,
            "AbC123",
        )

        self.assertEqual(
            snapshot.title,
            "Spotify Playlist",
        )

        self.assertEqual(
            snapshot.owner,
            "Waiting for Spotify",
        )

    def test_add_card_opens_direct_spotify_playlist_picker(
        self,
    ):
        harness = ConfigureHarness()

        class FakeDialog:

            received_entries = ()
            received_title = None
            received_description = None
            received_search_placeholder = None

            def __init__(
                self,
                entries,
                *,
                title,
                description,
                search_placeholder,
                theme=None,
                parent=None,
            ):
                del theme
                del parent

                FakeDialog.received_entries = (
                    tuple(
                        entries
                    )
                )

                FakeDialog.received_title = (
                    title
                )

                FakeDialog.received_description = (
                    description
                )

                FakeDialog.received_search_placeholder = (
                    search_placeholder
                )

            def exec(
                self,
            ):
                return 1

            def selected_item_id(
                self,
            ):
                return (
                    FakeDialog
                    .received_entries[0]
                    .item_id
                )

        with (
            patch(
                (
                    "src.ui.dashboard."
                    "QuickAccessGroupPickerDialog"
                ),
                FakeDialog,
            ),
            patch(
                (
                    "src.ui.dashboard."
                    "QuickAccessPickerDialog"
                ),
                side_effect=AssertionError(
                    "Root Quick Access picker must not open."
                ),
            ),
        ):
            result = (
                DashboardPage
                .add_spotify_playlist_card(
                    harness
                )
            )

        self.assertTrue(
            result
        )

        self.assertTrue(
            FakeDialog.received_entries
        )

        self.assertTrue(
            all(
                item.kind
                == "spotify_playlist"
                for item
                in FakeDialog.received_entries
            )
        )

        self.assertEqual(
            FakeDialog.received_title,
            "Spotify Playlists",
        )

        self.assertEqual(
            FakeDialog.received_search_placeholder,
            "Search playlists",
        )

        self.assertIn(
            "Dashboard card",
            FakeDialog.received_description,
        )

        config = (
            harness
            .spotify_playlist_card_preferences_store
            .preferences
            .get(
                SPOTIFY_PLAYLIST_DASHBOARD_CARD_CONFIG_ID
            )
        )

        self.assertIsNotNone(
            config
        )

        self.assertEqual(
            config.playlist_id,
            "AbC123",
        )

    def test_direct_playlist_picker_cancel_is_noop(
        self,
    ):
        harness = ConfigureHarness()

        class FakeDialog:

            def __init__(
                self,
                entries,
                *,
                title,
                description,
                search_placeholder,
                theme=None,
                parent=None,
            ):
                del entries
                del title
                del description
                del search_placeholder
                del theme
                del parent

            def exec(
                self,
            ):
                return 0

            def selected_item_id(
                self,
            ):
                raise AssertionError(
                    "Selection must not be read after cancel."
                )

        with patch(
            (
                "src.ui.dashboard."
                "QuickAccessGroupPickerDialog"
            ),
            FakeDialog,
        ):
            result = (
                DashboardPage
                .add_spotify_playlist_card(
                    harness
                )
            )

        self.assertFalse(
            result
        )

        self.assertEqual(
            harness
            .spotify_playlist_card_preferences_store
            .upserts,
            [],
        )

        self.assertEqual(
            harness.visibility_calls,
            [],
        )

    def test_add_card_with_no_loaded_playlists_does_not_open_picker(
        self,
    ):
        harness = ConfigureHarness()

        harness._spotify_quick_access_playlists = {}

        with (
            patch(
                (
                    "src.ui.dashboard."
                    "QuickAccessGroupPickerDialog"
                ),
                side_effect=AssertionError(
                    "Playlist picker must not open with no playlists."
                ),
            ),
            patch(
                (
                    "src.ui.dashboard."
                    "QuickAccessPickerDialog"
                ),
                side_effect=AssertionError(
                    "Root Quick Access picker must never open."
                ),
            ),
        ):
            result = (
                DashboardPage
                .add_spotify_playlist_card(
                    harness
                )
            )

        self.assertFalse(
            result
        )

        self.assertEqual(
            harness
            .spotify_playlist_card_preferences_store
            .upserts,
            [],
        )

        self.assertEqual(
            harness.visibility_calls,
            [],
        )

    def test_locked_layout_rejects_configuration(
        self,
    ):
        harness = ConfigureHarness(
            locked=True
        )

        result = (
            DashboardPage
            .configure_spotify_playlist_dashboard_card(
                harness,
                "AbC123",
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            harness
            .spotify_playlist_card_preferences_store
            .upserts,
            [],
        )

    def test_production_methods_add_no_playback_or_launch_path(
        self,
    ):
        methods = (
            DashboardPage
            .add_spotify_playlist_card,
            DashboardPage
            .configure_spotify_playlist_dashboard_card,
            DashboardPage
            .refresh_spotify_playlist_dashboard_card,
        )

        source = "\n".join(
            inspect.getsource(
                method
            )
            for method in methods
        ).casefold()

        forbidden = (
            "play_playlist_position",
            "play_playlist_track",
            "qmediaplayer",
            "os.startfile",
            "sendinput",
            "setforegroundwindow",
            "webbrowser",
            "subprocess",
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
