from __future__ import annotations

import unittest

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
)
from src.ui.spotify_artwork import (
    SpotifyArtworkLoader,
)
from src.ui.spotify_search import (
    SpotifySearchPage,
    SpotifySearchResultRow,
    SpotifySearchSection,
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


class FakeSearchRuntime(
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

    def search(
        self,
        *args,
        **kwargs,
    ):
        pass


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
            "card": "#18181f",
            "card_alt": "#202028",
            "border": "#34343e",
            "accent": "#ff4f91",
            "text": "#f4f4f6",
            "muted": "#a6a6b1",
        }


def make_item(
    *,
    image_url=(
        "https://i.scdn.co/image/example"
    ),
):
    return SpotifySearchItem(
        item_type=(
            SpotifySearchItemType.TRACK
        ),
        spotify_id="track-1",
        name="Test Track",
        image_url=image_url,
        subtitle="Test Artist",
    )


class SpotifySearchArtworkUiTests(
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

    def test_row_requests_item_artwork(
        self,
    ):
        loader = FakeArtworkLoader()

        row = SpotifySearchResultRow(
            make_item(),
            artwork_loader=loader,
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            loader.requests,
            [
                (
                    "https://i.scdn.co/"
                    "image/example"
                )
            ],
        )

    def test_row_without_artwork_keeps_fallback_icon(
        self,
    ):
        loader = FakeArtworkLoader()

        row = SpotifySearchResultRow(
            make_item(
                image_url=""
            ),
            artwork_loader=loader,
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            loader.requests,
            [],
        )

        self.assertTrue(
            row.icon_label.text()
        )

    def test_matching_artwork_replaces_fallback_icon(
        self,
    ):
        loader = FakeArtworkLoader()

        item = make_item()

        row = SpotifySearchResultRow(
            item,
            artwork_loader=loader,
        )

        self.addCleanup(
            row.deleteLater
        )

        pixmap = QPixmap(
            8,
            8,
        )

        loader.artwork_ready.emit(
            item.image_url,
            pixmap,
        )

        self.assertEqual(
            row.icon_label.text(),
            "",
        )

        self.assertIsNotNone(
            row.icon_label.pixmap()
        )

    def test_unrelated_artwork_is_ignored(
        self,
    ):
        loader = FakeArtworkLoader()

        row = SpotifySearchResultRow(
            make_item(),
            artwork_loader=loader,
        )

        self.addCleanup(
            row.deleteLater
        )

        original_text = (
            row.icon_label.text()
        )

        loader.artwork_ready.emit(
            (
                "https://i.scdn.co/"
                "image/other"
            ),
            QPixmap(
                8,
                8,
            ),
        )

        self.assertEqual(
            row.icon_label.text(),
            original_text,
        )

    def test_failed_artwork_keeps_fallback_icon(
        self,
    ):
        loader = FakeArtworkLoader()

        item = make_item()

        row = SpotifySearchResultRow(
            item,
            artwork_loader=loader,
        )

        self.addCleanup(
            row.deleteLater
        )

        original_text = (
            row.icon_label.text()
        )

        loader.artwork_failed.emit(
            item.image_url
        )

        self.assertEqual(
            row.icon_label.text(),
            original_text,
        )

    def test_section_passes_loader_to_rows(
        self,
    ):
        loader = FakeArtworkLoader()

        section = SpotifySearchSection(
            SpotifySearchItemType.TRACK,
            artwork_loader=loader,
        )

        self.addCleanup(
            section.deleteLater
        )

        section.set_items(
            (
                make_item(),
            )
        )

        self.assertEqual(
            loader.requests,
            [
                (
                    "https://i.scdn.co/"
                    "image/example"
                )
            ],
        )

        self.assertIs(
            section.rows[0].artwork_loader,
            loader,
        )

    def test_page_accepts_shared_artwork_loader(
        self,
    ):
        loader = FakeArtworkLoader()

        page = SpotifySearchPage(
            FakeSearchRuntime(),
            theme_manager=(
                FakeThemeManager()
            ),
            artwork_loader=loader,
        )

        self.addCleanup(
            page.deleteLater
        )

        self.assertIs(
            page.artwork_loader,
            loader,
        )

        for section in (
            page.sections.values()
        ):
            self.assertIs(
                section.artwork_loader,
                loader,
            )

    def test_page_creates_default_artwork_loader(
        self,
    ):
        page = SpotifySearchPage(
            FakeSearchRuntime(),
            theme_manager=(
                FakeThemeManager()
            ),
        )

        self.addCleanup(
            page.deleteLater
        )

        self.assertIsInstance(
            page.artwork_loader,
            SpotifyArtworkLoader,
        )
