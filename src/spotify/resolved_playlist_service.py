from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.media.spotify_playlist_resolver import (
    ResolvedSpotifyPlaylistPage,
    SpotifyPlaylistResolver,
)
from src.spotify.playlist_service import (
    SpotifyPlaylistServiceResult,
    SpotifyPlaylistServiceStatus,
)


class SpotifyResolvedPlaylistServiceStatus(
    str,
    Enum,
):
    READY = "ready"
    DISCONNECTED = "disconnected"
    REAUTHORIZATION_REQUIRED = (
        "reauthorization_required"
    )
    ERROR = "error"


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyResolvedPlaylistServiceResult:
    status: SpotifyResolvedPlaylistServiceStatus
    resolved_page: (
        ResolvedSpotifyPlaylistPage
        | None
    ) = None
    message: str = ""
    error_code: str = ""
    retry_after_seconds: int | None = None
    refreshed: bool = False
    local_snapshot_available: (
        bool
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            SpotifyResolvedPlaylistServiceStatus,
        ):
            raise TypeError(
                (
                    "status must be a "
                    "SpotifyResolvedPlaylistServiceStatus"
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
            self.local_snapshot_available
            is not None
            and not isinstance(
                self.local_snapshot_available,
                bool,
            )
        ):
            raise TypeError(
                (
                    "local_snapshot_available must "
                    "be a boolean or None"
                )
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
                        "retry_after_seconds must be "
                        "an integer or None"
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
            is SpotifyResolvedPlaylistServiceStatus
            .READY
        ):
            if not isinstance(
                self.resolved_page,
                ResolvedSpotifyPlaylistPage,
            ):
                raise ValueError(
                    (
                        "Ready resolved playlist "
                        "results require a "
                        "ResolvedSpotifyPlaylistPage."
                    )
                )

            if self.error_code:
                raise ValueError(
                    (
                        "Ready resolved playlist "
                        "results cannot contain "
                        "an error code."
                    )
                )

        else:
            if self.resolved_page is not None:
                raise ValueError(
                    (
                        "Non-ready resolved playlist "
                        "results cannot contain "
                        "a resolved page."
                    )
                )

            if (
                self.local_snapshot_available
                is not None
            ):
                raise ValueError(
                    (
                        "Non-ready resolved playlist "
                        "results cannot describe a "
                        "local snapshot."
                    )
                )

        if (
            self.status
            is SpotifyResolvedPlaylistServiceStatus
            .ERROR
            and not self.error_code
        ):
            raise ValueError(
                (
                    "Error resolved playlist "
                    "results require an error code."
                )
            )

    @property
    def ready(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyResolvedPlaylistServiceStatus
            .READY
        )

    @property
    def connected(
        self,
    ) -> bool:
        return self.status in {
            SpotifyResolvedPlaylistServiceStatus
            .READY,
            SpotifyResolvedPlaylistServiceStatus
            .ERROR,
        }

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyResolvedPlaylistServiceStatus
            .REAUTHORIZATION_REQUIRED
        )


def _no_local_snapshot():
    return None


