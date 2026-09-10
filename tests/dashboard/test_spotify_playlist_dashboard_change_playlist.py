from __future__ import annotations

import inspect
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch


os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)


from PyQt6.QtWidgets import (
    QApplication,
    QPushButton,
)

from src.system.quick_access_preferences import (
    spotify_playlist_quick_access_target,
)
from src.ui.dashboard import (
    DashboardPage,
    SPOTIFY_PLAYLIST_DASHBOARD_CARD_CONFIG_ID,
)
from src.ui.spotify_playlist_dashboard_card import (
    SpotifyPlaylistDashboardCard,
)


class _Dialog:

    accepted = True
    selected = "playlist.other"
    dynamic_items = ()

    def __init__(
        self,
        existing_item_ids,
        theme=None,
        parent=None,
        *,
        dynamic_items=(),
    ):
        del existing_item_ids
        del theme
        del parent

        type(self).dynamic_items = tuple(
            dynamic_items
        )

    def exec(self):
        return int(
            bool(
                type(self).accepted
            )
        )

    def selected_item_id(self):
        return type(self).selected


def _item(
    item_id,
    playlist_id,
):
    return SimpleNamespace(
        item_id=item_id,
        target=(
            spotify_playlist_quick_access_target(
                playlist_id
            )
        ),
    )


class _Layout:

    def __init__(
        self,
        *,
        locked,
        visible,
    ):
        self.locked = bool(
            locked
        )

        self.playlist = (
            SimpleNamespace(
                visible=bool(
                    visible
                )
            )
        )

    def card(
        self,
        card_id,
    ):
        if card_id != "spotify_playlist":
            raise KeyError(card_id)

        return self.playlist


class _Store:

    def __init__(self):
        self.upserts = []

    def upsert(
        self,
        config,
    ):
        self.upserts.append(
            config
        )


