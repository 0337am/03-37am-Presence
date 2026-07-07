import asyncio
import time

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)
from winsdk.windows.storage.streams import DataReader

from src.music.song import Song


class WindowsMedia:
    """
    Reads metadata and artwork from Spotify's Windows media session.

    Other media applications such as Chrome, Edge, YouTube, and
    media players are deliberately ignored.
    """

    MEDIA_TIMEOUT_SECONDS = 3.0
    ARTWORK_TIMEOUT_SECONDS = 2.0
    ARTWORK_RETRY_SECONDS = 5.0
    MAX_ARTWORK_SIZE = 10 * 1024 * 1024

    # Works with both the desktop and Microsoft Store versions
    # because their source application IDs contain "spotify".
    SPOTIFY_SOURCE_MARKERS = (
        "spotify",
    )

    def __init__(self):
        self._last_track_key = None
        self._last_artwork_bytes = None
        self._next_artwork_retry = 0.0

    def get_current_song(self) -> Song | None:
        try:
            return asyncio.run(
                self._get_current_song()
            )

        except asyncio.TimeoutError:
            print(
                "Windows Media request timed out."
            )
            return None

        except Exception as error:
            print("Windows Media error:")
            print(error)
            return None

    async def _get_current_song(
        self,
    ) -> Song | None:
        manager = await asyncio.wait_for(
            MediaManager.request_async(),
            timeout=self.MEDIA_TIMEOUT_SECONDS,
        )

        # Do not use get_current_session(), because Windows may
        # decide Chrome or another browser is the current session.
        session = self._select_spotify_session(
            manager
        )

        if session is None:
            self._reset_cache()
            return None

        media = await asyncio.wait_for(
            session.try_get_media_properties_async(),
            timeout=self.MEDIA_TIMEOUT_SECONDS,
        )

        timeline = (
            session.get_timeline_properties()
        )

        playback = (
            session.get_playback_info()
        )

        title = (
            media.title
            or "Unknown title"
        )

        artist = (
            media.artist
            or media.album_artist
            or "Unknown artist"
        )

        album = (
            media.album_title
            or ""
        )

        position_seconds = max(
            0,
            int(
                timeline.position.total_seconds()
            ),
        )

        duration_seconds = max(
            0,
            int(
                timeline.end_time.total_seconds()
            ),
        )

        track_key = (
            title.strip().lower(),
            artist.strip().lower(),
            album.strip().lower(),
        )

        if track_key != self._last_track_key:
            self._last_track_key = track_key
            self._last_artwork_bytes = None
            self._next_artwork_retry = 0.0

        await self._update_artwork(
            media.thumbnail
        )

        playing = self._is_playing(
            playback
        )

        source_app = self._get_source_app(
            session
        )

        return Song(
            title=title,
            artist=artist,
            album=album,
            duration=self._format_time(
                duration_seconds
            ),
            position=self._format_time(
                position_seconds
            ),
            playing=playing,
            artwork_bytes=(
                self._last_artwork_bytes
            ),
            source_app=source_app,
        )

    def _select_spotify_session(
        self,
        manager,
    ):
        """
        Finds Spotify among all available Windows media sessions.

        A playing Spotify session is preferred. If Spotify is
        paused, its paused session is still returned instead of
        allowing Chrome to take over.
        """

        try:
            sessions = list(
                manager.get_sessions()
            )

        except Exception as error:
            print(
                "Could not read Windows media sessions:"
            )
            print(error)
            return None

        spotify_sessions = [
            session
            for session in sessions
            if self._is_spotify_session(
                session
            )
        ]

        if not spotify_sessions:
            return None

        # Prefer a Spotify session that is currently playing.
        for session in spotify_sessions:
            try:
                playback = (
                    session.get_playback_info()
                )

                if self._is_playing(playback):
                    return session

            except Exception:
                continue

        # Spotify exists but is currently paused or stopped.
        current_session = (
            manager.get_current_session()
        )

        if (
            current_session is not None
            and self._is_spotify_session(
                current_session
            )
        ):
            return current_session

        return spotify_sessions[0]

    def _is_spotify_session(
        self,
        session,
    ) -> bool:
        source_app = self._get_source_app(
            session
        ).lower()

        return any(
            marker in source_app
            for marker
            in self.SPOTIFY_SOURCE_MARKERS
        )

    @staticmethod
    def _get_source_app(
        session,
    ) -> str:
        try:
            return str(
                getattr(
                    session,
                    "source_app_user_model_id",
                    "",
                )
                or ""
            )

        except Exception:
            return ""

    @staticmethod
    def _is_playing(
        playback,
    ) -> bool:
        if playback is None:
            return False

        status = getattr(
            playback,
            "playback_status",
            None,
        )

        try:
            return int(status) == 4

        except (
            TypeError,
            ValueError,
        ):
            return (
                "playing"
                in str(status).lower()
            )

    async def _update_artwork(
        self,
        thumbnail,
    ):
        if (
            self._last_artwork_bytes
            is not None
        ):
            return

        if thumbnail is None:
            return

        current_time = time.monotonic()

        if (
            current_time
            < self._next_artwork_retry
        ):
            return

        self._next_artwork_retry = (
            current_time
            + self.ARTWORK_RETRY_SECONDS
        )

        artwork = await self._read_thumbnail(
            thumbnail
        )

        if artwork:
            self._last_artwork_bytes = artwork

    async def _read_thumbnail(
        self,
        thumbnail,
    ) -> bytes | None:
        stream = None
        input_stream = None
        reader = None

        try:
            stream = await asyncio.wait_for(
                thumbnail.open_read_async(),
                timeout=(
                    self.ARTWORK_TIMEOUT_SECONDS
                ),
            )

            size = int(stream.size)

            if size <= 0:
                return None

            if size > self.MAX_ARTWORK_SIZE:
                print(
                    "Artwork ignored because it is "
                    "unexpectedly large:"
                    f" {size} bytes"
                )
                return None

            input_stream = (
                stream.get_input_stream_at(0)
            )

            reader = DataReader(
                input_stream
            )

            loaded = int(
                await asyncio.wait_for(
                    reader.load_async(size),
                    timeout=(
                        self.ARTWORK_TIMEOUT_SECONDS
                    ),
                )
            )

            if loaded <= 0:
                return None

            image_data = bytearray(
                loaded
            )

            reader.read_bytes(
                image_data
            )

            return bytes(image_data)

        except asyncio.TimeoutError:
            print(
                "Artwork read timed out."
            )
            return None

        except Exception as error:
            print(
                "Artwork read failed:"
            )
            print(error)
            return None

        finally:
            self._close_safely(reader)
            self._close_safely(input_stream)
            self._close_safely(stream)

    def _reset_cache(self):
        self._last_track_key = None
        self._last_artwork_bytes = None
        self._next_artwork_retry = 0.0

    @staticmethod
    def _close_safely(item):
        if item is None:
            return

        try:
            item.close()

        except Exception:
            pass

    @staticmethod
    def _format_time(
        seconds: int,
    ) -> str:
        minutes, remaining_seconds = divmod(
            seconds,
            60,
        )

        return (
            f"{minutes}:"
            f"{remaining_seconds:02d}"
        )