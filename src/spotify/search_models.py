from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SpotifySearchItemType(
    str,
    Enum,
):
    TRACK = "track"
    ALBUM = "album"
    ARTIST = "artist"
    PLAYLIST = "playlist"


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


def _checked_integer(
    value,
    field_name: str,
    *,
    minimum: int,
    maximum: int | None = None,
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
    ):
        raise TypeError(
            f"{field_name} must be an integer"
        )

    if value < minimum:
        raise ValueError(
            (
                f"{field_name} must be at least "
                f"{minimum}"
            )
        )

    if (
        maximum is not None
        and value > maximum
    ):
        raise ValueError(
            (
                f"{field_name} cannot exceed "
                f"{maximum}"
            )
        )

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifySearchItem:
    item_type: SpotifySearchItemType
    spotify_id: str
    name: str
    uri: str = ""
    spotify_url: str = ""
    image_url: str = ""
    subtitle: str = ""
    duration_ms: int | None = None
    explicit: bool | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.item_type,
            SpotifySearchItemType,
        ):
            raise TypeError(
                (
                    "item_type must be a "
                    "SpotifySearchItemType"
                )
            )

        object.__setattr__(
            self,
            "spotify_id",
            _checked_text(
                self.spotify_id,
                "spotify_id",
                required=True,
            ),
        )

        object.__setattr__(
            self,
            "name",
            _checked_text(
                self.name,
                "name",
                required=True,
            ),
        )

        for field_name in (
            "uri",
            "spotify_url",
            "image_url",
            "subtitle",
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

        if self.duration_ms is not None:
            _checked_integer(
                self.duration_ms,
                "duration_ms",
                minimum=0,
            )

        if (
            self.explicit is not None
            and not isinstance(
                self.explicit,
                bool,
            )
        ):
            raise TypeError(
                (
                    "explicit must be a boolean "
                    "or None"
                )
            )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifySearchPage:
    item_type: SpotifySearchItemType
    items: tuple[
        SpotifySearchItem,
        ...,
    ]
    limit: int
    offset: int
    total: int

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.item_type,
            SpotifySearchItemType,
        ):
            raise TypeError(
                (
                    "item_type must be a "
                    "SpotifySearchItemType"
                )
            )

        if not isinstance(
            self.items,
            tuple,
        ):
            raise TypeError(
                "items must be a tuple"
            )

        for item in self.items:
            if not isinstance(
                item,
                SpotifySearchItem,
            ):
                raise TypeError(
                    (
                        "items must contain "
                        "SpotifySearchItem values"
                    )
                )

            if (
                item.item_type
                is not self.item_type
            ):
                raise ValueError(
                    (
                        "search page items must match "
                        "the page item type"
                    )
                )

        _checked_integer(
            self.limit,
            "limit",
            minimum=0,
            maximum=10,
        )

        _checked_integer(
            self.offset,
            "offset",
            minimum=0,
            maximum=1000,
        )

        _checked_integer(
            self.total,
            "total",
            minimum=0,
        )

        if (
            self.limit > 0
            and len(
                self.items
            ) > self.limit
        ):
            raise ValueError(
                (
                    "search page contains more items "
                    "than its limit"
                )
            )

    @property
    def has_more(
        self,
    ) -> bool:
        if self.limit <= 0:
            return False

        return (
            self.offset
            + self.limit
            < self.total
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifySearchResults:
    query: str
    pages: tuple[
        SpotifySearchPage,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "query",
            _checked_text(
                self.query,
                "query",
                required=True,
            ),
        )

        if not isinstance(
            self.pages,
            tuple,
        ):
            raise TypeError(
                "pages must be a tuple"
            )

        seen = set()

        for page in self.pages:
            if not isinstance(
                page,
                SpotifySearchPage,
            ):
                raise TypeError(
                    (
                        "pages must contain "
                        "SpotifySearchPage values"
                    )
                )

            if page.item_type in seen:
                raise ValueError(
                    (
                        "search results cannot contain "
                        "duplicate page types"
                    )
                )

            seen.add(
                page.item_type
            )

    def page_for(
        self,
        item_type: SpotifySearchItemType,
    ) -> SpotifySearchPage | None:
        if not isinstance(
            item_type,
            SpotifySearchItemType,
        ):
            raise TypeError(
                (
                    "item_type must be a "
                    "SpotifySearchItemType"
                )
            )

        for page in self.pages:
            if page.item_type is item_type:
                return page

        return None

    def items_for(
        self,
        item_type: SpotifySearchItemType,
    ) -> tuple[
        SpotifySearchItem,
        ...,
    ]:
        page = self.page_for(
            item_type
        )

        if page is None:
            return ()

        return page.items

    @property
    def tracks(
        self,
    ) -> tuple[
        SpotifySearchItem,
        ...,
    ]:
        return self.items_for(
            SpotifySearchItemType.TRACK
        )

    @property
    def albums(
        self,
    ) -> tuple[
        SpotifySearchItem,
        ...,
    ]:
        return self.items_for(
            SpotifySearchItemType.ALBUM
        )

    @property
    def artists(
        self,
    ) -> tuple[
        SpotifySearchItem,
        ...,
    ]:
        return self.items_for(
            SpotifySearchItemType.ARTIST
        )

    @property
    def playlists(
        self,
    ) -> tuple[
        SpotifySearchItem,
        ...,
    ]:
        return self.items_for(
            SpotifySearchItemType.PLAYLIST
        )
