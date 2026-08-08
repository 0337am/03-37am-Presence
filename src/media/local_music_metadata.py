from __future__ import annotations

import math
from pathlib import Path

from tinytag import (
    TinyTag,
    TinyTagException,
)

from src.media.unified_track import (
    LocalTrackCandidate,
)


SUPPORTED_LOCAL_AUDIO_EXTENSIONS = frozenset(
    {
        ".mp1",
        ".mp2",
        ".mp3",
        ".m4a",
        ".m4b",
        ".wav",
        ".ogg",
        ".oga",
        ".opus",
        ".spx",
        ".flac",
        ".wma",
        ".aif",
        ".aiff",
        ".aifc",
    }
)


class LocalMusicMetadataError(
    Exception
):
    def __init__(
        self,
        error_code: str,
        message: str,
    ) -> None:
        self.error_code = str(
            error_code
        ).strip()

        if not self.error_code:
            raise ValueError(
                "error_code cannot be empty"
            )

        super().__init__(
            str(
                message
            ).strip()
            or (
                "Local music metadata "
                "could not be read."
            )
        )


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


def _tag_text(
    value,
) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        str,
    ):
        return value.strip()

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        for item in value:
            if isinstance(
                item,
                str,
            ):
                checked = item.strip()

                if checked:
                    return checked

        return ""

    return str(
        value
    ).strip()


def _duration_ms(
    value,
) -> int:
    if value is None:
        return 0

    if isinstance(
        value,
        bool,
    ):
        return 0

    try:
        seconds = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0

    if (
        not math.isfinite(
            seconds
        )
        or seconds < 0
    ):
        return 0

    return max(
        0,
        int(
            round(
                seconds
                * 1000
            )
        ),
    )


def read_local_track_candidate(
    file_path,
    *,
    tag_reader=None,
) -> LocalTrackCandidate:
    try:
        path = Path(
            file_path
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise LocalMusicMetadataError(
            "invalid_path",
            (
                "The local music path "
                "is invalid."
            ),
        ) from error

    if not path.is_absolute():
        raise LocalMusicMetadataError(
            "relative_path",
            (
                "Local music files must "
                "use absolute paths."
            ),
        )

    if _is_network_path(
        path
    ):
        raise LocalMusicMetadataError(
            "network_path",
            (
                "Network music paths are "
                "not supported."
            ),
        )

    try:
        path = path.resolve(
            strict=True
        )
    except OSError as error:
        raise LocalMusicMetadataError(
            "file_missing",
            (
                "The local music file "
                "is unavailable."
            ),
        ) from error

    if not path.is_file():
        raise LocalMusicMetadataError(
            "not_file",
            (
                "The local music path "
                "is not a file."
            ),
        )

    extension = (
        path.suffix.casefold()
    )

    if (
        extension
        not in
        SUPPORTED_LOCAL_AUDIO_EXTENSIONS
    ):
        raise LocalMusicMetadataError(
            "unsupported_format",
            (
                "The local music format "
                "is not supported."
            ),
        )

    reader = (
        tag_reader
        or TinyTag.get
    )

    try:
        tag = reader(
            str(
                path
            ),
            tags=True,
            duration=True,
            image=False,
        )
    except (
        TinyTagException,
        OSError,
        ValueError,
    ) as error:
        raise LocalMusicMetadataError(
            "metadata_read_failed",
            (
                "The local music metadata "
                "could not be read."
            ),
        ) from error
    except Exception as error:
        raise LocalMusicMetadataError(
            "metadata_read_failed",
            (
                "The local music metadata "
                "could not be read."
            ),
        ) from error

    title = _tag_text(
        getattr(
            tag,
            "title",
            None,
        )
    )

    if not title:
        title = path.stem.strip()

    if not title:
        raise LocalMusicMetadataError(
            "missing_title",
            (
                "The local music file "
                "has no usable title."
            ),
        )

    artist = _tag_text(
        getattr(
            tag,
            "artist",
            None,
        )
    )

    if not artist:
        artist = _tag_text(
            getattr(
                tag,
                "albumartist",
                None,
            )
        )

    album = _tag_text(
        getattr(
            tag,
            "album",
            None,
        )
    )

    duration_ms = _duration_ms(
        getattr(
            tag,
            "duration",
            None,
        )
    )

    return LocalTrackCandidate(
        title=title,
        artist=artist,
        album=album,
        duration_ms=duration_ms,
        local_path=str(
            path
        ),
    )
