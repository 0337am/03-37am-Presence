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


if __name__ == "__main__":
    unittest.main()
