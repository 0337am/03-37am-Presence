from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.media.local_music_index import (
    LocalMusicIndex,
    LocalMusicIndexError,
)
from src.media.local_music_metadata import (
    LocalMusicMetadataError,
)
from src.media.unified_track import (
    LocalTrackCandidate,
)
from tests.repo_paths import REPO_ROOT


class LocalMusicIndexTests(
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

    def touch(
        self,
        relative,
    ):
        path = (
            self.root
            / relative
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.touch()

        return path

    @staticmethod
    def metadata_reader(
        path,
    ):
        return LocalTrackCandidate(
            title=path.stem,
            artist="Juice WRLD",
            album="Unreleased",
            duration_ms=240000,
            local_path=str(
                path.resolve()
            ),
        )

    def test_scans_selected_folder_recursively(
        self,
    ):
        self.touch(
            "Rental.mp3"
        )

        self.touch(
            "Deep/Monsters.flac"
        )

        result = LocalMusicIndex(
            metadata_reader=(
                self.metadata_reader
            )
        ).scan(
            (
                self.root,
            )
        )

        self.assertEqual(
            result.indexed_files,
            2,
        )

        self.assertEqual(
            result.scanned_files,
            2,
        )

    def test_unsupported_files_are_ignored(
        self,
    ):
        self.touch(
            "Rental.mp3"
        )

        self.touch(
            "notes.txt"
        )

        result = LocalMusicIndex(
            metadata_reader=(
                self.metadata_reader
            )
        ).scan(
            (
                self.root,
            )
        )

        self.assertEqual(
            result.indexed_files,
            1,
        )

    def test_empty_folder_is_safe(
        self,
    ):
        result = LocalMusicIndex(
            metadata_reader=(
                self.metadata_reader
            )
        ).scan(
            (
                self.root,
            )
        )

        self.assertEqual(
            result.indexed_files,
            0,
        )

        self.assertFalse(
            result.limit_reached
        )

    def test_no_folders_is_safe(
        self,
    ):
        result = LocalMusicIndex(
            metadata_reader=(
                self.metadata_reader
            )
        ).scan(
            ()
        )

        self.assertEqual(
            result.roots,
            (),
        )

        self.assertEqual(
            result.candidates,
            (),
        )

    def test_relative_folder_is_rejected(
        self,
    ):
        with self.assertRaises(
            LocalMusicIndexError
        ):
            LocalMusicIndex(
                metadata_reader=(
                    self.metadata_reader
                )
            ).scan(
                (
                    Path("Music"),
                )
            )

    def test_missing_folder_is_rejected(
        self,
    ):
        with self.assertRaises(
            LocalMusicIndexError
        ):
            LocalMusicIndex(
                metadata_reader=(
                    self.metadata_reader
                )
            ).scan(
                (
                    self.root
                    / "missing",
                )
            )

    def test_duplicate_root_is_deduplicated(
        self,
    ):
        self.touch(
            "Rental.mp3"
        )

        result = LocalMusicIndex(
            metadata_reader=(
                self.metadata_reader
            )
        ).scan(
            (
                self.root,
                self.root,
            )
        )

        self.assertEqual(
            len(
                result.roots
            ),
            1,
        )

        self.assertEqual(
            result.indexed_files,
            1,
        )

    def test_overlapping_roots_do_not_duplicate_files(
        self,
    ):
        child = (
            self.root
            / "Juice WRLD"
        )

        child.mkdir()

        self.touch(
            "Juice WRLD/Rental.mp3"
        )

        result = LocalMusicIndex(
            metadata_reader=(
                self.metadata_reader
            )
        ).scan(
            (
                self.root,
                child,
            )
        )

        self.assertEqual(
            result.indexed_files,
            1,
        )

    def test_bad_metadata_skips_only_bad_file(
        self,
    ):
        good = self.touch(
            "Good.mp3"
        )

        self.touch(
            "Broken.mp3"
        )

        def reader(
            path,
        ):
            if path.name == "Broken.mp3":
                raise LocalMusicMetadataError(
                    "metadata_read_failed",
                    "bad metadata",
                )

            return self.metadata_reader(
                path
            )

        result = LocalMusicIndex(
            metadata_reader=reader
        ).scan(
            (
                self.root,
            )
        )

        self.assertEqual(
            result.indexed_files,
            1,
        )

        self.assertEqual(
            result.skipped_files,
            1,
        )

        self.assertEqual(
            Path(
                result.candidates[
                    0
                ].local_path
            ),
            good,
        )

    def test_file_limit_is_enforced(
        self,
    ):
        self.touch(
            "One.mp3"
        )

        self.touch(
            "Two.mp3"
        )

        result = LocalMusicIndex(
            metadata_reader=(
                self.metadata_reader
            ),
            maximum_files=1,
        ).scan(
            (
                self.root,
            )
        )

        self.assertEqual(
            result.scanned_files,
            1,
        )

        self.assertTrue(
            result.limit_reached
        )

    def test_results_are_sorted_deterministically(
        self,
    ):
        self.touch(
            "Zebra.mp3"
        )

        self.touch(
            "Alpha.mp3"
        )

        result = LocalMusicIndex(
            metadata_reader=(
                self.metadata_reader
            )
        ).scan(
            (
                self.root,
            )
        )

        self.assertEqual(
            [
                candidate.title
                for candidate
                in result.candidates
            ],
            [
                "Alpha",
                "Zebra",
            ],
        )

    def test_constructor_validates_limit(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            LocalMusicIndex(
                maximum_files=0
            )

        with self.assertRaises(
            TypeError
        ):
            LocalMusicIndex(
                maximum_files=True
            )

    def test_reader_must_return_candidate(
        self,
    ):
        self.touch(
            "Rental.mp3"
        )

        with self.assertRaises(
            TypeError
        ):
            LocalMusicIndex(
                metadata_reader=(
                    lambda _path: object()
                )
            ).scan(
                (
                    self.root,
                )
            )


    class LocalMusicIndexBoundaryTests(
        unittest.TestCase
    ):
        def test_index_owns_no_ui_spotify_or_network(
            self,
        ):
            root = (
                REPO_ROOT
            )

            source = (
                root
                / "src"
                / "media"
                / "local_music_index.py"
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
                "QSettings",
            ):
                with self.subTest(
                    forbidden=forbidden
                ):
                    self.assertNotIn(
                        forbidden,
                        source,
                    )


    if __name__ == "__main__":
        unittest.main(
            verbosity=2
        )
