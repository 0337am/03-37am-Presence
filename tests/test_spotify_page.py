from __future__ import annotations

import inspect
import unittest

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
)

import src.ui.spotify_page as page_module
from src.ui.spotify_page import (
    SPOTIFY_HOME_INDEX,
    SPOTIFY_SEARCH_INDEX,
    SpotifyPage,
)
from src.ui.spotify_search import (
    SpotifySearchPage,
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
            "accent": "#ff4f91",
            "text": "#f4f4f6",
            "muted": "#a6a6b1",
        }


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
        self.calls = []

    def search(
        self,
        *args,
        **kwargs,
    ):
        self.calls.append(
            (
                args,
                kwargs,
            )
        )


class FakePlaylistRuntime:
    def __init__(
        self,
    ):
        self.playlist_calls = []
        self.item_calls = []

    def load_playlists(
        self,
        *args,
        **kwargs,
    ):
        self.playlist_calls.append(
            (
                args,
                kwargs,
            )
        )

    def load_playlist_items(
        self,
        *args,
        **kwargs,
    ):
        self.item_calls.append(
            (
                args,
                kwargs,
            )
        )


class SpotifyPageTests(
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

    def setUp(
        self,
    ):
        self.search_runtime = (
            FakeSearchRuntime()
        )

        self.playlist_runtime = (
            FakePlaylistRuntime()
        )

        self.theme = (
            FakeThemeManager()
        )

    def make_page(
        self,
    ):
        page = SpotifyPage(
            search_runtime=(
                self.search_runtime
            ),
            playlist_runtime=(
                self.playlist_runtime
            ),
            theme_manager=(
                self.theme
            ),
        )

        self.addCleanup(
            page.deleteLater
        )

        return page

    def test_constructor_requires_search_runtime(
        self,
    ):
        class InvalidSearchRuntime:
            pass

        with self.assertRaises(
            TypeError
        ):
            SpotifyPage(
                search_runtime=(
                    InvalidSearchRuntime()
                ),
                playlist_runtime=(
                    self.playlist_runtime
                ),
                theme_manager=(
                    self.theme
                ),
            )

    def test_constructor_requires_playlist_list_operation(
        self,
    ):
        class InvalidPlaylistRuntime:
            def load_playlist_items(
                self,
            ):
                pass

        with self.assertRaises(
            TypeError
        ):
            SpotifyPage(
                search_runtime=(
                    self.search_runtime
                ),
                playlist_runtime=(
                    InvalidPlaylistRuntime()
                ),
                theme_manager=(
                    self.theme
                ),
            )

    def test_constructor_requires_playlist_item_operation(
        self,
    ):
        class InvalidPlaylistRuntime:
            def load_playlists(
                self,
            ):
                pass

        with self.assertRaises(
            TypeError
        ):
            SpotifyPage(
                search_runtime=(
                    self.search_runtime
                ),
                playlist_runtime=(
                    InvalidPlaylistRuntime()
                ),
                theme_manager=(
                    self.theme
                ),
            )

    def test_page_defaults_to_home(
        self,
    ):
        page = self.make_page()

        self.assertEqual(
            page.current_section,
            "home",
        )

        self.assertEqual(
            page.content_stack.currentIndex(),
            SPOTIFY_HOME_INDEX,
        )

    def test_show_search_changes_section(
        self,
    ):
        page = self.make_page()

        page.show_search()

        self.assertEqual(
            page.current_section,
            "search",
        )

        self.assertEqual(
            page.content_stack.currentIndex(),
            SPOTIFY_SEARCH_INDEX,
        )

    def test_show_home_restores_home_section(
        self,
    ):
        page = self.make_page()

        page.show_search()
        page.show_home()

        self.assertEqual(
            page.current_section,
            "home",
        )

    def test_existing_search_page_is_preserved(
        self,
    ):
        page = self.make_page()

        self.assertIsInstance(
            page.search_page,
            SpotifySearchPage,
        )

    def test_search_page_receives_existing_runtime(
        self,
    ):
        page = self.make_page()

        self.assertIs(
            page.search_page.runtime,
            self.search_runtime,
        )

    def test_playlist_runtime_is_preserved_for_home_and_detail(
        self,
    ):
        page = self.make_page()

        self.assertIs(
            page.playlist_runtime,
            self.playlist_runtime,
        )

    def test_construction_does_not_start_playlist_requests(
        self,
    ):
        self.make_page()

        self.assertEqual(
            self.playlist_runtime.playlist_calls,
            [],
        )

        self.assertEqual(
            self.playlist_runtime.item_calls,
            [],
        )

    def test_section_buttons_track_selected_section(
        self,
    ):
        page = self.make_page()

        self.assertTrue(
            page.home_button.isChecked()
        )

        self.assertFalse(
            page.search_button.isChecked()
        )

        page.show_search()

        self.assertFalse(
            page.home_button.isChecked()
        )

        self.assertTrue(
            page.search_button.isChecked()
        )

    def test_page_owns_no_network_credentials_or_main_navigation(
        self,
    ):
        source = inspect.getsource(
            page_module
        )

        lowered = source.casefold()

        for forbidden in (
            "spotifywebapiclient",
            "credential_store",
            "access_token",
            "refresh_token",
            "oauth",
            "mainwindow",
            "switch_page",
        ):
            self.assertNotIn(
                forbidden,
                lowered,
            )
