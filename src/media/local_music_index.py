from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from src.media.local_music_metadata import (
    LocalMusicMetadataError,
    SUPPORTED_LOCAL_AUDIO_EXTENSIONS,
    read_local_track_candidate,
)
from src.media.unified_track import (
    LocalTrackCandidate,
)


class LocalMusicIndexError(
    Exception
):
    pass


def _is_network_path(
    path: Path,
) -> bool:
    text = str(
        path
    )

    return (
        text.startswith(
            "\\\\"
        )
        or text.startswith(
            "//"
        )
    )


def _path_key(
    path: Path,
) -> str:
    return os.path.normcase(
        os.path.abspath(
            str(
                path
            )
        )
    )


def _is_junction(
    path: Path,
) -> bool:
    checker = getattr(
        os.path,
        "isjunction",
        None,
    )

    if not callable(
        checker
    ):
        return False

    try:
        return bool(
            checker(
                path
            )
        )
    except OSError:
        return False


@dataclass(
    frozen=True,
    slots=True,
)
class LocalMusicScanResult:
    candidates: tuple[
        LocalTrackCandidate,
        ...,
    ]
    roots: tuple[
        str,
        ...,
    ]
    scanned_files: int
    indexed_files: int
    skipped_files: int
    limit_reached: bool

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.candidates,
            tuple,
        ):
            raise TypeError(
                "candidates must be a tuple"
            )

        for candidate in (
            self.candidates
        ):
            if not isinstance(
                candidate,
                LocalTrackCandidate,
            ):
                raise TypeError(
                    (
                        "candidates must contain "
                        "LocalTrackCandidate values"
                    )
                )

        if not isinstance(
            self.roots,
            tuple,
        ):
            raise TypeError(
                "roots must be a tuple"
            )

        for value in (
            self.scanned_files,
            self.indexed_files,
            self.skipped_files,
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
            ):
                raise TypeError(
                    (
                        "scan counts must "
                        "be integers"
                    )
                )

            if value < 0:
                raise ValueError(
                    (
                        "scan counts cannot "
                        "be negative"
                    )
                )

        if not isinstance(
            self.limit_reached,
            bool,
        ):
            raise TypeError(
                (
                    "limit_reached must "
                    "be a boolean"
                )
            )


class LocalMusicIndex:
    def __init__(
        self,
        *,
        metadata_reader=None,
        maximum_files: int = 50000,
    ) -> None:
        if (
            isinstance(
                maximum_files,
                bool,
            )
            or not isinstance(
                maximum_files,
                int,
            )
        ):
            raise TypeError(
                "maximum_files must be an integer"
            )

        if maximum_files < 1:
            raise ValueError(
                (
                    "maximum_files must "
                    "be at least 1"
                )
            )

        self.metadata_reader = (
            metadata_reader
            or read_local_track_candidate
        )

        if not callable(
            self.metadata_reader
        ):
            raise TypeError(
                (
                    "metadata_reader must "
                    "be callable"
                )
            )

        self.maximum_files = (
            maximum_files
        )

    @staticmethod
    def _checked_roots(
        folders,
    ) -> tuple[
        Path,
        ...,
    ]:
        if isinstance(
            folders,
            (
                str,
                bytes,
                Path,
            ),
        ):
            raise TypeError(
                (
                    "folders must be an "
                    "iterable of paths"
                )
            )

        try:
            values = tuple(
                folders
            )
        except TypeError as error:
            raise TypeError(
                (
                    "folders must be an "
                    "iterable of paths"
                )
            ) from error

        checked = []
        seen = set()

        for value in values:
            try:
                path = Path(
                    value
                )
            except (
                TypeError,
                ValueError,
            ) as error:
                raise LocalMusicIndexError(
                    (
                        "A local music folder "
                        "path is invalid."
                    )
                ) from error

            if not path.is_absolute():
                raise LocalMusicIndexError(
                    (
                        "Local music folders "
                        "must use absolute paths."
                    )
                )

            if _is_network_path(
                path
            ):
                raise LocalMusicIndexError(
                    (
                        "Network music folders "
                        "are not supported."
                    )
                )

            try:
                path = path.resolve(
                    strict=True
                )
            except OSError as error:
                raise LocalMusicIndexError(
                    (
                        "A local music folder "
                        "is unavailable."
                    )
                ) from error

            if not path.is_dir():
                raise LocalMusicIndexError(
                    (
                        "A local music folder "
                        "is not a directory."
                    )
                )

            if (
                path.is_symlink()
                or _is_junction(
                    path
                )
            ):
                raise LocalMusicIndexError(
                    (
                        "Linked local music "
                        "roots are not supported."
                    )
                )

            key = _path_key(
                path
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            checked.append(
                path
            )

        return tuple(
            checked
        )

    @staticmethod
    def _iter_audio_files(
        root: Path,
    ):
        root_resolved = (
            root.resolve()
        )

        for (
            current_root,
            directories,
            filenames,
        ) in os.walk(
            root,
            topdown=True,
            followlinks=False,
        ):
            current = Path(
                current_root
            )

            safe_directories = []

            for directory in sorted(
                directories,
                key=str.casefold,
            ):
                child = (
                    current
                    / directory
                )

                try:
                    if (
                        child.is_symlink()
                        or _is_junction(
                            child
                        )
                    ):
                        continue
                except OSError:
                    continue

                safe_directories.append(
                    directory
                )

            directories[:] = (
                safe_directories
            )

            for filename in sorted(
                filenames,
                key=str.casefold,
            ):
                path = (
                    current
                    / filename
                )

                if (
                    path.suffix.casefold()
                    not in
                    SUPPORTED_LOCAL_AUDIO_EXTENSIONS
                ):
                    continue

                try:
                    if path.is_symlink():
                        continue

                    resolved = path.resolve(
                        strict=True
                    )

                    resolved.relative_to(
                        root_resolved
                    )
                except (
                    OSError,
                    ValueError,
                ):
                    continue

                if not resolved.is_file():
                    continue

                yield resolved

    def scan(
        self,
        folders,
    ) -> LocalMusicScanResult:
        roots = self._checked_roots(
            folders
        )

        candidates = []
        seen_files = set()

        scanned_files = 0
        skipped_files = 0
        limit_reached = False

        for root in roots:
            for path in (
                self._iter_audio_files(
                    root
                )
            ):
                key = _path_key(
                    path
                )

                if key in seen_files:
                    continue

                if (
                    scanned_files
                    >= self.maximum_files
                ):
                    limit_reached = True
                    break

                seen_files.add(
                    key
                )

                scanned_files += 1

                try:
                    candidate = (
                        self.metadata_reader(
                            path
                        )
                    )
                except (
                    LocalMusicMetadataError,
                    OSError,
                ):
                    skipped_files += 1
                    continue

                if not isinstance(
                    candidate,
                    LocalTrackCandidate,
                ):
                    raise TypeError(
                        (
                            "metadata_reader must "
                            "return LocalTrackCandidate"
                        )
                    )

                candidates.append(
                    candidate
                )

            if limit_reached:
                break

        candidates.sort(
            key=lambda candidate: (
                candidate.artist.casefold(),
                candidate.album.casefold(),
                candidate.title.casefold(),
                os.path.normcase(
                    candidate.local_path
                ),
            )
        )

        return LocalMusicScanResult(
            candidates=tuple(
                candidates
            ),
            roots=tuple(
                str(
                    root
                )
                for root in roots
            ),
            scanned_files=(
                scanned_files
            ),
            indexed_files=len(
                candidates
            ),
            skipped_files=(
                skipped_files
            ),
            limit_reached=(
                limit_reached
            ),
        )
