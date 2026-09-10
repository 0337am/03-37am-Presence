from __future__ import annotations

import dataclasses
import os
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication

from src.ui.spotify_playlist_dashboard_card import (
    SpotifyPlaylistDashboardCard,
    SpotifyPlaylistDashboardCardError,
    SpotifyPlaylistDashboardSnapshot,
    SpotifyPlaylistDashboardTrack,
    format_playlist_duration,
)


class SpotifyPlaylistDashboardCardTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def make_tracks(self):
        return (
            SpotifyPlaylistDashboardTrack(
                position=0,
                title="mellow",
                artists="northstar, julez",
                duration_seconds=95,
            ),
            SpotifyPlaylistDashboardTrack(
                position=1,
                title="Arctic Tundra (v1)",
                artists="Juice WRLD",
                duration_seconds=192,
                is_local=True,
            ),
            SpotifyPlaylistDashboardTrack(
                position=2,
                title="BAD!",
                artists="XXXTENTACION",
                duration_seconds=94,
            ),
        )

    def make_snapshot(self):
        return SpotifyPlaylistDashboardSnapshot.build(
            playlist_id="PlaylistABC123",
            title="It's late, go to sleep.",
            owner="northstar.",
            track_count=3,
            tracks=self.make_tracks(),
        )

    def test_duration_formats_minutes(self):
        self.assertEqual(
            format_playlist_duration(
                95
            ),
            "1:35",
        )

    def test_duration_formats_hours(self):
        self.assertEqual(
            format_playlist_duration(
                3723
            ),
            "1:02:03",
        )

    def test_duration_rejects_invalid_values(self):
        for value in (
            -1,
            True,
            1.5,
            "95",
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    SpotifyPlaylistDashboardCardError
                ):
                    format_playlist_duration(
                        value
                    )

    def test_track_is_frozen(self):
        track = self.make_tracks()[0]

        with self.assertRaises(
            dataclasses.FrozenInstanceError
        ):
            track.title = "changed"

    def test_track_exposes_display_number_and_duration(self):
        track = self.make_tracks()[1]

        self.assertEqual(
            track.display_number,
            "2",
        )

        self.assertEqual(
            track.display_duration,
            "3:12",
        )

    def test_track_rejects_invalid_position(self):
        with self.assertRaises(
            SpotifyPlaylistDashboardCardError
        ):
            SpotifyPlaylistDashboardTrack(
                position=-1,
                title="Track",
                artists="Artist",
                duration_seconds=1,
            )

    def test_snapshot_is_frozen(self):
        snapshot = self.make_snapshot()

        with self.assertRaises(
            dataclasses.FrozenInstanceError
        ):
            snapshot.title = "changed"

    def test_snapshot_normalises_playlist_id(self):
        snapshot = (
            SpotifyPlaylistDashboardSnapshot.build(
                playlist_id="  AbC123  ",
                title="Playlist",
                owner="Owner",
                track_count=0,
                tracks=(),
            )
        )

        self.assertEqual(
            snapshot.playlist_id,
            "AbC123",
        )

    def test_snapshot_rejects_count_smaller_than_rows(self):
        with self.assertRaises(
            SpotifyPlaylistDashboardCardError
        ):
            SpotifyPlaylistDashboardSnapshot.build(
                playlist_id="AbC123",
                title="Playlist",
                owner="Owner",
                track_count=1,
                tracks=self.make_tracks(),
            )

    def test_card_has_expected_structure(self):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        self.assertEqual(
            card.objectName(),
            "spotifyPlaylistDashboardCard",
        )

        self.assertEqual(
            card.header.objectName(),
            "spotifyPlaylistDashboardHeader",
        )

        self.assertEqual(
            card.scroll_area.objectName(),
            "spotifyPlaylistDashboardScroll",
        )

        self.assertEqual(
            card.artwork_label.objectName(),
            "spotifyPlaylistDashboardArtwork",
        )

    def test_static_play_control_is_inert(self):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        self.assertFalse(
            card.play_button.isEnabled()
        )

    def test_card_does_not_expose_skip_controls(self):
        card = (
            SpotifyPlaylistDashboardCard()
        )

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

    def test_scroll_viewport_has_explicit_theme_target(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        self.assertEqual(
            card.scroll_area
            .viewport()
            .objectName(),
            "spotifyPlaylistDashboardViewport",
        )

    def test_apply_theme_uses_dashboard_palette(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        theme = {
            "background": "#180b10",
            "card": "#3b1d2a",
            "card_alt": "#4a2535",
            "border": "#6b354a",
            "accent": "#ff7fa8",
            "text": "#fff5f8",
            "muted": "#d8aab9",
        }

        card.apply_theme(
            theme
        )

        stylesheet = (
            card.styleSheet()
            .casefold()
        )

        for value in theme.values():
            with self.subTest(
                value=value
            ):
                self.assertIn(
                    value.casefold(),
                    stylesheet,
                )

        self.assertIn(
            "qframe#spotifyplaylistdashboardcard",
            stylesheet,
        )

        self.assertIn(
            "qwidget#spotifyplaylistdashboardviewport",
            stylesheet,
        )

        self.assertIn(
            "qpushbutton#spotifyplaylistdashboardplaybutton",
            stylesheet,
        )

    def test_apply_theme_rejects_non_mapping_safely(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        before = card.styleSheet()

        card.apply_theme(
            None
        )

        self.assertEqual(
            card.styleSheet(),
            before,
        )

    def test_snapshot_updates_header(self):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        card.set_snapshot(
            self.make_snapshot()
        )

        self.assertEqual(
            card.title_label.text(),
            "It's late, go to sleep.",
        )

        self.assertEqual(
            card.owner_label.text(),
            "northstar.",
        )

        self.assertEqual(
            card.count_label.text(),
            "3 tracks",
        )

    def test_snapshot_builds_track_rows(self):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        card.set_snapshot(
            self.make_snapshot()
        )

        self.assertEqual(
            len(card.track_rows),
            3,
        )

        self.assertEqual(
            card.track_rows[0].title_label.text(),
            "mellow",
        )

        self.assertEqual(
            card.track_rows[2].duration_label.text(),
            "1:34",
        )

    def test_local_track_has_local_badge(self):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        card.set_snapshot(
            self.make_snapshot()
        )

        self.assertFalse(
            card.track_rows[0].local_badge.isVisible()
        )

        card.show()
        self.app.processEvents()

        self.assertTrue(
            card.track_rows[1].local_badge.isVisible()
        )

        card.hide()

    def test_unavailable_track_exposes_badge_property(self):
        track = (
            SpotifyPlaylistDashboardTrack(
                position=0,
                title="Unavailable",
                artists="Artist",
                duration_seconds=30,
                available=False,
            )
        )

        card = (
            SpotifyPlaylistDashboardCard()
        )

        card.set_snapshot(
            SpotifyPlaylistDashboardSnapshot.build(
                playlist_id="AbC123",
                title="Playlist",
                owner="Owner",
                track_count=1,
                tracks=(track,),
            )
        )

        self.assertFalse(
            card.track_rows[0].property(
                "available"
            )
        )

    def test_scroll_area_is_vertical_and_no_horizontal_scroll(self):
        card = (
            SpotifyPlaylistDashboardCard()
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

    def test_artwork_accepts_and_square_crops_pixmap(self):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        pixmap = QPixmap(
            300,
            180,
        )

        pixmap.fill(
            Qt.GlobalColor.darkCyan
        )

        self.assertTrue(
            card.set_artwork_pixmap(
                pixmap
            )
        )

        installed = (
            card.artwork_label.pixmap()
        )

        self.assertIsNotNone(
            installed
        )

        self.assertEqual(
            installed.width(),
            card.ARTWORK_SIZE,
        )

        self.assertEqual(
            installed.height(),
            card.ARTWORK_SIZE,
        )

    def test_clear_artwork_restores_placeholder(self):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        pixmap = QPixmap(
            100,
            100,
        )

        pixmap.fill(
            Qt.GlobalColor.black
        )

        card.set_artwork_pixmap(
            pixmap
        )

        card.clear_artwork()

        self.assertEqual(
            card.artwork_label.text(),
            "PLAYLIST",
        )

    def test_replacing_snapshot_replaces_rows(self):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        card.set_snapshot(
            self.make_snapshot()
        )

        self.assertEqual(
            len(card.track_rows),
            3,
        )

        card.set_snapshot(
            SpotifyPlaylistDashboardSnapshot.build(
                playlist_id="Other123",
                title="Other playlist",
                owner="Owner",
                track_count=1,
                tracks=(
                    SpotifyPlaylistDashboardTrack(
                        position=0,
                        title="Only track",
                        artists="Artist",
                        duration_seconds=42,
                    ),
                ),
            )
        )

        self.assertEqual(
            len(card.track_rows),
            1,
        )

        self.assertEqual(
            card.track_rows[0].title_label.text(),
            "Only track",
        )

    def test_clear_snapshot_restores_empty_state(self):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        card.set_snapshot(
            self.make_snapshot()
        )

        card.clear_snapshot()

        self.assertIsNone(
            card.snapshot
        )

        self.assertEqual(
            card.title_label.text(),
            "Choose a playlist",
        )

        self.assertEqual(
            len(card.track_rows),
            0,
        )

    def test_track_rows_are_owned_widgets_not_windows(self):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        card.set_snapshot(
            self.make_snapshot()
        )

        for row in card.track_rows:
            self.assertIs(
                row.parent(),
                card.track_container,
            )

            self.assertFalse(
                row.isWindow()
            )

    def test_source_owns_no_network_playback_or_polling(self):
        source = (
            Path(
                "src/ui/"
                "spotify_playlist_dashboard_card.py"
            )
            .read_text(
                encoding="utf-8"
            )
            .lower()
        )

        forbidden = (
            "requests",
            "urllib",
            "web_api",
            "access_token",
            "refresh_token",
            "client_secret",
            "oauth",
            "qmediaplayer",
            "os.startfile",
            "play_playlist_position",
            "play_playlist_track",
            "spotify_transport",
            "qtimer",
            "pypresence",
            "keyboard",
            "mouse_event",
        )

        for token in forbidden:
            with self.subTest(
                token=token
            ):
                self.assertNotIn(
                    token,
                    source,
                )

    def test_extending_same_playlist_reuses_existing_row_widgets(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        initial = (
            self.make_snapshot()
        )

        card.set_snapshot(
            initial
        )

        original_rows = (
            card.track_rows
        )

        extra_tracks = (
            SpotifyPlaylistDashboardTrack(
                position=3,
                title="fourth",
                artists="Artist Four",
                duration_seconds=121,
            ),
            SpotifyPlaylistDashboardTrack(
                position=4,
                title="fifth",
                artists="Artist Five",
                duration_seconds=122,
            ),
        )

        extended = (
            SpotifyPlaylistDashboardSnapshot
            .build(
                playlist_id=(
                    initial.playlist_id
                ),
                title=(
                    initial.title
                ),
                owner=(
                    initial.owner
                ),
                track_count=5,
                tracks=(
                    initial.tracks
                    + extra_tracks
                ),
            )
        )

        card.set_snapshot(
            extended
        )

        self.assertEqual(
            len(
                card.track_rows
            ),
            5,
        )

        for index in range(
            len(
                original_rows
            )
        ):
            self.assertIs(
                card.track_rows[
                    index
                ],
                original_rows[
                    index
                ],
            )

        self.assertEqual(
            card.track_rows[
                3
            ].title_label.text(),
            "fourth",
        )

        self.assertEqual(
            card.track_rows[
                4
            ].title_label.text(),
            "fifth",
        )

    def test_reapplying_identical_snapshot_does_not_rebuild_rows(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        snapshot = (
            self.make_snapshot()
        )

        card.set_snapshot(
            snapshot
        )

        original_rows = (
            card.track_rows
        )

        card.set_snapshot(
            snapshot
        )

        self.assertEqual(
            len(
                card.track_rows
            ),
            len(
                original_rows
            ),
        )

        for (
            current,
            original,
        ) in zip(
            card.track_rows,
            original_rows,
        ):
            self.assertIs(
                current,
                original,
            )

    def test_incremental_growth_keeps_every_row_owned_and_non_window(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        initial = (
            self.make_snapshot()
        )

        card.set_snapshot(
            initial
        )

        card.show()

        self.app.processEvents()

        extra = (
            SpotifyPlaylistDashboardTrack(
                position=3,
                title="fourth",
                artists="Artist",
                duration_seconds=90,
            ),
        )

        card.set_snapshot(
            SpotifyPlaylistDashboardSnapshot.build(
                playlist_id=(
                    initial.playlist_id
                ),
                title=(
                    initial.title
                ),
                owner=(
                    initial.owner
                ),
                track_count=4,
                tracks=(
                    initial.tracks
                    + extra
                ),
            )
        )

        self.app.processEvents()

        self.assertEqual(
            len(
                card.track_rows
            ),
            4,
        )

        for row in card.track_rows:
            self.assertIs(
                row.parent(),
                card.track_container,
            )

            self.assertFalse(
                row.isWindow()
            )

        card.hide()

    def test_badges_never_show_as_parentless_top_level_windows(
        self,
    ):
        from PyQt6.QtCore import (
            QEvent,
            QObject,
        )
        from PyQt6.QtWidgets import (
            QWidget,
        )
        from src.ui.spotify_playlist_dashboard_card import (
            SpotifyPlaylistDashboardTrackRow,
        )

        class ShowSpy(
            QObject
        ):

            def __init__(
                self,
            ):
                super().__init__()

                self.top_level_badge_shows = []

            def eventFilter(
                self,
                watched,
                event,
            ):
                if (
                    event.type()
                    == QEvent.Type.Show
                    and isinstance(
                        watched,
                        QWidget,
                    )
                    and watched.objectName()
                    in {
                        "spotifyPlaylistDashboardLocalBadge",
                        "spotifyPlaylistDashboardUnavailableBadge",
                    }
                    and watched.isWindow()
                ):
                    self.top_level_badge_shows.append(
                        watched.objectName()
                    )

                return False

        spy = ShowSpy()

        self.app.installEventFilter(
            spy
        )

        parent = QWidget()

        try:
            track = (
                SpotifyPlaylistDashboardTrack(
                    position=0,
                    title="Local unavailable test",
                    artists="Juice WRLD",
                    duration_seconds=120,
                    is_local=True,
                    available=False,
                )
            )

            row = (
                SpotifyPlaylistDashboardTrackRow(
                    track,
                    parent,
                )
            )

            self.assertIs(
                row.parentWidget(),
                parent,
            )

            self.assertIs(
                row.number_label.parentWidget(),
                row,
            )

            self.assertIs(
                row.local_badge.parentWidget(),
                row,
            )

            self.assertIs(
                row.unavailable_badge.parentWidget(),
                row,
            )

            self.assertIs(
                row.duration_label.parentWidget(),
                row,
            )

        finally:
            self.app.removeEventFilter(
                spy
            )

        self.assertEqual(
            spy.top_level_badge_shows,
            [],
        )


if __name__ == "__main__":
    unittest.main()
