from __future__ import annotations

import inspect
import tempfile
import unittest
from dataclasses import (
    FrozenInstanceError,
)
from pathlib import Path

from src.media.local_track_resolver import (
    LocalTrackResolution,
    LocalTrackResolutionStatus,
)
from src.media.spotify_playlist_resolver import (
    ResolvedSpotifyPlaylistItem,
    ResolvedSpotifyPlaylistPage,
    SpotifyPlaylistResolver,
    SpotifyPlaylistResolverError,
)
from src.media.unified_track import (
    LocalTrackCandidate,
    UnifiedTrack,
    UnifiedTrackSource,
)
from src.spotify.playlist_models import (
    SpotifyPlaylistItem,
    SpotifyPlaylistItemsPage,
    SpotifyPlaylistTrack,
)


def catalogue_item(
    *,
    playable=True,
    artwork_reference=(
        "https://i.scdn.co/track-art"
    ),
):
    return SpotifyPlaylistItem(
        track=SpotifyPlaylistTrack(
            title="Rental",
            artist="Juice WRLD",
            album="Unreleased",
            duration_ms=240000,
            spotify_id="track123",
            spotify_uri=(
                "spotify:track:track123"
            ),
            artwork_reference=(
                artwork_reference
            ),
            is_local=False,
            playable=playable,
        ),
        is_local=False,
        added_at=(
            "2026-08-08T00:00:00Z"
        ),
    )


