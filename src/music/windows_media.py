import asyncio
import time

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)
from winsdk.windows.storage.streams import DataReader

from src.music.song import Song


class WindowsMedia:
    """
    Reads metadata and artwork from the active Windows media session.

    The public get_current_song() method is blocking, so it must be
    called from a background worker rather than directly from the UI.
    """

    MEDIA_TIMEOUT_SECONDS = 3.0
    ARTWORK_TIMEOUT_SECONDS = 2.0
    ARTWORK_RETRY_SECONDS = 5.0
    MAX_ARTWORK_SIZE = 10 * 1024 * 1024

    def __init__(self):
        self._last_track_key = None
        self._last_artwork_bytes = None
        self._next_artwork_retry = 0.0

    def get_current_song(self) -> Song | None:
        try:
            return asyncio.run(self._get_current_song())

        except asyncio.TimeoutError:
            print("Windows Media request timed out.")
            return None

        except Exception as error:
            print("Windows Media error:")
            print(error)
            return None

    async def _get_current_song(self) -> Song | None:
        manager = await asyncio.wait_for(
            MediaManager.request_async(),
            timeout=self.MEDIA_TIMEOUT_SECONDS,
        )

        session = manager.get_current_session()

        if session is None:
            self._reset_cache()
            return None

        media = await asyncio.wait_for(
            session.try_get_media_properties_async(),
            timeout=self.MEDIA_TIMEOUT_SECONDS,
        )

        timeline = session.get_timeline_properties()
        playback = session.get_playback_info()

        title = media.title or "Unknown title"
        artist = (
            media.artist
            or media.album_artist
            or "Unknown artist"
        )
        album = media.album_title or ""

        position_seconds = max(
            0,
            int(timeline.position.total_seconds()),
        )

        duration_seconds = max(
            0,
            int(timeline.end_time.total_seconds()),
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

        await self._update_artwork(media.thumbnail)

        status = playback.playback_status

        try:
            playing = int(status) == 4
        except (TypeError, ValueError):
            playing = "playing" in str(status).lower()

        source_app = getattr(
            session,
            "source_app_user_model_id",
            "",
        )

        return Song(
            title=title,
            artist=artist,
            album=album,
            duration=self._format_time(duration_seconds),
            position=self._format_time(position_seconds),
            playing=playing,
            artwork_bytes=self._last_artwork_bytes,
            source_app=source_app,
        )

    async def _update_artwork(self, thumbnail):
        if self._last_artwork_bytes is not None:
            return

        if thumbnail is None:
            return

        current_time = time.monotonic()

        if current_time < self._next_artwork_retry:
            return

        self._next_artwork_retry = (
            current_time + self.ARTWORK_RETRY_SECONDS
        )

        artwork = await self._read_thumbnail(thumbnail)

        if artwork:
            self._last_artwork_bytes = artwork

    async def _read_thumbnail(self, thumbnail) -> bytes | None:
        stream = None
        input_stream = None
        reader = None

        try:
            stream = await asyncio.wait_for(
                thumbnail.open_read_async(),
                timeout=self.ARTWORK_TIMEOUT_SECONDS,
            )

            size = int(stream.size)

            if size <= 0:
                return None

            if size > self.MAX_ARTWORK_SIZE:
                print(
                    "Artwork ignored because it is unexpectedly large:"
                    f" {size} bytes"
                )
                return None

            input_stream = stream.get_input_stream_at(0)
            reader = DataReader(input_stream)

            loaded = int(
                await asyncio.wait_for(
                    reader.load_async(size),
                    timeout=self.ARTWORK_TIMEOUT_SECONDS,
                )
            )

            if loaded <= 0:
                return None

            image_data = bytearray(loaded)
            reader.read_bytes(image_data)

            return bytes(image_data)

        except asyncio.TimeoutError:
            print("Artwork read timed out.")
            return None

        except Exception as error:
            print("Artwork read failed:")
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
    def _format_time(seconds: int) -> str:
        minutes, remaining_seconds = divmod(seconds, 60)
        return f"{minutes}:{remaining_seconds:02d}"