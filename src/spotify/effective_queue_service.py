from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import math
import time
from urllib.parse import unquote_plus

from src.spotify.queue_models import (
    QUEUE_ITEM_TRACK,
    SpotifyQueueItem,
    SpotifyQueueSnapshot,
    spotify_queue_item_from_payload,
)
from src.spotify.queue_service import (
    SpotifyQueueServiceResult,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiClient,
)


_PLAYLIST_URI_PREFIX = "spotify:playlist:"
_LOCAL_URI_PREFIX = "spotify:local:"

_PLAYLIST_PAGE_LIMIT = 50
_MAX_PLAYLIST_PAGES = 200
_DEFAULT_CACHE_SECONDS = 60.0


def _text(value) -> str:
    if not isinstance(
        value,
        str,
    ):
        return ""

    return value.strip()


def _normal(value) -> str:
    return " ".join(
        _text(value).split()
    ).casefold()


def _position(value) -> int | None:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < 0
    ):
        return None

    return value


def _duration(value) -> int | None:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < 0
    ):
        return None

    return value


def _local_uri_key(uri) -> str:
    uri = _text(uri)

    if not uri.casefold().startswith(
        _LOCAL_URI_PREFIX
    ):
        return ""

    value = uri[
        len(_LOCAL_URI_PREFIX):
    ]

    return (
        _LOCAL_URI_PREFIX
        + unquote_plus(
            value
        ).casefold()
    )


def _uris_equal(
    first,
    second,
) -> bool:
    first = _text(first)
    second = _text(second)

    if (
        not first
        or not second
    ):
        return False

    first_local = (
        first.casefold().startswith(
            _LOCAL_URI_PREFIX
        )
    )

    second_local = (
        second.casefold().startswith(
            _LOCAL_URI_PREFIX
        )
    )

    if (
        first_local
        or second_local
    ):
        return (
            first_local
            and second_local
            and _local_uri_key(first)
            == _local_uri_key(second)
        )

    return first == second


def _playlist_id(
    payload,
) -> str:
    if not isinstance(
        payload,
        Mapping,
    ):
        return ""

    context = payload.get(
        "context"
    )

    if not isinstance(
        context,
        Mapping,
    ):
        return ""

    if _normal(
        context.get("type")
    ) != "playlist":
        return ""

    uri = _text(
        context.get("uri")
    )

    if not uri.startswith(
        _PLAYLIST_URI_PREFIX
    ):
        return ""

    value = uri[
        len(_PLAYLIST_URI_PREFIX):
    ]

    if (
        not value
        or not value.isascii()
        or not value.isalnum()
    ):
        return ""

    return value


def _shuffle_enabled(
    payload,
) -> bool:
    if not isinstance(
        payload,
        Mapping,
    ):
        return False

    value = payload.get(
        "shuffle_state"
    )

    return value is True


def _player_item(
    payload,
):
    if not isinstance(
        payload,
        Mapping,
    ):
        return None

    value = payload.get(
        "item"
    )

    if not isinstance(
        value,
        Mapping,
    ):
        return None

    return value


def _player_uri(
    payload,
) -> str:
    item = _player_item(
        payload
    )

    if item is None:
        return ""

    return _text(
        item.get("uri")
    )


