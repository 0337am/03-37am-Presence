from __future__ import annotations

import ntpath
import os
from dataclasses import dataclass
from enum import Enum


class UnifiedTrackSource(
    str,
    Enum,
):
    SPOTIFY = "spotify"
    LOCAL = "local"


def _checked_text(
    value,
    field_name: str,
    *,
    required: bool,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be a string"
        )

    checked = value.strip()

    if (
        required
        and not checked
    ):
        raise ValueError(
            f"{field_name} cannot be empty"
        )

    return checked


def _checked_duration(
    value,
    field_name: str,
    *,
    optional: bool,
) -> int | None:
    if (
        value is None
        and optional
    ):
        return None

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
            f"{field_name} must be an integer"
        )

    if value < 0:
        raise ValueError(
            f"{field_name} cannot be negative"
        )

    return value


def _is_absolute_path(
    value: str,
) -> bool:
    return bool(
        os.path.isabs(
            value
        )
        or ntpath.isabs(
            value
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class UnifiedTrack:
    title: str
    source: UnifiedTrackSource
    artist: str = ""
    album: str = ""
    duration_ms: int | None = None
    artwork_reference: str = ""
    spotify_id: str = ""
    spotify_uri: str = ""
    local_path: str = ""
    local_available: bool | None = None
    playable: bool = True

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "title",
            _checked_text(
                self.title,
                "title",
                required=True,
            ),
        )

        if not isinstance(
            self.source,
            UnifiedTrackSource,
        ):
            raise TypeError(
                (
                    "source must be a "
                    "UnifiedTrackSource"
                )
            )

        for field_name in (
            "artist",
            "album",
            "artwork_reference",
            "spotify_id",
            "spotify_uri",
            "local_path",
        ):
            object.__setattr__(
                self,
                field_name,
                _checked_text(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name,
                    required=False,
                ),
            )

        _checked_duration(
            self.duration_ms,
            "duration_ms",
            optional=True,
        )

        if not isinstance(
            self.playable,
            bool,
        ):
            raise TypeError(
                "playable must be a boolean"
            )

        if (
            self.local_available
            is not None
            and not isinstance(
                self.local_available,
                bool,
            )
        ):
            raise TypeError(
                (
                    "local_available must be "
                    "a boolean or None"
                )
            )

        if (
            self.source
            is UnifiedTrackSource.SPOTIFY
        ):
            if self.local_path:
                raise ValueError(
                    (
                        "Spotify catalogue tracks "
                        "cannot own a local path"
                    )
                )

            if (
                self.local_available
                is not None
            ):
                raise ValueError(
                    (
                        "Spotify catalogue tracks "
                        "cannot have local availability"
                    )
                )

            return

        if (
            self.local_available
            is None
        ):
            raise ValueError(
                (
                    "Local tracks must declare "
                    "local availability"
                )
            )

        if self.local_available:
            if not self.local_path:
                raise ValueError(
                    (
                        "Available local tracks "
                        "must provide local_path"
                    )
                )

            if not _is_absolute_path(
                self.local_path
            ):
                raise ValueError(
                    (
                        "local_path must be "
                        "absolute"
                    )
                )

        else:
            if self.local_path:
                raise ValueError(
                    (
                        "Unavailable local tracks "
                        "cannot expose a stale path"
                    )
                )

            if self.playable:
                raise ValueError(
                    (
                        "Unavailable local tracks "
                        "cannot be playable"
                    )
                )


@dataclass(
    frozen=True,
    slots=True,
)
class LocalTrackReference:
    title: str
    artist: str
    album: str
    duration_ms: int
    spotify_local_uri: str

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "title",
            _checked_text(
                self.title,
                "title",
                required=True,
            ),
        )

        object.__setattr__(
            self,
            "artist",
            _checked_text(
                self.artist,
                "artist",
                required=False,
            ),
        )

        object.__setattr__(
            self,
            "album",
            _checked_text(
                self.album,
                "album",
                required=False,
            ),
        )

        _checked_duration(
            self.duration_ms,
            "duration_ms",
            optional=False,
        )

        uri = _checked_text(
            self.spotify_local_uri,
            "spotify_local_uri",
            required=True,
        )

        if not uri.startswith(
            "spotify:local:"
        ):
            raise ValueError(
                (
                    "spotify_local_uri must use "
                    "the spotify:local: scheme"
                )
            )

        object.__setattr__(
            self,
            "spotify_local_uri",
            uri,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class LocalTrackCandidate:
    title: str
    artist: str
    album: str
    duration_ms: int
    local_path: str
    artwork_reference: str = ""

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "title",
            _checked_text(
                self.title,
                "title",
                required=True,
            ),
        )

        object.__setattr__(
            self,
            "artist",
            _checked_text(
                self.artist,
                "artist",
                required=False,
            ),
        )

        object.__setattr__(
            self,
            "album",
            _checked_text(
                self.album,
                "album",
                required=False,
            ),
        )

        _checked_duration(
            self.duration_ms,
            "duration_ms",
            optional=False,
        )

        local_path = _checked_text(
            self.local_path,
            "local_path",
            required=True,
        )

        if not _is_absolute_path(
            local_path
        ):
            raise ValueError(
                (
                    "local_path must be "
                    "absolute"
                )
            )

        object.__setattr__(
            self,
            "local_path",
            local_path,
        )

        object.__setattr__(
            self,
            "artwork_reference",
            _checked_text(
                self.artwork_reference,
                "artwork_reference",
                required=False,
            ),
        )
