from __future__ import annotations

import os
from pathlib import Path
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

from src.spotify.qt_search_runtime import (
    SpotifyQtSearchRuntimeError,
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
    SEARCH_SECTION_ORDER,
    SpotifySearchPage,
    SpotifySearchResultRow,
    SpotifySearchSection,
)


TEST_THEME = {
    "background": "#101014",
    "card": "#18181f",
    "card_alt": "#202028",
    "border": "#34343e",
    "accent": "#ff4f91",
    "text": "#f4f4f6",
    "muted": "#a6a6b1",
}


class FakeThemeManager(
    QObject
):
    theme_changed = pyqtSignal(
        dict
    )

    def theme(
        self,
    ):
        return dict(
            TEST_THEME
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

    def __init__(
        self,
    ):
        super().__init__()

        self.busy = False
        self.calls = []
        self.error = None

    def search(
        self,
        query,
        **kwargs,
    ):
        self.calls.append(
            (
                query,
                kwargs,
            )
        )

        if self.error is not None:
            raise self.error


def item(
    item_type,
    spotify_id,
    name,
    subtitle,
):
    return SpotifySearchItem(
        item_type=item_type,
        spotify_id=spotify_id,
        name=name,
        uri=(
            "spotify:"
            + item_type.value
            + ":"
            + spotify_id
        ),
        subtitle=subtitle,
    )


def ready_results(
    query="query",
):
    items = {
        SpotifySearchItemType.TRACK: (
            item(
                SpotifySearchItemType.TRACK,
                "track-1",
                "Track One",
                "Artist One",
            ),
        ),
        SpotifySearchItemType.ALBUM: (
            item(
                SpotifySearchItemType.ALBUM,
                "album-1",
                "Album One",
                "Artist One",
            ),
        ),
        SpotifySearchItemType.ARTIST: (
            item(
                SpotifySearchItemType.ARTIST,
                "artist-1",
                "Artist One",
                "Artist",
            ),
        ),
        SpotifySearchItemType.PLAYLIST: (
            item(
                SpotifySearchItemType.PLAYLIST,
                "playlist-1",
                "Playlist One",
                "Owner",
            ),
        ),
    }

    pages = []

    for item_type in SEARCH_SECTION_ORDER:
        pages.append(
            SpotifySearchResultPage(
                item_type=item_type,
                items=items[
                    item_type
                ],
                limit=5,
                offset=0,
                total=1,
            )
        )

    return SpotifySearchResults(
        query=query,
        pages=tuple(
            pages
        ),
    )


def ready_service_result(
    query="query",
    *,
    refreshed=False,
):
    return SpotifySearchServiceResult(
        status=(
            SpotifySearchServiceStatus.READY
        ),
        results=ready_results(
            query
        ),
        message=(
            "Spotify search completed."
        ),
        refreshed=refreshed,
    )


class SpotifySearchUiTests(
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
        runtime=None,
    ):
        runtime = (
            runtime
            or FakeRuntime()
        )

        theme = FakeThemeManager()

        page = SpotifySearchPage(
            runtime,
            theme_manager=theme,
        )

        self.addCleanup(
            page.close
        )

        return (
            page,
            runtime,
            theme,
        )

    def test_constructor_requires_search_runtime(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifySearchPage(
                object(),
                theme_manager=(
                    FakeThemeManager()
                ),
            )

    def test_page_contains_expected_catalog_sections(
        self,
    ):
        page, _, _ = (
            self.make_page()
        )

        self.assertEqual(
            tuple(
                page.sections.keys()
            ),
            SEARCH_SECTION_ORDER,
        )

        self.assertEqual(
            len(
                page.sections
            ),
            4,
        )

    def test_search_button_starts_default_catalog_search(
        self,
    ):
        page, runtime, _ = (
            self.make_page()
        )

        page.search_input.setText(
            "Juice WRLD"
        )

        page.start_search()

        self.assertEqual(
            runtime.calls,
            [
                (
                    "Juice WRLD",
                    {
                        "limit": 5,
                        "offset": 0,
                    },
                ),
            ],
        )

    def test_blank_search_is_not_sent(
        self,
    ):
        page, runtime, _ = (
            self.make_page()
        )

        page.search_input.setText(
            "   "
        )

        page.start_search()

        self.assertEqual(
            runtime.calls,
            [],
        )

        self.assertIn(
            "Enter something",
            page.status_label.text(),
        )


    def test_typing_enables_and_clearing_disables_search_button(
        self,
    ):
        page, _, _ = (
            self.make_page()
        )

        self.assertFalse(
            page.search_button.isEnabled()
        )

        page.search_input.setText(
            "Juice WRLD"
        )

        self.app.processEvents()

        self.assertTrue(
            page.search_button.isEnabled()
        )

        page.search_input.clear()

        self.app.processEvents()

        self.assertFalse(
            page.search_button.isEnabled()
        )

    def test_busy_state_keeps_input_enabled_and_disables_button(
        self,
    ):
        page, _, _ = (
            self.make_page()
        )

        page.search_input.setText(
            "query"
        )

        page.handle_busy(
            True
        )

        self.assertTrue(
            page.busy
        )

        self.assertTrue(
            page.search_input.isEnabled()
        )

        self.assertFalse(
            page.search_button.isEnabled()
        )

        self.assertEqual(
            page.search_button.text(),
            "Searching...",
        )

        page.handle_busy(
            False
        )

        self.assertFalse(
            page.busy
        )

        self.assertTrue(
            page.search_input.isEnabled()
        )

    def test_ready_result_populates_all_sections(
        self,
    ):
        page, _, _ = (
            self.make_page()
        )

        page.handle_result(
            ready_service_result(
                "query"
            )
        )

        self.assertIsInstance(
            page.last_results,
            SpotifySearchResults,
        )

        for item_type in (
            SEARCH_SECTION_ORDER
        ):
            section = page.sections[
                item_type
            ]

            self.assertEqual(
                len(
                    section.rows
                ),
                1,
            )

            self.assertEqual(
                section.count_label.text(),
                "1",
            )

            self.assertTrue(
                section.empty_label.isHidden()
            )

        self.assertEqual(
            page.connection_badge.text(),
            "READY",
        )

        self.assertIn(
            "4 Spotify results",
            page.status_label.text(),
        )

    def test_refreshed_result_updates_badge(
        self,
    ):
        page, _, _ = (
            self.make_page()
        )

        page.handle_result(
            ready_service_result(
                refreshed=True
            )
        )

        self.assertEqual(
            page.connection_badge.text(),
            "REFRESHED",
        )

    def test_disconnected_result_clears_results(
        self,
    ):
        page, _, _ = (
            self.make_page()
        )

        page.handle_result(
            ready_service_result()
        )

        result = SpotifySearchServiceResult(
            status=(
                SpotifySearchServiceStatus
                .DISCONNECTED
            ),
            message=(
                "Connect Spotify before searching."
            ),
        )

        page.handle_result(
            result
        )

        self.assertIsNone(
            page.last_results
        )

        self.assertEqual(
            page.connection_badge.text(),
            "OFFLINE",
        )

        self.assertIn(
            "Connect Spotify",
            page.status_label.text(),
        )

    def test_reauthorization_result_is_visible(
        self,
    ):
        page, _, _ = (
            self.make_page()
        )

        result = SpotifySearchServiceResult(
            status=(
                SpotifySearchServiceStatus
                .REAUTHORIZATION_REQUIRED
            ),
            message=(
                "Reconnect Spotify before searching."
            ),
        )

        page.handle_result(
            result
        )

        self.assertEqual(
            page.connection_badge.text(),
            "RECONNECT",
        )

        self.assertIn(
            "Reconnect Spotify",
            page.status_label.text(),
        )

    def test_error_result_preserves_retry_delay(
        self,
    ):
        page, _, _ = (
            self.make_page()
        )

        result = SpotifySearchServiceResult(
            status=(
                SpotifySearchServiceStatus.ERROR
            ),
            message=(
                "Spotify search could not "
                "be completed."
            ),
            error_code="rate_limited",
            retry_after_seconds=12,
        )

        page.handle_result(
            result
        )

        self.assertEqual(
            page.connection_badge.text(),
            "ERROR",
        )

        self.assertIn(
            "12 seconds",
            page.status_label.text(),
        )

    def test_runtime_failure_is_user_safe(
        self,
    ):
        page, _, _ = (
            self.make_page()
        )

        page.handle_failure(
            "operation_failed",
            (
                "Spotify Search could not "
                "be completed."
            ),
        )

        self.assertEqual(
            page.connection_badge.text(),
            "ERROR",
        )

        self.assertEqual(
            page.status_label.text(),
            (
                "Spotify Search could not "
                "be completed."
            ),
        )

    def test_runtime_error_during_start_is_shown(
        self,
    ):
        runtime = FakeRuntime()

        runtime.error = (
            SpotifyQtSearchRuntimeError(
                "busy",
                (
                    "Spotify Search is already "
                    "running."
                ),
            )
        )

        page, _, _ = (
            self.make_page(
                runtime
            )
        )

        page.search_input.setText(
            "query"
        )

        page.start_search()

        self.assertIn(
            "already running",
            page.status_label.text(),
        )

    def test_invalid_result_object_is_rejected(
        self,
    ):
        page, _, _ = (
            self.make_page()
        )

        page.handle_result(
            object()
        )

        self.assertIsNone(
            page.last_results
        )

        self.assertIn(
            "invalid",
            page.status_label.text().casefold(),
        )

    def test_result_row_rejects_non_search_item(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifySearchResultRow(
                object()
            )

    def test_section_rejects_wrong_result_type(
        self,
    ):
        section = SpotifySearchSection(
            SpotifySearchItemType.TRACK
        )

        self.addCleanup(
            section.close
        )

        wrong = item(
            SpotifySearchItemType.ALBUM,
            "album-1",
            "Album",
            "Artist",
        )

        with self.assertRaises(
            ValueError
        ):
            section.set_items(
                (
                    wrong,
                )
            )

    def test_clear_results_removes_visible_rows(
        self,
    ):
        page, _, _ = (
            self.make_page()
        )

        page.handle_result(
            ready_service_result()
        )

        page.clear_results()

        self.assertIsNone(
            page.last_results
        )

        for section in (
            page.sections.values()
        ):
            self.assertEqual(
                section.rows,
                (),
            )

            self.assertEqual(
                section.count_label.text(),
                "0",
            )

    def test_theme_change_reapplies_stylesheet(
        self,
    ):
        page, _, theme = (
            self.make_page()
        )

        before = (
            page.styleSheet()
        )

        changed = dict(
            TEST_THEME
        )

        changed[
            "accent"
        ] = "#abcdef"

        theme.theme_changed.emit(
            changed
        )

        self.app.processEvents()

        after = (
            page.styleSheet()
        )

        self.assertNotEqual(
            before,
            after,
        )

        self.assertIn(
            "#abcdef",
            after,
        )


class SpotifySearchUiBoundaryTests(
    unittest.TestCase
):
    def test_ui_does_not_own_credentials_oauth_or_network(
        self,
    ):
        root = (
            Path(
                __file__
            )
            .resolve()
            .parents[1]
        )

        source = (
            root
            / "src"
            / "ui"
            / "spotify_search.py"
        ).read_text(
            encoding="utf-8"
        )

        forbidden = (
            "SpotifyCredentialStore",
            "SpotifySessionManager",
            "SpotifyTokenClient",
            "windows_dpapi",
            "spotify_auth.dat",
            "SpotifyOAuthSession",
            "client_secret",
            "refresh_token",
            "access_token",
            "urllib",
            "urlopen",
            "requests.",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_ui_uses_credential_free_search_models(
        self,
    ):
        fields = (
            SpotifySearchServiceResult
            .__dataclass_fields__
        )

        for forbidden in (
            "token",
            "access_token",
            "refresh_token",
        ):
            self.assertNotIn(
                forbidden,
                fields,
            )

    def test_ui_does_not_modify_main_window_navigation(
        self,
    ):
        root = (
            Path(
                __file__
            )
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

        self.assertNotIn(
            "SpotifySearchPage",
            source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
