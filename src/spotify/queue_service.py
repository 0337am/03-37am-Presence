from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.spotify.queue_models import (
    SpotifyQueueSnapshot,
    spotify_queue_from_payload,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiClient,
    SpotifyWebApiError,
)


class SpotifyQueueServiceStatus(
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
class SpotifyQueueServiceResult:
    status: SpotifyQueueServiceStatus

    queue: SpotifyQueueSnapshot | None = None

    message: str = ""
    error_code: str = ""
    retry_after_seconds: int | None = None
    refreshed: bool = False

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            SpotifyQueueServiceStatus,
        ):
            raise TypeError(
                (
                    "status must be a "
                    "SpotifyQueueServiceStatus"
                )
            )

        if (
            self.queue is not None
            and not isinstance(
                self.queue,
                SpotifyQueueSnapshot,
            )
        ):
            raise TypeError(
                (
                    "queue must be a "
                    "SpotifyQueueSnapshot or None"
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
            is SpotifyQueueServiceStatus.READY
        ):
            if self.queue is None:
                raise ValueError(
                    (
                        "Ready queue results require "
                        "a queue snapshot."
                    )
                )

        elif self.queue is not None:
            raise ValueError(
                (
                    "Non-ready queue results cannot "
                    "expose a queue snapshot."
                )
            )

        if (
            self.status
            is SpotifyQueueServiceStatus.ERROR
        ):
            if not self.error_code.strip():
                raise ValueError(
                    (
                        "Queue error results require "
                        "an error_code."
                    )
                )

        elif self.error_code.strip():
            raise ValueError(
                (
                    "Non-error queue results cannot "
                    "expose an error_code."
                )
            )

    @property
    def ready(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyQueueServiceStatus.READY
        )

    @property
    def connected(
        self,
    ) -> bool:
        return (
            self.status
            is not SpotifyQueueServiceStatus
            .DISCONNECTED
        )

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyQueueServiceStatus
            .REAUTHORIZATION_REQUIRED
        )


class SpotifyQueueService:

    def __init__(
        self,
        session_manager,
        *,
        api_client=None,
    ) -> None:
        resolver = getattr(
            session_manager,
            "resolve",
            None,
        )

        if not callable(
            resolver
        ):
            raise TypeError(
                (
                    "session_manager must expose "
                    "resolve()"
                )
            )

        if api_client is None:
            api_client = (
                SpotifyWebApiClient()
            )

        getter = getattr(
            api_client,
            "get_queue",
            None,
        )

        if not callable(
            getter
        ):
            raise TypeError(
                (
                    "api_client must expose "
                    "get_queue()"
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
    ) -> SpotifyQueueServiceResult:
        return SpotifyQueueServiceResult(
            status=(
                SpotifyQueueServiceStatus.ERROR
            ),
            message=message,
            error_code=(
                str(
                    error_code
                    or "queue_error"
                )
            ),
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

        except Exception:
            return (
                "",
                False,
                self._error(
                    "session_error",
                    (
                        "Spotify Queue could not "
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
                SpotifyQueueServiceResult(
                    status=(
                        SpotifyQueueServiceStatus
                        .DISCONNECTED
                    ),
                    message=(
                        "Connect Spotify to view "
                        "the Queue."
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
                SpotifyQueueServiceResult(
                    status=(
                        SpotifyQueueServiceStatus
                        .REAUTHORIZATION_REQUIRED
                    ),
                    message=(
                        "Reconnect Spotify to view "
                        "the Queue."
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
                        "Spotify Queue could not "
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
    ) -> SpotifyQueueServiceResult:
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
            return SpotifyQueueServiceResult(
                status=(
                    SpotifyQueueServiceStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                message=(
                    "Reconnect Spotify to view "
                    "the Queue."
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

        if error_code in {
            "rate_limited",
            "quota_exceeded",
        }:
            message = (
                "Spotify is limiting Queue "
                "requests. Try again shortly."
            )

        elif error_code in {
            "forbidden",
            "playback_forbidden",
        }:
            message = (
                "Spotify Queue is unavailable "
                "for the current account."
            )

        else:
            message = (
                "Spotify Queue could not be loaded."
            )

        return self._error(
            error_code,
            message,
            retry_after_seconds=(
                retry_after
            ),
            refreshed=refreshed,
        )

    def get_queue(
        self,
    ) -> SpotifyQueueServiceResult:
        (
            access_token,
            refreshed,
            session_error,
        ) = self._resolve_session()

        if session_error is not None:
            return session_error

        try:
            payload = (
                self._api_client
                .get_queue(
                    access_token
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
                    "Spotify Queue could not "
                    "be loaded."
                ),
                refreshed=refreshed,
            )

        try:
            snapshot = (
                spotify_queue_from_payload(
                    payload
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_response",
                (
                    "Spotify returned invalid "
                    "Queue data."
                ),
                refreshed=refreshed,
            )

        return SpotifyQueueServiceResult(
            status=(
                SpotifyQueueServiceStatus.READY
            ),
            queue=snapshot,
            message=(
                "Spotify Queue loaded."
            ),
            refreshed=refreshed,
        )
