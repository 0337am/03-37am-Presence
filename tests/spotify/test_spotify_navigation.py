from __future__ import annotations

import inspect
import unittest

import src.ui.main_window as main_window_module
from src.ui.main_window import (
    MainWindow,
)


class SpotifyNavigationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.module_source = (
            inspect.getsource(
                main_window_module
            )
        )

        cls.sidebar_source = (
            inspect.getsource(
                MainWindow.build_sidebar
            )
        )

        cls.build_pages_source = (
            inspect.getsource(
                MainWindow.build_pages
            )
        )

        cls.switch_source = (
            inspect.getsource(
                MainWindow.switch_page
            )
        )

        cls.settings_source = (
            inspect.getsource(
                MainWindow.open_settings_section
            )
        )

        cls.shutdown_source = (
            inspect.getsource(
                MainWindow.shutdown
            )
        )

    def test_main_window_imports_spotify_page(
        self,
    ):
        self.assertIn(
            (
                "from src.ui.spotify_page "
                "import SpotifyPage"
            ),
            self.module_source,
        )

    def test_main_window_imports_search_and_playlist_runtimes(
        self,
    ):
        self.assertIn(
            "SpotifyQtSearchRuntime",
            self.module_source,
        )

        self.assertIn(
            "SpotifySearchService",
            self.module_source,
        )

        self.assertIn(
            "SpotifyQtPlaylistRuntime",
            self.module_source,
        )

    def test_sidebar_places_spotify_between_library_and_settings(
        self,
    ):
        library_position = (
            self.sidebar_source.index(
                "self.library_button ="
            )
        )

        spotify_position = (
            self.sidebar_source.index(
                "self.spotify_button ="
            )
        )

        settings_position = (
            self.sidebar_source.index(
                "self.settings_button ="
            )
        )

        self.assertLess(
            library_position,
            spotify_position,
        )

        self.assertLess(
            spotify_position,
            settings_position,
        )

    def test_navigation_button_order_includes_spotify_before_settings(
        self,
    ):
        list_start = (
            self.sidebar_source.index(
                "self.navigation_buttons = ["
            )
        )

        list_end = (
            self.sidebar_source.index(
                "]",
                list_start,
            )
        )

        block = (
            self.sidebar_source[
                list_start:list_end
            ]
        )

        self.assertLess(
            block.index(
                "self.spotify_button"
            ),
            block.index(
                "self.settings_button"
            ),
        )

    def test_navigation_mapping_preserves_legacy_page_indexes(
        self,
    ):
        self.assertIn(
            (
                "self.navigation_page_indexes = "
                "["
            ),
            self.sidebar_source,
        )

        compact = "".join(
            self.sidebar_source.split()
        )

        self.assertIn(
            (
                "self.navigation_page_indexes="
                "[0,1,2,5,3,4,]"
            ),
            compact,
        )

    def test_spotify_page_is_appended_after_existing_pages(
        self,
    ):
        settings_position = (
            self.build_pages_source.index(
                "self.settings_page"
            )
        )

        about_add_position = (
            self.build_pages_source.rindex(
                "self.about_page"
            )
        )

        spotify_add_position = (
            self.build_pages_source.rindex(
                "self.spotify_page"
            )
        )

        self.assertLess(
            settings_position,
            about_add_position,
        )

        self.assertLess(
            about_add_position,
            spotify_add_position,
        )

    def test_sidebar_buttons_route_to_preserved_indexes(
        self,
    ):
        compact = "".join(
            self.build_pages_source.split()
        )

        self.assertIn(
            (
                "self.spotify_button.clicked.connect("
                "lambda:self.switch_page(5))"
            ),
            compact,
        )

        self.assertIn(
            (
                "self.settings_button.clicked.connect("
                "lambda:self.switch_page(3))"
            ),
            compact,
        )

        self.assertIn(
            (
                "self.about_button.clicked.connect("
                "lambda:self.switch_page(4))"
            ),
            compact,
        )

    def test_switch_page_uses_explicit_navigation_mapping(
        self,
    ):
        self.assertIn(
            "navigation_page_indexes",
            self.switch_source,
        )

        self.assertIn(
            "zip(",
            self.switch_source,
        )

        compact_switch = "".join(
            self.switch_source.split()
        )

        self.assertIn(
            "navigation_page_index==page_index",
            compact_switch,
        )

    def test_settings_page_index_remains_three(
        self,
    ):
        compact_settings = "".join(
            self.settings_source.split()
        )

        compact_switch = "".join(
            self.switch_source.split()
        )

        self.assertIn(
            "self.switch_page(3)",
            compact_settings,
        )

        self.assertIn(
            "ifpage_index==3:",
            compact_switch,
        )

    def test_search_runtime_is_production_composed(
        self,
    ):
        self.assertIn(
            "SpotifyQtSearchRuntime(",
            self.build_pages_source,
        )

        self.assertIn(
            "SpotifySearchService(",
            self.build_pages_source,
        )

        self.assertIn(
            "self.spotify_session_manager",
            self.build_pages_source,
        )

    def test_playlist_runtime_and_spotify_page_are_production_composed(
        self,
    ):
        self.assertIn(
            "SpotifyQtPlaylistRuntime(",
            self.build_pages_source,
        )

        self.assertIn(
            "self.spotify_playlist_service",
            self.build_pages_source,
        )

        self.assertIn(
            "self.spotify_resolved_playlist_service",
            self.build_pages_source,
        )

        self.assertIn(
            "SpotifyPage(",
            self.build_pages_source,
        )

        self.assertIn(
            "search_runtime=",
            self.build_pages_source,
        )

        self.assertIn(
            "playlist_runtime=",
            self.build_pages_source,
        )

    def test_build_pages_does_not_eagerly_fetch_spotify_content(
        self,
    ):
        self.assertNotIn(
            ".load_playlists(",
            self.build_pages_source,
        )

        self.assertNotIn(
            ".load_playlist_items(",
            self.build_pages_source,
        )

        self.assertNotIn(
            ".search(",
            self.build_pages_source,
        )

    def test_shutdown_closes_search_playlist_and_connection_runtimes(
        self,
    ):
        for runtime_name in (
            "spotify_search_runtime",
            "spotify_playlist_runtime",
            "spotify_connection_runtime",
        ):
            self.assertIn(
                runtime_name,
                self.shutdown_source,
            )

        self.assertIn(
            '"shutdown"',
            self.shutdown_source,
        )
