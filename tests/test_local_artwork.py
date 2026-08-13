from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.media.local_artwork import (
    MAX_LOCAL_ARTWORK_BYTES,
    read_local_embedded_artwork,
)


class _FakeImage:
    def __init__(
        self,
        data,
    ):
        self.data = data


class _FakeImages:
    def __init__(
        self,
        image,
    ):
        self.any = image


class _FakeTag:
    def __init__(
        self,
        image,
    ):
        self.images = (
            _FakeImages(
                image
            )
        )


class LocalArtworkTests(
    unittest.TestCase
):
    def make_file(
        self,
    ) -> Path:
        handle = (
            tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False,
            )
        )

        path = Path(
            handle.name
        )

        handle.write(
            b"audio"
        )
        handle.close()

        self.addCleanup(
            lambda:
                path.unlink(
                    missing_ok=True
                )
        )

        return path

    def test_reads_embedded_artwork_bytes(
        self,
    ):
        path = self.make_file()
        calls = []

        def reader(
            filename,
            **kwargs,
        ):
            calls.append(
                (
                    filename,
                    kwargs,
                )
            )

            return _FakeTag(
                _FakeImage(
                    b"image-data"
                )
            )

        result = (
            read_local_embedded_artwork(
                path,
                tag_reader=reader,
            )
        )

        self.assertEqual(
            result,
            b"image-data",
        )

        self.assertEqual(
            calls,
            [
                (
                    str(
                        path.resolve()
                    ),
                    {
                        "tags": False,
                        "duration": False,
                        "image": True,
                    },
                ),
            ],
        )

    def test_missing_image_returns_none(
        self,
    ):
        path = self.make_file()

        result = (
            read_local_embedded_artwork(
                path,
                tag_reader=(
                    lambda *args, **kwargs:
                        _FakeTag(
                            None
                        )
                ),
            )
        )

        self.assertIsNone(
            result
        )

    def test_empty_image_returns_none(
        self,
    ):
        path = self.make_file()

        result = (
            read_local_embedded_artwork(
                path,
                tag_reader=(
                    lambda *args, **kwargs:
                        _FakeTag(
                            _FakeImage(
                                b""
                            )
                        )
                ),
            )
        )

        self.assertIsNone(
            result
        )

    def test_invalid_image_data_returns_none(
        self,
    ):
        path = self.make_file()

        result = (
            read_local_embedded_artwork(
                path,
                tag_reader=(
                    lambda *args, **kwargs:
                        _FakeTag(
                            _FakeImage(
                                "not-bytes"
                            )
                        )
                ),
            )
        )

        self.assertIsNone(
            result
        )

    def test_bytearray_is_normalized(
        self,
    ):
        path = self.make_file()

        result = (
            read_local_embedded_artwork(
                path,
                tag_reader=(
                    lambda *args, **kwargs:
                        _FakeTag(
                            _FakeImage(
                                bytearray(
                                    b"art"
                                )
                            )
                        )
                ),
            )
        )

        self.assertEqual(
            result,
            b"art",
        )

        self.assertIsInstance(
            result,
            bytes,
        )

    def test_oversized_artwork_returns_none(
        self,
    ):
        path = self.make_file()

        result = (
            read_local_embedded_artwork(
                path,
                tag_reader=(
                    lambda *args, **kwargs:
                        _FakeTag(
                            _FakeImage(
                                b"12345"
                            )
                        )
                ),
                max_bytes=4,
            )
        )

        self.assertIsNone(
            result
        )

    def test_missing_file_is_safe(
        self,
    ):
        path = (
            Path(
                tempfile.gettempdir()
            )
            / "03-37am-missing-art.mp3"
        )

        path.unlink(
            missing_ok=True
        )

        called = False

        def reader(
            *args,
            **kwargs,
        ):
            nonlocal called
            called = True

        result = (
            read_local_embedded_artwork(
                path,
                tag_reader=reader,
            )
        )

        self.assertIsNone(
            result
        )

        self.assertFalse(
            called
        )

    def test_relative_path_is_rejected(
        self,
    ):
        called = False

        def reader(
            *args,
            **kwargs,
        ):
            nonlocal called
            called = True

        result = (
            read_local_embedded_artwork(
                "song.mp3",
                tag_reader=reader,
            )
        )

        self.assertIsNone(
            result
        )

        self.assertFalse(
            called
        )

    def test_network_path_is_rejected(
        self,
    ):
        called = False

        def reader(
            *args,
            **kwargs,
        ):
            nonlocal called
            called = True

        result = (
            read_local_embedded_artwork(
                r"\\server\music\song.mp3",
                tag_reader=reader,
            )
        )

        self.assertIsNone(
            result
        )

        self.assertFalse(
            called
        )

    def test_reader_failure_is_safe(
        self,
    ):
        path = self.make_file()

        def reader(
            *args,
            **kwargs,
        ):
            raise RuntimeError(
                "simulated read failure"
            )

        result = (
            read_local_embedded_artwork(
                path,
                tag_reader=reader,
            )
        )

        self.assertIsNone(
            result
        )

    def test_non_callable_reader_is_rejected(
        self,
    ):
        path = self.make_file()

        with self.assertRaises(
            TypeError
        ):
            read_local_embedded_artwork(
                path,
                tag_reader=object(),
            )

    def test_max_bytes_requires_integer(
        self,
    ):
        path = self.make_file()

        for value in (
            True,
            False,
            1.5,
            "1024",
            None,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    TypeError
                ):
                    read_local_embedded_artwork(
                        path,
                        max_bytes=value,
                    )

    def test_max_bytes_must_be_positive(
        self,
    ):
        path = self.make_file()

        for value in (
            0,
            -1,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    ValueError
                ):
                    read_local_embedded_artwork(
                        path,
                        max_bytes=value,
                    )

    def test_default_limit_is_bounded(
        self,
    ):
        self.assertEqual(
            MAX_LOCAL_ARTWORK_BYTES,
            8 * 1024 * 1024,
        )

    def test_source_uses_current_tinytag_image_api(
        self,
    ):
        source_path = (
            Path(__file__)
            .resolve()
            .parents[1]
            / "src"
            / "media"
            / "local_artwork.py"
        )

        source = (
            source_path.read_text(
                encoding="utf-8"
            )
        )

        self.assertIn(
            '"images"',
            source,
        )

        self.assertIn(
            '"any"',
            source,
        )

        self.assertIn(
            "image=True",
            source,
        )

        deprecated_call = (
            "get_"
            + "image("
        )

        self.assertNotIn(
            deprecated_call,
            source,
        )


if __name__ == "__main__":
    unittest.main()