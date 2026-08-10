from __future__ import annotations

from dataclasses import dataclass

from src.media.unified_track import (
    LocalTrackReference,
    UnifiedTrack,
    UnifiedTrackSource,
)


class SpotifyPlaylistParseError(
    ValueError
):
    pass


def _text(
    value,
    field_name: str,
    *,
    required: bool = False,
) -> str:
    if value is None:
        value = ""

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            field_name
            + " must be text"
        )

    checked = value.strip()

    if required and not checked:
        raise ValueError(
            field_name
            + " cannot be empty"
        )

    return checked


def _integer(
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
        raise TypeError(
            field_name
            + " must be an integer"
        )

    if value < 0:
        raise ValueError(
            field_name
            + " cannot be negative"
        )

    return value


def _boolean(
    value,
    field_name: str,
) -> bool:
    if not isinstance(
        value,
        bool,
    ):
        raise TypeError(
            field_name
            + " must be a boolean"
        )

    return value


def _optional_boolean(
    value,
    field_name: str,
) -> bool | None:
    if value is None:
        return None

    return _boolean(
        value,
        field_name,
    )


def _object(
    value,
    field_name: str,
) -> dict:
    if not isinstance(
        value,
        dict,
    ):
        raise SpotifyPlaylistParseError(
            field_name
            + " must be an object"
        )

    return value


def _array(
    value,
    field_name: str,
) -> list:
    if not isinstance(
        value,
        list,
    ):
        raise SpotifyPlaylistParseError(
            field_name
            + " must be an array"
        )

    return value


def _artwork_reference(
    images,
) -> str:
    if not isinstance(
        images,
        list,
    ):
        return ""

    for image in images:
        if not isinstance(
            image,
            dict,
        ):
            continue

        url = image.get(
            "url"
        )

        if (
            isinstance(
                url,
                str,
            )
            and url.strip()
        ):
            return url.strip()

    return ""


def _artist_text(
    artists,
) -> str:
    if not isinstance(
        artists,
        list,
    ):
        return ""

    names = []

    for artist in artists:
        if not isinstance(
            artist,
            dict,
        ):
            continue

        name = artist.get(
            "name"
        )

        if (
            isinstance(
                name,
                str,
            )
            and name.strip()
        ):
            names.append(
                name.strip()
            )

    return ", ".join(
        names
    )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyPlaylistSummary:
    spotify_id: str
    name: str
    spotify_uri: str

    owner_id: str = ""
    owner_name: str = ""
    description: str = ""

    public: bool | None = None
    collaborative: bool = False

    total_items: int = 0
    artwork_reference: str = ""

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "spotify_id",
            _text(
                self.spotify_id,
                "spotify_id",
                required=True,
            ),
        )

        object.__setattr__(
            self,
            "name",
            _text(
                self.name,
                "name",
                required=True,
            ),
        )

        uri = _text(
            self.spotify_uri,
            "spotify_uri",
            required=True,
        )

        if not uri.startswith(
            "spotify:playlist:"
        ):
            raise ValueError(
                (
                    "spotify_uri must use "
                    "the spotify:playlist: scheme"
                )
            )

        object.__setattr__(
            self,
            "spotify_uri",
            uri,
        )

        for field_name in (
            "owner_id",
            "owner_name",
            "description",
            "artwork_reference",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name,
                ),
            )

        object.__setattr__(
            self,
            "public",
            _optional_boolean(
                self.public,
                "public",
            ),
        )

        object.__setattr__(
            self,
            "collaborative",
            _boolean(
                self.collaborative,
                "collaborative",
            ),
        )

        object.__setattr__(
            self,
            "total_items",
            _integer(
                self.total_items,
                "total_items",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyPlaylistTrack:
    title: str
    artist: str
    album: str
    duration_ms: int

    spotify_id: str
    spotify_uri: str

    artwork_reference: str = ""
    is_local: bool = False
    playable: bool = True

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "title",
            _text(
                self.title,
                "title",
                required=True,
            ),
        )

        for field_name in (
            "artist",
            "album",
            "spotify_id",
            "artwork_reference",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name,
                ),
            )

        object.__setattr__(
            self,
            "duration_ms",
            _integer(
                self.duration_ms,
                "duration_ms",
            ),
        )

        object.__setattr__(
            self,
            "is_local",
            _boolean(
                self.is_local,
                "is_local",
            ),
        )

        object.__setattr__(
            self,
            "playable",
            _boolean(
                self.playable,
                "playable",
            ),
        )

        uri = _text(
            self.spotify_uri,
            "spotify_uri",
            required=True,
        )

        if self.is_local:
            if not uri.startswith(
                "spotify:local:"
            ):
                raise ValueError(
                    (
                        "Local playlist tracks "
                        "must use spotify:local:"
                    )
                )

            if self.spotify_id:
                raise ValueError(
                    (
                        "Local playlist tracks "
                        "cannot expose a Spotify ID"
                    )
                )

        else:
            if not self.spotify_id:
                raise ValueError(
                    (
                        "Spotify catalogue tracks "
                        "require spotify_id"
                    )
                )

            if not uri.startswith(
                "spotify:track:"
            ):
                raise ValueError(
                    (
                        "Spotify catalogue tracks "
                        "must use spotify:track:"
                    )
                )

        object.__setattr__(
            self,
            "spotify_uri",
            uri,
        )

    def to_local_reference(
        self,
    ) -> LocalTrackReference:
        if not self.is_local:
            raise ValueError(
                (
                    "Only local Spotify playlist "
                    "tracks have LocalTrackReference "
                    "values."
                )
            )

        return LocalTrackReference(
            title=self.title,
            artist=self.artist,
            album=self.album,
            duration_ms=self.duration_ms,
            spotify_local_uri=(
                self.spotify_uri
            ),
        )

    def to_unified_track(
        self,
    ) -> UnifiedTrack:
        if self.is_local:
            raise ValueError(
                (
                    "Local Spotify playlist tracks "
                    "must be resolved against the "
                    "local music index first."
                )
            )

        return UnifiedTrack(
            title=self.title,
            source=(
                UnifiedTrackSource.SPOTIFY
            ),
            artist=self.artist,
            album=self.album,
            duration_ms=self.duration_ms,
            artwork_reference=(
                self.artwork_reference
            ),
            spotify_id=self.spotify_id,
            spotify_uri=self.spotify_uri,
            playable=self.playable,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyPlaylistItem:
    track: SpotifyPlaylistTrack
    is_local: bool
    added_at: str = ""
    position: int = 0

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.track,
            SpotifyPlaylistTrack,
        ):
            raise TypeError(
                (
                    "track must be a "
                    "SpotifyPlaylistTrack"
                )
            )

        local = _boolean(
            self.is_local,
            "is_local",
        )

        if local != self.track.is_local:
            raise ValueError(
                (
                    "Playlist item local status "
                    "must match its track."
                )
            )

        raw_position = self.position

        if isinstance(
            raw_position,
            bool,
        ):
            raise TypeError(
                "position must be an integer"
            )

        checked_position = _integer(
            raw_position,
            "position",
        )

        if checked_position < 0:
            raise ValueError(
                "position cannot be negative"
            )

        object.__setattr__(
            self,
            "position",
            checked_position,
        )

        object.__setattr__(
            self,
            "added_at",
            _text(
                self.added_at,
                "added_at",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyPlaylistPage:
    playlists: tuple[
        SpotifyPlaylistSummary,
        ...,
    ]
    limit: int
    offset: int
    total: int

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.playlists,
            tuple,
        ):
            raise TypeError(
                "playlists must be a tuple"
            )

        for playlist in self.playlists:
            if not isinstance(
                playlist,
                SpotifyPlaylistSummary,
            ):
                raise TypeError(
                    (
                        "playlists must contain "
                        "SpotifyPlaylistSummary values"
                    )
                )

        object.__setattr__(
            self,
            "limit",
            _integer(
                self.limit,
                "limit",
            ),
        )

        object.__setattr__(
            self,
            "offset",
            _integer(
                self.offset,
                "offset",
            ),
        )

        object.__setattr__(
            self,
            "total",
            _integer(
                self.total,
                "total",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyPlaylistItemsPage:
    items: tuple[
        SpotifyPlaylistItem,
        ...,
    ]
    limit: int
    offset: int
    total: int
    omitted_items: int = 0

    def __post_init__(
        self,
    ) -> None:
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
                SpotifyPlaylistItem,
            ):
                raise TypeError(
                    (
                        "items must contain "
                        "SpotifyPlaylistItem values"
                    )
                )

        for field_name in (
            "limit",
            "offset",
            "total",
            "omitted_items",
        ):
            object.__setattr__(
                self,
                field_name,
                _integer(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name,
                ),
            )


def _page_values(
    payload,
):
    page = _object(
        payload,
        "playlist page",
    )

    limit = _integer(
        page.get(
            "limit"
        ),
        "limit",
    )

    offset = _integer(
        page.get(
            "offset"
        ),
        "offset",
    )

    total = _integer(
        page.get(
            "total"
        ),
        "total",
    )

    values = _array(
        page.get(
            "items"
        ),
        "items",
    )

    return (
        page,
        values,
        limit,
        offset,
        total,
    )


def _playlist_summary_from_payload(
    payload,
) -> SpotifyPlaylistSummary:
    data = _object(
        payload,
        "playlist",
    )

    owner = data.get(
        "owner"
    )

    if not isinstance(
        owner,
        dict,
    ):
        owner = {}

    current_items = data.get(
        "items"
    )

    deprecated_tracks = data.get(
        "tracks"
    )

    item_summary = (
        current_items
        if isinstance(
            current_items,
            dict,
        )
        else deprecated_tracks
    )

    if not isinstance(
        item_summary,
        dict,
    ):
        item_summary = {}

    total_items = item_summary.get(
        "total",
        0,
    )

    return SpotifyPlaylistSummary(
        spotify_id=_text(
            data.get(
                "id"
            ),
            "playlist.id",
            required=True,
        ),
        name=_text(
            data.get(
                "name"
            ),
            "playlist.name",
            required=True,
        ),
        spotify_uri=_text(
            data.get(
                "uri"
            ),
            "playlist.uri",
            required=True,
        ),
        owner_id=_text(
            owner.get(
                "id"
            ),
            "playlist.owner.id",
        ),
        owner_name=_text(
            owner.get(
                "display_name"
            ),
            "playlist.owner.display_name",
        ),
        description=_text(
            data.get(
                "description"
            ),
            "playlist.description",
        ),
        public=_optional_boolean(
            data.get(
                "public"
            ),
            "playlist.public",
        ),
        collaborative=_boolean(
            data.get(
                "collaborative",
                False,
            ),
            "playlist.collaborative",
        ),
        total_items=_integer(
            total_items,
            "playlist.items.total",
        ),
        artwork_reference=(
            _artwork_reference(
                data.get(
                    "images"
                )
            )
        ),
    )


def spotify_playlist_page_from_payload(
    payload,
) -> SpotifyPlaylistPage:
    (
        _page,
        raw_items,
        limit,
        offset,
        total,
    ) = _page_values(
        payload
    )

    playlists = tuple(
        _playlist_summary_from_payload(
            item
        )
        for item
        in raw_items
    )

    return SpotifyPlaylistPage(
        playlists=playlists,
        limit=limit,
        offset=offset,
        total=total,
    )


def _track_from_payload(
    payload,
    *,
    local_hint: bool,
) -> SpotifyPlaylistTrack:
    data = _object(
        payload,
        "playlist item",
    )

    item_type = _text(
        data.get(
            "type"
        ),
        "playlist item type",
    )

    if (
        item_type
        and item_type != "track"
    ):
        raise SpotifyPlaylistParseError(
            (
                "Playlist item is not "
                "a track."
            )
        )

    uri = _text(
        data.get(
            "uri"
        ),
        "track.uri",
        required=True,
    )

    track_local = data.get(
        "is_local",
        False,
    )

    if not isinstance(
        track_local,
        bool,
    ):
        raise SpotifyPlaylistParseError(
            (
                "track.is_local must "
                "be a boolean"
            )
        )

    local = bool(
        local_hint
        or track_local
        or uri.startswith(
            "spotify:local:"
        )
    )

    album = data.get(
        "album"
    )

    if not isinstance(
        album,
        dict,
    ):
        album = {}

    raw_playable = data.get(
        "is_playable",
        True,
    )

    if not isinstance(
        raw_playable,
        bool,
    ):
        raw_playable = True

    spotify_id = _text(
        data.get(
            "id"
        ),
        "track.id",
    )

    if local:
        spotify_id = ""

    return SpotifyPlaylistTrack(
        title=_text(
            data.get(
                "name"
            ),
            "track.name",
            required=True,
        ),
        artist=_artist_text(
            data.get(
                "artists"
            )
        ),
        album=_text(
            album.get(
                "name"
            ),
            "track.album.name",
        ),
        duration_ms=_integer(
            data.get(
                "duration_ms"
            ),
            "track.duration_ms",
        ),
        spotify_id=spotify_id,
        spotify_uri=uri,
        artwork_reference=(
            _artwork_reference(
                album.get(
                    "images"
                )
            )
        ),
        is_local=local,
        playable=(
            raw_playable
            if not local
            else False
        ),
    )


def spotify_playlist_items_page_from_payload(
    payload,
) -> SpotifyPlaylistItemsPage:
    (
        _page,
        raw_items,
        limit,
        offset,
        total,
    ) = _page_values(
        payload
    )

    parsed = []
    omitted = 0

    for (
        raw_index,
        raw_entry,
    ) in enumerate(
        raw_items
    ):
        entry = _object(
            raw_entry,
            "playlist entry",
        )

        raw_item = entry.get(
            "item"
        )

        if raw_item is None:
            raw_item = entry.get(
                "track"
            )

        if raw_item is None:
            omitted += 1
            continue

        if not isinstance(
            raw_item,
            dict,
        ):
            raise SpotifyPlaylistParseError(
                (
                    "Playlist entry item "
                    "must be an object or null."
                )
            )

        item_type = raw_item.get(
            "type"
        )

        if (
            isinstance(
                item_type,
                str,
            )
            and item_type.strip()
            and item_type.strip()
            != "track"
        ):
            omitted += 1
            continue

        raw_local = entry.get(
            "is_local",
            False,
        )

        if not isinstance(
            raw_local,
            bool,
        ):
            raise SpotifyPlaylistParseError(
                (
                    "Playlist entry is_local "
                    "must be a boolean."
                )
            )

        track = _track_from_payload(
            raw_item,
            local_hint=raw_local,
        )

        parsed.append(
            SpotifyPlaylistItem(
                track=track,
                is_local=(
                    track.is_local
                ),
                position=(
                    offset
                    + raw_index
                ),
                added_at=_text(
                    entry.get(
                        "added_at"
                    ),
                    "playlist entry added_at",
                ),
            )
        )

    return SpotifyPlaylistItemsPage(
        items=tuple(
            parsed
        ),
        limit=limit,
        offset=offset,
        total=total,
        omitted_items=omitted,
    )
