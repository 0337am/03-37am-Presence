from dataclasses import dataclass
from enum import Enum

from src.spotify.album_models import (
    SpotifyAlbumParseError,
    SpotifyAlbumSummary,
    SpotifyAlbumTracksPage,
    spotify_album_summary_from_payload,
    spotify_album_tracks_page_from_payload,
)
from src.spotify.session_manager import (
    SpotifySessionManagerError,
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiClient,
    SpotifyWebApiError,
)


DEFAULT_SPOTIFY_ALBUM_LIMIT = 50


class SpotifyAlbumServiceStatus(
    Enum
):
    READY = "ready"
    DISCONNECTED = "disconnected"
    REAUTHORIZATION_REQUIRED = (
        "reauthorization_required"
    )
    ERROR = "error"


@dataclass(
    frozen=True
)
class SpotifyAlbumServiceResult:
    status: SpotifyAlbumServiceStatus
    message: str = ""
    error_code: str = ""
    retry_after_seconds: int | None = None
    refreshed: bool = False
    album: SpotifyAlbumSummary | None = None
    tracks_page: SpotifyAlbumTracksPage | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            SpotifyAlbumServiceStatus,
        ):
            raise TypeError(
                (
                    "status must be a "
                    "SpotifyAlbumServiceStatus"
                )
            )

        if (
            isinstance(
                self.retry_after_seconds,
                bool,
            )
            or (
                self.retry_after_seconds
                is not None
                and (
                    not isinstance(
                        self.retry_after_seconds,
                        int,
                    )
                    or self.retry_after_seconds < 0
                )
            )
        ):
            raise ValueError(
                (
                    "retry_after_seconds must be "
                    "a non-negative integer or None"
                )
            )

        payload_count = sum(
            (
                self.album is not None,
                self.tracks_page is not None,
            )
        )

        if (
            self.status
            is SpotifyAlbumServiceStatus.READY
        ):
            if payload_count != 1:
                raise ValueError(
                    (
                        "READY album results must "
                        "contain exactly one payload"
                    )
                )

            if self.error_code:
                raise ValueError(
                    (
                        "READY album results cannot "
                        "contain an error code"
                    )
                )

        else:
            if payload_count:
                raise ValueError(
                    (
                        "Non-ready album results cannot "
                        "contain album payloads"
                    )
                )

        if (
            self.status
            is SpotifyAlbumServiceStatus.ERROR
            and not str(
                self.error_code
                or ""
            ).strip()
        ):
            raise ValueError(
                (
                    "ERROR album results require "
                    "an error code"
                )
            )

    @property
    def ready(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyAlbumServiceStatus.READY
        )

    @property
    def connected(
        self,
    ) -> bool:
        return self.status not in {
            SpotifyAlbumServiceStatus.DISCONNECTED,
            SpotifyAlbumServiceStatus.REAUTHORIZATION_REQUIRED,
        }

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyAlbumServiceStatus
            .REAUTHORIZATION_REQUIRED
        )


def _validate_album_id(
    album_id,
) -> str:
    if not isinstance(
        album_id,
        str,
    ):
        raise TypeError(
            "album_id must be text."
        )

    checked = album_id.strip()

    if (
        not checked
        or not checked.isalnum()
    ):
        raise ValueError(
            "album_id is invalid."
        )

    return checked


def _validate_limit(
    limit,
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
        or limit < 1
        or limit > 50
    ):
        raise ValueError(
            "limit must be between 1 and 50."
        )

    return limit


def _validate_offset(
    offset,
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
        or offset < 0
    ):
        raise ValueError(
            "offset must be zero or greater."
        )

    return offset


def _validate_market(
    market,
) -> str:
    if market is None:
        return ""

    if not isinstance(
        market,
        str,
    ):
        raise TypeError(
            "market must be text or None."
        )

    checked = market.strip().upper()

    if (
        len(
            checked
        ) != 2
        or not checked.isalpha()
        or not checked.isascii()
    ):
        raise ValueError(
            "market must be a two-letter country code."
        )

    return checked


class SpotifyAlbumService:
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
    ) -> SpotifyAlbumServiceResult:
        return SpotifyAlbumServiceResult(
            status=(
                SpotifyAlbumServiceStatus.ERROR
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

        except (
            SpotifySessionManagerError,
            Exception,
        ):
            return (
                "",
                False,
                self._error(
                    "session_error",
                    (
                        "Spotify albums could not "
                        "restore the saved session."
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
                SpotifyAlbumServiceResult(
                    status=(
                        SpotifyAlbumServiceStatus
                        .DISCONNECTED
                    ),
                    message=(
                        "Connect Spotify before "
                        "loading albums."
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
                SpotifyAlbumServiceResult(
                    status=(
                        SpotifyAlbumServiceStatus
                        .REAUTHORIZATION_REQUIRED
                    ),
                    message=(
                        "Reconnect Spotify before "
                        "loading albums."
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
                        "Spotify albums could not "
                        "use the saved session."
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
    ) -> SpotifyAlbumServiceResult:
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
            return SpotifyAlbumServiceResult(
                status=(
                    SpotifyAlbumServiceStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                message=(
                    "Reconnect Spotify before "
                    "loading albums."
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
                "Spotify album data could "
                "not be loaded."
            ),
            retry_after_seconds=(
                retry_after
            ),
            refreshed=refreshed,
        )

    def get_album(
        self,
        album_id: str,
        *,
        market: str | None = None,
    ) -> SpotifyAlbumServiceResult:
        checked_album_id = (
            _validate_album_id(
                album_id
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

        query = {}

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
                        "/albums/"
                        + checked_album_id
                    ),
                    query=(
                        query
                        or None
                    ),
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
                    "Spotify album data could "
                    "not be loaded."
                ),
                refreshed=refreshed,
            )

        try:
            album = (
                spotify_album_summary_from_payload(
                    payload
                )
            )

        except (
            SpotifyAlbumParseError,
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_response",
                (
                    "Spotify returned invalid "
                    "album data."
                ),
                refreshed=refreshed,
            )

        return SpotifyAlbumServiceResult(
            status=(
                SpotifyAlbumServiceStatus.READY
            ),
            message=(
                "Spotify album loaded."
            ),
            refreshed=refreshed,
            album=album,
        )

    def get_album_tracks(
        self,
        album_id: str,
        *,
        limit: int = (
            DEFAULT_SPOTIFY_ALBUM_LIMIT
        ),
        offset: int = 0,
        market: str | None = None,
    ) -> SpotifyAlbumServiceResult:
        checked_album_id = (
            _validate_album_id(
                album_id
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
                        "/albums/"
                        + checked_album_id
                        + "/tracks"
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
                    "Spotify album tracks could "
                    "not be loaded."
                ),
                refreshed=refreshed,
            )

        try:
            page = (
                spotify_album_tracks_page_from_payload(
                    payload
                )
            )

        except (
            SpotifyAlbumParseError,
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_response",
                (
                    "Spotify returned invalid "
                    "album track data."
                ),
                refreshed=refreshed,
            )

        return SpotifyAlbumServiceResult(
            status=(
                SpotifyAlbumServiceStatus.READY
            ),
            message=(
                "Spotify album tracks loaded."
            ),
            refreshed=refreshed,
            tracks_page=page,
        )
