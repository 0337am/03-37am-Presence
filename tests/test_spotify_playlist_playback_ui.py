from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.playlist_models import (
    SpotifyPlaylistSummary,
)
from src.ui.spotify_playlist_detail import (
    SpotifyPlaylistDetail,
    SpotifyPlaylistTrackRow,
)


TRACK_URI = (
    "spotify:track:"
    "4uLU6hMCjMI75M1A2tKUQC"
)


class FakePlaylistRuntime(
    QObject
):
    playlist_items_ready = pyqtSignal(
        str,
        object,
    )

    failed = pyqtSignal(
        str,
        str,
        str,
        str,
    )

    operation_finished = pyqtSignal(
        str,
        str,
    )

    busy_changed = pyqtSignal(
        bool
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.busy = False
        self.calls = []

    def load_playlist_items(
        self,
        playlist_id,
        *,
        limit=50,
        offset=0,
        market=None,
    ):
        self.calls.append(
            (
                playlist_id,
                limit,
                offset,
                market,
            )
        )


class FakePlaybackRuntime(
    QObject
):
    result_ready = pyqtSignal(
        object
    )

    failed = pyqtSignal(
        str,
        str,
    )

    busy_changed = pyqtSignal(
        bool
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.busy = False
        self.calls = []

    def play_playlist_track(
        self,
        playlist_id,
        spotify_uri,
    ):
        if self.busy:
            error = RuntimeError(
                "busy"
            )

            error.error_code = "busy"

            raise error

        self.calls.append(
            (
                playlist_id,
                spotify_uri,
            )
        )


def catalogue_item(
    *,
    title="Test Track",
    playable=True,
):
    return SimpleNamespace(
        is_local=False,
        local_available=None,
        unified_track=SimpleNamespace(
            title=title,
            artist="Test Artist",
            duration_ms=180000,
            spotify_uri=TRACK_URI,
            playable=playable,
        ),
    )


def local_item(
    *,
    available=True,
):
    return SimpleNamespace(
        is_local=True,
        local_available=available,
        unified_track=SimpleNamespace(
            title="Local Track",
            artist="Local Artist",
            duration_ms=180000,
            spotify_uri=(
                "spotify:local:"
                "Local+Artist:"
                "Album:"
                "Local+Track:180"
            ),
            playable=available,
        ),
    )


class SpotifyPlaylistPlaybackUiTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication(
                []
            )
        )

    def make_detail(
        self,
    ):
        playlist_runtime = (
            FakePlaylistRuntime()
        )

        playback_runtime = (
            FakePlaybackRuntime()
        )

        detail = SpotifyPlaylistDetail(
            playlist_runtime,
            playback_runtime=(
                playback_runtime
            ),
        )

        detail.set_playlist(
            SpotifyPlaylistSummary(
                spotify_id=(
                    "37i9dQZF1DXcBWIGoYBM5M"
                ),
                spotify_uri=(
                    "spotify:playlist:"
                    "37i9dQZF1DXcBWIGoYBM5M"
                ),
                name="Playback Test",
                owner_name="Tester",
                total_items=2,
                artwork_reference="",
            )
        )

        self.addCleanup(
            detail.deleteLater
        )

        return (
            detail,
            playback_runtime,
        )

    def test_catalogue_row_can_activate(
        self,
    ):
        item = catalogue_item()

        row = SpotifyPlaylistTrackRow(
            item,
            number=1,
        )

        self.addCleanup(
            row.deleteLater
        )

        observed = []

        row.activated.connect(
            observed.append
        )

        self.assertTrue(
            row.playback_available
        )

        self.assertTrue(
            row.activate()
        )

        self.assertEqual(
            observed,
            [
                item,
            ],
        )

    def test_available_local_row_does_not_activate_spotify_playback(
        self,
    ):
        item = local_item(
            available=True
        )

        row = SpotifyPlaylistTrackRow(
            item,
            number=1,
        )

        self.addCleanup(
            row.deleteLater
        )

        observed = []

        row.activated.connect(
            observed.append
        )

        self.assertFalse(
            row.playback_available
        )

        self.assertFalse(
            row.activate()
        )

        self.assertEqual(
            observed,
            [],
        )

    def test_unavailable_local_row_does_not_activate(
        self,
    ):
        item = local_item(
            available=False
        )

        row = SpotifyPlaylistTrackRow(
            item,
            number=1,
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertFalse(
            row.playback_available
        )

        self.assertFalse(
            row.activate()
        )

    def test_unplayable_catalogue_row_does_not_activate(
        self,
    ):
        row = SpotifyPlaylistTrackRow(
            catalogue_item(
                playable=False
            ),
            number=1,
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertFalse(
            row.playback_available
        )

        self.assertFalse(
            row.activate()
        )

    def test_detail_routes_catalogue_track_to_playback_runtime(
        self,
    ):
        (
            detail,
            playback,
        ) = self.make_detail()

        result = (
            detail
            ._handle_track_activated(
                catalogue_item(
                    title="Play Me"
                )
            )
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            playback.calls,
            [
                (
                    detail.playlist.spotify_id,
                    TRACK_URI,
                ),
            ],
        )

        self.assertEqual(
            detail.status_label.text(),
            "Starting Play Me...",
        )

    def test_detail_never_routes_local_track_to_spotify_runtime(
        self,
    ):
        (
            detail,
            playback,
        ) = self.make_detail()

        result = (
            detail
            ._handle_track_activated(
                local_item()
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            playback.calls,
            [],
        )

    def test_busy_playback_request_is_rejected_safely(
        self,
    ):
        (
            detail,
            playback,
        ) = self.make_detail()

        playback.busy = True

        result = (
            detail
            ._handle_track_activated(
                catalogue_item()
            )
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            playback.calls,
            [],
        )

        self.assertIn(
            "already running",
            detail.status_label.text(),
        )

    def test_ready_result_updates_status(
        self,
    ):
        (
            detail,
            _playback,
        ) = self.make_detail()

        detail._active_playback_title = (
            "Started Track"
        )

        detail.handle_playback_result(
            SimpleNamespace(
                ready=True,
                message=(
                    "Spotify playback started."
                ),
                retry_after_seconds=None,
            )
        )

        self.assertEqual(
            detail.status_label.text(),
            "Playing Started Track.",
        )

    def test_non_ready_result_uses_service_message_and_retry(
        self,
    ):
        (
            detail,
            _playback,
        ) = self.make_detail()

        detail._active_playback_title = (
            "Rate Limited Track"
        )

        detail.handle_playback_result(
            SimpleNamespace(
                ready=False,
                message=(
                    "Spotify is limiting playback "
                    "requests. Try again shortly."
                ),
                retry_after_seconds=7,
            )
        )

        self.assertIn(
            "limiting playback requests",
            detail.status_label.text(),
        )

        self.assertIn(
            "7 seconds",
            detail.status_label.text(),
        )

    def test_runtime_failure_uses_safe_message(
        self,
    ):
        (
            detail,
            _playback,
        ) = self.make_detail()

        detail.handle_playback_failure(
            "runtime_setup_failed",
            (
                "Spotify playback could "
                "not be prepared."
            ),
        )

        self.assertEqual(
            detail.status_label.text(),
            (
                "Spotify playback could "
                "not be prepared."
            ),
        )

    def test_main_window_owns_and_shuts_down_playback_runtime(
        self,
    ):
        root = (
            Path(__file__)
            .resolve()
            .parents[1]
        )

        source = (
            root
            / "src"
            / "ui"
            / "main_window.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            (
                "from src.spotify.playback_service "
                "import"
            ),
            source,
        )

        self.assertIn(
            "SpotifyPlaybackService",
            source,
        )

        self.assertIn(
            "SpotifyQtPlaybackRuntime",
            source,
        )

        self.assertIn(
            "self.spotify_playback_runtime",
            source,
        )

        self.assertIn(
            '"spotify_playback_runtime"',
            source,
        )

        self.assertIn(
            "playback_runtime=(",
            source,
        )

    def test_spotify_page_passes_runtime_to_playlist_detail(
        self,
    ):
        root = (
            Path(__file__)
            .resolve()
            .parents[1]
        )

        source = (
            root
            / "src"
            / "ui"
            / "spotify_page.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "playback_runtime=None",
            source,
        )

        self.assertIn(
            (
                "self.playback_runtime = ("
            ),
            source,
        )

        self.assertIn(
            (
                "playback_runtime=("
            ),
            source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
