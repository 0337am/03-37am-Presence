from __future__ import annotations

from src.spotify.oauth_callback import (
    LoopbackCallbackCancelled,
)
from collections.abc import Callable
from collections.abc import Iterable
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from numbers import Real

from src.spotify.auth_state import (
    OAuthValidationError,
)
from src.spotify.auth_state import (
    build_authorization_request,
)
from src.spotify.auth_state import (
    parse_authorization_callback,
)
from src.spotify.constants import (
    SPOTIFY_CONNECT_SCOPES,
)
from src.spotify.constants import (
    normalize_scopes,
)
from src.spotify.models import (
    SpotifyTokenBundle,
)
from src.spotify.oauth_callback import (
    LoopbackCallbackError,
)
from src.spotify.oauth_callback import (
    LoopbackCallbackTimeout,
)
from src.spotify.oauth_callback import (
    SpotifyLoopbackCallbackServer,
)
from src.spotify.token_client import (
    SpotifyTokenClient,
)
from src.spotify.token_client import (
    SpotifyTokenError,
)


DEFAULT_CALLBACK_TIMEOUT_SECONDS = 120.0


class SpotifyOAuthSessionStatus(
    str,
    Enum,
):
    CONNECTED = "connected"
    DENIED = "denied"
    CANCELLED = "cancelled"


