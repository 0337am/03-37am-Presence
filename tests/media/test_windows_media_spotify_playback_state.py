import asyncio
import unittest

from src.music.windows_media import (
    SpotifyPlaybackState,
    WindowsMedia,
)


class FakePlaybackInfo:
    def __init__(
        self,
        status,
    ):
        self.playback_status = status


class FakeMediaProperties:
    def __init__(
        self,
        *,
        title="",
        artist="",
        album_artist="",
    ):
        self.title = title
        self.artist = artist
        self.album_artist = album_artist


class FakeSession:
    def __init__(
        self,
        *,
        source,
        title="",
        artist="",
        album_artist="",
        playback_status=4,
    ):
        self.source_app_user_model_id = source
        self._properties = FakeMediaProperties(
            title=title,
            artist=artist,
            album_artist=album_artist,
        )
        self._playback_info = FakePlaybackInfo(
            playback_status
        )

    async def try_get_media_properties_async(
        self,
    ):
        return self._properties

    def get_playback_info(
        self,
    ):
        return self._playback_info


class FakeManager:
    def __init__(
        self,
        sessions,
        current_session=None,
    ):
        self._sessions = list(
            sessions
        )
        self._current_session = (
            current_session
        )

    def get_sessions(
        self,
    ):
        return list(
            self._sessions
        )

    def get_current_session(
        self,
    ):
        return self._current_session


class TestWindowsMedia(
    WindowsMedia
):
    def __init__(
        self,
        manager,
    ):
        self._test_manager = manager

    async def _request_session_manager(
        self,
    ):
        return self._test_manager


class SpotifyPlaybackStateTests(
    unittest.TestCase
):
    def read_state(
        self,
        manager,
    ):
        media = TestWindowsMedia(
            manager
        )

        return asyncio.run(
            media
            ._get_spotify_playback_state_async()
        )

    def test_reads_playing_spotify_identity(
        self,
    ):
        spotify = FakeSession(
            source="Spotify.exe",
            title="CELLOPHANE",
            artist="WesGhost",
            playback_status=4,
        )

        state = self.read_state(
            FakeManager(
                [spotify],
                current_session=spotify,
            )
        )

        self.assertEqual(
            state.title,
            "CELLOPHANE",
        )

        self.assertEqual(
            state.artist,
            "WesGhost",
        )

        self.assertTrue(
            state.playing
        )

        self.assertEqual(
            state.source_app,
            "Spotify.exe",
        )

    def test_browser_current_session_does_not_hide_spotify(
        self,
    ):
        browser = FakeSession(
            source="chrome.exe",
            title="Video",
            artist="Website",
            playback_status=4,
        )

        spotify = FakeSession(
            source="Spotify.exe",
            title="MIGRAINE",
            artist="WesGhost",
            playback_status=4,
        )

        state = self.read_state(
            FakeManager(
                [
                    browser,
                    spotify,
                ],
                current_session=browser,
            )
        )

        self.assertEqual(
            state.title,
            "MIGRAINE",
        )

        self.assertEqual(
            state.artist,
            "WesGhost",
        )

        self.assertTrue(
            state.playing
        )

    def test_album_artist_is_fallback(
        self,
    ):
        spotify = FakeSession(
            source="Spotify.exe",
            title="Track",
            artist="",
            album_artist="Fallback Artist",
            playback_status=4,
        )

        state = self.read_state(
            FakeManager(
                [spotify]
            )
        )

        self.assertEqual(
            state.artist,
            "Fallback Artist",
        )

    def test_paused_spotify_state_is_reported(
        self,
    ):
        spotify = FakeSession(
            source="Spotify.exe",
            title="CELLOPHANE",
            artist="WesGhost",
            playback_status=5,
        )

        state = self.read_state(
            FakeManager(
                [spotify]
            )
        )

        self.assertFalse(
            state.playing
        )

    def test_no_spotify_session_returns_empty_state(
        self,
    ):
        browser = FakeSession(
            source="chrome.exe",
            title="Video",
            artist="Website",
            playback_status=4,
        )

        state = self.read_state(
            FakeManager(
                [browser],
                current_session=browser,
            )
        )

        self.assertEqual(
            state,
            SpotifyPlaybackState(),
        )


if __name__ == "__main__":
    unittest.main()
