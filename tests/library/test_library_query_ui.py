from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace

from src.music.song import Song
from src.ui.library import LibraryPage


class FakeHistoryStore:
    def __init__(self):
        self.record_play_calls = []
        self.update_current_calls = []
        self.record_event_calls = []

    def record_play(self, song):
        self.record_play_calls.append(song)

    def update_current(self, song):
        self.update_current_calls.append(song)

    def record_event(self, song):
        self.record_event_calls.append(song)
        return True


class FakeLabel:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class LibraryQueryUiTests(unittest.TestCase):
    def setUp(self):
        self.today = datetime(
            2026,
            7,
            16,
            21,
            30,
        )

    def test_all_time_has_no_boundaries(self):
        self.assertEqual(
            LibraryPage._date_range_bounds(
                "all",
                self.today,
            ),
            ("", ""),
        )

    def test_unknown_range_has_no_boundaries(self):
        self.assertEqual(
            LibraryPage._date_range_bounds(
                "unknown",
                self.today,
            ),
            ("", ""),
        )

    def test_today_range_is_inclusive(self):
        self.assertEqual(
            LibraryPage._date_range_bounds(
                "today",
                self.today,
            ),
            (
                "2026-07-16",
                "2026-07-16",
            ),
        )

    def test_last_seven_days_is_inclusive(self):
        self.assertEqual(
            LibraryPage._date_range_bounds(
                "last_7",
                self.today,
            ),
            (
                "2026-07-10",
                "2026-07-16",
            ),
        )

    def test_last_thirty_days_is_inclusive(self):
        self.assertEqual(
            LibraryPage._date_range_bounds(
                "last_30",
                self.today,
            ),
            (
                "2026-06-17",
                "2026-07-16",
            ),
        )

    def test_this_year_starts_on_january_first(self):
        self.assertEqual(
            LibraryPage._date_range_bounds(
                "this_year",
                self.today,
            ),
            (
                "2026-01-01",
                "2026-07-16",
            ),
        )

    def test_page_offset_is_aligned_and_clamped(self):
        self.assertEqual(
            LibraryPage._normalise_page_offset(
                total_tracks=136,
                page_size=50,
                offset=999,
            ),
            100,
        )

        self.assertEqual(
            LibraryPage._normalise_page_offset(
                total_tracks=0,
                page_size=50,
                offset=50,
            ),
            0,
        )

    def test_page_summary_formats_result_window(self):
        self.assertEqual(
            LibraryPage._page_summary(
                total_tracks=136,
                offset=50,
                row_count=50,
            ),
            "Showing 51-100 of 136",
        )

        self.assertEqual(
            LibraryPage._page_summary(
                total_tracks=0,
                offset=0,
                row_count=0,
            ),
            "0 results",
        )

    @staticmethod
    def make_logic_page():
        page = SimpleNamespace(
            history_store=FakeHistoryStore(),
            _last_track_key=None,
            _last_status=None,
            _current_track_event_recorded=False,
            latest_status=FakeLabel(),
            load_history=lambda: None,
        )

        return page

    @staticmethod
    def make_song(
        *,
        title="Test Song",
        playing=False,
    ):
        return Song(
            title=title,
            artist="Test Artist",
            album="Test Album",
            source_app="Spotify.exe",
            playing=playing,
        )

    def test_paused_new_track_waits_for_event(
        self,
    ):
        page = self.make_logic_page()

        LibraryPage.add_song(
            page,
            self.make_song(
                playing=False,
            ),
        )

        self.assertEqual(
            len(
                page.history_store
                .record_play_calls
            ),
            1,
        )

        self.assertEqual(
            len(
                page.history_store
                .record_event_calls
            ),
            0,
        )

        self.assertFalse(
            page._current_track_event_recorded
        )

    def test_paused_to_playing_records_one_event(
        self,
    ):
        page = self.make_logic_page()

        LibraryPage.add_song(
            page,
            self.make_song(
                playing=False,
            ),
        )

        LibraryPage.add_song(
            page,
            self.make_song(
                playing=True,
            ),
        )

        self.assertEqual(
            len(
                page.history_store
                .record_play_calls
            ),
            1,
        )

        self.assertEqual(
            len(
                page.history_store
                .update_current_calls
            ),
            1,
        )

        self.assertEqual(
            len(
                page.history_store
                .record_event_calls
            ),
            1,
        )

        self.assertTrue(
            page._current_track_event_recorded
        )

    def test_resume_after_confirmed_play_adds_no_event(
        self,
    ):
        page = self.make_logic_page()

        LibraryPage.add_song(
            page,
            self.make_song(
                playing=True,
            ),
        )

        LibraryPage.add_song(
            page,
            self.make_song(
                playing=False,
            ),
        )

        LibraryPage.add_song(
            page,
            self.make_song(
                playing=True,
            ),
        )

        self.assertEqual(
            len(
                page.history_store
                .record_play_calls
            ),
            1,
        )

        self.assertEqual(
            len(
                page.history_store
                .update_current_calls
            ),
            2,
        )

        self.assertEqual(
            len(
                page.history_store
                .record_event_calls
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()
