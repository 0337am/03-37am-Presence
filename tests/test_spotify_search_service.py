from __future__ import annotations

from dataclasses import (
    FrozenInstanceError,
)
from pathlib import Path
from types import SimpleNamespace
import unittest

from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
    SpotifySearchPage,
    SpotifySearchResults,
)
from src.spotify.search_service import (
    DEFAULT_SPOTIFY_SEARCH_LIMIT,
    DEFAULT_SPOTIFY_SEARCH_TYPES,
    MAX_SPOTIFY_SEARCH_LIMIT,
    MAX_SPOTIFY_SEARCH_OFFSET,
    SpotifySearchParseError,
    SpotifySearchService,
    SpotifySearchServiceResult,
    SpotifySearchServiceStatus,
    normalize_search_types,
    spotify_search_results_from_payload,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiError,
)


def artist_stub(
    name="Artist",
    spotify_id="artist-1",
):
    return {
        "id": spotify_id,
        "name": name,
        "type": "artist",
        "uri": (
            "spotify:artist:"
            + spotify_id
        ),
        "external_urls": {
            "spotify": (
                "https://open.spotify.com/"
                "artist/"
                + spotify_id
            ),
        },
    }


def track_stub():
    return {
        "id": "track-1",
        "name": "Track One",
        "type": "track",
        "uri": "spotify:track:track-1",
        "external_urls": {
            "spotify": (
                "https://open.spotify.com/"
                "track/track-1"
            ),
        },
        "duration_ms": 183000,
        "explicit": True,
        "artists": [
            artist_stub(
                "Artist One",
                "artist-1",
            ),
            artist_stub(
                "Artist Two",
                "artist-2",
            ),
        ],
        "album": {
            "id": "album-1",
            "name": "Album One",
            "images": [
                {
                    "url": (
                        "https://i.scdn.co/"
                        "image/track-image"
                    ),
                    "width": 640,
                    "height": 640,
                },
            ],
        },
    }


def album_stub():
    return {
        "id": "album-1",
        "name": "Album One",
        "type": "album",
        "uri": "spotify:album:album-1",
        "external_urls": {
            "spotify": (
                "https://open.spotify.com/"
                "album/album-1"
            ),
        },
        "artists": [
            artist_stub(
                "Artist One",
                "artist-1",
            ),
        ],
        "images": [
            {
                "url": (
                    "https://i.scdn.co/"
                    "image/album-image"
                ),
            },
        ],
    }


def full_artist_stub():
    payload = artist_stub(
        "Artist One",
        "artist-1",
    )

    payload[
        "images"
    ] = [
        {
            "url": (
                "https://i.scdn.co/"
                "image/artist-image"
            ),
        },
    ]

    return payload


def playlist_stub():
    return {
        "id": "playlist-1",
        "name": "Playlist One",
        "type": "playlist",
        "uri": (
            "spotify:playlist:"
            "playlist-1"
        ),
        "external_urls": {
            "spotify": (
                "https://open.spotify.com/"
                "playlist/playlist-1"
            ),
        },
        "images": [
            {
                "url": (
                    "https://i.scdn.co/"
                    "image/playlist-image"
                ),
            },
        ],
        "owner": {
            "display_name": "Playlist Owner",
        },
    }


def page_stub(
    items,
    *,
    limit=5,
    offset=0,
    total=None,
):
    if total is None:
        total = len(
            items
        )

    return {
        "items": items,
        "limit": limit,
        "offset": offset,
        "total": total,
        "href": (
            "https://api.spotify.com/"
            "v1/search"
        ),
        "next": None,
        "previous": None,
    }


def search_payload(
    *,
    tracks=None,
    albums=None,
    artists=None,
    playlists=None,
    limit=5,
    offset=0,
):
    payload = {}

    if tracks is not None:
        payload[
            "tracks"
        ] = page_stub(
            tracks,
            limit=limit,
            offset=offset,
        )

    if albums is not None:
        payload[
            "albums"
        ] = page_stub(
            albums,
            limit=limit,
            offset=offset,
        )

    if artists is not None:
        payload[
            "artists"
        ] = page_stub(
            artists,
            limit=limit,
            offset=offset,
        )

    if playlists is not None:
        payload[
            "playlists"
        ] = page_stub(
            playlists,
            limit=limit,
            offset=offset,
        )

    return payload


