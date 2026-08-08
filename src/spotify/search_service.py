from __future__ import annotations

from collections.abc import (
    Iterable,
    Mapping,
)
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlsplit

from src.spotify.search_models import (
    SpotifySearchItem,
    SpotifySearchItemType,
    SpotifySearchPage,
    SpotifySearchResults,
)
from src.spotify.session_manager import (
    SpotifySessionManagerError,
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiClient,
    SpotifyWebApiError,
)


DEFAULT_SPOTIFY_SEARCH_TYPES = (
    SpotifySearchItemType.TRACK,
    SpotifySearchItemType.ALBUM,
    SpotifySearchItemType.ARTIST,
    SpotifySearchItemType.PLAYLIST,
)

DEFAULT_SPOTIFY_SEARCH_LIMIT = 5
MAX_SPOTIFY_SEARCH_LIMIT = 10
MAX_SPOTIFY_SEARCH_OFFSET = 1000


class SpotifySearchServiceStatus(
    str,
    Enum,
):
    READY = "ready"
    DISCONNECTED = "disconnected"
    REAUTHORIZATION_REQUIRED = (
        "reauthorization_required"
    )
    ERROR = "error"


class SpotifySearchParseError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifySearchServiceResult:
    status: SpotifySearchServiceStatus
    results: SpotifySearchResults | None = None
    message: str = ""
    error_code: str = ""
    retry_after_seconds: int | None = None
    refreshed: bool = False

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            SpotifySearchServiceStatus,
        ):
            raise TypeError(
                (
                    "status must be a "
                    "SpotifySearchServiceStatus"
                )
            )

        if not isinstance(
            self.message,
            str,
        ):
            raise TypeError(
                "message must be a string"
            )

        if not isinstance(
            self.error_code,
            str,
        ):
            raise TypeError(
                "error_code must be a string"
            )

        if not isinstance(
            self.refreshed,
            bool,
        ):
            raise TypeError(
                "refreshed must be a boolean"
            )

        if (
            self.retry_after_seconds
            is not None
        ):
            if (
                isinstance(
                    self.retry_after_seconds,
                    bool,
                )
                or not isinstance(
                    self.retry_after_seconds,
                    int,
                )
            ):
                raise TypeError(
                    (
                        "retry_after_seconds must "
                        "be an integer or None"
                    )
                )

            if (
                self.retry_after_seconds
                < 0
            ):
                raise ValueError(
                    (
                        "retry_after_seconds cannot "
                        "be negative"
                    )
                )

        if (
            self.status
            is SpotifySearchServiceStatus.READY
        ):
            if not isinstance(
                self.results,
                SpotifySearchResults,
            ):
                raise ValueError(
                    (
                        "ready search result requires "
                        "SpotifySearchResults"
                    )
                )

            if self.error_code:
                raise ValueError(
                    (
                        "ready search result cannot "
                        "contain an error code"
                    )
                )

        elif self.results is not None:
            raise ValueError(
                (
                    "non-ready search result cannot "
                    "contain search results"
                )
            )

        if (
            self.status
            is SpotifySearchServiceStatus.ERROR
            and not self.error_code
        ):
            raise ValueError(
                (
                    "error search result requires "
                    "an error code"
                )
            )

    @property
    def ready(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifySearchServiceStatus.READY
        )

    @property
    def connected(
        self,
    ) -> bool:
        return self.status in {
            SpotifySearchServiceStatus.READY,
            SpotifySearchServiceStatus.ERROR,
        }

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifySearchServiceStatus
            .REAUTHORIZATION_REQUIRED
        )


def _contains_control_character(
    value: str,
) -> bool:
    return any(
        ord(character) < 32
        or ord(character) == 127
        for character in value
    )


def _validate_query(
    query: str,
) -> str:
    if not isinstance(
        query,
        str,
    ):
        raise TypeError(
            "Spotify search query must be a string"
        )

    checked = query.strip()

    if not checked:
        raise ValueError(
            "Spotify search query cannot be empty"
        )

    if _contains_control_character(
        checked
    ):
        raise ValueError(
            (
                "Spotify search query cannot "
                "contain control characters"
            )
        )

    return checked


