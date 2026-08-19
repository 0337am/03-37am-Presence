import unittest
from pathlib import Path
from types import SimpleNamespace

from src.ui.library import LibraryPage


class FakeLabel:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = str(text)


class FakeHistoryStore:
    def __init__(self, insights):
        self.insights = insights
        self.calls = []

    def get_insights(self, **arguments):
        self.calls.append(arguments)
        return self.insights


class LibraryInsightsUiTests(unittest.TestCase):
    @staticmethod
    def make_ranked(
        name,
        *,
        detail="",
        play_count=1,
        track_count=1,
    ):
        return SimpleNamespace(
            name=name,
            detail=detail,
            play_count=play_count,
            track_count=track_count,
        )

    @staticmethod
    def make_event(
        *,
        title="Goodbye",
        artist="Juice WRLD",
        played_at="2026-07-16 22:39:47",
    ):
        return SimpleNamespace(
            title=title,
            artist=artist,
            played_at=played_at,
        )

    def make_page(self, insights):
        store = FakeHistoryStore(
            insights
        )

        page = SimpleNamespace(
            history_store=store,
            artist_insight=FakeLabel(),
            album_insight=FakeLabel(),
            confirmed_play_insight=FakeLabel(),
            listening_day_insight=FakeLabel(),
            current_streak_insight=FakeLabel(),
            longest_streak_insight=FakeLabel(),
            insights_summary=FakeLabel(),
            _format_count=LibraryPage._format_count,
            _format_ranked_insight=(
                LibraryPage._format_ranked_insight
            ),
            _format_recent_event=(
                LibraryPage._format_recent_event
            ),
        )

        return page, store

    def test_load_insights_updates_metrics(
        self,
    ):
        insights = SimpleNamespace(
            unique_artist_count=20,
            unique_album_count=74,
            detailed_play_count=3,
            listening_day_count=1,
            current_streak_days=1,
            longest_streak_days=4,
            top_tracks=(
                self.make_ranked(
                    "Toxic Humans",
                    detail="Juice WRLD",
                    play_count=16,
                ),
            ),
            top_artists=(
                self.make_ranked(
                    "Juice WRLD",
                    play_count=88,
                    track_count=42,
                ),
            ),
            top_albums=(
                self.make_ranked(
                    "Goodbye & Good Riddance",
                    detail="Juice WRLD",
                    play_count=40,
                    track_count=12,
                ),
            ),
            recent_events=(
                self.make_event(),
            ),
        )

        page, store = self.make_page(
            insights
        )

        LibraryPage.load_insights(
            page
        )

        self.assertEqual(
            page.artist_insight.text,
            "20 ARTISTS",
        )

        self.assertEqual(
            page.album_insight.text,
            "74 ALBUMS",
        )

        self.assertEqual(
            page.confirmed_play_insight.text,
            "3 CONFIRMED PLAYS",
        )

        self.assertEqual(
            page.listening_day_insight.text,
            "1 LISTENING DAY",
        )

        self.assertEqual(
            page.current_streak_insight.text,
            "CURRENT 1 DAY",
        )

        self.assertEqual(
            page.longest_streak_insight.text,
            "LONGEST 4 DAYS",
        )

        self.assertIn(
            "Top track: Toxic Humans "
            "by Juice WRLD | 16 plays",
            page.insights_summary.text,
        )

        self.assertIn(
            "Top artist: Juice WRLD | 88 plays",
            page.insights_summary.text,
        )

        self.assertIn(
            "Top album: Goodbye & Good Riddance "
            "by Juice WRLD | 40 plays",
            page.insights_summary.text,
        )

        self.assertIn(
            "Latest confirmed play: "
            "Goodbye by Juice WRLD",
            page.insights_summary.text,
        )

        self.assertEqual(
            store.calls,
            [
                {
                    "top_limit": 1,
                    "recent_limit": 1,
                }
            ],
        )

    def test_empty_insights_use_clear_fallbacks(
        self,
    ):
        insights = SimpleNamespace(
            unique_artist_count=0,
            unique_album_count=0,
            detailed_play_count=0,
            listening_day_count=0,
            current_streak_days=0,
            longest_streak_days=0,
            top_tracks=(),
            top_artists=(),
            top_albums=(),
            recent_events=(),
        )

        page, _ = self.make_page(
            insights
        )

        LibraryPage.load_insights(
            page
        )

        self.assertEqual(
            page.artist_insight.text,
            "0 ARTISTS",
        )

        self.assertEqual(
            page.confirmed_play_insight.text,
            "0 CONFIRMED PLAYS",
        )

        self.assertIn(
            "Top track: No listening history yet",
            page.insights_summary.text,
        )

        self.assertIn(
            "Latest confirmed play: None yet",
            page.insights_summary.text,
        )

    def test_singular_metric_labels(
        self,
    ):
        insights = SimpleNamespace(
            unique_artist_count=1,
            unique_album_count=1,
            detailed_play_count=1,
            listening_day_count=1,
            current_streak_days=1,
            longest_streak_days=1,
            top_tracks=(),
            top_artists=(),
            top_albums=(),
            recent_events=(),
        )

        page, _ = self.make_page(
            insights
        )

        LibraryPage.load_insights(
            page
        )

        self.assertEqual(
            page.artist_insight.text,
            "1 ARTIST",
        )

        self.assertEqual(
            page.album_insight.text,
            "1 ALBUM",
        )

        self.assertEqual(
            page.confirmed_play_insight.text,
            "1 CONFIRMED PLAY",
        )

        self.assertEqual(
            page.listening_day_insight.text,
            "1 LISTENING DAY",
        )

    def test_ranked_artist_needs_no_byline(
        self,
    ):
        item = self.make_ranked(
            "Juice WRLD",
            play_count=88,
        )

        formatted = (
            LibraryPage._format_ranked_insight(
                (item,),
                "Missing",
            )
        )

        self.assertEqual(
            formatted,
            "Juice WRLD | 88 plays",
        )

    def test_ranked_fallback_is_preserved(
        self,
    ):
        self.assertEqual(
            LibraryPage._format_ranked_insight(
                (),
                "Nothing recorded",
            ),
            "Nothing recorded",
        )

    def test_recent_event_without_artist(
        self,
    ):
        event = self.make_event(
            title="Instrumental",
            artist="",
            played_at="",
        )

        self.assertEqual(
            LibraryPage._format_recent_event(
                (event,)
            ),
            "Instrumental",
        )

        self.assertEqual(
            LibraryPage._format_recent_event(
                ()
            ),
            "None yet",
        )

    def test_source_contains_accessible_wiring(
        self,
    ):
        source = Path(
            "src/ui/library.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'self.load_insights()',
            source,
        )

        self.assertIn(
            '"Library insights"',
            source,
        )

        self.assertIn(
            '"Confirmed detailed plays"',
            source,
        )

        self.assertIn(
            '"Current listening streak"',
            source,
        )

        self.assertIn(
            "confirmed activity",
            source,
        )

        self.assertIn(
            "QGridLayout",
            source,
        )


if __name__ == "__main__":
    unittest.main()
