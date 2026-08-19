from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.media.local_track_resolver import (
    LocalTrackResolutionStatus,
    LocalTrackResolver,
    normalize_track_text,
)
from src.media.unified_track import (
    LocalTrackCandidate,
    LocalTrackReference,
    UnifiedTrackSource,
)
from tests.repo_paths import REPO_ROOT


class LocalTrackResolverTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp_directory.cleanup
        )

        self.root = Path(
            self.temp_directory.name
        ).resolve()

        self.reference = (
            LocalTrackReference(
                title="Rental",
                artist="Juice WRLD",
                album="Unreleased",
                duration_ms=240000,
                spotify_local_uri=(
                    "spotify:local:"
                    "Juice+WRLD:"
                    "Unreleased:"
                    "Rental:240"
                ),
            )
        )

    def candidate(
        self,
        *,
        filename="Rental.mp3",
        title="Rental",
        artist="Juice WRLD",
        album="Unreleased",
        duration_ms=240000,
        create=True,
    ):
        path = (
            self.root
            / filename
        )

        if create:
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            path.touch()

        return LocalTrackCandidate(
            title=title,
            artist=artist,
            album=album,
            duration_ms=duration_ms,
            local_path=str(
                path
            ),
        )

    def test_normalization_is_case_and_punctuation_tolerant(
        self,
    ):
        self.assertEqual(
            normalize_track_text(
                "  Monsters-In My Basement! "
            ),
            "monsters in my basement",
        )

    def test_exact_candidate_matches(
        self,
    ):
        candidate = self.candidate()

        result = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (
                    candidate,
                ),
            )
        )

        self.assertEqual(
            result.status,
            (
                LocalTrackResolutionStatus
                .MATCHED
            ),
        )

        self.assertEqual(
            result.candidate,
            candidate,
        )

    def test_case_and_punctuation_variation_matches(
        self,
    ):
        candidate = self.candidate(
            title="RENTAL!",
            artist="juice wrld",
        )

        result = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (
                    candidate,
                ),
            )
        )

        self.assertEqual(
            result.status,
            (
                LocalTrackResolutionStatus
                .MATCHED
            ),
        )

    def test_different_title_does_not_match(
        self,
    ):
        candidate = self.candidate(
            title="Robbery",
        )

        result = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (
                    candidate,
                ),
            )
        )

        self.assertEqual(
            result.status,
            (
                LocalTrackResolutionStatus
                .NOT_FOUND
            ),
        )

    def test_different_artist_does_not_match(
        self,
    ):
        candidate = self.candidate(
            artist="Different Artist",
        )

        result = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (
                    candidate,
                ),
            )
        )

        self.assertEqual(
            result.status,
            (
                LocalTrackResolutionStatus
                .NOT_FOUND
            ),
        )

    def test_excessive_duration_delta_does_not_match(
        self,
    ):
        candidate = self.candidate(
            duration_ms=260001,
        )

        result = (
            LocalTrackResolver(
                maximum_duration_delta_ms=10000
            )
            .resolve(
                self.reference,
                (
                    candidate,
                ),
            )
        )

        self.assertEqual(
            result.status,
            (
                LocalTrackResolutionStatus
                .NOT_FOUND
            ),
        )

    def test_matching_album_breaks_tie(
        self,
    ):
        weaker = self.candidate(
            filename="weak.mp3",
            album="Different Album",
        )

        stronger = self.candidate(
            filename="strong.mp3",
            album="Unreleased",
        )

        result = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (
                    weaker,
                    stronger,
                ),
            )
        )

        self.assertEqual(
            result.status,
            (
                LocalTrackResolutionStatus
                .MATCHED
            ),
        )

        self.assertEqual(
            result.candidate,
            stronger,
        )

    def test_better_duration_breaks_tie(
        self,
    ):
        weaker = self.candidate(
            filename="weak.mp3",
            album="Different",
            duration_ms=246000,
        )

        stronger = self.candidate(
            filename="strong.mp3",
            album="Different",
            duration_ms=240500,
        )

        result = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (
                    weaker,
                    stronger,
                ),
            )
        )

        self.assertEqual(
            result.candidate,
            stronger,
        )

    def test_equal_best_matches_are_ambiguous(
        self,
    ):
        first = self.candidate(
            filename="one.mp3",
        )

        second = self.candidate(
            filename="two.mp3",
        )

        result = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (
                    first,
                    second,
                ),
            )
        )

        self.assertEqual(
            result.status,
            (
                LocalTrackResolutionStatus
                .AMBIGUOUS
            ),
        )

        self.assertIsNone(
            result.candidate
        )

    def test_configurable_margin_can_force_ambiguity(
        self,
    ):
        stronger = self.candidate(
            filename="strong.mp3",
            album="Different",
            duration_ms=240500,
        )

        weaker = self.candidate(
            filename="weak.mp3",
            album="Different",
            duration_ms=244000,
        )

        result = (
            LocalTrackResolver(
                ambiguity_margin=10
            )
            .resolve(
                self.reference,
                (
                    stronger,
                    weaker,
                ),
            )
        )

        self.assertEqual(
            result.status,
            (
                LocalTrackResolutionStatus
                .AMBIGUOUS
            ),
        )

    def test_missing_file_is_ignored(
        self,
    ):
        candidate = self.candidate(
            create=False,
        )

        result = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (
                    candidate,
                ),
            )
        )

        self.assertEqual(
            result.status,
            (
                LocalTrackResolutionStatus
                .NOT_FOUND
            ),
        )

        self.assertEqual(
            result.considered_candidates,
            0,
        )

    def test_empty_candidate_list_is_not_found(
        self,
    ):
        result = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (),
            )
        )

        self.assertEqual(
            result.status,
            (
                LocalTrackResolutionStatus
                .NOT_FOUND
            ),
        )

    def test_duplicate_path_is_not_treated_as_ambiguity(
        self,
    ):
        candidate = self.candidate()

        duplicate = LocalTrackCandidate(
            title=candidate.title,
            artist=candidate.artist,
            album=candidate.album,
            duration_ms=(
                candidate.duration_ms
            ),
            local_path=(
                candidate.local_path
            ),
        )

        result = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (
                    candidate,
                    duplicate,
                ),
            )
        )

        self.assertEqual(
            result.status,
            (
                LocalTrackResolutionStatus
                .MATCHED
            ),
        )

        self.assertEqual(
            result.considered_candidates,
            1,
        )

    def test_constructor_validates_matching_settings(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            LocalTrackResolver(
                maximum_duration_delta_ms=-1
            )

        with self.assertRaises(
            TypeError
        ):
            LocalTrackResolver(
                ambiguity_margin=True
            )

    def test_matched_resolution_becomes_available_unified_track(
        self,
    ):
        candidate = self.candidate()

        resolution = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (
                    candidate,
                ),
            )
        )

        track = (
            resolution.as_unified_track(
                self.reference
            )
        )

        self.assertEqual(
            track.source,
            UnifiedTrackSource.LOCAL,
        )

        self.assertTrue(
            track.local_available
        )

        self.assertTrue(
            track.playable
        )

        self.assertEqual(
            track.local_path,
            candidate.local_path,
        )

    def test_not_found_becomes_unavailable_unified_track(
        self,
    ):
        resolution = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (),
            )
        )

        track = (
            resolution.as_unified_track(
                self.reference
            )
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

    def test_ambiguous_becomes_unavailable_unified_track(
        self,
    ):
        first = self.candidate(
            filename="one.mp3",
        )

        second = self.candidate(
            filename="two.mp3",
        )

        resolution = (
            LocalTrackResolver()
            .resolve(
                self.reference,
                (
                    first,
                    second,
                ),
            )
        )

        track = (
            resolution.as_unified_track(
                self.reference
            )
        )

        self.assertEqual(
            resolution.status,
            (
                LocalTrackResolutionStatus
                .AMBIGUOUS
            ),
        )

        self.assertFalse(
            track.local_available
        )

        self.assertFalse(
            track.playable
        )

    def test_resolver_rejects_non_candidate_values(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            LocalTrackResolver().resolve(
                self.reference,
                (
                    object(),
                ),
            )


class LocalTrackResolverBoundaryTests(
    unittest.TestCase
):
    def test_resolver_owns_no_spotify_network_ui_or_credentials(
        self,
    ):
        root = (
            REPO_ROOT
        )

        source = (
            root
            / "src"
            / "media"
            / "local_track_resolver.py"
        ).read_text(
            encoding="utf-8"
        )

        forbidden = (
            "PyQt",
            "urllib",
            "requests.",
            "SpotifyCredentialStore",
            "SpotifySessionManager",
            "SpotifyTokenClient",
            "windows_dpapi",
            "access_token",
            "refresh_token",
            "client_secret",
            "QSettings",
        )

        for marker in forbidden:
            with self.subTest(
                marker=marker
            ):
                self.assertNotIn(
                    marker,
                    source,
                )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
