from __future__ import annotations

import hashlib
import ntpath
import os
from pathlib import Path

from tinytag import (
    TinyTag,
    TinyTagException,
)


MAX_LOCAL_ARTWORK_BYTES = (
    8 * 1024 * 1024
)

SPOTIFY_ARTWORK_CACHE_SOURCE_APPS = (
    "spotify.exe",
    "spotify",
    (
        "spotifyab.spotifymusic_"
        "zpdnekdrzrea0!spotify"
    ),
)


def _is_absolute_path(
    value: str,
) -> bool:
    return bool(
        Path(value).is_absolute()
        or ntpath.isabs(value)
    )


def _is_network_path(
    value: str,
) -> bool:
    normalized = (
        str(value)
        .strip()
        .replace("/", "\\")
    )

    return normalized.startswith(
        "\\\\"
    )


def read_local_embedded_artwork(
    file_path,
    *,
    tag_reader=None,
    max_bytes: int = (
        MAX_LOCAL_ARTWORK_BYTES
    ),
) -> bytes | None:
    """
    Read embedded artwork from one trusted local
    music file.

    This helper is intentionally passive:
    - no network access
    - no persistent cache writes
    - no Qt objects
    - no playback interaction

    Missing, stale, unsupported, or malformed
    artwork safely returns None.
    """
    if (
        isinstance(
            max_bytes,
            bool,
        )
        or not isinstance(
            max_bytes,
            int,
        )
    ):
        raise TypeError(
            "max_bytes must be an integer"
        )

    if max_bytes <= 0:
        raise ValueError(
            "max_bytes must be positive"
        )

    if not isinstance(
        file_path,
        (
            str,
            Path,
        ),
    ):
        return None

    path_text = str(
        file_path
    ).strip()

    if not path_text:
        return None

    if not _is_absolute_path(
        path_text
    ):
        return None

    if _is_network_path(
        path_text
    ):
        return None

    try:
        path = Path(
            path_text
        ).resolve(
            strict=True
        )

    except (
        OSError,
        RuntimeError,
        ValueError,
    ):
        return None

    if not path.is_file():
        return None

    resolved_text = str(
        path
    )

    if _is_network_path(
        resolved_text
    ):
        return None

    reader = (
        tag_reader
        or TinyTag.get
    )

    if not callable(
        reader
    ):
        raise TypeError(
            "tag_reader must be callable"
        )

    try:
        tag = reader(
            resolved_text,
            tags=False,
            duration=False,
            image=True,
        )

    except (
        TinyTagException,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return None

    except Exception:
        return None

    images = getattr(
        tag,
        "images",
        None,
    )

    image = getattr(
        images,
        "any",
        None,
    )

    if image is None:
        return None

    data = getattr(
        image,
        "data",
        None,
    )

    if not isinstance(
        data,
        (
            bytes,
            bytearray,
            memoryview,
        ),
    ):
        return None

    artwork_bytes = bytes(
        data
    )

    if not artwork_bytes:
        return None

    if (
        len(
            artwork_bytes
        )
        > max_bytes
    ):
        return None

    return artwork_bytes
def artwork_cache_directory(
) -> Path:
    local_app_data = os.getenv(
        "LOCALAPPDATA",
        "",
    ).strip()

    if local_app_data:
        return (
            Path(
                local_app_data
            )
            / "0337am Presence"
            / "artwork_cache"
        )

    return (
        Path.home()
        / ".0337am-presence"
        / "artwork_cache"
    )


def artwork_cache_identity(
    title,
    artist,
    album,
    source_app,
) -> str:
    identity = "|".join(
        [
            str(
                title
                or ""
            )
            .strip()
            .lower(),

            str(
                artist
                or ""
            )
            .strip()
            .lower(),

            str(
                album
                or ""
            )
            .strip()
            .lower(),

            str(
                source_app
                or ""
            )
            .strip()
            .lower(),
        ]
    )

    return hashlib.sha256(
        identity.encode(
            "utf-8"
        )
    ).hexdigest()


def _cache_tag_text(
    value,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).strip()


def read_local_cached_artwork(
    file_path,
    *,
    tag_reader=None,
    cache_directory=None,
    source_apps=(
        SPOTIFY_ARTWORK_CACHE_SOURCE_APPS
    ),
    max_bytes: int = (
        MAX_LOCAL_ARTWORK_BYTES
    ),
) -> bytes | None:
    """
    Read artwork previously learned by
    03:37am Presence for an exact local
    Spotify track identity.

    Matching is deliberately strict:
    title + artist + album + source_app.
    """
    if (
        isinstance(
            max_bytes,
            bool,
        )
        or not isinstance(
            max_bytes,
            int,
        )
    ):
        raise TypeError(
            "max_bytes must be an integer"
        )

    if max_bytes <= 0:
        raise ValueError(
            "max_bytes must be positive"
        )

    if not isinstance(
        file_path,
        (
            str,
            Path,
        ),
    ):
        return None

    path_text = str(
        file_path
    ).strip()

    if not path_text:
        return None

    if not _is_absolute_path(
        path_text
    ):
        return None

    if _is_network_path(
        path_text
    ):
        return None

    try:
        path = Path(
            path_text
        ).resolve(
            strict=True
        )

    except (
        OSError,
        RuntimeError,
        ValueError,
    ):
        return None

    if not path.is_file():
        return None

    if _is_network_path(
        str(
            path
        )
    ):
        return None

    reader = (
        tag_reader
        or TinyTag.get
    )

    if not callable(
        reader
    ):
        raise TypeError(
            "tag_reader must be callable"
        )

    try:
        tag = reader(
            str(
                path
            ),
            tags=True,
            duration=False,
            image=False,
        )

    except (
        TinyTagException,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return None

    except Exception:
        return None

    title = _cache_tag_text(
        getattr(
            tag,
            "title",
            None,
        )
    )

    if not title:
        title = path.stem.strip()

    if not title:
        return None

    artist = _cache_tag_text(
        getattr(
            tag,
            "artist",
            None,
        )
    )

    if not artist:
        artist = _cache_tag_text(
            getattr(
                tag,
                "albumartist",
                None,
            )
        )

    album = _cache_tag_text(
        getattr(
            tag,
            "album",
            None,
        )
    )

    if isinstance(
        source_apps,
        (
            str,
            bytes,
        ),
    ):
        return None

    try:
        checked_source_apps = tuple(
            source_apps
        )

    except TypeError:
        return None

    try:
        directory = (
            Path(
                cache_directory
            )
            if cache_directory
            is not None
            else artwork_cache_directory()
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    try:
        if not directory.is_dir():
            return None

    except OSError:
        return None

    for source_app in (
        checked_source_apps
    ):
        if not isinstance(
            source_app,
            str,
        ):
            continue

        checked_source_app = (
            source_app.strip()
        )

        if not checked_source_app:
            continue

        key = artwork_cache_identity(
            title,
            artist,
            album,
            checked_source_app,
        )

        cache_path = (
            directory
            / f"{key}.img"
        )

        try:
            data = (
                cache_path.read_bytes()
            )

        except OSError:
            continue

        if not data:
            continue

        if len(data) > max_bytes:
            continue

        return bytes(
            data
        )

    return None


def read_local_artwork(
    file_path,
    *,
    tag_reader=None,
    cache_directory=None,
    max_bytes: int = (
        MAX_LOCAL_ARTWORK_BYTES
    ),
) -> bytes | None:
    """
    Return the best safe local artwork.

    Priority:
    1. Embedded file artwork.
    2. Exact 03:37am persistent cache match.
    3. None, leaving the UI fallback intact.
    """
    embedded = (
        read_local_embedded_artwork(
            file_path,
            tag_reader=(
                tag_reader
            ),
            max_bytes=(
                max_bytes
            ),
        )
    )

    if embedded is not None:
        return embedded

    return read_local_cached_artwork(
        file_path,
        tag_reader=(
            tag_reader
        ),
        cache_directory=(
            cache_directory
        ),
        max_bytes=(
            max_bytes
        ),
    )
