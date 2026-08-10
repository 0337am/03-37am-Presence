from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
from typing import Any

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
)

from src.music.song import Song
from src.music.artwork_cache_policy import (
    should_upgrade_artwork,
)
from src.music.source_preferences import (
    SourcePreferences,
    SourcePreferencesStore,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyPlaybackState:
    title: str = ""
    artist: str = ""
    playing: bool = False
    source_app: str = ""


class WindowsMedia:
    ARTWORK_RECHECK_SECONDS = 5.0

    SPOTIFY_SOURCE_MARKERS = (
        "spotify",
    )

    BROWSER_SOURCE_MARKERS = (
        "chrome",
        "googlechrome",
        "msedge",
        "microsoftedge",
        "firefox",
        "brave",
        "opera",
        "vivaldi",
    )

    def __init__(self):
        self.preference_store = (
            SourcePreferencesStore()
        )

        self._artwork_cache: dict[
            str,
            bytes,
        ] = {}

        self._artwork_cache_checked_at: dict[
            str,
            float,
        ] = {}

        self._last_artwork_key = ""

    def get_current_song(self) -> Song:
        try:
            return asyncio.run(
                self._get_current_song_async()
            )

        except RuntimeError:
            loop = asyncio.new_event_loop()

            try:
                return loop.run_until_complete(
                    self._get_current_song_async()
                )

            finally:
                loop.close()

        except Exception as error:
            print(
                "Windows media error:",
                error,
            )
            return Song()

    def get_spotify_playback_state(
        self,
    ) -> SpotifyPlaybackState:
        """
        Return lightweight playback identity for
        Spotify's Windows media session only.

        This intentionally avoids artwork loading.
        """

        try:
            return asyncio.run(
                self
                ._get_spotify_playback_state_async()
            )

        except Exception as error:
            print(
                "Spotify media verification error:",
                error,
            )

            return SpotifyPlaybackState()

    async def _request_session_manager(
        self,
    ):
        return await (
            GlobalSystemMediaTransportControlsSessionManager
            .request_async()
        )

    def _select_spotify_session(
        self,
        *,
        sessions: list[Any],
        current_session,
    ):
        spotify_sessions = [
            session
            for session in sessions
            if self._is_spotify_source(
                self._source_app(
                    session
                )
            )
        ]

        if not spotify_sessions:
            return None

        if (
            current_session is not None
            and self._is_spotify_source(
                self._source_app(
                    current_session
                )
            )
            and self._is_playing(
                current_session
            )
        ):
            return current_session

        for session in spotify_sessions:
            if self._is_playing(
                session
            ):
                return session

        if (
            current_session is not None
            and self._is_spotify_source(
                self._source_app(
                    current_session
                )
            )
        ):
            return current_session

        return spotify_sessions[0]

    async def _get_spotify_playback_state_async(
        self,
    ) -> SpotifyPlaybackState:
        manager = await (
            self._request_session_manager()
        )

        sessions = list(
            manager.get_sessions()
        )

        current_session = (
            manager.get_current_session()
        )

        session = (
            self._select_spotify_session(
                sessions=sessions,
                current_session=current_session,
            )
        )

        if session is None:
            return SpotifyPlaybackState()

        try:
            media = await (
                session
                .try_get_media_properties_async()
            )

        except Exception:
            return SpotifyPlaybackState()

        title = self._clean_text(
            getattr(
                media,
                "title",
                "",
            )
        )

        artist = self._clean_text(
            getattr(
                media,
                "artist",
                "",
            )
        )

        if not artist:
            artist = self._clean_text(
                getattr(
                    media,
                    "album_artist",
                    "",
                )
            )

        return SpotifyPlaybackState(
            title=title,
            artist=artist,
            playing=self._is_playing(
                session
            ),
            source_app=self._source_app(
                session
            ),
        )

    async def _get_current_song_async(
        self,
    ) -> Song:
        preferences = (
            self.preference_store.load()
        )

        if not (
            preferences.spotify_enabled
            or preferences.browser_enabled
        ):
            return Song()

        manager = await (
            GlobalSystemMediaTransportControlsSessionManager
            .request_async()
        )

        sessions = list(
            manager.get_sessions()
        )

        current_session = (
            manager.get_current_session()
        )

        session = self._select_session(
            sessions=sessions,
            current_session=current_session,
            preferences=preferences,
        )

        if session is None:
            return Song()

        return await self._song_from_session(
            session
        )

    def _select_session(
        self,
        sessions: list[Any],
        current_session,
        preferences: SourcePreferences,
    ):
        allowed_sessions = [
            session
            for session in sessions
            if self._session_is_enabled(
                session,
                preferences,
            )
        ]

        if not allowed_sessions:
            return None

        if (
            current_session is not None
            and self._session_is_enabled(
                current_session,
                preferences,
            )
            and self._is_playing(
                current_session
            )
        ):
            return current_session

        for session in allowed_sessions:
            if self._is_playing(session):
                return session

        if (
            current_session is not None
            and self._session_is_enabled(
                current_session,
                preferences,
            )
        ):
            return current_session

        return allowed_sessions[0]

    def _session_is_enabled(
        self,
        session,
        preferences: SourcePreferences,
    ) -> bool:
        source_app = self._source_app(
            session
        )

        if (
            preferences.spotify_enabled
            and self._is_spotify_source(
                source_app
            )
        ):
            return True

        if (
            preferences.browser_enabled
            and self._is_browser_source(
                source_app
            )
        ):
            return True

        return False

    def _source_app(
        self,
        session,
    ) -> str:
        try:
            return str(
                session.source_app_user_model_id
                or ""
            ).strip()

        except Exception:
            return ""

    def _is_spotify_source(
        self,
        source_app: str,
    ) -> bool:
        lowered = source_app.lower()

        return any(
            marker in lowered
            for marker
            in self.SPOTIFY_SOURCE_MARKERS
        )

    def _is_browser_source(
        self,
        source_app: str,
    ) -> bool:
        lowered = source_app.lower()

        return any(
            marker in lowered
            for marker
            in self.BROWSER_SOURCE_MARKERS
        )

    async def _song_from_session(
        self,
        session,
    ) -> Song:
        try:
            media = await (
                session
                .try_get_media_properties_async()
            )

        except Exception as error:
            print(
                "Media properties error:",
                error,
            )
            return Song()

        title = self._clean_text(
            getattr(
                media,
                "title",
                "",
            )
        )

        artist = self._clean_text(
            getattr(
                media,
                "artist",
                "",
            )
        )

        album = self._clean_text(
            getattr(
                media,
                "album_title",
                "",
            )
        )

        if not artist:
            artist = self._clean_text(
                getattr(
                    media,
                    "album_artist",
                    "",
                )
            )

        if not title:
            return Song()

        timeline = self._timeline(
            session
        )

        duration_seconds = (
            self._timeline_seconds(
                timeline,
                "end_time",
            )
        )

        position_seconds = (
            self._timeline_seconds(
                timeline,
                "position",
            )
        )

        artwork_bytes = await (
            self._get_artwork_bytes(
                media=media,
                title=title,
                artist=artist,
                album=album,
            )
        )

        return Song(
            title=title,
            artist=(
                artist
                or "Unknown artist"
            ),
            album=(
                album
                or "No album"
            ),
            duration=self._format_time(
                duration_seconds
            ),
            position=self._format_time(
                position_seconds
            ),
            playing=self._is_playing(
                session
            ),
            artwork_bytes=artwork_bytes,
            source_app=self._source_app(
                session
            ),
        )

    @staticmethod
    def _timeline(
        session,
    ):
        try:
            return (
                session
                .get_timeline_properties()
            )

        except Exception:
            return None

    def _timeline_seconds(
        self,
        timeline,
        attribute_name: str,
    ) -> int:
        if timeline is None:
            return 0

        try:
            value = getattr(
                timeline,
                attribute_name,
            )

        except Exception:
            return 0

        return self._time_value_to_seconds(
            value
        )

    @staticmethod
    def _time_value_to_seconds(
        value,
    ) -> int:
        if value is None:
            return 0

        try:
            total_seconds = (
                value.total_seconds()
            )

            return max(
                0,
                int(total_seconds),
            )

        except (
            AttributeError,
            TypeError,
            ValueError,
        ):
            pass

        try:
            duration = int(
                value.duration
            )

            return max(
                0,
                duration // 10_000_000,
            )

        except (
            AttributeError,
            TypeError,
            ValueError,
        ):
            return 0

    @staticmethod
    def _format_time(
        seconds: int,
    ) -> str:
        safe_seconds = max(
            0,
            int(seconds),
        )

        minutes, remaining = divmod(
            safe_seconds,
            60,
        )

        hours, minutes = divmod(
            minutes,
            60,
        )

        if hours:
            return (
                f"{hours}:"
                f"{minutes:02d}:"
                f"{remaining:02d}"
            )

        return (
            f"{minutes}:"
            f"{remaining:02d}"
        )

    @staticmethod
    def _clean_text(
        value,
    ) -> str:
        return str(
            value or ""
        ).strip()

    async def _get_artwork_bytes(
        self,
        media,
        title: str,
        artist: str,
        album: str,
    ) -> bytes | None:
        artwork_key = "|".join(
            [
                title.lower(),
                artist.lower(),
                album.lower(),
            ]
        )

        cached_artwork = (
            self._artwork_cache.get(
                artwork_key
            )
        )

        checked_at = (
            self._artwork_cache_checked_at.get(
                artwork_key,
                0.0,
            )
        )

        now = time.monotonic()

        if (
            cached_artwork
            and (
                now - checked_at
                < self.ARTWORK_RECHECK_SECONDS
            )
        ):
            self._last_artwork_key = (
                artwork_key
            )

            return cached_artwork

        thumbnail = getattr(
            media,
            "thumbnail",
            None,
        )

        if thumbnail is None:
            self._artwork_cache_checked_at[
                artwork_key
            ] = now

            if cached_artwork:
                self._last_artwork_key = (
                    artwork_key
                )

                return cached_artwork

            return None

        artwork_bytes = None

        for attempt in range(2):
            try:
                stream = await (
                    thumbnail.open_read_async()
                )

                artwork_bytes = await (
                    self._read_stream_bytes(
                        stream
                    )
                )

                if artwork_bytes:
                    break

            except Exception as error:
                if attempt == 1:
                    print(
                        "Artwork read error:",
                        error,
                    )

                await asyncio.sleep(
                    0.05
                )

        self._artwork_cache_checked_at[
            artwork_key
        ] = now

        if not artwork_bytes:
            if cached_artwork:
                self._last_artwork_key = (
                    artwork_key
                )

                return cached_artwork

            return None

        candidate_artwork = bytes(
            artwork_bytes
        )

        if (
            cached_artwork
            and not should_upgrade_artwork(
                len(
                    cached_artwork
                ),
                len(
                    candidate_artwork
                ),
            )
        ):
            self._last_artwork_key = (
                artwork_key
            )

            return cached_artwork

        self._artwork_cache[
            artwork_key
        ] = candidate_artwork

        self._last_artwork_key = (
            artwork_key
        )

        self._trim_artwork_cache()

        return candidate_artwork

    @staticmethod
    async def _read_stream_bytes(
        stream,
    ) -> bytes | None:
        try:
            from winsdk.windows.storage.streams import (
                DataReader,
            )

            stream_size = int(
                stream.size
            )

            if stream_size <= 0:
                return None

            input_stream = (
                stream.get_input_stream_at(
                    0
                )
            )

            reader = DataReader(
                input_stream
            )

            try:
                loaded_size = await (
                    reader.load_async(
                        stream_size
                    )
                )

                if int(loaded_size) <= 0:
                    return None

                data = bytearray(
                    int(loaded_size)
                )

                reader.read_bytes(
                    data
                )

                return bytes(data)

            finally:
                try:
                    reader.detach_stream()

                except Exception:
                    pass

                try:
                    reader.close()

                except Exception:
                    pass

                try:
                    input_stream.close()

                except Exception:
                    pass

        except Exception:
            return None

        finally:
            try:
                stream.close()

            except Exception:
                pass

    def _trim_artwork_cache(
        self,
    ):
        maximum_items = 30

        while (
            len(self._artwork_cache)
            > maximum_items
        ):
            oldest_key = next(
                iter(
                    self._artwork_cache
                )
            )

            if (
                oldest_key
                == self._last_artwork_key
                and len(
                    self._artwork_cache
                ) > 1
            ):
                keys = list(
                    self._artwork_cache
                )

                oldest_key = keys[1]

            self._artwork_cache.pop(
                oldest_key,
                None,
            )

            self._artwork_cache_checked_at.pop(
                oldest_key,
                None,
            )

    @staticmethod
    def _is_playing(
        session,
    ) -> bool:
        try:
            playback_info = (
                session
                .get_playback_info()
            )

            if playback_info is None:
                return False

            status = getattr(
                playback_info,
                "playback_status",
                None,
            )

            if status is None:
                return False

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

        except Exception:
            return False

    def get_source_preferences(
        self,
    ) -> SourcePreferences:
        return (
            self.preference_store.load()
        )

    def update_source_preferences(
        self,
        spotify_enabled: bool | None = None,
        browser_enabled: bool | None = None,
    ) -> SourcePreferences:
        return self.preference_store.update(
            spotify_enabled=spotify_enabled,
            browser_enabled=browser_enabled,
        )