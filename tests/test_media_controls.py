from __future__ import annotations

import math
import unittest
from datetime import timedelta
from types import SimpleNamespace

from winsdk.windows.media import (
    MediaPlaybackAutoRepeatMode,
)

from src.music.media_controls import (
    MediaControls,
    STATE_CONFIRM_ATTEMPTS,
    TICKS_PER_SECOND,
)


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
        shuffle_active=False,
        repeat_mode=MediaPlaybackAutoRepeatMode.NONE,
        position_seconds=50.0,
        minimum_seconds=0.0,
        maximum_seconds=200.0,
        shuffle_enabled=True,
        repeat_enabled=True,
        position_enabled=True,
    ):
        self.result = result
        self.calls = []

        self.shuffle_active = (
            shuffle_active
        )

        self.repeat_mode = (
            repeat_mode
        )

        self.position_seconds = (
            position_seconds
        )

        self.minimum_seconds = (
            minimum_seconds
        )

        self.maximum_seconds = (
            maximum_seconds
        )

        self.shuffle_enabled = (
            shuffle_enabled
        )

        self.repeat_enabled = (
            repeat_enabled
        )

        self.position_enabled = (
            position_enabled
        )

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

    async def try_change_shuffle_active_async(
        self,
        active,
    ):
        self.calls.append(
            (
                "shuffle",
                bool(active),
            )
        )

        self.shuffle_active = bool(active)

        return self.result

    async def try_change_auto_repeat_mode_async(
        self,
        mode,
    ):
        self.calls.append(
            (
                "repeat",
                int(mode),
            )
        )

        self.repeat_mode = mode

        return self.result

    async def try_change_playback_position_async(
        self,
        ticks,
    ):
        self.calls.append(
            (
                "seek",
                int(ticks),
            )
        )

        self.position_seconds = (
            int(ticks)
            / TICKS_PER_SECOND
        )

        return self.result

    def get_playback_info(self):
        return SimpleNamespace(
            auto_repeat_mode=(
                self.repeat_mode
            ),
            is_shuffle_active=(
                self.shuffle_active
            ),
            controls=SimpleNamespace(
                is_shuffle_enabled=(
                    self.shuffle_enabled
                ),
                is_repeat_enabled=(
                    self.repeat_enabled
                ),
                is_playback_position_enabled=(
                    self.position_enabled
                ),
            ),
        )

    def get_timeline_properties(self):
        return SimpleNamespace(
            start_time=timedelta(0),
            position=timedelta(
                seconds=self.position_seconds
            ),
            end_time=timedelta(
                seconds=self.maximum_seconds
            ),
            min_seek_time=timedelta(
                seconds=self.minimum_seconds
            ),
            max_seek_time=timedelta(
                seconds=self.maximum_seconds
            ),
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

    def test_set_shuffle_enables_shuffle(
        self,
    ):
        session = FakeSession(
            shuffle_active=False,
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.set_shuffle(
                True
            )
        )

        self.assertEqual(
            session.calls,
            [
                (
                    "shuffle",
                    True,
                )
            ],
        )

    def test_toggle_shuffle_inverts_state(
        self,
    ):
        session = FakeSession(
            shuffle_active=True,
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.toggle_shuffle()
        )

        self.assertEqual(
            session.calls,
            [
                (
                    "shuffle",
                    False,
                )
            ],
        )

    def test_shuffle_capability_is_respected(
        self,
    ):
        session = FakeSession(
            shuffle_enabled=False,
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertFalse(
            controls.toggle_shuffle()
        )

        self.assertEqual(
            session.calls,
            [],
        )

    def test_set_repeat_mode(
        self,
    ):
        session = FakeSession()

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.set_repeat_mode(
                MediaPlaybackAutoRepeatMode.LIST
            )
        )

        self.assertEqual(
            session.calls,
            [
                (
                    "repeat",
                    int(
                        MediaPlaybackAutoRepeatMode.LIST
                    ),
                )
            ],
        )

    def test_repeat_cycle_none_to_list(
        self,
    ):
        session = FakeSession(
            repeat_mode=(
                MediaPlaybackAutoRepeatMode.NONE
            ),
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.cycle_repeat_mode()
        )

        self.assertEqual(
            session.calls[-1],
            (
                "repeat",
                int(
                    MediaPlaybackAutoRepeatMode.LIST
                ),
            ),
        )

    def test_repeat_cycle_list_to_track(
        self,
    ):
        session = FakeSession(
            repeat_mode=(
                MediaPlaybackAutoRepeatMode.LIST
            ),
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.cycle_repeat_mode()
        )

        self.assertEqual(
            session.calls[-1],
            (
                "repeat",
                int(
                    MediaPlaybackAutoRepeatMode.TRACK
                ),
            ),
        )

    def test_repeat_cycle_track_to_none(
        self,
    ):
        session = FakeSession(
            repeat_mode=(
                MediaPlaybackAutoRepeatMode.TRACK
            ),
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.cycle_repeat_mode()
        )

        self.assertEqual(
            session.calls[-1],
            (
                "repeat",
                int(
                    MediaPlaybackAutoRepeatMode.NONE
                ),
            ),
        )

    def test_invalid_repeat_mode_fails(
        self,
    ):
        session = FakeSession()

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertFalse(
            controls.set_repeat_mode(
                999
            )
        )

        self.assertEqual(
            session.calls,
            [],
        )

    def test_repeat_capability_is_respected(
        self,
    ):
        session = FakeSession(
            repeat_enabled=False,
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertFalse(
            controls.cycle_repeat_mode()
        )

        self.assertEqual(
            session.calls,
            [],
        )

    def test_seek_to_seconds_uses_winrt_ticks(
        self,
    ):
        session = FakeSession()

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.seek_to_seconds(
                25.5
            )
        )

        self.assertEqual(
            session.calls,
            [
                (
                    "seek",
                    255_000_000,
                )
            ],
        )

    def test_seek_to_seconds_clamps_to_maximum(
        self,
    ):
        session = FakeSession(
            maximum_seconds=100.0,
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.seek_to_seconds(
                500.0
            )
        )

        self.assertEqual(
            session.calls[-1],
            (
                "seek",
                1_000_000_000,
            ),
        )

    def test_seek_by_seconds_uses_current_position(
        self,
    ):
        session = FakeSession(
            position_seconds=55.5,
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.seek_by_seconds(
                10.0
            )
        )

        self.assertEqual(
            session.calls[-1],
            (
                "seek",
                655_000_000,
            ),
        )

    def test_seek_by_seconds_clamps_to_minimum(
        self,
    ):
        session = FakeSession(
            position_seconds=5.0,
            minimum_seconds=0.0,
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertTrue(
            controls.seek_by_seconds(
                -10.0
            )
        )

        self.assertEqual(
            session.calls[-1],
            (
                "seek",
                0,
            ),
        )

    def test_seek_capability_is_respected(
        self,
    ):
        session = FakeSession(
            position_enabled=False,
        )

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        self.assertFalse(
            controls.seek_by_seconds(
                10.0
            )
        )

        self.assertEqual(
            session.calls,
            [],
        )

    def test_invalid_seek_value_fails(
        self,
    ):
        session = FakeSession()

        controls, *_ = self._controls(
            session=session,
            sessions=[session],
        )

        for value in (
            "not-a-number",
            math.inf,
            -math.inf,
            math.nan,
        ):
            self.assertFalse(
                controls.seek_to_seconds(
                    value
                )
            )

        self.assertEqual(
            session.calls,
            [],
        )



class DelayedStateSession(
    FakeSession
):
    def __init__(
        self,
        *,
        lag_reads=2,
        **kwargs,
    ):
        super().__init__(
            **kwargs
        )

        self.lag_reads = int(
            lag_reads
        )

        self._pending_shuffle = None
        self._shuffle_reads = 0

        self._pending_repeat = None
        self._repeat_reads = 0

        self._pending_position = None
        self._position_reads = 0

    async def try_change_shuffle_active_async(
        self,
        active,
    ):
        self.calls.append(
            (
                "shuffle",
                bool(active),
            )
        )

        self._pending_shuffle = bool(
            active
        )

        self._shuffle_reads = (
            self.lag_reads
        )

        return self.result

    async def try_change_auto_repeat_mode_async(
        self,
        mode,
    ):
        self.calls.append(
            (
                "repeat",
                int(mode),
            )
        )

        self._pending_repeat = mode

        self._repeat_reads = (
            self.lag_reads
        )

        return self.result

    async def try_change_playback_position_async(
        self,
        ticks,
    ):
        self.calls.append(
            (
                "seek",
                int(ticks),
            )
        )

        self._pending_position = (
            int(ticks)
            / TICKS_PER_SECOND
        )

        self._position_reads = (
            self.lag_reads
        )

        return self.result

    def _advance_shuffle(
        self,
    ):
        if self._pending_shuffle is None:
            return

        if self._shuffle_reads > 0:
            self._shuffle_reads -= 1
            return

        self.shuffle_active = (
            self._pending_shuffle
        )

        self._pending_shuffle = None

    def _advance_repeat(
        self,
    ):
        if self._pending_repeat is None:
            return

        if self._repeat_reads > 0:
            self._repeat_reads -= 1
            return

        self.repeat_mode = (
            self._pending_repeat
        )

        self._pending_repeat = None

    def _advance_position(
        self,
    ):
        if self._pending_position is None:
            return

        if self._position_reads > 0:
            self._position_reads -= 1
            return

        self.position_seconds = (
            self._pending_position
        )

        self._pending_position = None

    def get_playback_info(
        self,
    ):
        self._advance_shuffle()
        self._advance_repeat()

        return super().get_playback_info()

    def get_timeline_properties(
        self,
    ):
        self._advance_position()

        return super().get_timeline_properties()


class MediaControlsSynchronizationTests(
    unittest.TestCase
):
    def _controls(
        self,
        session,
    ):
        media = FakeMedia(
            selected_session=session,
        )

        manager = FakeManager(
            sessions=[session],
            current_session=session,
        )

        sleep_calls = []

        async def request_manager():
            return manager

        async def fake_sleep(
            seconds,
        ):
            sleep_calls.append(
                seconds
            )

        controls = MediaControls(
            media=media,
            manager_request=request_manager,
            sleep_request=fake_sleep,
        )

        return (
            controls,
            sleep_calls,
        )

    def test_shuffle_waits_for_delayed_state(
        self,
    ):
        session = DelayedStateSession(
            shuffle_active=True,
            lag_reads=2,
        )

        controls, sleeps = self._controls(
            session
        )

        self.assertTrue(
            controls.set_shuffle(
                False
            )
        )

        self.assertFalse(
            session.shuffle_active
        )

        self.assertEqual(
            len(sleeps),
            2,
        )

    def test_repeat_waits_for_delayed_state(
        self,
    ):
        session = DelayedStateSession(
            repeat_mode=(
                MediaPlaybackAutoRepeatMode.NONE
            ),
            lag_reads=2,
        )

        controls, sleeps = self._controls(
            session
        )

        self.assertTrue(
            controls.set_repeat_mode(
                MediaPlaybackAutoRepeatMode.LIST
            )
        )

        self.assertEqual(
            session.repeat_mode,
            MediaPlaybackAutoRepeatMode.LIST,
        )

        self.assertEqual(
            len(sleeps),
            2,
        )

    def test_seek_waits_for_delayed_timeline(
        self,
    ):
        session = DelayedStateSession(
            position_seconds=20.0,
            lag_reads=2,
        )

        controls, sleeps = self._controls(
            session
        )

        self.assertTrue(
            controls.seek_to_seconds(
                50.0
            )
        )

        self.assertAlmostEqual(
            session.position_seconds,
            50.0,
        )

        self.assertEqual(
            len(sleeps),
            2,
        )

    def test_confirmation_timeout_fails_safely(
        self,
    ):
        session = DelayedStateSession(
            shuffle_active=True,
            lag_reads=(
                STATE_CONFIRM_ATTEMPTS
                + 10
            ),
        )

        controls, sleeps = self._controls(
            session
        )

        self.assertFalse(
            controls.set_shuffle(
                False
            )
        )

        self.assertEqual(
            len(sleeps),
            STATE_CONFIRM_ATTEMPTS - 1,
        )


if __name__ == "__main__":
    unittest.main()
