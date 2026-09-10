from __future__ import annotations

import inspect
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from src.spotify.qt_playlist_runtime import (
    OPERATION_PLAYLIST_ITEMS,
)
from src.ui.dashboard import (
    DashboardPage,
)
from src.ui.main_window import (
    MainWindow,
)
from src.ui.spotify_playlist_dashboard_card import (
    MAX_RENDERED_TRACKS,
    SpotifyPlaylistDashboardSnapshot,
)


PLAYLIST_ID = "playlist123"

ARTWORK = (
    "https://i.scdn.co/image/"
    "playlist123"
)


class FakeSignal:

    def __init__(
        self,
    ):
        self.callbacks = []

    def connect(
        self,
        callback,
    ):
        self.callbacks.append(
            callback
        )

    def emit(
        self,
        *args,
    ):
        for callback in tuple(
            self.callbacks
        ):
            callback(
                *args
            )


class FakeRuntime:

    def __init__(
        self,
        *,
        busy=False,
    ):
        self.busy = bool(
            busy
        )

        self.calls = []

        self.playlist_load_calls = 0

        self.playlist_items_ready = (
            FakeSignal()
        )

        self.failed = (
            FakeSignal()
        )

        self.operation_finished = (
            FakeSignal()
        )

    def load_playlists(
        self,
    ):
        if self.busy:
            raise RuntimeError(
                "busy"
            )

        self.playlist_load_calls += 1

        self.busy = True

    def load_playlist_items(
        self,
        playlist_id,
        *,
        limit=50,
        offset=0,
        market=None,
    ):
        if self.busy:
            raise RuntimeError(
                "busy"
            )

        self.calls.append(
            {
                "playlist_id":
                    playlist_id,
                "limit":
                    limit,
                "offset":
                    offset,
                "market":
                    market,
            }
        )

        self.busy = True


class FakeArtworkLoader:

    def __init__(
        self,
    ):
        self.requests = []

        self.artwork_ready = (
            FakeSignal()
        )

        self.artwork_failed = (
            FakeSignal()
        )

    def request(
        self,
        reference,
    ):
        self.requests.append(
            reference
        )

        return True


class FakeCard:

    def __init__(
        self,
    ):
        self._snapshot = None
        self.pixmaps = []
        self.clear_artwork_calls = 0

    @property
    def snapshot(
        self,
    ):
        return self._snapshot

    def set_snapshot(
        self,
        snapshot,
    ):
        self._snapshot = snapshot

    def clear_snapshot(
        self,
    ):
        self._snapshot = None

    def set_artwork_pixmap(
        self,
        pixmap,
    ):
        self.pixmaps.append(
            pixmap
        )

        return True

    def clear_artwork(
        self,
    ):
        self.clear_artwork_calls += 1


def playlist_summary(
    *,
    total=207,
    artwork=ARTWORK,
):
    return SimpleNamespace(
        spotify_id=PLAYLIST_ID,
        name="All I need",
        owner_name="03:37am",
        total_items=total,
        artwork_reference=artwork,
    )


def resolved_item(
    position,
    *,
    title="Track",
    artist="Artist",
    duration_ms=180000,
    is_local=False,
    local_available=None,
    playable=True,
):
    return SimpleNamespace(
        position=position,
        is_local=is_local,
        local_available=local_available,
        unified_track=(
            SimpleNamespace(
                title=title,
                artist=artist,
                duration_ms=duration_ms,
                playable=playable,
            )
        ),
    )


def resolved_page(
    *items,
    offset=0,
    limit=50,
    total=None,
):
    if total is None:
        total = (
            offset
            + len(
                items
            )
        )

    return SimpleNamespace(
        items=tuple(
            items
        ),
        offset=offset,
        limit=limit,
        total=total,
    )


def ready_result(
    page,
):
    return SimpleNamespace(
        ready=True,
        resolved_page=page,
        local_snapshot_available=True,
        message="Loaded.",
    )


