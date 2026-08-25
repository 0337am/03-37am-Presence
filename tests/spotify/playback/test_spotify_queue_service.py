from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.spotify.queue_models import (
    QUEUE_ITEM_EPISODE,
    QUEUE_ITEM_TRACK,
    SpotifyQueueSnapshot,
    spotify_queue_from_payload,
)
from src.spotify.queue_service import (
    SpotifyQueueService,
    SpotifyQueueServiceResult,
    SpotifyQueueServiceStatus,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiError,
)


def track_payload(
    *,
    local=False,
):
    uri = (
        "spotify:local:Juice+WRLD:"
        "Sessions:Sic+Em:180"
        if local
        else "spotify:track:track123"
    )

    return {
        "type": "track",
        "name": "Sic 'Em",
        "uri": uri,
        "artists": [
            {
                "name": "Juice WRLD",
            },
        ],
        "album": {
            "name": (
                "Death Race For Love "
                "(Sessions)"
            ),
            "images": [
                {
                    "url": (
                        "https://i.scdn.co/"
                        "queue-cover"
                    ),
                },
            ],
        },
        "is_local": local,
        "duration_ms": 180000,
    }


def episode_payload():
    return {
        "type": "episode",
        "name": "Episode One",
        "uri": (
            "spotify:episode:"
            "episode456"
        ),
        "show": {
            "name": "Example Show",
            "images": [
                {
                    "url": (
                        "https://i.scdn.co/"
                        "show-cover"
                    ),
                },
            ],
        },
        "images": [
            {
                "url": (
                    "https://i.scdn.co/"
                    "episode-cover"
                ),
            },
        ],
        "is_local": False,
        "duration_ms": 3600000,
    }


def queue_payload():
    return {
        "currently_playing": (
            track_payload()
        ),
        "queue": [
            track_payload(
                local=True
            ),
            episode_payload(),
        ],
    }


def session(
    status=SpotifySessionStatus.READY,
    *,
    token="access-token",
):
    token_value = (
        None
        if token is None
        else SimpleNamespace(
            access_token=token
        )
    )

    return SimpleNamespace(
        status=status,
        token=token_value,
    )


class FakeSessionManager:

    def __init__(
        self,
        result=None,
        error=None,
    ):
        self.result = (
            session()
            if result is None
            else result
        )

        self.error = error

    def resolve(
        self,
    ):
        if self.error is not None:
            raise self.error

        return self.result


class FakeApi:

    def __init__(
        self,
        payload=None,
        error=None,
    ):
        self.payload = (
            queue_payload()
            if payload is None
            else payload
        )

        self.error = error
        self.calls = []

    def get_queue(
        self,
        access_token,
    ):
        self.calls.append(
            access_token
        )

        if self.error is not None:
            raise self.error

        return self.payload


class SpotifyQueueModelTests(
    unittest.TestCase
):

    def test_track_payload_maps_to_display_model(
        self,
    ):
        snapshot = (
            spotify_queue_from_payload(
                {
                    "currently_playing": None,
                    "queue": [
                        track_payload()
                    ],
                }
            )
        )

        item = snapshot.items[0]

        self.assertEqual(
            item.item_type,
            QUEUE_ITEM_TRACK,
        )
        self.assertEqual(
            item.name,
            "Sic 'Em",
        )
        self.assertEqual(
            item.creator,
            "Juice WRLD",
        )
        self.assertEqual(
            item.collection,
            (
                "Death Race For Love "
                "(Sessions)"
            ),
        )
        self.assertEqual(
            item.artwork_url,
            (
                "https://i.scdn.co/"
                "queue-cover"
            ),
        )

    def test_episode_payload_maps_to_display_model(
        self,
    ):
        snapshot = (
            spotify_queue_from_payload(
                {
                    "currently_playing": None,
                    "queue": [
                        episode_payload()
                    ],
                }
            )
        )

        item = snapshot.items[0]

        self.assertEqual(
            item.item_type,
            QUEUE_ITEM_EPISODE,
        )
        self.assertEqual(
            item.creator,
            "Example Show",
        )
        self.assertEqual(
            item.collection,
            "Example Show",
        )
        self.assertEqual(
            item.artwork_url,
            (
                "https://i.scdn.co/"
                "episode-cover"
            ),
        )

    def test_local_track_is_preserved_for_queue_display(
        self,
    ):
        snapshot = (
            spotify_queue_from_payload(
                {
                    "currently_playing": None,
                    "queue": [
                        track_payload(
                            local=True
                        )
                    ],
                }
            )
        )

        item = snapshot.items[0]

        self.assertTrue(
            item.is_local
        )
        self.assertTrue(
            item.uri.startswith(
                "spotify:local:"
            )
        )

    def test_non_mapping_queue_payload_is_rejected(
        self,
    ):
        for value in (
            None,
            [],
            "queue",
        ):
            with self.subTest(
                value=type(
                    value
                ).__name__
            ):
                with self.assertRaises(
                    TypeError
                ):
                    spotify_queue_from_payload(
                        value
                    )

    def test_queue_list_is_required(
        self,
    ):
        for value in (
            None,
            {},
            "items",
        ):
            with self.subTest(
                value=repr(
                    value
                )
            ):
                with self.assertRaises(
                    TypeError
                ):
                    spotify_queue_from_payload(
                        {
                            "currently_playing": None,
                            "queue": value,
                        }
                    )


