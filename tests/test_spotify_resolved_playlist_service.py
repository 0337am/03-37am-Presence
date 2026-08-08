from __future__ import annotations

import inspect
import tempfile
import unittest
from dataclasses import (
    FrozenInstanceError,
)
from pathlib import Path

from src.media.spotify_playlist_resolver import (
    ResolvedSpotifyPlaylistPage,
    SpotifyPlaylistResolver,
)
from src.media.unified_track import (
    LocalTrackCandidate,
    UnifiedTrackSource,
)
from src.spotify.playlist_models import (
    SpotifyPlaylistItem,
    SpotifyPlaylistItemsPage,
    SpotifyPlaylistTrack,
)
from src.spotify.playlist_service import (
    SpotifyPlaylistServiceResult,
    SpotifyPlaylistServiceStatus,
)
from src.spotify.resolved_playlist_service import (
    SpotifyResolvedPlaylistService,
    SpotifyResolvedPlaylistServiceResult,
    SpotifyResolvedPlaylistServiceStatus,
)


def catalogue_item():
    return SpotifyPlaylistItem(
        track=SpotifyPlaylistTrack(
            title="Catalog Track",
            artist="Artist",
            album="Album",
            duration_ms=180000,
            spotify_id="track123",
            spotify_uri=(
                "spotify:track:track123"
            ),
            artwork_reference=(
                "https://i.scdn.co/art"
            ),
            is_local=False,
            playable=True,
        ),
        is_local=False,
        added_at=(
            "2026-08-08T00:00:00Z"
        ),
    )


def local_item(
    *,
    title="Rental",
):
    return SpotifyPlaylistItem(
        track=SpotifyPlaylistTrack(
            title=title,
            artist="Juice WRLD",
            album="Unreleased",
            duration_ms=240000,
            spotify_id="",
            spotify_uri=(
                "spotify:local:"
                "Juice%20WRLD:"
                "Unreleased:"
                + title.replace(
                    " ",
                    "%20",
                )
                + ":240"
            ),
            artwork_reference="",
            is_local=True,
            playable=False,
        ),
        is_local=True,
        added_at=(
            "2026-08-08T00:00:00Z"
        ),
    )


def source_page(
    *items,
    limit=50,
    offset=0,
    total=None,
    omitted_items=0,
):
    if total is None:
        total = len(
            items
        )

    return SpotifyPlaylistItemsPage(
        items=tuple(
            items
        ),
        limit=limit,
        offset=offset,
        total=total,
        omitted_items=(
            omitted_items
        ),
    )


def upstream_ready(
    page,
    *,
    refreshed=False,
):
    return SpotifyPlaylistServiceResult(
        status=(
            SpotifyPlaylistServiceStatus
            .READY
        ),
        items_page=page,
        message="Spotify playlist loaded.",
        refreshed=refreshed,
    )


def resolved_catalogue_page():
    return (
        SpotifyPlaylistResolver()
        .resolve_page(
            source_page(
                catalogue_item()
            )
        )
    )