class SpotifyOAuthSessionError(
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
class SpotifyOAuthSessionResult:
    status: SpotifyOAuthSessionStatus
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
            SpotifyOAuthSessionStatus,
        ):
            raise TypeError(
                "status must be a SpotifyOAuthSessionStatus"
            )

        if (
            self.status
            is SpotifyOAuthSessionStatus.CONNECTED
        ):
            if not isinstance(
                self.token,
                SpotifyTokenBundle,
            ):
                raise ValueError(
                    "connected OAuth result requires a token"
                )

        if (
            self.status
            is SpotifyOAuthSessionStatus.DENIED
            and self.token is not None
        ):
            raise ValueError(
                "denied OAuth result cannot contain a token"
            )

        if (
            self.status
            is SpotifyOAuthSessionStatus.CANCELLED
            and self.token is not None
        ):
            raise ValueError(
                "cancelled OAuth result cannot contain a token"
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
        return (
            self.status
            is SpotifyOAuthSessionStatus.CONNECTED
        )

    @property
    def denied(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyOAuthSessionStatus.DENIED
        )


    @property
    def cancelled(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyOAuthSessionStatus.CANCELLED
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
            "OAuth callback timeout must be a number"
        )

    timeout = float(
        timeout_seconds
    )

    if timeout <= 0:
        raise ValueError(
            "OAuth callback timeout must be positive"
        )

    return timeout


class SpotifyOAuthSession:
    def __init__(
        self,
        client_id: str,
        *,
        browser_opener: Callable[[str], object],
        scopes: Iterable[str] = SPOTIFY_CONNECT_SCOPES,
        callback_timeout_seconds: float = (
            DEFAULT_CALLBACK_TIMEOUT_SECONDS
        ),
        callback_server_factory=(
            SpotifyLoopbackCallbackServer
        ),
        cancel_requested: Callable[[], bool] | None = None,
        token_client=None,
    ) -> None:
        self._client_id = _validate_client_id(
            client_id
        )

        if not callable(
            browser_opener
        ):
            raise TypeError(
                "browser_opener must be callable"
            )

        self._browser_opener = browser_opener

        self._scopes = normalize_scopes(
            scopes
        )

        self._callback_timeout_seconds = (
            _validate_timeout(
                callback_timeout_seconds
            )
        )

        if not callable(
            callback_server_factory
        ):
            raise TypeError(
                "callback_server_factory must be callable"
            )

        self._callback_server_factory = (
            callback_server_factory
        )

        if token_client is None:
            token_client = SpotifyTokenClient(
                self._client_id
            )

        exchange = getattr(
            token_client,
            "exchange_authorization_code",
            None,
        )

        if not callable(
            exchange
        ):
            raise TypeError(
                "token_client must provide "
                "exchange_authorization_code()"
            )

        self._token_client = token_client
        if (
            cancel_requested is not None
            and not callable(
                cancel_requested
            )
        ):
            raise TypeError(
                "cancel_requested must be callable or None"
            )

        self._cancel_requested = (
            cancel_requested
        )

    @property
    def scopes(
        self,
    ) -> tuple[str, ...]:
        return self._scopes

    def _cancelled(
        self,
    ) -> bool:
        if self._cancel_requested is None:
            return False

        try:
            return bool(
                self._cancel_requested()
            )

        except Exception as error:
            raise SpotifyOAuthSessionError(
                "cancellation_error",
                (
                    "Spotify authorization cancellation "
                    "state could not be checked."
                ),
            ) from error

    @staticmethod
    def _cancelled_result(
    ) -> SpotifyOAuthSessionResult:
        return SpotifyOAuthSessionResult(
            status=(
                SpotifyOAuthSessionStatus.CANCELLED
            ),
            message=(
                "Spotify authorization was cancelled."
            ),
        )


    def _open_authorization_page(
        self,
        url: str,
    ) -> None:
        try:
            opened = self._browser_opener(
                url
            )
        except Exception as error:
            raise SpotifyOAuthSessionError(
                "browser_open_failed",
                (
                    "Could not open Spotify authorization "
                    "in the default browser."
                ),
            ) from error

        if not bool(
            opened
        ):
            raise SpotifyOAuthSessionError(
                "browser_open_failed",
                (
                    "Could not open Spotify authorization "
                    "in the default browser."
                ),
            )

    def connect(
        self,
    ) -> SpotifyOAuthSessionResult:
        if self._cancelled():
            return self._cancelled_result()

        try:
            callback_server = (
                self._callback_server_factory()
            )
        except OSError as error:
            raise SpotifyOAuthSessionError(
                "callback_server_error",
                (
                    "Could not start the local Spotify "
                    "authorization listener."
                ),
            ) from error
        except LoopbackCallbackError as error:
            raise SpotifyOAuthSessionError(
                "callback_server_error",
                (
                    "Could not start the local Spotify "
                    "authorization listener."
                ),
            ) from error

        try:
            with callback_server:
                try:
                    redirect_uri = (
                        callback_server.redirect_uri
                    )
                except Exception as error:
                    raise SpotifyOAuthSessionError(
                        "callback_server_error",
                        (
                            "The local Spotify authorization "
                            "listener is invalid."
                        ),
                    ) from error

                authorization = (
                    build_authorization_request(
                        self._client_id,
                        redirect_uri,
                        scopes=self._scopes,
                    )
                )

                self._open_authorization_page(
                    authorization.url
                )

                try:
                    wait_kwargs = {
                        "timeout_seconds": (
                            self._callback_timeout_seconds
                        ),
                    }

                    if (
                        self._cancel_requested
                        is not None
                    ):
                        wait_kwargs[
                            "cancel_requested"
                        ] = self._cancel_requested

                    callback_result = (
                        callback_server.wait_for_callback(
                            **wait_kwargs
                        )
                    )
                except LoopbackCallbackCancelled:
                    return self._cancelled_result()

                except LoopbackCallbackTimeout as error:
                    raise SpotifyOAuthSessionError(
                        "callback_timeout",
                        (
                            "Spotify authorization timed out. "
                            "Try connecting again."
                        ),
                    ) from error
                except LoopbackCallbackError as error:
                    raise SpotifyOAuthSessionError(
                        "callback_error",
                        (
                            "The local Spotify authorization "
                            "callback could not be received."
                        ),
                    ) from error

                try:
                    callback = (
                        parse_authorization_callback(
                            callback_result.callback_url,
                            expected_redirect_uri=(
                                authorization.redirect_uri
                            ),
                            expected_state=(
                                authorization.state
                            ),
                        )
                    )
                except (
                    OAuthValidationError,
                    TypeError,
                ) as error:
                    raise SpotifyOAuthSessionError(
                        "invalid_callback",
                        (
                            "Spotify returned an invalid "
                            "authorization callback."
                        ),
                    ) from error

                if callback.denied:
                    return SpotifyOAuthSessionResult(
                        status=(
                            SpotifyOAuthSessionStatus.DENIED
                        ),
                        message=(
                            "Spotify connection was cancelled."
                        ),
                    )

                try:
                    token = (
                        self._token_client
                        .exchange_authorization_code(
                            callback.code,
                            authorization.redirect_uri,
                            authorization.code_verifier,
                            requested_scopes=(
                                authorization.scopes
                            ),
                        )
                    )
                except SpotifyTokenError as error:
                    raise SpotifyOAuthSessionError(
                        error.error_code,
                        error.message,
                    ) from error

                if not isinstance(
                    token,
                    SpotifyTokenBundle,
                ):
                    raise SpotifyOAuthSessionError(
                        "invalid_token_result",
                        (
                            "Spotify returned an invalid "
                            "authorization result."
                        ),
                    )

                return SpotifyOAuthSessionResult(
                    status=(
                        SpotifyOAuthSessionStatus.CONNECTED
                    ),
                    token=token,
                    message=(
                        "Spotify connected successfully."
                    ),
                )
        except SpotifyOAuthSessionError:
            raise
        except Exception as error:
            raise SpotifyOAuthSessionError(
                "session_error",
                (
                    "Spotify authorization could not "
                    "be completed."
                ),
            ) from error
