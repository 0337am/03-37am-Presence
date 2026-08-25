from __future__ import annotations

import inspect
import time
import unittest
from dataclasses import replace

from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.queue_models import (
    QUEUE_PARTIAL_REASON_SHUFFLE_LOCAL_ORDER,
    SpotifyQueueItem,
    SpotifyQueueSnapshot,
)
from src.spotify.queue_service import (
    SpotifyQueueServiceResult,
    SpotifyQueueServiceStatus,
)
from src.ui.dashboard import (
    DashboardPage,
)
from src.ui.dashboard_layout import (
    preset_layout,
)


class FakeSignal:

    def __init__(
        self,
    ):
        self.callbacks = []

    def connect(
        self,
        callback,
    ):
        self.callbacks.append(
            callback
        )

    def emit(
        self,
        *args,
    ):
        for callback in tuple(
            self.callbacks
        ):
            callback(
                *args
            )


class FakeQueueRuntime:

    def __init__(
        self,
    ):
        self.queue_ready = FakeSignal()
        self.failed = FakeSignal()
        self.busy_changed = FakeSignal()
        self.busy = False
        self.load_calls = 0

    def load_queue(
        self,
    ):
        self.load_calls += 1


def queue_layout(
    *,
    visible=True,
):
    base = preset_layout(
        "Default"
    )

    return replace(
        base,
        cards=tuple(
            replace(
                card,
                visible=bool(
                    visible
                ),
            )
            if card.card_id == "queue"
            else card
            for card in base.cards
        ),
        preset="Custom",
        locked=False,
    )


def queue_item(
    name,
    *,
    creator="Artist",
    collection="Album",
    item_type="track",
    is_local=False,
    duration_ms=180000,
):
    uri = (
        "spotify:local:artist:album:track"
        if is_local
        else (
            f"spotify:{item_type}:"
            "QueuePresentation123"
        )
    )

    return SpotifyQueueItem(
        item_type=item_type,
        name=name,
        uri=uri,
        creator=creator,
        collection=collection,
        artwork_url="",
        is_local=is_local,
        duration_ms=duration_ms,
    )


class DashboardQueuePresentationTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
        app = QApplication.instance()

        if app is None:
            app = QApplication([])

        cls.app = app

    def make_harness(
        self,
        *,
        visible=True,
        runtime=None,
    ):
        harness = type(
            "DashboardHarness",
            (),
            {},
        )()

        DashboardPage.build_queue_card(
            harness
        )

        harness.dashboard_layout_state = (
            queue_layout(
                visible=visible
            )
        )

        self.addCleanup(
            harness.queue_card.deleteLater
        )

        if runtime is not None:
            DashboardPage.set_spotify_queue_runtime(
                harness,
                runtime,
            )

        return harness

    def test_queue_card_builds_current_and_three_up_next_rows(
        self,
    ):
        harness = self.make_harness()

        self.assertEqual(
            len(
                harness.queue_rows
            ),
            3,
        )

        self.assertIsNotNone(
            harness.queue_current_row
        )

        self.assertEqual(
            harness.queue_refresh_button.text(),
            "Refresh",
        )

    def test_runtime_setter_connects_signals_without_eager_load(
        self,
    ):
        runtime = FakeQueueRuntime()

        harness = self.make_harness(
            runtime=runtime
        )

        self.assertEqual(
            runtime.load_calls,
            0,
        )

        self.assertEqual(
            len(
                runtime.queue_ready.callbacks
            ),
            1,
        )

        self.assertEqual(
            len(
                runtime.failed.callbacks
            ),
            1,
        )

        self.assertEqual(
            len(
                runtime.busy_changed.callbacks
            ),
            1,
        )

    def test_hidden_queue_does_not_refresh(
        self,
    ):
        runtime = FakeQueueRuntime()

        harness = self.make_harness(
            visible=False,
            runtime=runtime,
        )

        self.assertFalse(
            DashboardPage.refresh_spotify_queue(
                harness
            )
        )

        self.assertEqual(
            runtime.load_calls,
            0,
        )

    def test_periodic_refresh_is_throttled_and_busy_safe(
        self,
    ):
        runtime = FakeQueueRuntime()

        harness = self.make_harness(
            runtime=runtime
        )

        self.assertTrue(
            DashboardPage.refresh_spotify_queue(
                harness
            )
        )

        self.assertEqual(
            runtime.load_calls,
            1,
        )

        self.assertEqual(
            harness.queue_placeholder.text(),
            "Loading Spotify Queue...",
        )

        self.assertFalse(
            DashboardPage.refresh_spotify_queue(
                harness
            )
        )

        self.assertEqual(
            runtime.load_calls,
            1,
        )

        harness._spotify_queue_next_refresh_at = (
            0.0
        )

        runtime.busy = True

        self.assertFalse(
            DashboardPage.refresh_spotify_queue(
                harness
            )
        )

        self.assertEqual(
            runtime.load_calls,
            1,
        )

    def test_manual_refresh_button_bypasses_time_throttle(
        self,
    ):
        runtime = FakeQueueRuntime()

        harness = self.make_harness(
            runtime=runtime
        )

        harness._spotify_queue_next_refresh_at = (
            time.monotonic()
            + 999.0
        )

        harness.queue_refresh_button.click()

        self.assertEqual(
            runtime.load_calls,
            1,
        )

    def test_visibility_change_requests_queue_immediately(
        self,
    ):
        source = inspect.getsource(
            DashboardPage
            .set_dashboard_card_visibility
        )

        self.assertIn(
            'card_id == "queue"',
            source,
        )

        self.assertIn(
            "force=True",
            source,
        )

        self.assertIn(
            (
                "DashboardPage."
                "refresh_spotify_queue"
            ),
            source,
        )

    def test_dashboard_refresh_polls_queue_through_throttle(
        self,
    ):
        source = inspect.getsource(
            DashboardPage.refresh_dashboard_data
        )

        self.assertIn(
            (
                "DashboardPage."
                "refresh_spotify_queue"
            ),
            source,
        )

    def test_ready_snapshot_renders_current_up_next_and_more_count(
        self,
    ):
        harness = self.make_harness()

        snapshot = SpotifyQueueSnapshot(
            currently_playing=queue_item(
                "Current Song",
                creator="Juice WRLD",
                collection="Session",
            ),
            items=(
                queue_item(
                    "Local Song",
                    creator="Juice WRLD",
                    collection="Unreleased",
                    is_local=True,
                ),
                queue_item(
                    "Episode One",
                    creator="Show Host",
                    collection="Podcast",
                    item_type="episode",
                ),
                queue_item(
                    "Third Song",
                ),
                queue_item(
                    "Fourth Song",
                ),
                queue_item(
                    "Fifth Song",
                ),
            ),
        )

        result = SpotifyQueueServiceResult(
            status=(
                SpotifyQueueServiceStatus.READY
            ),
            queue=snapshot,
        )

        DashboardPage.show_spotify_queue_result(
            harness,
            result,
        )

        self.assertFalse(
            harness
            .queue_current_row[
                "card"
            ]
            .isHidden()
        )

        self.assertEqual(
            harness
            .queue_current_row[
                "title"
            ].text(),
            "Current Song",
        )

        self.assertEqual(
            harness
            .queue_current_row[
                "source"
            ].text(),
            "NOW",
        )

        self.assertEqual(
            harness.queue_rows[
                0
            ][
                "source"
            ].text(),
            "LOCAL",
        )

        self.assertEqual(
            harness.queue_rows[
                1
            ][
                "source"
            ].text(),
            "EPISODE",
        )

        self.assertEqual(
            harness.queue_rows[
                2
            ][
                "title"
            ].text(),
            "Third Song",
        )

        self.assertEqual(
            harness.queue_more.text(),
            "+2 more in Queue",
        )

        self.assertEqual(
            harness.queue_status.text(),
            "5 items up next",
        )

    def test_ready_empty_queue_shows_empty_state(
        self,
    ):
        harness = self.make_harness()

        result = SpotifyQueueServiceResult(
            status=(
                SpotifyQueueServiceStatus.READY
            ),
            queue=SpotifyQueueSnapshot(
                currently_playing=None,
                items=(),
            ),
        )

        DashboardPage.show_spotify_queue_result(
            harness,
            result,
        )

        self.assertEqual(
            harness.queue_placeholder.text(),
            "Spotify Queue is empty.",
        )

        self.assertEqual(
            harness.queue_status.text(),
            "Queue is empty",
        )

    def test_disconnected_result_is_presented(
        self,
    ):
        harness = self.make_harness()

        result = SpotifyQueueServiceResult(
            status=(
                SpotifyQueueServiceStatus
                .DISCONNECTED
            ),
            message=(
                "Connect Spotify to view "
                "the Queue."
            ),
        )

        DashboardPage.show_spotify_queue_result(
            harness,
            result,
        )

        self.assertEqual(
            harness.queue_status.text(),
            "Spotify disconnected",
        )

        self.assertIn(
            "Connect Spotify",
            harness.queue_placeholder.text(),
        )

    def test_reauthorization_result_is_presented(
        self,
    ):
        harness = self.make_harness()

        result = SpotifyQueueServiceResult(
            status=(
                SpotifyQueueServiceStatus
                .REAUTHORIZATION_REQUIRED
            ),
            message=(
                "Reconnect Spotify to view "
                "the Queue."
            ),
        )

        DashboardPage.show_spotify_queue_result(
            harness,
            result,
        )

        self.assertEqual(
            harness.queue_status.text(),
            "Reconnect Spotify",
        )

        self.assertIn(
            "Reconnect Spotify",
            harness.queue_placeholder.text(),
        )

    def test_error_result_honours_retry_after(
        self,
    ):
        harness = self.make_harness()

        before = time.monotonic()

        result = SpotifyQueueServiceResult(
            status=(
                SpotifyQueueServiceStatus.ERROR
            ),
            message=(
                "Spotify is limiting Queue "
                "requests."
            ),
            error_code="rate_limited",
            retry_after_seconds=30,
        )

        DashboardPage.show_spotify_queue_result(
            harness,
            result,
        )

        self.assertEqual(
            harness.queue_status.text(),
            "Queue unavailable",
        )

        self.assertIn(
            "30s",
            harness.queue_placeholder.text(),
        )

        self.assertGreaterEqual(
            (
                harness
                ._spotify_queue_next_refresh_at
            ),
            before + 29.0,
        )

    def test_runtime_failure_is_user_safe(
        self,
    ):
        harness = self.make_harness()

        DashboardPage.show_spotify_queue_runtime_failure(
            harness,
            "service_error",
            "Simulated Queue failure",
        )

        self.assertEqual(
            harness.queue_status.text(),
            "Queue unavailable",
        )

        self.assertEqual(
            harness.queue_placeholder.text(),
            "Simulated Queue failure",
        )

    def test_busy_signal_disables_manual_refresh(
        self,
    ):
        runtime = FakeQueueRuntime()

        harness = self.make_harness(
            runtime=runtime
        )

        runtime.busy_changed.emit(
            True
        )

        self.assertFalse(
            harness
            .queue_refresh_button
            .isEnabled()
        )

        runtime.busy_changed.emit(
            False
        )

        self.assertTrue(
            harness
            .queue_refresh_button
            .isEnabled()
        )

    def test_shuffle_partial_queue_avoids_exact_position_claims(
        self,
    ):
        harness = self.make_harness()

        def item(
            name,
            *,
            local=False,
        ):
            return SpotifyQueueItem(
                item_type="track",
                name=name,
                uri=(
                    (
                        "spotify:local:"
                        + name.replace(
                            " ",
                            "+",
                        )
                        + ":180"
                    )
                    if local
                    else (
                        "spotify:track:"
                        + name.replace(
                            " ",
                            "",
                        )
                        + "123"
                    )
                ),
                creator="Juice WRLD",
                collection="Sessions",
                artwork_url="",
                is_local=bool(
                    local
                ),
                duration_ms=180000,
            )

        snapshot = SpotifyQueueSnapshot(
            currently_playing=(
                item(
                    "Red Moonlight",
                    local=True,
                )
            ),
            items=(
                item(
                    "Cuffed"
                ),
                item(
                    "Lace It"
                ),
                item(
                    "Barbarian"
                ),
                item(
                    "Used To"
                ),
            ),
            partial_reason=(
                QUEUE_PARTIAL_REASON_SHUFFLE_LOCAL_ORDER
            ),
        )

        DashboardPage.populate_spotify_queue(
            harness,
            snapshot,
        )

        self.assertEqual(
            harness.queue_status.text(),
            (
                "Shuffle on | "
                "local-file order hidden"
            ),
        )

        self.assertEqual(
            harness.queue_up_next_label.text(),
            "SPOTIFY-VISIBLE QUEUE",
        )

        self.assertEqual(
            [
                row[
                    "icon"
                ].text()
                for row
                in harness.queue_rows
            ],
            [
                "♪",
                "♪",
                "♪",
            ],
        )

        self.assertEqual(
            harness.queue_more.text(),
            "+1 more Spotify-visible",
        )

        self.assertEqual(
            harness.queue_current_row[
                "source"
            ].text(),
            "NOW / LOCAL",
        )


if __name__ == "__main__":
    unittest.main()
