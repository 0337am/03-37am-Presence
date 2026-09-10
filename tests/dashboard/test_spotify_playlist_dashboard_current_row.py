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

from src.ui.dashboard import DashboardPage
from src.ui.spotify_playlist_dashboard_card import (
    SpotifyPlaylistDashboardCard,
    SpotifyPlaylistDashboardSnapshot,
    SpotifyPlaylistDashboardTrack,
    SpotifyPlaylistDashboardTrackRow,
)


PLAYLIST_ID = "AbC123"


class FakePlaybackRuntime:

    def __init__(
        self,
        *,
        busy=False,
    ):
        self.busy = bool(
            busy
        )

    def play_playlist_position(
        self,
        playlist_id,
        position,
    ):
        del playlist_id
        del position


class CurrentRowHarness:
    pass


class SpotifyPlaylistDashboardCurrentRowTests(
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
        artists="Juice WRLD",
        is_local=False,
        available=True,
    ):
        return (
            SpotifyPlaylistDashboardTrack(
                position=position,
                title=(
                    title
                    or "Track "
                    + str(
                        position
                    )
                ),
                artists=artists,
                duration_seconds=180,
                is_local=is_local,
                available=available,
            )
        )

    def snapshot(
        self,
        *tracks,
        playlist_id=PLAYLIST_ID,
    ):
        return (
            SpotifyPlaylistDashboardSnapshot
            .build(
                playlist_id=playlist_id,
                title="Current Row Test",
                owner="03:37am",
                track_count=len(
                    tracks
                ),
                tracks=tracks,
            )
        )

    def song(
        self,
        *,
        title,
        artist="Juice WRLD",
        playing=True,
        source_app="Spotify.exe",
    ):
        return SimpleNamespace(
            title=title,
            artist=artist,
            album="Album",
            playing=bool(
                playing
            ),
            source_app=source_app,
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

        card.set_snapshot(
            self.snapshot(
                *tracks
            )
        )

        return card

    def harness(
        self,
        card,
        *,
        active=True,
        song=None,
    ):
        harness = (
            CurrentRowHarness()
        )

        harness.spotify_playlist_card = (
            card
        )

        harness._spotify_playlist_dashboard_playback_runtime = (
            FakePlaybackRuntime()
        )

        harness._spotify_playlist_dashboard_active_playlist_id = (
            PLAYLIST_ID
            if active
            else ""
        )

        harness._spotify_playlist_dashboard_pending_playlist_id = ""
        harness._spotify_playlist_dashboard_pending_track_identity = None
        harness._spotify_playlist_dashboard_pending_deadline = 0.0
        harness._spotify_playlist_dashboard_header_song = song

        return harness

    def sync(
        self,
        harness,
    ):
        DashboardPage.sync_spotify_playlist_dashboard_header_playback_state(
            harness
        )

    def theme(
        self,
    ):
        return {
            "background": "#101014",
            "card": "#18181f",
            "card_alt": "#202028",
            "border": "#34343e",
            "accent": "#abcdef",
            "text": "#f4f4f6",
            "muted": "#a6a6b1",
        }

    def test_row_defaults_to_not_current(
        self,
    ):
        row = (
            SpotifyPlaylistDashboardTrackRow(
                self.track(
                    4
                )
            )
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertFalse(
            row.current
        )

        self.assertFalse(
            bool(
                row.property(
                    "current"
                )
            )
        )

        self.assertFalse(
            bool(
                row.number_label.property(
                    "current"
                )
            )
        )

        self.assertFalse(
            bool(
                row.title_label.property(
                    "current"
                )
            )
        )

    def test_row_set_current_updates_existing_widget_in_place(
        self,
    ):
        row = (
            SpotifyPlaylistDashboardTrackRow(
                self.track(
                    7
                )
            )
        )

        self.addCleanup(
            row.deleteLater
        )

        identity = id(
            row
        )

        self.assertTrue(
            row.set_current(
                True
            )
        )

        self.assertEqual(
            id(
                row
            ),
            identity,
        )

        self.assertTrue(
            row.current
        )

        self.assertTrue(
            bool(
                row.property(
                    "current"
                )
            )
        )

        self.assertTrue(
            bool(
                row.number_label.property(
                    "current"
                )
            )
        )

        self.assertTrue(
            bool(
                row.title_label.property(
                    "current"
                )
            )
        )

        self.assertFalse(
            row.set_current(
                True
            )
        )

    def test_card_marks_exact_raw_position(
        self,
    ):
        card = self.card(
            self.track(
                4
            ),
            self.track(
                28
            ),
        )

        self.assertTrue(
            card.set_current_position(
                28
            )
        )

        self.assertEqual(
            card.current_position,
            28,
        )

        self.assertFalse(
            card.track_rows[
                0
            ].current
        )

        self.assertTrue(
            card.track_rows[
                1
            ].current
        )

    def test_changing_current_position_clears_old_row(
        self,
    ):
        card = self.card(
            self.track(
                2
            ),
            self.track(
                6
            ),
        )

        card.set_current_position(
            2
        )

        card.set_current_position(
            6
        )

        self.assertFalse(
            card.track_rows[
                0
            ].current
        )

        self.assertTrue(
            card.track_rows[
                1
            ].current
        )

    def test_none_clears_current_row(
        self,
    ):
        card = self.card(
            self.track(
                3
            )
        )

        card.set_current_position(
            3
        )

        card.set_current_position(
            None
        )

        self.assertIsNone(
            card.current_position
        )

        self.assertFalse(
            card.track_rows[
                0
            ].current
        )

    def test_invalid_position_fails_closed(
        self,
    ):
        card = self.card(
            self.track(
                1
            )
        )

        for invalid in (
            True,
            False,
            -1,
            1.5,
            "1",
        ):
            with self.subTest(
                invalid=invalid
            ):
                card.set_current_position(
                    1
                )

                card.set_current_position(
                    invalid
                )

                self.assertIsNone(
                    card.current_position
                )

                self.assertFalse(
                    card.track_rows[
                        0
                    ].current
                )

    def test_initial_replace_row_inherits_remembered_position(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        self.addCleanup(
            card.deleteLater
        )

        card.set_current_position(
            5
        )

        card.set_snapshot(
            self.snapshot(
                self.track(
                    5,
                    title="Initial Track",
                )
            )
        )

        self.assertEqual(
            card.current_position,
            5,
        )

        self.assertTrue(
            card.track_rows[
                0
            ].current
        )

    def test_same_playlist_growth_reveals_remembered_position(
        self,
    ):
        first = self.track(
            0
        )

        second = self.track(
            1
        )

        later = self.track(
            2
        )

        card = self.card(
            first,
            second,
        )

        original_rows = (
            card.track_rows
        )

        card.set_current_position(
            2
        )

        self.assertFalse(
            any(
                row.current
                for row
                in card.track_rows
            )
        )

        card.set_snapshot(
            self.snapshot(
                first,
                second,
                later,
            )
        )

        self.assertIs(
            card.track_rows[
                0
            ],
            original_rows[
                0
            ],
        )

        self.assertIs(
            card.track_rows[
                1
            ],
            original_rows[
                1
            ],
        )

        self.assertEqual(
            len(
                card.track_rows
            ),
            3,
        )

        self.assertTrue(
            card.track_rows[
                2
            ].current
        )

        self.assertEqual(
            card.current_position,
            2,
        )

    def test_incremental_new_row_inherits_current_at_construction(
        self,
    ):
        first = self.track(
            0
        )

        card = self.card(
            first
        )

        card.set_current_position(
            5
        )

        card.set_snapshot(
            self.snapshot(
                first,
                self.track(
                    5,
                    title="Later Page Track",
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
            ].track.position,
            5,
        )

        self.assertTrue(
            card.track_rows[
                1
            ].current
        )

    def test_replacing_playlist_clears_old_current_position(
        self,
    ):
        card = self.card(
            self.track(
                4
            )
        )

        card.set_current_position(
            4
        )

        card.set_snapshot(
            self.snapshot(
                self.track(
                    4,
                    title="Other Song",
                ),
                playlist_id="Other123",
            )
        )

        self.assertIsNone(
            card.current_position
        )

        self.assertFalse(
            card.track_rows[
                0
            ].current
        )

    def test_clear_snapshot_clears_current_position(
        self,
    ):
        card = self.card(
            self.track(
                9
            )
        )

        card.set_current_position(
            9
        )

        card.clear_snapshot()

        self.assertIsNone(
            card.current_position
        )

        self.assertEqual(
            card.track_rows,
            (),
        )

    def test_trusted_playing_song_marks_unique_row(
        self,
    ):
        card = self.card(
            self.track(
                5,
                title="First",
            ),
            self.track(
                11,
                title="Second",
            ),
        )

        harness = self.harness(
            card,
            song=self.song(
                title="Second",
                playing=True,
            ),
        )

        self.sync(
            harness
        )

        self.assertEqual(
            card.current_position,
            11,
        )

        self.assertFalse(
            card.track_rows[
                0
            ].current
        )

        self.assertTrue(
            card.track_rows[
                1
            ].current
        )

    def test_trusted_paused_song_remains_current(
        self,
    ):
        card = self.card(
            self.track(
                28,
                title="Paused Local",
                is_local=True,
            )
        )

        harness = self.harness(
            card,
            song=self.song(
                title="Paused Local",
                playing=False,
            ),
        )

        self.sync(
            harness
        )

        self.assertEqual(
            card.current_position,
            28,
        )

        self.assertTrue(
            card.track_rows[
                0
            ].current
        )

        self.assertEqual(
            card.play_button.toolTip(),
            "Play playlist",
        )

    def test_available_local_track_can_be_current(
        self,
    ):
        card = self.card(
            self.track(
                41,
                title="Local Song",
                is_local=True,
                available=True,
            )
        )

        harness = self.harness(
            card,
            song=self.song(
                title="Local Song",
                playing=True,
            ),
        )

        self.sync(
            harness
        )

        self.assertEqual(
            card.current_position,
            41,
        )

        self.assertTrue(
            card.track_rows[
                0
            ].current
        )

    def test_matching_song_without_trusted_playlist_does_not_mark_row(
        self,
    ):
        card = self.card(
            self.track(
                7,
                title="Startup Match",
            )
        )

        harness = self.harness(
            card,
            active=False,
            song=self.song(
                title="Startup Match",
                playing=True,
            ),
        )

        self.sync(
            harness
        )

        self.assertIsNone(
            card.current_position
        )

        self.assertFalse(
            card.track_rows[
                0
            ].current
        )

    def test_duplicate_identity_fails_closed_visually(
        self,
    ):
        card = self.card(
            self.track(
                3,
                title="Duplicate",
            ),
            self.track(
                12,
                title="Duplicate",
            ),
        )

        harness = self.harness(
            card,
            song=self.song(
                title="Duplicate",
                playing=True,
            ),
        )

        self.sync(
            harness
        )

        self.assertIsNone(
            card.current_position
        )

        self.assertFalse(
            any(
                row.current
                for row
                in card.track_rows
            )
        )

        self.assertEqual(
            getattr(
                harness,
                "_spotify_playlist_dashboard_active_playlist_id",
                "",
            ),
            "",
        )

    def test_next_song_moves_current_row(
        self,
    ):
        card = self.card(
            self.track(
                1,
                title="First",
            ),
            self.track(
                2,
                title="Second",
            ),
        )

        harness = self.harness(
            card,
            song=self.song(
                title="First",
                playing=True,
            ),
        )

        self.sync(
            harness
        )

        self.assertEqual(
            card.current_position,
            1,
        )

        harness._spotify_playlist_dashboard_header_song = (
            self.song(
                title="Second",
                playing=True,
            )
        )

        self.sync(
            harness
        )

        self.assertEqual(
            card.current_position,
            2,
        )

        self.assertFalse(
            card.track_rows[
                0
            ].current
        )

        self.assertTrue(
            card.track_rows[
                1
            ].current
        )

    def test_leaving_playlist_clears_current_row(
        self,
    ):
        card = self.card(
            self.track(
                8,
                title="Playlist Song",
            )
        )

        harness = self.harness(
            card,
            song=self.song(
                title="Playlist Song",
                playing=True,
            ),
        )

        self.sync(
            harness
        )

        self.assertEqual(
            card.current_position,
            8,
        )

        harness._spotify_playlist_dashboard_header_song = (
            self.song(
                title="Outside Song",
                playing=True,
            )
        )

        self.sync(
            harness
        )

        self.assertIsNone(
            card.current_position
        )

        self.assertFalse(
            card.track_rows[
                0
            ].current
        )

    def test_theme_contains_current_row_accent_selectors(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        self.addCleanup(
            card.deleteLater
        )

        theme = self.theme()

        card.apply_theme(
            theme
        )

        style = (
            card.styleSheet()
        )

        self.assertIn(
            (
                'QFrame#spotifyPlaylistDashboardTrackRow'
                '[current="true"]'
            ),
            style,
        )

        self.assertIn(
            (
                'QLabel#spotifyPlaylistDashboardTrackTitle'
                '[current="true"]'
            ),
            style,
        )

        self.assertIn(
            (
                'QLabel#spotifyPlaylistDashboardTrackNumber'
                '[current="true"]'
            ),
            style,
        )

        self.assertIn(
            theme[
                "accent"
            ],
            style,
        )

    def test_reapplying_theme_does_not_duplicate_current_qss(
        self,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        self.addCleanup(
            card.deleteLater
        )

        theme = self.theme()

        selector = (
            'QFrame#spotifyPlaylistDashboardTrackRow'
            '[current="true"]'
        )

        card.apply_theme(
            theme
        )

        first = (
            card.styleSheet()
        )

        card.apply_theme(
            theme
        )

        second = (
            card.styleSheet()
        )

        self.assertEqual(
            first.count(
                selector
            ),
            1,
        )

        self.assertEqual(
            second.count(
                selector
            ),
            1,
        )

    def test_current_row_update_does_not_replace_existing_rows(
        self,
    ):
        card = self.card(
            self.track(
                1
            ),
            self.track(
                2
            ),
        )

        rows = (
            card.track_rows
        )

        card.set_current_position(
            1
        )

        card.set_current_position(
            2
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

    def test_card_current_row_surface_remains_ui_only(
        self,
    ):
        source = (
            inspect.getsource(
                SpotifyPlaylistDashboardCard
            )
            + inspect.getsource(
                SpotifyPlaylistDashboardTrackRow
            )
        ).casefold()

        forbidden = (
            "qtimer",
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
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_dashboard_current_position_reuses_b05_truth_helpers(
        self,
    ):
        source = inspect.getsource(
            DashboardPage
            ._spotify_playlist_dashboard_current_track_position
        )

        self.assertIn(
            (
                "_spotify_playlist_dashboard_"
                "song_belongs_to_snapshot"
            ),
            source,
        )

        self.assertIn(
            (
                "_spotify_playlist_dashboard_"
                "track_identity"
            ),
            source,
        )

        self.assertIn(
            (
                "_spotify_playlist_dashboard_"
                "song_matches_identity"
            ),
            source,
        )


if __name__ == "__main__":
    unittest.main()
