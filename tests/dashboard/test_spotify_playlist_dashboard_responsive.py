from __future__ import annotations

import inspect
import os
import unittest
from types import SimpleNamespace


os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QSizePolicy,
)

from src.ui.dashboard import DashboardPage
from src.ui.spotify_playlist_dashboard_card import (
    SpotifyPlaylistDashboardCard,
    SpotifyPlaylistDashboardSnapshot,
    SpotifyPlaylistDashboardTrack,
)


class SpotifyPlaylistDashboardResponsiveTests(
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

    def track(
        self,
        position,
        *,
        title=None,
        local=False,
        available=True,
    ):
        return SpotifyPlaylistDashboardTrack(
            position=position,
            title=(
                title
                or f"Track {position}"
            ),
            artists="Juice WRLD",
            duration_seconds=180,
            is_local=local,
            available=available,
        )

    def snapshot(
        self,
        *tracks,
    ):
        return (
            SpotifyPlaylistDashboardSnapshot
            .build(
                playlist_id="AbC123",
                title="Responsive Playlist",
                owner="03:37am",
                track_count=len(
                    tracks
                ),
                tracks=tracks,
            )
        )

    def card(
        self,
        *tracks,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        self.addCleanup(
            card.deleteLater
        )

        if tracks:
            card.set_snapshot(
                self.snapshot(
                    *tracks
                )
            )

        return card

    def resize(
        self,
        card,
        width,
        height,
    ):
        card.resize(
            width,
            height,
        )

        card._apply_responsive_state()

        self.app.processEvents()

    def test_card_has_useful_explicit_minimum(
        self,
    ):
        card = self.card()

        self.assertEqual(
            card.minimumWidth(),
            260,
        )

        self.assertEqual(
            card.minimumHeight(),
            220,
        )

    def test_compact_state_uses_small_header_controls(
        self,
    ):
        card = self.card(
            self.track(
                0
            )
        )

        self.resize(
            card,
            320,
            260,
        )

        self.assertEqual(
            card.responsive_state,
            "compact",
        )

        self.assertEqual(
            card.artwork_label.width(),
            64,
        )

        self.assertEqual(
            card.play_button.width(),
            40,
        )

        self.assertTrue(
            card.owner_label.isHidden()
        )

        self.assertTrue(
            card.more_label.isHidden()
        )

        self.assertFalse(
            card.count_label.isHidden()
        )

    def test_compact_row_hides_only_duration(
        self,
    ):
        card = self.card(
            self.track(
                0,
                local=True,
            ),
            self.track(
                1,
                available=False,
            ),
        )

        self.resize(
            card,
            320,
            260,
        )

        local_row = (
            card.track_rows[
                0
            ]
        )

        unavailable_row = (
            card.track_rows[
                1
            ]
        )

        self.assertEqual(
            local_row.responsive_state,
            "compact",
        )

        self.assertTrue(
            local_row.duration_label.isHidden()
        )

        self.assertFalse(
            local_row.local_badge.isHidden()
        )

        self.assertFalse(
            unavailable_row
            .unavailable_badge
            .isHidden()
        )

    def test_medium_state_restores_secondary_metadata(
        self,
    ):
        card = self.card(
            self.track(
                0
            )
        )

        self.resize(
            card,
            440,
            360,
        )

        self.assertEqual(
            card.responsive_state,
            "medium",
        )

        self.assertEqual(
            card.artwork_label.width(),
            84,
        )

        self.assertEqual(
            card.play_button.width(),
            46,
        )

        self.assertFalse(
            card.owner_label.isHidden()
        )

        self.assertFalse(
            card.more_label.isHidden()
        )

        self.assertFalse(
            card.track_rows[
                0
            ].duration_label.isHidden()
        )

    def test_large_state_restores_original_header_geometry(
        self,
    ):
        card = self.card(
            self.track(
                0
            )
        )

        original_artwork = (
            card._capture_responsive_defaults()[
                "artwork_size"
            ]
        )

        original_play = (
            card._capture_responsive_defaults()[
                "play_size"
            ]
        )

        self.resize(
            card,
            320,
            260,
        )

        self.resize(
            card,
            720,
            620,
        )

        self.assertEqual(
            card.responsive_state,
            "large",
        )

        self.assertEqual(
            (
                card.artwork_label.width(),
                card.artwork_label.height(),
            ),
            original_artwork,
        )

        self.assertEqual(
            (
                card.play_button.width(),
                card.play_button.height(),
            ),
            original_play,
        )

        self.assertFalse(
            card.owner_label.isHidden()
        )

        self.assertFalse(
            card.more_label.isHidden()
        )

        self.assertFalse(
            card.track_rows[
                0
            ].duration_label.isHidden()
        )

    def test_short_height_alone_enters_compact_state(
        self,
    ):
        card = self.card(
            self.track(
                0
            )
        )

        self.resize(
            card,
            700,
            260,
        )

        self.assertEqual(
            card.responsive_state,
            "compact",
        )

    def test_medium_height_can_trigger_medium_state(
        self,
    ):
        card = self.card(
            self.track(
                0
            )
        )

        self.resize(
            card,
            700,
            360,
        )

        self.assertEqual(
            card.responsive_state,
            "medium",
        )

    def test_existing_rows_change_density_in_place(
        self,
    ):
        card = self.card(
            self.track(
                0
            ),
            self.track(
                1
            ),
        )

        rows = card.track_rows

        self.resize(
            card,
            320,
            260,
        )

        self.resize(
            card,
            720,
            620,
        )

        self.assertIs(
            card.track_rows[
                0
            ],
            rows[
                0
            ],
        )

        self.assertIs(
            card.track_rows[
                1
            ],
            rows[
                1
            ],
        )

        self.assertEqual(
            card.track_rows[
                0
            ].responsive_state,
            "large",
        )

    def test_paginated_row_inherits_current_density(
        self,
    ):
        first = self.track(
            0
        )

        card = self.card(
            first
        )

        self.resize(
            card,
            320,
            260,
        )

        card.set_snapshot(
            self.snapshot(
                first,
                self.track(
                    1
                ),
            )
        )

        self.assertEqual(
            len(
                card.track_rows
            ),
            2,
        )

        self.assertEqual(
            card.track_rows[
                1
            ].responsive_state,
            "compact",
        )

        self.assertTrue(
            card.track_rows[
                1
            ].duration_label.isHidden()
        )

    def test_replacement_rows_inherit_current_density(
        self,
    ):
        card = self.card()

        self.resize(
            card,
            320,
            260,
        )

        card.set_snapshot(
            self.snapshot(
                self.track(
                    4
                )
            )
        )

        self.assertEqual(
            card.track_rows[
                0
            ].responsive_state,
            "compact",
        )

    def test_current_row_state_survives_density_changes(
        self,
    ):
        card = self.card(
            self.track(
                0
            ),
            self.track(
                8
            ),
        )

        card.set_current_position(
            8
        )

        self.resize(
            card,
            320,
            260,
        )

        self.assertTrue(
            card.track_rows[
                1
            ].current
        )

        self.resize(
            card,
            720,
            620,
        )

        self.assertTrue(
            card.track_rows[
                1
            ].current
        )

        self.assertEqual(
            card.current_position,
            8,
        )

    def test_playback_button_state_survives_resize(
        self,
    ):
        card = self.card(
            self.track(
                0
            )
        )

        card.set_playback_state(
            enabled=True,
            playing=True,
        )

        self.resize(
            card,
            320,
            260,
        )

        self.assertTrue(
            card.play_button.isEnabled()
        )

        self.assertEqual(
            card.play_button.toolTip(),
            "Pause playlist",
        )

        card.set_playback_state(
            enabled=True,
            playing=False,
        )

        self.resize(
            card,
            440,
            360,
        )

        self.assertTrue(
            card.play_button.isEnabled()
        )

        self.assertEqual(
            card.play_button.toolTip(),
            "Play playlist",
        )

    def test_scroll_contract_is_preserved(
        self,
    ):
        card = self.card(
            self.track(
                0
            )
        )

        self.resize(
            card,
            320,
            260,
        )

        self.assertTrue(
            card.scroll_area.widgetResizable()
        )

        self.assertEqual(
            card.scroll_area
            .horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )

        self.assertEqual(
            card.scroll_area
            .verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )

    def test_taller_card_gives_scroll_body_more_room(
        self,
    ):
        tracks = tuple(
            self.track(
                index
            )
            for index in range(
                12
            )
        )

        card = self.card(
            *tracks
        )

        card.show()

        self.resize(
            card,
            440,
            300,
        )

        short_height = (
            card.scroll_area.height()
        )

        self.resize(
            card,
            440,
            620,
        )

        tall_height = (
            card.scroll_area.height()
        )

        card.hide()

        self.assertGreater(
            tall_height,
            short_height,
        )

    def test_text_labels_can_yield_horizontal_space(
        self,
    ):
        card = self.card(
            self.track(
                0,
                title=(
                    "A deliberately very long playlist "
                    "row title for responsive sizing"
                ),
            )
        )

        self.resize(
            card,
            320,
            260,
        )

        row = (
            card.track_rows[
                0
            ]
        )

        self.assertEqual(
            row.title_label
            .sizePolicy()
            .horizontalPolicy(),
            QSizePolicy.Policy.Ignored,
        )

        self.assertEqual(
            row.artist_label
            .sizePolicy()
            .horizontalPolicy(),
            QSizePolicy.Policy.Ignored,
        )

        self.assertEqual(
            card.title_label
            .sizePolicy()
            .horizontalPolicy(),
            QSizePolicy.Policy.Ignored,
        )

    def test_dashboard_resize_engine_uses_playlist_explicit_minimum(
        self,
    ):
        card = self.card()

        harness = SimpleNamespace(
            recent_card=None,
            quick_access_card=None,
            spotify_playlist_card=card,
        )

        minimum = (
            DashboardPage
            .dashboard_minimum_card_size(
                harness,
                card,
            )
        )

        self.assertEqual(
            minimum,
            (
                260,
                220,
            ),
        )

    def test_card_has_no_playlist_skip_controls(
        self,
    ):
        card = self.card()

        self.assertFalse(
            hasattr(
                card,
                "previous_button",
            )
        )

        self.assertFalse(
            hasattr(
                card,
                "next_button",
            )
        )

    def test_responsive_code_is_presentation_only(
        self,
    ):
        card_source = (
            inspect.getsource(
                SpotifyPlaylistDashboardCard
                ._apply_responsive_state
            )
            + inspect.getsource(
                SpotifyPlaylistDashboardCard
                ._apply_responsive_to_row
            )
        ).casefold()

        row_source = (
            inspect.getsource(
                type(
                    self.card(
                        self.track(
                            0
                        )
                    )
                    .track_rows[
                        0
                    ]
                )
                .set_responsive_state
            )
            .casefold()
        )

        source = (
            card_source
            + "\n"
            + row_source
        )

        forbidden = (
            "spotifywebapiclient",
            "access_token",
            "refresh_token",
            "client_secret",
            "play_playlist_position",
            "play_playlist_track",
            "pause_playback",
            "resume_playback",
            "qmediaplayer",
            "os.startfile",
            "sendinput",
            "setforegroundwindow",
            "mouse_event",
            "keybd_event",
            "qtimer",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )


if __name__ == "__main__":
    unittest.main()