class SpotifyResolvedPlaylistService:
    def __init__(
        self,
        playlist_service,
        *,
        playlist_resolver=None,
        candidate_provider=None,
    ) -> None:
        get_playlist_items = getattr(
            playlist_service,
            "get_playlist_items",
            None,
        )

        if not callable(
            get_playlist_items
        ):
            raise TypeError(
                (
                    "playlist_service must provide "
                    "get_playlist_items()"
                )
            )

        if playlist_resolver is None:
            playlist_resolver = (
                SpotifyPlaylistResolver()
            )

        resolve_page = getattr(
            playlist_resolver,
            "resolve_page",
            None,
        )

        if not callable(
            resolve_page
        ):
            raise TypeError(
                (
                    "playlist_resolver must provide "
                    "resolve_page()"
                )
            )

        if candidate_provider is None:
            candidate_provider = (
                _no_local_snapshot
            )

        if not callable(
            candidate_provider
        ):
            raise TypeError(
                (
                    "candidate_provider must be "
                    "callable"
                )
            )

        self._playlist_service = (
            playlist_service
        )

        self._playlist_resolver = (
            playlist_resolver
        )

        self._candidate_provider = (
            candidate_provider
        )

    @staticmethod
    def _error(
        error_code: str,
        message: str,
        *,
        retry_after_seconds: int | None = None,
        refreshed: bool = False,
    ) -> SpotifyResolvedPlaylistServiceResult:
        return SpotifyResolvedPlaylistServiceResult(
            status=(
                SpotifyResolvedPlaylistServiceStatus
                .ERROR
            ),
            message=message,
            error_code=error_code,
            retry_after_seconds=(
                retry_after_seconds
            ),
            refreshed=refreshed,
        )

    @staticmethod
    def _map_non_ready(
        result: SpotifyPlaylistServiceResult,
    ) -> SpotifyResolvedPlaylistServiceResult:
        if (
            result.status
            is SpotifyPlaylistServiceStatus
            .DISCONNECTED
        ):
            return SpotifyResolvedPlaylistServiceResult(
                status=(
                    SpotifyResolvedPlaylistServiceStatus
                    .DISCONNECTED
                ),
                message=result.message,
                refreshed=result.refreshed,
            )

        if (
            result.status
            is SpotifyPlaylistServiceStatus
            .REAUTHORIZATION_REQUIRED
        ):
            return SpotifyResolvedPlaylistServiceResult(
                status=(
                    SpotifyResolvedPlaylistServiceStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                message=result.message,
                refreshed=result.refreshed,
            )

        if (
            result.status
            is SpotifyPlaylistServiceStatus
            .ERROR
        ):
            return SpotifyResolvedPlaylistServiceResult(
                status=(
                    SpotifyResolvedPlaylistServiceStatus
                    .ERROR
                ),
                message=result.message,
                error_code=result.error_code,
                retry_after_seconds=(
                    result.retry_after_seconds
                ),
                refreshed=result.refreshed,
            )

        return SpotifyResolvedPlaylistService._error(
            "invalid_playlist_result",
            (
                "Spotify returned an unexpected "
                "playlist result."
            ),
            refreshed=result.refreshed,
        )

    def get_playlist_items(
        self,
        playlist_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
        market: str | None = None,
    ) -> SpotifyResolvedPlaylistServiceResult:
        try:
            upstream = (
                self._playlist_service
                .get_playlist_items(
                    playlist_id,
                    limit=limit,
                    offset=offset,
                    market=market,
                )
            )

        except Exception:
            return self._error(
                "playlist_service_error",
                (
                    "Spotify playlist items could "
                    "not be loaded."
                ),
            )

        if not isinstance(
            upstream,
            SpotifyPlaylistServiceResult,
        ):
            return self._error(
                "invalid_playlist_result",
                (
                    "Spotify returned an invalid "
                    "playlist result."
                ),
            )

        if (
            upstream.status
            is not SpotifyPlaylistServiceStatus
            .READY
        ):
            return self._map_non_ready(
                upstream
            )

        source_page = (
            upstream.items_page
        )

        if source_page is None:
            return self._error(
                "invalid_playlist_result",
                (
                    "Spotify returned no playlist "
                    "item page."
                ),
                refreshed=upstream.refreshed,
            )

        has_local_items = any(
            item.is_local
            for item in source_page.items
        )

        local_snapshot_available = None
        candidates = ()

        if has_local_items:
            try:
                provided_candidates = (
                    self._candidate_provider()
                )

            except Exception:
                return self._error(
                    "local_snapshot_error",
                    (
                        "Local Music availability "
                        "could not be checked."
                    ),
                    refreshed=upstream.refreshed,
                )

            if provided_candidates is None:
                local_snapshot_available = False
                candidates = ()

            else:
                local_snapshot_available = True
                candidates = provided_candidates

        try:
            resolved_page = (
                self._playlist_resolver
                .resolve_page(
                    source_page,
                    candidates,
                )
            )

        except Exception:
            return self._error(
                "playlist_resolution_error",
                (
                    "Spotify playlist items could "
                    "not be resolved."
                ),
                refreshed=upstream.refreshed,
            )

        if not isinstance(
            resolved_page,
            ResolvedSpotifyPlaylistPage,
        ):
            return self._error(
                "invalid_resolved_playlist",
                (
                    "Spotify playlist resolution "
                    "returned invalid data."
                ),
                refreshed=upstream.refreshed,
            )

        return SpotifyResolvedPlaylistServiceResult(
            status=(
                SpotifyResolvedPlaylistServiceStatus
                .READY
            ),
            resolved_page=resolved_page,
            message=(
                "Spotify playlist items loaded."
            ),
            refreshed=upstream.refreshed,
            local_snapshot_available=(
                local_snapshot_available
            ),
        )
