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


if __name__ == "__main__":
    unittest.main()
