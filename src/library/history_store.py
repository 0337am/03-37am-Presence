from __future__ import annotations

import hashlib
import os
import sqlite3
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


class HistoryStore:
    """
    Persistent listening history backed by SQLite.

    The database is stored in the application's
    Local AppData directory so it survives updates
    and application restarts.
    """

    def __init__(self):
        self.database_path = (
            self._get_database_path()
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

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
        )

        connection.row_factory = (
            sqlite3.Row
        )

        connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        return connection

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
            min(limit, 5000),
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
