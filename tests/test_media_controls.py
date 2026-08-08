from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.music.media_controls import MediaControls


class FakePreferenceStore:
    def __init__(
        self,
        *,
        spotify_enabled=True,
        browser_enabled=False,
    ):
        self.preferences = SimpleNamespace(
            spotify_enabled=spotify_enabled,
            browser_enabled=browser_enabled,
        )

    def load(self):
        return self.preferences


class FakeMedia:
    def __init__(
        self,
        *,
        selected_session=None,
        spotify_enabled=True,
        browser_enabled=False,
    ):
        self.preference_store = FakePreferenceStore(
            spotify_enabled=spotify_enabled,
            browser_enabled=browser_enabled,
        )

        self.selected_session = selected_session
        self.selection_calls = []

    def _select_session(
        self,
        *,
        sessions,
        current_session,
        preferences,
    ):
        self.selection_calls.append(
            {
                "sessions": sessions,
                "current_session": current_session,
                "preferences": preferences,
            }
        )

        return self.selected_session


class FakeManager:
    def __init__(
        self,
        *,
        sessions=None,
        current_session=None,
    ):
        self.sessions = list(
            sessions or []
        )
        self.current_session = current_session

    def get_sessions(self):
        return self.sessions

    def get_current_session(self):
        return self.current_session


class FakeSession:
    def __init__(
        self,
        *,
        result=True,
    ):
        self.result = result
        self.calls = []

    async def _record(
        self,
        name,
    ):
        self.calls.append(name)
        return self.result

    async def try_play_async(self):
        return await self._record(
            "play"
        )

    async def try_pause_async(self):
        return await self._record(
            "pause"
        )

    async def try_toggle_play_pause_async(self):
        return await self._record(
            "toggle"
        )

    async def try_skip_next_async(self):
        return await self._record(
            "next"
        )

    async def try_skip_previous_async(self):
        return await self._record(
            "previous"
        )


class BrokenSession:
    async def try_play_async(self):
        raise RuntimeError(
            "simulated command failure"
        )


class MediaControlsTests(
    unittest.TestCase
):
    def _controls(
        self,
        *,
        session=None,
        sessions=None,
        current_session=None,
        spotify_enabled=True,
        browser_enabled=False,
    ):
        media = FakeMedia(
            selected_session=session,
            spotify_enabled=spotify_enabled,
            browser_enabled=browser_enabled,
        )

        manager = FakeManager(
            sessions=sessions,
            current_session=current_session,
        )

        request_count = {
            "value": 0,
        }

        async def request_manager():
            request_count["value"] += 1
            return manager

        controls = MediaControls(
            media=media,
            manager_request=request_manager,
        )

        return (
            controls,
            media,
            manager,
            request_count,
        )

    def test_play_requests_selected_session(
        self,
    ):
        session = FakeSession()

        (
            controls,
            media,
            _manager,
            request_count,
        ) = self._controls(
            session=session,
            sessions=[session],
            current_session=session,
        )

        self.assertTrue(
            controls.play()
        )

        self.assertEqual(
            session.calls,
            ["play"],
        )

        self.assertEqual(
            request_count["value"],
            1,
        )

        self.assertEqual(
            len(media.selection_calls),
            1,
        )

    def test_pause_requests_selected_session(
        self,
    ):
        session = FakeSession()

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.pause()
        )

        self.assertEqual(
            session.calls,
            ["pause"],
        )

    def test_toggle_requests_selected_session(
        self,
    ):
        session = FakeSession()

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.toggle_play_pause()
        )

        self.assertEqual(
            session.calls,
            ["toggle"],
        )

    def test_next_requests_selected_session(
        self,
    ):
        session = FakeSession()

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.skip_next()
        )

        self.assertEqual(
            session.calls,
            ["next"],
        )

    def test_previous_requests_selected_session(
        self,
    ):
        session = FakeSession()

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.skip_previous()
        )

        self.assertEqual(
            session.calls,
            ["previous"],
        )

    def test_false_result_is_propagated(
        self,
    ):
        session = FakeSession(
            result=False,
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertFalse(
            controls.play()
        )

        self.assertEqual(
            session.calls,
            ["play"],
        )

    def test_missing_session_fails_safely(
        self,
    ):
        controls, *_ = self._controls(
            session=None,
            sessions=[],
        )

        self.assertFalse(
            controls.play()
        )

    def test_disabled_sources_do_not_request_manager(
        self,
    ):
        (
            controls,
            media,
            _manager,
            request_count,
        ) = self._controls(
            session=FakeSession(),
            spotify_enabled=False,
            browser_enabled=False,
        )

        self.assertFalse(
            controls.play()
        )

        self.assertEqual(
            request_count["value"],
            0,
        )

        self.assertEqual(
            media.selection_calls,
            [],
        )

    def test_missing_command_fails_safely(
        self,
    ):
        session = object()

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertFalse(
            controls.play()
        )

    def test_command_exception_fails_safely(
        self,
    ):
        session = BrokenSession()

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertFalse(
            controls.play()
        )

    def test_manager_exception_fails_safely(
        self,
    ):
        media = FakeMedia(
            selected_session=FakeSession(),
        )

        async def broken_request():
            raise RuntimeError(
                "simulated manager failure"
            )

        controls = MediaControls(
            media=media,
            manager_request=broken_request,
        )

        self.assertFalse(
            controls.play()
        )

        self.assertEqual(
            media.selection_calls,
            [],
        )


if __name__ == "__main__":
    unittest.main()