def normalize_search_types(
    types: Iterable[
        SpotifySearchItemType | str
    ] | None,
) -> tuple[
    SpotifySearchItemType,
    ...,
]:
    if types is None:
        return DEFAULT_SPOTIFY_SEARCH_TYPES

    if isinstance(
        types,
        (
            str,
            bytes,
        ),
    ):
        raise TypeError(
            (
                "Spotify search types must be "
                "an iterable of item types"
            )
        )

    normalized = []
    seen = set()

    for raw_type in types:
        if isinstance(
            raw_type,
            SpotifySearchItemType,
        ):
            item_type = raw_type

        elif isinstance(
            raw_type,
            str,
        ):
            checked = (
                raw_type
                .strip()
                .casefold()
            )

            try:
                item_type = (
                    SpotifySearchItemType(
                        checked
                    )
                )

            except ValueError as error:
                raise ValueError(
                    (
                        "Unsupported Spotify "
                        "search item type."
                    )
                ) from error

        else:
            raise TypeError(
                (
                    "Spotify search item types "
                    "must be strings or "
                    "SpotifySearchItemType values"
                )
            )

        if item_type in seen:
            continue

        seen.add(
            item_type
        )

        normalized.append(
            item_type
        )

    if not normalized:
        raise ValueError(
            (
                "At least one Spotify search "
                "item type is required"
            )
        )

    return tuple(
        normalized
    )


def _validate_limit(
    limit: int,
) -> int:
    if (
        isinstance(
            limit,
            bool,
        )
        or not isinstance(
            limit,
            int,
        )
    ):
        raise TypeError(
            "Spotify search limit must be an integer"
        )

    if not 1 <= limit <= MAX_SPOTIFY_SEARCH_LIMIT:
        raise ValueError(
            (
                "Spotify search limit must be "
                "between 1 and 10"
            )
        )

    return limit


def _validate_offset(
    offset: int,
) -> int:
    if (
        isinstance(
            offset,
            bool,
        )
        or not isinstance(
            offset,
            int,
        )
    ):
        raise TypeError(
            "Spotify search offset must be an integer"
        )

    if (
        offset < 0
        or offset > MAX_SPOTIFY_SEARCH_OFFSET
    ):
        raise ValueError(
            (
                "Spotify search offset must be "
                "between 0 and 1000"
            )
        )

    return offset


def _validate_market(
    market: str | None,
) -> str:
    if market is None:
        return ""

    if not isinstance(
        market,
        str,
    ):
        raise TypeError(
            (
                "Spotify search market must be "
                "a string or None"
            )
        )

    checked = market.strip().upper()

    if not checked:
        return ""

    if (
        len(
            checked
        ) != 2
        or not checked.isascii()
        or not checked.isalpha()
    ):
        raise ValueError(
            (
                "Spotify search market must be "
                "a two-letter country code"
            )
        )

    return checked


def _required_mapping(
    value,
    field_name: str,
) -> Mapping:
    if not isinstance(
        value,
        Mapping,
    ):
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "must be an object."
            )
        )

    return value


def _required_list(
    value,
    field_name: str,
) -> list:
    if not isinstance(
        value,
        list,
    ):
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "must be an array."
            )
        )

    return value


def _required_text(
    value,
    field_name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "must be a string."
            )
        )

    checked = value.strip()

    if not checked:
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "cannot be empty."
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
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "must be a string when present."
            )
        )

    return value.strip()


def _required_nonnegative_integer(
    value,
    field_name: str,
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
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "must be an integer."
            )
        )

    if value < 0:
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "cannot be negative."
            )
        )

    return value


def _optional_nonnegative_integer(
    value,
    field_name: str,
) -> int | None:
    if value is None:
        return None

    return _required_nonnegative_integer(
        value,
        field_name,
    )


