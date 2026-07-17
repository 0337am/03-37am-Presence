from __future__ import annotations

import csv
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path


TRACK_SUMMARY_HEADERS = (
    "Title",
    "Artist",
    "Album",
    "Source",
    "First played",
    "Last played",
    "Play count",
    "Last status",
)

LISTENING_ACTIVITY_HEADERS = (
    "Played at",
    "Title",
    "Artist",
    "Album",
    "Source",
    "Status",
)


def normalise_csv_destination(
    destination: str | Path,
) -> Path:
    path = Path(destination)

    if path.suffix.lower() != ".csv":
        path = path.with_suffix(".csv")

    return path


def safe_csv_cell(value) -> str:
    text = (
        ""
        if value is None
        else str(value)
    )

    inspected = text.lstrip()

    if inspected.startswith(
        (
            "=",
            "+",
            "-",
            "@",
        )
    ):
        return "'" + text

    return text


def _write_csv(
    destination: str | Path,
    headers: tuple[str, ...],
    rows: Iterable[Iterable],
) -> tuple[Path, int]:
    final_path = normalise_csv_destination(
        destination
    )

    final_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=(
                f".{final_path.stem}-"
            ),
            suffix=".tmp",
            dir=final_path.parent,
        )
    )

    os.close(file_descriptor)

    temporary_path = Path(
        temporary_name
    )

    row_count = 0

    try:
        with temporary_path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            writer = csv.writer(
                csv_file
            )

            writer.writerow(
                headers
            )

            for row in rows:
                writer.writerow(
                    [
                        safe_csv_cell(value)
                        for value in row
                    ]
                )

                row_count += 1

        os.replace(
            temporary_path,
            final_path,
        )

    except Exception:
        temporary_path.unlink(
            missing_ok=True
        )

        raise

    return (
        final_path,
        row_count,
    )


def export_track_summary_csv(
    destination: str | Path,
    tracks,
) -> tuple[Path, int]:
    rows = (
        (
            track.title,
            track.artist,
            track.album,
            track.source_app,
            track.first_played,
            track.last_played,
            track.play_count,
            track.last_status,
        )
        for track in tracks
    )

    return _write_csv(
        destination,
        TRACK_SUMMARY_HEADERS,
        rows,
    )


def export_listening_activity_csv(
    destination: str | Path,
    events,
) -> tuple[Path, int]:
    rows = (
        (
            event.played_at,
            event.title,
            event.artist,
            event.album,
            event.source_app,
            event.status,
        )
        for event in events
        if str(
            event.status
            or ""
        ).strip().lower() == "playing"
    )

    return _write_csv(
        destination,
        LISTENING_ACTIVITY_HEADERS,
        rows,
    )