class RecordingPlaylistService:
    def __init__(
        self,
        result,
    ):
        self.result = result
        self.calls = []

    def get_playlist_items(
        self,
        playlist_id,
        *,
        limit=50,
        offset=0,
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

        return self.result


class ExplodingPlaylistService:
    def get_playlist_items(
        self,
        playlist_id,
        *,
        limit=50,
        offset=0,
        market=None,
    ):
        raise RuntimeError(
            "simulated upstream failure"
        )


class CountingProvider:
    def __init__(
        self,
        value,
    ):
        self.value = value
        self.calls = 0

    def __call__(
        self,
    ):
        self.calls += 1
        return self.value


class ExplodingProvider:
    def __init__(
        self,
    ):
        self.calls = 0

    def __call__(
        self,
    ):
        self.calls += 1

        raise RuntimeError(
            "simulated snapshot failure"
        )


class ExplodingResolver:
    def resolve_page(
        self,
        page,
        candidates,
    ):
        raise RuntimeError(
            "simulated resolution failure"
        )


class InvalidResolver:
    def resolve_page(
        self,
        page,
        candidates,
    ):
        return object()


class RecordingResolver:
    def __init__(
        self,
        result,
    ):
        self.result = result
        self.calls = []

    def resolve_page(
        self,
        page,
        candidates,
    ):
        self.calls.append(
            (
                page,
                candidates,
            )
        )

        return self.result


class SpotifyResolvedPlaylistResultTests(
    unittest.TestCase
):
    def test_result_is_frozen(
        self,
    ):
        result = (
            SpotifyResolvedPlaylistServiceResult(
                status=(
                    SpotifyResolvedPlaylistServiceStatus
                    .READY
                ),
                resolved_page=(
                    resolved_catalogue_page()
                ),
            )
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            result.message = "changed"

    def test_ready_result_requires_resolved_page(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyResolvedPlaylistServiceResult(
                status=(
                    SpotifyResolvedPlaylistServiceStatus
                    .READY
                )
            )

    def test_non_ready_result_rejects_resolved_page(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyResolvedPlaylistServiceResult(
                status=(
                    SpotifyResolvedPlaylistServiceStatus
                    .DISCONNECTED
                ),
                resolved_page=(
                    resolved_catalogue_page()
                ),
            )

    def test_error_result_requires_error_code(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyResolvedPlaylistServiceResult(
                status=(
                    SpotifyResolvedPlaylistServiceStatus
                    .ERROR
                )
            )

    def test_retry_after_is_validated(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyResolvedPlaylistServiceResult(
                status=(
                    SpotifyResolvedPlaylistServiceStatus
                    .ERROR
                ),
                error_code="rate_limit",
                retry_after_seconds=-1,
            )

    def test_ready_result_properties(
        self,
    ):
        result = (
            SpotifyResolvedPlaylistServiceResult(
                status=(
                    SpotifyResolvedPlaylistServiceStatus
                    .READY
                ),
                resolved_page=(
                    resolved_catalogue_page()
                ),
                local_snapshot_available=None,
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertTrue(
            result.connected
        )

        self.assertFalse(
            result.requires_reauthorization
        )

    def test_reauthorization_result_property(
        self,
    ):
        result = (
            SpotifyResolvedPlaylistServiceResult(
                status=(
                    SpotifyResolvedPlaylistServiceStatus
                    .REAUTHORIZATION_REQUIRED
                )
            )
        )

        self.assertFalse(
            result.ready
        )

        self.assertFalse(
            result.connected
        )

        self.assertTrue(
            result.requires_reauthorization
        )

    def test_local_snapshot_marker_requires_ready_state(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            SpotifyResolvedPlaylistServiceResult(
                status=(
                    SpotifyResolvedPlaylistServiceStatus
                    .ERROR
                ),
                error_code="test_error",
                local_snapshot_available=False,
            )


class SpotifyResolvedPlaylistServiceTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.root = Path(
            self.temp.name
        ).resolve()

    def tearDown(
        self,
    ):
        self.temp.cleanup()

    def candidate(
        self,
    ):
        path = (
            self.root
            / "Rental.mp3"
        )

        path.touch(
            exist_ok=True
        )

        return LocalTrackCandidate(
            title="Rental",
            artist="Juice WRLD",
            album="Unreleased",
            duration_ms=240000,
            local_path=str(
                path
            ),
            artwork_reference=(
                "local-art"
            ),
        )

    def test_constructor_requires_playlist_service(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyResolvedPlaylistService(
                object()
            )

    def test_constructor_requires_resolver(
        self,
    ):
        upstream = (
            RecordingPlaylistService(
                upstream_ready(
                    source_page(
                        catalogue_item()
                    )
                )
            )
        )

        with self.assertRaises(
            TypeError
        ):
            SpotifyResolvedPlaylistService(
                upstream,
                playlist_resolver=object(),
            )

    def test_constructor_requires_candidate_provider(
        self,
    ):
        upstream = (
            RecordingPlaylistService(
                upstream_ready(
                    source_page(
                        catalogue_item()
                    )
                )
            )
        )

        with self.assertRaises(
            TypeError
        ):
            SpotifyResolvedPlaylistService(
                upstream,
                candidate_provider=object(),
            )

    def test_catalogue_page_skips_candidate_provider(
        self,
    ):
        page = source_page(
            catalogue_item()
        )

        upstream = (
            RecordingPlaylistService(
                upstream_ready(
                    page
                )
            )
        )

        provider = (
            ExplodingProvider()
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream,
                candidate_provider=provider,
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            provider.calls,
            0,
        )

        self.assertIsNone(
            result.local_snapshot_available
        )

        track = (
            result.resolved_page
            .items[
                0
            ]
            .unified_track
        )

        self.assertIs(
            track.source,
            UnifiedTrackSource.SPOTIFY,
        )

    def test_local_page_with_snapshot_resolves_available(
        self,
    ):
        page = source_page(
            local_item()
        )

        upstream = (
            RecordingPlaylistService(
                upstream_ready(
                    page
                )
            )
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream,
                candidate_provider=(
                    lambda: (
                        self.candidate(),
                    )
                ),
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertIs(
            result.local_snapshot_available,
            True,
        )

        track = (
            result.resolved_page
            .items[
                0
            ]
            .unified_track
        )

        self.assertIs(
            track.source,
            UnifiedTrackSource.LOCAL,
        )

        self.assertTrue(
            track.local_available
        )

        self.assertTrue(
            track.playable
        )

        self.assertTrue(
            Path(
                track.local_path
            ).is_file()
        )

    def test_local_page_without_snapshot_is_safe(
        self,
    ):
        page = source_page(
            local_item()
        )

        upstream = (
            RecordingPlaylistService(
                upstream_ready(
                    page
                )
            )
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertIs(
            result.local_snapshot_available,
            False,
        )

        track = (
            result.resolved_page
            .items[
                0
            ]
            .unified_track
        )

        self.assertFalse(
            track.local_available
        )

        self.assertFalse(
            track.playable
        )

        self.assertEqual(
            track.local_path,
            "",
        )

    def test_candidate_provider_is_called_once_per_local_page(
        self,
    ):
        page = source_page(
            local_item(),
            local_item(),
        )

        upstream = (
            RecordingPlaylistService(
                upstream_ready(
                    page
                )
            )
        )

        provider = (
            CountingProvider(
                (
                    self.candidate(),
                )
            )
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream,
                candidate_provider=provider,
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            provider.calls,
            1,
        )

        self.assertEqual(
            len(
                result.resolved_page.items
            ),
            2,
        )

    def test_candidate_provider_exception_is_safe(
        self,
    ):
        upstream = (
            RecordingPlaylistService(
                upstream_ready(
                    source_page(
                        local_item()
                    )
                )
            )
        )

        provider = (
            ExplodingProvider()
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream,
                candidate_provider=provider,
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyResolvedPlaylistServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.error_code,
            "local_snapshot_error",
        )

        self.assertEqual(
            provider.calls,
            1,
        )

    def test_disconnected_upstream_is_mapped(
        self,
    ):
        upstream = (
            RecordingPlaylistService(
                SpotifyPlaylistServiceResult(
                    status=(
                        SpotifyPlaylistServiceStatus
                        .DISCONNECTED
                    ),
                    message=(
                        "Spotify is not connected."
                    ),
                )
            )
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyResolvedPlaylistServiceStatus
            .DISCONNECTED,
        )

        self.assertEqual(
            result.message,
            "Spotify is not connected.",
        )

    def test_reauthorization_upstream_is_mapped(
        self,
    ):
        upstream = (
            RecordingPlaylistService(
                SpotifyPlaylistServiceResult(
                    status=(
                        SpotifyPlaylistServiceStatus
                        .REAUTHORIZATION_REQUIRED
                    ),
                    message=(
                        "Reconnect Spotify."
                    ),
                )
            )
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyResolvedPlaylistServiceStatus
            .REAUTHORIZATION_REQUIRED,
        )

        self.assertTrue(
            result.requires_reauthorization
        )

    def test_upstream_error_metadata_is_preserved(
        self,
    ):
        upstream = (
            RecordingPlaylistService(
                SpotifyPlaylistServiceResult(
                    status=(
                        SpotifyPlaylistServiceStatus
                        .ERROR
                    ),
                    message="Rate limited.",
                    error_code="rate_limit",
                    retry_after_seconds=9,
                    refreshed=True,
                )
            )
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyResolvedPlaylistServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.error_code,
            "rate_limit",
        )

        self.assertEqual(
            result.retry_after_seconds,
            9,
        )

        self.assertTrue(
            result.refreshed
        )

    def test_invalid_upstream_result_is_safe(
        self,
    ):
        upstream = (
            RecordingPlaylistService(
                object()
            )
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyResolvedPlaylistServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_playlist_result",
        )

    def test_upstream_exception_is_safe(
        self,
    ):
        result = (
            SpotifyResolvedPlaylistService(
                ExplodingPlaylistService()
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyResolvedPlaylistServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.error_code,
            "playlist_service_error",
        )

    def test_resolver_exception_is_safe(
        self,
    ):
        upstream = (
            RecordingPlaylistService(
                upstream_ready(
                    source_page(
                        catalogue_item()
                    )
                )
            )
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream,
                playlist_resolver=(
                    ExplodingResolver()
                ),
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyResolvedPlaylistServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.error_code,
            "playlist_resolution_error",
        )

    def test_invalid_resolver_result_is_safe(
        self,
    ):
        upstream = (
            RecordingPlaylistService(
                upstream_ready(
                    source_page(
                        catalogue_item()
                    )
                )
            )
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream,
                playlist_resolver=(
                    InvalidResolver()
                ),
            )
            .get_playlist_items(
                "playlist123"
            )
        )

        self.assertIs(
            result.status,
            SpotifyResolvedPlaylistServiceStatus
            .ERROR,
        )

        self.assertEqual(
            result.error_code,
            "invalid_resolved_playlist",
        )

    def test_arguments_are_forwarded_exactly(
        self,
    ):
        page = source_page(
            catalogue_item()
        )

        upstream = (
            RecordingPlaylistService(
                upstream_ready(
                    page,
                    refreshed=True,
                )
            )
        )

        result = (
            SpotifyResolvedPlaylistService(
                upstream
            )
            .get_playlist_items(
                "abc123",
                limit=17,
                offset=34,
                market="GB",
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertTrue(
            result.refreshed
        )

        self.assertEqual(
            upstream.calls,
            [
                (
                    "abc123",
                    17,
                    34,
                    "GB",
                )
            ],
        )


class SpotifyResolvedPlaylistServiceBoundaryTests(
    unittest.TestCase
):
    def test_service_owns_no_qt_scanning_credentials_or_direct_api(
        self,
    ):
        module = __import__(
            (
                "src.spotify."
                "resolved_playlist_service"
            ),
            fromlist=[
                "dummy",
            ],
        )

        source = inspect.getsource(
            module
        )

        forbidden = (
            "PyQt",
            "LocalMusicIndex",
            "LocalMusicQtScanRuntime",
            "src.media.local_music_index",
            "src.system.local_music_preferences",
            "src.spotify.web_api",
            "src.spotify.session_manager",
            "SpotifyWebApiClient",
            "access_token",
            "credential",
            "start_scan",
        )

        for marker in forbidden:
            self.assertNotIn(
                marker,
                source,
            )