def _optional_boolean(
    value,
    field_name: str,
) -> bool | None:
    if value is None:
        return None

    if not isinstance(
        value,
        bool,
    ):
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "must be a boolean when present."
            )
        )

    return value


def _safe_https_url(
    value,
    field_name: str,
    *,
    spotify_page: bool = False,
) -> str:
    if value is None:
        return ""

    if not isinstance(
        value,
        str,
    ):
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "must be a URL string."
            )
        )

    checked = value.strip()

    if not checked:
        return ""

    if (
        _contains_control_character(
            checked
        )
        or any(
            character.isspace()
            for character in checked
        )
    ):
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "contains invalid URL characters."
            )
        )

    try:
        parts = urlsplit(
            checked
        )

    except ValueError as error:
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "contains an invalid URL."
            )
        ) from error

    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
    ):
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "contains an untrusted URL."
            )
        )

    if (
        spotify_page
        and parts.hostname.casefold()
        != "open.spotify.com"
    ):
        raise SpotifySearchParseError(
            (
                f"Spotify search {field_name} "
                "is not a Spotify page."
            )
        )

    return checked


def _spotify_external_url(
    payload: Mapping,
) -> str:
    external_urls = payload.get(
        "external_urls"
    )

    if external_urls is None:
        return ""

    external_urls = _required_mapping(
        external_urls,
        "external_urls",
    )

    return _safe_https_url(
        external_urls.get(
            "spotify"
        ),
        "external_urls.spotify",
        spotify_page=True,
    )


def _first_image_url(
    value,
) -> str:
    if value is None:
        return ""

    images = _required_list(
        value,
        "images",
    )

    for image in images:
        if image is None:
            continue

        image = _required_mapping(
            image,
            "image",
        )

        image_url = image.get(
            "url"
        )

        if image_url is None:
            continue

        return _safe_https_url(
            image_url,
            "image URL",
        )

    return ""


def _artist_names(
    value,
) -> str:
    if value is None:
        return ""

    artists = _required_list(
        value,
        "artists",
    )

    names = []

    for artist in artists:
        if artist is None:
            continue

        artist = _required_mapping(
            artist,
            "artist",
        )

        name = artist.get(
            "name"
        )

        if name is None:
            continue

        checked = _optional_text(
            name,
            "artist name",
        )

        if checked:
            names.append(
                checked
            )

    return ", ".join(
        names
    )


def _spotify_uri(
    payload: Mapping,
    item_type: SpotifySearchItemType,
) -> str:
    uri = _optional_text(
        payload.get(
            "uri"
        ),
        "uri",
    )

    if not uri:
        return ""

    required_prefix = (
        "spotify:"
        + item_type.value
        + ":"
    )

    if not uri.startswith(
        required_prefix
    ):
        raise SpotifySearchParseError(
            (
                "Spotify search item URI does "
                "not match its item type."
            )
        )

    return uri


def _track_item(
    payload: Mapping,
) -> SpotifySearchItem:
    album = payload.get(
        "album"
    )

    image_url = ""

    if album is not None:
        album = _required_mapping(
            album,
            "track album",
        )

        image_url = _first_image_url(
            album.get(
                "images"
            )
        )

    subtitle = _artist_names(
        payload.get(
            "artists"
        )
    )

    return SpotifySearchItem(
        item_type=(
            SpotifySearchItemType.TRACK
        ),
        spotify_id=_required_text(
            payload.get(
                "id"
            ),
            "track id",
        ),
        name=_required_text(
            payload.get(
                "name"
            ),
            "track name",
        ),
        uri=_spotify_uri(
            payload,
            SpotifySearchItemType.TRACK,
        ),
        spotify_url=(
            _spotify_external_url(
                payload
            )
        ),
        image_url=image_url,
        subtitle=(
            subtitle
            or "Track"
        ),
        duration_ms=(
            _optional_nonnegative_integer(
                payload.get(
                    "duration_ms"
                ),
                "track duration_ms",
            )
        ),
        explicit=(
            _optional_boolean(
                payload.get(
                    "explicit"
                ),
                "track explicit",
            )
        ),
    )


