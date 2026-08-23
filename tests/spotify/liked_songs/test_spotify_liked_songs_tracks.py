from __future__ import annotations

import time
import unittest
from types import SimpleNamespace

from PyQt6.QtCore import (
    QEventLoop,
    QThread,
    QTimer,
)
from PyQt6.QtWidgets import (
    QApplication,
)

from src.spotify.liked_songs_service import (
    SpotifyLikedSongsService,
    SpotifyLikedSongsServiceResult,
    SpotifyLikedSongsServiceStatus,
)

from src.spotify.playlist_models import (
    SpotifyPlaylistItemsPage,
)

from src.spotify.qt_liked_songs_runtime import (
    SpotifyQtLikedSongsRuntime,
    SpotifyQtLikedSongsRuntimeError,
)

from src.spotify.session_manager import (
    SpotifySessionStatus,
)


TRACK_URI = (
    "spotify:track:"
    "0123456789ABCDEFGHIJKL"
)


def ready_session():
    return SimpleNamespace(
        status=SpotifySessionStatus.READY,
        token=SimpleNamespace(
            access_token="access-token"
        ),
    )


class FakeSessionManager:
    def __init__(
        self,
        result=None,
    ):
        self.result = (
            result
            if result is not None
            else ready_session()
        )

        self.calls = 0

    def resolve(
        self,
    ):
        self.calls += 1

        return self.result


class FakeApi:
    def __init__(
        self,
        payload,
    ):
        self.payload = payload
        self.calls = []

    def get_json(
        self,
        token,
        path,
        *,
        query=None,
    ):
        self.calls.append(
            (
                token,
                path,
                query,
            )
        )

        return self.payload


def track_payload(
    *,
    title="Saved Track",
):
    return {
        "type": "track",
        "name": title,
        "artists": [
            {
                "name": "Saved Artist",
            },
        ],
        "album": {
            "name": "Saved Album",
            "images": [],
        },
        "duration_ms": 180000,
        "id": (
            "0123456789ABCDEFGHIJKL"
        ),
        "uri": TRACK_URI,
        "is_local": False,
        "is_playable": True,
    }


def page_payload(
    *,
    limit=50,
    offset=0,
    total=1,
):
    return {
        "limit": limit,
        "offset": offset,
        "total": total,
        "items": [
            {
                "added_at": (
                    "2026-08-10T00:00:00Z"
                ),
                "track": track_payload(),
            },
        ],
    }


class ReadyTracksService:
    def __init__(
        self,
        *,
        delay=0.0,
    ):
        self.delay = delay
        self.calls = []
        self.thread = None

    def get_tracks_page(
        self,
        *,
        limit=50,
        offset=0,
    ):
        self.thread = (
            QThread.currentThread()
        )

        self.calls.append(
            (
                limit,
                offset,
            )
        )

        if self.delay:
            time.sleep(
                self.delay
            )

        page = SpotifyPlaylistItemsPage(
            items=(),
            limit=limit,
            offset=offset,
            total=0,
        )

        return SpotifyLikedSongsServiceResult(
            status=(
                SpotifyLikedSongsServiceStatus.READY
            ),
            total=0,
            page=page,
        )


class SpotifyLikedSongsTracksTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication(
                []
            )
        )

    def wait_for_signal(
        self,
        signal,
        action,
        *,
        timeout_ms=2000,
    ):
        loop = QEventLoop()

        values = []

        signal.connect(
            lambda *args: (
                values.append(
                    args
                ),
                loop.quit(),
            )
        )

        timer = QTimer()
        timer.setSingleShot(
            True
        )

        timer.timeout.connect(
            loop.quit
        )

        timer.start(
            timeout_ms
        )

        action()

        if not values:
            loop.exec()

        timer.stop()

        self.assertTrue(
            values,
            "Expected Qt signal was not emitted.",
        )

        return values

    def test_service_requests_paginated_saved_tracks(
        self,
    ):
        session = FakeSessionManager()

        api = FakeApi(
            page_payload(
                limit=25,
                offset=50,
                total=321,
            )
        )

        service = SpotifyLikedSongsService(
            session,
            api_client=api,
        )

        result = service.get_tracks_page(
            limit=25,
            offset=50,
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            result.total,
            321,
        )

        self.assertIsNotNone(
            result.page
        )

        self.assertEqual(
            result.page.limit,
            25,
        )

        self.assertEqual(
            result.page.offset,
            50,
        )

        self.assertEqual(
            result.page.total,
            321,
        )

        self.assertEqual(
            len(
                result.page.items
            ),
            1,
        )

        item = result.page.items[0]

        self.assertEqual(
            item.position,
            50,
        )

        self.assertEqual(
            item.added_at,
            "2026-08-10T00:00:00Z",
        )

        self.assertEqual(
            item.track.title,
            "Saved Track",
        )

        self.assertEqual(
            item.track.spotify_uri,
            TRACK_URI,
        )

        self.assertEqual(
            api.calls,
            [
                (
                    "access-token",
                    "/me/tracks",
                    {
                        "limit": 25,
                        "offset": 50,
                    },
                )
            ],
        )

    def test_service_reuses_shared_track_parser(
        self,
    ):
        service = SpotifyLikedSongsService(
            FakeSessionManager(),
            api_client=FakeApi(
                {
                    "limit": 50,
                    "offset": 0,
                    "total": 2,
                    "items": [
                        {
                            "added_at": "",
                            "track": None,
                        },
                        {
                            "added_at": (
                                "2026-08-10T00:00:00Z"
                            ),
                            "track": track_payload(
                                title="Kept"
                            ),
                        },
                    ],
                }
            ),
        )

        result = service.get_tracks_page()

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            result.page.omitted_items,
            1,
        )

        self.assertEqual(
            len(
                result.page.items
            ),
            1,
        )

        self.assertEqual(
            result.page.items[
                0
            ].position,
            1,
        )

    def test_invalid_page_request_is_rejected_before_session(
        self,
    ):
        invalid = (
            (
                {
                    "limit": 0,
                    "offset": 0,
                },
                ValueError,
            ),
            (
                {
                    "limit": 51,
                    "offset": 0,
                },
                ValueError,
            ),
            (
                {
                    "limit": True,
                    "offset": 0,
                },
                TypeError,
            ),
            (
                {
                    "limit": 50,
                    "offset": -1,
                },
                ValueError,
            ),
            (
                {
                    "limit": 50,
                    "offset": False,
                },
                TypeError,
            ),
        )

        for kwargs, error in invalid:
            with self.subTest(
                kwargs=kwargs
            ):
                session = FakeSessionManager()

                service = (
                    SpotifyLikedSongsService(
                        session,
                        api_client=FakeApi(
                            page_payload()
                        ),
                    )
                )

                with self.assertRaises(
                    error
                ):
                    service.get_tracks_page(
                        **kwargs
                    )

                self.assertEqual(
                    session.calls,
                    0,
                )

    def test_summary_result_remains_page_free(
        self,
    ):
        service = SpotifyLikedSongsService(
            FakeSessionManager(),
            api_client=FakeApi(
                {
                    "total": 12,
                    "items": [],
                }
            ),
        )

        result = service.get_summary()

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            result.total,
            12,
        )

        self.assertIsNone(
            result.page
        )

    def test_result_rejects_mismatched_page_total(
        self,
    ):
        page = SpotifyPlaylistItemsPage(
            items=(),
            limit=50,
            offset=0,
            total=5,
        )

        with self.assertRaises(
            ValueError
        ):
            SpotifyLikedSongsServiceResult(
                status=(
                    SpotifyLikedSongsServiceStatus.READY
                ),
                total=4,
                page=page,
            )

    def test_runtime_forwards_tracks_asynchronously(
        self,
    ):
        service = ReadyTracksService()

        runtime = SpotifyQtLikedSongsRuntime(
            lambda: service
        )

        self.addCleanup(
            runtime.shutdown
        )

        values = self.wait_for_signal(
            runtime.tracks_ready,
            lambda:
            runtime.load_tracks_page(
                limit=25,
                offset=75,
            ),
        )

        self.assertEqual(
            len(
                values
            ),
            1,
        )

        result = values[0][0]

        self.assertTrue(
            result.ready
        )

        self.assertIsNotNone(
            result.page
        )

        self.assertEqual(
            service.calls,
            [
                (
                    25,
                    75,
                ),
            ],
        )

        self.assertIsNot(
            service.thread,
            QThread.currentThread(),
        )

    def test_runtime_validates_page_before_thread(
        self,
    ):
        service = ReadyTracksService()

        runtime = SpotifyQtLikedSongsRuntime(
            lambda: service
        )

        self.addCleanup(
            runtime.shutdown
        )

        with self.assertRaises(
            ValueError
        ):
            runtime.load_tracks_page(
                limit=0
            )

        self.assertFalse(
            runtime.busy
        )

        self.assertEqual(
            service.calls,
            [],
        )

    def test_runtime_busy_is_shared_between_summary_and_tracks(
        self,
    ):
        service = ReadyTracksService(
            delay=0.1
        )

        runtime = SpotifyQtLikedSongsRuntime(
            lambda: service
        )

        self.addCleanup(
            runtime.shutdown
        )

        runtime.load_tracks_page()

        with self.assertRaises(
            SpotifyQtLikedSongsRuntimeError
        ):
            runtime.load_summary()

        deadline = (
            time.monotonic()
            + 2.0
        )

        while (
            runtime.busy
            and time.monotonic()
            < deadline
        ):
            self.app.processEvents()
            time.sleep(
                0.005
            )

        self.assertFalse(
            runtime.busy
        )


    def test_context_discovery_validates_current_account(
        self,
    ):
        class RoutingApi:
            def __init__(
                self,
            ):
                self.calls = []

            def get_json(
                self,
                token,
                path,
                *,
                query=None,
            ):
                self.calls.append(
                    (
                        path,
                        query,
                    )
                )

                if path == "/me/tracks":
                    return page_payload()

                if path == "/me":
                    return {
                        "id": "current-user",
                    }

                if (
                    path
                    == "/me/player/currently-playing"
                ):
                    return {
                        "context": None,
                    }

                if (
                    path
                    == (
                        "/playlists/"
                        "37i9dQZF1F5p3rmiWPIYgZ"
                    )
                ):
                    return {
                        "id": (
                            "37i9dQZF1F5p3rmiWPIYgZ"
                        ),
                        "name": "Liked Songs",
                        "owner": {
                            "id": "current-user",
                        },
                    }

                raise AssertionError(
                    (
                        "Unexpected path: "
                        + path
                    )
                )

        service = SpotifyLikedSongsService(
            FakeSessionManager(),
            api_client=RoutingApi(),
        )

        result = service.get_tracks_page(
            include_context=True
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            result.context_playlist_id,
            "37i9dQZF1F5p3rmiWPIYgZ",
        )

    def test_context_discovery_rejects_wrong_owner(
        self,
    ):
        class RoutingApi:
            def get_json(
                self,
                token,
                path,
                *,
                query=None,
            ):
                if path == "/me/tracks":
                    return page_payload()

                if path == "/me":
                    return {
                        "id": "current-user",
                    }

                if (
                    path
                    == "/me/player/currently-playing"
                ):
                    return {
                        "context": None,
                    }

                if path.startswith(
                    "/playlists/"
                ):
                    return {
                        "id": (
                            "37i9dQZF1F5p3rmiWPIYgZ"
                        ),
                        "name": "Liked Songs",
                        "owner": {
                            "id": "someone-else",
                        },
                    }

                raise AssertionError(
                    (
                        "Unexpected path: "
                        + path
                    )
                )

        service = SpotifyLikedSongsService(
            FakeSessionManager(),
            api_client=RoutingApi(),
        )

        result = service.get_tracks_page(
            include_context=True
        )

        self.assertTrue(
            result.ready
        )

        self.assertIsNone(
            result.context_playlist_id
        )

    def test_context_discovery_failure_does_not_break_tracks(
        self,
    ):
        class RoutingApi:
            def get_json(
                self,
                token,
                path,
                *,
                query=None,
            ):
                if path == "/me/tracks":
                    return page_payload()

                raise RuntimeError(
                    "simulated context failure"
                )

        service = SpotifyLikedSongsService(
            FakeSessionManager(),
            api_client=RoutingApi(),
        )

        result = service.get_tracks_page(
            include_context=True
        )

        self.assertTrue(
            result.ready
        )

        self.assertIsNotNone(
            result.page
        )

        self.assertIsNone(
            result.context_playlist_id
        )

    def test_include_context_requires_boolean(
        self,
    ):
        session = FakeSessionManager()

        service = SpotifyLikedSongsService(
            session,
            api_client=FakeApi(
                page_payload()
            ),
        )

        with self.assertRaises(
            TypeError
        ):
            service.get_tracks_page(
                include_context=1
            )

        self.assertEqual(
            session.calls,
            0,
        )


if __name__ == "__main__":
    unittest.main()
