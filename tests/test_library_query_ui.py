from __future__ import annotations

import unittest
from datetime import datetime

from src.ui.library import LibraryPage


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


if __name__ == "__main__":
    unittest.main()