def local_item(
    *,
    title="Rental",
    duration_ms=240000,
):
    return SpotifyPlaylistItem(
        track=SpotifyPlaylistTrack(
            title=title,
            artist="Juice WRLD",
            album="Unreleased",
            duration_ms=duration_ms,
            spotify_id="",
            spotify_uri=(
                "spotify:local:"
                "Juice%20WRLD:"
                "Unreleased:"
                + title.replace(
                    " ",
                    "%20",
                )
                + ":"
                + str(
                    duration_ms // 1000
                )
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


def local_unavailable_track(
    item,
):
    return UnifiedTrack(
        title=item.track.title,
        source=UnifiedTrackSource.LOCAL,
        artist=item.track.artist,
        album=item.track.album,
        duration_ms=(
            item.track.duration_ms
        ),
        spotify_uri=(
            item.track.spotify_uri
        ),
        local_available=False,
        playable=False,
    )


class RecordingResolver:
    def __init__(
        self,
        result,
    ):
        self.result = result
        self.calls = []

    def resolve(
        self,
        reference,
        candidates,
    ):
        self.calls.append(
            (
                reference,
                candidates,
            )
        )

        return self.result


class InvalidResolver:
    def resolve(
        self,
        reference,
        candidates,
    ):
        return object()


class ExplodingResolver:
    def __init__(
        self,
    ):
        self.calls = 0

    def resolve(
        self,
        reference,
        candidates,
    ):
        self.calls += 1

        raise AssertionError(
            (
                "Catalogue track touched "
                "the local resolver."
            )
        )


class ResolvedSpotifyPlaylistModelTests(
    unittest.TestCase
):
    def test_resolved_item_exposes_exact_playlist_position(
        self,
    ):
        from dataclasses import replace

        item = replace(
            catalogue_item(),
            position=28,
        )

        resolved = (
            SpotifyPlaylistResolver()
            .resolve_item(
                item
            )
        )

        self.assertEqual(
            resolved.position,
            28,
        )

        self.assertEqual(
            resolved.playlist_item.position,
            28,
        )

    def test_resolved_item_is_frozen(
        self,
    ):
        item = catalogue_item()

        resolved = (
            ResolvedSpotifyPlaylistItem(
                playlist_item=item,
                unified_track=(
                    item.track
                    .to_unified_track()
                ),
            )
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            resolved.unified_track = None

    def test_local_item_requires_resolution(
        self,
    ):
        item = local_item()

        with self.assertRaises(
            ValueError
        ):
            ResolvedSpotifyPlaylistItem(
                playlist_item=item,
                unified_track=(
                    local_unavailable_track(
                        item
                    )
                ),
            )

    def test_catalogue_item_rejects_local_resolution(
        self,
    ):
        item = catalogue_item()

        with self.assertRaises(
            ValueError
        ):
            ResolvedSpotifyPlaylistItem(
                playlist_item=item,
                unified_track=(
                    item.track
                    .to_unified_track()
                ),
                local_resolution=(
                    LocalTrackResolution(
                        status=(
                            LocalTrackResolutionStatus
                            .NOT_FOUND
                        )
                    )
                ),
            )

    def test_local_item_requires_local_unified_source(
        self,
    ):
        item = local_item()

        resolution = (
            LocalTrackResolution(
                status=(
                    LocalTrackResolutionStatus
                    .NOT_FOUND
                )
            )
        )

        catalogue = catalogue_item()

        with self.assertRaises(
            ValueError
        ):
            ResolvedSpotifyPlaylistItem(
                playlist_item=item,
                unified_track=(
                    catalogue.track
                    .to_unified_track()
                ),
                local_resolution=(
                    resolution
                ),
            )

    def test_catalogue_item_requires_spotify_source(
        self,
    ):
        item = catalogue_item()

        local = local_item()

        with self.assertRaises(
            ValueError
        ):
            ResolvedSpotifyPlaylistItem(
                playlist_item=item,
                unified_track=(
                    local_unavailable_track(
                        local
                    )
                ),
            )

    def test_resolved_page_is_frozen_and_counts_sources(
        self,
    ):
        catalogue = catalogue_item()
        local = local_item()

        catalogue_resolved = (
            ResolvedSpotifyPlaylistItem(
                playlist_item=(
                    catalogue
                ),
                unified_track=(
                    catalogue.track
                    .to_unified_track()
                ),
            )
        )

        local_resolution = (
            LocalTrackResolution(
                status=(
                    LocalTrackResolutionStatus
                    .NOT_FOUND
                )
            )
        )

        local_resolved = (
            ResolvedSpotifyPlaylistItem(
                playlist_item=local,
                unified_track=(
                    local_resolution
                    .as_unified_track(
                        local.track
                        .to_local_reference()
                    )
                ),
                local_resolution=(
                    local_resolution
                ),
            )
        )

        page = (
            ResolvedSpotifyPlaylistPage(
                items=(
                    catalogue_resolved,
                    local_resolved,
                ),
                limit=50,
                offset=0,
                total=2,
            )
        )

        self.assertEqual(
            page.catalogue_count,
            1,
        )

        self.assertEqual(
            page.local_count,
            1,
        )

        self.assertEqual(
            page.available_local_count,
            0,
        )

        self.assertEqual(
            page.unavailable_local_count,
            1,
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            page.total = 10

    def test_resolved_page_rejects_wrong_item_type(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            ResolvedSpotifyPlaylistPage(
                items=(
                    object(),
                ),
                limit=50,
                offset=0,
                total=1,
            )


class SpotifyPlaylistResolverTests(
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
        *,
        filename="Rental.mp3",
        title="Rental",
        duration_ms=240000,
        artwork_reference="",
    ):
        path = (
            self.root
            / filename
        )

        path.touch(
            exist_ok=True
        )

        return LocalTrackCandidate(
            title=title,
            artist="Juice WRLD",
            album="Unreleased",
            duration_ms=duration_ms,
            local_path=str(
                path
            ),
            artwork_reference=(
                artwork_reference
            ),
        )

    def test_constructor_requires_resolve_dependency(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            SpotifyPlaylistResolver(
                local_resolver=object()
            )

    def test_resolve_item_rejects_wrong_type(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            (
                SpotifyPlaylistResolver()
                .resolve_item(
                    object()
                )
            )

    def test_catalogue_item_bypasses_local_resolver(
        self,
    ):
        local_resolver = (
            ExplodingResolver()
        )

        resolved = (
            SpotifyPlaylistResolver(
                local_resolver=(
                    local_resolver
                )
            )
            .resolve_item(
                catalogue_item()
            )
        )

        self.assertIs(
            resolved.unified_track.source,
            UnifiedTrackSource.SPOTIFY,
        )

        self.assertEqual(
            local_resolver.calls,
            0,
        )

        self.assertIsNone(
            resolved.local_resolution
        )

    def test_catalogue_item_preserves_playability_and_artwork(
        self,
    ):
        item = catalogue_item(
            playable=False,
            artwork_reference="art-ref",
        )

        resolved = (
            SpotifyPlaylistResolver()
            .resolve_item(
                item
            )
        )

        self.assertFalse(
            resolved.unified_track.playable
        )

        self.assertEqual(
            resolved.unified_track
            .artwork_reference,
            "art-ref",
        )

    def test_local_matched_item_becomes_available_unified_track(
        self,
    ):
        item = local_item()

        candidate = self.candidate()

        resolved = (
            SpotifyPlaylistResolver()
            .resolve_item(
                item,
                (
                    candidate,
                ),
            )
        )

        self.assertIs(
            resolved.unified_track.source,
            UnifiedTrackSource.LOCAL,
        )

        self.assertTrue(
            resolved.unified_track
            .local_available
        )

        self.assertTrue(
            resolved.unified_track.playable
        )

        self.assertEqual(
            resolved.unified_track.local_path,
            candidate.local_path,
        )

        self.assertIs(
            resolved.local_resolution.status,
            LocalTrackResolutionStatus.MATCHED,
        )

    def test_local_not_found_becomes_unavailable(
        self,
    ):
        item = local_item()

        resolved = (
            SpotifyPlaylistResolver()
            .resolve_item(
                item,
                (),
            )
        )

        self.assertFalse(
            resolved.unified_track
            .local_available
        )

        self.assertFalse(
            resolved.unified_track.playable
        )

        self.assertEqual(
            resolved.unified_track.local_path,
            "",
        )

        self.assertIs(
            resolved.local_resolution.status,
            LocalTrackResolutionStatus
            .NOT_FOUND,
        )

    def test_local_ambiguous_becomes_unavailable(
        self,
    ):
        item = local_item()

        first = self.candidate(
            filename="one.mp3",
        )

        second = self.candidate(
            filename="two.mp3",
        )

        resolved = (
            SpotifyPlaylistResolver()
            .resolve_item(
                item,
                (
                    first,
                    second,
                ),
            )
        )

        self.assertIs(
            resolved.local_resolution.status,
            LocalTrackResolutionStatus
            .AMBIGUOUS,
        )

        self.assertFalse(
            resolved.unified_track
            .local_available
        )

        self.assertFalse(
            resolved.unified_track.playable
        )

    def test_resolve_page_handles_mixed_catalogue_and_local_items(
        self,
    ):
        local = local_item()

        candidate = self.candidate()

        page = SpotifyPlaylistItemsPage(
            items=(
                catalogue_item(),
                local,
            ),
            limit=50,
            offset=0,
            total=2,
        )

        resolved = (
            SpotifyPlaylistResolver()
            .resolve_page(
                page,
                (
                    candidate,
                ),
            )
        )

        self.assertEqual(
            len(
                resolved.items
            ),
            2,
        )

        self.assertEqual(
            resolved.catalogue_count,
            1,
        )

        self.assertEqual(
            resolved.local_count,
            1,
        )

        self.assertEqual(
            resolved.available_local_count,
            1,
        )

    def test_resolve_page_preserves_pagination_metadata(
        self,
    ):
        page = SpotifyPlaylistItemsPage(
            items=(
                catalogue_item(),
            ),
            limit=17,
            offset=34,
            total=88,
            omitted_items=3,
        )

        resolved = (
            SpotifyPlaylistResolver()
            .resolve_page(
                page
            )
        )

        self.assertEqual(
            resolved.limit,
            17,
        )

        self.assertEqual(
            resolved.offset,
            34,
        )

        self.assertEqual(
            resolved.total,
            88,
        )

        self.assertEqual(
            resolved.omitted_items,
            3,
        )

    def test_resolve_page_snapshots_candidate_generator_once(
        self,
    ):
        candidate = self.candidate()

        local_resolver = (
            RecordingResolver(
                LocalTrackResolution(
                    status=(
                        LocalTrackResolutionStatus
                        .NOT_FOUND
                    )
                )
            )
        )

        generated = []

        def candidates():
            generated.append(
                "iterated"
            )

            yield candidate

        page = SpotifyPlaylistItemsPage(
            items=(
                local_item(
                    title="Rental"
                ),
                local_item(
                    title="Rental Two"
                ),
            ),
            limit=50,
            offset=0,
            total=2,
        )

        (
            SpotifyPlaylistResolver(
                local_resolver=(
                    local_resolver
                )
            )
            .resolve_page(
                page,
                candidates(),
            )
        )

        self.assertEqual(
            generated,
            [
                "iterated",
            ],
        )

        self.assertEqual(
            len(
                local_resolver.calls
            ),
            2,
        )

        first_candidates = (
            local_resolver.calls[
                0
            ][1]
        )

        second_candidates = (
            local_resolver.calls[
                1
            ][1]
        )

        self.assertIs(
            first_candidates,
            second_candidates,
        )

        self.assertEqual(
            first_candidates,
            (
                candidate,
            ),
        )

    def test_local_match_uses_candidate_artwork(
        self,
    ):
        item = local_item()

        candidate = self.candidate(
            artwork_reference=(
                "local-art"
            )
        )

        resolved = (
            SpotifyPlaylistResolver()
            .resolve_item(
                item,
                (
                    candidate,
                ),
            )
        )

        self.assertEqual(
            resolved.unified_track
            .artwork_reference,
            "local-art",
        )

    def test_invalid_local_resolver_result_is_rejected(
        self,
    ):
        with self.assertRaises(
            SpotifyPlaylistResolverError
        ):
            (
                SpotifyPlaylistResolver(
                    local_resolver=(
                        InvalidResolver()
                    )
                )
                .resolve_item(
                    local_item(),
                    (),
                )
            )


class SpotifyPlaylistResolverBoundaryTests(
    unittest.TestCase
):
    def test_resolver_owns_no_qt_network_settings_or_scanning(
        self,
    ):
        source = inspect.getsource(
            __import__(
                (
                    "src.media."
                    "spotify_playlist_resolver"
                ),
                fromlist=[
                    "dummy",
                ],
            )
        )

        forbidden = (
            "PyQt",
            "qt_local_music",
            "LocalMusicIndex",
            "LocalMusicQtScanRuntime",
            "src.ui",
            "src.system.local_music_preferences",
            "src.spotify.web_api",
            "src.spotify.playlist_service",
            "SpotifyPlaylistService",
        )

        for marker in forbidden:
            self.assertNotIn(
                marker,
                source,
            )
