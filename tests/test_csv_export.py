import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from src.library.csv_export import (
    LISTENING_ACTIVITY_HEADERS,
    TRACK_SUMMARY_HEADERS,
    _write_csv,
    export_listening_activity_csv,
    export_track_summary_csv,
    normalise_csv_destination,
    safe_csv_cell,
)


class CsvExportTests(unittest.TestCase):
    def test_destination_adds_csv_suffix(
        self,
    ):
        self.assertEqual(
            normalise_csv_destination(
                "library-export"
            ).suffix,
            ".csv",
        )

        self.assertEqual(
            normalise_csv_destination(
                "library-export.CSV"
            ).name,
            "library-export.CSV",
        )

    def test_formula_cells_are_protected(
        self,
    ):
        for value in (
            "=SUM(A1:A2)",
            "+1+1",
            "-10+20",
            "@command",
            "   =hidden",
        ):
            with self.subTest(value=value):
                protected = safe_csv_cell(
                    value
                )

                self.assertTrue(
                    protected.startswith("'")
                )

        self.assertEqual(
            safe_csv_cell("Normal title"),
            "Normal title",
        )

        self.assertEqual(
            safe_csv_cell(None),
            "",
        )

    def test_track_summary_writes_expected_csv(
        self,
    ):
        track = SimpleNamespace(
            title="Track",
            artist="Artist",
            album="Album",
            source_app="Spotify.exe",
            first_played="2026-07-16 10:00:00",
            last_played="2026-07-16 11:00:00",
            play_count=3,
            last_status="Playing",
        )

        with TemporaryDirectory() as directory:
            destination, count = (
                export_track_summary_csv(
                    Path(directory)
                    / "summary",
                    (track,),
                )
            )

            self.assertEqual(
                count,
                1,
            )

            self.assertTrue(
                destination.read_bytes().startswith(
                    b"\xef\xbb\xbf"
                )
            )

            with destination.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as csv_file:
                rows = list(
                    csv.reader(csv_file)
                )

        self.assertEqual(
            tuple(rows[0]),
            TRACK_SUMMARY_HEADERS,
        )

        self.assertEqual(
            rows[1],
            [
                "Track",
                "Artist",
                "Album",
                "Spotify.exe",
                "2026-07-16 10:00:00",
                "2026-07-16 11:00:00",
                "3",
                "Playing",
            ],
        )

    def test_track_export_creates_parent_folder(
        self,
    ):
        with TemporaryDirectory() as directory:
            destination = (
                Path(directory)
                / "nested"
                / "deeper"
                / "history.csv"
            )

            written_path, count = (
                export_track_summary_csv(
                    destination,
                    (),
                )
            )

            self.assertEqual(
                written_path,
                destination,
            )

            self.assertEqual(
                count,
                0,
            )

            self.assertTrue(
                destination.is_file()
            )

    def test_activity_export_keeps_only_playing(
        self,
    ):
        events = (
            SimpleNamespace(
                played_at="2026-07-16 12:00:00",
                title="Confirmed",
                artist="Artist",
                album="Album",
                source_app="Spotify.exe",
                status="Playing",
            ),
            SimpleNamespace(
                played_at="2026-07-16 12:01:00",
                title="Legacy pause",
                artist="Artist",
                album="Album",
                source_app="Spotify.exe",
                status="Paused",
            ),
            SimpleNamespace(
                played_at="2026-07-16 12:02:00",
                title="Lowercase status",
                artist="Artist",
                album="Album",
                source_app="Spotify.exe",
                status="playing",
            ),
        )

        with TemporaryDirectory() as directory:
            destination, count = (
                export_listening_activity_csv(
                    Path(directory)
                    / "activity.csv",
                    events,
                )
            )

            with destination.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as csv_file:
                rows = list(
                    csv.reader(csv_file)
                )

        self.assertEqual(
            count,
            2,
        )

        self.assertEqual(
            tuple(rows[0]),
            LISTENING_ACTIVITY_HEADERS,
        )

        self.assertEqual(
            [
                row[1]
                for row in rows[1:]
            ],
            [
                "Confirmed",
                "Lowercase status",
            ],
        )

    def test_empty_activity_export_has_header(
        self,
    ):
        with TemporaryDirectory() as directory:
            destination, count = (
                export_listening_activity_csv(
                    Path(directory)
                    / "empty.csv",
                    (),
                )
            )

            with destination.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as csv_file:
                rows = list(
                    csv.reader(csv_file)
                )

        self.assertEqual(
            count,
            0,
        )

        self.assertEqual(
            rows,
            [
                list(
                    LISTENING_ACTIVITY_HEADERS
                )
            ],
        )

    def test_failed_write_preserves_existing_file(
        self,
    ):
        def broken_rows():
            yield (
                "first",
                "row",
            )

            raise RuntimeError(
                "simulated export failure"
            )

        with TemporaryDirectory() as directory:
            destination = (
                Path(directory)
                / "existing.csv"
            )

            destination.write_text(
                "original contents",
                encoding="utf-8",
            )

            with self.assertRaises(
                RuntimeError
            ):
                _write_csv(
                    destination,
                    (
                        "Column A",
                        "Column B",
                    ),
                    broken_rows(),
                )

            self.assertEqual(
                destination.read_text(
                    encoding="utf-8"
                ),
                "original contents",
            )

            temporary_files = list(
                destination.parent.glob(
                    ".existing-*.tmp"
                )
            )

            self.assertEqual(
                temporary_files,
                [],
            )

    def test_successful_write_replaces_old_file(
        self,
    ):
        with TemporaryDirectory() as directory:
            destination = (
                Path(directory)
                / "replace.csv"
            )

            destination.write_text(
                "old contents",
                encoding="utf-8",
            )

            written_path, count = _write_csv(
                destination,
                ("Heading",),
                (
                    ("New value",),
                ),
            )

            self.assertEqual(
                written_path,
                destination,
            )

            self.assertEqual(
                count,
                1,
            )

            self.assertNotIn(
                "old contents",
                destination.read_text(
                    encoding="utf-8-sig"
                ),
            )


if __name__ == "__main__":
    unittest.main()
