from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from src.library.history_store import (
    HistoryStore,
)
from src.music.song import Song


class HistoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        self.database_path = (
            Path(self.temp_directory.name)
            / "history.db"
        )

    def tearDown(self):
        self.temp_directory.cleanup()

    def make_store(self):
        return HistoryStore(
            database_path=self.database_path
        )

    @staticmethod
    def make_song(
        *,
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        source_app="Spotify",
        playing=True,
    ):
        return Song(
            title=title,
            artist=artist,
            album=album,
            duration="3:00",
            position="0:10",
            playing=playing,
            source_app=source_app,
        )

    def record_song(
        self,
        store,
        *,
        title,
        artist="Test Artist",
        album="Test Album",
        source_app="Spotify.exe",
        plays=1,
    ):
        for _ in range(plays):
            store.record_play(
                self.make_song(
                    title=title,
                    artist=artist,
                    album=album,
                    source_app=source_app,
                )
            )

    def set_last_played(
        self,
        title,
        timestamp,
    ):
        with closing(
            sqlite3.connect(
                self.database_path
            )
        ) as connection:
            connection.execute(
                """
                UPDATE tracks
                SET last_played = ?
                WHERE title = ?
                """,
                (
                    timestamp,
                    title,
                ),
            )

            connection.commit()

    def test_fresh_database_uses_schema_two(
        self,
    ):
        store = self.make_store()

        self.assertEqual(
            store.schema_version(),
            2,
        )

        with closing(
            sqlite3.connect(
                self.database_path
            )
        ) as connection:
            rows = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()

        table_names = {
            str(row[0])
            for row in rows
        }

        self.assertIn(
            "tracks",
            table_names,
        )

        self.assertIn(
            "play_events",
            table_names,
        )

    def test_existing_database_migrates_safely(
        self,
    ):
        with closing(
            sqlite3.connect(
                self.database_path
            )
        ) as connection:
            connection.execute(
                """
                CREATE TABLE tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_key TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    album TEXT NOT NULL,
                    source_app TEXT NOT NULL,
                    first_played TEXT NOT NULL,
                    last_played TEXT NOT NULL,
                    play_count INTEGER NOT NULL DEFAULT 1,
                    last_status TEXT NOT NULL DEFAULT 'Paused'
                )
                """
            )

            connection.execute(
                """
                INSERT INTO tracks (
                    track_key,
                    title,
                    artist,
                    album,
                    source_app,
                    first_played,
                    last_played,
                    play_count,
                    last_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-key",
                    "Legacy Song",
                    "Legacy Artist",
                    "Legacy Album",
                    "Spotify",
                    "2026-07-01 12:00:00",
                    "2026-07-02 12:00:00",
                    4,
                    "Paused",
                ),
            )

            connection.commit()

        store = self.make_store()

        self.assertEqual(
            store.schema_version(),
            2,
        )

        self.assertEqual(
            store.count_tracks(),
            1,
        )

        self.assertEqual(
            store.total_plays(),
            4,
        )

        self.assertEqual(
            store.count_events(),
            0,
        )

        tracks = store.list_tracks()

        self.assertEqual(
            tracks[0].title,
            "Legacy Song",
        )

    def test_record_play_adds_event(
        self,
    ):
        store = self.make_store()
        song = self.make_song()

        store.record_play(song)

        self.assertEqual(
            store.count_tracks(),
            1,
        )

        self.assertEqual(
            store.total_plays(),
            1,
        )

        self.assertEqual(
            store.count_events(),
            1,
        )

        event = store.list_events()[0]

        self.assertEqual(
            event.title,
            song.title,
        )

        self.assertEqual(
            event.artist,
            song.artist,
        )

        self.assertEqual(
            event.source_app,
            song.source_app,
        )

    def test_repeated_play_creates_new_event(
        self,
    ):
        store = self.make_store()
        song = self.make_song()

        store.record_play(song)
        store.record_play(song)

        self.assertEqual(
            store.count_tracks(),
            1,
        )

        self.assertEqual(
            store.total_plays(),
            2,
        )

        self.assertEqual(
            store.count_events(),
            2,
        )

    def test_status_update_does_not_add_event(
        self,
    ):
        store = self.make_store()

        store.record_play(
            self.make_song(
                playing=True,
            )
        )

        store.update_current(
            self.make_song(
                playing=False,
            )
        )

        self.assertEqual(
            store.count_events(),
            1,
        )

        track = store.list_tracks()[0]

        self.assertEqual(
            track.last_status,
            "Paused",
        )

    def test_deleting_track_cascades_events(
        self,
    ):
        store = self.make_store()

        store.record_play(
            self.make_song()
        )

        track = store.list_tracks()[0]

        store.delete_track(
            track.track_id
        )

        self.assertEqual(
            store.count_tracks(),
            0,
        )

        self.assertEqual(
            store.count_events(),
            0,
        )

    def test_clear_history_removes_everything(
        self,
    ):
        store = self.make_store()

        store.record_play(
            self.make_song(
                title="First Song",
            )
        )

        store.record_play(
            self.make_song(
                title="Second Song",
            )
        )

        store.clear_history()

        self.assertEqual(
            store.count_tracks(),
            0,
        )

        self.assertEqual(
            store.total_plays(),
            0,
        )

        self.assertEqual(
            store.count_events(),
            0,
        )

    def test_query_searches_all_text_fields(
        self,
    ):
        store = self.make_store()

        self.record_song(
            store,
            title="Neon Rain",
            artist="Night Artist",
            album="Glass City",
        )

        self.record_song(
            store,
            title="Quiet Track",
            artist="Other Artist",
            album="Plain Album",
        )

        by_title = store.query_tracks(
            search_text="neon",
        )

        by_artist = store.query_tracks(
            search_text="night artist",
        )

        by_album = store.query_tracks(
            search_text="glass city",
        )

        self.assertEqual(
            by_title.total_tracks,
            1,
        )

        self.assertEqual(
            by_artist.total_tracks,
            1,
        )

        self.assertEqual(
            by_album.total_tracks,
            1,
        )

    def test_query_search_escapes_wildcards(
        self,
    ):
        store = self.make_store()

        self.record_song(
            store,
            title="100% Real",
        )

        self.record_song(
            store,
            title="Ordinary Song",
        )

        percent_result = store.query_tracks(
            search_text="%",
        )

        underscore_result = store.query_tracks(
            search_text="_",
        )

        self.assertEqual(
            [
                track.title
                for track
                in percent_result.tracks
            ],
            ["100% Real"],
        )

        self.assertEqual(
            underscore_result.total_tracks,
            0,
        )

    def test_query_filters_named_sources(
        self,
    ):
        store = self.make_store()

        self.record_song(
            store,
            title="Spotify Track",
            source_app="Spotify.exe",
        )

        self.record_song(
            store,
            title="Chrome Track",
            source_app="GoogleChrome.exe",
        )

        self.record_song(
            store,
            title="Edge Track",
            source_app="msedge.exe",
        )

        spotify = store.query_tracks(
            source_filter="spotify",
        )

        chrome = store.query_tracks(
            source_filter="chrome",
        )

        edge = store.query_tracks(
            source_filter="edge",
        )

        self.assertEqual(
            spotify.tracks[0].title,
            "Spotify Track",
        )

        self.assertEqual(
            chrome.tracks[0].title,
            "Chrome Track",
        )

        self.assertEqual(
            edge.tracks[0].title,
            "Edge Track",
        )

    def test_query_filters_other_sources(
        self,
    ):
        store = self.make_store()

        self.record_song(
            store,
            title="Spotify Track",
            source_app="Spotify.exe",
        )

        self.record_song(
            store,
            title="Mystery Track",
            source_app="MoonPlayer.exe",
        )

        result = store.query_tracks(
            source_filter="other",
        )

        self.assertEqual(
            result.total_tracks,
            1,
        )

        self.assertEqual(
            result.tracks[0].title,
            "Mystery Track",
        )

    def test_query_sorts_most_played(
        self,
    ):
        store = self.make_store()

        self.record_song(
            store,
            title="One Play",
            plays=1,
        )

        self.record_song(
            store,
            title="Three Plays",
            plays=3,
        )

        self.record_song(
            store,
            title="Two Plays",
            plays=2,
        )

        result = store.query_tracks(
            sort_mode="most_played",
        )

        self.assertEqual(
            [
                track.title
                for track
                in result.tracks
            ],
            [
                "Three Plays",
                "Two Plays",
                "One Play",
            ],
        )

    def test_query_applies_inclusive_date_range(
        self,
    ):
        store = self.make_store()

        self.record_song(
            store,
            title="Before",
        )

        self.record_song(
            store,
            title="Inside",
        )

        self.record_song(
            store,
            title="After",
        )

        self.set_last_played(
            "Before",
            "2026-07-10 23:59:59",
        )

        self.set_last_played(
            "Inside",
            "2026-07-11 22:15:00",
        )

        self.set_last_played(
            "After",
            "2026-07-12 00:00:00",
        )

        result = store.query_tracks(
            date_from="2026-07-11",
            date_to="2026-07-11",
        )

        self.assertEqual(
            result.total_tracks,
            1,
        )

        self.assertEqual(
            result.tracks[0].title,
            "Inside",
        )

    def test_query_paginates_with_stable_totals(
        self,
    ):
        store = self.make_store()

        self.record_song(
            store,
            title="Alpha",
            plays=3,
        )

        self.record_song(
            store,
            title="Beta",
            plays=2,
        )

        self.record_song(
            store,
            title="Gamma",
            plays=1,
        )

        result = store.query_tracks(
            sort_mode="most_played",
            limit=2,
            offset=0,
        )

        self.assertEqual(
            len(result.tracks),
            2,
        )

        self.assertEqual(
            result.total_tracks,
            3,
        )

        self.assertEqual(
            result.total_plays,
            6,
        )

        self.assertTrue(
            result.has_more
        )

    def test_query_unknown_sort_uses_newest(
        self,
    ):
        store = self.make_store()

        self.record_song(
            store,
            title="Older",
        )

        self.record_song(
            store,
            title="Newer",
        )

        self.set_last_played(
            "Older",
            "2026-07-10 12:00:00",
        )

        self.set_last_played(
            "Newer",
            "2026-07-11 12:00:00",
        )

        result = store.query_tracks(
            sort_mode="DROP TABLE tracks",
        )

        self.assertEqual(
            result.tracks[0].title,
            "Newer",
        )

        self.assertEqual(
            store.count_tracks(),
            2,
        )

    def test_query_rejects_invalid_dates(
        self,
    ):
        store = self.make_store()

        with self.assertRaisesRegex(
            ValueError,
            "date_from",
        ):
            store.query_tracks(
                date_from="11/07/2026",
            )

        with self.assertRaisesRegex(
            ValueError,
            "date_to",
        ):
            store.query_tracks(
                date_to="tomorrow",
            )

    def test_list_tracks_remains_compatible(
        self,
    ):
        store = self.make_store()

        self.record_song(
            store,
            title="Needle Star",
        )

        tracks = store.list_tracks(
            search_text="needle",
            limit=10,
        )

        self.assertIsInstance(
            tracks,
            list,
        )

        self.assertEqual(
            len(tracks),
            1,
        )

        self.assertEqual(
            tracks[0].title,
            "Needle Star",
        )

    def test_paused_record_does_not_add_event(
        self,
    ):
        store = self.make_store()

        store.record_play(
            self.make_song(
                playing=False,
            )
        )

        self.assertEqual(
            store.count_tracks(),
            1,
        )

        self.assertEqual(
            store.total_plays(),
            1,
        )

        self.assertEqual(
            store.count_events(),
            0,
        )

    def test_record_event_confirms_play_without_increment(
        self,
    ):
        store = self.make_store()

        store.record_play(
            self.make_song(
                playing=False,
            )
        )

        recorded = store.record_event(
            self.make_song(
                playing=True,
            )
        )

        self.assertTrue(
            recorded
        )

        self.assertEqual(
            store.total_plays(),
            1,
        )

        self.assertEqual(
            store.count_events(),
            1,
        )

        event = store.list_events()[0]

        self.assertEqual(
            event.status,
            "Playing",
        )

    def test_record_event_ignores_paused_state(
        self,
    ):
        store = self.make_store()

        store.record_play(
            self.make_song(
                playing=False,
            )
        )

        recorded = store.record_event(
            self.make_song(
                playing=False,
            )
        )

        self.assertFalse(
            recorded
        )

        self.assertEqual(
            store.count_events(),
            0,
        )

    def test_empty_insights_are_safe(
        self,
    ):
        store = self.make_store()

        insights = store.get_insights(
            today="2026-07-16",
        )

        self.assertEqual(
            insights.aggregate_track_count,
            0,
        )

        self.assertEqual(
            insights.aggregate_play_count,
            0,
        )

        self.assertEqual(
            insights.unique_artist_count,
            0,
        )

        self.assertEqual(
            insights.unique_album_count,
            0,
        )

        self.assertEqual(
            insights.detailed_play_count,
            0,
        )

        self.assertEqual(
            insights.listening_day_count,
            0,
        )

        self.assertEqual(
            insights.current_streak_days,
            0,
        )

        self.assertEqual(
            insights.longest_streak_days,
            0,
        )

        self.assertEqual(
            insights.top_tracks,
            (),
        )

        self.assertEqual(
            insights.recent_events,
            (),
        )

    def test_insights_rank_aggregate_history(
        self,
    ):
        store = self.make_store()

        for _ in range(3):
            store.record_play(
                self.make_song(
                    title="First Track",
                    artist="Artist One",
                    album="Album One",
                    playing=True,
                )
            )

        for _ in range(2):
            store.record_play(
                self.make_song(
                    title="Second Track",
                    artist="Artist One",
                    album="Album Two",
                    playing=True,
                )
            )

        store.record_play(
            self.make_song(
                title="Third Track",
                artist="Artist Two",
                album="Album Three",
                playing=True,
            )
        )

        insights = store.get_insights(
            top_limit=3,
            today="2026-07-16",
        )

        self.assertEqual(
            insights.aggregate_track_count,
            3,
        )

        self.assertEqual(
            insights.aggregate_play_count,
            6,
        )

        self.assertEqual(
            insights.unique_artist_count,
            2,
        )

        self.assertEqual(
            insights.unique_album_count,
            3,
        )

        self.assertEqual(
            insights.top_tracks[0].name,
            "First Track",
        )

        self.assertEqual(
            insights.top_tracks[0].play_count,
            3,
        )

        self.assertEqual(
            insights.top_artists[0].name,
            "Artist One",
        )

        self.assertEqual(
            insights.top_artists[0].play_count,
            5,
        )

        self.assertEqual(
            insights.top_artists[0].track_count,
            2,
        )

        self.assertEqual(
            insights.top_albums[0].name,
            "Album One",
        )

    def test_paused_events_are_excluded(
        self,
    ):
        store = self.make_store()

        store.record_play(
            self.make_song(
                title="Legacy Paused",
                artist="Test Artist",
                album="Test Album",
                playing=True,
            )
        )

        with store._connect() as connection:
            connection.execute(
                """
                UPDATE play_events
                SET status = 'Paused'
                WHERE title = ?
                """,
                (
                    "Legacy Paused",
                ),
            )

        insights = store.get_insights(
            today="2026-07-16",
        )

        self.assertEqual(
            insights.aggregate_play_count,
            1,
        )

        self.assertEqual(
            insights.detailed_play_count,
            0,
        )

        self.assertEqual(
            insights.listening_day_count,
            0,
        )

        self.assertEqual(
            insights.recent_events,
            (),
        )

    def test_detailed_days_recent_and_streak(
        self,
    ):
        store = self.make_store()

        for title in (
            "Day One",
            "Day Two",
            "Day Three",
        ):
            store.record_play(
                self.make_song(
                    title=title,
                    artist="Timeline Artist",
                    album="Timeline Album",
                    playing=True,
                )
            )

        timestamps = {
            "Day One": "2026-07-14 12:00:00",
            "Day Two": "2026-07-15 12:00:00",
            "Day Three": "2026-07-16 12:00:00",
        }

        with store._connect() as connection:
            for title, timestamp in timestamps.items():
                connection.execute(
                    """
                    UPDATE play_events
                    SET played_at = ?
                    WHERE title = ?
                    """,
                    (
                        timestamp,
                        title,
                    ),
                )

        insights = store.get_insights(
            today="2026-07-16",
        )

        self.assertEqual(
            insights.detailed_play_count,
            3,
        )

        self.assertEqual(
            insights.listening_day_count,
            3,
        )

        self.assertEqual(
            insights.current_streak_days,
            3,
        )

        self.assertEqual(
            insights.longest_streak_days,
            3,
        )

        self.assertEqual(
            insights.first_detailed_play,
            "2026-07-14 12:00:00",
        )

        self.assertEqual(
            insights.latest_detailed_play,
            "2026-07-16 12:00:00",
        )

        self.assertEqual(
            [
                event.title
                for event
                in insights.recent_events
            ],
            [
                "Day Three",
                "Day Two",
                "Day One",
            ],
        )

    def test_streak_gap_behavior(
        self,
    ):
        current, longest = (
            HistoryStore._calculate_streaks(
                [
                    "2026-07-08",
                    "2026-07-09",
                    "2026-07-12",
                    "2026-07-13",
                    "2026-07-14",
                ],
                today="2026-07-16",
            )
        )

        self.assertEqual(
            current,
            0,
        )

        self.assertEqual(
            longest,
            3,
        )

        current, longest = (
            HistoryStore._calculate_streaks(
                [
                    "2026-07-13",
                    "2026-07-14",
                    "2026-07-15",
                ],
                today="2026-07-16",
            )
        )

        self.assertEqual(
            current,
            3,
        )

        self.assertEqual(
            longest,
            3,
        )

    def test_insight_limits_are_applied(
        self,
    ):
        store = self.make_store()

        for index in range(4):
            store.record_play(
                self.make_song(
                    title=f"Track {index}",
                    artist=f"Artist {index}",
                    album=f"Album {index}",
                    playing=True,
                )
            )

        insights = store.get_insights(
            top_limit=2,
            recent_limit=2,
            today="2026-07-16",
        )

        self.assertEqual(
            len(insights.top_tracks),
            2,
        )

        self.assertEqual(
            len(insights.top_artists),
            2,
        )

        self.assertEqual(
            len(insights.top_albums),
            2,
        )

        self.assertEqual(
            len(insights.recent_events),
            2,
        )



if __name__ == "__main__":
    unittest.main()
