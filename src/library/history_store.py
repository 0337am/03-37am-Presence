from __future__ import annotations

import hashlib
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
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


@dataclass(frozen=True)
class TrackQueryResult:
    tracks: tuple[HistoryTrack, ...]
    total_tracks: int
    total_plays: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return (
            self.offset
            + len(self.tracks)
            < self.total_tracks
        )


class HistoryStore:
    """
    Persistent listening history backed by SQLite.

    The database is stored in the application's
    Local AppData directory so it survives updates
    and application restarts.
    """

    SCHEMA_VERSION = 2

    SOURCE_FILTERS = {
        "spotify": ("spotify",),
        "soundcloud": ("soundcloud",),
        "chrome": ("chrome",),
        "edge": ("edge",),
        "firefox": ("firefox",),
        "brave": ("brave",),
        "opera": ("opera",),
        "vivaldi": ("vivaldi",),
    }

    TRACK_SORTS = {
        "newest": (
            "last_played DESC, "
            "id DESC"
        ),
        "oldest": (
            "last_played ASC, "
            "id ASC"
        ),
        "most_played": (
            "play_count DESC, "
            "title COLLATE NOCASE ASC, "
            "artist COLLATE NOCASE ASC, "
            "id DESC"
        ),
        "title": (
            "title COLLATE NOCASE ASC, "
            "artist COLLATE NOCASE ASC, "
            "last_played DESC, "
            "id DESC"
        ),
        "artist": (
            "artist COLLATE NOCASE ASC, "
            "title COLLATE NOCASE ASC, "
            "last_played DESC, "
            "id DESC"
        ),
    }

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

    def query_tracks(
        self,
        *,
        search_text: str = "",
        source_filter: str = "all",
        sort_mode: str = "newest",
        date_from: str = "",
        date_to: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> TrackQueryResult:
        safe_limit = max(
            1,
            min(int(limit), 5000),
        )

        safe_offset = max(
            0,
            int(offset),
        )

        where_sql, parameters = (
            self._track_query_where(
                search_text=search_text,
                source_filter=source_filter,
                date_from=date_from,
                date_to=date_to,
            )
        )

        order_sql = self.TRACK_SORTS.get(
            str(
                sort_mode
                or "newest"
            ).strip().lower(),
            self.TRACK_SORTS["newest"],
        )

        track_query = f"""
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
            {where_sql}
            ORDER BY {order_sql}
            LIMIT ?
            OFFSET ?
        """

        summary_query = f"""
            SELECT
                COUNT(*) AS total_tracks,
                COALESCE(
                    SUM(play_count),
                    0
                ) AS total_plays
            FROM tracks
            {where_sql}
        """

        with self._connect() as connection:
            rows = connection.execute(
                track_query,
                [
                    *parameters,
                    safe_limit,
                    safe_offset,
                ],
            ).fetchall()

            summary = connection.execute(
                summary_query,
                parameters,
            ).fetchone()

        tracks = tuple(
            self._row_to_track(row)
            for row in rows
        )

        total_tracks = (
            int(
                summary["total_tracks"]
                or 0
            )
            if summary is not None
            else 0
        )

        total_plays = (
            int(
                summary["total_plays"]
                or 0
            )
            if summary is not None
            else 0
        )

        return TrackQueryResult(
            tracks=tracks,
            total_tracks=total_tracks,
            total_plays=total_plays,
            limit=safe_limit,
            offset=safe_offset,
        )

    def list_tracks(
        self,
        search_text: str = "",
        limit: int = 1000,
    ) -> list[HistoryTrack]:
        result = self.query_tracks(
            search_text=search_text,
            limit=limit,
        )

        return list(
            result.tracks
        )

    def _track_query_where(
        self,
        *,
        search_text: str,
        source_filter: str,
        date_from: str,
        date_to: str,
    ) -> tuple[str, list[object]]:
        clauses: list[str] = []
        parameters: list[object] = []

        cleaned_search = str(
            search_text
            or ""
        ).strip()

        if cleaned_search:
            search_pattern = (
                "%"
                + self._escape_like(
                    cleaned_search
                )
                + "%"
            )

            clauses.append(
                """
                (
                    title LIKE ? ESCAPE '\\'
                    OR artist LIKE ? ESCAPE '\\'
                    OR album LIKE ? ESCAPE '\\'
                    OR source_app LIKE ? ESCAPE '\\'
                )
                """
            )

            parameters.extend(
                [
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                ]
            )

        selected_source = str(
            source_filter
            or "all"
        ).strip().lower()

        if selected_source in self.SOURCE_FILTERS:
            source_terms = (
                self.SOURCE_FILTERS[
                    selected_source
                ]
            )

            source_clauses = []

            for term in source_terms:
                source_clauses.append(
                    """
                    LOWER(source_app)
                    LIKE ? ESCAPE '\\'
                    """
                )

                parameters.append(
                    "%"
                    + self._escape_like(
                        term.lower()
                    )
                    + "%"
                )

            clauses.append(
                "("
                + " OR ".join(
                    source_clauses
                )
                + ")"
            )

        elif selected_source == "other":
            known_terms = sorted({
                term
                for terms in (
                    self.SOURCE_FILTERS.values()
                )
                for term in terms
            })

            for term in known_terms:
                clauses.append(
                    """
                    LOWER(source_app)
                    NOT LIKE ? ESCAPE '\\'
                    """
                )

                parameters.append(
                    "%"
                    + self._escape_like(
                        term.lower()
                    )
                    + "%"
                )

        start_boundary = (
            self._date_boundary(
                date_from,
                field_name="date_from",
                exclusive_end=False,
            )
        )

        end_boundary = (
            self._date_boundary(
                date_to,
                field_name="date_to",
                exclusive_end=True,
            )
        )

        if start_boundary:
            clauses.append(
                "last_played >= ?"
            )

            parameters.append(
                start_boundary
            )

        if end_boundary:
            clauses.append(
                "last_played < ?"
            )

            parameters.append(
                end_boundary
            )

        if not clauses:
            return "", parameters

        return (
            "WHERE "
            + " AND ".join(
                clauses
            ),
            parameters,
        )

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
    def _escape_like(
        value: str,
    ) -> str:
        return (
            str(value)
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )

    @staticmethod
    def _date_boundary(
        value: str,
        *,
        field_name: str,
        exclusive_end: bool,
    ) -> str:
        cleaned = str(
            value
            or ""
        ).strip()

        if not cleaned:
            return ""

        try:
            parsed = datetime.strptime(
                cleaned,
                "%Y-%m-%d",
            )

        except ValueError as error:
            raise ValueError(
                f"{field_name} must use "
                "YYYY-MM-DD format."
            ) from error

        if exclusive_end:
            parsed += timedelta(
                days=1
            )

        return parsed.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

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
