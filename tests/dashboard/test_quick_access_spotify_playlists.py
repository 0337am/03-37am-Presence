from __future__ import annotations

import inspect
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtWidgets import QApplication

from src.spotify.playlist_models import (
    SpotifyPlaylistSummary,
)
from src.system.quick_access_preferences import (
    QuickAccessItem,
    QuickAccessPreferences,
    quick_access_item_from_payload,
    quick_access_item_to_payload,
    spotify_playlist_id_from_quick_access_target,
    spotify_playlist_quick_access_target,
)
from src.ui.dashboard import DashboardPage
from src.ui.main_window import MainWindow
from src.ui.quick_access_manager import (
    QuickAccessManagerDialog,
)
from src.ui.quick_access_picker import (
    QuickAccessGroupPickerDialog,
    QuickAccessPickerDialog,
)
from src.ui.spotify_page import SpotifyPage


def playlist() -> SpotifyPlaylistSummary:
    return SpotifyPlaylistSummary(
        spotify_id="AbC123",
        name="Night Mix",
        spotify_uri=(
            "spotify:playlist:AbC123"
        ),
        owner_name="Owner",
        total_items=5,
        artwork_reference=None,
    )


def playlist_item(
    *,
    title="Night Mix",
    detail="Owner",
    visible=True,
) -> QuickAccessItem:
    target = (
        spotify_playlist_quick_access_target(
            "AbC123"
        )
    )

    return QuickAccessItem(
        item_id=(
            "spotify_playlist."
            + target
        ),
        kind="spotify_playlist",
        target=target,
        title=title,
        detail=detail,
        icon_key="spotify",
        visible=visible,
    )


class QuickAccessSpotifyPlaylistTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_codec_round_trip_preserves_case(
        self,
    ):
        target = (
            spotify_playlist_quick_access_target(
                "AbC123"
            )
        )

        self.assertEqual(
            target,
            "p_ab_c123",
        )

        self.assertEqual(
            spotify_playlist_id_from_quick_access_target(
                target
            ),
            "AbC123",
        )

    def test_codec_rejects_invalid_spotify_ids(
        self,
    ):
        for value in (
            "",
            " AbC123",
            "AbC123 ",
            "playlist-1",
            "abc_123",
            "é123",
            "A" * 23,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    ValueError
                ):
                    spotify_playlist_quick_access_target(
                        value
                    )

        with self.assertRaises(
            TypeError
        ):
            spotify_playlist_quick_access_target(
                None
            )

    def test_quick_access_item_accepts_playlist(
        self,
    ):
        item = playlist_item()

        self.assertEqual(
            item.kind,
            "spotify_playlist",
        )
        self.assertEqual(
            item.target,
            "p_ab_c123",
        )
        self.assertEqual(
            item.icon_key,
            "spotify",
        )

    def test_playlist_item_rejects_mismatched_item_id(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id=(
                    "spotify_playlist.pwrong"
                ),
                kind="spotify_playlist",
                target="p_ab_c123",
                title="Night Mix",
                detail="Owner",
                icon_key="spotify",
            )

    def test_playlist_item_rejects_wrong_icon(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id=(
                    "spotify_playlist."
                    "p_ab_c123"
                ),
                kind="spotify_playlist",
                target="p_ab_c123",
                title="Night Mix",
                detail="Owner",
                icon_key="presets",
            )

    def test_playlist_item_payload_round_trip(
        self,
    ):
        item = playlist_item(
            visible=False
        )

        payload = (
            quick_access_item_to_payload(
                item
            )
        )

        self.assertEqual(
            quick_access_item_from_payload(
                payload
            ),
            item,
        )

    def test_dashboard_dynamic_item_uses_live_metadata(
        self,
    ):
        host = SimpleNamespace(
            _spotify_quick_access_playlists={
                "AbC123": playlist(),
            }
        )

        items = (
            DashboardPage
            ._spotify_playlist_quick_access_items(
                host
            )
        )

        self.assertEqual(
            len(items),
            1,
        )

        item = items[0]

        self.assertEqual(
            item.item_id,
            (
                "spotify_playlist."
                "p_ab_c123"
            ),
        )
        self.assertEqual(
            item.title,
            "Night Mix",
        )
        self.assertEqual(
            item.detail,
            "Owner",
        )

    def test_dashboard_setter_stores_and_refreshes(
        self,
    ):
        calls = []

        host = SimpleNamespace(
            quick_access_grid=object(),
            refresh_quick_access_buttons=(
                lambda force=False:
                calls.append(
                    force
                )
            ),
        )

        DashboardPage.set_spotify_quick_access_playlists(
            host,
            (
                playlist(),
                object(),
            ),
        )

        self.assertEqual(
            tuple(
                host
                ._spotify_quick_access_playlists
                .keys()
            ),
            (
                "AbC123",
            ),
        )

        self.assertEqual(
            calls,
            [
                True,
            ],
        )

    def test_dashboard_playlist_route_is_signal_only(
        self,
    ):
        source = inspect.getsource(
            DashboardPage
            .refresh_quick_access_buttons
        )

        self.assertIn(
            (
                "spotify_playlist_requested"
                ".emit"
            ),
            source,
        )

        self.assertNotIn(
            "spotify:",
            source,
        )
        self.assertNotIn(
            "play_track(",
            source,
        )
        self.assertNotIn(
            "start_playback",
            source,
        )

    def test_picker_groups_playlist_and_filters_duplicate(
        self,
    ):
        item = playlist_item()

        dialog = QuickAccessPickerDialog(
            (),
            dynamic_items=(
                item,
            ),
        )

        try:
            self.assertNotIn(
                item,
                dialog._entries,
            )

            self.assertEqual(
                dialog._group_entries[
                    "spotify_playlists"
                ],
                (
                    item,
                ),
            )

            self.assertEqual(
                [
                    row[
                        "title"
                    ].text()
                    for row
                    in dialog._group_rows
                ],
                [
                    "Playlists",
                ],
            )

            regular_row_ids = [
                row[
                    "item_id"
                ]
                for row
                in dialog._rows
            ]

            self.assertNotIn(
                item.item_id,
                regular_row_ids,
            )

        finally:
            dialog.close()

        duplicate = QuickAccessPickerDialog(
            (
                item.item_id,
            ),
            dynamic_items=(
                item,
            ),
        )

        try:
            self.assertNotIn(
                "spotify_playlists",
                duplicate._group_entries,
            )

            self.assertEqual(
                duplicate._group_rows,
                [],
            )

        finally:
            duplicate.close()

    def test_playlist_group_search_matches_title_and_owner(
        self,
    ):
        first = playlist_item()

        second_target = (
            spotify_playlist_quick_access_target(
                "ZyX987"
            )
        )

        second = QuickAccessItem(
            item_id=(
                "spotify_playlist."
                + second_target
            ),
            kind="spotify_playlist",
            target=second_target,
            title="Late Night Archive",
            detail="Second Owner",
            icon_key="spotify",
            visible=True,
        )

        dialog = QuickAccessGroupPickerDialog(
            (
                first,
                second,
            ),
            title="Playlists",
            description=(
                "Choose a Spotify playlist."
            ),
            search_placeholder=(
                "Search playlists"
            ),
        )

        try:
            dialog._filter_rows(
                "second owner"
            )

            self.assertTrue(
                dialog._rows[
                    0
                ][
                    "row"
                ].isHidden()
            )

            self.assertFalse(
                dialog._rows[
                    1
                ][
                    "row"
                ].isHidden()
            )

            dialog._filter_rows(
                "night mix"
            )

            self.assertFalse(
                dialog._rows[
                    0
                ][
                    "row"
                ].isHidden()
            )

            self.assertTrue(
                dialog._rows[
                    1
                ][
                    "row"
                ].isHidden()
            )

        finally:
            dialog.close()


    def test_playlist_group_choose_returns_stable_item_id(
        self,
    ):
        item = playlist_item()

        dialog = QuickAccessGroupPickerDialog(
            (
                item,
            ),
            title="Playlists",
            description=(
                "Choose a Spotify playlist."
            ),
            search_placeholder=(
                "Search playlists"
            ),
        )

        try:
            self.assertTrue(
                dialog._choose(
                    item.item_id
                )
            )

            self.assertEqual(
                dialog.selected_item_id(),
                item.item_id,
            )

        finally:
            dialog.close()


    def test_root_accepts_playlist_selected_from_group(
        self,
    ):
        item = playlist_item()

        dialog = QuickAccessPickerDialog(
            (),
            dynamic_items=(
                item,
            ),
        )

        try:
            self.assertTrue(
                dialog._accept_group_item(
                    "spotify_playlists",
                    item.item_id,
                )
            )

            self.assertEqual(
                dialog.selected_item_id(),
                item.item_id,
            )

        finally:
            dialog.close()


    def test_root_rejects_unknown_playlist_group_item(
        self,
    ):
        item = playlist_item()

        dialog = QuickAccessPickerDialog(
            (),
            dynamic_items=(
                item,
            ),
        )

        try:
            self.assertFalse(
                dialog._accept_group_item(
                    "spotify_playlists",
                    "spotify_playlist.pwrong",
                )
            )

            self.assertIsNone(
                dialog.selected_item_id()
            )

        finally:
            dialog.close()


    def test_manager_refreshes_metadata_and_keeps_visibility(
        self,
    ):
        snapshot = playlist_item(
            title="Old title",
            detail="Old owner",
            visible=False,
        )

        live = playlist_item(
            title="Night Mix",
            detail="Owner",
            visible=True,
        )

        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=(
                    snapshot,
                )
            ),
            dynamic_items=(
                live,
            ),
        )

        try:
            refreshed = (
                dialog._items[
                    0
                ]
            )

            self.assertEqual(
                refreshed.title,
                "Night Mix",
            )
            self.assertEqual(
                refreshed.detail,
                "Owner",
            )
            self.assertFalse(
                refreshed.visible
            )
        finally:
            dialog.close()

    def test_manager_keeps_stale_playlist_removable(
        self,
    ):
        stale = playlist_item(
            title="Deleted playlist",
            detail="Spotify playlist",
        )

        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=(
                    stale,
                )
            ),
            dynamic_items=(),
        )

        try:
            self.assertEqual(
                len(
                    dialog._items
                ),
                1,
            )

            self.assertTrue(
                dialog._remove_item(
                    0
                )
            )

            self.assertEqual(
                dialog._items,
                [],
            )
        finally:
            dialog.close()

    def test_spotify_page_reference_builds_summary(
        self,
    ):
        captured = []

        host = SimpleNamespace(
            show_playlist_detail=(
                lambda value:
                (
                    captured.append(
                        value
                    )
                    or True
                )
            )
        )

        self.assertTrue(
            SpotifyPage.show_playlist_reference(
                host,
                "AbC123",
                "Night Mix",
                "Owner",
            )
        )

        self.assertEqual(
            len(captured),
            1,
        )

        summary = captured[
            0
        ]

        self.assertIsInstance(
            summary,
            SpotifyPlaylistSummary,
        )
        self.assertEqual(
            summary.spotify_id,
            "AbC123",
        )
        self.assertEqual(
            summary.spotify_uri,
            "spotify:playlist:AbC123",
        )

    def test_spotify_page_reference_rejects_bad_id(
        self,
    ):
        captured = []

        host = SimpleNamespace(
            show_playlist_detail=(
                lambda value:
                captured.append(
                    value
                )
            )
        )

        self.assertFalse(
            SpotifyPage.show_playlist_reference(
                host,
                "playlist-1",
                "Bad",
            )
        )

        self.assertEqual(
            captured,
            [],
        )

    def test_main_window_deep_link_switches_to_spotify(
        self,
    ):
        pages = []
        references = []

        host = SimpleNamespace(
            spotify_page=SimpleNamespace(
                show_playlist_reference=(
                    lambda spotify_id, title:
                    (
                        references.append(
                            (
                                spotify_id,
                                title,
                            )
                        )
                        or True
                    )
                )
            ),
            switch_page=(
                lambda index:
                pages.append(
                    index
                )
            ),
        )

        self.assertTrue(
            MainWindow
            .open_spotify_playlist_from_dashboard(
                host,
                "AbC123",
                "Night Mix",
            )
        )

        self.assertEqual(
            pages,
            [
                5,
            ],
        )

        self.assertEqual(
            references,
            [
                (
                    "AbC123",
                    "Night Mix",
                ),
            ],
        )

    def test_main_window_runtime_ready_forwards_playlists(
        self,
    ):
        captured = []

        host = SimpleNamespace(
            dashboard_page=SimpleNamespace(
                set_spotify_quick_access_playlists=(
                    lambda value:
                    captured.append(
                        value
                    )
                )
            )
        )

        MainWindow._handle_quick_access_spotify_playlists_ready(
            host,
            SimpleNamespace(
                playlists_page=(
                    SimpleNamespace(
                        playlists=(
                            playlist(),
                        )
                    )
                )
            ),
        )

        self.assertEqual(
            len(captured),
            1,
        )
        self.assertEqual(
            captured[0][0].spotify_id,
            "AbC123",
        )

    def test_main_window_runtime_ready_rejects_bad_shape(
        self,
    ):
        captured = []

        host = SimpleNamespace(
            dashboard_page=SimpleNamespace(
                set_spotify_quick_access_playlists=(
                    lambda value:
                    captured.append(
                        value
                    )
                )
            )
        )

        MainWindow._handle_quick_access_spotify_playlists_ready(
            host,
            SimpleNamespace(
                playlists_page=None
            ),
        )

        MainWindow._handle_quick_access_spotify_playlists_ready(
            host,
            SimpleNamespace(
                playlists_page=(
                    SimpleNamespace(
                        playlists="bad"
                    )
                )
            ),
        )

        self.assertEqual(
            captured,
            [],
        )

    def test_connect_services_contains_playlist_connections(
        self,
    ):
        source = inspect.getsource(
            MainWindow.connect_services
        )

        self.assertIn(
            (
                "spotify_playlist_requested"
                ".connect"
            ),
            source,
        )
        self.assertIn(
            (
                "spotify_playlist_runtime"
                ".playlists_ready.connect"
            ),
            source,
        )


if __name__ == "__main__":
    unittest.main()