class ContentHarness:

    def __init__(
        self,
        *,
        configured=True,
        summary=None,
    ):
        self.spotify_playlist_card = (
            FakeCard()
        )

        self._config = (
            SimpleNamespace(
                playlist_id=PLAYLIST_ID,
            )
            if configured
            else None
        )

        self._summary = (
            summary
            if summary is not None
            else playlist_summary()
        )

        self.header_refreshes = 0

    def _spotify_playlist_dashboard_config(
        self,
    ):
        return self._config

    def _spotify_playlist_dashboard_summary(
        self,
        playlist_id,
    ):
        if self._summary is None:
            return None

        if (
            str(
                playlist_id
            ).strip()
            != str(
                self._summary.spotify_id
            ).strip()
        ):
            return None

        return self._summary

    def _refresh_spotify_playlist_dashboard_header(
        self,
    ):
        self.header_refreshes += 1

        if (
            self._config is None
            or self._summary is None
        ):
            self.spotify_playlist_card.clear_snapshot()
            return False

        self.spotify_playlist_card.set_snapshot(
            SpotifyPlaylistDashboardSnapshot.build(
                playlist_id=(
                    self._summary.spotify_id
                ),
                title=(
                    self._summary.name
                ),
                owner=(
                    self._summary.owner_name
                ),
                track_count=(
                    self._summary.total_items
                ),
                tracks=(),
            )
        )

        return True


for method_name in (
    "install_spotify_playlist_dashboard_content_sources",
    "_request_spotify_playlist_dashboard_summary_restore",
    "prime_spotify_playlist_dashboard_catalog",
    "restore_spotify_playlist_dashboard_assignment",
    "_reset_spotify_playlist_dashboard_content",
    "_spotify_playlist_dashboard_rendered_tracks",
    "_render_spotify_playlist_dashboard_content",
    "_spotify_playlist_dashboard_artwork_reference_for_playlist",
    "_request_spotify_playlist_dashboard_artwork",
    "_request_spotify_playlist_dashboard_content_page",
    "refresh_spotify_playlist_dashboard_card",
    "handle_spotify_playlist_dashboard_items_ready",
    "handle_spotify_playlist_dashboard_runtime_failure",
    "handle_spotify_playlist_dashboard_operation_finished",
    "handle_spotify_playlist_dashboard_artwork_ready",
    "handle_spotify_playlist_dashboard_artwork_failed",
):
    setattr(
        ContentHarness,
        method_name,
        getattr(
            DashboardPage,
            method_name,
        ),
    )


