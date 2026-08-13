from __future__ import annotations

import inspect
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication

from src.ui.spotify_page import (
    SpotifyPage,
)
from src.ui.spotify_playlist_detail import (
    SpotifyPlaylistDetail,
    SpotifyPlaylistTrackRow,
)


def ensure_app():
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class FakeArtworkLoader(
    QObject
):
    artwork_ready = pyqtSignal(
        str,
        QPixmap,
    )

    artwork_failed = pyqtSignal(
        str,
    )

    def __init__(
        self,
        *,
        synchronous_pixmap=None,
    ):
        super().__init__()

        self.requests = []

        self.synchronous_pixmap = (
            synchronous_pixmap
        )

    def request(
        self,
        reference,
    ):
        self.requests.append(
            reference
        )

        if (
            self.synchronous_pixmap
            is not None
        ):
            self.artwork_ready.emit(
                reference,
                self.synchronous_pixmap,
            )

        return True


def resolved_item(
    *,
    is_local,
    local_available,
    local_path="",
    artwork_reference="",
    position=0,
):
    return SimpleNamespace(
        is_local=is_local,
        local_available=(
            local_available
        ),
        position=position,
        unified_track=(
            SimpleNamespace(
                title="Example Track",
                artist="Example Artist",
                album="Example Album",
                duration_ms=180000,
                artwork_reference=(
                    artwork_reference
                ),
                local_path=local_path,
                spotify_uri=(
                    ""
                    if is_local
                    else (
                        "spotify:track:"
                        "track123"
                    )
                ),
                playable=True,
            )
        ),
    )


class FakeShutdownLoader:
    def __init__(
        self,
        *,
        result=True,
        raises=False,
    ):
        self.calls = 0
        self.result = result
        self.raises = raises

    def shutdown(
        self,
    ):
        self.calls += 1

        if self.raises:
            raise RuntimeError(
                "simulated shutdown failure"
            )

        return self.result


class SpotifyPlaylistLocalArtworkTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = ensure_app()

    def test_catalogue_row_still_uses_spotify_loader(
        self,
    ):
        spotify_loader = (
            FakeArtworkLoader()
        )

        local_loader = (
            FakeArtworkLoader()
        )

        reference = (
            "https://i.scdn.co/"
            "image/catalogue"
        )

        row = SpotifyPlaylistTrackRow(
            resolved_item(
                is_local=False,
                local_available=None,
                artwork_reference=(
                    reference
                ),
            ),
            number=1,
            artwork_loader=(
                spotify_loader
            ),
            local_artwork_loader=(
                local_loader
            ),
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            spotify_loader.requests,
            [reference],
        )

        self.assertEqual(
            local_loader.requests,
            [],
        )

    def test_available_local_row_requests_local_path(
        self,
    ):
        spotify_loader = (
            FakeArtworkLoader()
        )

        local_loader = (
            FakeArtworkLoader()
        )

        local_path = str(
            (
                Path(
                    tempfile.gettempdir()
                )
                / "playlist-local-art.mp3"
            ).resolve()
        )

        row = SpotifyPlaylistTrackRow(
            resolved_item(
                is_local=True,
                local_available=True,
                local_path=local_path,
            ),
            number=2,
            artwork_loader=(
                spotify_loader
            ),
            local_artwork_loader=(
                local_loader
            ),
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            local_loader.requests,
            [local_path],
        )

        self.assertEqual(
            spotify_loader.requests,
            [],
        )

    def test_unavailable_local_row_keeps_fallback(
        self,
    ):
        spotify_loader = (
            FakeArtworkLoader()
        )

        local_loader = (
            FakeArtworkLoader()
        )

        local_path = str(
            (
                Path(
                    tempfile.gettempdir()
                )
                / "unavailable-local.mp3"
            ).resolve()
        )

        row = SpotifyPlaylistTrackRow(
            resolved_item(
                is_local=True,
                local_available=False,
                local_path=local_path,
            ),
            number=3,
            artwork_loader=(
                spotify_loader
            ),
            local_artwork_loader=(
                local_loader
            ),
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            local_loader.requests,
            [],
        )

        self.assertEqual(
            spotify_loader.requests,
            [],
        )

        self.assertEqual(
            row.artwork_label.text(),
            "\u266b",
        )

        self.assertTrue(
            row.artwork_label
            .pixmap()
            .isNull()
        )

    def test_matching_local_artwork_installs_pixmap(
        self,
    ):
        local_loader = (
            FakeArtworkLoader()
        )

        local_path = str(
            (
                Path(
                    tempfile.gettempdir()
                )
                / "matching-local.mp3"
            ).resolve()
        )

        row = SpotifyPlaylistTrackRow(
            resolved_item(
                is_local=True,
                local_available=True,
                local_path=local_path,
            ),
            number=4,
            local_artwork_loader=(
                local_loader
            ),
        )

        self.addCleanup(
            row.deleteLater
        )

        pixmap = QPixmap(
            10,
            10,
        )

        local_loader.artwork_ready.emit(
            local_path,
            pixmap,
        )

        self.assertEqual(
            row.artwork_label.text(),
            "",
        )

        self.assertFalse(
            row.artwork_label
            .pixmap()
            .isNull()
        )

    def test_unrelated_local_artwork_is_ignored(
        self,
    ):
        local_loader = (
            FakeArtworkLoader()
        )

        local_path = str(
            (
                Path(
                    tempfile.gettempdir()
                )
                / "expected-local.mp3"
            ).resolve()
        )

        other_path = str(
            (
                Path(
                    tempfile.gettempdir()
                )
                / "other-local.mp3"
            ).resolve()
        )

        row = SpotifyPlaylistTrackRow(
            resolved_item(
                is_local=True,
                local_available=True,
                local_path=local_path,
            ),
            number=5,
            local_artwork_loader=(
                local_loader
            ),
        )

        self.addCleanup(
            row.deleteLater
        )

        local_loader.artwork_ready.emit(
            other_path,
            QPixmap(
                10,
                10,
            ),
        )

        self.assertEqual(
            row.artwork_label.text(),
            "\u266b",
        )

        self.assertTrue(
            row.artwork_label
            .pixmap()
            .isNull()
        )

    def test_synchronous_local_cache_hit_is_handled(
        self,
    ):
        local_path = str(
            (
                Path(
                    tempfile.gettempdir()
                )
                / "cached-local.mp3"
            ).resolve()
        )

        loader = FakeArtworkLoader(
            synchronous_pixmap=(
                QPixmap(
                    10,
                    10,
                )
            ),
        )

        row = SpotifyPlaylistTrackRow(
            resolved_item(
                is_local=True,
                local_available=True,
                local_path=local_path,
            ),
            number=6,
            local_artwork_loader=(
                loader
            ),
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            loader.requests,
            [local_path],
        )

        self.assertEqual(
            row.artwork_label.text(),
            "",
        )

        self.assertFalse(
            row.artwork_label
            .pixmap()
            .isNull()
        )

    def test_failure_cannot_replace_good_local_artwork(
        self,
    ):
        local_loader = (
            FakeArtworkLoader()
        )

        local_path = str(
            (
                Path(
                    tempfile.gettempdir()
                )
                / "good-local.mp3"
            ).resolve()
        )

        row = SpotifyPlaylistTrackRow(
            resolved_item(
                is_local=True,
                local_available=True,
                local_path=local_path,
            ),
            number=7,
            local_artwork_loader=(
                local_loader
            ),
        )

        self.addCleanup(
            row.deleteLater
        )

        local_loader.artwork_ready.emit(
            local_path,
            QPixmap(
                10,
                10,
            ),
        )

        self.assertFalse(
            row.artwork_label
            .pixmap()
            .isNull()
        )

        local_loader.artwork_failed.emit(
            local_path
        )

        self.assertEqual(
            row.artwork_label.text(),
            "",
        )

        self.assertFalse(
            row.artwork_label
            .pixmap()
            .isNull()
        )

    def test_detail_exposes_local_loader_dependency(
        self,
    ):
        signature = inspect.signature(
            SpotifyPlaylistDetail.__init__
        )

        self.assertIn(
            "local_artwork_loader",
            signature.parameters,
        )

        source = inspect.getsource(
            SpotifyPlaylistDetail
            ._append_resolved_page
        )

        self.assertIn(
            "local_artwork_loader",
            source,
        )

        self.assertIn(
            "self.local_artwork_loader",
            source,
        )

    def test_page_owns_and_passes_local_loader(
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
            encoding="utf-8-sig"
        )

        self.assertIn(
            "LocalArtworkLoader",
            source,
        )

        self.assertIn(
            "self.local_artwork_loader",
            source,
        )

        self.assertIn(
            "local_artwork_loader=(",
            source,
        )

        self.assertIn(
            "aboutToQuit.connect(",
            source,
        )

        self.assertIn(
            "self.shutdown",
            source,
        )

    def test_page_shutdown_stops_local_loader(
        self,
    ):
        loader = FakeShutdownLoader()

        fake_page = SimpleNamespace(
            local_artwork_loader=loader
        )

        result = SpotifyPage.shutdown(
            fake_page
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            loader.calls,
            1,
        )

    def test_page_shutdown_is_exception_safe(
        self,
    ):
        loader = FakeShutdownLoader(
            raises=True
        )

        fake_page = SimpleNamespace(
            local_artwork_loader=loader
        )

        result = SpotifyPage.shutdown(
            fake_page
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            loader.calls,
            1,
        )


if __name__ == "__main__":
    unittest.main()