def _album_item(
    payload: Mapping,
) -> SpotifySearchItem:
    subtitle = _artist_names(
        payload.get(
            "artists"
        )
    )

    return SpotifySearchItem(
        item_type=(
            SpotifySearchItemType.ALBUM
        ),
        spotify_id=_required_text(
            payload.get(
                "id"
            ),
            "album id",
        ),
        name=_required_text(
            payload.get(
                "name"
            ),
            "album name",
        ),
        uri=_spotify_uri(
            payload,
            SpotifySearchItemType.ALBUM,
        ),
        spotify_url=(
            _spotify_external_url(
                payload
            )
        ),
        image_url=(
            _first_image_url(
                payload.get(
                    "images"
                )
            )
        ),
        subtitle=(
            subtitle
            or "Album"
        ),
    )


def _artist_item(
    payload: Mapping,
) -> SpotifySearchItem:
    return SpotifySearchItem(
        item_type=(
            SpotifySearchItemType.ARTIST
        ),
        spotify_id=_required_text(
            payload.get(
                "id"
            ),
            "artist id",
        ),
        name=_required_text(
            payload.get(
                "name"
            ),
            "artist name",
        ),
        uri=_spotify_uri(
            payload,
            SpotifySearchItemType.ARTIST,
        ),
        spotify_url=(
            _spotify_external_url(
                payload
            )
        ),
        image_url=(
            _first_image_url(
                payload.get(
                    "images"
                )
            )
        ),
        subtitle="Artist",
    )


def _playlist_item(
    payload: Mapping,
) -> SpotifySearchItem:
    subtitle = "Playlist"

    owner = payload.get(
        "owner"
    )

    if owner is not None:
        owner = _required_mapping(
            owner,
            "playlist owner",
        )

        display_name = (
            _optional_text(
                owner.get(
                    "display_name"
                ),
                (
                    "playlist owner "
                    "display_name"
                ),
            )
        )

        if display_name:
            subtitle = display_name

    return SpotifySearchItem(
        item_type=(
            SpotifySearchItemType.PLAYLIST
        ),
        spotify_id=_required_text(
            payload.get(
                "id"
            ),
            "playlist id",
        ),
        name=_required_text(
            payload.get(
                "name"
            ),
            "playlist name",
        ),
        uri=_spotify_uri(
            payload,
            SpotifySearchItemType.PLAYLIST,
        ),
        spotify_url=(
            _spotify_external_url(
                payload
            )
        ),
        image_url=(
            _first_image_url(
                payload.get(
                    "images"
                )
            )
        ),
        subtitle=subtitle,
    )


_ITEM_PARSERS = {
    SpotifySearchItemType.TRACK: (
        _track_item
    ),
    SpotifySearchItemType.ALBUM: (
        _album_item
    ),
    SpotifySearchItemType.ARTIST: (
        _artist_item
    ),
    SpotifySearchItemType.PLAYLIST: (
        _playlist_item
    ),
}

_PAGE_KEYS = {
    SpotifySearchItemType.TRACK: (
        "tracks"
    ),
    SpotifySearchItemType.ALBUM: (
        "albums"
    ),
    SpotifySearchItemType.ARTIST: (
        "artists"
    ),
    SpotifySearchItemType.PLAYLIST: (
        "playlists"
    ),
}