class DashboardSpotifyPlaylistContentTests(
    unittest.TestCase
):

    def install(
        self,
        *,
        harness=None,
        runtime=None,
        loader=None,
    ):
        if harness is None:
            harness = (
                ContentHarness()
            )

        if runtime is None:
            runtime = (
                FakeRuntime()
            )

        if loader is None:
            loader = (
                FakeArtworkLoader()
            )

        installed = (
            harness
            .install_spotify_playlist_dashboard_content_sources(
                runtime,
                loader,
            )
        )

        return (
            harness,
            runtime,
            loader,
            installed,
        )

    def refresh(
        self,
        harness,
        *,
        reload_content=False,
    ):
        return (
            harness
            .refresh_spotify_playlist_dashboard_card(
                reload_content=(
                    reload_content
                )
            )
        )

    def finish(
        self,
        runtime,
    ):
        runtime.busy = False

        runtime.operation_finished.emit(
            OPERATION_PLAYLIST_ITEMS,
            PLAYLIST_ID,
        )

    def test_main_window_installation_is_inside_build_pages(
        self,
    ):
        source = inspect.getsource(
            MainWindow.build_pages
        )

        self.assertIn(
            (
                "install_spotify_playlist_"
                "dashboard_content_sources"
            ),
            source,
        )

        self.assertIn(
            "self.spotify_playlist_runtime",
            source,
        )

        self.assertIn(
            "self.spotify_page",
            source,
        )

        self.assertIn(
            "artwork_loader",
            source,
        )

        self.assertNotIn(
            "SpotifyArtworkLoader(",
            source,
        )

    def test_header_only_refresh_preserves_b04b_return_value(
        self,
    ):
        harness = (
            ContentHarness()
        )

        result = self.refresh(
            harness
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            harness.header_refreshes,
            1,
        )

        self.assertIsNotNone(
            harness
            .spotify_playlist_card
            .snapshot
        )

        self.assertFalse(
            hasattr(
                harness,
                (
                    "_spotify_playlist_dashboard_"
                    "content_playlist_id"
                ),
            )
        )

    def test_source_installation_is_inert_until_refresh(
        self,
    ):
        (
            _harness,
            runtime,
            loader,
            installed,
        ) = self.install()

        self.assertTrue(
            installed
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

        self.assertEqual(
            loader.requests,
            [],
        )

    def test_install_does_not_shadow_artwork_helper(
        self,
    ):
        (
            harness,
            _runtime,
            _loader,
            _installed,
        ) = self.install()

        self.assertTrue(
            callable(
                harness
                ._spotify_playlist_dashboard_artwork_reference_for_playlist
            )
        )

        self.assertEqual(
            harness
            ._spotify_playlist_dashboard_active_artwork_reference,
            "",
        )

    def test_first_refresh_requests_artwork_and_page_zero(
        self,
    ):
        (
            harness,
            runtime,
            loader,
            _installed,
        ) = self.install()

        result = self.refresh(
            harness
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            [
                call[
                    "offset"
                ]
                for call
                in runtime.calls
            ],
            [
                0,
            ],
        )

        self.assertEqual(
            loader.requests,
            [
                ARTWORK,
            ],
        )

    def test_busy_runtime_defers_first_page(
        self,
    ):
        runtime = (
            FakeRuntime(
                busy=True
            )
        )

        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install(
            runtime=runtime
        )

        self.refresh(
            harness
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

        self.assertEqual(
            harness
            ._spotify_playlist_dashboard_pending_offset,
            0,
        )

        runtime.busy = False

        runtime.operation_finished.emit(
            "playlists",
            "",
        )

        self.assertEqual(
            [
                call[
                    "offset"
                ]
                for call
                in runtime.calls
            ],
            [
                0,
            ],
        )

    def test_catalogue_row_preserves_exact_position(
        self,
    ):
        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install()

        self.refresh(
            harness
        )

        runtime.playlist_items_ready.emit(
            PLAYLIST_ID,
            ready_result(
                resolved_page(
                    resolved_item(
                        4,
                        title="BAD!",
                        artist="XXXTENTACION",
                        duration_ms=94200,
                    ),
                    total=5,
                )
            ),
        )

        track = (
            harness
            .spotify_playlist_card
            .snapshot
            .tracks[
                0
            ]
        )

        self.assertEqual(
            track.position,
            4,
        )

        self.assertEqual(
            track.title,
            "BAD!",
        )

        self.assertEqual(
            track.artists,
            "XXXTENTACION",
        )

        self.assertEqual(
            track.duration_seconds,
            94,
        )

        self.assertFalse(
            track.is_local
        )

        self.assertTrue(
            track.available
        )

    def test_available_local_row_is_preserved(
        self,
    ):
        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install()

        self.refresh(
            harness
        )

        runtime.playlist_items_ready.emit(
            PLAYLIST_ID,
            ready_result(
                resolved_page(
                    resolved_item(
                        1,
                        title="Arctic Tundra (v1)",
                        artist="Juice WRLD",
                        is_local=True,
                        local_available=True,
                        playable=False,
                    ),
                    total=3,
                )
            ),
        )

        track = (
            harness
            .spotify_playlist_card
            .snapshot
            .tracks[
                0
            ]
        )

        self.assertEqual(
            track.position,
            1,
        )

        self.assertTrue(
            track.is_local
        )

        self.assertTrue(
            track.available
        )

    def test_unavailable_local_row_is_truthful(
        self,
    ):
        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install()

        self.refresh(
            harness
        )

        runtime.playlist_items_ready.emit(
            PLAYLIST_ID,
            ready_result(
                resolved_page(
                    resolved_item(
                        2,
                        title="Missing Local",
                        is_local=True,
                        local_available=False,
                        playable=False,
                    ),
                    total=3,
                )
            ),
        )

        track = (
            harness
            .spotify_playlist_card
            .snapshot
            .tracks[
                0
            ]
        )

        self.assertTrue(
            track.is_local
        )

        self.assertFalse(
            track.available
        )

    def test_stale_playlist_result_is_ignored(
        self,
    ):
        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install()

        self.refresh(
            harness
        )

        runtime.playlist_items_ready.emit(
            "stale-playlist",
            ready_result(
                resolved_page(
                    resolved_item(
                        0
                    ),
                    total=1,
                )
            ),
        )

        self.assertEqual(
            harness
            .spotify_playlist_card
            .snapshot
            .tracks,
            (),
        )

    def test_next_page_waits_for_operation_finished(
        self,
    ):
        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install()

        self.refresh(
            harness
        )

        runtime.playlist_items_ready.emit(
            PLAYLIST_ID,
            ready_result(
                resolved_page(
                    resolved_item(
                        0,
                        title="First",
                    ),
                    offset=0,
                    limit=50,
                    total=120,
                )
            ),
        )

        self.assertEqual(
            harness
            ._spotify_playlist_dashboard_pending_offset,
            50,
        )

        self.finish(
            runtime
        )

        self.assertEqual(
            [
                call[
                    "offset"
                ]
                for call
                in runtime.calls
            ],
            [
                0,
                50,
            ],
        )

    def test_header_refresh_does_not_erase_rows(
        self,
    ):
        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install()

        self.refresh(
            harness
        )

        runtime.playlist_items_ready.emit(
            PLAYLIST_ID,
            ready_result(
                resolved_page(
                    resolved_item(
                        0,
                        title="Persist Me",
                    ),
                    total=1,
                )
            ),
        )

        result = self.refresh(
            harness
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            harness
            .spotify_playlist_card
            .snapshot
            .tracks[
                0
            ]
            .title,
            "Persist Me",
        )

        self.assertEqual(
            len(
                runtime.calls
            ),
            1,
        )

    def test_resolved_total_updates_count(
        self,
    ):
        harness = (
            ContentHarness(
                summary=(
                    playlist_summary(
                        total=0
                    )
                )
            )
        )

        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install(
            harness=harness
        )

        self.refresh(
            harness
        )

        runtime.playlist_items_ready.emit(
            PLAYLIST_ID,
            ready_result(
                resolved_page(
                    resolved_item(
                        0
                    ),
                    total=207,
                )
            ),
        )

        self.assertEqual(
            harness
            .spotify_playlist_card
            .snapshot
            .track_count,
            207,
        )

    def test_matching_artwork_is_installed(
        self,
    ):
        (
            harness,
            _runtime,
            loader,
            _installed,
        ) = self.install()

        self.refresh(
            harness
        )

        pixmap = object()

        loader.artwork_ready.emit(
            ARTWORK,
            pixmap,
        )

        self.assertEqual(
            harness
            .spotify_playlist_card
            .pixmaps,
            [
                pixmap,
            ],
        )

        loader.artwork_ready.emit(
            "stale-artwork",
            object(),
        )

        self.assertEqual(
            harness
            .spotify_playlist_card
            .pixmaps,
            [
                pixmap,
            ],
        )

    def test_same_artwork_reference_is_not_requested_twice(
        self,
    ):
        (
            harness,
            _runtime,
            loader,
            _installed,
        ) = self.install()

        self.refresh(
            harness
        )

        self.refresh(
            harness
        )

        self.assertEqual(
            loader.requests,
            [
                ARTWORK,
            ],
        )

    def test_raw_position_limit_is_500(
        self,
    ):
        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install()

        self.refresh(
            harness
        )

        harness._spotify_playlist_dashboard_requested_offset = (
            450
        )

        runtime.busy = True

        harness.handle_spotify_playlist_dashboard_items_ready(
            PLAYLIST_ID,
            ready_result(
                resolved_page(
                    resolved_item(
                        499,
                        title="Visible",
                    ),
                    resolved_item(
                        500,
                        title="Beyond",
                    ),
                    offset=450,
                    limit=50,
                    total=700,
                )
            ),
        )

        self.assertEqual(
            [
                track.position
                for track
                in (
                    harness
                    .spotify_playlist_card
                    .snapshot
                    .tracks
                )
            ],
            [
                499,
            ],
        )

        self.assertIsNone(
            harness
            ._spotify_playlist_dashboard_pending_offset
        )

        self.assertEqual(
            MAX_RENDERED_TRACKS,
            500,
        )

    def test_runtime_failure_keeps_existing_rows(
        self,
    ):
        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install()

        self.refresh(
            harness
        )

        runtime.playlist_items_ready.emit(
            PLAYLIST_ID,
            ready_result(
                resolved_page(
                    resolved_item(
                        0,
                        title="Keep Me",
                    ),
                    total=120,
                )
            ),
        )

        self.finish(
            runtime
        )

        runtime.failed.emit(
            OPERATION_PLAYLIST_ITEMS,
            PLAYLIST_ID,
            "simulated",
            "Simulated failure",
        )

        self.assertEqual(
            harness
            .spotify_playlist_card
            .snapshot
            .tracks[
                0
            ]
            .title,
            "Keep Me",
        )

        self.assertIsNone(
            harness
            ._spotify_playlist_dashboard_pending_offset
        )

    def test_content_layer_adds_no_playback_or_auth_boundary(
        self,
    ):
        methods = (
            DashboardPage
            .install_spotify_playlist_dashboard_content_sources,
            DashboardPage
            ._request_spotify_playlist_dashboard_content_page,
            DashboardPage
            ._request_spotify_playlist_dashboard_artwork,
            DashboardPage
            .handle_spotify_playlist_dashboard_items_ready,
        )

        source = "\n".join(
            inspect.getsource(
                method
            )
            for method
            in methods
        ).casefold()

        forbidden = (
            "spotifywebapiclient",
            "access_token",
            "refresh_token",
            "client_secret",
            "requests.",
            "urllib",
            "play_playlist_position",
            "play_playlist_track",
            "play_track(",
            "os.startfile",
            "qmediaplayer",
            "keyboard",
            "mouse_event",
            "setforegroundwindow",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_restore_saved_assignment_starts_without_spotify_tab(
        self,
    ):
        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install()

        result = (
            harness
            .restore_spotify_playlist_dashboard_assignment()
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            runtime.playlist_load_calls,
            1,
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

        self.assertTrue(
            harness
            ._spotify_playlist_dashboard_summary_restore_pending
        )

        self.assertEqual(
            harness
            ._spotify_playlist_dashboard_pending_offset,
            0,
        )

    def test_restore_without_assignment_does_not_fetch(
        self,
    ):
        harness = ContentHarness(
            configured=False
        )

        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install(
            harness=harness
        )

        result = (
            harness
            .restore_spotify_playlist_dashboard_assignment()
        )

        self.assertFalse(
            result
        )

        self.assertEqual(
            runtime.playlist_load_calls,
            0,
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_busy_startup_waits_for_summary_before_items(
        self,
    ):
        runtime = FakeRuntime(
            busy=True
        )

        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install(
            runtime=runtime
        )

        self.assertTrue(
            harness
            .restore_spotify_playlist_dashboard_assignment()
        )

        self.assertEqual(
            runtime.playlist_load_calls,
            0,
        )

        self.assertEqual(
            harness
            ._spotify_playlist_dashboard_pending_offset,
            0,
        )

        runtime.busy = False

        runtime.operation_finished.emit(
            "search",
            "",
        )

        self.assertEqual(
            runtime.playlist_load_calls,
            1,
        )

        self.assertTrue(
            runtime.busy
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

        runtime.busy = False

        runtime.operation_finished.emit(
            "playlists",
            "",
        )

        self.assertFalse(
            harness
            ._spotify_playlist_dashboard_summary_restore_pending
        )

        self.assertEqual(
            [
                call[
                    "offset"
                ]
                for call
                in runtime.calls
            ],
            [
                0,
            ],
        )

    def test_main_window_restores_inside_connect_services_after_playlist_signal(
        self,
    ):
        source = inspect.getsource(
            MainWindow.connect_services
        )

        signal_index = source.find(
            "playlists_ready.connect"
        )

        restore_index = source.find(
            "restore_spotify_playlist_dashboard_assignment"
        )

        self.assertGreaterEqual(
            signal_index,
            0,
        )

        self.assertGreaterEqual(
            restore_index,
            0,
        )

        self.assertLess(
            signal_index,
            restore_index,
        )

    def test_catalog_prime_loads_playlists_without_saved_assignment(
        self,
    ):
        harness = ContentHarness(
            configured=False
        )

        (
            harness,
            runtime,
            _loader,
            _installed,
        ) = self.install(
            harness=harness
        )

        result = (
            harness
            .prime_spotify_playlist_dashboard_catalog()
        )

        self.assertTrue(
            result
        )

        self.assertEqual(
            runtime.playlist_load_calls,
            1,
        )

        self.assertTrue(
            harness
            ._spotify_playlist_dashboard_summary_restore_pending
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_main_window_primes_catalog_before_saved_assignment_restore(
        self,
    ):
        source = inspect.getsource(
            MainWindow.connect_services
        )

        signal_index = source.find(
            "playlists_ready.connect"
        )

        prime_index = source.find(
            "prime_spotify_playlist_dashboard_catalog"
        )

        restore_index = source.find(
            "restore_spotify_playlist_dashboard_assignment"
        )

        self.assertGreaterEqual(
            signal_index,
            0,
        )

        self.assertGreaterEqual(
            prime_index,
            0,
        )

        self.assertGreaterEqual(
            restore_index,
            0,
        )

        self.assertLess(
            signal_index,
            prime_index,
        )

        self.assertLess(
            prime_index,
            restore_index,
        )


if __name__ == "__main__":
    unittest.main()
