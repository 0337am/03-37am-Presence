from __future__ import annotations

import unittest

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
)
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.qt_search_runtime import (
    SpotifyQtSearchRuntimeError,
)
from src.ui.spotify_search import (
    SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS,
    SPOTIFY_LIVE_SEARCH_MINIMUM_CHARACTERS,
    SpotifySearchPage,
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

    def request(
        self,
        artwork_url,
    ):
        return True


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

    search_started = pyqtSignal(
        str
    )

    search_finished = pyqtSignal(
        str
    )

    def __init__(
        self,
    ):
        super().__init__()

        self.calls = []
        self.busy = False
        self.active_query = None

    def search(
        self,
        query,
        *,
        types=None,
        limit=5,
        offset=0,
        market=None,
    ):
        if self.busy:
            raise SpotifyQtSearchRuntimeError(
                "busy",
                (
                    "Spotify Search is already "
                    "running."
                ),
            )

        checked = str(
            query
        ).strip()

        self.calls.append(
            {
                "query": checked,
                "types": types,
                "limit": limit,
                "offset": offset,
                "market": market,
            }
        )

        self.active_query = checked
        self.busy = True

        self.busy_changed.emit(
            True
        )

        self.search_started.emit(
            checked
        )

    def finish(
        self,
    ):
        finished_query = (
            self.active_query
            or ""
        )

        self.active_query = None
        self.busy = False

        self.busy_changed.emit(
            False
        )

        self.search_finished.emit(
            finished_query
        )


class SpotifyLiveSearchTests(
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

    def make_page(
        self,
    ):
        runtime = FakeRuntime()

        page = SpotifySearchPage(
            runtime,
            theme_manager=(
                FakeThemeManager()
            ),
            artwork_loader=(
                FakeArtworkLoader()
            ),
        )

        self.addCleanup(
            page._live_search_timer.stop
        )

        self.addCleanup(
            page.deleteLater
        )

        return (
            page,
            runtime,
        )

    def test_live_search_timer_is_single_shot_350ms(
        self,
    ):
        page, _runtime = (
            self.make_page()
        )

        self.assertTrue(
            page._live_search_timer.isSingleShot()
        )

        self.assertEqual(
            page._live_search_timer.interval(),
            SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS,
        )

        self.assertEqual(
            SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS,
            350,
        )

    def test_one_character_does_not_trigger_live_search(
        self,
    ):
        page, runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "j"
        )

        QTest.qWait(
            (
                SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS
                + 60
            )
        )

        self.assertEqual(
            runtime.calls,
            [],
        )

        self.assertEqual(
            SPOTIFY_LIVE_SEARCH_MINIMUM_CHARACTERS,
            2,
        )

    def test_two_characters_trigger_live_search(
        self,
    ):
        page, runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "ju"
        )

        QTest.qWait(
            (
                SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS
                + 60
            )
        )

        self.assertEqual(
            [
                call["query"]
                for call in runtime.calls
            ],
            [
                "ju"
            ],
        )

    def test_rapid_typing_only_submits_newest_query(
        self,
    ):
        page, runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "ju"
        )

        QTest.qWait(
            100
        )

        page.search_input.setText(
            "juice"
        )

        QTest.qWait(
            (
                SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS
                + 60
            )
        )

        self.assertEqual(
            [
                call["query"]
                for call in runtime.calls
            ],
            [
                "juice"
            ],
        )

    def test_search_input_remains_editable_while_busy(
        self,
    ):
        page, runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "juice"
        )

        page.start_search()

        self.assertTrue(
            runtime.busy
        )

        self.assertTrue(
            page.search_input.isEnabled()
        )

        self.assertFalse(
            page.search_button.isEnabled()
        )

    def test_debounced_query_is_queued_while_busy(
        self,
    ):
        page, runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "juice"
        )

        page.start_search()

        page.search_input.setText(
            "pink"
        )

        QTest.qWait(
            (
                SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS
                + 60
            )
        )

        self.assertEqual(
            page._pending_search_query,
            "pink",
        )

        self.assertEqual(
            [
                call["query"]
                for call in runtime.calls
            ],
            [
                "juice"
            ],
        )

    def test_finished_search_launches_debounced_pending_query(
        self,
    ):
        page, runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "juice"
        )

        page.start_search()

        page.search_input.setText(
            "pink"
        )

        QTest.qWait(
            (
                SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS
                + 60
            )
        )

        runtime.finish()

        self.assertEqual(
            [
                call["query"]
                for call in runtime.calls
            ],
            [
                "juice",
            ],
        )

        QTest.qWait(
            10
        )

        self.assertEqual(
            [
                call["query"]
                for call in runtime.calls
            ],
            [
                "juice",
                "pink",
            ],
        )

    def test_deferred_pending_query_is_dropped_if_input_changes(
        self,
    ):
        page, runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "juice"
        )

        page.start_search()

        page.search_input.setText(
            "pink"
        )

        QTest.qWait(
            (
                SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS
                + 60
            )
        )

        self.assertEqual(
            page._pending_search_query,
            "pink",
        )

        runtime.finish()

        page.search_input.setText(
            "pinkpantheress"
        )

        QTest.qWait(
            10
        )

        self.assertEqual(
            [
                call["query"]
                for call in runtime.calls
            ],
            [
                "juice"
            ],
        )

        QTest.qWait(
            (
                SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS
                + 60
            )
        )

        self.assertEqual(
            [
                call["query"]
                for call in runtime.calls
            ],
            [
                "juice",
                "pinkpantheress",
            ],
        )

    def test_new_typing_cancels_old_pending_query_until_new_debounce(
        self,
    ):
        page, runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "juice"
        )

        page.start_search()

        page.search_input.setText(
            "pink"
        )

        QTest.qWait(
            (
                SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS
                + 60
            )
        )

        self.assertEqual(
            page._pending_search_query,
            "pink",
        )

        page.search_input.setText(
            "pinkpantheress"
        )

        self.assertIsNone(
            page._pending_search_query
        )

        runtime.finish()

        self.assertEqual(
            [
                call["query"]
                for call in runtime.calls
            ],
            [
                "juice"
            ],
        )

        QTest.qWait(
            (
                SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS
                + 60
            )
        )

        self.assertEqual(
            [
                call["query"]
                for call in runtime.calls
            ],
            [
                "juice",
                "pinkpantheress",
            ],
        )

    def test_changed_input_marks_active_completion_stale(
        self,
    ):
        page, _runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "juice"
        )

        page.start_search()

        page.search_input.setText(
            "pink"
        )

        self.assertTrue(
            page._should_ignore_search_completion()
        )

    def test_matching_input_accepts_active_completion(
        self,
    ):
        page, _runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "juice"
        )

        page.start_search()

        self.assertFalse(
            page._should_ignore_search_completion()
        )

    def test_clearing_input_cancels_pending_query(
        self,
    ):
        page, runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "juice"
        )

        page.start_search()

        page.search_input.setText(
            "pink"
        )

        QTest.qWait(
            (
                SPOTIFY_LIVE_SEARCH_DEBOUNCE_MS
                + 60
            )
        )

        self.assertEqual(
            page._pending_search_query,
            "pink",
        )

        page.search_input.clear()

        self.assertIsNone(
            page._pending_search_query
        )

        self.assertFalse(
            page._live_search_timer.isActive()
        )

        runtime.finish()

        self.assertEqual(
            [
                call["query"]
                for call in runtime.calls
            ],
            [
                "juice"
            ],
        )

    def test_manual_search_allows_one_character_immediately(
        self,
    ):
        page, runtime = (
            self.make_page()
        )

        page.search_input.setText(
            "j"
        )

        page.start_search()

        self.assertEqual(
            [
                call["query"]
                for call in runtime.calls
            ],
            [
                "j"
            ],
        )
