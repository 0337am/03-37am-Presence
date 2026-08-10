from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.spotify.session_manager import (
    SpotifySessionManagerError,
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiClient,
    SpotifyWebApiError,
)

from src.spotify.playlist_models import (
    SpotifyPlaylistItemsPage,
    SpotifyPlaylistParseError,
    spotify_playlist_items_page_from_payload,
)


SPOTIFY_LIKED_SONGS_CONTEXT_COMPATIBILITY_ID = (
    "37i9dQZF1F5p3rmiWPIYgZ"
)


class SpotifyLikedSongsServiceStatus(
    str,
    Enum,
):
    READY = "ready"
    DISCONNECTED = "disconnected"
    REAUTHORIZATION_REQUIRED = (
        "reauthorization_required"
    )
    ERROR = "error"


@dataclass(frozen=True)
class SpotifyLikedSongsServiceResult:
    status: SpotifyLikedSongsServiceStatus
    total: int | None = None
    page: SpotifyPlaylistItemsPage | None = None
    context_playlist_id: str | None = None
    message: str = ""
    error_code: str = ""
    retry_after_seconds: int | None = None
    refreshed: bool = False

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            SpotifyLikedSongsServiceStatus,
        ):
            raise TypeError(
                (
                    "status must be a "
                    "SpotifyLikedSongsServiceStatus"
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
            self.page is not None
            and not isinstance(
                self.page,
                SpotifyPlaylistItemsPage,
            )
        ):
            raise TypeError(
                (
                    "page must be a "
                    "SpotifyPlaylistItemsPage "
                    "or None"
                )
            )

        if self.context_playlist_id is not None:
            if not isinstance(
                self.context_playlist_id,
                str,
            ):
                raise TypeError(
                    (
                        "context_playlist_id must "
                        "be a string or None"
                    )
                )

            if not self.context_playlist_id.strip():
                raise ValueError(
                    (
                        "context_playlist_id cannot "
                        "be empty"
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
                        "retry_after_seconds must "
                        "be an integer or None"
                    )
                )

            if self.retry_after_seconds < 0:
                raise ValueError(
                    (
                        "retry_after_seconds "
                        "cannot be negative"
                    )
                )

        if (
            self.status
            is SpotifyLikedSongsServiceStatus.READY
        ):
            if (
                isinstance(
                    self.total,
                    bool,
                )
                or not isinstance(
                    self.total,
                    int,
                )
            ):
                raise ValueError(
                    (
                        "Ready Liked Songs results "
                        "require an integer total."
                    )
                )

            if self.total < 0:
                raise ValueError(
                    (
                        "Liked Songs total cannot "
                        "be negative."
                    )
                )

            if (
                self.page is not None
                and self.page.total
                != self.total
            ):
                raise ValueError(
                    (
                        "Liked Songs page total "
                        "must match result total."
                    )
                )

        elif (
            self.total is not None
            or self.page is not None
            or self.context_playlist_id
            is not None
        ):
            raise ValueError(
                (
                    "Non-ready Liked Songs results "
                    "cannot expose data."
                )
            )

    @property
    def ready(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyLikedSongsServiceStatus.READY
        )

    @property
    def connected(
        self,
    ) -> bool:
        return (
            self.status
            is not
            SpotifyLikedSongsServiceStatus.DISCONNECTED
        )

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyLikedSongsServiceStatus
            .REAUTHORIZATION_REQUIRED
        )


