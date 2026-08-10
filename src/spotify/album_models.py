from collections.abc import Mapping
from dataclasses import dataclass


class SpotifyAlbumParseError(
    ValueError
):
    pass


def _mapping(
    value,
    label: str,
) -> Mapping:
    if not isinstance(
        value,
        Mapping,
    ):
        raise SpotifyAlbumParseError(
            label + " must be an object."
        )

    return value


def _text(
    value,
    label: str,
    *,
    required: bool = False,
) -> str:
    if value is None:
        value = ""

    if not isinstance(
        value,
        str,
    ):
        raise SpotifyAlbumParseError(
            label + " must be text."
        )

    checked = value.strip()

    if required and not checked:
        raise SpotifyAlbumParseError(
            label + " is required."
        )

    return checked


def _integer(
    value,
    label: str,
    *,
    minimum: int = 0,
) -> int:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < minimum
    ):
        raise SpotifyAlbumParseError(
            label + " must be a valid integer."
        )

    return value


def _optional_boolean(
    value,
    label: str,
):
    if value is None:
        return None

    if not isinstance(
        value,
        bool,
    ):
        raise SpotifyAlbumParseError(
            label + " must be a boolean or null."
        )

    return value


def _artists_from_payload(
    value,
) -> tuple[str, ...]:
    if not isinstance(
        value,
        list,
    ):
        raise SpotifyAlbumParseError(
            "artists must be a list."
        )

    artists = []

    for raw_artist in value:
        artist = _mapping(
            raw_artist,
            "artist",
        )

        name = _text(
            artist.get(
                "name"
            ),
            "artist name",
            required=False,
        )

        if name:
            artists.append(
                name
            )

    return tuple(
        artists
    )


def _spotify_url(
    payload: Mapping,
) -> str:
    raw_urls = payload.get(
        "external_urls"
    )

    if raw_urls is None:
        return ""

    urls = _mapping(
        raw_urls,
        "external_urls",
    )

    return _text(
        urls.get(
            "spotify"
        ),
        "Spotify URL",
        required=False,
    )


def _image_url(
    payload: Mapping,
) -> str:
    images = payload.get(
        "images"
    )

    if images is None:
        return ""

    if not isinstance(
        images,
        list,
    ):
        raise SpotifyAlbumParseError(
            "images must be a list."
        )

    for raw_image in images:
        image = _mapping(
            raw_image,
            "image",
        )

        url = _text(
            image.get(
                "url"
            ),
            "image URL",
            required=False,
        )

        if url:
            return url

    return ""


@dataclass(
    frozen=True
)
class SpotifyAlbumSummary:
    spotify_id: str
    name: str
    uri: str
    artists: tuple[str, ...]
    total_tracks: int
    album_type: str = ""
    spotify_url: str = ""
    image_url: str = ""
    release_date: str = ""
    release_date_precision: str = ""

    @property
    def artist_text(
        self,
    ) -> str:
        return (
            ", ".join(
                self.artists
            )
            or "Unknown artist"
        )


@dataclass(
    frozen=True
)
class SpotifyAlbumTrack:
    spotify_id: str
    name: str
    uri: str
    artists: tuple[str, ...]
    duration_ms: int
    disc_number: int
    track_number: int
    spotify_url: str = ""
    explicit: bool = False
    is_playable: bool | None = None

    @property
    def artist_text(
        self,
    ) -> str:
        return (
            ", ".join(
                self.artists
            )
            or "Unknown artist"
        )


@dataclass(
    frozen=True
)
class SpotifyAlbumTracksPage:
    items: tuple[
        SpotifyAlbumTrack,
        ...
    ]
    limit: int
    offset: int
    total: int
    next_url: str = ""
    previous_url: str = ""

    @property
    def complete(
        self,
    ) -> bool:
        return (
            self.offset
            + self.limit
            >= self.total
        )


