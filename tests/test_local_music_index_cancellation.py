from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.media.local_music_index import (
    LocalMusicIndex,
    LocalMusicScanCancelled,
)
from src.media.unified_track import (
    LocalTrackCandidate,
)


class LocalMusicIndexCancellationTests(
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
        name,
    ):
        path = (
            self.root
            / name
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.touch()

        return path

    @staticmethod
    def candidate(
        path,
    ):
        return LocalTrackCandidate(
            title=path.stem,
            artist="Juice WRLD",
            album="Unreleased",
            duration_ms=180000,
            local_path=str(
                path.resolve()
            ),
        )

    def test_cancel_callback_must_be_callable(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            LocalMusicIndex(
                metadata_reader=(
                    self.candidate
                )
            ).scan(
                (
                    self.root,
                ),
                cancel_requested=True,
            )

    def test_cancel_before_scan_raises_cancelled(
        self,
    ):
        self.touch(
            "Rental.mp3"
        )

        with self.assertRaises(
            LocalMusicScanCancelled
        ):
            LocalMusicIndex(
                metadata_reader=(
                    self.candidate
                )
            ).scan(
                (
                    self.root,
                ),
                cancel_requested=(
                    lambda: True
                ),
            )

    def test_cancel_stops_between_files(
        self,
    ):
        self.touch(
            "One.mp3"
        )

        self.touch(
            "Two.mp3"
        )

        reads = []

        cancelled = {
            "value": False,
        }

        def reader(
            path,
        ):
            reads.append(
                path.name
            )

            cancelled[
                "value"
            ] = True

            return self.candidate(
                path
            )

        with self.assertRaises(
            LocalMusicScanCancelled
        ):
            LocalMusicIndex(
                metadata_reader=reader
            ).scan(
                (
                    self.root,
                ),
                cancel_requested=(
                    lambda: cancelled[
                        "value"
                    ]
                ),
            )

        self.assertEqual(
            len(
                reads
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
