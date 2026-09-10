from __future__ import annotations

import inspect
import os
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtWidgets import QApplication

from src.ui.dashboard import DashboardPage
from src.ui.main_window import MainWindow
from src.ui.spotify_playlist_dashboard_card import (
    SpotifyPlaylistDashboardCard,
    SpotifyPlaylistDashboardSnapshot,
    SpotifyPlaylistDashboardTrack,
)


PLAYLIST_ID = "AbC123"


class FakeSignal:

    def __init__(
        self,
    ):
        self.slots = []
        self.emissions = []

    def connect(
        self,
        slot,
    ):
        self.slots.append(
            slot
        )

    def emit(
        self,
        *args,
    ):
        self.emissions.append(
            args
        )

        for slot in tuple(
            self.slots
        ):
            slot(
                *args
            )


class FakePlaybackRuntime:

    def __init__(
        self,
        *,
        busy=False,
        result=None,
    ):
        self.busy = bool(
            busy
        )

        self.result = result
        self.calls = []
        self.busy_changed = (
            FakeSignal()
        )

    def play_playlist_position(
        self,
        playlist_id,
        position,
    ):
        self.calls.append(
            (
                playlist_id,
                position,
            )
        )

        return self.result


class Harness:
    pass


class SpotifyPlaylistDashboardHeaderPlaybackTests(
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
        position=0,
        *,
        title="Target Song",
        artists="Target Artist",
        available=True,
        is_local=False,
    ):
        return (
            SpotifyPlaylistDashboardTrack(
                position=position,
                title=title,
                artists=artists,
                duration_seconds=180,
                available=available,
                is_local=is_local,
            )
        )

    def song(
        self,
        *,
        title="Target Song",
        artist="Target Artist",
        playing=True,
        source_app="Spotify.exe",
    ):
        return (
            SimpleNamespace(
                title=title,
                artist=artist,
                album="Album",
                playing=bool(
                    playing
                ),
                source_app=source_app,
            )
        )

    def make_harness(
        self,
        *tracks,
        busy=False,
        result=None,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        self.addCleanup(
            card.deleteLater
        )

        card.set_snapshot(
            SpotifyPlaylistDashboardSnapshot.build(
                playlist_id=PLAYLIST_ID,
                title="Header Test",
                owner="03:37am",
                track_count=len(
                    tracks
                ),
                tracks=tracks,
            )
        )

        runtime = (
            FakePlaybackRuntime(
                busy=busy,
                result=result,
            )
        )

        harness = (
            Harness()
        )

        harness.spotify_playlist_card = (
            card
        )

        harness._spotify_playlist_dashboard_playback_runtime = (
            runtime
        )

        harness.playback_control_requested = (
            FakeSignal()
        )

        harness.song = self.song(
            title="",
            artist="",
            playing=False,
            source_app="",
        )

        installed = (
            DashboardPage
            .install_spotify_playlist_dashboard_header_playback(
                harness,
                runtime,
            )
        )

        self.assertTrue(
            installed
        )

        return (
            harness,
            runtime,
            card,
            harness.playback_control_requested,
        )

    def confirm_song(
        self,
        harness,
        song,
    ):
        DashboardPage.handle_spotify_playlist_dashboard_song_update(
            harness,
            song,
        )

    def establish_active(
        self,
        harness,
        runtime,
        card,
        *,
        track=None,
        playing=True,
    ):
        if track is None:
            track = (
                card.snapshot
                .tracks[
                    0
                ]
            )

        accepted = (
            DashboardPage
            .play_spotify_playlist_dashboard_track(
                harness,
                track,
            )
        )

        self.assertTrue(
            accepted
        )

        current = self.song(
            title=(
                track.title
            ),
            artist=(
                track.artists.split(
                    ",",
                    1,
                )[
                    0
                ].strip()
            ),
            playing=playing,
        )

        self.confirm_song(
            harness,
            current,
        )

        self.assertEqual(
            getattr(
                harness,
                "_spotify_playlist_dashboard_active_playlist_id",
                "",
            ),
            PLAYLIST_ID,
        )

        return current

    def test_header_starts_first_available_raw_position(
        self,
    ):
        unavailable = self.track(
            position=0,
            title="Unavailable",
            available=False,
        )

        local = self.track(
            position=41,
            title="Local",
            artists="Juice WRLD",
            available=True,
            is_local=True,
        )

        (
            _harness,
            runtime,
            card,
            controls,
        ) = self.make_harness(
            unavailable,
            local,
        )

        self.assertTrue(
            card.play_button.isEnabled()
        )

        card.play_button.click()

        self.assertEqual(
            runtime.calls,
            [
                (
                    PLAYLIST_ID,
                    41,
                ),
            ],
        )

        self.assertEqual(
            controls.emissions,
            [],
        )

    def test_runtime_false_does_not_mark_pending_context(
        self,
    ):
        track = self.track(
            position=4
        )

        (
            harness,
            runtime,
            card,
            _controls,
        ) = self.make_harness(
            track,
            result=False,
        )

        card.play_button.click()

        self.assertEqual(
            runtime.calls,
            [
                (
                    PLAYLIST_ID,
                    4,
                ),
            ],
        )

        self.assertEqual(
            getattr(
                harness,
                "_spotify_playlist_dashboard_pending_playlist_id",
                "",
            ),
            "",
        )

    def test_accepted_row_is_pending_until_matching_media_truth(
        self,
    ):
        track = self.track(
            position=28
        )

        (
            harness,
            runtime,
            card,
            _controls,
        ) = self.make_harness(
            track
        )

        accepted = (
            DashboardPage
            .play_spotify_playlist_dashboard_track(
                harness,
                track,
            )
        )

        self.assertTrue(
            accepted
        )

        self.assertEqual(
            runtime.calls,
            [
                (
                    PLAYLIST_ID,
                    28,
                ),
            ],
        )

        self.assertEqual(
            getattr(
                harness,
                "_spotify_playlist_dashboard_active_playlist_id",
                "",
            ),
            "",
        )

        self.assertEqual(
            getattr(
                harness,
                "_spotify_playlist_dashboard_pending_playlist_id",
                "",
            ),
            PLAYLIST_ID,
        )

        self.assertEqual(
            card.play_button.toolTip(),
            "Play playlist",
        )

        self.confirm_song(
            harness,
            self.song(),
        )

        self.assertEqual(
            getattr(
                harness,
                "_spotify_playlist_dashboard_active_playlist_id",
                "",
            ),
            PLAYLIST_ID,
        )

        self.assertEqual(
            card.play_button.toolTip(),
            "Pause playlist",
        )

    def test_matching_startup_song_cannot_claim_context(
        self,
    ):
        track = self.track(
            position=9
        )

        (
            harness,
            runtime,
            card,
            controls,
        ) = self.make_harness(
            track
        )

        self.confirm_song(
            harness,
            self.song(
                playing=True
            ),
        )

        self.assertEqual(
            getattr(
                harness,
                "_spotify_playlist_dashboard_active_playlist_id",
                "",
            ),
            "",
        )

        self.assertEqual(
            card.play_button.toolTip(),
            "Play playlist",
        )

        card.play_button.click()

        self.assertEqual(
            runtime.calls,
            [
                (
                    PLAYLIST_ID,
                    9,
                ),
            ],
        )

        self.assertEqual(
            controls.emissions,
            [],
        )

    def test_duplicate_identity_fails_closed_for_active_trust(
        self,
    ):
        first = self.track(
            position=3
        )

        duplicate = self.track(
            position=11
        )

        (
            harness,
            _runtime,
            card,
            _controls,
        ) = self.make_harness(
            first,
            duplicate,
        )

        accepted = (
            DashboardPage
            .play_spotify_playlist_dashboard_track(
                harness,
                first,
            )
        )

        self.assertTrue(
            accepted
        )

        self.confirm_song(
            harness,
            self.song(),
        )

        self.assertEqual(
            getattr(
                harness,
                "_spotify_playlist_dashboard_active_playlist_id",
                "",
            ),
            "",
        )

        self.assertEqual(
            card.play_button.toolTip(),
            "Play playlist",
        )

    def test_active_playing_header_uses_existing_toggle_signal(
        self,
    ):
        track = self.track(
            position=5
        )

        (
            harness,
            runtime,
            card,
            controls,
        ) = self.make_harness(
            track
        )

        self.establish_active(
            harness,
            runtime,
            card,
            track=track,
            playing=True,
        )

        calls_before = list(
            runtime.calls
        )

        card.play_button.click()

        self.assertEqual(
            runtime.calls,
            calls_before,
        )

        self.assertEqual(
            controls.emissions,
            [
                (
                    "toggle_play_pause",
                    "Spotify.exe",
                    True,
                ),
            ],
        )

    def test_paused_active_header_requests_resume_without_restart(
        self,
    ):
        track = self.track(
            position=6
        )

        (
            harness,
            runtime,
            card,
            controls,
        ) = self.make_harness(
            track
        )

        self.establish_active(
            harness,
            runtime,
            card,
            track=track,
            playing=True,
        )

        self.confirm_song(
            harness,
            self.song(
                playing=False
            ),
        )

        self.assertEqual(
            card.play_button.toolTip(),
            "Play playlist",
        )

        calls_before = list(
            runtime.calls
        )

        card.play_button.click()

        self.assertEqual(
            runtime.calls,
            calls_before,
        )

        self.assertEqual(
            controls.emissions,
            [
                (
                    "toggle_play_pause",
                    "Spotify.exe",
                    False,
                ),
            ],
        )

    def test_active_context_survives_unique_next_track(
        self,
    ):
        first = self.track(
            position=1,
            title="First",
            artists="Artist One",
        )

        second = self.track(
            position=2,
            title="Second",
            artists="Artist Two",
        )

        (
            harness,
            runtime,
            card,
            _controls,
        ) = self.make_harness(
            first,
            second,
        )

        self.establish_active(
            harness,
            runtime,
            card,
            track=first,
        )

        self.confirm_song(
            harness,
            self.song(
                title="Second",
                artist="Artist Two",
                playing=True,
            ),
        )

        self.assertEqual(
            getattr(
                harness,
                "_spotify_playlist_dashboard_active_playlist_id",
                "",
            ),
            PLAYLIST_ID,
        )

        self.assertEqual(
            card.play_button.toolTip(),
            "Pause playlist",
        )

    def test_active_context_clears_when_song_leaves_playlist(
        self,
    ):
        track = self.track()

        (
            harness,
            runtime,
            card,
            _controls,
        ) = self.make_harness(
            track
        )

        self.establish_active(
            harness,
            runtime,
            card,
        )

        self.confirm_song(
            harness,
            self.song(
                title="Different",
                artist="Other",
                playing=True,
            ),
        )

        self.assertEqual(
            getattr(
                harness,
                "_spotify_playlist_dashboard_active_playlist_id",
                "",
            ),
            "",
        )

        self.assertEqual(
            card.play_button.toolTip(),
            "Play playlist",
        )

    def test_non_spotify_source_clears_active_context(
        self,
    ):
        track = self.track()

        (
            harness,
            runtime,
            card,
            _controls,
        ) = self.make_harness(
            track
        )

        self.establish_active(
            harness,
            runtime,
            card,
        )

        self.confirm_song(
            harness,
            self.song(
                source_app="vlc.exe",
                playing=True,
            ),
        )

        self.assertEqual(
            getattr(
                harness,
                "_spotify_playlist_dashboard_active_playlist_id",
                "",
            ),
            "",
        )

    def test_busy_runtime_disables_header(
        self,
    ):
        track = self.track()

        (
            _harness,
            runtime,
            card,
            _controls,
        ) = self.make_harness(
            track
        )

        runtime.busy = True
        runtime.busy_changed.emit(
            True
        )

        self.assertFalse(
            card.play_button.isEnabled()
        )

        runtime.busy = False
        runtime.busy_changed.emit(
            False
        )

        self.assertTrue(
            card.play_button.isEnabled()
        )

    def test_clear_snapshot_disables_header(
        self,
    ):
        track = self.track()

        (
            _harness,
            _runtime,
            card,
            _controls,
        ) = self.make_harness(
            track
        )

        self.assertTrue(
            card.play_button.isEnabled()
        )

        card.clear_snapshot()

        self.assertFalse(
            card.play_button.isEnabled()
        )

        self.assertEqual(
            card.play_button.toolTip(),
            "Play playlist",
        )

    def test_header_installer_is_idempotent(
        self,
    ):
        track = self.track(
            position=19
        )

        (
            harness,
            runtime,
            card,
            controls,
        ) = self.make_harness(
            track
        )

        second = (
            DashboardPage
            .install_spotify_playlist_dashboard_header_playback(
                harness,
                runtime,
            )
        )

        self.assertTrue(
            second
        )

        card.play_button.click()

        self.assertEqual(
            runtime.calls,
            [
                (
                    PLAYLIST_ID,
                    19,
                ),
            ],
        )

        self.assertEqual(
            controls.emissions,
            [],
        )

    def test_card_remains_ui_only_and_has_no_skip_controls(
        self,
    ):
        source = (
            inspect.getsource(
                SpotifyPlaylistDashboardCard
            )
            .casefold()
        )

        forbidden = (
            "spotifywebapiclient",
            "access_token",
            "refresh_token",
            "client_secret",
            "play_playlist_position",
            "pause_playback",
            "resume_playback",
            "qmediaplayer",
            "os.startfile",
            "setforegroundwindow",
            "mouse_event",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

        card = (
            SpotifyPlaylistDashboardCard()
        )

        self.addCleanup(
            card.deleteLater
        )

        for name in (
            "previous_button",
            "next_button",
            "playback_previous_button",
            "playback_next_button",
        ):
            self.assertFalse(
                hasattr(
                    card,
                    name,
                )
            )

    def test_main_window_wires_song_truth_and_header_runtime(
        self,
    ):
        handle_source = (
            inspect.getsource(
                MainWindow.handle_song_update
            )
        )

        self.assertIn(
            "handle_spotify_playlist_dashboard_song_update",
            handle_source,
        )

        root = (
            Path(__file__)
            .resolve()
            .parents[
                2
            ]
        )

        source = (
            root
            / "src"
            / "ui"
            / "main_window.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        row_marker = (
            "install_spotify_playlist_dashboard_"
            "playback_runtime"
        )

        header_marker = (
            "install_spotify_playlist_dashboard_"
            "header_playback"
        )

        self.assertEqual(
            source.count(
                header_marker
            ),
            1,
        )

        self.assertLess(
            source.index(
                row_marker
            ),
            source.index(
                header_marker
            ),
        )

    def test_header_runtime_installer_is_not_staticmethod(
        self,
    ):
        descriptor = inspect.getattr_static(
            DashboardPage,
            "install_spotify_playlist_dashboard_header_playback",
        )

        self.assertFalse(
            isinstance(
                descriptor,
                staticmethod,
            )
        )

        self.assertTrue(
            callable(
                getattr(
                    DashboardPage,
                    "install_spotify_playlist_dashboard_header_playback",
                    None,
                )
            )
        )

    def test_song_update_handler_is_not_staticmethod(
        self,
    ):
        descriptor = inspect.getattr_static(
            DashboardPage,
            "handle_spotify_playlist_dashboard_song_update",
        )

        self.assertFalse(
            isinstance(
                descriptor,
                staticmethod,
            )
        )

        self.assertTrue(
            callable(
                getattr(
                    DashboardPage,
                    "handle_spotify_playlist_dashboard_song_update",
                    None,
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