def spotify_album_summary_from_payload(
    payload,
) -> SpotifyAlbumSummary:
    album = _mapping(
        payload,
        "album",
    )

    spotify_id = _text(
        album.get(
            "id"
        ),
        "album id",
        required=True,
    )

    uri = _text(
        album.get(
            "uri"
        ),
        "album URI",
        required=True,
    )

    expected_uri = (
        "spotify:album:"
        + spotify_id
    )

    if uri != expected_uri:
        raise SpotifyAlbumParseError(
            "album URI does not match album id."
        )

    album_type = _text(
        album.get(
            "album_type"
        ),
        "album type",
        required=False,
    )

    if (
        album_type
        and album_type
        not in {
            "album",
            "single",
            "compilation",
        }
    ):
        raise SpotifyAlbumParseError(
            "album type is invalid."
        )

    release_precision = _text(
        album.get(
            "release_date_precision"
        ),
        "release date precision",
        required=False,
    )

    if (
        release_precision
        and release_precision
        not in {
            "year",
            "month",
            "day",
        }
    ):
        raise SpotifyAlbumParseError(
            "release date precision is invalid."
        )

    name = _text(
        album.get(
            "name"
        ),
        "album name",
        required=False,
    )

    if not name:
        name = "Unknown album"

    return SpotifyAlbumSummary(
        spotify_id=spotify_id,
        name=name,
        uri=uri,
        artists=(
            _artists_from_payload(
                album.get(
                    "artists"
                )
            )
        ),
        total_tracks=(
            _integer(
                album.get(
                    "total_tracks"
                ),
                "total tracks",
            )
        ),
        album_type=album_type,
        spotify_url=(
            _spotify_url(
                album
            )
        ),
        image_url=(
            _image_url(
                album
            )
        ),
        release_date=(
            _text(
                album.get(
                    "release_date"
                ),
                "release date",
                required=False,
            )
        ),
        release_date_precision=(
            release_precision
        ),
    )


def spotify_album_track_from_payload(
    payload,
) -> SpotifyAlbumTrack:
    track = _mapping(
        payload,
        "track",
    )

    spotify_id = _text(
        track.get(
            "id"
        ),
        "track id",
        required=True,
    )

    uri = _text(
        track.get(
            "uri"
        ),
        "track URI",
        required=True,
    )

    expected_uri = (
        "spotify:track:"
        + spotify_id
    )

    if uri != expected_uri:
        raise SpotifyAlbumParseError(
            "track URI does not match track id."
        )

    name = _text(
        track.get(
            "name"
        ),
        "track name",
        required=False,
    )

    if not name:
        name = "Unknown track"

    explicit = track.get(
        "explicit",
        False,
    )

    if not isinstance(
        explicit,
        bool,
    ):
        raise SpotifyAlbumParseError(
            "explicit must be a boolean."
        )

    return SpotifyAlbumTrack(
        spotify_id=spotify_id,
        name=name,
        uri=uri,
        artists=(
            _artists_from_payload(
                track.get(
                    "artists"
                )
            )
        ),
        duration_ms=(
            _integer(
                track.get(
                    "duration_ms"
                ),
                "duration_ms",
            )
        ),
        disc_number=(
            _integer(
                track.get(
                    "disc_number"
                ),
                "disc_number",
                minimum=1,
            )
        ),
        track_number=(
            _integer(
                track.get(
                    "track_number"
                ),
                "track_number",
                minimum=1,
            )
        ),
        spotify_url=(
            _spotify_url(
                track
            )
        ),
        explicit=explicit,
        is_playable=(
            _optional_boolean(
                track.get(
                    "is_playable"
                ),
                "is_playable",
            )
        ),
    )


def spotify_album_tracks_page_from_payload(
    payload,
) -> SpotifyAlbumTracksPage:
    page = _mapping(
        payload,
        "album tracks page",
    )

    raw_items = page.get(
        "items"
    )

    if not isinstance(
        raw_items,
        list,
    ):
        raise SpotifyAlbumParseError(
            "album track items must be a list."
        )

    items = tuple(
        spotify_album_track_from_payload(
            item
        )
        for item in raw_items
    )

    return SpotifyAlbumTracksPage(
        items=items,
        limit=(
            _integer(
                page.get(
                    "limit"
                ),
                "limit",
                minimum=1,
            )
        ),
        offset=(
            _integer(
                page.get(
                    "offset"
                ),
                "offset",
            )
        ),
        total=(
            _integer(
                page.get(
                    "total"
                ),
                "total",
            )
        ),
        next_url=(
            _text(
                page.get(
                    "next"
                ),
                "next URL",
                required=False,
            )
        ),
        previous_url=(
            _text(
                page.get(
                    "previous"
                ),
                "previous URL",
                required=False,
            )
        ),
    )
