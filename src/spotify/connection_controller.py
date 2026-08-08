from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
import math
from numbers import Real

from src.spotify.models import (
    SpotifyTokenBundle,
)
from src.spotify.oauth_session import (
    SpotifyOAuthSession,
)
from src.spotify.oauth_session import (
    SpotifyOAuthSessionError,
)
from src.spotify.session_manager import (
    SpotifySessionManager,
)
from src.spotify.session_manager import (
    SpotifySessionManagerError,
)
from src.spotify.session_manager import (
    SpotifySessionStatus,
)


DEFAULT_CALLBACK_TIMEOUT_SECONDS = 180.0


class SpotifyConnectionStatus(
    str,
    Enum,
):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    REFRESHED = "refreshed"
    REAUTHORIZATION_REQUIRED = (
        "reauthorization_required"
    )
    CANCELLED = "cancelled"


class SpotifyConnectionError(
    RuntimeError
):
    def __init__(
        self,
        error_code: str,
        message: str,
    ) -> None:
        super().__init__(
            message
        )

        self.error_code = error_code
        self.message = message


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyConnectionResult:
    status: SpotifyConnectionStatus
    token: SpotifyTokenBundle | None = field(
        default=None,
        repr=False,
    )
    message: str = ""

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            SpotifyConnectionStatus,
        ):
            raise TypeError(
                "status must be a SpotifyConnectionStatus"
            )

        connected_statuses = {
            SpotifyConnectionStatus.CONNECTED,
            SpotifyConnectionStatus.REFRESHED,
        }

        if self.status in connected_statuses:
            if not isinstance(
                self.token,
                SpotifyTokenBundle,
            ):
                raise ValueError(
                    "Connected Spotify result requires a token."
                )
        elif self.token is not None:
            raise ValueError(
                "Disconnected Spotify result cannot contain a token."
            )

        if not isinstance(
            self.message,
            str,
        ):
            raise TypeError(
                "message must be a string"
            )

    @property
    def connected(
        self,
    ) -> bool:
        return self.status in {
            SpotifyConnectionStatus.CONNECTED,
            SpotifyConnectionStatus.REFRESHED,
        }

    @property
    def refreshed(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyConnectionStatus.REFRESHED
        )

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyConnectionStatus.REAUTHORIZATION_REQUIRED
        )

    @property
    def cancelled(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyConnectionStatus.CANCELLED
        )


def _validate_client_id(
    client_id: str,
) -> str:
    if not isinstance(
        client_id,
        str,
    ):
        raise TypeError(
            "Spotify client ID must be a string"
        )

    checked = client_id.strip()

    if not checked:
        raise ValueError(
            "Spotify client ID cannot be empty"
        )

    if any(
        character.isspace()
        for character in checked
    ):
        raise ValueError(
            "Spotify client ID cannot contain whitespace"
        )

    return checked


def _validate_timeout(
    timeout_seconds: float,
) -> float:
    if (
        isinstance(
            timeout_seconds,
            bool,
        )
        or not isinstance(
            timeout_seconds,
            Real,
        )
    ):
        raise TypeError(
            "callback timeout must be a number"
        )

    checked = float(
        timeout_seconds
    )

    if (
        not math.isfinite(
            checked
        )
        or checked <= 0
    ):
        raise ValueError(
            "callback timeout must be a finite positive number"
        )

    return checked