def _parse_page(
    payload,
    item_type: SpotifySearchItemType,
) -> SpotifySearchPage:
    page = _required_mapping(
        payload,
        (
            item_type.value
            + " page"
        ),
    )

    raw_items = _required_list(
        page.get(
            "items"
        ),
        (
            item_type.value
            + " items"
        ),
    )

    limit = _required_nonnegative_integer(
        page.get(
            "limit"
        ),
        (
            item_type.value
            + " limit"
        ),
    )

    if limit > MAX_SPOTIFY_SEARCH_LIMIT:
        raise SpotifySearchParseError(
            (
                "Spotify search response limit "
                "exceeded 10."
            )
        )

    offset = (
        _required_nonnegative_integer(
            page.get(
                "offset"
            ),
            (
                item_type.value
                + " offset"
            ),
        )
    )

    if (
        offset
        > MAX_SPOTIFY_SEARCH_OFFSET
    ):
        raise SpotifySearchParseError(
            (
                "Spotify search response offset "
                "exceeded 1000."
            )
        )

    total = _required_nonnegative_integer(
        page.get(
            "total"
        ),
        (
            item_type.value
            + " total"
        ),
    )

    parser = _ITEM_PARSERS[
        item_type
    ]

    items = []

    for raw_item in raw_items:
        if raw_item is None:
            continue

        item = parser(
            _required_mapping(
                raw_item,
                (
                    item_type.value
                    + " item"
                ),
            )
        )

        items.append(
            item
        )

    if (
        limit > 0
        and len(
            items
        ) > limit
    ):
        raise SpotifySearchParseError(
            (
                "Spotify search returned more "
                "items than its page limit."
            )
        )

    return SpotifySearchPage(
        item_type=item_type,
        items=tuple(
            items
        ),
        limit=limit,
        offset=offset,
        total=total,
    )


def spotify_search_results_from_payload(
    payload,
    *,
    query: str,
    types: Iterable[
        SpotifySearchItemType | str
    ],
) -> SpotifySearchResults:
    root = _required_mapping(
        payload,
        "response",
    )

    checked_query = _validate_query(
        query
    )

    checked_types = (
        normalize_search_types(
            types
        )
    )

    pages = []

    for item_type in checked_types:
        page_key = _PAGE_KEYS[
            item_type
        ]

        if page_key not in root:
            raise SpotifySearchParseError(
                (
                    "Spotify search response is "
                    f"missing {page_key}."
                )
            )

        pages.append(
            _parse_page(
                root[
                    page_key
                ],
                item_type,
            )
        )

    return SpotifySearchResults(
        query=checked_query,
        pages=tuple(
            pages
        ),
    )


