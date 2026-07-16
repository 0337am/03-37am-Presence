from __future__ import annotations

import hashlib
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.music.song import Song


@dataclass(frozen=True)
class HistoryTrack:
    track_id: int
    title: str
    artist: str
    album: str
    source_app: str
    first_played: str
    last_played: str
    play_count: int
    last_status: str


@dataclass(frozen=True)
class ListeningEvent:
    event_id: int
    track_id: int
    track_key: str
    title: str
    artist: str
    album: str
    source_app: str
    played_at: str
    status: str


class HistoryStore:
    """
    Persistent listening history backed by SQLite.

    The database is stored in the application's
    Local AppData directory so it survives updates
    and application restarts.
    """

    SCHEMA_VERSION = 2

    def __init__(
        self,
        database_path: str | Path | None = None,
    ):
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else self._get_database_path()
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._create_schema()

    def _get_database_path(self) -> Path:
        local_app_data = os.getenv(
            "LOCALAPPDATA",
            "",
        ).strip()

        if local_app_data:
            data_directory = (
                Path(local_app_data)
                / "0337am Presence"
            )
        else:
            data_directory = (
                Path.home()
                / ".0337am-presence"
            )

        return (
            data_directory
            / "library.db"
        )

    @contextmanager
    def _connect(
        self,
    ) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
        )

        try:
            connection.row_factory = (
                sqlite3.Row
            )

            connection.execute(
                "PRAGMA journal_mode = WAL"
            )

            connection.execute(
                "PRAGMA foreign_keys = ON"
            )

            yield connection
            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def _create_schema(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tracks (
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
                CREATE INDEX IF NOT EXISTS
                index_tracks_last_played
                ON tracks(last_played DESC)
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS play_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id INTEGER NOT NULL,
                    track_key TEXT NOT NULL,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    album TEXT NOT NULL,
                    source_app TEXT NOT NULL,
                    played_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Playing',
                    FOREIGN KEY(track_id)
                        REFERENCES tracks(id)
                        ON DELETE CASCADE
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                index_play_events_played_at
                ON play_events(
                    played_at DESC,
                    id DESC
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                index_play_events_track
                ON play_events(track_id)
                """
            )

            connection.execute(
                f"PRAGMA user_version = "
                f"{self.SCHEMA_VERSION}"
            )

    def record_play(
        self,
        song: Song,
    ):
        values = self._song_values(
            song
        )

        now = self._current_timestamp()

        with self._connect() as connection:
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
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)

                ON CONFLICT(track_key)
                DO UPDATE SET
                    title = excluded.title,
                    artist = excluded.artist,
                    album = excluded.album,
                    source_app = excluded.source_app,
                    last_played = excluded.last_played,
                    play_count = tracks.play_count + 1,
                    last_status = excluded.last_status
                """,
                (
                    values["track_key"],
                    values["title"],
                    values["artist"],
                    values["album"],
                    values["source_app"],
                    now,
                    now,
                    values["status"],
                ),
            )

            track_row = connection.execute(
                """
                SELECT id
                FROM tracks
                WHERE track_key = ?
                """,
                (
                    values["track_key"],
                ),
            ).fetchone()

            if track_row is None:
                raise RuntimeError(
                    "Recorded track could not be found."
                )

            connection.execute(
                """
                INSERT INTO play_events (
                    track_id,
                    track_key,
                    title,
                    artist,
                    album,
                    source_app,
                    played_at,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(track_row["id"]),
                    values["track_key"],
                    values["title"],
                    values["artist"],
                    values["album"],
                    values["source_app"],
                    now,
                    values["status"],
                ),
            )

    def update_current(
        self,
        song: Song,
    ):
        values = self._song_values(
            song
        )

        now = self._current_timestamp()
        track_exists = False

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tracks
                SET
                    title = ?,
                    artist = ?,
                    album = ?,
                    source_app = ?,
                    last_played = ?,
                    last_status = ?
                WHERE track_key = ?
                """,
                (
                    values["title"],
                    values["artist"],
                    values["album"],
                    values["source_app"],
                    now,
                    values["status"],
                    values["track_key"],
                ),
            )

            track_exists = (
                cursor.rowcount > 0
            )

        if not track_exists:
            self.record_play(song)

    def list_tracks(
        self,
        search_text: str = "",
        limit: int = 1000,
    ) -> list[HistoryTrack]:
        search_text = (
            search_text.strip()
        )

        safe_limit = max(
            1,
            min(int(limit), 5000),
        )

        query = """
            SELECT
                id,
                title,
                artist,
                album,
                source_app,
                first_played,
                last_played,
                play_count,
                last_status
            FROM tracks
        """

        parameters: list[object] = []

        if search_text:
            search_pattern = (
                f"%{search_text}%"
            )

            query += """
                WHERE
                    title LIKE ?
                    OR artist LIKE ?
                    OR album LIKE ?
                    OR source_app LIKE ?
            """

            parameters.extend(
                [
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                ]
            )

        query += """
            ORDER BY
                last_played DESC,
                id DESC
            LIMIT ?
        """

        parameters.append(
            safe_limit
        )

        with self._connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            self._row_to_track(row)
            for row in rows
        ]

    def list_events(
        self,
        limit: int = 5000,
    ) -> list[ListeningEvent]:
        safe_limit = max(
            1,
            min(int(limit), 50000),
        )

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    track_id,
                    track_key,
                    title,
                    artist,
                    album,
                    source_app,
                    played_at,
                    status
                FROM play_events
                ORDER BY
                    played_at DESC,
                    id DESC
                LIMIT ?
                """,
                (
                    safe_limit,
                ),
            ).fetchall()

        return [
            self._row_to_event(row)
            for row in rows
        ]

    def count_events(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM play_events
                """
            ).fetchone()

        if row is None:
            return 0

        return int(
            row["total"]
            or 0
        )

    def schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "PRAGMA user_version"
            ).fetchone()

        if row is None:
            return 0

        return int(
            row[0]
            or 0
        )

    def count_tracks(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM tracks
                """
            ).fetchone()

        if row is None:
            return 0

        return int(
            row["total"]
            or 0
        )

    def total_plays(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COALESCE(
                        SUM(play_count),
                        0
                    ) AS total
                FROM tracks
                """
            ).fetchone()

        if row is None:
            return 0

        return int(
            row["total"]
            or 0
        )

    def delete_track(
        self,
        track_id: int,
    ):
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM tracks
                WHERE id = ?
                """,
                (
                    int(track_id),
                ),
            )

    def clear_history(self):
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM play_events"
            )

            connection.execute(
                "DELETE FROM tracks"
            )

    def _song_values(
        self,
        song: Song,
    ) -> dict[str, str]:
        title = self._clean_text(
            song.title,
            "Unknown title",
        )

        artist = self._clean_text(
            song.artist,
            "Unknown artist",
        )

        album = self._clean_text(
            song.album,
            "No album",
        )

        source_app = self._clean_text(
            song.source_app,
            "Unknown source",
        )

        status = (
            "Playing"
            if song.playing
            else "Paused"
        )

        identity = "|".join(
            [
                title.lower(),
                artist.lower(),
                album.lower(),
                source_app.lower(),
            ]
        )

        track_key = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

        return {
            "track_key": track_key,
            "title": title,
            "artist": artist,
            "album": album,
            "source_app": source_app,
            "status": status,
        }

    @staticmethod
    def _row_to_track(
        row: sqlite3.Row,
    ) -> HistoryTrack:
        return HistoryTrack(
            track_id=int(row["id"]),
            title=str(row["title"]),
            artist=str(row["artist"]),
            album=str(row["album"]),
            source_app=str(
                row["source_app"]
            ),
            first_played=str(
                row["first_played"]
            ),
            last_played=str(
                row["last_played"]
            ),
            play_count=int(
                row["play_count"]
            ),
            last_status=str(
                row["last_status"]
            ),
        )

    @staticmethod
    def _row_to_event(
        row: sqlite3.Row,
    ) -> ListeningEvent:
        return ListeningEvent(
            event_id=int(row["id"]),
            track_id=int(row["track_id"]),
            track_key=str(row["track_key"]),
            title=str(row["title"]),
            artist=str(row["artist"]),
            album=str(row["album"]),
            source_app=str(
                row["source_app"]
            ),
            played_at=str(
                row["played_at"]
            ),
            status=str(row["status"]),
        )

    @staticmethod
    def _clean_text(
        value,
        fallback: str,
    ) -> str:
        cleaned = str(
            value or ""
        ).strip()

        return (
            cleaned
            or fallback
        )

    @staticmethod
    def _current_timestamp() -> str:
        return datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
