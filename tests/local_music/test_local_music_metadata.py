from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.media.local_music_metadata import (
    LocalMusicMetadataError,
    SUPPORTED_LOCAL_AUDIO_EXTENSIONS,
    read_local_track_candidate,
)
from tests.repo_paths import REPO_ROOT


class LocalMusicMetadataTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp.cleanup
        )

        self.root = Path(
            self.temp.name
        ).resolve()

    def audio_file(
        self,
        name="Rental.mp3",
    ):
        path = self.root / name

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.touch()

        return path

    @staticmethod
    def reader(
        *,
        title="Rental",
        artist="Juice WRLD",
        album="Unreleased",
        albumartist=None,
        duration=240.125,
    ):
        def read(
            _path,
            **_kwargs,
        ):
            return SimpleNamespace(
                title=title,
                artist=artist,
                album=album,
                albumartist=albumartist,
                duration=duration,
            )

        return read

    def test_core_formats_are_supported(
        self,
    ):
        for extension in (
            ".mp3",
            ".m4a",
            ".wav",
            ".ogg",
            ".opus",
            ".flac",
            ".wma",
            ".aiff",
        ):
            with self.subTest(
                extension=extension
            ):
                self.assertIn(
                    extension,
                    SUPPORTED_LOCAL_AUDIO_EXTENSIONS,
                )

    def test_relative_path_is_rejected(
        self,
    ):
        with self.assertRaises(
            LocalMusicMetadataError
        ):
            read_local_track_candidate(
                "Rental.mp3",
                tag_reader=self.reader(),
            )

    def test_missing_file_is_rejected(
        self,
    ):
        with self.assertRaises(
            LocalMusicMetadataError
        ):
            read_local_track_candidate(
                self.root
                / "missing.mp3",
                tag_reader=self.reader(),
            )

    def test_unsupported_extension_is_rejected(
        self,
    ):
        path = self.audio_file(
            "notes.txt"
        )

        with self.assertRaises(
            LocalMusicMetadataError
        ):
            read_local_track_candidate(
                path,
                tag_reader=self.reader(),
            )

    def test_metadata_becomes_candidate(
        self,
    ):
        path = self.audio_file()

        candidate = (
            read_local_track_candidate(
                path,
                tag_reader=self.reader(),
            )
        )

        self.assertEqual(
            candidate.title,
            "Rental",
        )

        self.assertEqual(
            candidate.artist,
            "Juice WRLD",
        )

        self.assertEqual(
            candidate.album,
            "Unreleased",
        )

        self.assertEqual(
            candidate.duration_ms,
            240125,
        )

        self.assertEqual(
            Path(
                candidate.local_path
            ),
            path,
        )

    def test_filename_is_title_fallback(
        self,
    ):
        path = self.audio_file(
            "Monsters In My Basement.mp3"
        )

        candidate = (
            read_local_track_candidate(
                path,
                tag_reader=self.reader(
                    title=None
                ),
            )
        )

        self.assertEqual(
            candidate.title,
            "Monsters In My Basement",
        )

    def test_albumartist_is_artist_fallback(
        self,
    ):
        path = self.audio_file()

        candidate = (
            read_local_track_candidate(
                path,
                tag_reader=self.reader(
                    artist=None,
                    albumartist="Juice WRLD",
                ),
            )
        )

        self.assertEqual(
            candidate.artist,
            "Juice WRLD",
        )

    def test_missing_duration_becomes_zero(
        self,
    ):
        path = self.audio_file()

        candidate = (
            read_local_track_candidate(
                path,
                tag_reader=self.reader(
                    duration=None
                ),
            )
        )

        self.assertEqual(
            candidate.duration_ms,
            0,
        )

    def test_nonfinite_duration_becomes_zero(
        self,
    ):
        path = self.audio_file()

        candidate = (
            read_local_track_candidate(
                path,
                tag_reader=self.reader(
                    duration=float("nan")
                ),
            )
        )

        self.assertEqual(
            candidate.duration_ms,
            0,
        )

    def test_tag_reader_receives_read_only_options(
        self,
    ):
        path = self.audio_file()

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

            return SimpleNamespace(
                title="Rental",
                artist="Juice WRLD",
                album="Unreleased",
                albumartist=None,
                duration=240.0,
            )

        read_local_track_candidate(
            path,
            tag_reader=reader,
        )

        self.assertEqual(
            len(
                calls
            ),
            1,
        )

        self.assertEqual(
            calls[0][1],
            {
                "tags": True,
                "duration": True,
                "image": False,
            },
        )

    def test_parser_exception_is_safe(
        self,
    ):
        path = self.audio_file()

        def broken(
            _filename,
            **_kwargs,
        ):
            raise ValueError(
                "simulated parser failure"
            )

        with self.assertRaises(
            LocalMusicMetadataError
        ) as raised:
            read_local_track_candidate(
                path,
                tag_reader=broken,
            )

        self.assertEqual(
            raised.exception.error_code,
            "metadata_read_failed",
        )


    class LocalMusicMetadataBoundaryTests(
        unittest.TestCase
    ):
        def test_metadata_module_is_read_only_and_local(
            self,
        ):
            root = (
                REPO_ROOT
            )

            source = (
                root
                / "src"
                / "media"
                / "local_music_metadata.py"
            ).read_text(
                encoding="utf-8"
            )

            for forbidden in (
                "PyQt",
                "SpotifyCredentialStore",
                "SpotifySessionManager",
                "SpotifyTokenClient",
                "access_token",
                "refresh_token",
                "client_secret",
                "urllib",
                "requests.",
                ".save(",
                ".delete(",
            ):
                with self.subTest(
                    forbidden=forbidden
                ):
                    self.assertNotIn(
                        forbidden,
                        source,
                    )

        def test_requirements_pin_tinytag(
            self,
        ):
            root = (
                REPO_ROOT
            )

            requirements = (
                root
                / "requirements.txt"
            ).read_text(
                encoding="utf-8"
            )

            self.assertIn(
                "tinytag==2.2.1",
                requirements,
            )


    if __name__ == "__main__":
        unittest.main(
            verbosity=2
        )