class SpotifySearchService:
    def __init__(
        self,
        session_manager,
        *,
        api_client=None,
    ) -> None:
        resolve = getattr(
            session_manager,
            "resolve",
            None,
        )

        if not callable(
            resolve
        ):
            raise TypeError(
                (
                    "session_manager must provide "
                    "a callable resolve method"
                )
            )

        if api_client is None:
            api_client = (
                SpotifyWebApiClient()
            )

        get_json = getattr(
            api_client,
            "get_json",
            None,
        )

        if not callable(
            get_json
        ):
            raise TypeError(
                (
                    "api_client must provide a "
                    "callable get_json method"
                )
            )

        self._session_manager = (
            session_manager
        )

        self._api_client = (
            api_client
        )

    @staticmethod
    def _error(
        error_code: str,
        message: str,
        *,
        retry_after_seconds: int | None = None,
        refreshed: bool = False,
    ) -> SpotifySearchServiceResult:
        return SpotifySearchServiceResult(
            status=(
                SpotifySearchServiceStatus
                .ERROR
            ),
            message=message,
            error_code=error_code,
            retry_after_seconds=(
                retry_after_seconds
            ),
            refreshed=refreshed,
        )

    def search(
        self,
        query: str,
        *,
        types: Iterable[
            SpotifySearchItemType | str
        ] | None = None,
        limit: int = (
            DEFAULT_SPOTIFY_SEARCH_LIMIT
        ),
        offset: int = 0,
        market: str | None = None,
    ) -> SpotifySearchServiceResult:
        checked_query = (
            _validate_query(
                query
            )
        )

        checked_types = (
            normalize_search_types(
                types
            )
        )

        checked_limit = (
            _validate_limit(
                limit
            )
        )

        checked_offset = (
            _validate_offset(
                offset
            )
        )

        checked_market = (
            _validate_market(
                market
            )
        )

        try:
            session = (
                self._session_manager
                .resolve()
            )

        except SpotifySessionManagerError:
            return self._error(
                "session_error",
                (
                    "Spotify search could not "
                    "restore the saved session."
                ),
            )

        except Exception:
            return self._error(
                "session_error",
                (
                    "Spotify search could not "
                    "restore the saved session."
                ),
            )

        status = getattr(
            session,
            "status",
            None,
        )

        if (
            status
            is SpotifySessionStatus
            .DISCONNECTED
        ):
            return SpotifySearchServiceResult(
                status=(
                    SpotifySearchServiceStatus
                    .DISCONNECTED
                ),
                message=(
                    "Connect Spotify before "
                    "searching."
                ),
            )

        if (
            status
            is SpotifySessionStatus
            .REAUTHORIZATION_REQUIRED
        ):
            return SpotifySearchServiceResult(
                status=(
                    SpotifySearchServiceStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                message=(
                    "Reconnect Spotify before "
                    "searching."
                ),
            )

        ready_statuses = {
            SpotifySessionStatus.READY,
            SpotifySessionStatus.REFRESHED,
        }

        if status not in ready_statuses:
            return self._error(
                "invalid_session_state",
                (
                    "Spotify returned an unexpected "
                    "session state."
                ),
            )

        refreshed = (
            status
            is SpotifySessionStatus
            .REFRESHED
        )

        token = getattr(
            session,
            "token",
            None,
        )

        access_token = getattr(
            token,
            "access_token",
            None,
        )

        if (
            not isinstance(
                access_token,
                str,
            )
            or not access_token
        ):
            return self._error(
                "invalid_session",
                (
                    "Spotify search could not use "
                    "the saved session."
                ),
                refreshed=refreshed,
            )

        request_query = {
            "q": checked_query,
            "type": ",".join(
                item_type.value
                for item_type
                in checked_types
            ),
            "limit": checked_limit,
            "offset": checked_offset,
        }

        if checked_market:
            request_query[
                "market"
            ] = checked_market

        try:
            payload = (
                self._api_client
                .get_json(
                    access_token,
                    "/search",
                    query=request_query,
                )
            )

        except SpotifyWebApiError as error:
            error_code = str(
                getattr(
                    error,
                    "error_code",
                    "",
                )
                or "spotify_api_error"
            )

            if (
                error_code
                == "reauthorization_required"
            ):
                return SpotifySearchServiceResult(
                    status=(
                        SpotifySearchServiceStatus
                        .REAUTHORIZATION_REQUIRED
                    ),
                    message=(
                        "Reconnect Spotify before "
                        "searching."
                    ),
                    refreshed=refreshed,
                )

            retry_after = getattr(
                error,
                "retry_after_seconds",
                None,
            )

            if (
                isinstance(
                    retry_after,
                    bool,
                )
                or not isinstance(
                    retry_after,
                    int,
                )
            ):
                retry_after = None

            return self._error(
                error_code,
                (
                    "Spotify search could not "
                    "be completed."
                ),
                retry_after_seconds=(
                    retry_after
                ),
                refreshed=refreshed,
            )

        except Exception:
            return self._error(
                "spotify_api_error",
                (
                    "Spotify search could not "
                    "be completed."
                ),
                refreshed=refreshed,
            )

        try:
            results = (
                spotify_search_results_from_payload(
                    payload,
                    query=checked_query,
                    types=checked_types,
                )
            )

        except (
            SpotifySearchParseError,
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_response",
                (
                    "Spotify returned invalid "
                    "search data."
                ),
                refreshed=refreshed,
            )

        return SpotifySearchServiceResult(
            status=(
                SpotifySearchServiceStatus.READY
            ),
            results=results,
            message="Spotify search completed.",
            refreshed=refreshed,
        )
