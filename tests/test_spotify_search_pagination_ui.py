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
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
    SpotifySearchPage as SpotifySearchResultPage,
    SpotifySearchResults,
)
from src.spotify.search_service import (
    SpotifySearchServiceResult,
    SpotifySearchServiceStatus,
)
from src.ui.spotify_search import (
    SPOTIFY_SEARCH_PAGE_LIMIT,
    SpotifySearchPage,
    SpotifySearchSection,
)


class FakeRuntime(
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

    search_finished = pyqtSignal(
        str
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.busy = False
        self.active_query = ""
        self.calls = []

    def search(
        self,
        query,
        *,
        types=None,
        limit=5,
        offset=0,
        market=None,
    ):
        self.calls.append(
            (
                query,
                limit,
                offset,
            )
        )

        self.active_query = str(
            query
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
            "card": "#18181f",
            "card_alt": "#202028",
            "border": "#34343e",
            "text": "#f5f5f7",
            "muted": "#a0a0aa",
            "accent": "#ff4f91",
        }


class FakeArtworkLoader(
    QObject
):
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


def search_item(
    item_type,
    index,
):
    prefixes = {
        SpotifySearchItemType.TRACK:
            "track",
        SpotifySearchItemType.ALBUM:
            "album",
        SpotifySearchItemType.ARTIST:
            "artist",
        SpotifySearchItemType.PLAYLIST:
            "playlist",
    }

    prefix = prefixes[
        item_type
    ]

    spotify_id = (
        prefix
        + str(
            index
        )
    )

    return SpotifySearchItem(
        item_type=item_type,
        spotify_id=spotify_id,
        name=(
            prefix.title()
            + " "
            + str(
                index
            )
        ),
        uri=(
            "spotify:"
            + prefix
            + ":"
            + spotify_id
        ),
        subtitle="Example",
    )


def search_results(
    query="juice wrld",
    *,
    offset=0,
    total=8,
):
    remaining = max(
        0,
        total - offset,
    )

    count = min(
        SPOTIFY_SEARCH_PAGE_LIMIT,
        remaining,
    )

    pages = []

    for item_type in (
        SpotifySearchItemType.TRACK,
        SpotifySearchItemType.ALBUM,
        SpotifySearchItemType.ARTIST,
        SpotifySearchItemType.PLAYLIST,
    ):
        items = tuple(
            search_item(
                item_type,
                offset + index,
            )
            for index in range(
                count
            )
        )

        pages.append(
            SpotifySearchResultPage(
                item_type=item_type,
                items=items,
                limit=(
                    SPOTIFY_SEARCH_PAGE_LIMIT
                ),
                offset=offset,
                total=total,
            )
        )

    return SpotifySearchResults(
        query=query,
        pages=tuple(
            pages
        ),
    )


def ready_result(
    results,
):
    return SpotifySearchServiceResult(
        status=(
            SpotifySearchServiceStatus.READY
        ),
        results=results,
    )


class SpotifySearchPaginationUiTests(
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

    def make_page(
        self,
    ):
        runtime = FakeRuntime()
        theme = FakeThemeManager()
        artwork = FakeArtworkLoader()

        page = SpotifySearchPage(
            runtime,
            theme_manager=theme,
            artwork_loader=artwork,
        )

        self.addCleanup(
            page.deleteLater
        )

        return (
            page,
            runtime,
        )

    def test_page_limit_remains_five(
        self,
    ):
        self.assertEqual(
            SPOTIFY_SEARCH_PAGE_LIMIT,
            5,
        )

    def test_section_can_append_without_replacing_rows(
        self,
    ):
        section = SpotifySearchSection(
            SpotifySearchItemType.TRACK,
            artwork_loader=(
                FakeArtworkLoader()
            ),
        )

        self.addCleanup(
            section.deleteLater
        )

        section.set_items(
            (
                search_item(
                    SpotifySearchItemType.TRACK,
                    0,
                ),
                search_item(
                    SpotifySearchItemType.TRACK,
                    1,
                ),
            )
        )

        section.append_items(
            (
                search_item(
                    SpotifySearchItemType.TRACK,
                    2,
                ),
            )
        )

        self.assertEqual(
            section.item_count,
            3,
        )

        self.assertEqual(
            section.count_label.text(),
            "3",
        )

    def test_initial_results_expose_load_more(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        self.assertEqual(
            page._next_search_offset,
            5,
        )

        self.assertFalse(
            page.load_more_button.isHidden()
        )

    def test_load_more_uses_next_offset_and_preserves_rows(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        before = (
            page.sections[
                SpotifySearchItemType.TRACK
            ].item_count
        )

        self.assertTrue(
            page.load_more_results()
        )

        self.assertEqual(
            runtime.calls[
                -1
            ],
            (
                "juice wrld",
                5,
                5,
            ),
        )

        self.assertEqual(
            page.sections[
                SpotifySearchItemType.TRACK
            ].item_count,
            before,
        )

    def test_ready_pagination_result_appends_rows(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        self.assertTrue(
            page.load_more_results()
        )

        page.handle_result(
            ready_result(
                search_results(
                    offset=5,
                )
            )
        )

        for item_type in (
            SpotifySearchItemType.TRACK,
            SpotifySearchItemType.ALBUM,
            SpotifySearchItemType.ARTIST,
            SpotifySearchItemType.PLAYLIST,
        ):
            self.assertEqual(
                page.sections[
                    item_type
                ].item_count,
                8,
            )

        self.assertIsNone(
            page._next_search_offset
        )

        self.assertTrue(
            page.load_more_button.isHidden()
        )

    def test_changed_query_cannot_paginate_old_results(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        page.search_input.setText(
            "juice"
        )

        page._sync_search_controls()

        self.assertFalse(
            page.load_more_results()
        )

        self.assertTrue(
            page.load_more_button.isHidden()
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_new_initial_search_still_uses_offset_zero(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        page.search_input.setText(
            "eminem"
        )

        self.assertTrue(
            page._submit_search(
                "eminem",
                allow_repeat=True,
            )
        )

        self.assertEqual(
            runtime.calls[
                -1
            ],
            (
                "eminem",
                5,
                0,
            ),
        )

        self.assertIsNone(
            page._last_results
        )

        self.assertIsNone(
            page._next_search_offset
        )



    def test_wrong_offset_page_is_rejected_without_duplicate_rows(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        self.assertTrue(
            page.load_more_results()
        )

        page.handle_result(
            ready_result(
                search_results(
                    offset=0,
                )
            )
        )

        for item_type in (
            SpotifySearchItemType.TRACK,
            SpotifySearchItemType.ALBUM,
            SpotifySearchItemType.ARTIST,
            SpotifySearchItemType.PLAYLIST,
        ):
            self.assertEqual(
                page.sections[
                    item_type
                ].item_count,
                5,
            )

        self.assertEqual(
            page._next_search_offset,
            5,
        )

        self.assertIn(
            "pagination state",
            page.status_label
            .text()
            .casefold(),
        )

    def test_runtime_failure_during_load_more_preserves_rows(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        self.assertTrue(
            page.load_more_results()
        )

        page.handle_failure(
            "network_error",
            "Temporary failure",
        )

        self.assertEqual(
            page.sections[
                SpotifySearchItemType.TRACK
            ].item_count,
            5,
        )

        self.assertIsNotNone(
            page._last_results
        )

        self.assertEqual(
            page._next_search_offset,
            5,
        )

    def test_service_error_during_load_more_preserves_rows(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        self.assertTrue(
            page.load_more_results()
        )

        result = SpotifySearchServiceResult(
            status=(
                SpotifySearchServiceStatus.ERROR
            ),
            error_code="rate_limited",
            message="Please try again.",
            retry_after_seconds=3,
        )

        page.handle_result(
            result
        )

        self.assertEqual(
            page.sections[
                SpotifySearchItemType.TRACK
            ].item_count,
            5,
        )

        self.assertIsNotNone(
            page._last_results
        )

        self.assertEqual(
            page._next_search_offset,
            5,
        )

        self.assertIn(
            "3 seconds",
            page.status_label.text(),
        )

    def test_disconnected_load_more_preserves_rows(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        self.assertTrue(
            page.load_more_results()
        )

        result = SpotifySearchServiceResult(
            status=(
                SpotifySearchServiceStatus
                .DISCONNECTED
            ),
            message="Spotify is disconnected.",
        )

        page.handle_result(
            result
        )

        self.assertEqual(
            page.sections[
                SpotifySearchItemType.TRACK
            ].item_count,
            5,
        )

        self.assertIsNotNone(
            page._last_results
        )

        self.assertEqual(
            page._next_search_offset,
            5,
        )

    def test_reauthorization_load_more_preserves_rows(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        self.assertTrue(
            page.load_more_results()
        )

        result = SpotifySearchServiceResult(
            status=(
                SpotifySearchServiceStatus
                .REAUTHORIZATION_REQUIRED
            ),
            message="Reconnect Spotify.",
        )

        page.handle_result(
            result
        )

        self.assertEqual(
            page.sections[
                SpotifySearchItemType.TRACK
            ].item_count,
            5,
        )

        self.assertIsNotNone(
            page._last_results
        )

        self.assertEqual(
            page._next_search_offset,
            5,
        )

    def test_changed_query_ignores_inflight_pagination_result(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        self.assertTrue(
            page.load_more_results()
        )

        page.search_input.setText(
            "eminem"
        )

        page.handle_result(
            ready_result(
                search_results(
                    offset=5,
                )
            )
        )

        self.assertEqual(
            page.sections[
                SpotifySearchItemType.TRACK
            ].item_count,
            5,
        )

        self.assertEqual(
            page._last_results.query,
            "juice wrld",
        )

    def test_initial_search_error_still_clears_old_results(
        self,
    ):
        (
            page,
            runtime,
        ) = self.make_page()

        page.search_input.setText(
            "juice wrld"
        )

        page.show_results(
            search_results()
        )

        page._active_search_append = False

        result = SpotifySearchServiceResult(
            status=(
                SpotifySearchServiceStatus.ERROR
            ),
            error_code="search_failed",
            message="Search failed.",
        )

        page.handle_result(
            result
        )

        self.assertIsNone(
            page._last_results
        )

        self.assertEqual(
            page.sections[
                SpotifySearchItemType.TRACK
            ].item_count,
            0,
        )


if __name__ == "__main__":
    unittest.main()
