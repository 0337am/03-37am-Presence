from dataclasses import dataclass
from enum import Enum

from src.spotify.artist_models import (
    SpotifyArtistAlbumsPage,
    SpotifyArtistParseError,
    SpotifyArtistSummary,
    spotify_artist_albums_page_from_payload,
    spotify_artist_summary_from_payload,
)
from src.spotify.session_manager import (
    SpotifySessionManagerError,
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiClient,
    SpotifyWebApiError,
)


DEFAULT_SPOTIFY_ARTIST_ALBUM_LIMIT = 10


class SpotifyArtistServiceStatus(
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
class SpotifyArtistServiceResult:
    status: SpotifyArtistServiceStatus
    message: str = ""
    error_code: str = ""
    retry_after_seconds: int | None = None
    refreshed: bool = False
    artist: SpotifyArtistSummary | None = None
    albums_page: SpotifyArtistAlbumsPage | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            SpotifyArtistServiceStatus,
        ):
            raise TypeError(
                (
                    "status must be a "
                    "SpotifyArtistServiceStatus"
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
                self.artist is not None,
                self.albums_page is not None,
            )
        )

        if (
            self.status
            is SpotifyArtistServiceStatus.READY
        ):
            if payload_count != 1:
                raise ValueError(
                    (
                        "READY artist results must "
                        "contain exactly one payload"
                    )
                )

            if self.error_code:
                raise ValueError(
                    (
                        "READY artist results cannot "
                        "contain an error code"
                    )
                )

        elif payload_count:
            raise ValueError(
                (
                    "Non-ready artist results cannot "
                    "contain artist payloads"
                )
            )

    @property
    def ready(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyArtistServiceStatus.READY
        )

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyArtistServiceStatus
            .REAUTHORIZATION_REQUIRED
        )


def _validate_artist_id(
    artist_id,
) -> str:
    if not isinstance(
        artist_id,
        str,
    ):
        raise TypeError(
            "artist_id must be text."
        )

    checked = artist_id.strip()

    if (
        not checked
        or not checked.isascii()
        or not checked.isalnum()
    ):
        raise ValueError(
            "artist_id is invalid."
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
        or limit > 10
    ):
        raise ValueError(
            "limit must be between 1 and 10."
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


class SpotifyArtistService:
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
    ) -> SpotifyArtistServiceResult:
        return SpotifyArtistServiceResult(
            status=(
                SpotifyArtistServiceStatus.ERROR
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
                        "Spotify artists could not "
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
                SpotifyArtistServiceResult(
                    status=(
                        SpotifyArtistServiceStatus
                        .DISCONNECTED
                    ),
                    message=(
                        "Connect Spotify before "
                        "loading artists."
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
                SpotifyArtistServiceResult(
                    status=(
                        SpotifyArtistServiceStatus
                        .REAUTHORIZATION_REQUIRED
                    ),
                    message=(
                        "Reconnect Spotify before "
                        "loading artists."
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
                    "session_error",
                    (
                        "Spotify artist session "
                        "state is invalid."
                    ),
                ),
            )

        token = getattr(
            session,
            "token",
            None,
        )

        access_token = getattr(
            token,
            "access_token",
            "",
        )

        if (
            not isinstance(
                access_token,
                str,
            )
            or not access_token.strip()
        ):
            return (
                "",
                False,
                self._error(
                    "session_error",
                    (
                        "Spotify artist session "
                        "has no access token."
                    ),
                ),
            )

        refreshed = (
            status
            is SpotifySessionStatus.REFRESHED
        )

        return (
            access_token.strip(),
            refreshed,
            None,
        )

    def _api_error(
        self,
        error,
        *,
        refreshed: bool,
    ) -> SpotifyArtistServiceResult:
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
            return SpotifyArtistServiceResult(
                status=(
                    SpotifyArtistServiceStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                message=(
                    "Reconnect Spotify before "
                    "loading artists."
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
            or (
                retry_after is not None
                and (
                    not isinstance(
                        retry_after,
                        int,
                    )
                    or retry_after < 0
                )
            )
        ):
            retry_after = None

        return self._error(
            error_code,
            (
                "Spotify artist data could "
                "not be loaded."
            ),
            retry_after_seconds=(
                retry_after
            ),
            refreshed=refreshed,
        )

    def get_artist(
        self,
        artist_id: str,
    ) -> SpotifyArtistServiceResult:
        checked_artist_id = (
            _validate_artist_id(
                artist_id
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
                    (
                        "/artists/"
                        + checked_artist_id
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
                    "Spotify artist data could "
                    "not be loaded."
                ),
                refreshed=refreshed,
            )

        try:
            artist = (
                spotify_artist_summary_from_payload(
                    payload
                )
            )

        except (
            SpotifyArtistParseError,
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_response",
                (
                    "Spotify returned invalid "
                    "artist data."
                ),
                refreshed=refreshed,
            )

        return SpotifyArtistServiceResult(
            status=(
                SpotifyArtistServiceStatus.READY
            ),
            message=(
                "Spotify artist loaded."
            ),
            refreshed=refreshed,
            artist=artist,
        )

    def get_artist_albums(
        self,
        artist_id: str,
        *,
        limit: int = (
            DEFAULT_SPOTIFY_ARTIST_ALBUM_LIMIT
        ),
        offset: int = 0,
        market: str | None = None,
    ) -> SpotifyArtistServiceResult:
        checked_artist_id = (
            _validate_artist_id(
                artist_id
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
                        "/artists/"
                        + checked_artist_id
                        + "/albums"
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
                    "Spotify artist albums could "
                    "not be loaded."
                ),
                refreshed=refreshed,
            )

        try:
            page = (
                spotify_artist_albums_page_from_payload(
                    payload
                )
            )

        except (
            SpotifyArtistParseError,
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_response",
                (
                    "Spotify returned invalid "
                    "artist album data."
                ),
                refreshed=refreshed,
            )

        return SpotifyArtistServiceResult(
            status=(
                SpotifyArtistServiceStatus.READY
            ),
            message=(
                "Spotify artist albums loaded."
            ),
            refreshed=refreshed,
            albums_page=page,
        )