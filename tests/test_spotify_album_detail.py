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
    SpotifyAlbumTrack,
    SpotifyAlbumTracksPage,
)
from src.spotify.album_service import (
    SpotifyAlbumServiceResult,
    SpotifyAlbumServiceStatus,
)
from src.spotify.qt_album_runtime import (
    OPERATION_ALBUM,
)
from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
)
from src.ui.spotify_album_detail import (
    SpotifyAlbumDetail,
    SpotifyAlbumTrackRow,
    format_album_duration,
)


def ensure_app():
    app = QApplication.instance()

    if app is None:
        app = QApplication(
            []
        )

    return app


def album_item(
    *,
    image_url="",
):
    return SpotifySearchItem(
        item_type=(
            SpotifySearchItemType.ALBUM
        ),
        spotify_id="album123",
        name="Example Album",
        uri="spotify:album:album123",
        image_url=image_url,
        subtitle="Artist One",
    )


def album_summary(
    *,
    image_url="",
):
    return SpotifyAlbumSummary(
        spotify_id="album123",
        name="Example Album",
        uri="spotify:album:album123",
        artists=(
            "Artist One",
        ),
        total_tracks=2,
        album_type="album",
        image_url=image_url,
        release_date="2026-08-10",
        release_date_precision="day",
    )


def track(
    spotify_id,
    number,
):
    return SpotifyAlbumTrack(
        spotify_id=spotify_id,
        name=(
            "Track "
            + str(
                number
            )
        ),
        uri=(
            "spotify:track:"
            + spotify_id
        ),
        artists=(
            "Artist One",
        ),
        duration_ms=125000,
        disc_number=1,
        track_number=number,
    )