class FakeSessionManager:
    def __init__(
        self,
        status=SpotifySessionStatus.READY,
        *,
        token="test-access-token",
        error=None,
    ):
        self.status = status
        self.token = token
        self.error = error
        self.resolve_calls = 0

    def resolve(
        self,
    ):
        self.resolve_calls += 1

        if self.error is not None:
            raise self.error

        token = None

        if self.token is not None:
            token = SimpleNamespace(
                access_token=self.token
            )

        return SimpleNamespace(
            status=self.status,
            token=token,
        )


class FakeApiClient:
    def __init__(
        self,
        payload=None,
        *,
        error=None,
    ):
        if payload is None:
            payload = search_payload(
                tracks=[
                    track_stub()
                ],
                albums=[
                    album_stub()
                ],
                artists=[
                    full_artist_stub()
                ],
                playlists=[
                    playlist_stub()
                ],
            )

        self.payload = payload
        self.error = error
        self.calls = []

    def get_json(
        self,
        access_token,
        path,
        *,
        query=None,
    ):
        self.calls.append(
            (
                access_token,
                path,
                query,
            )
        )

        if self.error is not None:
            raise self.error

        return self.payload


class SpotifySearchModelTests(
    unittest.TestCase
):
    def test_search_item_is_frozen_and_typed(
        self,
    ):
        item = SpotifySearchItem(
            item_type=(
                SpotifySearchItemType.TRACK
            ),
            spotify_id="track-1",
            name="Track",
            duration_ms=1000,
            explicit=False,
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            item.name = "Changed"

        with self.assertRaises(
            TypeError
        ):
            SpotifySearchItem(
                item_type="track",
                spotify_id="track-1",
                name="Track",
            )

    def test_search_item_rejects_invalid_required_fields(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifySearchItem(
                item_type=(
                    SpotifySearchItemType.TRACK
                ),
                spotify_id="",
                name="Track",
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifySearchItem(
                item_type=(
                    SpotifySearchItemType.TRACK
                ),
                spotify_id="track-1",
                name="Track",
                duration_ms=True,
            )

    def test_page_rejects_wrong_item_type(
        self,
    ):
        item = SpotifySearchItem(
            item_type=(
                SpotifySearchItemType.ALBUM
            ),
            spotify_id="album-1",
            name="Album",
        )

        with self.assertRaises(
            ValueError
        ):
            SpotifySearchPage(
                item_type=(
                    SpotifySearchItemType.TRACK
                ),
                items=(
                    item,
                ),
                limit=5,
                offset=0,
                total=1,
            )

    def test_results_expose_items_by_type(
        self,
    ):
        track = SpotifySearchItem(
            item_type=(
                SpotifySearchItemType.TRACK
            ),
            spotify_id="track-1",
            name="Track",
        )

        page = SpotifySearchPage(
            item_type=(
                SpotifySearchItemType.TRACK
            ),
            items=(
                track,
            ),
            limit=5,
            offset=0,
            total=1,
        )

        results = SpotifySearchResults(
            query="query",
            pages=(
                page,
            ),
        )

        self.assertEqual(
            results.tracks,
            (
                track,
            ),
        )

        self.assertEqual(
            results.albums,
            (),
        )

    def test_page_has_more_uses_limit_and_total(
        self,
    ):
        page = SpotifySearchPage(
            item_type=(
                SpotifySearchItemType.TRACK
            ),
            items=(),
            limit=5,
            offset=5,
            total=20,
        )

        self.assertTrue(
            page.has_more
        )

        final_page = SpotifySearchPage(
            item_type=(
                SpotifySearchItemType.TRACK
            ),
            items=(),
            limit=5,
            offset=15,
            total=20,
        )

        self.assertFalse(
            final_page.has_more
        )


class SpotifySearchInputTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        self.manager = (
            FakeSessionManager()
        )

        self.api = FakeApiClient()

        self.service = (
            SpotifySearchService(
                self.manager,
                api_client=self.api,
            )
        )

    def test_constructor_validates_dependencies(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifySearchService(
                object()
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifySearchService(
                self.manager,
                api_client=object(),
            )

    def test_query_validation_happens_before_session_resolution(
        self,
    ):
        for query in (
            "",
            "   ",
            "bad\nquery",
        ):
            with self.subTest(
                query=repr(
                    query
                )
            ):
                with self.assertRaises(
                    ValueError
                ):
                    self.service.search(
                        query
                    )

        with self.assertRaises(
            TypeError
        ):
            self.service.search(
                None
            )

        self.assertEqual(
            self.manager.resolve_calls,
            0,
        )

    def test_search_types_are_normalized_and_deduplicated(
        self,
    ):
        normalized = normalize_search_types(
            (
                "track",
                "ALBUM",
                (
                    SpotifySearchItemType
                    .TRACK
                ),
            )
        )

        self.assertEqual(
            normalized,
            (
                SpotifySearchItemType.TRACK,
                SpotifySearchItemType.ALBUM,
            ),
        )

        self.assertEqual(
            normalize_search_types(
                None
            ),
            DEFAULT_SPOTIFY_SEARCH_TYPES,
        )

    def test_invalid_search_types_are_rejected(
        self,
    ):
        for types in (
            (),
            (
                "show",
            ),
            (
                123,
            ),
        ):
            with self.subTest(
                types=repr(
                    types
                )
            ):
                with self.assertRaises(
                    (
                        TypeError,
                        ValueError,
                    )
                ):
                    self.service.search(
                        "query",
                        types=types,
                    )

        with self.assertRaises(
            TypeError
        ):
            self.service.search(
                "query",
                types="track",
            )

    def test_limit_is_bounded_to_current_spotify_contract(
        self,
    ):
        self.assertEqual(
            DEFAULT_SPOTIFY_SEARCH_LIMIT,
            5,
        )

        self.assertEqual(
            MAX_SPOTIFY_SEARCH_LIMIT,
            10,
        )

        for limit in (
            0,
            11,
            -1,
        ):
            with self.subTest(
                limit=limit
            ):
                with self.assertRaises(
                    ValueError
                ):
                    self.service.search(
                        "query",
                        limit=limit,
                    )

        with self.assertRaises(
            TypeError
        ):
            self.service.search(
                "query",
                limit=True,
            )

    def test_offset_is_bounded_to_current_spotify_contract(
        self,
    ):
        self.assertEqual(
            MAX_SPOTIFY_SEARCH_OFFSET,
            1000,
        )

        for offset in (
            -1,
            1001,
        ):
            with self.subTest(
                offset=offset
            ):
                with self.assertRaises(
                    ValueError
                ):
                    self.service.search(
                        "query",
                        offset=offset,
                    )

        with self.assertRaises(
            TypeError
        ):
            self.service.search(
                "query",
                offset=True,
            )

    def test_market_validation(
        self,
    ):
        payload = search_payload(
            tracks=[
                track_stub()
            ],
        )

        api = FakeApiClient(
            payload
        )

        service = SpotifySearchService(
            self.manager,
            api_client=api,
        )

        result = service.search(
            "query",
            types=(
                "track",
            ),
            market="gb",
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            api.calls[
                0
            ][2][
                "market"
            ],
            "GB",
        )

        for market in (
            "G",
            "GBR",
            "1B",
        ):
            with self.subTest(
                market=market
            ):
                with self.assertRaises(
                    ValueError
                ):
                    self.service.search(
                        "query",
                        market=market,
                    )


class SpotifySearchParserTests(
    unittest.TestCase
):
    def test_track_is_mapped_to_app_owned_model(
        self,
    ):
        results = (
            spotify_search_results_from_payload(
                search_payload(
                    tracks=[
                        track_stub()
                    ],
                ),
                query="Track",
                types=(
                    "track",
                ),
            )
        )

        self.assertEqual(
            len(
                results.tracks
            ),
            1,
        )

        track = results.tracks[
            0
        ]

        self.assertEqual(
            track.item_type,
            SpotifySearchItemType.TRACK,
        )

        self.assertEqual(
            track.name,
            "Track One",
        )

        self.assertEqual(
            track.subtitle,
            "Artist One, Artist Two",
        )

        self.assertEqual(
            track.duration_ms,
            183000,
        )

        self.assertTrue(
            track.explicit
        )

        self.assertEqual(
            track.image_url,
            (
                "https://i.scdn.co/"
                "image/track-image"
            ),
        )

    def test_album_is_mapped_to_app_owned_model(
        self,
    ):
        results = (
            spotify_search_results_from_payload(
                search_payload(
                    albums=[
                        album_stub()
                    ],
                ),
                query="Album",
                types=(
                    "album",
                ),
            )
        )

        album = results.albums[
            0
        ]

        self.assertEqual(
            album.name,
            "Album One",
        )

        self.assertEqual(
            album.subtitle,
            "Artist One",
        )

        self.assertEqual(
            album.uri,
            "spotify:album:album-1",
        )

    def test_artist_is_mapped_to_app_owned_model(
        self,
    ):
        results = (
            spotify_search_results_from_payload(
                search_payload(
                    artists=[
                        full_artist_stub()
                    ],
                ),
                query="Artist",
                types=(
                    "artist",
                ),
            )
        )

        artist = results.artists[
            0
        ]

        self.assertEqual(
            artist.name,
            "Artist One",
        )

        self.assertEqual(
            artist.subtitle,
            "Artist",
        )

        self.assertEqual(
            artist.image_url,
            (
                "https://i.scdn.co/"
                "image/artist-image"
            ),
        )

    def test_playlist_is_mapped_without_playlist_contents(
        self,
    ):
        payload = playlist_stub()

        self.assertNotIn(
            "items",
            payload
        )

        results = (
            spotify_search_results_from_payload(
                search_payload(
                    playlists=[
                        payload
                    ],
                ),
                query="Playlist",
                types=(
                    "playlist",
                ),
            )
        )

        playlist = (
            results.playlists[
                0
            ]
        )

        self.assertEqual(
            playlist.name,
            "Playlist One",
        )

        self.assertEqual(
            playlist.subtitle,
            "Playlist Owner",
        )

    def test_all_four_search_types_can_share_one_response(
        self,
    ):
        results = (
            spotify_search_results_from_payload(
                search_payload(
                    tracks=[
                        track_stub()
                    ],
                    albums=[
                        album_stub()
                    ],
                    artists=[
                        full_artist_stub()
                    ],
                    playlists=[
                        playlist_stub()
                    ],
                ),
                query="Everything",
                types=(
                    "track",
                    "album",
                    "artist",
                    "playlist",
                ),
            )
        )

        self.assertEqual(
            len(
                results.pages
            ),
            4,
        )

        self.assertEqual(
            len(
                results.tracks
            ),
            1,
        )

        self.assertEqual(
            len(
                results.albums
            ),
            1,
        )

        self.assertEqual(
            len(
                results.artists
            ),
            1,
        )

        self.assertEqual(
            len(
                results.playlists
            ),
            1,
        )

    def test_null_items_are_skipped_safely(
        self,
    ):
        results = (
            spotify_search_results_from_payload(
                search_payload(
                    tracks=[
                        None,
                        track_stub(),
                    ],
                ),
                query="Track",
                types=(
                    "track",
                ),
            )
        )

        self.assertEqual(
            len(
                results.tracks
            ),
            1,
        )

    def test_removed_legacy_fields_are_not_required(
        self,
    ):
        artist = full_artist_stub()

        self.assertNotIn(
            "followers",
            artist
        )

        self.assertNotIn(
            "popularity",
            artist
        )

        results = (
            spotify_search_results_from_payload(
                search_payload(
                    artists=[
                        artist
                    ],
                ),
                query="Artist",
                types=(
                    "artist",
                ),
            )
        )

        self.assertEqual(
            results.artists[
                0
            ].name,
            "Artist One",
        )

    def test_missing_requested_page_is_rejected(
        self,
    ):
        with self.assertRaises(
            SpotifySearchParseError
        ):
            spotify_search_results_from_payload(
                {},
                query="Track",
                types=(
                    "track",
                ),
            )

    def test_malformed_page_is_rejected(
        self,
    ):
        with self.assertRaises(
            SpotifySearchParseError
        ):
            spotify_search_results_from_payload(
                {
                    "tracks": {
                        "items": {},
                        "limit": 5,
                        "offset": 0,
                        "total": 0,
                    },
                },
                query="Track",
                types=(
                    "track",
                ),
            )

    def test_untrusted_spotify_page_url_is_rejected(
        self,
    ):
        track = track_stub()

        track[
            "external_urls"
        ][
            "spotify"
        ] = (
            "https://example.com/"
            "track/track-1"
        )

        with self.assertRaises(
            SpotifySearchParseError
        ):
            spotify_search_results_from_payload(
                search_payload(
                    tracks=[
                        track
                    ],
                ),
                query="Track",
                types=(
                    "track",
                ),
            )

    def test_item_uri_must_match_item_type(
        self,
    ):
        track = track_stub()

        track[
            "uri"
        ] = (
            "spotify:album:wrong"
        )

        with self.assertRaises(
            SpotifySearchParseError
        ):
            spotify_search_results_from_payload(
                search_payload(
                    tracks=[
                        track
                    ],
                ),
                query="Track",
                types=(
                    "track",
                ),
            )


class SpotifySearchServiceTests(
    unittest.TestCase
):
    def test_disconnected_session_never_calls_search_api(
        self,
    ):
        manager = FakeSessionManager(
            SpotifySessionStatus
            .DISCONNECTED,
            token=None,
        )

        api = FakeApiClient()

        service = SpotifySearchService(
            manager,
            api_client=api,
        )

        result = service.search(
            "query"
        )

        self.assertEqual(
            result.status,
            SpotifySearchServiceStatus
            .DISCONNECTED,
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_reauthorization_session_never_calls_search_api(
        self,
    ):
        manager = FakeSessionManager(
            SpotifySessionStatus
            .REAUTHORIZATION_REQUIRED,
            token=None,
        )

        api = FakeApiClient()

        result = SpotifySearchService(
            manager,
            api_client=api,
        ).search(
            "query"
        )

        self.assertTrue(
            result.requires_reauthorization
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_ready_session_builds_expected_search_request(
        self,
    ):
        manager = (
            FakeSessionManager()
        )

        api = FakeApiClient(
            search_payload(
                tracks=[
                    track_stub()
                ],
                albums=[
                    album_stub()
                ],
            )
        )

        service = SpotifySearchService(
            manager,
            api_client=api,
        )

        result = service.search(
            "Juice WRLD",
            types=(
                "track",
                "album",
            ),
            limit=10,
            offset=5,
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            len(
                api.calls
            ),
            1,
        )

        token, path, query = (
            api.calls[
                0
            ]
        )

        self.assertEqual(
            token,
            "test-access-token",
        )

        self.assertEqual(
            path,
            "/search",
        )

        self.assertEqual(
            query,
            {
                "q": "Juice WRLD",
                "type": "track,album",
                "limit": 10,
                "offset": 5,
            },
        )

    def test_refreshed_session_is_preserved(
        self,
    ):
        manager = FakeSessionManager(
            SpotifySessionStatus
            .REFRESHED
        )

        api = FakeApiClient(
            search_payload(
                tracks=[
                    track_stub()
                ],
            )
        )

        result = SpotifySearchService(
            manager,
            api_client=api,
        ).search(
            "query",
            types=(
                "track",
            ),
        )

        self.assertTrue(
            result.ready
        )

        self.assertTrue(
            result.refreshed
        )

    def test_missing_access_token_is_safe_error(
        self,
    ):
        manager = FakeSessionManager(
            token=None
        )

        api = FakeApiClient()

        result = SpotifySearchService(
            manager,
            api_client=api,
        ).search(
            "query"
        )

        self.assertEqual(
            result.status,
            SpotifySearchServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_session",
        )

        self.assertEqual(
            api.calls,
            [],
        )

    def test_web_api_reauthorization_maps_to_service_state(
        self,
    ):
        manager = (
            FakeSessionManager()
        )

        api = FakeApiClient(
            error=SpotifyWebApiError(
                "reauthorization_required",
                "safe",
            )
        )

        result = SpotifySearchService(
            manager,
            api_client=api,
        ).search(
            "query"
        )

        self.assertTrue(
            result.requires_reauthorization
        )

        self.assertIsNone(
            result.results
        )

    def test_web_api_error_preserves_safe_error_code(
        self,
    ):
        manager = (
            FakeSessionManager()
        )

        api = FakeApiClient(
            error=SpotifyWebApiError(
                "rate_limited",
                "safe",
            )
        )

        result = SpotifySearchService(
            manager,
            api_client=api,
        ).search(
            "query"
        )

        self.assertEqual(
            result.status,
            SpotifySearchServiceStatus.ERROR,
        )

        self.assertEqual(
            result.error_code,
            "rate_limited",
        )

        self.assertEqual(
            result.message,
            (
                "Spotify search could not "
                "be completed."
            ),
        )

    def test_session_exception_is_wrapped_without_detail(
        self,
    ):
        manager = FakeSessionManager(
            error=RuntimeError(
                "secret session detail"
            )
        )

        result = SpotifySearchService(
            manager,
            api_client=FakeApiClient(),
        ).search(
            "query"
        )

        self.assertEqual(
            result.error_code,
            "session_error",
        )

        self.assertNotIn(
            "secret session detail",
            result.message,
        )

    def test_api_exception_is_wrapped_without_detail(
        self,
    ):
        manager = (
            FakeSessionManager()
        )

        api = FakeApiClient(
            error=RuntimeError(
                "secret api detail"
            )
        )

        result = SpotifySearchService(
            manager,
            api_client=api,
        ).search(
            "query"
        )

        self.assertEqual(
            result.error_code,
            "spotify_api_error",
        )

        self.assertNotIn(
            "secret api detail",
            result.message,
        )

    def test_invalid_payload_becomes_safe_error(
        self,
    ):
        result = SpotifySearchService(
            FakeSessionManager(),
            api_client=FakeApiClient(
                payload={}
            ),
        ).search(
            "query",
            types=(
                "track",
            ),
        )

        self.assertEqual(
            result.error_code,
            "invalid_response",
        )

        self.assertIsNone(
            result.results
        )


class SpotifySearchResultTests(
    unittest.TestCase
):
    def test_ready_result_requires_results(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifySearchServiceResult(
                status=(
                    SpotifySearchServiceStatus
                    .READY
                )
            )

    def test_error_result_requires_error_code(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifySearchServiceResult(
                status=(
                    SpotifySearchServiceStatus
                    .ERROR
                )
            )


class SpotifySearchBoundaryTests(
    unittest.TestCase
):
    def test_search_service_result_has_no_credential_fields(
        self,
    ):
        fields = (
            SpotifySearchServiceResult
            .__dataclass_fields__
        )

        for forbidden in (
            "token",
            "access_token",
            "refresh_token",
        ):
            self.assertNotIn(
                forbidden,
                fields,
            )

    def test_search_layers_do_not_own_ui_oauth_or_persistence(
        self,
    ):
        root = (
            Path(
                __file__
            )
            .resolve()
            .parents[1]
        )

        source = "\n".join(
            (
                (
                    root
                    / "src"
                    / "spotify"
                    / "search_models.py"
                ).read_text(
                    encoding="utf-8"
                ),
                (
                    root
                    / "src"
                    / "spotify"
                    / "search_service.py"
                ).read_text(
                    encoding="utf-8"
                ),
            )
        )

        forbidden = (
            "PyQt6",
            "QSettings",
            "SpotifyCredentialStore",
            "windows_dpapi",
            "spotify_auth.dat",
            "SpotifyOAuthSession",
            "client_secret",
            "refresh_token",
            "print(",
            "logging.",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_search_contract_is_limited_to_first_four_catalog_types(
        self,
    ):
        self.assertEqual(
            DEFAULT_SPOTIFY_SEARCH_TYPES,
            (
                SpotifySearchItemType.TRACK,
                SpotifySearchItemType.ALBUM,
                SpotifySearchItemType.ARTIST,
                SpotifySearchItemType.PLAYLIST,
            ),
        )

    def test_result_repr_contains_no_access_token(
        self,
    ):
        result = SpotifySearchServiceResult(
            status=(
                SpotifySearchServiceStatus
                .DISCONNECTED
            ),
            message=(
                "Connect Spotify before "
                "searching."
            ),
        )

        rendered = repr(
            result
        )

        self.assertNotIn(
            "access_token",
            rendered
        )

        self.assertNotIn(
            "refresh_token",
            rendered
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