class SpotifyConnectionController:
    def __init__(
        self,
        client_id: str,
        *,
        session_manager=None,
        oauth_session_factory: Callable = (
            SpotifyOAuthSession
        ),
        browser_opener: Callable[
            [str],
            bool,
        ] | None = None,
        callback_timeout_seconds: float = (
            DEFAULT_CALLBACK_TIMEOUT_SECONDS
        ),
    ) -> None:
        self._client_id = _validate_client_id(
            client_id
        )

        if session_manager is None:
            session_manager = SpotifySessionManager(
                self._client_id
            )

        for method_name in (
            "resolve",
            "persist_authorized_token",
            "disconnect",
        ):
            method = getattr(
                session_manager,
                method_name,
                None,
            )

            if not callable(
                method
            ):
                raise TypeError(
                    "session_manager must provide "
                    "resolve(), persist_authorized_token(), "
                    "and disconnect()"
                )

        if not callable(
            oauth_session_factory
        ):
            raise TypeError(
                "oauth_session_factory must be callable"
            )

        if (
            browser_opener is not None
            and not callable(
                browser_opener
            )
        ):
            raise TypeError(
                "browser_opener must be callable or None"
            )

        self._session_manager = (
            session_manager
        )
        self._oauth_session_factory = (
            oauth_session_factory
        )
        self._browser_opener = browser_opener
        self._callback_timeout_seconds = (
            _validate_timeout(
                callback_timeout_seconds
            )
        )

    @property
    def client_id(
        self,
    ) -> str:
        return self._client_id

    @property
    def browser_available(
        self,
    ) -> bool:
        return self._browser_opener is not None

    def restore(
        self,
    ) -> SpotifyConnectionResult:
        try:
            result = (
                self._session_manager.resolve()
            )
        except SpotifySessionManagerError:
            raise SpotifyConnectionError(
                "restore_failed",
                (
                    "Spotify connection state could "
                    "not be restored."
                ),
            ) from None

        if (
            result.status
            is SpotifySessionStatus.DISCONNECTED
        ):
            return SpotifyConnectionResult(
                status=(
                    SpotifyConnectionStatus.DISCONNECTED
                ),
                message="Spotify is not connected.",
            )

        if (
            result.status
            is SpotifySessionStatus.READY
        ):
            return SpotifyConnectionResult(
                status=(
                    SpotifyConnectionStatus.CONNECTED
                ),
                token=result.token,
                message="Spotify is connected.",
            )

        if (
            result.status
            is SpotifySessionStatus.REFRESHED
        ):
            return SpotifyConnectionResult(
                status=(
                    SpotifyConnectionStatus.REFRESHED
                ),
                token=result.token,
                message=(
                    "Spotify connection was refreshed."
                ),
            )

        if (
            result.status
            is SpotifySessionStatus.REAUTHORIZATION_REQUIRED
        ):
            return SpotifyConnectionResult(
                status=(
                    SpotifyConnectionStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                message=(
                    "Spotify must be connected again."
                ),
            )

        raise SpotifyConnectionError(
            "invalid_restore_state",
            (
                "Spotify returned an unexpected "
                "connection state."
            ),
        )

    def connect(
        self,
    ) -> SpotifyConnectionResult:
        if self._browser_opener is None:
            raise SpotifyConnectionError(
                "browser_unavailable",
                (
                    "Spotify authorization cannot start "
                    "because no browser opener is configured."
                ),
            )

        try:
            oauth_session = (
                self._oauth_session_factory(
                    self._client_id,
                    browser_opener=(
                        self._browser_opener
                    ),
                    callback_timeout_seconds=(
                        self._callback_timeout_seconds
                    ),
                )
            )
        except Exception:
            raise SpotifyConnectionError(
                "authorization_setup_failed",
                (
                    "Spotify authorization could not "
                    "be prepared."
                ),
            ) from None

        connect_method = getattr(
            oauth_session,
            "connect",
            None,
        )

        if not callable(
            connect_method
        ):
            raise SpotifyConnectionError(
                "authorization_setup_failed",
                (
                    "Spotify authorization could not "
                    "be prepared."
                ),
            )

        try:
            oauth_result = connect_method()
        except SpotifyOAuthSessionError:
            raise SpotifyConnectionError(
                "authorization_failed",
                (
                    "Spotify authorization did not "
                    "complete successfully."
                ),
            ) from None

        if getattr(
            oauth_result,
            "denied",
            False,
        ):
            return SpotifyConnectionResult(
                status=(
                    SpotifyConnectionStatus.CANCELLED
                ),
                message=(
                    "Spotify authorization was cancelled."
                ),
            )

        if not getattr(
            oauth_result,
            "connected",
            False,
        ):
            raise SpotifyConnectionError(
                "authorization_failed",
                (
                    "Spotify authorization returned "
                    "an unexpected result."
                ),
            )

        token = getattr(
            oauth_result,
            "token",
            None,
        )

        if not isinstance(
            token,
            SpotifyTokenBundle,
        ):
            raise SpotifyConnectionError(
                "authorization_failed",
                (
                    "Spotify authorization returned "
                    "an invalid token."
                ),
            )

        try:
            persisted = (
                self._session_manager
                .persist_authorized_token(
                    token
                )
            )
        except SpotifySessionManagerError:
            raise SpotifyConnectionError(
                "credential_save_failed",
                (
                    "Spotify connected, but the "
                    "credentials could not be saved securely."
                ),
            ) from None

        if (
            persisted.status
            is not SpotifySessionStatus.READY
            or not isinstance(
                persisted.token,
                SpotifyTokenBundle,
            )
        ):
            raise SpotifyConnectionError(
                "credential_save_failed",
                (
                    "Spotify connected, but the "
                    "saved session was invalid."
                ),
            )

        return SpotifyConnectionResult(
            status=(
                SpotifyConnectionStatus.CONNECTED
            ),
            token=persisted.token,
            message="Spotify is connected.",
        )

    def disconnect(
        self,
    ) -> SpotifyConnectionResult:
        try:
            result = (
                self._session_manager.disconnect()
            )
        except SpotifySessionManagerError:
            raise SpotifyConnectionError(
                "disconnect_failed",
                (
                    "Spotify could not be disconnected."
                ),
            ) from None

        if (
            result.status
            is not SpotifySessionStatus.DISCONNECTED
        ):
            raise SpotifyConnectionError(
                "invalid_disconnect_state",
                (
                    "Spotify returned an unexpected "
                    "disconnect state."
                ),
            )

        return SpotifyConnectionResult(
            status=(
                SpotifyConnectionStatus.DISCONNECTED
            ),
            message="Spotify is disconnected.",
        )