class FakeAlbumRuntime(
    QObject
):
    album_ready = pyqtSignal(
        str,
        object,
    )

    album_tracks_ready = pyqtSignal(
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

    def load_album(
        self,
        album_id,
        *,
        market=None,
    ):
        self.calls.append(
            (
                "album",
                album_id,
                market,
            )
        )

    def load_album_tracks(
        self,
        album_id,
        *,
        limit,
        offset,
        market=None,
    ):
        self.calls.append(
            (
                "tracks",
                album_id,
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
        str
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.requests = []

    def request(
        self,
        artwork_url,
    ):
        self.requests.append(
            artwork_url
        )

        return True


class SpotifyAlbumDetailTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = ensure_app()

    def make_detail(
        self,
        *,
        artwork_loader=None,
    ):
        runtime = FakeAlbumRuntime()

        detail = SpotifyAlbumDetail(
            runtime,
            artwork_loader=(
                artwork_loader
            ),
        )

        self.addCleanup(
            detail.deleteLater
        )

        return (
            detail,
            runtime,
        )

    def test_duration_format(
        self,
    ):
        self.assertEqual(
            format_album_duration(
                125000
            ),
            "2:05",
        )

    def test_track_row_uses_album_track(
        self,
    ):
        row = SpotifyAlbumTrackRow(
            track(
                "track123",
                1,
            ),
            number=1,
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            row.title_label.text(),
            "Track 1",
        )

        self.assertEqual(
            row.artist_label.text(),
            "Artist One",
        )

    def test_search_item_seeds_header(
        self,
    ):
        detail, runtime = (
            self.make_detail()
        )

        del runtime

        self.assertTrue(
            detail.set_search_item(
                album_item()
            )
        )

        self.assertEqual(
            detail.title_label.text(),
            "Example Album",
        )

        self.assertEqual(
            detail.artist_label.text(),
            "Artist One",
        )

    def test_search_item_requests_seed_artwork(
        self,
    ):
        artwork = FakeArtworkLoader()

        detail, runtime = (
            self.make_detail(
                artwork_loader=artwork
            )
        )

        del runtime

        self.assertTrue(
            detail.set_search_item(
                album_item(
                    image_url=(
                        "https://i.scdn.co/"
                        "image/search-art"
                    )
                )
            )
        )

        self.assertEqual(
            artwork.requests,
            [
                (
                    "https://i.scdn.co/"
                    "image/search-art"
                ),
            ],
        )

    def test_album_result_requests_authoritative_artwork(
        self,
    ):
        artwork = FakeArtworkLoader()

        detail, runtime = (
            self.make_detail(
                artwork_loader=artwork
            )
        )

        del runtime

        detail.set_search_item(
            album_item(
                image_url=(
                    "https://i.scdn.co/"
                    "image/search-art"
                )
            )
        )

        detail.handle_album_ready(
            "album123",
            SpotifyAlbumServiceResult(
                status=(
                    SpotifyAlbumServiceStatus.READY
                ),
                album=(
                    album_summary(
                        image_url=(
                            "https://i.scdn.co/"
                            "image/album-art"
                        )
                    )
                ),
            ),
        )

        self.assertEqual(
            artwork.requests[-1],
            (
                "https://i.scdn.co/"
                "image/album-art"
            ),
        )

    def test_current_artwork_result_is_rendered(
        self,
    ):
        artwork = FakeArtworkLoader()

        detail, runtime = (
            self.make_detail(
                artwork_loader=artwork
            )
        )

        del runtime

        url = (
            "https://i.scdn.co/"
            "image/album-art"
        )

        detail.set_search_item(
            album_item(
                image_url=url
            )
        )

        pixmap = QPixmap(
            32,
            32,
        )

        self.assertFalse(
            pixmap.isNull()
        )

        detail._handle_artwork_ready(
            url,
            pixmap,
        )

        display = (
            detail.artwork_label
            .pixmap()
        )

        self.assertIsNotNone(
            display
        )

        self.assertFalse(
            display.isNull()
        )

        self.assertEqual(
            detail.artwork_label.text(),
            "",
        )

    def test_stale_artwork_result_is_ignored(
        self,
    ):
        artwork = FakeArtworkLoader()

        detail, runtime = (
            self.make_detail(
                artwork_loader=artwork
            )
        )

        del runtime

        current_url = (
            "https://i.scdn.co/"
            "image/current-art"
        )

        detail.set_search_item(
            album_item(
                image_url=current_url
            )
        )

        pixmap = QPixmap(
            32,
            32,
        )

        detail._handle_artwork_ready(
            (
                "https://i.scdn.co/"
                "image/stale-art"
            ),
            pixmap,
        )

        self.assertEqual(
            detail.artwork_label.text(),
            "Album",
        )


    def test_non_album_item_is_rejected(
        self,
    ):
        detail, runtime = (
            self.make_detail()
        )

        del runtime

        item = SpotifySearchItem(
            item_type=(
                SpotifySearchItemType.TRACK
            ),
            spotify_id="track123",
            name="Track",
            uri="spotify:track:track123",
        )

        self.assertFalse(
            detail.set_search_item(
                item
            )
        )

    def test_load_requests_album_metadata_first(
        self,
    ):
        detail, runtime = (
            self.make_detail()
        )

        detail.set_search_item(
            album_item()
        )

        self.assertTrue(
            detail.load()
        )

        self.assertEqual(
            runtime.calls,
            [
                (
                    "album",
                    "album123",
                    None,
                ),
            ],
        )

    def test_album_result_updates_metadata(
        self,
    ):
        detail, runtime = (
            self.make_detail()
        )

        del runtime

        detail.set_search_item(
            album_item()
        )

        detail.handle_album_ready(
            "album123",
            SpotifyAlbumServiceResult(
                status=(
                    SpotifyAlbumServiceStatus.READY
                ),
                album=(
                    album_summary()
                ),
            ),
        )

        self.assertEqual(
            detail.title_label.text(),
            "Example Album",
        )

        self.assertIn(
            "2026-08-10",
            detail.metadata_label.text(),
        )

        self.assertIn(
            "2 tracks",
            detail.metadata_label.text(),
        )

    def test_metadata_completion_starts_track_load(
        self,
    ):
        detail, runtime = (
            self.make_detail()
        )

        detail.set_search_item(
            album_item()
        )

        detail.load()

        detail.handle_album_ready(
            "album123",
            SpotifyAlbumServiceResult(
                status=(
                    SpotifyAlbumServiceStatus.READY
                ),
                album=(
                    album_summary()
                ),
            ),
        )

        detail.handle_operation_finished(
            OPERATION_ALBUM,
            "album123",
        )

        self.assertEqual(
            runtime.calls[-1],
            (
                "tracks",
                "album123",
                50,
                0,
                None,
            ),
        )

    def test_track_page_renders_rows(
        self,
    ):
        detail, runtime = (
            self.make_detail()
        )

        del runtime

        detail.set_search_item(
            album_item()
        )

        page = SpotifyAlbumTracksPage(
            items=(
                track(
                    "track123",
                    1,
                ),
                track(
                    "track456",
                    2,
                ),
            ),
            limit=50,
            offset=0,
            total=2,
        )

        detail.handle_album_tracks_ready(
            "album123",
            SpotifyAlbumServiceResult(
                status=(
                    SpotifyAlbumServiceStatus.READY
                ),
                tracks_page=page,
            ),
        )

        self.assertEqual(
            len(
                detail._track_rows
            ),
            2,
        )

        self.assertEqual(
            detail._loaded_count,
            2,
        )

        self.assertFalse(
            detail.load_more_button.isVisible()
        )

    def test_load_more_uses_loaded_offset(
        self,
    ):
        detail, runtime = (
            self.make_detail()
        )

        detail.set_search_item(
            album_item()
        )

        detail._loaded_count = 50
        detail._total_tracks = 75

        self.assertTrue(
            detail.load_more()
        )

        self.assertEqual(
            runtime.calls[-1],
            (
                "tracks",
                "album123",
                50,
                50,
                None,
            ),
        )

    def test_back_signal_is_exposed(
        self,
    ):
        detail, runtime = (
            self.make_detail()
        )

        del runtime

        seen = []

        detail.back_requested.connect(
            lambda:
            seen.append(
                True
            )
        )

        detail.back_button.click()

        self.assertEqual(
            seen,
            [
                True
            ],
        )


if __name__ == "__main__":
    unittest.main()
