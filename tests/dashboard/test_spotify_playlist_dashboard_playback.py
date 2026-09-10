from __future__ import annotations

import inspect
import os
import types
import unittest
from pathlib import Path


os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)


from PyQt6.QtCore import (
    Qt,
)
from PyQt6.QtTest import (
    QTest,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.ui.dashboard import (
    DashboardPage,
)
from src.ui.main_window import (
    MainWindow,
)
from src.ui.spotify_playlist_dashboard_card import (
    SpotifyPlaylistDashboardCard,
    SpotifyPlaylistDashboardSnapshot,
    SpotifyPlaylistDashboardTrack,
)


PLAYLIST_ID = "AbC123"


class FakePlaybackRuntime:

    def __init__(
        self,
        *,
        busy=False,
        result=None,
        error=None,
    ):
        self.busy = bool(
            busy
        )

        self.result = result
        self.error = error
        self.calls = []

    def play_playlist_position(
        self,
        playlist_id,
        position,
    ):
        if self.error is not None:
            raise self.error

        self.calls.append(
            (
                playlist_id,
                position,
            )
        )

        return self.result


class PlaybackHarness:

    def __init__(
        self,
        card,
        runtime=None,
    ):
        self.spotify_playlist_card = (
            card
        )

        self._spotify_playlist_dashboard_playback_runtime = (
            runtime
        )

        self.play_spotify_playlist_dashboard_track = (
            types.MethodType(
                DashboardPage
                .play_spotify_playlist_dashboard_track,
                self,
            )
        )


class SpotifyPlaylistDashboardPlaybackTests(
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

    def make_track(
        self,
        *,
        position=28,
        title="Track",
        is_local=False,
        available=True,
    ):
        return (
            SpotifyPlaylistDashboardTrack(
                position=position,
                title=title,
                artists="Artist",
                duration_seconds=180,
                is_local=is_local,
                available=available,
            )
        )

    def make_card(
        self,
        track,
    ):
        card = (
            SpotifyPlaylistDashboardCard()
        )

        card.resize(
            720,
            620,
        )

        card.set_snapshot(
            SpotifyPlaylistDashboardSnapshot.build(
                playlist_id=PLAYLIST_ID,
                title="Playback Test",
                owner="Tester",
                track_count=1,
                tracks=(
                    track,
                ),
            )
        )

        self.addCleanup(
            card.deleteLater
        )

        return card

    def route(
        self,
        track,
        runtime,
    ):
        card = self.make_card(
            track
        )

        harness = PlaybackHarness(
            card,
            runtime,
        )

        result = (
            DashboardPage
            .play_spotify_playlist_dashboard_track(
                harness,
                track,
            )
        )

        return (
            result,
            runtime,
            card,
        )

    def test_available_catalogue_row_uses_exact_raw_position(
        self,
    ):
        track = self.make_track(
            position=28,
            is_local=False,
        )

        runtime = (
            FakePlaybackRuntime()
        )

        result, runtime, _card = (
            self.route(
                track,
                runtime,
            )
        )

        self.assertTrue(
            result
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

    def test_available_local_row_uses_exact_raw_position(
        self,
    ):
        track = self.make_track(
            position=41,
            title="Local Track",
            is_local=True,
            available=True,
        )

        runtime = (
            FakePlaybackRuntime()
        )

        result, runtime, _card = (
            self.route(
                track,
                runtime,
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            runtime.calls,
            [
                (
                    PLAYLIST_ID,
                    41,
                ),
            ],
        )

    def test_unavailable_row_fails_closed(
        self,
    ):
        track = self.make_track(
            position=9,
            is_local=True,
            available=False,
        )

        runtime = (
            FakePlaybackRuntime()
        )

        result, runtime, _card = (
            self.route(
                track,
                runtime,
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_busy_runtime_fails_closed(
        self,
    ):
        track = self.make_track(
            position=5,
        )

        runtime = (
            FakePlaybackRuntime(
                busy=True
            )
        )

        result, runtime, _card = (
            self.route(
                track,
                runtime,
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_runtime_exception_fails_closed(
        self,
    ):
        track = self.make_track(
            position=7,
        )

        runtime = (
            FakePlaybackRuntime(
                error=RuntimeError(
                    "busy"
                )
            )
        )

        result, runtime, _card = (
            self.route(
                track,
                runtime,
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_explicit_runtime_rejection_fails_closed(
        self,
    ):
        track = self.make_track(
            position=8,
        )

        runtime = (
            FakePlaybackRuntime(
                result=False
            )
        )

        result, runtime, _card = (
            self.route(
                track,
                runtime,
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            runtime.calls,
            [
                (
                    PLAYLIST_ID,
                    8,
                ),
            ],
        )

    def test_stale_track_from_other_snapshot_is_rejected(
        self,
    ):
        visible = self.make_track(
            position=1,
            title="Visible",
        )

        stale = self.make_track(
            position=2,
            title="Stale",
        )

        card = self.make_card(
            visible
        )

        runtime = (
            FakePlaybackRuntime()
        )

        harness = PlaybackHarness(
            card,
            runtime,
        )

        result = (
            DashboardPage
            .play_spotify_playlist_dashboard_track(
                harness,
                stale,
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_row_mouse_click_emits_card_track_activation(
        self,
    ):
        track = self.make_track(
            position=14,
        )

        card = self.make_card(
            track
        )

        received = []

        card.track_activated.connect(
            received.append
        )

        card.show()

        self.app.processEvents()

        row = card.track_rows[0]

        self.assertTrue(
            row.title_label.testAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents
            )
        )

        QTest.mouseClick(
            row,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            row.rect().center(),
        )

        self.app.processEvents()

        self.assertEqual(
            received,
            [
                track,
            ],
        )

        card.hide()

    def test_unavailable_row_mouse_click_does_not_activate(
        self,
    ):
        track = self.make_track(
            position=15,
            available=False,
        )

        card = self.make_card(
            track
        )

        received = []

        card.track_activated.connect(
            received.append
        )

        card.show()

        self.app.processEvents()

        row = card.track_rows[0]

        QTest.mouseClick(
            row,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            row.rect().center(),
        )

        self.app.processEvents()

        self.assertEqual(
            received,
            [],
        )

        card.hide()

    def test_runtime_installer_connects_card_only_once(
        self,
    ):
        track = self.make_track(
            position=19,
        )

        card = self.make_card(
            track
        )

        runtime = (
            FakePlaybackRuntime()
        )

        harness = PlaybackHarness(
            card
        )

        first = (
            DashboardPage
            .install_spotify_playlist_dashboard_playback_runtime(
                harness,
                runtime,
            )
        )

        second = (
            DashboardPage
            .install_spotify_playlist_dashboard_playback_runtime(
                harness,
                runtime,
            )
        )

        self.assertTrue(
            first
        )

        self.assertTrue(
            second
        )

        card.track_activated.emit(
            track
        )

        self.assertEqual(
            runtime.calls,
            [
                (
                    PLAYLIST_ID,
                    19,
                ),
            ],
        )

    def test_main_window_installs_existing_shared_playback_runtime(
        self,
    ):
        source = inspect.getsource(
            MainWindow.build_pages
        )

        self.assertIn(
            (
                "install_spotify_playlist_"
                "dashboard_playback_runtime"
            ),
            source,
        )

        self.assertIn(
            "self.spotify_playback_runtime",
            source,
        )

    def test_header_play_control_remains_inert(
        self,
    ):
        track = self.make_track()

        card = self.make_card(
            track
        )

        self.assertFalse(
            card.play_button.isEnabled()
        )

    def test_card_owns_no_spotify_playback_or_auth_boundary(
        self,
    ):
        source = (
            Path(
                "src/ui/"
                "spotify_playlist_dashboard_card.py"
            )
            .read_text(
                encoding="utf-8"
            )
            .casefold()
        )

        forbidden = (
            "play_playlist_position",
            "play_playlist_track",
            "spotifywebapiclient",
            "access_token",
            "refresh_token",
            "client_secret",
            "requests.",
            "urllib",
            "os.startfile",
            "qmediaplayer",
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


if __name__ == "__main__":
    unittest.main()
