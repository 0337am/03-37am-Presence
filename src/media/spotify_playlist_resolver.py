from __future__ import annotations

from dataclasses import dataclass

from src.media.local_track_resolver import (
    LocalTrackResolution,
    LocalTrackResolutionStatus,
    LocalTrackResolver,
)
from src.media.unified_track import (
    LocalTrackCandidate,
    UnifiedTrack,
    UnifiedTrackSource,
)
from src.spotify.playlist_models import (
    SpotifyPlaylistItem,
    SpotifyPlaylistItemsPage,
)


class SpotifyPlaylistResolverError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class ResolvedSpotifyPlaylistItem:
    playlist_item: SpotifyPlaylistItem
    unified_track: UnifiedTrack
    local_resolution: (
        LocalTrackResolution
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.playlist_item,
            SpotifyPlaylistItem,
        ):
            raise TypeError(
                (
                    "playlist_item must be a "
                    "SpotifyPlaylistItem"
                )
            )

        if not isinstance(
            self.unified_track,
            UnifiedTrack,
        ):
            raise TypeError(
                (
                    "unified_track must be a "
                    "UnifiedTrack"
                )
            )

        if self.playlist_item.is_local:
            if not isinstance(
                self.local_resolution,
                LocalTrackResolution,
            ):
                raise ValueError(
                    (
                        "Resolved local playlist "
                        "items require a local "
                        "resolution."
                    )
                )

            if (
                self.unified_track.source
                is not UnifiedTrackSource.LOCAL
            ):
                raise ValueError(
                    (
                        "Resolved local playlist "
                        "items require a local "
                        "UnifiedTrack."
                    )
                )

            matched = (
                self.local_resolution.status
                is LocalTrackResolutionStatus.MATCHED
            )

            if (
                self.unified_track.local_available
                is not matched
            ):
                raise ValueError(
                    (
                        "Local availability must "
                        "match the resolution state."
                    )
                )

            return

        if self.local_resolution is not None:
            raise ValueError(
                (
                    "Catalogue playlist items "
                    "cannot own a local resolution."
                )
            )

        if (
            self.unified_track.source
            is not UnifiedTrackSource.SPOTIFY
        ):
            raise ValueError(
                (
                    "Catalogue playlist items "
                    "require a Spotify "
                    "UnifiedTrack."
                )
            )

    @property
    def is_local(
        self,
    ) -> bool:
        return self.playlist_item.is_local

    @property
    def added_at(
        self,
    ) -> str:
        return self.playlist_item.added_at

    @property
    def local_available(
        self,
    ) -> bool | None:
        return (
            self.unified_track
            .local_available
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ResolvedSpotifyPlaylistPage:
    items: tuple[
        ResolvedSpotifyPlaylistItem,
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
                ResolvedSpotifyPlaylistItem,
            ):
                raise TypeError(
                    (
                        "items must contain "
                        "ResolvedSpotifyPlaylistItem "
                        "values"
                    )
                )

        for name in (
            "limit",
            "offset",
            "total",
            "omitted_items",
        ):
            value = getattr(
                self,
                name,
            )

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
                    f"{name} must be an integer"
                )

            if value < 0:
                raise ValueError(
                    (
                        f"{name} cannot be "
                        "negative"
                    )
                )

    @property
    def local_count(
        self,
    ) -> int:
        return sum(
            1
            for item in self.items
            if item.is_local
        )

    @property
    def catalogue_count(
        self,
    ) -> int:
        return (
            len(
                self.items
            )
            - self.local_count
        )

    @property
    def available_local_count(
        self,
    ) -> int:
        return sum(
            1
            for item in self.items
            if (
                item.is_local
                and item.local_available
                is True
            )
        )

    @property
    def unavailable_local_count(
        self,
    ) -> int:
        return (
            self.local_count
            - self.available_local_count
        )


def _checked_candidates(
    candidates,
) -> tuple[
    LocalTrackCandidate,
    ...,
]:
    if isinstance(
        candidates,
        (
            str,
            bytes,
        ),
    ):
        raise TypeError(
            (
                "candidates must be an "
                "iterable of "
                "LocalTrackCandidate values"
            )
        )

    try:
        checked = tuple(
            candidates
        )
    except TypeError as error:
        raise TypeError(
            (
                "candidates must be an "
                "iterable of "
                "LocalTrackCandidate values"
            )
        ) from error

    for candidate in checked:
        if not isinstance(
            candidate,
            LocalTrackCandidate,
        ):
            raise TypeError(
                (
                    "candidates must contain "
                    "LocalTrackCandidate values"
                )
            )

    return checked


class SpotifyPlaylistResolver:
    def __init__(
        self,
        local_resolver=None,
    ) -> None:
        if local_resolver is None:
            local_resolver = (
                LocalTrackResolver()
            )

        resolve = getattr(
            local_resolver,
            "resolve",
            None,
        )

        if not callable(
            resolve
        ):
            raise TypeError(
                (
                    "local_resolver must provide "
                    "resolve()"
                )
            )

        self._local_resolver = (
            local_resolver
        )

    def _resolve_item_with_candidates(
        self,
        item: SpotifyPlaylistItem,
        candidates: tuple[
            LocalTrackCandidate,
            ...,
        ],
    ) -> ResolvedSpotifyPlaylistItem:
        if not item.is_local:
            return ResolvedSpotifyPlaylistItem(
                playlist_item=item,
                unified_track=(
                    item.track
                    .to_unified_track()
                ),
            )

        reference = (
            item.track
            .to_local_reference()
        )

        resolution = (
            self._local_resolver
            .resolve(
                reference,
                candidates,
            )
        )

        if not isinstance(
            resolution,
            LocalTrackResolution,
        ):
            raise SpotifyPlaylistResolverError(
                (
                    "Local playlist resolver "
                    "returned an invalid result."
                )
            )

        unified_track = (
            resolution
            .as_unified_track(
                reference
            )
        )

        return ResolvedSpotifyPlaylistItem(
            playlist_item=item,
            unified_track=unified_track,
            local_resolution=resolution,
        )

    def resolve_item(
        self,
        item: SpotifyPlaylistItem,
        candidates=(),
    ) -> ResolvedSpotifyPlaylistItem:
        if not isinstance(
            item,
            SpotifyPlaylistItem,
        ):
            raise TypeError(
                (
                    "item must be a "
                    "SpotifyPlaylistItem"
                )
            )

        if not item.is_local:
            return (
                self
                ._resolve_item_with_candidates(
                    item,
                    (),
                )
            )

        checked_candidates = (
            _checked_candidates(
                candidates
            )
        )

        return (
            self
            ._resolve_item_with_candidates(
                item,
                checked_candidates,
            )
        )

    def resolve_page(
        self,
        page: SpotifyPlaylistItemsPage,
        candidates=(),
    ) -> ResolvedSpotifyPlaylistPage:
        if not isinstance(
            page,
            SpotifyPlaylistItemsPage,
        ):
            raise TypeError(
                (
                    "page must be a "
                    "SpotifyPlaylistItemsPage"
                )
            )

        checked_candidates = (
            _checked_candidates(
                candidates
            )
        )

        resolved_items = tuple(
            self
            ._resolve_item_with_candidates(
                item,
                checked_candidates,
            )
            for item in page.items
        )

        return ResolvedSpotifyPlaylistPage(
            items=resolved_items,
            limit=page.limit,
            offset=page.offset,
            total=page.total,
            omitted_items=(
                page.omitted_items
            ),
        )
