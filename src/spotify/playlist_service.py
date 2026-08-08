from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from src.spotify.playlist_models import (
    SpotifyPlaylistItemsPage,
    SpotifyPlaylistPage,
    SpotifyPlaylistParseError,
    spotify_playlist_items_page_from_payload,
    spotify_playlist_page_from_payload,
)
from src.spotify.session_manager import (
    SpotifySessionManagerError,
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiClient,
    SpotifyWebApiError,
)


DEFAULT_SPOTIFY_PLAYLIST_LIMIT = 50
MAX_SPOTIFY_PLAYLIST_LIMIT = 50
MAX_SPOTIFY_PLAYLIST_OFFSET = 100000

_PLAYLIST_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9]+$"
)

_MARKET_PATTERN = re.compile(
    r"^[A-Za-z]{2}$"
)


class SpotifyPlaylistServiceStatus(
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
class SpotifyPlaylistServiceResult:
    status: SpotifyPlaylistServiceStatus

    playlists_page: (
        SpotifyPlaylistPage
        | None
    ) = None

    items_page: (
        SpotifyPlaylistItemsPage
        | None
    ) = None

    message: str = ""
    error_code: str = ""
    retry_after_seconds: int | None = None
    refreshed: bool = False

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            SpotifyPlaylistServiceStatus,
        ):
            raise TypeError(
                (
                    "status must be a "
                    "SpotifyPlaylistServiceStatus"
                )
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

            if self.retry_after_seconds < 0:
                raise ValueError(
                    (
                        "retry_after_seconds "
                        "cannot be negative"
                    )
                )

        ready_payloads = sum(
            (
                self.playlists_page
                is not None,
                self.items_page
                is not None,
            )
        )

        if (
            self.status
            is SpotifyPlaylistServiceStatus.READY
        ):
            if ready_payloads != 1:
                raise ValueError(
                    (
                        "Ready playlist results "
                        "require exactly one page."
                    )
                )

        elif ready_payloads:
            raise ValueError(
                (
                    "Non-ready playlist results "
                    "cannot expose page data."
                )
            )

    @property
    def ready(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyPlaylistServiceStatus.READY
        )

    @property
    def connected(
        self,
    ) -> bool:
        return (
            self.status
            is not SpotifyPlaylistServiceStatus
            .DISCONNECTED
        )

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyPlaylistServiceStatus
            .REAUTHORIZATION_REQUIRED
        )


def _validate_limit(
    value,
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
            "limit must be an integer"
        )

    if not (
        1
        <= value
        <= MAX_SPOTIFY_PLAYLIST_LIMIT
    ):
        raise ValueError(
            (
                "limit must be between "
                "1 and 50"
            )
        )

    return value


def _validate_offset(
    value,
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
            "offset must be an integer"
        )

    if not (
        0
        <= value
        <= MAX_SPOTIFY_PLAYLIST_OFFSET
    ):
        raise ValueError(
            (
                "offset must be between "
                "0 and 100000"
            )
        )

    return value


def _validate_playlist_id(
    value,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "playlist_id must be text"
        )

    checked = value.strip()

    if (
        not checked
        or len(
            checked
        ) > 128
        or not _PLAYLIST_ID_PATTERN
        .fullmatch(
            checked
        )
    ):
        raise ValueError(
            "playlist_id is invalid"
        )

    return checked


def _validate_market(
    value,
) -> str:
    if value is None:
        return ""

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "market must be text or None"
        )

    checked = value.strip()

    if not checked:
        return ""

    if not _MARKET_PATTERN.fullmatch(
        checked
    ):
        raise ValueError(
            (
                "market must be a two-letter "
                "country code"
            )
        )

    return checked.upper()


class SpotifyPlaylistService:
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
    ) -> SpotifyPlaylistServiceResult:
        return SpotifyPlaylistServiceResult(
            status=(
                SpotifyPlaylistServiceStatus
                .ERROR
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
                        "Spotify playlists could "
                        "not restore the saved session."
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
                        "Spotify playlists could "
                        "not restore the saved session."
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
            is SpotifySessionStatus
            .DISCONNECTED
        ):
            return (
                "",
                False,
                SpotifyPlaylistServiceResult(
                    status=(
                        SpotifyPlaylistServiceStatus
                        .DISCONNECTED
                    ),
                    message=(
                        "Connect Spotify before "
                        "loading playlists."
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
                SpotifyPlaylistServiceResult(
                    status=(
                        SpotifyPlaylistServiceStatus
                        .REAUTHORIZATION_REQUIRED
                    ),
                    message=(
                        "Reconnect Spotify before "
                        "loading playlists."
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
            return (
                "",
                refreshed,
                self._error(
                    "invalid_session",
                    (
                        "Spotify playlists could "
                        "not use the saved session."
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
    ) -> SpotifyPlaylistServiceResult:
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
            return SpotifyPlaylistServiceResult(
                status=(
                    SpotifyPlaylistServiceStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                message=(
                    "Reconnect Spotify before "
                    "loading playlists."
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
                "Spotify playlists could "
                "not be loaded."
            ),
            retry_after_seconds=(
                retry_after
            ),
            refreshed=refreshed,
        )

    def get_current_playlists(
        self,
        *,
        limit: int = (
            DEFAULT_SPOTIFY_PLAYLIST_LIMIT
        ),
        offset: int = 0,
    ) -> SpotifyPlaylistServiceResult:
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
                    "/me/playlists",
                    query={
                        "limit": (
                            checked_limit
                        ),
                        "offset": (
                            checked_offset
                        ),
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
                    "Spotify playlists could "
                    "not be loaded."
                ),
                refreshed=refreshed,
            )

        try:
            page = (
                spotify_playlist_page_from_payload(
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
                    "playlist data."
                ),
                refreshed=refreshed,
            )

        return SpotifyPlaylistServiceResult(
            status=(
                SpotifyPlaylistServiceStatus
                .READY
            ),
            playlists_page=page,
            message=(
                "Spotify playlists loaded."
            ),
            refreshed=refreshed,
        )

    def get_playlist_items(
        self,
        playlist_id: str,
        *,
        limit: int = (
            DEFAULT_SPOTIFY_PLAYLIST_LIMIT
        ),
        offset: int = 0,
        market: str | None = None,
    ) -> SpotifyPlaylistServiceResult:
        checked_playlist_id = (
            _validate_playlist_id(
                playlist_id
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

        (
            access_token,
            refreshed,
            immediate,
        ) = self._resolve_session()

        if immediate is not None:
            return immediate

        query = {
            "limit": checked_limit,
            "offset": checked_offset,
        }

        if checked_market:
            query[
                "market"
            ] = checked_market

        try:
            payload = (
                self._api_client
                .get_json(
                    access_token,
                    (
                        "/playlists/"
                        + checked_playlist_id
                        + "/items"
                    ),
                    query=query,
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
                    "Spotify playlist items "
                    "could not be loaded."
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
                    "playlist item data."
                ),
                refreshed=refreshed,
            )

        return SpotifyPlaylistServiceResult(
            status=(
                SpotifyPlaylistServiceStatus
                .READY
            ),
            items_page=page,
            message=(
                "Spotify playlist items loaded."
            ),
            refreshed=refreshed,
        )
