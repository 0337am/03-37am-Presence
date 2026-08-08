from __future__ import annotations

import unittest
from dataclasses import (
    FrozenInstanceError,
)

from src.media.unified_track import (
    LocalTrackCandidate,
    LocalTrackReference,
    UnifiedTrack,
    UnifiedTrackSource,
)


class UnifiedTrackTests(
    unittest.TestCase
):
    def test_source_values_are_stable(
        self,
    ):
        self.assertEqual(
            UnifiedTrackSource.SPOTIFY.value,
            "spotify",
        )

        self.assertEqual(
            UnifiedTrackSource.LOCAL.value,
            "local",
        )

    def test_spotify_track_can_be_created(
        self,
    ):
        track = UnifiedTrack(
            title="Flaws And Sins",
            source=(
                UnifiedTrackSource.SPOTIFY
            ),
            artist="Juice WRLD",
            album="Death Race for Love",
            duration_ms=218000,
            spotify_id="spotify-id",
            spotify_uri=(
                "spotify:track:spotify-id"
            ),
        )

        self.assertEqual(
            track.artist,
            "Juice WRLD",
        )

        self.assertIsNone(
            track.local_available
        )

    def test_available_local_track_can_be_created(
        self,
    ):
        track = UnifiedTrack(
            title="Rental",
            source=(
                UnifiedTrackSource.LOCAL
            ),
            artist="Juice WRLD",
            local_path=(
                r"C:\Music\Rental.mp3"
            ),
            local_available=True,
        )

        self.assertTrue(
            track.local_available
        )

        self.assertTrue(
            track.playable
        )

    def test_unavailable_local_track_can_be_created(
        self,
    ):
        track = UnifiedTrack(
            title="Rental",
            source=(
                UnifiedTrackSource.LOCAL
            ),
            artist="Juice WRLD",
            local_available=False,
            playable=False,
        )

        self.assertFalse(
            track.local_available
        )

        self.assertFalse(
            track.playable
        )

    def test_title_is_required(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            UnifiedTrack(
                title="   ",
                source=(
                    UnifiedTrackSource.SPOTIFY
                ),
            )

    def test_source_must_be_enum(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            UnifiedTrack(
                title="Track",
                source="spotify",
            )

    def test_duration_rejects_boolean(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            UnifiedTrack(
                title="Track",
                source=(
                    UnifiedTrackSource.SPOTIFY
                ),
                duration_ms=True,
            )

    def test_duration_rejects_negative_value(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            UnifiedTrack(
                title="Track",
                source=(
                    UnifiedTrackSource.SPOTIFY
                ),
                duration_ms=-1,
            )

    def test_spotify_track_cannot_expose_local_path(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            UnifiedTrack(
                title="Track",
                source=(
                    UnifiedTrackSource.SPOTIFY
                ),
                local_path=(
                    r"C:\Music\Track.mp3"
                ),
            )

    def test_spotify_track_cannot_have_local_availability(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            UnifiedTrack(
                title="Track",
                source=(
                    UnifiedTrackSource.SPOTIFY
                ),
                local_available=True,
            )

    def test_local_track_requires_availability(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            UnifiedTrack(
                title="Track",
                source=(
                    UnifiedTrackSource.LOCAL
                ),
            )

    def test_available_local_track_requires_path(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            UnifiedTrack(
                title="Track",
                source=(
                    UnifiedTrackSource.LOCAL
                ),
                local_available=True,
            )

    def test_unavailable_local_track_cannot_expose_path(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            UnifiedTrack(
                title="Track",
                source=(
                    UnifiedTrackSource.LOCAL
                ),
                local_available=False,
                playable=False,
                local_path=(
                    r"C:\Music\Track.mp3"
                ),
            )

    def test_unavailable_local_track_cannot_be_playable(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            UnifiedTrack(
                title="Track",
                source=(
                    UnifiedTrackSource.LOCAL
                ),
                local_available=False,
                playable=True,
            )

    def test_local_reference_validates_and_trims_metadata(
        self,
    ):
        reference = LocalTrackReference(
            title="  Rental  ",
            artist=" Juice WRLD ",
            album=" Unreleased ",
            duration_ms=240000,
            spotify_local_uri=(
                "spotify:local:"
                "Juice+WRLD:"
                "Unreleased:"
                "Rental:240"
            ),
        )

        self.assertEqual(
            reference.title,
            "Rental",
        )

        self.assertEqual(
            reference.artist,
            "Juice WRLD",
        )

    def test_local_reference_requires_local_uri(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            LocalTrackReference(
                title="Rental",
                artist="Juice WRLD",
                album="Unreleased",
                duration_ms=240000,
                spotify_local_uri=(
                    "spotify:track:abc"
                ),
            )

    def test_candidate_requires_absolute_path(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            LocalTrackCandidate(
                title="Rental",
                artist="Juice WRLD",
                album="Unreleased",
                duration_ms=240000,
                local_path=(
                    "relative/Rental.mp3"
                ),
            )

    def test_models_are_frozen(
        self,
    ):
        reference = LocalTrackReference(
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

        with self.assertRaises(
            FrozenInstanceError
        ):
            reference.title = "Changed"


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