class SpotifyLikedSongsService:
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

        if not callable(resolve):
            raise TypeError(
                (
                    "session_manager must provide "
                    "a callable resolve method"
                )
            )

        if api_client is None:
            api_client = SpotifyWebApiClient()

        get_json = getattr(
            api_client,
            "get_json",
            None,
        )

        if not callable(get_json):
            raise TypeError(
                (
                    "api_client must provide "
                    "a callable get_json method"
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
        retry_after_seconds=None,
        refreshed: bool = False,
    ) -> SpotifyLikedSongsServiceResult:
        return SpotifyLikedSongsServiceResult(
            status=(
                SpotifyLikedSongsServiceStatus.ERROR
            ),
            message=message,
            error_code=error_code,
            retry_after_seconds=(
                retry_after_seconds
            ),
            refreshed=refreshed,
        )

    def _resolve_session(
        self,
    ):
        try:
            session = (
                self._session_manager
                .resolve()
            )

        except SpotifySessionManagerError:
            return (
                "",
                False,
                self._error(
                    "session_error",
                    (
                        "Liked Songs could not restore "
                        "the saved Spotify session."
                    ),
                ),
            )

        except Exception:
            return (
                "",
                False,
                self._error(
                    "session_error",
                    (
                        "Liked Songs could not restore "
                        "the saved Spotify session."
                    ),
                ),
            )

        status = getattr(
            session,
            "status",
            None,
        )

        if (
            status
            is SpotifySessionStatus.DISCONNECTED
        ):
            return (
                "",
                False,
                SpotifyLikedSongsServiceResult(
                    status=(
                        SpotifyLikedSongsServiceStatus
                        .DISCONNECTED
                    ),
                    message=(
                        "Connect Spotify before "
                        "loading Liked Songs."
                    ),
                ),
            )

        if (
            status
            is SpotifySessionStatus
            .REAUTHORIZATION_REQUIRED
        ):
            return (
                "",
                False,
                SpotifyLikedSongsServiceResult(
                    status=(
                        SpotifyLikedSongsServiceStatus
                        .REAUTHORIZATION_REQUIRED
                    ),
                    message=(
                        "Reconnect Spotify before "
                        "loading Liked Songs."
                    ),
                ),
            )

        if status not in {
            SpotifySessionStatus.READY,
            SpotifySessionStatus.REFRESHED,
        }:
            return (
                "",
                False,
                self._error(
                    "invalid_session_state",
                    (
                        "Spotify returned an "
                        "unexpected session state."
                    ),
                ),
            )

        refreshed = (
            status
            is SpotifySessionStatus.REFRESHED
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
            return (
                "",
                refreshed,
                self._error(
                    "invalid_session",
                    (
                        "Liked Songs could not use "
                        "the saved Spotify session."
                    ),
                    refreshed=refreshed,
                ),
            )

        return (
            access_token,
            refreshed,
            None,
        )

    def _api_error(
        self,
        error,
        *,
        refreshed: bool,
    ) -> SpotifyLikedSongsServiceResult:
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
            return SpotifyLikedSongsServiceResult(
                status=(
                    SpotifyLikedSongsServiceStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                message=(
                    "Reconnect Spotify before "
                    "loading Liked Songs."
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
                "Liked Songs could not be "
                "loaded from Spotify."
            ),
            retry_after_seconds=(
                retry_after
            ),
            refreshed=refreshed,
        )

    def get_summary(
        self,
    ) -> SpotifyLikedSongsServiceResult:
        (
            access_token,
            refreshed,
            immediate,
        ) = self._resolve_session()

        if immediate is not None:
            return immediate

        try:
            payload = (
                self._api_client
                .get_json(
                    access_token,
                    "/me/tracks",
                    query={
                        "limit": 1,
                        "offset": 0,
                    },
                )
            )

        except SpotifyWebApiError as error:
            return self._api_error(
                error,
                refreshed=refreshed,
            )

        except Exception:
            return self._error(
                "spotify_api_error",
                (
                    "Liked Songs could not be "
                    "loaded from Spotify."
                ),
                refreshed=refreshed,
            )

        if not isinstance(
            payload,
            dict,
        ):
            return self._error(
                "invalid_response",
                (
                    "Spotify returned invalid "
                    "Liked Songs data."
                ),
                refreshed=refreshed,
            )

        total = payload.get(
            "total"
        )

        if (
            isinstance(
                total,
                bool,
            )
            or not isinstance(
                total,
                int,
            )
            or total < 0
        ):
            return self._error(
                "invalid_response",
                (
                    "Spotify returned invalid "
                    "Liked Songs data."
                ),
                refreshed=refreshed,
            )

        return SpotifyLikedSongsServiceResult(
            status=(
                SpotifyLikedSongsServiceStatus.READY
            ),
            total=total,
            message=(
                "Liked Songs loaded."
            ),
            refreshed=refreshed,
        )


    @staticmethod
    def _playlist_id_from_context(
        payload,
    ) -> str | None:
        if not isinstance(
            payload,
            dict,
        ):
            return None

        context = payload.get(
            "context"
        )

        if not isinstance(
            context,
            dict,
        ):
            return None

        if str(
            context.get(
                "type"
            )
            or ""
        ).strip().casefold() != "playlist":
            return None

        uri = str(
            context.get(
                "uri"
            )
            or ""
        ).strip()

        prefix = "spotify:playlist:"

        if not uri.startswith(
            prefix
        ):
            return None

        playlist_id = uri[
            len(
                prefix
            ):
        ].strip()

        return (
            playlist_id
            or None
        )

    def _validate_liked_context(
        self,
        access_token: str,
        playlist_id: str,
        user_id: str,
    ) -> str | None:
        try:
            payload = (
                self._api_client
                .get_json(
                    access_token,
                    (
                        "/playlists/"
                        + playlist_id
                    ),
                )
            )

        except Exception:
            return None

        if not isinstance(
            payload,
            dict,
        ):
            return None

        returned_id = str(
            payload.get(
                "id"
            )
            or ""
        ).strip()

        name = str(
            payload.get(
                "name"
            )
            or ""
        ).strip()

        owner = payload.get(
            "owner"
        )

        if not isinstance(
            owner,
            dict,
        ):
            return None

        owner_id = str(
            owner.get(
                "id"
            )
            or ""
        ).strip()

        if (
            returned_id != playlist_id
            or name.casefold()
            != "liked songs"
            or owner_id != user_id
        ):
            return None

        return playlist_id

    def _discover_liked_context(
        self,
        access_token: str,
    ) -> str | None:
        try:
            profile = (
                self._api_client
                .get_json(
                    access_token,
                    "/me",
                )
            )

        except Exception:
            return None

        if not isinstance(
            profile,
            dict,
        ):
            return None

        user_id = str(
            profile.get(
                "id"
            )
            or ""
        ).strip()

        if not user_id:
            return None

        candidates = []

        try:
            playback = (
                self._api_client
                .get_json(
                    access_token,
                    (
                        "/me/player/"
                        "currently-playing"
                    ),
                )
            )

        except Exception:
            playback = None

        live_candidate = (
            self._playlist_id_from_context(
                playback
            )
        )

        if live_candidate:
            candidates.append(
                live_candidate
            )

        compatibility_candidate = (
            SPOTIFY_LIKED_SONGS_CONTEXT_COMPATIBILITY_ID
        )

        if (
            compatibility_candidate
            not in candidates
        ):
            candidates.append(
                compatibility_candidate
            )

        for playlist_id in candidates:
            validated = (
                self._validate_liked_context(
                    access_token,
                    playlist_id,
                    user_id,
                )
            )

            if validated is not None:
                return validated

        return None

    def get_tracks_page(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        include_context: bool = False,
    ) -> SpotifyLikedSongsServiceResult:
        if not isinstance(
            include_context,
            bool,
        ):
            raise TypeError(
                (
                    "include_context must be "
                    "a boolean"
                )
            )

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
                "limit must be an integer"
            )

        if (
            limit < 1
            or limit > 50
        ):
            raise ValueError(
                (
                    "limit must be between "
                    "1 and 50"
                )
            )

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
                "offset must be an integer"
            )

        if offset < 0:
            raise ValueError(
                "offset cannot be negative"
            )

        (
            access_token,
            refreshed,
            immediate,
        ) = self._resolve_session()

        if immediate is not None:
            return immediate

        try:
            payload = (
                self._api_client
                .get_json(
                    access_token,
                    "/me/tracks",
                    query={
                        "limit": limit,
                        "offset": offset,
                    },
                )
            )

        except SpotifyWebApiError as error:
            return self._api_error(
                error,
                refreshed=refreshed,
            )

        except Exception:
            return self._error(
                "spotify_api_error",
                (
                    "Liked Songs could not be "
                    "loaded from Spotify."
                ),
                refreshed=refreshed,
            )

        try:
            page = (
                spotify_playlist_items_page_from_payload(
                    payload
                )
            )

        except (
            SpotifyPlaylistParseError,
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_response",
                (
                    "Spotify returned invalid "
                    "Liked Songs data."
                ),
                refreshed=refreshed,
            )

        context_playlist_id = None

        if (
            include_context
            and offset == 0
        ):
            context_playlist_id = (
                self._discover_liked_context(
                    access_token
                )
            )

        return SpotifyLikedSongsServiceResult(
            status=(
                SpotifyLikedSongsServiceStatus.READY
            ),
            total=page.total,
            page=page,
            context_playlist_id=(
                context_playlist_id
            ),
            message=(
                "Liked Songs loaded."
            ),
            refreshed=refreshed,
        )
