from __future__ import annotations

import inspect
import unittest
from types import SimpleNamespace

from src.spotify.effective_queue_service import (
    SpotifyEffectiveQueueService,
)
from src.spotify.queue_models import (
    SpotifyQueueItem,
    SpotifyQueueSnapshot,
)
from src.spotify.queue_service import (
    SpotifyQueueServiceResult,
    SpotifyQueueServiceStatus,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)
from src.ui.main_window import (
    MainWindow,
)


PLAYLIST_ID = "Playlist123"

PLAYLIST_URI = (
    "spotify:playlist:"
    + PLAYLIST_ID
)


def queue_item(
    name,
    uri,
    *,
    local=False,
    item_type="track",
):
    return SpotifyQueueItem(
        item_type=item_type,
        name=name,
        uri=uri,
        creator="Juice WRLD",
        collection="Sessions",
        artwork_url="",
        is_local=local,
        duration_ms=180000,
    )


def ready_queue(
    current,
    *items,
):
    return SpotifyQueueServiceResult(
        status=(
            SpotifyQueueServiceStatus.READY
        ),
        queue=SpotifyQueueSnapshot(
            currently_playing=current,
            items=tuple(items),
        ),
        message="Queue ready.",
        refreshed=True,
    )


def player_track(
    name,
    uri,
    *,
    local=False,
):
    data = {
        "type": "track",
        "name": name,
        "artists": [
            {
                "name": "Juice WRLD",
            },
        ],
        "album": {
            "name": "Sessions",
            "images": [],
        },
        "is_local": bool(local),
        "duration_ms": 180000,
    }

    if uri is not None:
        data["uri"] = uri

    return data


def player_payload(
    item,
    *,
    context_type="playlist",
    shuffle=False,
):
    context = None

    if context_type is not None:
        if context_type == "playlist":
            context_uri = PLAYLIST_URI
        else:
            context_uri = (
                "spotify:album:"
                "Album123"
            )

        context = {
            "type": context_type,
            "uri": context_uri,
        }

    return {
        "item": item,
        "context": context,
        "shuffle_state": bool(
            shuffle
        ),
    }


def resolved_item(
    position,
    name,
    uri,
    *,
    local=False,
):
    track = SimpleNamespace(
        title=name,
        artist="Juice WRLD",
        album="Sessions",
        duration_ms=180000,
        spotify_uri=uri,
        artwork_reference="",
    )

    return SimpleNamespace(
        position=position,
        is_local=bool(local),
        unified_track=track,
    )


class QueueServiceStub:

    def __init__(
        self,
        result,
    ):
        self.result = result
        self.calls = 0

    def get_queue(
        self,
    ):
        self.calls += 1
        return self.result


class SessionStub:

    def __init__(
        self,
    ):
        self.calls = 0

    def resolve(
        self,
    ):
        self.calls += 1

        return SimpleNamespace(
            status=(
                SpotifySessionStatus.READY
            ),
            token=SimpleNamespace(
                access_token=(
                    "access-token"
                )
            ),
        )


class ApiStub:

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


class ResolvedServiceStub:

    def __init__(
        self,
        items,
        *,
        ready=True,
        page_size=None,
    ):
        self.items = tuple(items)
        self.ready = bool(ready)
        self.page_size = page_size
        self.calls = []

    def get_playlist_items(
        self,
        playlist_id,
        *,
        limit,
        offset,
        market=None,
    ):
        self.calls.append(
            (
                playlist_id,
                limit,
                offset,
                market,
            )
        )

        if not self.ready:
            return SimpleNamespace(
                ready=False,
                resolved_page=None,
            )

        page_limit = (
            self.page_size
            if self.page_size
            is not None
            else limit
        )

        return SimpleNamespace(
            ready=True,
            resolved_page=(
                SimpleNamespace(
                    items=(
                        self.items[
                            offset:
                            offset
                            + page_limit
                        ]
                    ),
                    offset=offset,
                    limit=page_limit,
                    total=len(
                        self.items
                    ),
                )
            ),
        )