class SpotifyQueueResultTests(
    unittest.TestCase
):

    def test_ready_result_requires_snapshot(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyQueueServiceResult(
                status=(
                    SpotifyQueueServiceStatus
                    .READY
                )
            )

    def test_non_ready_result_rejects_snapshot(
        self,
    ):
        snapshot = (
            spotify_queue_from_payload(
                {
                    "currently_playing": None,
                    "queue": [],
                }
            )
        )

        with self.assertRaises(
            ValueError
        ):
            SpotifyQueueServiceResult(
                status=(
                    SpotifyQueueServiceStatus
                    .DISCONNECTED
                ),
                queue=snapshot,
            )

    def test_error_result_requires_error_code(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyQueueServiceResult(
                status=(
                    SpotifyQueueServiceStatus
                    .ERROR
                )
            )


class SpotifyQueueServiceTests(
    unittest.TestCase
):

    def test_constructor_requires_session_resolve(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyQueueService(
                object(),
                api_client=FakeApi(),
            )

    def test_constructor_requires_api_get_queue(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyQueueService(
                FakeSessionManager(),
                api_client=object(),
            )

    def test_ready_service_requests_and_parses_queue(
        self,
    ):
        api = FakeApi()

        result = (
            SpotifyQueueService(
                FakeSessionManager(),
                api_client=api,
            )
            .get_queue()
        )

        self.assertTrue(
            result.ready
        )

        self.assertIsInstance(
            result.queue,
            SpotifyQueueSnapshot,
        )

        self.assertEqual(
            len(
                result.queue.items
            ),
            2,
        )

        self.assertEqual(
            api.calls,
            [
                "access-token",
            ],
        )

    def test_disconnected_session_is_safe(
        self,
    ):
        api = FakeApi()

        result = (
            SpotifyQueueService(
                FakeSessionManager(
                    session(
                        SpotifySessionStatus
                        .DISCONNECTED,
                        token=None,
                    )
                ),
                api_client=api,
            )
            .get_queue()
        )

        self.assertEqual(
            result.status,
            SpotifyQueueServiceStatus
            .DISCONNECTED,
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_reauthorization_session_is_safe(
        self,
    ):
        api = FakeApi()

        result = (
            SpotifyQueueService(
                FakeSessionManager(
                    session(
                        SpotifySessionStatus
                        .REAUTHORIZATION_REQUIRED,
                        token=None,
                    )
                ),
                api_client=api,
            )
            .get_queue()
        )

        self.assertTrue(
            result.requires_reauthorization
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_refreshed_session_is_preserved(
        self,
    ):
        result = (
            SpotifyQueueService(
                FakeSessionManager(
                    session(
                        SpotifySessionStatus
                        .REFRESHED,
                    )
                ),
                api_client=FakeApi(),
            )
            .get_queue()
        )

        self.assertTrue(
            result.ready
        )
        self.assertTrue(
            result.refreshed
        )

    def test_api_reauthorization_maps_to_reconnect(
        self,
    ):
        result = (
            SpotifyQueueService(
                FakeSessionManager(),
                api_client=FakeApi(
                    error=SpotifyWebApiError(
                        "reauthorization_required",
                        "expired",
                    )
                ),
            )
            .get_queue()
        )

        self.assertTrue(
            result.requires_reauthorization
        )

    def test_rate_limit_preserves_retry_after(
        self,
    ):
        result = (
            SpotifyQueueService(
                FakeSessionManager(),
                api_client=FakeApi(
                    error=SpotifyWebApiError(
                        "rate_limited",
                        "slow down",
                        retry_after_seconds=9,
                    )
                ),
            )
            .get_queue()
        )

        self.assertEqual(
            result.status,
            SpotifyQueueServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.retry_after_seconds,
            9,
        )

    def test_invalid_response_is_safe(
        self,
    ):
        result = (
            SpotifyQueueService(
                FakeSessionManager(),
                api_client=FakeApi(
                    {
                        "currently_playing": None,
                        "queue": {},
                    }
                ),
            )
            .get_queue()
        )

        self.assertEqual(
            result.status,
            SpotifyQueueServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_response",
        )

    def test_unexpected_api_exception_is_safe(
        self,
    ):
        result = (
            SpotifyQueueService(
                FakeSessionManager(),
                api_client=FakeApi(
                    error=RuntimeError(
                        "simulated failure"
                    )
                ),
            )
            .get_queue()
        )

        self.assertEqual(
            result.status,
            SpotifyQueueServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.error_code,
            "spotify_api_error",
        )


if __name__ == "__main__":
    unittest.main()
