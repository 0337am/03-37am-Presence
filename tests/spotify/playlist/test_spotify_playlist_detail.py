from __future__ import annotations

import inspect
import unittest
from types import SimpleNamespace

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
)

import src.ui.spotify_playlist_detail as detail_module
from src.spotify.playlist_models import (
    SpotifyPlaylistSummary,
)
from src.spotify.qt_playlist_runtime import (
    OPERATION_PLAYLIST_ITEMS,
)
from src.ui.spotify_playlist_detail import (
    SpotifyPlaylistDetail,
    SpotifyPlaylistTrackRow,
    format_duration,
)
from src.ui.spotify_playlist_widgets import (
    SpotifyPlaylistHome,
    SpotifyPlaylistRow,
)
from src.ui.spotify_page import (
    SpotifyPage,
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


class FakePlaylistRuntime(
    QObject
):
    playlist_items_ready = pyqtSignal(
        str,
        object,
    )

    failed = pyqtSignal(
        str,
        str,
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

    def load_playlist_items(
        self,
        playlist_id,
        *,
        limit,
        offset,
        market=None,
    ):
        self.calls.append(
            {
                "playlist_id": (
                    playlist_id
                ),
                "limit": limit,
                "offset": offset,
                "market": market,
            }
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
        *,
        cached_pixmap=None,
    ):
        super().__init__()
        self.requests = []
        self.cached_pixmap = cached_pixmap

    def request(
        self,
        artwork_url,
    ):
        self.requests.append(
            artwork_url
        )

        if self.cached_pixmap is not None:
            self.artwork_ready.emit(
                artwork_url,
                self.cached_pixmap,
            )


def playlist(
    spotify_id="playlist123",
    name="LLJW",
):
    return SpotifyPlaylistSummary(
        spotify_id=spotify_id,
        name=name,
        spotify_uri=(
            "spotify:playlist:"
            + spotify_id
        ),
        owner_name="03:37am",
        total_items=94,
    )


def resolved_item(
    *,
    title="Rental",
    artist="Juice WRLD",
    duration_ms=240000,
    is_local=False,
    local_available=None,
    artwork_reference="",
):
    return SimpleNamespace(
        is_local=is_local,
        local_available=(
            local_available
        ),
        unified_track=(
            SimpleNamespace(
                title=title,
                artist=artist,
                duration_ms=(
                    duration_ms
                ),
                artwork_reference=(
                    artwork_reference
                ),
            )
        ),
    )


def resolved_page(
    *items,
    total=None,
    offset=0,
    limit=50,
    omitted_items=0,
):
    local_count = sum(
        1
        for item in items
        if item.is_local
    )

    unavailable = sum(
        1
        for item in items
        if (
            item.is_local
            and item.local_available
            is not True
        )
    )

    return SimpleNamespace(
        items=tuple(
            items
        ),
        total=(
            len(
                items
            )
            if total is None
            else total
        ),
        offset=offset,
        limit=limit,
        omitted_items=omitted_items,
        local_count=local_count,
        unavailable_local_count=(
            unavailable
        ),
    )


def ready_result(
    page,
    *,
    local_snapshot_available=True,
):
    return SimpleNamespace(
        ready=True,
        resolved_page=page,
        message="Loaded.",
        local_snapshot_available=(
            local_snapshot_available
        ),
    )


class SpotifyPlaylistDetailTests(
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

    def make_detail(
        self,
        *,
        artwork_loader=None,
    ):
        runtime = (
            FakePlaylistRuntime()
        )

        widget = (
            SpotifyPlaylistDetail(
                runtime,
                theme_manager=(
                    FakeThemeManager()
                ),
                artwork_loader=(
                    artwork_loader
                ),
            )
        )

        self.addCleanup(
            widget.deleteLater
        )

        return (
            widget,
            runtime,
        )

    def test_catalogue_row_requests_expected_artwork(
        self,
    ):
        loader = FakeArtworkLoader()
        reference = "https://i.scdn.co/image/album"
        row = SpotifyPlaylistTrackRow(
            resolved_item(
                artwork_reference=reference,
            ),
            number=1,
            artwork_loader=loader,
        )
        self.addCleanup(row.deleteLater)

        self.assertEqual(loader.requests, [reference])
        self.assertEqual(row.artwork_label.text(), "\u266b")

    def test_missing_artwork_keeps_fallback_without_request(
        self,
    ):
        loader = FakeArtworkLoader()
        row = SpotifyPlaylistTrackRow(
            resolved_item(),
            number=1,
            artwork_loader=loader,
        )
        self.addCleanup(row.deleteLater)

        self.assertEqual(loader.requests, [])
        self.assertEqual(row.artwork_label.text(), "\u266b")
        self.assertTrue(
            row.artwork_label.pixmap().isNull()
        )

    def test_matching_artwork_installs_pixmap(
        self,
    ):
        loader = FakeArtworkLoader()
        reference = "https://i.scdn.co/image/album"
        row = SpotifyPlaylistTrackRow(
            resolved_item(artwork_reference=reference),
            number=1,
            artwork_loader=loader,
        )
        self.addCleanup(row.deleteLater)
        pixmap = QPixmap(8, 8)

        loader.artwork_ready.emit(reference, pixmap)

        self.assertEqual(row.artwork_label.text(), "")
        self.assertIsNotNone(row.artwork_label.pixmap())

    def test_unrelated_artwork_and_failure_keep_fallback(
        self,
    ):
        loader = FakeArtworkLoader()
        reference = "https://i.scdn.co/image/album"
        row = SpotifyPlaylistTrackRow(
            resolved_item(artwork_reference=reference),
            number=1,
            artwork_loader=loader,
        )
        self.addCleanup(row.deleteLater)

        loader.artwork_ready.emit(
            "https://i.scdn.co/image/other",
            QPixmap(8, 8),
        )
        loader.artwork_failed.emit(reference)

        self.assertEqual(row.artwork_label.text(), "\u266b")
        self.assertTrue(
            row.artwork_label.pixmap().isNull()
        )

    def test_null_pixmap_keeps_fallback(
        self,
    ):
        loader = FakeArtworkLoader()
        reference = "https://i.scdn.co/image/album"
        row = SpotifyPlaylistTrackRow(
            resolved_item(artwork_reference=reference),
            number=1,
            artwork_loader=loader,
        )
        self.addCleanup(row.deleteLater)

        loader.artwork_ready.emit(reference, QPixmap())

        self.assertEqual(row.artwork_label.text(), "\u266b")
        self.assertTrue(
            row.artwork_label.pixmap().isNull()
        )

    def test_synchronous_cached_artwork_is_handled(
        self,
    ):
        loader = FakeArtworkLoader(
            cached_pixmap=QPixmap(8, 8)
        )
        reference = "https://i.scdn.co/image/album"
        row = SpotifyPlaylistTrackRow(
            resolved_item(artwork_reference=reference),
            number=1,
            artwork_loader=loader,
        )
        self.addCleanup(row.deleteLater)

        self.assertEqual(row.artwork_label.text(), "")
        self.assertIsNotNone(row.artwork_label.pixmap())

    def test_shared_album_artwork_updates_multiple_rows(
        self,
    ):
        loader = FakeArtworkLoader()
        reference = "https://i.scdn.co/image/shared"
        rows = [
            SpotifyPlaylistTrackRow(
                resolved_item(
                    title=title,
                    artwork_reference=reference,
                ),
                number=index,
                artwork_loader=loader,
            )
            for index, title in enumerate(
                ("One", "Two"),
                start=1,
            )
        ]
        for row in rows:
            self.addCleanup(row.deleteLater)

        loader.artwork_ready.emit(reference, QPixmap(8, 8))

        for row in rows:
            self.assertEqual(
                row.artwork_label.text(),
                "",
            )
            self.assertFalse(
                row.artwork_label.pixmap().isNull()
            )

    def test_good_artwork_is_not_replaced_by_failure(
        self,
    ):
        loader = FakeArtworkLoader()
        reference = "https://i.scdn.co/image/album"
        row = SpotifyPlaylistTrackRow(
            resolved_item(artwork_reference=reference),
            number=1,
            artwork_loader=loader,
        )
        self.addCleanup(row.deleteLater)
        loader.artwork_ready.emit(reference, QPixmap(8, 8))

        loader.artwork_failed.emit(reference)

        self.assertEqual(row.artwork_label.text(), "")
        self.assertIsNotNone(row.artwork_label.pixmap())

    def test_local_row_keeps_fallback_without_artwork_request(
        self,
    ):
        loader = FakeArtworkLoader()
        row = SpotifyPlaylistTrackRow(
            resolved_item(
                is_local=True,
                local_available=True,
                artwork_reference="C:\\Music\\cover.jpg",
            ),
            number=1,
            artwork_loader=loader,
        )
        self.addCleanup(row.deleteLater)

        self.assertEqual(loader.requests, [])
        self.assertEqual(row.artwork_label.text(), "\u266b")

    def test_detail_passes_shared_loader_and_rejects_old_playlist_artwork(
        self,
    ):
        loader = FakeArtworkLoader()
        widget, _runtime = self.make_detail(
            artwork_loader=loader
        )
        playlist_a = playlist(
            "playlist-a",
            "Playlist A",
        )
        playlist_b = playlist(
            "playlist-b",
            "Playlist B",
        )
        artwork_a = "https://i.scdn.co/image/artwork-a"
        artwork_b = "https://i.scdn.co/image/artwork-b"
        widget.set_playlist(playlist_a)
        widget.set_resolved_page(
            resolved_page(
                resolved_item(artwork_reference=artwork_a)
            )
        )
        widget.set_playlist(playlist_b)
        widget.set_resolved_page(
            resolved_page(
                resolved_item(artwork_reference=artwork_b)
            )
        )
        current_row = widget.rows[0]

        loader.artwork_ready.emit(artwork_a, QPixmap(8, 8))

        self.assertIs(widget.playlist, playlist_b)
        self.assertEqual(widget.title_label.text(), "Playlist B")
        self.assertEqual(
            current_row._artwork_reference,
            artwork_b,
        )
        self.assertIs(current_row.artwork_loader, loader)
        self.assertEqual(current_row.artwork_label.text(), "\u266b")
        self.assertTrue(
            current_row.artwork_label.pixmap().isNull()
        )

        loader.artwork_ready.emit(artwork_b, QPixmap(8, 8))

        self.assertEqual(current_row.artwork_label.text(), "")
        self.assertFalse(
            current_row.artwork_label.pixmap().isNull()
        )

    def test_duration_formatter_uses_minutes_and_seconds(
        self,
    ):
        self.assertEqual(
            format_duration(
                240000
            ),
            "4:00",
        )

        self.assertEqual(
            format_duration(
                131000
            ),
            "2:11",
        )

    def test_duration_formatter_supports_hours(
        self,
    ):
        self.assertEqual(
            format_duration(
                3723000
            ),
            "1:02:03",
        )

    def test_catalogue_row_has_no_local_badge(
        self,
    ):
        row = (
            SpotifyPlaylistTrackRow(
                resolved_item(),
                number=1,
            )
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            row.title_label.text(),
            "Rental",
        )

        self.assertEqual(
            row.artist_label.text(),
            "Juice WRLD",
        )

        self.assertEqual(
            row.duration_label.text(),
            "4:00",
        )

        self.assertFalse(
            row.local_badge.isVisible()
        )

    def test_track_row_controls_are_owned_children_not_windows(
        self,
    ):
        row = (
            SpotifyPlaylistTrackRow(
                resolved_item(),
                number=1,
            )
        )

        self.addCleanup(
            row.deleteLater
        )

        controls = (
            row.number_label,
            row.title_label,
            row.artist_label,
            row.local_badge,
            row.duration_label,
        )

        for control in controls:
            self.assertIs(
                control.parentWidget(),
                row,
            )

            self.assertFalse(
                control.isWindow()
            )

    def test_available_local_row_is_marked_local(
        self,
    ):
        row = (
            SpotifyPlaylistTrackRow(
                resolved_item(
                    is_local=True,
                    local_available=True,
                ),
                number=2,
            )
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            row.local_badge.text(),
            "LOCAL",
        )

        self.assertEqual(
            row.local_badge.objectName(),
            "spotifyPlaylistLocalBadge",
        )

    def test_unavailable_local_row_is_marked_unavailable(
        self,
    ):
        row = (
            SpotifyPlaylistTrackRow(
                resolved_item(
                    is_local=True,
                    local_available=False,
                ),
                number=3,
            )
        )

        self.addCleanup(
            row.deleteLater
        )

        self.assertEqual(
            row.local_badge.text(),
            "LOCAL • UNAVAILABLE",
        )

        self.assertEqual(
            row.local_badge.objectName(),
            "spotifyPlaylistUnavailableBadge",
        )

    def test_detail_construction_is_network_passive(
        self,
    ):
        _widget, runtime = (
            self.make_detail()
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_set_playlist_updates_header_without_loading(
        self,
    ):
        widget, runtime = (
            self.make_detail()
        )

        widget.set_playlist(
            playlist()
        )

        self.assertEqual(
            widget.title_label.text(),
            "LLJW",
        )

        self.assertIn(
            "03:37am",
            widget.subtitle_label.text(),
        )

        self.assertIn(
            "94 tracks",
            widget.subtitle_label.text(),
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

    def test_load_requests_first_fifty_items(
        self,
    ):
        widget, runtime = (
            self.make_detail()
        )

        widget.set_playlist(
            playlist()
        )

        self.assertTrue(
            widget.load()
        )

        self.assertEqual(
            runtime.calls,
            [
                {
                    "playlist_id": (
                        "playlist123"
                    ),
                    "limit": 50,
                    "offset": 0,
                    "market": None,
                }
            ],
        )

    def test_busy_runtime_defers_request_until_available(
        self,
    ):
        widget, runtime = (
            self.make_detail()
        )

        runtime.busy = True

        widget.set_playlist(
            playlist()
        )

        self.assertFalse(
            widget.load()
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

        runtime.busy = False

        widget.handle_busy_changed(
            False
        )

        self.assertEqual(
            len(
                runtime.calls
            ),
            1,
        )

    def test_ready_result_populates_track_rows(
        self,
    ):
        widget, _runtime = (
            self.make_detail()
        )

        widget.set_playlist(
            playlist()
        )

        widget.load()

        page = resolved_page(
            resolved_item(
                title="Rental",
            ),
            resolved_item(
                title="Toxic Humans",
                is_local=True,
                local_available=True,
            ),
            resolved_item(
                title="Missing Song",
                is_local=True,
                local_available=False,
            ),
            total=94,
        )

        widget.handle_items_ready(
            "playlist123",
            ready_result(
                page
            ),
        )

        self.assertEqual(
            len(
                widget.rows
            ),
            3,
        )

        self.assertEqual(
            widget.rows[
                1
            ].local_badge.text(),
            "LOCAL",
        )

        self.assertEqual(
            widget.rows[
                2
            ].local_badge.text(),
            "LOCAL • UNAVAILABLE",
        )

        self.assertIn(
            "3 / 94 tracks loaded",
            widget.status_label.text(),
        )

        self.assertIn(
            "2 local",
            widget.status_label.text(),
        )

        self.assertIn(
            "1 unavailable",
            widget.status_label.text(),
        )

    def test_stale_result_is_ignored(
        self,
    ):
        widget, _runtime = (
            self.make_detail()
        )

        widget.set_playlist(
            playlist()
        )

        widget.handle_items_ready(
            "different-playlist",
            ready_result(
                resolved_page(
                    resolved_item()
                )
            ),
        )

        self.assertEqual(
            widget.rows,
            [],
        )

        self.assertIsNone(
            widget.last_result
        )

\
    def test_ready_result_updates_header_with_real_total(
        self,
    ):
        widget, _runtime = (
            self.make_detail()
        )

        widget.set_playlist(
            playlist()
        )

        self.assertIn(
            "94 tracks",
            widget.subtitle_label.text(),
        )

        widget.load()

        page = resolved_page(
            resolved_item(
                title="Rental",
            ),
            total=35,
        )

        widget.handle_items_ready(
            "playlist123",
            ready_result(
                page
            ),
        )

        self.assertIn(
            "35 tracks",
            widget.subtitle_label.text(),
        )

        self.assertNotIn(
            "94 tracks",
            widget.subtitle_label.text(),
        )

    def test_forbidden_result_uses_track_list_unavailable_state(
        self,
    ):
        widget, _runtime = (
            self.make_detail()
        )

        widget.set_playlist(
            playlist()
        )

        widget.load()

        widget.handle_items_ready(
            "playlist123",
            SimpleNamespace(
                ready=False,
                error_code="forbidden",
                message=(
                    "Spotify playlists could "
                    "not be loaded."
                ),
            ),
        )

        self.assertEqual(
            widget.empty_label.text(),
            "Track list unavailable.",
        )


        self.assertIn(
            "track count unavailable",
            widget.subtitle_label.text(),
        )

        self.assertNotIn(
            "0 tracks",
            widget.subtitle_label.text(),
        )

        self.assertEqual(
            widget.status_label.text(),
            (
                "Spotify did not allow this app "
                "to load tracks for this playlist."
            ),
        )

    def test_forbidden_runtime_failure_uses_track_list_unavailable_state(
        self,
    ):
        widget, _runtime = (
            self.make_detail()
        )

        widget.set_playlist(
            playlist()
        )

        widget.load()

        widget.handle_runtime_failure(
            OPERATION_PLAYLIST_ITEMS,
            "playlist123",
            "forbidden",
            (
                "Spotify playlists could "
                "not be loaded."
            ),
        )

        self.assertEqual(
            widget.empty_label.text(),
            "Track list unavailable.",
        )


        self.assertIn(
            "track count unavailable",
            widget.subtitle_label.text(),
        )

        self.assertNotIn(
            "0 tracks",
            widget.subtitle_label.text(),
        )

        self.assertEqual(
            widget.status_label.text(),
            (
                "Spotify did not allow this app "
                "to load tracks for this playlist."
            ),
        )

\
    def test_playlist_subtitle_uses_ascii_separator(
        self,
    ):
        widget, _runtime = (
            self.make_detail()
        )

        widget.set_playlist(
            playlist()
        )

        self.assertEqual(
            widget.subtitle_label.text(),
            "03:37am | 94 tracks",
        )

        widget.load()

        page = resolved_page(
            resolved_item(
                title="Rental",
            ),
            total=35,
        )

        widget.handle_items_ready(
            "playlist123",
            ready_result(
                page
            ),
        )

        self.assertEqual(
            widget.subtitle_label.text(),
            "03:37am | 35 tracks",
        )

    def test_forbidden_playlist_subtitle_uses_ascii_separator(
        self,
    ):
        widget, _runtime = (
            self.make_detail()
        )

        widget.set_playlist(
            playlist()
        )

        widget.load()

        widget.handle_items_ready(
            "playlist123",
            SimpleNamespace(
                ready=False,
                error_code="forbidden",
                message=(
                    "Spotify playlists could "
                    "not be loaded."
                ),
            ),
        )

        self.assertEqual(
            widget.subtitle_label.text(),
            (
                "03:37am | "
                "track count unavailable"
            ),
        )

    def test_non_ready_and_runtime_failures_are_user_safe(
        self,
    ):
        widget, _runtime = (
            self.make_detail()
        )

        widget.set_playlist(
            playlist()
        )

        widget.load()

        widget.handle_items_ready(
            "playlist123",
            SimpleNamespace(
                ready=False,
                message=(
                    "Reconnect Spotify."
                ),
            ),
        )

        self.assertEqual(
            widget.status_label.text(),
            "Reconnect Spotify.",
        )

        widget.load()

        widget.handle_runtime_failure(
            OPERATION_PLAYLIST_ITEMS,
            "playlist123",
            "rate_limit",
            "Try again shortly.",
        )

        self.assertEqual(
            widget.status_label.text(),
            "Try again shortly.",
        )

        widget.handle_runtime_failure(
            "playlists",
            "",
            "ignored",
            "Wrong operation.",
        )

        self.assertEqual(
            widget.status_label.text(),
            "Try again shortly.",
        )

    def test_back_button_emits_request(
        self,
    ):
        widget, _runtime = (
            self.make_detail()
        )

        observed = []

        widget.back_requested.connect(
            lambda:
            observed.append(
                True
            )
        )

        widget.back_button.click()

        self.assertEqual(
            observed,
            [
                True,
            ],
        )

    def test_home_and_page_sources_expose_detail_activation_wiring(
        self,
    ):
        row_source = (
            inspect.getsource(
                SpotifyPlaylistRow
            )
        )

        home_source = (
            inspect.getsource(
                SpotifyPlaylistHome
            )
        )

        page_source = (
            inspect.getsource(
                SpotifyPage
            )
        )

        detail_source = (
            inspect.getsource(
                detail_module
            )
        )

        self.assertIn(
            "activated = pyqtSignal(object)",
            row_source,
        )

        self.assertIn(
            "def activate(",
            row_source,
        )

        self.assertIn(
            "playlist_activated = pyqtSignal(object)",
            home_source,
        )

        self.assertIn(
            ".activated.connect(",
            inspect.getsource(
                SpotifyPlaylistHome
                .set_playlist_page
            ),
        )

        for marker in (
            "_install_playlist_detail",
            "show_playlist_detail",
            "playlist_activated.connect",
            "back_requested.connect",
            "SPOTIFY_PLAYLIST_DETAIL_INDEX",
        ):
            self.assertIn(
                marker,
                page_source,
            )

        for forbidden in (
            "urllib",
            "requests.",
            "SpotifyWebApiClient",
            "access_token",
            "refresh_token",
            "client_secret",
        ):
            self.assertNotIn(
                forbidden,
                detail_source,
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
