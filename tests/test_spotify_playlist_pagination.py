from __future__ import annotations

import unittest
from types import SimpleNamespace

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.playlist_models import (
    SpotifyPlaylistSummary,
)
from src.spotify.qt_playlist_runtime import (
    OPERATION_PLAYLIST_ITEMS,
)
from src.ui.spotify_playlist_detail import (
    SpotifyPlaylistDetail,
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
        return {}


class PaginationRuntime(
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

    operation_finished = pyqtSignal(
        str,
        str,
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
                "playlist_id": playlist_id,
                "limit": limit,
                "offset": offset,
                "market": market,
            }
        )


def playlist(
    total=94,
):
    return SpotifyPlaylistSummary(
        spotify_id="playlist123",
        name="LLJW",
        spotify_uri=(
            "spotify:playlist:playlist123"
        ),
        owner_name="03:37am",
        total_items=total,
    )


def item(
    title="Rental",
):
    return SimpleNamespace(
        is_local=False,
        local_available=None,
        unified_track=(
            SimpleNamespace(
                title=title,
                artist="Juice WRLD",
                duration_ms=240000,
            )
        ),
    )


def page(
    *items,
    total,
    offset,
    limit=50,
    omitted_items=0,
):
    return SimpleNamespace(
        items=tuple(
            items
        ),
        total=total,
        offset=offset,
        limit=limit,
        omitted_items=omitted_items,
        local_count=0,
        unavailable_local_count=0,
    )


def ready(
    resolved_page,
):
    return SimpleNamespace(
        ready=True,
        resolved_page=resolved_page,
        message="Loaded.",
        local_snapshot_available=True,
    )


class SpotifyPlaylistPaginationTests(
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
        total=94,
    ):
        runtime = (
            PaginationRuntime()
        )

        widget = (
            SpotifyPlaylistDetail(
                runtime,
                theme_manager=(
                    FakeThemeManager()
                ),
            )
        )

        widget.set_playlist(
            playlist(
                total
            )
        )

        self.addCleanup(
            widget.deleteLater
        )

        return (
            widget,
            runtime,
        )

    def items(
        self,
        count,
        *,
        start=0,
    ):
        return tuple(
            item(
                title=(
                    "Track "
                    + str(
                        start
                        + index
                        + 1
                    )
                )
            )
            for index in range(
                count
            )
        )

    def test_page_two_waits_for_runtime_cleanup(
        self,
    ):
        widget, runtime = (
            self.make_detail()
        )

        self.assertTrue(
            widget.load()
        )

        widget.handle_items_ready(
            "playlist123",
            ready(
                page(
                    *self.items(
                        50
                    ),
                    total=94,
                    offset=0,
                )
            ),
        )

        self.assertEqual(
            len(
                widget.rows
            ),
            50,
        )

        self.assertEqual(
            [
                call[
                    "offset"
                ]
                for call in runtime.calls
            ],
            [
                0,
            ],
        )

        widget.handle_operation_finished(
            OPERATION_PLAYLIST_ITEMS,
            "playlist123",
        )

        self.assertEqual(
            [
                call[
                    "offset"
                ]
                for call in runtime.calls
            ],
            [
                0,
                50,
            ],
        )

    def test_second_page_appends_to_full_playlist(
        self,
    ):
        widget, runtime = (
            self.make_detail()
        )

        widget.load()

        widget.handle_items_ready(
            "playlist123",
            ready(
                page(
                    *self.items(
                        50
                    ),
                    total=94,
                    offset=0,
                )
            ),
        )

        widget.handle_operation_finished(
            OPERATION_PLAYLIST_ITEMS,
            "playlist123",
        )

        widget.handle_items_ready(
            "playlist123",
            ready(
                page(
                    *self.items(
                        44,
                        start=50,
                    ),
                    total=94,
                    offset=50,
                )
            ),
        )

        self.assertEqual(
            len(
                widget.rows
            ),
            94,
        )

        self.assertEqual(
            widget.rows[
                50
            ].number_label.text(),
            "51",
        )

        self.assertIn(
            "94 / 94 tracks loaded",
            widget.status_label.text(),
        )

        widget.handle_operation_finished(
            OPERATION_PLAYLIST_ITEMS,
            "playlist123",
        )

        self.assertEqual(
            len(
                runtime.calls
            ),
            2,
        )

    def test_next_offset_uses_page_limit_not_rendered_count(
        self,
    ):
        widget, runtime = (
            self.make_detail()
        )

        widget.load()

        widget.handle_items_ready(
            "playlist123",
            ready(
                page(
                    *self.items(
                        49
                    ),
                    total=94,
                    offset=0,
                    limit=50,
                    omitted_items=1,
                )
            ),
        )

        widget.handle_operation_finished(
            OPERATION_PLAYLIST_ITEMS,
            "playlist123",
        )

        self.assertEqual(
            runtime.calls[
                1
            ][
                "offset"
            ],
            50,
        )

    def test_large_playlist_requests_every_page(
        self,
    ):
        widget, runtime = (
            self.make_detail(
                total=250
            )
        )

        widget.load()

        for offset in (
            0,
            50,
            100,
            150,
            200,
        ):
            widget.handle_items_ready(
                "playlist123",
                ready(
                    page(
                        *self.items(
                            50,
                            start=offset,
                        ),
                        total=250,
                        offset=offset,
                    )
                ),
            )

            if offset < 200:
                widget.handle_operation_finished(
                    OPERATION_PLAYLIST_ITEMS,
                    "playlist123",
                )

        self.assertEqual(
            [
                call[
                    "offset"
                ]
                for call in runtime.calls
            ],
            [
                0,
                50,
                100,
                150,
                200,
            ],
        )

        self.assertEqual(
            len(
                widget.rows
            ),
            250,
        )

        self.assertIn(
            "250 / 250 tracks loaded",
            widget.status_label.text(),
        )

    def test_back_stops_pending_pagination(
        self,
    ):
        widget, runtime = (
            self.make_detail()
        )

        widget.load()

        widget.handle_items_ready(
            "playlist123",
            ready(
                page(
                    *self.items(
                        50
                    ),
                    total=94,
                    offset=0,
                )
            ),
        )

        widget.back_button.click()

        widget.handle_operation_finished(
            OPERATION_PLAYLIST_ITEMS,
            "playlist123",
        )

        self.assertEqual(
            len(
                runtime.calls
            ),
            1,
        )

        self.assertFalse(
            widget._pending_next_page
        )

    def test_unrequested_same_playlist_result_is_ignored(
        self,
    ):
        widget, _runtime = (
            self.make_detail()
        )

        widget.handle_items_ready(
            "playlist123",
            ready(
                page(
                    item(),
                    total=1,
                    offset=0,
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

    def test_later_page_failure_preserves_first_page(
        self,
    ):
        widget, runtime = (
            self.make_detail()
        )

        widget.load()

        widget.handle_items_ready(
            "playlist123",
            ready(
                page(
                    *self.items(
                        50
                    ),
                    total=94,
                    offset=0,
                )
            ),
        )

        widget.handle_operation_finished(
            OPERATION_PLAYLIST_ITEMS,
            "playlist123",
        )

        self.assertEqual(
            len(
                runtime.calls
            ),
            2,
        )

        widget.handle_runtime_failure(
            OPERATION_PLAYLIST_ITEMS,
            "playlist123",
            "rate_limit",
            "Try again shortly.",
        )

        self.assertEqual(
            len(
                widget.rows
            ),
            50,
        )

        self.assertIn(
            "50 tracks loaded",
            widget.status_label.text(),
        )

        self.assertIn(
            "Try again shortly.",
            widget.status_label.text(),
        )

        widget.handle_operation_finished(
            OPERATION_PLAYLIST_ITEMS,
            "playlist123",
        )

        self.assertEqual(
            len(
                runtime.calls
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
