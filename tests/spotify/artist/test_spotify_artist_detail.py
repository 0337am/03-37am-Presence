import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.album_models import (
    SpotifyAlbumSummary,
)
from src.spotify.artist_models import (
    SpotifyArtistAlbumsPage,
    SpotifyArtistSummary,
)
from src.spotify.artist_service import (
    SpotifyArtistServiceResult,
    SpotifyArtistServiceStatus,
)
from src.spotify.qt_artist_runtime import (
    OPERATION_ARTIST,
)
from src.ui.spotify_artist_detail import (
    SPOTIFY_ARTIST_DETAIL_LIMIT,
    SpotifyArtistAlbumRow,
    SpotifyArtistDetail,
)


class FakeArtistRuntime(
    QObject
):
    artist_ready = pyqtSignal(
        str,
        object,
    )

    artist_albums_ready = pyqtSignal(
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

    def __init__(
        self,
    ):
        super().__init__()

        self.calls = []

    def load_artist(
        self,
        artist_id,
    ):
        self.calls.append(
            (
                "artist",
                artist_id,
            )
        )

    def load_artist_albums(
        self,
        artist_id,
        *,
        limit,
        offset,
        market=None,
    ):
        self.calls.append(
            (
                "albums",
                artist_id,
                limit,
                offset,
                market,
            )
        )


class FakeArtworkLoader(
    QObject
):
    artwork_ready = pyqtSignal(
        str,
        object,
    )

    artwork_failed = pyqtSignal(
        str,
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.requests = []

    def request(
        self,
        url,
    ):
        self.requests.append(
            url
        )


class FakeThemeManager(
    QObject
):
    theme_changed = pyqtSignal(
        dict
    )

    def theme(
        self,
    ):
        return {
            "background": "#101014",
            "card": "#19191f",
            "border": "#303038",
            "text": "#f5f5f7",
            "muted": "#a0a0aa",
            "accent": "#ff4f9a",
        }


def artist_summary():
    return SpotifyArtistSummary(
        spotify_id="artist123",
        name="Artist One",
        uri="spotify:artist:artist123",
        spotify_url=(
            "https://open.spotify.com/"
            "artist/artist123"
        ),
        image_url=(
            "https://i.scdn.co/"
            "image/artist-one"
        ),
    )


def album_summary(
    spotify_id="album123",
    *,
    name="Album One",
):
    return SpotifyAlbumSummary(
        spotify_id=spotify_id,
        name=name,
        uri=(
            "spotify:album:"
            + spotify_id
        ),
        artists=(
            "Artist One",
        ),
        total_tracks=12,
        album_type="album",
        spotify_url=(
            "https://open.spotify.com/"
            "album/"
            + spotify_id
        ),
        image_url=(
            "https://i.scdn.co/"
            "image/"
            + spotify_id
        ),
        release_date="2026-08-10",
        release_date_precision="day",
    )


def artist_result():
    return SpotifyArtistServiceResult(
        status=(
            SpotifyArtistServiceStatus.READY
        ),
        artist=artist_summary(),
    )


def albums_result(
    *,
    items=None,
    offset=0,
    total=1,
):
    if items is None:
        items = (
            album_summary(),
        )

    return SpotifyArtistServiceResult(
        status=(
            SpotifyArtistServiceStatus.READY
        ),
        albums_page=(
            SpotifyArtistAlbumsPage(
                items=tuple(
                    items
                ),
                limit=(
                    SPOTIFY_ARTIST_DETAIL_LIMIT
                ),
                offset=offset,
                total=total,
                next_url=(
                    "next"
                    if (
                        offset
                        + len(items)
                        < total
                    )
                    else ""
                ),
                previous_url="",
            )
        ),
    )


class SpotifyArtistDetailTests(
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

    def make_detail(
        self,
    ):
        runtime = FakeArtistRuntime()
        artwork = FakeArtworkLoader()
        theme = FakeThemeManager()

        detail = SpotifyArtistDetail(
            runtime,
            theme_manager=theme,
            artwork_loader=artwork,
        )

        self.addCleanup(
            detail.deleteLater
        )

        return (
            detail,
            runtime,
            artwork,
        )

    def test_album_row_activation_emits_album(
        self,
    ):
        album = album_summary()

        row = SpotifyArtistAlbumRow(
            album
        )

        self.addCleanup(
            row.deleteLater
        )

        captured = []

        row.activated.connect(
            captured.append
        )

        self.assertEqual(
            row.title_label.text(),
            "Album One",
        )

        self.assertTrue(
            row.activate()
        )

        self.assertEqual(
            captured,
            [
                album
            ],
        )

    def test_album_row_shows_release_metadata(
        self,
    ):
        row = SpotifyArtistAlbumRow(
            album_summary()
        )

        self.addCleanup(
            row.deleteLater
        )

        text = (
            row.metadata_label.text()
        )

        self.assertIn(
            "Album",
            text,
        )

        self.assertIn(
            "2026-08-10",
            text,
        )

        self.assertIn(
            "12 tracks",
            text,
        )

    def test_set_artist_id_seeds_header_and_artwork(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        detail.set_artist_id(
            "artist123",
            seed_name="Seed Artist",
            seed_image_url="seed-art",
        )

        self.assertEqual(
            detail.artist_id,
            "artist123",
        )

        self.assertEqual(
            detail.title_label.text(),
            "Seed Artist",
        )

        self.assertEqual(
            artwork.requests,
            [
                "seed-art",
            ],
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_load_requests_artist_metadata_first(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        detail.set_artist_id(
            "artist123"
        )

        self.assertTrue(
            detail.load()
        )

        self.assertEqual(
            runtime.calls,
            [
                (
                    "artist",
                    "artist123",
                ),
            ],
        )

    def test_artist_result_waits_for_finish_then_loads_albums(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        detail.set_artist_id(
            "artist123"
        )

        detail.handle_artist_ready(
            "artist123",
            artist_result(),
        )

        self.assertEqual(
            detail.title_label.text(),
            "Artist One",
        )

        self.assertEqual(
            artwork.requests,
            [
                (
                    "https://i.scdn.co/"
                    "image/artist-one"
                ),
            ],
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

        runtime.operation_finished.emit(
            OPERATION_ARTIST,
            "artist123",
        )

        self.assertEqual(
            runtime.calls,
            [
                (
                    "albums",
                    "artist123",
                    10,
                    0,
                    None,
                ),
            ],
        )

    def test_album_row_activation_is_forwarded_by_detail(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        detail.set_artist_id(
            "artist123"
        )

        detail.handle_artist_albums_ready(
            "artist123",
            albums_result(),
        )

        captured = []

        detail.album_activated.connect(
            captured.append
        )

        row = detail.album_rows[
            0
        ]

        self.assertTrue(
            row.activate()
        )

        self.assertEqual(
            captured,
            [
                row.album
            ],
        )

    def test_album_page_renders_rows(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        detail.set_artist_id(
            "artist123"
        )

        detail.handle_artist_albums_ready(
            "artist123",
            albums_result(),
        )

        self.assertEqual(
            len(
                detail.album_rows
            ),
            1,
        )

        self.assertEqual(
            detail.album_rows[
                0
            ].album.spotify_id,
            "album123",
        )

        self.assertFalse(
            detail.load_more_button.isVisible()
        )

    def test_incomplete_page_exposes_load_more(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        detail.set_artist_id(
            "artist123"
        )

        detail.handle_artist_albums_ready(
            "artist123",
            albums_result(
                total=20
            ),
        )

        self.assertEqual(
            detail.loaded_count,
            1,
        )

        self.assertEqual(
            detail.total_albums,
            20,
        )

        self.assertFalse(
            detail.load_more_button.isHidden()
        )

    def test_load_more_uses_loaded_offset(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        detail.set_artist_id(
            "artist123"
        )

        detail.handle_artist_albums_ready(
            "artist123",
            albums_result(
                total=20
            ),
        )

        self.assertTrue(
            detail.load_more()
        )

        self.assertEqual(
            runtime.calls[
                -1
            ],
            (
                "albums",
                "artist123",
                10,
                1,
                None,
            ),
        )

    def test_stale_artist_result_is_ignored(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        detail.set_artist_id(
            "artist123",
            seed_name="Current Artist",
        )

        detail.handle_artist_ready(
            "oldartist",
            artist_result(),
        )

        self.assertEqual(
            detail.title_label.text(),
            "Current Artist",
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_runtime_failure_is_rendered(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        detail.set_artist_id(
            "artist123"
        )

        detail.handle_runtime_failure(
            OPERATION_ARTIST,
            "artist123",
            "offline",
            "Spotify is unavailable.",
        )

        self.assertEqual(
            detail.status_label.text(),
            "Spotify is unavailable.",
        )

        self.assertEqual(
            detail.empty_label.text(),
            "Spotify is unavailable.",
        )

    def test_current_artwork_is_rendered(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        detail.set_artist_id(
            "artist123",
            seed_image_url="current-art",
        )

        pixmap = QPixmap(
            16,
            16,
        )

        artwork.artwork_ready.emit(
            "current-art",
            pixmap,
        )

        self.assertFalse(
            detail.artwork_label.pixmap().isNull()
        )

        self.assertEqual(
            detail.artwork_label.text(),
            "",
        )

    def test_stale_artwork_is_ignored(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        detail.set_artist_id(
            "artist123",
            seed_image_url="current-art",
        )

        pixmap = QPixmap(
            16,
            16,
        )

        artwork.artwork_ready.emit(
            "old-art",
            pixmap,
        )

        self.assertEqual(
            detail.artwork_label.text(),
            "Artist",
        )

    def test_back_signal_is_exposed(
        self,
    ):
        (
            detail,
            runtime,
            artwork,
        ) = self.make_detail()

        captured = []

        detail.back_requested.connect(
            lambda: captured.append(
                True
            )
        )

        detail.back_button.click()

        self.assertEqual(
            captured,
            [
                True,
            ],
        )

    def test_invalid_runtime_is_rejected(
        self,
    ):
        class BadRuntime:
            pass

        with self.assertRaises(
            TypeError
        ):
            SpotifyArtistDetail(
                BadRuntime(),
                theme_manager=(
                    FakeThemeManager()
                ),
                artwork_loader=(
                    FakeArtworkLoader()
                ),
            )


if __name__ == "__main__":
    unittest.main()
