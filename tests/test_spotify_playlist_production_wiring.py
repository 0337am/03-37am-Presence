from __future__ import annotations

import inspect
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import src.ui.main_window as main_window_module
from src.ui.main_window import (
    MainWindow,
)


class SpotifyPlaylistProductionWiringTests(
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

        cls.build_pages_source = (
            inspect.getsource(
                MainWindow.build_pages
            )
        )

        cls.provider_source = (
            inspect.getsource(
                MainWindow
                ._spotify_local_candidates
            )
        )

    def test_main_window_imports_playlist_production_stack(
        self,
    ):
        for marker in (
            "SpotifyConnectionController",
            "SpotifySessionManager",
            "SpotifyPlaylistService",
            "SpotifyResolvedPlaylistService",
        ):
            self.assertIn(
                marker,
                self.module_source,
            )

    def test_build_pages_constructs_one_shared_session_manager(
        self,
    ):
        self.assertEqual(
            self.build_pages_source.count(
                "SpotifySessionManager("
            ),
            1,
        )

        self.assertIn(
            (
                "self.spotify_session_manager"
            ),
            self.build_pages_source,
        )

    def test_shared_session_manager_precedes_connection_runtime(
        self,
    ):
        session_position = (
            self.build_pages_source.index(
                "self.spotify_session_manager"
            )
        )

        runtime_position = (
            self.build_pages_source.index(
                "self.spotify_connection_runtime"
            )
        )

        self.assertLess(
            session_position,
            runtime_position,
        )

    def test_connection_runtime_receives_controller_factory(
        self,
    ):
        self.assertIn(
            (
                "controller_factory=("
            ),
            self.build_pages_source,
        )

        self.assertIn(
            (
                "self._create_spotify_connection_controller"
            ),
            self.build_pages_source,
        )

    def test_settings_exists_before_resolved_playlist_service(
        self,
    ):
        settings_position = (
            self.build_pages_source.index(
                "self.settings_page = SettingsPage"
            )
        )

        resolved_position = (
            self.build_pages_source.index(
                (
                    "self.spotify_resolved_playlist_service"
                )
            )
        )

        self.assertLess(
            settings_position,
            resolved_position,
        )

    def test_playlist_service_uses_shared_session_manager(
        self,
    ):
        self.assertIn(
            (
                "SpotifyPlaylistService("
            ),
            self.build_pages_source,
        )

        self.assertIn(
            (
                "self.spotify_session_manager"
            ),
            self.build_pages_source,
        )

    def test_resolved_service_uses_playlist_service_and_candidate_provider(
        self,
    ):
        self.assertIn(
            (
                "SpotifyResolvedPlaylistService("
            ),
            self.build_pages_source,
        )

        self.assertIn(
            (
                "self.spotify_playlist_service"
            ),
            self.build_pages_source,
        )

        self.assertIn(
            (
                "self._spotify_local_candidates"
            ),
            self.build_pages_source,
        )

    def test_candidate_provider_does_not_start_scans(
        self,
    ):
        forbidden = (
            "start_scan",
            ".scan(",
            "rescan",
            "LocalMusicIndex",
        )

        for marker in forbidden:
            self.assertNotIn(
                marker,
                self.provider_source,
            )

    def test_build_pages_does_not_fetch_playlist_data(
        self,
    ):
        for marker in (
            ".get_playlist_items(",
            ".get_current_playlists(",
        ):
            self.assertNotIn(
                marker,
                self.build_pages_source,
            )

    def test_candidate_provider_returns_none_without_settings(
        self,
    ):
        fake = SimpleNamespace()

        result = (
            MainWindow
            ._spotify_local_candidates(
                fake
            )
        )

        self.assertIsNone(
            result
        )

    def test_candidate_provider_returns_none_without_runtime(
        self,
    ):
        fake = SimpleNamespace(
            settings_page=(
                SimpleNamespace()
            )
        )

        result = (
            MainWindow
            ._spotify_local_candidates(
                fake
            )
        )

        self.assertIsNone(
            result
        )

    def test_candidate_provider_returns_none_without_scan_result(
        self,
    ):
        fake = SimpleNamespace(
            settings_page=(
                SimpleNamespace(
                    local_music_runtime=(
                        SimpleNamespace(
                            latest_result=None
                        )
                    )
                )
            )
        )

        result = (
            MainWindow
            ._spotify_local_candidates(
                fake
            )
        )

        self.assertIsNone(
            result
        )

    def test_candidate_provider_returns_cached_candidates(
        self,
    ):
        candidates = (
            object(),
            object(),
        )

        fake = SimpleNamespace(
            settings_page=(
                SimpleNamespace(
                    local_music_runtime=(
                        SimpleNamespace(
                            latest_result=(
                                SimpleNamespace(
                                    candidates=(
                                        candidates
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )

        result = (
            MainWindow
            ._spotify_local_candidates(
                fake
            )
        )

        self.assertIs(
            result,
            candidates,
        )

    def test_controller_factory_uses_shared_manager_and_browser_bridge(
        self,
    ):
        manager = object()
        browser_opener = object()
        controller = object()

        fake = SimpleNamespace(
            spotify_session_manager=manager
        )

        with patch.object(
            main_window_module,
            "SpotifyConnectionController",
            return_value=controller,
        ) as factory:
            result = (
                MainWindow
                ._create_spotify_connection_controller(
                    fake,
                    "client123",
                    browser_opener=(
                        browser_opener
                    ),
                )
            )

        self.assertIs(
            result,
            controller,
        )

        factory.assert_called_once_with(
            "client123",
            session_manager=manager,
            browser_opener=browser_opener,
        )


class SpotifyPlaylistProductionBoundaryTests(
    unittest.TestCase
):
    def test_production_wiring_has_no_private_runtime_session_access(
        self,
    ):
        source = inspect.getsource(
            MainWindow
        )

        forbidden = (
            "spotify_connection_runtime._",
            "_controller._session_manager",
        )

        for marker in forbidden:
            self.assertNotIn(
                marker,
                source,
            )
