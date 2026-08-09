from __future__ import annotations

import unittest

from src.music.artwork_cache_policy import (
    should_upgrade_artwork,
)


class ArtworkCachePolicyTests(
    unittest.TestCase
):
    def test_empty_cache_accepts_artwork(
        self,
    ):
        self.assertTrue(
            should_upgrade_artwork(
                0,
                100000,
            )
        )

    def test_large_upgrade_is_accepted(
        self,
    ):
        self.assertTrue(
            should_upgrade_artwork(
                7125,
                100773,
            )
        )

    def test_smaller_fallback_is_rejected(
        self,
    ):
        self.assertFalse(
            should_upgrade_artwork(
                100773,
                7125,
            )
        )

    def test_small_difference_is_rejected(
        self,
    ):
        self.assertFalse(
            should_upgrade_artwork(
                100000,
                104000,
            )
        )

    def test_similar_sized_candidate_is_rejected(
        self,
    ):
        self.assertFalse(
            should_upgrade_artwork(
                70000,
                90000,
            )
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
