from __future__ import annotations

import asyncio
import unittest

from src.music.windows_media import (
    WindowsMedia,
)


class FakeThumbnail:
    def __init__(
        self,
    ):
        self.open_count = 0

    async def open_read_async(
        self,
    ):
        self.open_count += 1
        return object()


class FakeMedia:
    def __init__(
        self,
    ):
        self.thumbnail = (
            FakeThumbnail()
        )


class WindowsMediaArtworkRefreshTests(
    unittest.TestCase
):
    def make_engine(
        self,
        payloads,
    ):
        engine = object.__new__(
            WindowsMedia
        )

        engine._artwork_cache = {}
        engine._artwork_cache_checked_at = {}
        engine._last_artwork_key = ""

        engine.ARTWORK_RECHECK_SECONDS = (
            0.0
        )

        remaining = list(
            payloads
        )

        async def read_stream(
            _stream,
        ):
            if not remaining:
                return None

            return remaining.pop(
                0
            )

        engine._read_stream_bytes = (
            read_stream
        )

        return engine

    def read_artwork(
        self,
        engine,
        media,
    ):
        return asyncio.run(
            engine._get_artwork_bytes(
                media,
                "Toxic Humans "
                "(Session Edit)",
                "Juice WRLD",
                "Studio Sessions",
            )
        )

    def test_larger_real_artwork_repairs_cached_fallback(
        self,
    ):
        fallback = b"f" * 7125
        real_artwork = b"r" * 100773

        engine = self.make_engine(
            [
                fallback,
                real_artwork,
            ]
        )

        media = FakeMedia()

        first = self.read_artwork(
            engine,
            media,
        )

        second = self.read_artwork(
            engine,
            media,
        )

        self.assertEqual(
            first,
            fallback,
        )

        self.assertEqual(
            second,
            real_artwork,
        )

    def test_smaller_fallback_does_not_replace_good_artwork(
        self,
    ):
        real_artwork = b"r" * 100773
        fallback = b"f" * 7125

        engine = self.make_engine(
            [
                real_artwork,
                fallback,
            ]
        )

        media = FakeMedia()

        first = self.read_artwork(
            engine,
            media,
        )

        second = self.read_artwork(
            engine,
            media,
        )

        self.assertEqual(
            first,
            real_artwork,
        )

        self.assertEqual(
            second,
            real_artwork,
        )

    def test_missing_current_thumbnail_keeps_cached_artwork(
        self,
    ):
        engine = self.make_engine(
            []
        )

        key = (
            "toxic humans "
            "(session edit)"
            "|juice wrld"
            "|studio sessions"
        )

        cached = b"c" * 100773

        engine._artwork_cache[
            key
        ] = cached

        media = FakeMedia()
        media.thumbnail = None

        result = self.read_artwork(
            engine,
            media,
        )

        self.assertEqual(
            result,
            cached,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