def _player_queue_item(
    payload,
) -> SpotifyQueueItem | None:
    item = _player_item(
        payload
    )

    if item is None:
        return None

    try:
        return spotify_queue_item_from_payload(
            item
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def _player_local_signature(
    payload,
):
    item = _player_item(
        payload
    )

    if item is None:
        return None

    if item.get(
        "is_local",
        False,
    ) is not True:
        return None

    title = _normal(
        item.get("name")
    )

    artists = item.get(
        "artists"
    )

    if not isinstance(
        artists,
        list,
    ):
        return None

    names = []

    for artist in artists:
        if not isinstance(
            artist,
            Mapping,
        ):
            continue

        name = _normal(
            artist.get("name")
        )

        if name:
            names.append(name)

    creator = ", ".join(
        names
    )

    album = item.get(
        "album"
    )

    album_name = ""

    if isinstance(
        album,
        Mapping,
    ):
        album_name = _normal(
            album.get("name")
        )

    duration_ms = _duration(
        item.get(
            "duration_ms"
        )
    )

    if (
        not title
        or not creator
    ):
        return None

    return (
        title,
        creator,
        album_name,
        duration_ms,
    )


def _resolved_position(
    item,
) -> int | None:
    return _position(
        getattr(
            item,
            "position",
            None,
        )
    )


def _resolved_is_local(
    item,
) -> bool:
    return bool(
        getattr(
            item,
            "is_local",
            False,
        )
    )


def _resolved_track(
    item,
):
    return getattr(
        item,
        "unified_track",
        None,
    )


def _resolved_uri(
    item,
) -> str:
    track = _resolved_track(
        item
    )

    if track is not None:
        uri = _text(
            getattr(
                track,
                "spotify_uri",
                "",
            )
        )

        if uri:
            return uri

    playlist_item = getattr(
        item,
        "playlist_item",
        None,
    )

    playlist_track = getattr(
        playlist_item,
        "track",
        None,
    )

    return _text(
        getattr(
            playlist_track,
            "spotify_uri",
            "",
        )
    )


def _resolved_local_signature(
    item,
):
    if not _resolved_is_local(
        item
    ):
        return None

    track = _resolved_track(
        item
    )

    if track is None:
        return None

    title = _normal(
        getattr(
            track,
            "title",
            "",
        )
    )

    creator = _normal(
        getattr(
            track,
            "artist",
            "",
        )
    )

    album = _normal(
        getattr(
            track,
            "album",
            "",
        )
    )

    duration_ms = _duration(
        getattr(
            track,
            "duration_ms",
            None,
        )
    )

    if (
        not title
        or not creator
    ):
        return None

    return (
        title,
        creator,
        album,
        duration_ms,
    )


def _signatures_match(
    first,
    second,
) -> bool:
    if (
        first is None
        or second is None
    ):
        return False

    (
        first_title,
        first_creator,
        first_album,
        first_duration,
    ) = first

    (
        second_title,
        second_creator,
        second_album,
        second_duration,
    ) = second

    if (
        first_title != second_title
        or first_creator != second_creator
    ):
        return False

    if (
        first_album
        and second_album
        and first_album != second_album
    ):
        return False

    if (
        first_duration is not None
        and second_duration is not None
        and abs(
            first_duration
            - second_duration
        ) > 3000
    ):
        return False

    return True


def _current_position(
    resolved_items,
    player_payload,
) -> int | None:
    current_uri = _player_uri(
        player_payload
    )

    if current_uri:
        matches = [
            _resolved_position(item)
            for item
            in resolved_items
            if _uris_equal(
                _resolved_uri(item),
                current_uri,
            )
        ]

        matches = [
            value
            for value in matches
            if value is not None
        ]

        if len(matches) == 1:
            return matches[0]

    signature = (
        _player_local_signature(
            player_payload
        )
    )

    if signature is None:
        return None

    matches = []

    for item in resolved_items:
        if not _signatures_match(
            _resolved_local_signature(
                item
            ),
            signature,
        ):
            continue

        position = (
            _resolved_position(item)
        )

        if position is not None:
            matches.append(
                position
            )

    if len(matches) != 1:
        return None

    return matches[0]


def _resolved_item_at(
    resolved_items,
    position,
):
    for item in resolved_items:
        if (
            _resolved_position(item)
            == position
        ):
            return item

    return None


def _local_queue_item(
    resolved_item,
) -> SpotifyQueueItem | None:
    if not _resolved_is_local(
        resolved_item
    ):
        return None

    track = _resolved_track(
        resolved_item
    )

    if track is None:
        return None

    name = _text(
        getattr(
            track,
            "title",
            "",
        )
    )

    uri = _resolved_uri(
        resolved_item
    )

    if (
        not name
        or not uri
    ):
        return None

    return SpotifyQueueItem(
        item_type=QUEUE_ITEM_TRACK,
        name=name,
        uri=uri,
        creator=_text(
            getattr(
                track,
                "artist",
                "",
            )
        ),
        collection=_text(
            getattr(
                track,
                "album",
                "",
            )
        ),
        artwork_url=_text(
            getattr(
                track,
                "artwork_reference",
                "",
            )
        ),
        is_local=True,
        duration_ms=_duration(
            getattr(
                track,
                "duration_ms",
                None,
            )
        ),
    )


def _same_current(
    first,
    second,
) -> bool:
    if (
        first is None
        or second is None
    ):
        return first is second

    return _uris_equal(
        getattr(
            first,
            "uri",
            "",
        ),
        getattr(
            second,
            "uri",
            "",
        ),
    )


class SpotifyEffectiveQueueService:

    def __init__(
        self,
        queue_service,
        session_manager,
        resolved_service_provider,
        *,
        api_client=None,
        cache_seconds=(
            _DEFAULT_CACHE_SECONDS
        ),
        clock=None,
    ) -> None:
        if not callable(
            getattr(
                queue_service,
                "get_queue",
                None,
            )
        ):
            raise TypeError(
                (
                    "queue_service must expose "
                    "get_queue()"
                )
            )

        if not callable(
            getattr(
                session_manager,
                "resolve",
                None,
            )
        ):
            raise TypeError(
                (
                    "session_manager must expose "
                    "resolve()"
                )
            )

        if not callable(
            resolved_service_provider
        ):
            raise TypeError(
                (
                    "resolved_service_provider "
                    "must be callable"
                )
            )

        if api_client is None:
            api_client = (
                SpotifyWebApiClient()
            )

        if not callable(
            getattr(
                api_client,
                "get_json",
                None,
            )
        ):
            raise TypeError(
                (
                    "api_client must expose "
                    "get_json()"
                )
            )

        if (
            isinstance(
                cache_seconds,
                bool,
            )
            or not isinstance(
                cache_seconds,
                (
                    int,
                    float,
                ),
            )
        ):
            raise TypeError(
                (
                    "cache_seconds must "
                    "be numeric"
                )
            )

        cache_seconds = float(
            cache_seconds
        )

        if (
            not math.isfinite(
                cache_seconds
            )
            or cache_seconds < 0
        ):
            raise ValueError(
                (
                    "cache_seconds must be "
                    "finite and non-negative"
                )
            )

        if clock is None:
            clock = time.monotonic

        if not callable(clock):
            raise TypeError(
                "clock must be callable"
            )

        self._queue_service = (
            queue_service
        )

        self._session_manager = (
            session_manager
        )

        self._resolved_service_provider = (
            resolved_service_provider
        )

        self._api_client = (
            api_client
        )

        self._cache_seconds = (
            cache_seconds
        )

        self._clock = clock
        self._playlist_cache = {}

    def _access_token(
        self,
    ) -> str:
        try:
            session = (
                self._session_manager
                .resolve()
            )

        except Exception:
            return ""

        status = getattr(
            session,
            "status",
            None,
        )

        if status not in {
            SpotifySessionStatus.READY,
            SpotifySessionStatus.REFRESHED,
        }:
            return ""

        token = getattr(
            session,
            "token",
            None,
        )

        return _text(
            getattr(
                token,
                "access_token",
                "",
            )
        )

    def _player_payload(
        self,
    ):
        token = self._access_token()

        if not token:
            return None

        try:
            payload = (
                self._api_client
                .get_json(
                    token,
                    "/me/player",
                )
            )

        except Exception:
            return None

        if not isinstance(
            payload,
            Mapping,
        ):
            return None

        return payload

    def _resolved_service(
        self,
    ):
        try:
            service = (
                self._resolved_service_provider()
            )

        except Exception:
            return None

        if not callable(
            getattr(
                service,
                "get_playlist_items",
                None,
            )
        ):
            return None

        return service

    def _resolved_items(
        self,
        playlist_id,
    ):
        service = self._resolved_service()

        if service is None:
            return None

        now = float(
            self._clock()
        )

        cached = (
            self._playlist_cache.get(
                playlist_id
            )
        )

        if cached is not None:
            (
                cached_at,
                cached_items,
            ) = cached

            age = (
                now
                - cached_at
            )

            if (
                age >= 0
                and age
                <= self._cache_seconds
            ):
                return cached_items

        collected = []
        total = None
        offset = 0

        for _ in range(
            _MAX_PLAYLIST_PAGES
        ):
            try:
                result = (
                    service
                    .get_playlist_items(
                        playlist_id,
                        limit=(
                            _PLAYLIST_PAGE_LIMIT
                        ),
                        offset=offset,
                    )
                )

            except Exception:
                return None

            if not bool(
                getattr(
                    result,
                    "ready",
                    False,
                )
            ):
                return None

            page = getattr(
                result,
                "resolved_page",
                None,
            )

            if page is None:
                return None

            page_offset = _position(
                getattr(
                    page,
                    "offset",
                    None,
                )
            )

            page_limit = _position(
                getattr(
                    page,
                    "limit",
                    None,
                )
            )

            page_total = _position(
                getattr(
                    page,
                    "total",
                    None,
                )
            )

            if (
                page_offset != offset
                or page_limit is None
                or page_limit <= 0
                or page_total is None
            ):
                return None

            if total is None:
                total = page_total

            elif page_total != total:
                return None

            collected.extend(
                tuple(
                    getattr(
                        page,
                        "items",
                        (),
                    )
                )
            )

            next_offset = (
                offset
                + page_limit
            )

            if next_offset >= page_total:
                break

            if next_offset <= offset:
                return None

            offset = next_offset

        else:
            return None

        ordered = []

        for item in collected:
            position = (
                _resolved_position(
                    item
                )
            )

            if position is None:
                return None

            ordered.append(
                (
                    position,
                    item,
                )
            )

        ordered.sort(
            key=lambda pair:
            pair[0]
        )

        positions = [
            pair[0]
            for pair in ordered
        ]

        if len(positions) != len(
            set(positions)
        ):
            return None

        items = tuple(
            pair[1]
            for pair in ordered
        )

        self._playlist_cache[
            playlist_id
        ] = (
            now,
            items,
        )

        return items

    @staticmethod
    def _future_items(
        snapshot,
        player_payload,
    ):
        future = list(
            snapshot.items
        )

        stale_current = (
            snapshot.currently_playing
        )

        if stale_current is None:
            return future

        actual_uri = _player_uri(
            player_payload
        )

        if (
            actual_uri
            and _uris_equal(
                stale_current.uri,
                actual_uri,
            )
        ):
            return future

        if (
            future
            and _uris_equal(
                future[0].uri,
                stale_current.uri,
            )
        ):
            return future

        future.insert(
            0,
            stale_current,
        )

        return future

    @staticmethod
    def _merge_local_gaps(
        snapshot,
        player_payload,
        resolved_items,
        current_position,
    ):
        future = (
            SpotifyEffectiveQueueService
            ._future_items(
                snapshot,
                player_payload,
            )
        )

        if not future:
            return None

        playlist_anchors = []

        for item in resolved_items:
            position = (
                _resolved_position(
                    item
                )
            )

            if (
                position is None
                or position
                <= current_position
                or _resolved_is_local(item)
            ):
                continue

            uri = _resolved_uri(item)

            if not uri:
                continue

            playlist_anchors.append(
                item
            )

        if not playlist_anchors:
            return None

        matched = []

        for api_item in future:
            if len(matched) >= len(
                playlist_anchors
            ):
                break

            if (
                api_item.item_type
                != QUEUE_ITEM_TRACK
                or api_item.is_local
            ):
                break

            expected = (
                playlist_anchors[
                    len(matched)
                ]
            )

            if not _uris_equal(
                api_item.uri,
                _resolved_uri(
                    expected
                ),
            ):
                break

            matched.append(
                (
                    api_item,
                    expected,
                )
            )

        if not matched:
            return None

        rebuilt = []
        previous_position = (
            current_position
        )

        for (
            api_item,
            anchor,
        ) in matched:
            target_position = (
                _resolved_position(
                    anchor
                )
            )

            if target_position is None:
                return None

            for item in resolved_items:
                position = (
                    _resolved_position(
                        item
                    )
                )

                if (
                    position is None
                    or position
                    <= previous_position
                    or position
                    >= target_position
                    or not _resolved_is_local(
                        item
                    )
                ):
                    continue

                local_item = (
                    _local_queue_item(
                        item
                    )
                )

                if local_item is None:
                    return None

                rebuilt.append(
                    local_item
                )

            rebuilt.append(
                api_item
            )

            previous_position = (
                target_position
            )

        rebuilt.extend(
            future[
                len(matched):
            ]
        )

        return tuple(rebuilt)

    def _effective_snapshot(
        self,
        snapshot,
    ):
        player = self._player_payload()

        if player is None:
            return snapshot

        player_current = (
            _player_queue_item(
                player
            )
        )

        current = (
            snapshot.currently_playing
        )

        current_changed = False

        if (
            player_current is not None
            and not _same_current(
                current,
                player_current,
            )
        ):
            current = player_current
            current_changed = True

        playlist_id = _playlist_id(
            player
        )

        if not playlist_id:
            if not current_changed:
                return snapshot

            return SpotifyQueueSnapshot(
                currently_playing=current,
                items=snapshot.items,
            )

        resolved_items = (
            self._resolved_items(
                playlist_id
            )
        )

        if resolved_items is None:
            if not current_changed:
                return snapshot

            return SpotifyQueueSnapshot(
                currently_playing=current,
                items=snapshot.items,
            )

        current_position = (
            _current_position(
                resolved_items,
                player,
            )
        )

        if current_position is None:
            if not current_changed:
                return snapshot

            return SpotifyQueueSnapshot(
                currently_playing=current,
                items=snapshot.items,
            )

        if player_current is None:
            resolved_current = (
                _resolved_item_at(
                    resolved_items,
                    current_position,
                )
            )

            local_current = (
                _local_queue_item(
                    resolved_current
                )
                if resolved_current
                is not None
                else None
            )

            if local_current is not None:
                current = local_current
                current_changed = True

        if _shuffle_enabled(player):
            if not current_changed:
                return snapshot

            return SpotifyQueueSnapshot(
                currently_playing=current,
                items=snapshot.items,
            )

        merged = self._merge_local_gaps(
            snapshot,
            player,
            resolved_items,
            current_position,
        )

        if merged is None:
            if not current_changed:
                return snapshot

            return SpotifyQueueSnapshot(
                currently_playing=current,
                items=snapshot.items,
            )

        return SpotifyQueueSnapshot(
            currently_playing=current,
            items=merged,
        )

    def get_queue(
        self,
    ):
        result = (
            self._queue_service
            .get_queue()
        )

        if not isinstance(
            result,
            SpotifyQueueServiceResult,
        ):
            return result

        if (
            not result.ready
            or result.queue is None
        ):
            return result

        try:
            snapshot = (
                self._effective_snapshot(
                    result.queue
                )
            )

        except Exception:
            return result

        if snapshot is result.queue:
            return result

        return replace(
            result,
            queue=snapshot,
        )
