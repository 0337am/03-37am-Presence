from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.liked_songs_service import (
    SpotifyLikedSongsServiceResult,
    SpotifyLikedSongsServiceStatus,
)
from src.spotify.playlist_models import (
    spotify_playlist_items_page_from_payload,
)
from src.ui.spotify_liked_songs_detail import (
    SPOTIFY_LIKED_SONGS_PAGE_LIMIT,
    SpotifyLikedSongsDetail,
)
from src.ui.spotify_playlist_widgets import (
    SpotifyLikedSongsCard,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


TRACK_ID = (
    "0123456789ABCDEFGHIJKL"
)

TRACK_URI = (
    "spotify:track:"
    + TRACK_ID
)


class FakeLikedRuntime(
    QObject
):
    summary_ready = pyqtSignal(object)
    tracks_ready = pyqtSignal(object)
    failed = pyqtSignal(str, str)
    busy_changed = pyqtSignal(bool)
    operation_started = pyqtSignal()
    operation_finished = pyqtSignal()

    def __init__(
        self,
    ):
        super().__init__()

        self.busy = False
        self.summary_calls = 0
        self.track_calls = []
        self.include_context_calls = []

    def load_summary(
        self,
    ):
        self.summary_calls += 1

    def load_tracks_page(
        self,
        *,
        limit=50,
        offset=0,
        include_context=False,
    ):
        self.track_calls.append(
            (
                limit,
                offset,
            )
        )

        self.include_context_calls.append(
            bool(
                include_context
            )
        )


class FakePlaybackRuntime(
    QObject
):
    result_ready = pyqtSignal(object)
    failed = pyqtSignal(str, str)

    def __init__(
        self,
    ):
        super().__init__()

        self.busy = False
        self.calls = []
        self.context_calls = []

    def play_track(
        self,
        spotify_uri,
    ):
        self.calls.append(
            spotify_uri
        )

    def play_playlist_track(
        self,
        playlist_id,
        spotify_uri,
    ):
        self.context_calls.append(
            (
                playlist_id,
                spotify_uri,
            )
        )


def payload(
    *,
    offset=0,
    limit=50,
    total=1,
    title="Saved Track",
):
    return {
        "offset": offset,
        "limit": limit,
        "total": total,
        "items": [
            {
                "added_at": (
                    "2026-08-10T00:00:00Z"
                ),
                "track": {
                    "type": "track",
                    "name": title,
                    "artists": [
                        {
                            "name": (
                                "Saved Artist"
                            ),
                        },
                    ],
                    "album": {
                        "name": (
                            "Saved Album"
                        ),
                        "images": [],
                    },
                    "duration_ms": 180000,
                    "id": TRACK_ID,
                    "uri": TRACK_URI,
                    "is_local": False,
                    "is_playable": True,
                },
            },
        ],
    }


def result(
    *,
    offset=0,
    limit=50,
    total=1,
    title="Saved Track",
    context_playlist_id=None,
):
    page = (
        spotify_playlist_items_page_from_payload(
            payload(
                offset=offset,
                limit=limit,
                total=total,
                title=title,
            )
        )
    )

    return SpotifyLikedSongsServiceResult(
        status=(
            SpotifyLikedSongsServiceStatus.READY
        ),
        total=total,
        page=page,
        context_playlist_id=(
            context_playlist_id
        ),
    )


class SpotifyLikedSongsDetailTests(
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
        liked = FakeLikedRuntime()
        playback = FakePlaybackRuntime()

        detail = SpotifyLikedSongsDetail(
            liked,
            playback_runtime=playback,
        )

        self.addCleanup(
            detail.deleteLater
        )

        return (
            detail,
            liked,
            playback,
        )

    def test_liked_songs_card_can_activate(
        self,
    ):
        card = SpotifyLikedSongsCard()

        self.addCleanup(
            card.deleteLater
        )

        calls = []

        card.activated.connect(
            lambda:
            calls.append(
                "liked"
            )
        )

        self.assertTrue(
            card.activate()
        )

        self.assertEqual(
            calls,
            [
                "liked",
            ],
        )

    def test_detail_construction_is_passive(
        self,
    ):
        (
            _detail,
            liked,
            playback,
        ) = self.make_detail()

        self.assertEqual(
            liked.track_calls,
            [],
        )

        self.assertEqual(
            playback.calls,
            [],
        )

    def test_load_requests_first_fifty_tracks(
        self,
    ):
        detail, liked, _playback = (
            self.make_detail()
        )

        self.assertTrue(
            detail.load()
        )

        self.assertEqual(
            liked.track_calls,
            [
                (
                    SPOTIFY_LIKED_SONGS_PAGE_LIMIT,
                    0,
                ),
            ],
        )

    def test_ready_page_populates_track_rows(
        self,
    ):
        detail, liked, _playback = (
            self.make_detail()
        )

        detail.load()

        liked.tracks_ready.emit(
            result(
                total=640
            )
        )

        self.assertEqual(
            len(
                detail.rows
            ),
            1,
        )

        self.assertEqual(
            detail.rows[
                0
            ].title_label.text(),
            "Saved Track",
        )

        self.assertEqual(
            detail.rows[
                0
            ].number_label.text(),
            "1",
        )

        self.assertEqual(
            detail.subtitle_label.text(),
            "640 songs",
        )

        self.assertFalse(
            detail.load_more_button.isHidden()
        )

    def test_load_more_uses_next_api_offset(
        self,
    ):
        detail, liked, _playback = (
            self.make_detail()
        )

        detail.load()

        liked.tracks_ready.emit(
            result(
                offset=0,
                limit=50,
                total=60,
                title="First",
            )
        )

        self.assertTrue(
            detail.load_more()
        )

        self.assertEqual(
            liked.track_calls[-1],
            (
                50,
                50,
            ),
        )

        liked.tracks_ready.emit(
            result(
                offset=50,
                limit=50,
                total=60,
                title="Second",
            )
        )

        self.assertEqual(
            len(
                detail.rows
            ),
            2,
        )

        self.assertEqual(
            detail.rows[
                1
            ].number_label.text(),
            "51",
        )

        self.assertTrue(
            detail.load_more_button.isHidden()
        )

    def test_loaded_page_is_reused_when_reopened(
        self,
    ):
        detail, liked, _playback = (
            self.make_detail()
        )

        detail.load()

        liked.tracks_ready.emit(
            result(
                total=1
            )
        )

        self.assertEqual(
            len(
                liked.track_calls
            ),
            1,
        )

        self.assertTrue(
            detail.load()
        )

        self.assertEqual(
            len(
                liked.track_calls
            ),
            1,
        )

    def test_catalogue_row_uses_normal_track_playback(
        self,
    ):
        detail, liked, playback = (
            self.make_detail()
        )

        detail.load()

        liked.tracks_ready.emit(
            result(
                total=1
            )
        )

        self.assertTrue(
            detail.rows[
                0
            ].activate()
        )

        self.assertEqual(
            playback.calls,
            [
                TRACK_URI,
            ],
        )

        self.assertEqual(
            detail.status_label.text(),
            "Starting Saved Track...",
        )

    def test_spotify_page_exposes_liked_navigation(
        self,
    ):
        source = (
            ROOT
            / "src"
            / "ui"
            / "spotify_page.py"
        ).read_text(
            encoding="utf-8"
        )

        for marker in (
            "SPOTIFY_LIKED_SONGS_INDEX = 3",
            "SpotifyLikedSongsDetail",
            "_install_liked_songs_detail",
            "liked_songs_activated.connect",
            "def show_liked_songs(",
            'return "liked_songs"',
        ):
            self.assertIn(
                marker,
                source,
            )

    def test_home_exposes_liked_activation_signal(
        self,
    ):
        source = (
            ROOT
            / "src"
            / "ui"
            / "spotify_playlist_widgets.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "liked_songs_activated = pyqtSignal()",
            source,
        )

        self.assertIn(
            "SpotifyLikedSongsCard()",
            source,
        )


    def test_first_page_requests_context_discovery(
        self,
    ):
        detail, liked, _playback = (
            self.make_detail()
        )

        self.assertTrue(
            detail.load()
        )

        self.assertEqual(
            liked.include_context_calls,
            [
                True,
            ],
        )

    def test_validated_context_uses_playlist_track_playback(
        self,
    ):
        detail, liked, playback = (
            self.make_detail()
        )

        detail.load()

        liked.tracks_ready.emit(
            result(
                total=1,
                context_playlist_id=(
                    "37i9dQZF1F5p3rmiWPIYgZ"
                ),
            )
        )

        self.assertTrue(
            detail.rows[
                0
            ].activate()
        )

        self.assertEqual(
            playback.context_calls,
            [
                (
                    "37i9dQZF1F5p3rmiWPIYgZ",
                    TRACK_URI,
                ),
            ],
        )

        self.assertEqual(
            playback.calls,
            [],
        )

    def test_missing_context_falls_back_to_track_playback(
        self,
    ):
        detail, liked, playback = (
            self.make_detail()
        )

        detail.load()

        liked.tracks_ready.emit(
            result(
                total=1
            )
        )

        self.assertTrue(
            detail.rows[
                0
            ].activate()
        )

        self.assertEqual(
            playback.calls,
            [
                TRACK_URI,
            ],
        )

        self.assertEqual(
            playback.context_calls,
            [],
        )


if __name__ == "__main__":
    unittest.main()
