from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.spotify.album_models import (
    SpotifyAlbumParseError,
    SpotifyAlbumSummary,
    spotify_album_summary_from_payload,
)


class SpotifyArtistParseError(ValueError):
    pass


def _mapping(
    value,
    label: str,
) -> Mapping:
    if not isinstance(value, Mapping):
        raise SpotifyArtistParseError(
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

    if not isinstance(value, str):
        raise SpotifyArtistParseError(
            label + " must be text."
        )

    checked = value.strip()

    if required and not checked:
        raise SpotifyArtistParseError(
            label + " is required."
        )

    return checked


def _integer(
    value,
    label: str,
    *,
    minimum: int = 0,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SpotifyArtistParseError(
            label + " must be an integer."
        )

    if value < minimum:
        raise SpotifyArtistParseError(
            label + " is out of range."
        )

    return value


def _spotify_url(
    payload: Mapping,
) -> str:
    raw_urls = payload.get("external_urls")

    if raw_urls is None:
        return ""

    urls = _mapping(
        raw_urls,
        "external_urls",
    )

    return _text(
        urls.get("spotify"),
        "Spotify URL",
    )


def _image_url(
    payload: Mapping,
) -> str:
    images = payload.get("images")

    if images is None:
        return ""

    if not isinstance(images, list):
        raise SpotifyArtistParseError(
            "images must be a list."
        )

    if not images:
        return ""

    image = _mapping(
        images[0],
        "artist image",
    )

    return _text(
        image.get("url"),
        "artist image URL",
    )


@dataclass(frozen=True)
class SpotifyArtistSummary:
    spotify_id: str
    name: str
    uri: str
    spotify_url: str = ""
    image_url: str = ""


@dataclass(frozen=True)
class SpotifyArtistAlbumsPage:
    items: tuple[
        SpotifyAlbumSummary,
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
            + len(self.items)
            >= self.total
        )


def spotify_artist_summary_from_payload(
    payload,
) -> SpotifyArtistSummary:
    artist = _mapping(
        payload,
        "artist",
    )

    spotify_id = _text(
        artist.get("id"),
        "artist id",
        required=True,
    )

    name = _text(
        artist.get("name"),
        "artist name",
        required=True,
    )

    uri = _text(
        artist.get("uri"),
        "artist URI",
        required=True,
    )

    expected_uri = (
        "spotify:artist:"
        + spotify_id
    )

    if uri != expected_uri:
        raise SpotifyArtistParseError(
            "artist URI does not match artist id."
        )

    raw_type = artist.get("type")

    if raw_type is not None:
        artist_type = _text(
            raw_type,
            "artist type",
            required=True,
        )

        if artist_type != "artist":
            raise SpotifyArtistParseError(
                "artist type is invalid."
            )

    return SpotifyArtistSummary(
        spotify_id=spotify_id,
        name=name,
        uri=uri,
        spotify_url=_spotify_url(
            artist
        ),
        image_url=_image_url(
            artist
        ),
    )


def spotify_artist_albums_page_from_payload(
    payload,
) -> SpotifyArtistAlbumsPage:
    page = _mapping(
        payload,
        "artist albums page",
    )

    raw_items = page.get("items")

    if not isinstance(raw_items, list):
        raise SpotifyArtistParseError(
            "artist album items must be a list."
        )

    items = []

    for raw_album in raw_items:
        try:
            album = (
                spotify_album_summary_from_payload(
                    raw_album
                )
            )

        except (
            SpotifyAlbumParseError,
            TypeError,
            ValueError,
        ) as error:
            raise SpotifyArtistParseError(
                "artist album item is invalid."
            ) from error

        items.append(album)

    limit = _integer(
        page.get("limit"),
        "artist album limit",
        minimum=0,
    )

    offset = _integer(
        page.get("offset"),
        "artist album offset",
        minimum=0,
    )

    total = _integer(
        page.get("total"),
        "artist album total",
        minimum=0,
    )

    if offset > total:
        raise SpotifyArtistParseError(
            "artist album offset exceeds total."
        )

    return SpotifyArtistAlbumsPage(
        items=tuple(items),
        limit=limit,
        offset=offset,
        total=total,
        next_url=_text(
            page.get("next"),
            "next URL",
        ),
        previous_url=_text(
            page.get("previous"),
            "previous URL",
        ),
    )