class SpotifyPlaylistDashboardChangePlaylistTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def setUp(self):
        _Dialog.accepted = True
        _Dialog.selected = (
            "playlist.other"
        )
        _Dialog.dynamic_items = ()

    def test_more_control_is_button(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        self.assertIsInstance(
            card.more_label,
            QPushButton,
        )

        self.assertEqual(
            card.more_label.text(),
            "...",
        )

        self.assertEqual(
            card.more_label.toolTip(),
            "Change playlist",
        )

        self.assertEqual(
            card.more_label.accessibleName(),
            "Change playlist",
        )

    def test_more_button_emits_signal_once(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        calls = []

        card.change_playlist_requested.connect(
            lambda:
            calls.append(True)
        )

        card.more_label.click()

        self.assertEqual(
            calls,
            [True],
        )

    def test_compact_still_hides_more_button(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        card.resize(
            300,
            250,
        )

        card._apply_responsive_state()

        self.assertEqual(
            card.responsive_state,
            "compact",
        )

        self.assertTrue(
            card.more_label.isHidden()
        )

    def test_large_shows_more_button(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        card.resize(
            720,
            620,
        )

        card._apply_responsive_state()

        self.assertEqual(
            card.responsive_state,
            "large",
        )

        self.assertFalse(
            card.more_label.isHidden()
        )

    def test_default_configure_still_rejects_locked_layout(
        self,
    ):
        layout = _Layout(
            locked=True,
            visible=True,
        )

        store = _Store()

        harness = SimpleNamespace(
            dashboard_layout_state=layout,
            sync_dashboard_layout_controls=(
                lambda: None
            ),
        )

        with patch.object(
            DashboardPage,
            "_spotify_playlist_dashboard_store",
            return_value=store,
        ):
            with patch.object(
                DashboardPage,
                "refresh_spotify_playlist_dashboard_card",
            ) as refresh:
                result = (
                    DashboardPage
                    .configure_spotify_playlist_dashboard_card(
                        harness,
                        "AbC123",
                    )
                )

        self.assertFalse(result)

        self.assertEqual(
            store.upserts,
            [],
        )

        refresh.assert_not_called()

    def test_locked_hidden_card_cannot_use_override(
        self,
    ):
        layout = _Layout(
            locked=True,
            visible=False,
        )

        store = _Store()

        harness = SimpleNamespace(
            dashboard_layout_state=layout,
            sync_dashboard_layout_controls=(
                lambda: None
            ),
        )

        with patch.object(
            DashboardPage,
            "_spotify_playlist_dashboard_store",
            return_value=store,
        ):
            with patch.object(
                DashboardPage,
                "refresh_spotify_playlist_dashboard_card",
            ) as refresh:
                result = (
                    DashboardPage
                    .configure_spotify_playlist_dashboard_card(
                        harness,
                        "AbC123",
                        allow_locked_existing=True,
                    )
                )

        self.assertFalse(result)

        self.assertEqual(
            store.upserts,
            [],
        )

        refresh.assert_not_called()

    def test_locked_visible_card_can_change_content(
        self,
    ):
        layout = _Layout(
            locked=True,
            visible=True,
        )

        store = _Store()

        sync_calls = []

        harness = SimpleNamespace(
            dashboard_layout_state=layout,
            sync_dashboard_layout_controls=(
                lambda:
                sync_calls.append(True)
            ),
        )

        with patch.object(
            DashboardPage,
            "_spotify_playlist_dashboard_store",
            return_value=store,
        ):
            with patch.object(
                DashboardPage,
                "refresh_spotify_playlist_dashboard_card",
                return_value=True,
            ) as refresh:
                result = (
                    DashboardPage
                    .configure_spotify_playlist_dashboard_card(
                        harness,
                        "Other456",
                        allow_locked_existing=True,
                    )
                )

        self.assertTrue(result)

        self.assertEqual(
            len(store.upserts),
            1,
        )

        self.assertEqual(
            store.upserts[0].card_id,
            SPOTIFY_PLAYLIST_DASHBOARD_CARD_CONFIG_ID,
        )

        self.assertEqual(
            store.upserts[0].playlist_id,
            "Other456",
        )

        refresh.assert_called_once_with(
            harness
        )

        self.assertEqual(
            sync_calls,
            [True],
        )

    def test_cancel_does_not_configure(
        self,
    ):
        harness = SimpleNamespace(
            theme_manager=SimpleNamespace(
                theme=lambda: {}
            )
        )

        _Dialog.accepted = False

        items = (
            _item(
                "playlist.other",
                "Other456",
            ),
        )

        with patch.object(
            DashboardPage,
            "_spotify_playlist_quick_access_items",
            return_value=items,
        ):
            with patch(
                "src.ui.dashboard."
                "QuickAccessPickerDialog",
                _Dialog,
            ):
                with patch.object(
                    DashboardPage,
                    "configure_spotify_playlist_dashboard_card",
                ) as configure:
                    result = (
                        DashboardPage
                        .change_spotify_playlist_dashboard_card(
                            harness
                        )
                    )

        self.assertFalse(result)

        configure.assert_not_called()

    def test_change_reuses_dynamic_playlist_items(
        self,
    ):
        harness = SimpleNamespace(
            theme_manager=SimpleNamespace(
                theme=lambda: {}
            )
        )

        items = (
            _item(
                "playlist.first",
                "First123",
            ),
            _item(
                "playlist.other",
                "Other456",
            ),
        )

        with patch.object(
            DashboardPage,
            "_spotify_playlist_quick_access_items",
            return_value=items,
        ):
            with patch(
                "src.ui.dashboard."
                "QuickAccessPickerDialog",
                _Dialog,
            ):
                with patch.object(
                    DashboardPage,
                    "configure_spotify_playlist_dashboard_card",
                    return_value=True,
                ):
                    result = (
                        DashboardPage
                        .change_spotify_playlist_dashboard_card(
                            harness
                        )
                    )

        self.assertTrue(result)

        self.assertEqual(
            _Dialog.dynamic_items,
            items,
        )

    def test_change_selected_playlist_uses_existing_configure_path(
        self,
    ):
        harness = SimpleNamespace(
            theme_manager=SimpleNamespace(
                theme=lambda: {}
            )
        )

        items = (
            _item(
                "playlist.other",
                "Other456",
            ),
        )

        with patch.object(
            DashboardPage,
            "_spotify_playlist_quick_access_items",
            return_value=items,
        ):
            with patch(
                "src.ui.dashboard."
                "QuickAccessPickerDialog",
                _Dialog,
            ):
                with patch.object(
                    DashboardPage,
                    "configure_spotify_playlist_dashboard_card",
                    return_value=True,
                ) as configure:
                    result = (
                        DashboardPage
                        .change_spotify_playlist_dashboard_card(
                            harness
                        )
                    )

        self.assertTrue(result)

        configure.assert_called_once_with(
            harness,
            "Other456",
            allow_locked_existing=True,
        )

    def test_unknown_selection_fails_closed(
        self,
    ):
        harness = SimpleNamespace(
            theme_manager=SimpleNamespace(
                theme=lambda: {}
            )
        )

        _Dialog.selected = (
            "playlist.missing"
        )

        items = (
            _item(
                "playlist.other",
                "Other456",
            ),
        )

        with patch.object(
            DashboardPage,
            "_spotify_playlist_quick_access_items",
            return_value=items,
        ):
            with patch(
                "src.ui.dashboard."
                "QuickAccessPickerDialog",
                _Dialog,
            ):
                with patch.object(
                    DashboardPage,
                    "configure_spotify_playlist_dashboard_card",
                ) as configure:
                    result = (
                        DashboardPage
                        .change_spotify_playlist_dashboard_card(
                            harness
                        )
                    )

        self.assertFalse(result)

        configure.assert_not_called()

    def test_add_card_does_not_use_locked_override(
        self,
    ):
        source = inspect.getsource(
            DashboardPage.add_spotify_playlist_card
        )

        self.assertNotIn(
            "allow_locked_existing",
            source,
        )

    def test_change_flow_contains_no_playback_logic(
        self,
    ):
        source = (
            inspect.getsource(
                DashboardPage
                .change_spotify_playlist_dashboard_card
            )
            .casefold()
        )

        forbidden = (
            "play_playlist_position",
            "play_playlist_track",
            "spotify_playback_runtime",
            "playback_control_requested",
            "qmediaplayer",
            "os.startfile",
            "sendinput",
            "mouse_event",
            "keybd_event",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_builder_signal_wiring_uses_class_dispatch(
        self,
    ):
        source = inspect.getsource(
            DashboardPage.build_spotify_playlist_card
        )

        self.assertIn(
            (
                "DashboardPage."
                "change_spotify_playlist_dashboard_card("
            ),
            source,
        )

        self.assertNotIn(
            (
                "self."
                "change_spotify_playlist_dashboard_card"
            ),
            source,
        )

    def test_more_qss_matches_button(
        self,
    ):
        source = inspect.getsource(
            SpotifyPlaylistDashboardCard
        )

        self.assertIn(
            (
                "QPushButton#"
                "spotifyPlaylistDashboardMore"
            ),
            source,
        )

        self.assertNotIn(
            (
                "QLabel#"
                "spotifyPlaylistDashboardMore"
            ),
            source,
        )


if __name__ == "__main__":
    unittest.main()
