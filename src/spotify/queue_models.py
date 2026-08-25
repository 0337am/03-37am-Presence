from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


QUEUE_ITEM_TRACK = "track"
QUEUE_ITEM_EPISODE = "episode"

_QUEUE_ITEM_TYPES = {
    QUEUE_ITEM_TRACK,
    QUEUE_ITEM_EPISODE,
}


def _required_text(
    value,
    field_name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "{} must be a string".format(
                field_name
            )
        )

    checked = value.strip()

    if not checked:
        raise ValueError(
            "{} cannot be empty".format(
                field_name
            )
        )

    return checked


def _optional_text(
    value,
    field_name: str,
) -> str:
    if value is None:
        return ""

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "{} must be a string".format(
                field_name
            )
        )

    return value.strip()


def _duration_ms(
    value,
) -> int | None:
    if value is None:
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
            "duration_ms must be an integer or None"
        )

    if value < 0:
        raise ValueError(
            "duration_ms cannot be negative"
        )

    return value


def _first_image_url(
    value,
) -> str:
    if value is None:
        return ""

    if not isinstance(
        value,
        list,
    ):
        raise TypeError(
            "images must be a list"
        )

    for image in value:
        if not isinstance(
            image,
            Mapping,
        ):
            continue

        url = image.get(
            "url"
        )

        if not isinstance(
            url,
            str,
        ):
            continue

        checked = url.strip()

        if checked:
            return checked

    return ""


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyQueueItem:
    item_type: str
    name: str
    uri: str

    creator: str = ""
    collection: str = ""
    artwork_url: str = ""

    is_local: bool = False
    duration_ms: int | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.item_type
            not in _QUEUE_ITEM_TYPES
        ):
            raise ValueError(
                "Unsupported Spotify queue item type."
            )

        object.__setattr__(
            self,
            "name",
            _required_text(
                self.name,
                "name",
            ),
        )

        object.__setattr__(
            self,
            "uri",
            _required_text(
                self.uri,
                "uri",
            ),
        )

        for field_name in (
            "creator",
            "collection",
            "artwork_url",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_text(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name,
                ),
            )

        if not isinstance(
            self.is_local,
            bool,
        ):
            raise TypeError(
                "is_local must be a boolean"
            )

        object.__setattr__(
            self,
            "duration_ms",
            _duration_ms(
                self.duration_ms
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyQueueSnapshot:
    currently_playing: (
        SpotifyQueueItem
        | None
    )

    items: tuple[
        SpotifyQueueItem,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        current = (
            self.currently_playing
        )

        if (
            current is not None
            and not isinstance(
                current,
                SpotifyQueueItem,
            )
        ):
            raise TypeError(
                (
                    "currently_playing must be "
                    "a SpotifyQueueItem or None"
                )
            )

        if not isinstance(
            self.items,
            tuple,
        ):
            object.__setattr__(
                self,
                "items",
                tuple(
                    self.items
                ),
            )

        for item in self.items:
            if not isinstance(
                item,
                SpotifyQueueItem,
            ):
                raise TypeError(
                    (
                        "queue items must be "
                        "SpotifyQueueItem instances"
                    )
                )


def spotify_queue_item_from_payload(
    payload: Mapping,
) -> SpotifyQueueItem:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise TypeError(
            "Spotify queue item must be an object."
        )

    item_type = _required_text(
        payload.get(
            "type"
        ),
        "type",
    ).lower()

    if (
        item_type
        not in _QUEUE_ITEM_TYPES
    ):
        raise ValueError(
            "Unsupported Spotify queue item type."
        )

    name = _required_text(
        payload.get(
            "name"
        ),
        "name",
    )

    uri = _required_text(
        payload.get(
            "uri"
        ),
        "uri",
    )

    is_local = payload.get(
        "is_local",
        False,
    )

    if not isinstance(
        is_local,
        bool,
    ):
        raise TypeError(
            "is_local must be a boolean"
        )

    duration = _duration_ms(
        payload.get(
            "duration_ms"
        )
    )

    creator = ""
    collection = ""
    artwork_url = ""

    if item_type == QUEUE_ITEM_TRACK:
        artists = payload.get(
            "artists",
            [],
        )

        if not isinstance(
            artists,
            list,
        ):
            raise TypeError(
                "track artists must be a list"
            )

        artist_names = []

        for artist in artists:
            if not isinstance(
                artist,
                Mapping,
            ):
                continue

            artist_name = artist.get(
                "name"
            )

            if not isinstance(
                artist_name,
                str,
            ):
                continue

            artist_name = (
                artist_name.strip()
            )

            if artist_name:
                artist_names.append(
                    artist_name
                )

        creator = ", ".join(
            artist_names
        )

        album = payload.get(
            "album"
        )

        if album is not None:
            if not isinstance(
                album,
                Mapping,
            ):
                raise TypeError(
                    "track album must be an object"
                )

            collection = _optional_text(
                album.get(
                    "name"
                ),
                "album name",
            )

            artwork_url = (
                _first_image_url(
                    album.get(
                        "images"
                    )
                )
            )

    else:
        show = payload.get(
            "show"
        )

        if show is not None:
            if not isinstance(
                show,
                Mapping,
            ):
                raise TypeError(
                    "episode show must be an object"
                )

            show_name = (
                _optional_text(
                    show.get(
                        "name"
                    ),
                    "show name",
                )
            )

            creator = show_name
            collection = show_name

        artwork_url = (
            _first_image_url(
                payload.get(
                    "images"
                )
            )
        )

        if (
            not artwork_url
            and isinstance(
                show,
                Mapping,
            )
        ):
            artwork_url = (
                _first_image_url(
                    show.get(
                        "images"
                    )
                )
            )

    return SpotifyQueueItem(
        item_type=item_type,
        name=name,
        uri=uri,
        creator=creator,
        collection=collection,
        artwork_url=artwork_url,
        is_local=is_local,
        duration_ms=duration,
    )


def spotify_queue_from_payload(
    payload: Mapping,
) -> SpotifyQueueSnapshot:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise TypeError(
            "Spotify queue response must be an object."
        )

    current_payload = payload.get(
        "currently_playing"
    )

    if current_payload is None:
        currently_playing = None
    else:
        currently_playing = (
            spotify_queue_item_from_payload(
                current_payload
            )
        )

    queue_payload = payload.get(
        "queue"
    )

    if not isinstance(
        queue_payload,
        list,
    ):
        raise TypeError(
            "Spotify queue response requires a queue list."
        )

    items = tuple(
        spotify_queue_item_from_payload(
            item
        )
        for item in queue_payload
    )

    return SpotifyQueueSnapshot(
        currently_playing=(
            currently_playing
        ),
        items=items,
    )
