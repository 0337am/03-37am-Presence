from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from enum import Enum

from src.media.unified_track import (
    LocalTrackCandidate,
    LocalTrackReference,
    UnifiedTrack,
    UnifiedTrackSource,
)


class LocalTrackResolutionStatus(
    str,
    Enum,
):
    MATCHED = "matched"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"


def normalize_track_text(
    value: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "value must be a string"
        )

    normalized = unicodedata.normalize(
        "NFKC",
        value,
    ).casefold()

    characters = []

    for character in normalized:
        if (
            character.isalnum()
            or character.isspace()
        ):
            characters.append(
                character
            )
        else:
            characters.append(
                " "
            )

    return " ".join(
        "".join(
            characters
        ).split()
    )


@dataclass(
    frozen=True,
    slots=True,
)
class LocalTrackResolution:
    status: LocalTrackResolutionStatus
    candidate: LocalTrackCandidate | None = None
    score: int | None = None
    considered_candidates: int = 0

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            LocalTrackResolutionStatus,
        ):
            raise TypeError(
                (
                    "status must be a "
                    "LocalTrackResolutionStatus"
                )
            )

        if (
            isinstance(
                self.considered_candidates,
                bool,
            )
            or not isinstance(
                self.considered_candidates,
                int,
            )
        ):
            raise TypeError(
                (
                    "considered_candidates "
                    "must be an integer"
                )
            )

        if self.considered_candidates < 0:
            raise ValueError(
                (
                    "considered_candidates "
                    "cannot be negative"
                )
            )

        if (
            self.score is not None
            and (
                isinstance(
                    self.score,
                    bool,
                )
                or not isinstance(
                    self.score,
                    int,
                )
            )
        ):
            raise TypeError(
                (
                    "score must be an integer "
                    "or None"
                )
            )

        if (
            self.status
            is LocalTrackResolutionStatus.MATCHED
        ):
            if not isinstance(
                self.candidate,
                LocalTrackCandidate,
            ):
                raise ValueError(
                    (
                        "Matched resolutions require "
                        "a candidate"
                    )
                )

            if self.score is None:
                raise ValueError(
                    (
                        "Matched resolutions require "
                        "a score"
                    )
                )

            return

        if self.candidate is not None:
            raise ValueError(
                (
                    "Unmatched resolutions cannot "
                    "expose a candidate"
                )
            )

        if self.score is not None:
            raise ValueError(
                (
                    "Unmatched resolutions cannot "
                    "expose a score"
                )
            )

    def as_unified_track(
        self,
        reference: LocalTrackReference,
    ) -> UnifiedTrack:
        if not isinstance(
            reference,
            LocalTrackReference,
        ):
            raise TypeError(
                (
                    "reference must be a "
                    "LocalTrackReference"
                )
            )

        if (
            self.status
            is LocalTrackResolutionStatus.MATCHED
        ):
            candidate = self.candidate

            if candidate is None:
                raise RuntimeError(
                    "Matched candidate disappeared"
                )

            return UnifiedTrack(
                title=reference.title,
                source=UnifiedTrackSource.LOCAL,
                artist=reference.artist,
                album=reference.album,
                duration_ms=reference.duration_ms,
                artwork_reference=(
                    candidate.artwork_reference
                ),
                spotify_uri=(
                    reference.spotify_local_uri
                ),
                local_path=(
                    candidate.local_path
                ),
                local_available=True,
                playable=True,
            )

        return UnifiedTrack(
            title=reference.title,
            source=UnifiedTrackSource.LOCAL,
            artist=reference.artist,
            album=reference.album,
            duration_ms=reference.duration_ms,
            spotify_uri=(
                reference.spotify_local_uri
            ),
            local_available=False,
            playable=False,
        )


class LocalTrackResolver:
    def __init__(
        self,
        *,
        maximum_duration_delta_ms: int = 10000,
        ambiguity_margin: int = 4,
    ) -> None:
        for (
            value,
            field_name,
        ) in (
            (
                maximum_duration_delta_ms,
                "maximum_duration_delta_ms",
            ),
            (
                ambiguity_margin,
                "ambiguity_margin",
            ),
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
                        field_name
                        + " must be an integer"
                    )
                )

            if value < 0:
                raise ValueError(
                    (
                        field_name
                        + " cannot be negative"
                    )
                )

        self.maximum_duration_delta_ms = (
            maximum_duration_delta_ms
        )

        self.ambiguity_margin = (
            ambiguity_margin
        )

    def _candidate_score(
        self,
        reference: LocalTrackReference,
        candidate: LocalTrackCandidate,
    ) -> int | None:
        reference_title = normalize_track_text(
            reference.title
        )

        candidate_title = normalize_track_text(
            candidate.title
        )

        if (
            not reference_title
            or reference_title
            != candidate_title
        ):
            return None

        score = 50

        reference_artist = normalize_track_text(
            reference.artist
        )

        candidate_artist = normalize_track_text(
            candidate.artist
        )

        if reference_artist:
            if (
                reference_artist
                != candidate_artist
            ):
                return None

            score += 30

        duration_delta = abs(
            reference.duration_ms
            - candidate.duration_ms
        )

        if (
            duration_delta
            > self.maximum_duration_delta_ms
        ):
            return None

        if duration_delta <= 1000:
            score += 20
        elif duration_delta <= 3000:
            score += 15
        elif duration_delta <= 5000:
            score += 10
        else:
            score += 5

        reference_album = normalize_track_text(
            reference.album
        )

        candidate_album = normalize_track_text(
            candidate.album
        )

        if (
            reference_album
            and reference_album
            == candidate_album
        ):
            score += 10

        return score

    def resolve(
        self,
        reference: LocalTrackReference,
        candidates,
    ) -> LocalTrackResolution:
        if not isinstance(
            reference,
            LocalTrackReference,
        ):
            raise TypeError(
                (
                    "reference must be a "
                    "LocalTrackReference"
                )
            )

        checked_candidates = tuple(
            candidates
        )

        unique_candidates = {}

        for candidate in checked_candidates:
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

            path_key = os.path.normcase(
                os.path.abspath(
                    candidate.local_path
                )
            )

            unique_candidates.setdefault(
                path_key,
                candidate,
            )

        scored = []

        considered = 0

        for candidate in (
            unique_candidates.values()
        ):
            if not os.path.isfile(
                candidate.local_path
            ):
                continue

            considered += 1

            score = self._candidate_score(
                reference,
                candidate,
            )

            if score is None:
                continue

            scored.append(
                (
                    score,
                    candidate,
                )
            )

        if not scored:
            return LocalTrackResolution(
                status=(
                    LocalTrackResolutionStatus
                    .NOT_FOUND
                ),
                considered_candidates=(
                    considered
                ),
            )

        scored.sort(
            key=lambda entry: (
                -entry[0],
                os.path.normcase(
                    entry[1].local_path
                ),
            )
        )

        best_score, best_candidate = (
            scored[0]
        )

        if len(
            scored
        ) > 1:
            second_score = scored[
                1
            ][0]

            if (
                best_score
                - second_score
                <= self.ambiguity_margin
            ):
                return LocalTrackResolution(
                    status=(
                        LocalTrackResolutionStatus
                        .AMBIGUOUS
                    ),
                    considered_candidates=(
                        considered
                    ),
                )

        return LocalTrackResolution(
            status=(
                LocalTrackResolutionStatus
                .MATCHED
            ),
            candidate=best_candidate,
            score=best_score,
            considered_candidates=(
                considered
            ),
        )