class SpotifyEffectiveQueueServiceTests(
    unittest.TestCase
):

    def make_service(
        self,
        result,
        player,
        resolved,
    ):
        return SpotifyEffectiveQueueService(
            QueueServiceStub(result),
            SessionStub(),
            lambda:
            resolved,
            api_client=(
                ApiStub(player)
            ),
            clock=lambda: 100.0,
        )

    def test_constructor_requires_queue_service(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyEffectiveQueueService(
                object(),
                SessionStub(),
                lambda:
                None,
                api_client=(
                    ApiStub({})
                ),
            )

    def test_constructor_requires_session_manager(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyEffectiveQueueService(
                QueueServiceStub(
                    ready_queue(None)
                ),
                object(),
                lambda:
                None,
                api_client=(
                    ApiStub({})
                ),
            )

    def test_constructor_requires_resolved_service_provider(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyEffectiveQueueService(
                QueueServiceStub(
                    ready_queue(None)
                ),
                SessionStub(),
                None,
                api_client=(
                    ApiStub({})
                ),
            )

    def test_non_ready_queue_skips_player_lookup(
        self,
    ):
        base = SpotifyQueueServiceResult(
            status=(
                SpotifyQueueServiceStatus.ERROR
            ),
            message="Unavailable",
            error_code="simulated",
        )

        api = ApiStub({})

        service = SpotifyEffectiveQueueService(
            QueueServiceStub(base),
            SessionStub(),
            lambda:
            None,
            api_client=api,
        )

        self.assertIs(
            service.get_queue(),
            base,
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_player_current_corrects_stale_queue_current_without_resolver(
        self,
    ):
        used_uri = (
            "spotify:track:UsedTo123"
        )

        local_uri = (
            "spotify:local:"
            "Juice+WRLD:"
            "Sessions:"
            "Devil+Horns:180"
        )

        base = ready_queue(
            queue_item(
                "Used To",
                used_uri,
            )
        )

        result = (
            SpotifyEffectiveQueueService(
                QueueServiceStub(base),
                SessionStub(),
                lambda:
                None,
                api_client=(
                    ApiStub(
                        player_payload(
                            player_track(
                                "Devil Horns",
                                local_uri,
                                local=True,
                            )
                        )
                    )
                ),
            )
            .get_queue()
        )

        self.assertEqual(
            result
            .queue
            .currently_playing
            .name,
            "Devil Horns",
        )

        self.assertTrue(
            result
            .queue
            .currently_playing
            .is_local
        )

    def test_local_playlist_gaps_are_reconstructed(
        self,
    ):
        current_uri = (
            "spotify:local:"
            "Juice+WRLD:"
            "Sessions:"
            "Devil+Horns:180"
        )

        used_uri = (
            "spotify:track:UsedTo123"
        )

        still_uri = (
            "spotify:track:ImStill123"
        )

        fast_uri = (
            "spotify:track:Fast123"
        )

        base = ready_queue(
            queue_item(
                "Used To",
                used_uri,
            ),
            queue_item(
                "I'm Still",
                still_uri,
            ),
            queue_item(
                "Fast",
                fast_uri,
            ),
        )

        resolved = ResolvedServiceStub(
            (
                resolved_item(
                    0,
                    "Devil Horns",
                    current_uri,
                    local=True,
                ),
                resolved_item(
                    1,
                    "Lost In My Head",
                    (
                        "spotify:local:"
                        "Juice+WRLD:"
                        "Sessions:"
                        "Lost+In+My+Head:181"
                    ),
                    local=True,
                ),
                resolved_item(
                    2,
                    "GoPro (v1)",
                    (
                        "spotify:local:"
                        "Juice+WRLD:"
                        "Sessions:"
                        "GoPro+v1:182"
                    ),
                    local=True,
                ),
                resolved_item(
                    3,
                    "Used To",
                    used_uri,
                ),
                resolved_item(
                    4,
                    "Lifes A Mess",
                    (
                        "spotify:local:"
                        "Juice+WRLD:"
                        "Sessions:"
                        "Lifes+A+Mess:183"
                    ),
                    local=True,
                ),
                resolved_item(
                    5,
                    "Rob And Scam",
                    (
                        "spotify:local:"
                        "Juice+WRLD:"
                        "Sessions:"
                        "Rob+And+Scam:184"
                    ),
                    local=True,
                ),
                resolved_item(
                    6,
                    "My Fault </3",
                    (
                        "spotify:local:"
                        "Juice+WRLD:"
                        "Sessions:"
                        "My+Fault:185"
                    ),
                    local=True,
                ),
                resolved_item(
                    7,
                    "Confessions",
                    (
                        "spotify:local:"
                        "Juice+WRLD:"
                        "Sessions:"
                        "Confessions:186"
                    ),
                    local=True,
                ),
                resolved_item(
                    8,
                    "I'm Still",
                    still_uri,
                ),
                resolved_item(
                    9,
                    "Fast",
                    fast_uri,
                ),
            )
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Devil Horns",
                        current_uri,
                        local=True,
                    )
                ),
                resolved,
            )
            .get_queue()
        )

        self.assertEqual(
            [
                item.name
                for item
                in result.queue.items
            ],
            [
                "Lost In My Head",
                "GoPro (v1)",
                "Used To",
                "Lifes A Mess",
                "Rob And Scam",
                "My Fault </3",
                "Confessions",
                "I'm Still",
                "Fast",
            ],
        )

    def test_local_uri_plus_and_percent_encoding_match(
        self,
    ):
        base = ready_queue(
            queue_item(
                "Next",
                "spotify:track:Next123",
            )
        )

        resolved = ResolvedServiceStub(
            (
                resolved_item(
                    0,
                    "Current",
                    (
                        "spotify:local:"
                        "Juice%20WRLD:"
                        "Sessions:"
                        "Current%20Song:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    1,
                    "Next",
                    "spotify:track:Next123",
                ),
            )
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Current",
                        (
                            "spotify:local:"
                            "Juice+WRLD:"
                            "Sessions:"
                            "Current+Song:180"
                        ),
                        local=True,
                    )
                ),
                resolved,
            )
            .get_queue()
        )

        self.assertEqual(
            result
            .queue
            .currently_playing
            .name,
            "Current",
        )

    def test_missing_local_uri_can_use_unique_metadata_match(
        self,
    ):
        base = ready_queue(
            queue_item(
                "Next",
                "spotify:track:Next123",
            )
        )

        resolved = ResolvedServiceStub(
            (
                resolved_item(
                    0,
                    "Devil Horns",
                    (
                        "spotify:local:"
                        "Juice+WRLD:"
                        "Sessions:"
                        "Devil+Horns:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    1,
                    "Local Next",
                    (
                        "spotify:local:"
                        "Juice+WRLD:"
                        "Sessions:"
                        "Local+Next:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    2,
                    "Next",
                    "spotify:track:Next123",
                ),
            )
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Devil Horns",
                        None,
                        local=True,
                    )
                ),
                resolved,
            )
            .get_queue()
        )

        self.assertEqual(
            result
            .queue
            .currently_playing
            .name,
            "Devil Horns",
        )

        self.assertEqual(
            [
                item.name
                for item
                in result.queue.items
            ],
            [
                "Local Next",
                "Next",
            ],
        )

    def test_non_playlist_context_does_not_reconstruct_gaps(
        self,
    ):
        current_uri = (
            "spotify:track:Current123"
        )

        base = ready_queue(
            queue_item(
                "Current",
                current_uri,
            ),
            queue_item(
                "Next",
                "spotify:track:Next123",
            ),
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Current",
                        current_uri,
                    ),
                    context_type="album",
                ),
                ResolvedServiceStub(
                    ()
                ),
            )
            .get_queue()
        )

        self.assertIs(
            result,
            base,
        )

    def test_shuffle_does_not_infer_playlist_gap_order(
        self,
    ):
        current_uri = (
            "spotify:local:"
            "artist:album:current:180"
        )

        base = ready_queue(
            queue_item(
                "First API",
                "spotify:track:First123",
            )
        )

        resolved = ResolvedServiceStub(
            (
                resolved_item(
                    0,
                    "Current",
                    current_uri,
                    local=True,
                ),
                resolved_item(
                    1,
                    "Local Next",
                    (
                        "spotify:local:"
                        "artist:album:"
                        "local:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    2,
                    "First API",
                    "spotify:track:First123",
                ),
            )
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Current",
                        current_uri,
                        local=True,
                    ),
                    shuffle=True,
                ),
                resolved,
            )
            .get_queue()
        )

        self.assertEqual(
            [
                item.name
                for item
                in result.queue.items
            ],
            [],
        )

        self.assertEqual(
            result
            .queue
            .currently_playing
            .name,
            "Current",
        )

    def test_manual_queue_mismatch_is_not_crossed(
        self,
    ):
        current_uri = (
            "spotify:local:"
            "artist:album:current:180"
        )

        base = ready_queue(
            queue_item(
                "Manual Queue",
                "spotify:track:Manual123",
            ),
            queue_item(
                "Expected",
                "spotify:track:Expected123",
            ),
        )

        resolved = ResolvedServiceStub(
            (
                resolved_item(
                    0,
                    "Current",
                    current_uri,
                    local=True,
                ),
                resolved_item(
                    1,
                    "Local",
                    (
                        "spotify:local:"
                        "artist:album:local:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    2,
                    "Expected",
                    "spotify:track:Expected123",
                ),
            )
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Current",
                        current_uri,
                        local=True,
                    )
                ),
                resolved,
            )
            .get_queue()
        )

        self.assertEqual(
            [
                item.name
                for item
                in result.queue.items
            ],
            [
                "Expected",
            ],
        )

    def test_episode_barrier_stops_local_inference(
        self,
    ):
        current_uri = (
            "spotify:local:"
            "artist:album:current:180"
        )

        first_uri = (
            "spotify:track:First123"
        )

        base = ready_queue(
            queue_item(
                "First",
                first_uri,
            ),
            queue_item(
                "Podcast",
                "spotify:episode:Episode123",
                item_type="episode",
            ),
            queue_item(
                "Later",
                "spotify:track:Later123",
            ),
        )

        resolved = ResolvedServiceStub(
            (
                resolved_item(
                    0,
                    "Current",
                    current_uri,
                    local=True,
                ),
                resolved_item(
                    1,
                    "Local Before",
                    (
                        "spotify:local:"
                        "artist:album:before:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    2,
                    "First",
                    first_uri,
                ),
                resolved_item(
                    3,
                    "Local After",
                    (
                        "spotify:local:"
                        "artist:album:after:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    4,
                    "Later",
                    "spotify:track:Later123",
                ),
            )
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Current",
                        current_uri,
                        local=True,
                    )
                ),
                resolved,
            )
            .get_queue()
        )

        self.assertEqual(
            [
                item.name
                for item
                in result.queue.items
            ],
            [
                "Local Before",
                "First",
                "Podcast",
                "Later",
            ],
        )

    def test_resolved_failure_falls_back_safely(
        self,
    ):
        current_uri = (
            "spotify:local:"
            "artist:album:current:180"
        )

        base = ready_queue(
            queue_item(
                "Next",
                "spotify:track:Next123",
            )
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Current",
                        current_uri,
                        local=True,
                    )
                ),
                ResolvedServiceStub(
                    (),
                    ready=False,
                ),
            )
            .get_queue()
        )

        self.assertEqual(
            [
                item.name
                for item
                in result.queue.items
            ],
            [],
        )

        self.assertEqual(
            result
            .queue
            .currently_playing
            .name,
            "Current",
        )

    def test_resolved_playlist_is_cached(
        self,
    ):
        current_uri = (
            "spotify:local:"
            "artist:album:current:180"
        )

        next_uri = (
            "spotify:track:Next123"
        )

        base = ready_queue(
            queue_item(
                "Next",
                next_uri,
            )
        )

        resolved = ResolvedServiceStub(
            (
                resolved_item(
                    0,
                    "Current",
                    current_uri,
                    local=True,
                ),
                resolved_item(
                    1,
                    "Local",
                    (
                        "spotify:local:"
                        "artist:album:local:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    2,
                    "Next",
                    next_uri,
                ),
            )
        )

        service = self.make_service(
            base,
            player_payload(
                player_track(
                    "Current",
                    current_uri,
                    local=True,
                )
            ),
            resolved,
        )

        service.get_queue()
        service.get_queue()

        self.assertEqual(
            len(
                resolved.calls
            ),
            1,
        )

    def test_resolved_playlist_paginates_by_raw_positions(
        self,
    ):
        current_uri = (
            "spotify:local:"
            "artist:album:current:180"
        )

        base = ready_queue(
            queue_item(
                "Next",
                "spotify:track:Next123",
            ),
            queue_item(
                "Later",
                "spotify:track:Later123",
            ),
        )

        resolved = ResolvedServiceStub(
            (
                resolved_item(
                    0,
                    "Current",
                    current_uri,
                    local=True,
                ),
                resolved_item(
                    1,
                    "Local One",
                    (
                        "spotify:local:"
                        "artist:album:one:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    2,
                    "Next",
                    "spotify:track:Next123",
                ),
                resolved_item(
                    3,
                    "Local Two",
                    (
                        "spotify:local:"
                        "artist:album:two:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    4,
                    "Later",
                    "spotify:track:Later123",
                ),
            ),
            page_size=2,
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Current",
                        current_uri,
                        local=True,
                    )
                ),
                resolved,
            )
            .get_queue()
        )

        self.assertEqual(
            [
                call[2]
                for call
                in resolved.calls
            ],
            [
                0,
                2,
                4,
            ],
        )

        self.assertEqual(
            [
                item.name
                for item
                in result.queue.items
            ],
            [
                "Local One",
                "Next",
                "Local Two",
                "Later",
            ],
        )

    def test_main_window_wraps_queue_service_with_effective_service(
        self,
    ):
        source = inspect.getsource(
            MainWindow.build_pages
        )

        self.assertIn(
            "SpotifyEffectiveQueueService",
            source,
        )

        self.assertIn(
            "SpotifyQueueService",
            source,
        )

        self.assertIn(
            (
                "spotify_resolved_playlist_service"
            ),
            source,
        )

    def test_main_window_keeps_queue_loading_lazy(
        self,
    ):
        source = inspect.getsource(
            MainWindow.build_pages
        )

        self.assertNotIn(
            ".load_queue(",
            source,
        )

        self.assertIn(
            (
                "lambda manager="
                "spotify_session_manager"
            ),
            source,
        )

    def test_all_local_playlist_tail_precedes_api_future(
        self,
    ):
        current_uri = (
            "spotify:local:"
            "artist:album:current:180"
        )

        base = ready_queue(
            queue_item(
                "Post Playlist",
                "spotify:track:Post123",
            ),
            queue_item(
                "Later",
                "spotify:track:Later123",
            ),
        )

        resolved = ResolvedServiceStub(
            (
                resolved_item(
                    0,
                    "Current",
                    current_uri,
                    local=True,
                ),
                resolved_item(
                    1,
                    "Local Tail One",
                    (
                        "spotify:local:"
                        "artist:album:tailone:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    2,
                    "Local Tail Two",
                    (
                        "spotify:local:"
                        "artist:album:tailtwo:180"
                    ),
                    local=True,
                ),
            )
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Current",
                        current_uri,
                        local=True,
                    )
                ),
                resolved,
            )
            .get_queue()
        )

        self.assertEqual(
            [
                item.name
                for item
                in result.queue.items
            ],
            [
                "Local Tail One",
                "Local Tail Two",
                "Post Playlist",
                "Later",
            ],
        )

        self.assertTrue(
            result.queue.items[
                0
            ].is_local
        )

        self.assertTrue(
            result.queue.items[
                1
            ].is_local
        )

    def test_trailing_locals_follow_last_matched_playlist_anchor(
        self,
    ):
        current_uri = (
            "spotify:local:"
            "artist:album:current:180"
        )

        anchor_uri = (
            "spotify:track:Anchor123"
        )

        base = ready_queue(
            queue_item(
                "Current",
                current_uri,
                local=True,
            ),
            queue_item(
                "Anchor",
                anchor_uri,
            ),
            queue_item(
                "Post Playlist",
                "spotify:track:Post123",
            ),
        )

        resolved = ResolvedServiceStub(
            (
                resolved_item(
                    0,
                    "Current",
                    current_uri,
                    local=True,
                ),
                resolved_item(
                    1,
                    "Anchor",
                    anchor_uri,
                ),
                resolved_item(
                    2,
                    "Local Tail One",
                    (
                        "spotify:local:"
                        "artist:album:tailone:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    3,
                    "Local Tail Two",
                    (
                        "spotify:local:"
                        "artist:album:tailtwo:180"
                    ),
                    local=True,
                ),
            )
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Current",
                        current_uri,
                        local=True,
                    )
                ),
                resolved,
            )
            .get_queue()
        )

        self.assertEqual(
            [
                item.name
                for item
                in result.queue.items
            ],
            [
                "Anchor",
                "Local Tail One",
                "Local Tail Two",
                "Post Playlist",
            ],
        )

    def test_missing_nonlocal_uri_blocks_tail_inference(
        self,
    ):
        current_uri = (
            "spotify:local:"
            "artist:album:current:180"
        )

        base = ready_queue(
            queue_item(
                "Current",
                current_uri,
                local=True,
            ),
            queue_item(
                "API Future",
                "spotify:track:Future123",
            ),
        )

        resolved = ResolvedServiceStub(
            (
                resolved_item(
                    0,
                    "Current",
                    current_uri,
                    local=True,
                ),
                resolved_item(
                    1,
                    "Local",
                    (
                        "spotify:local:"
                        "artist:album:local:180"
                    ),
                    local=True,
                ),
                resolved_item(
                    2,
                    "Untrusted Catalogue",
                    "",
                ),
            )
        )

        result = (
            self.make_service(
                base,
                player_payload(
                    player_track(
                        "Current",
                        current_uri,
                        local=True,
                    )
                ),
                resolved,
            )
            .get_queue()
        )

        self.assertIs(
            result,
            base,
        )


if __name__ == "__main__":
    unittest.main()
