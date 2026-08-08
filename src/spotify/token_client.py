from __future__ import annotations

from collections.abc import Callable
from collections.abc import Iterable
import json
from numbers import Real
import socket
import time
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen as default_urlopen

from src.spotify.auth_state import (
    validate_loopback_redirect_uri,
)
from src.spotify.constants import (
    SPOTIFY_CONNECT_SCOPES,
)
from src.spotify.constants import (
    SPOTIFY_TOKEN_URL,
)
from src.spotify.constants import normalize_scopes
from src.spotify.models import SpotifyTokenBundle
from src.spotify.pkce import validate_code_verifier


DEFAULT_TOKEN_TIMEOUT_SECONDS = 15.0
MAX_TOKEN_RESPONSE_BYTES = 64 * 1024

TOKEN_USER_AGENT = (
    "03-37am-Presence/Spotify-OAuth"
)


class SpotifyTokenError(
    RuntimeError
):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        spotify_error: str = "",
    ) -> None:
        super().__init__(
            message
        )

        self.error_code = error_code
        self.message = message
        self.spotify_error = (
            _sanitize_error_name(
                spotify_error
            )
        )


def _sanitize_error_name(
    value: object,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        return ""

    if not value:
        return ""

    if len(
        value
    ) > 64:
        return ""

    if not all(
        character.isalnum()
        or character in "_-"
        for character in value
    ):
        return ""

    return value


def _require_nonempty_string(
    value: object,
    field_name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be a string"
        )

    if not value:
        raise ValueError(
            f"{field_name} cannot be empty"
        )

    return value


def _validate_client_id(
    client_id: str,
) -> str:
    checked = _require_nonempty_string(
        client_id,
        "client_id",
    ).strip()

    if not checked:
        raise ValueError(
            "client_id cannot be empty"
        )

    if any(
        character.isspace()
        for character in checked
    ):
        raise ValueError(
            "client_id cannot contain whitespace"
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
            "token timeout must be a number"
        )

    timeout = float(
        timeout_seconds
    )

    if timeout <= 0:
        raise ValueError(
            "token timeout must be positive"
        )

    return timeout


def _safe_timestamp(
    clock: Callable[[], float],
) -> float:
    value = clock()

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            Real,
        )
    ):
        raise SpotifyTokenError(
            "clock_error",
            "Spotify token clock returned an invalid value.",
        )

    timestamp = float(
        value
    )

    if timestamp < 0:
        raise SpotifyTokenError(
            "clock_error",
            "Spotify token clock returned an invalid value.",
        )

    return timestamp


def _response_status(
    response: Any,
) -> int:
    status = getattr(
        response,
        "status",
        None,
    )

    if status is not None:
        return int(
            status
        )

    getcode = getattr(
        response,
        "getcode",
        None,
    )

    if callable(
        getcode
    ):
        return int(
            getcode()
        )

    return 200


def _response_url(
    response: Any,
) -> str:
    geturl = getattr(
        response,
        "geturl",
        None,
    )

    if callable(
        geturl
    ):
        result = geturl()

        if isinstance(
            result,
            str,
        ):
            return result

    return SPOTIFY_TOKEN_URL


def _content_length(
    response: Any,
) -> int | None:
    headers = getattr(
        response,
        "headers",
        None,
    )

    if headers is None:
        return None

    get = getattr(
        headers,
        "get",
        None,
    )

    if not callable(
        get
    ):
        return None

    raw = get(
        "Content-Length"
    )

    if raw is None:
        return None

    try:
        length = int(
            raw
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise SpotifyTokenError(
            "invalid_response",
            "Spotify returned an invalid token response.",
        ) from error

    if length < 0:
        raise SpotifyTokenError(
            "invalid_response",
            "Spotify returned an invalid token response.",
        )

    return length


def _read_response_body(
    response: Any,
) -> bytes:
    length = _content_length(
        response
    )

    if (
        length is not None
        and length > MAX_TOKEN_RESPONSE_BYTES
    ):
        raise SpotifyTokenError(
            "response_too_large",
            "Spotify returned an unexpectedly large token response.",
        )

    body = response.read(
        MAX_TOKEN_RESPONSE_BYTES
        + 1
    )

    if not isinstance(
        body,
        bytes,
    ):
        raise SpotifyTokenError(
            "invalid_response",
            "Spotify returned an invalid token response.",
        )

    if len(
        body
    ) > MAX_TOKEN_RESPONSE_BYTES:
        raise SpotifyTokenError(
            "response_too_large",
            "Spotify returned an unexpectedly large token response.",
        )

    return body


def _decode_json_object(
    body: bytes,
) -> dict[str, Any]:
    try:
        decoded = body.decode(
            "utf-8"
        )

        payload = json.loads(
            decoded
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise SpotifyTokenError(
            "invalid_response",
            "Spotify returned an invalid token response.",
        ) from error

    if not isinstance(
        payload,
        dict,
    ):
        raise SpotifyTokenError(
            "invalid_response",
            "Spotify returned an invalid token response.",
        )

    return payload


def _oauth_error_name(
    body: bytes,
) -> str:
    try:
        payload = _decode_json_object(
            body
        )
    except SpotifyTokenError:
        return ""

    return _sanitize_error_name(
        payload.get(
            "error",
            "",
        )
    )


def _raise_oauth_error(
    spotify_error: str,
) -> None:
    if spotify_error == "invalid_grant":
        raise SpotifyTokenError(
            "reauthorization_required",
            (
                "Spotify authorization is expired, revoked, "
                "or no longer valid. Reconnect Spotify."
            ),
            spotify_error=spotify_error,
        )

    if spotify_error == "invalid_client":
        raise SpotifyTokenError(
            "invalid_client",
            "Spotify rejected the application client ID.",
            spotify_error=spotify_error,
        )

    raise SpotifyTokenError(
        "spotify_rejected_request",
        "Spotify rejected the token request.",
        spotify_error=spotify_error,
    )


def _response_string(
    payload: dict[str, Any],
    field_name: str,
    *,
    required: bool,
) -> str:
    value = payload.get(
        field_name
    )

    if value is None:
        if required:
            raise SpotifyTokenError(
                "invalid_response",
                "Spotify returned an incomplete token response.",
            )

        return ""

    if not isinstance(
        value,
        str,
    ):
        raise SpotifyTokenError(
            "invalid_response",
            "Spotify returned an invalid token response.",
        )

    if (
        required
        and not value
    ):
        raise SpotifyTokenError(
            "invalid_response",
            "Spotify returned an incomplete token response.",
        )

    return value


def _response_expires_in(
    payload: dict[str, Any],
) -> int:
    value = payload.get(
        "expires_in"
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
        or value <= 0
    ):
        raise SpotifyTokenError(
            "invalid_response",
            "Spotify returned an invalid token lifetime.",
        )

    return value


def _response_scopes(
    payload: dict[str, Any],
    fallback: tuple[str, ...],
) -> tuple[str, ...]:
    raw_scope = payload.get(
        "scope"
    )

    if raw_scope is None:
        return fallback

    if not isinstance(
        raw_scope,
        str,
    ):
        raise SpotifyTokenError(
            "invalid_response",
            "Spotify returned invalid scope data.",
        )

    if not raw_scope.strip():
        return fallback

    try:
        return normalize_scopes(
            raw_scope.split()
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise SpotifyTokenError(
            "invalid_response",
            "Spotify returned invalid scope data.",
        ) from error


class SpotifyTokenClient:
    def __init__(
        self,
        client_id: str,
        *,
        urlopen=None,
        timeout_seconds: float = DEFAULT_TOKEN_TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client_id = _validate_client_id(
            client_id
        )

        self._urlopen = (
            default_urlopen
            if urlopen is None
            else urlopen
        )

        if not callable(
            self._urlopen
        ):
            raise TypeError(
                "urlopen must be callable"
            )

        self._timeout_seconds = (
            _validate_timeout(
                timeout_seconds
            )
        )

        if not callable(
            clock
        ):
            raise TypeError(
                "clock must be callable"
            )

        self._clock = clock

    def _post_form(
        self,
        fields: tuple[
            tuple[str, str],
            ...,
        ],
    ) -> dict[str, Any]:
        body = urlencode(
            fields
        ).encode(
            "utf-8"
        )

        request = Request(
            SPOTIFY_TOKEN_URL,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": (
                    "application/x-www-form-urlencoded"
                ),
                "User-Agent": TOKEN_USER_AGENT,
            },
        )

        try:
            response = self._urlopen(
                request,
                timeout=self._timeout_seconds,
            )

            with response:
                if (
                    _response_url(
                        response
                    )
                    != SPOTIFY_TOKEN_URL
                ):
                    raise SpotifyTokenError(
                        "untrusted_response",
                        "Spotify token response came from an unexpected URL.",
                    )

                status = _response_status(
                    response
                )

                response_body = (
                    _read_response_body(
                        response
                    )
                )

                if not 200 <= status <= 299:
                    _raise_oauth_error(
                        _oauth_error_name(
                            response_body
                        )
                    )

        except HTTPError as error:
            try:
                try:
                    response_body = error.read(
                        MAX_TOKEN_RESPONSE_BYTES
                        + 1
                    )
                except Exception:
                    response_body = b""

                if len(
                    response_body
                ) > MAX_TOKEN_RESPONSE_BYTES:
                    response_body = b""

                spotify_error = _oauth_error_name(
                    response_body
                )
            finally:
                try:
                    error.close()
                except Exception:
                    pass

            _raise_oauth_error(
                spotify_error
            )

        except (
            socket.timeout,
            TimeoutError,
        ) as error:
            raise SpotifyTokenError(
                "timeout",
                "Spotify token request timed out.",
            ) from error

        except URLError as error:
            reason = getattr(
                error,
                "reason",
                None,
            )

            if isinstance(
                reason,
                (
                    socket.timeout,
                    TimeoutError,
                ),
            ):
                raise SpotifyTokenError(
                    "timeout",
                    "Spotify token request timed out.",
                ) from error

            raise SpotifyTokenError(
                "network_error",
                "Could not reach Spotify.",
            ) from error

        return _decode_json_object(
            response_body
        )

    def exchange_authorization_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str,
        *,
        requested_scopes: Iterable[str] = (
            SPOTIFY_CONNECT_SCOPES
        ),
    ) -> SpotifyTokenBundle:
        checked_code = (
            _require_nonempty_string(
                code,
                "authorization code",
            )
        )

        checked_redirect_uri = (
            validate_loopback_redirect_uri(
                redirect_uri,
                require_port=True,
            )
        )

        checked_verifier = (
            validate_code_verifier(
                code_verifier
            )
        )

        checked_scopes = normalize_scopes(
            requested_scopes
        )

        now = _safe_timestamp(
            self._clock
        )

        payload = self._post_form(
            (
                (
                    "client_id",
                    self._client_id,
                ),
                (
                    "grant_type",
                    "authorization_code",
                ),
                (
                    "code",
                    checked_code,
                ),
                (
                    "redirect_uri",
                    checked_redirect_uri,
                ),
                (
                    "code_verifier",
                    checked_verifier,
                ),
            )
        )

        access_token = _response_string(
            payload,
            "access_token",
            required=True,
        )

        refresh_token = _response_string(
            payload,
            "refresh_token",
            required=True,
        )

        token_type = _response_string(
            payload,
            "token_type",
            required=True,
        )

        if token_type.casefold() != "bearer":
            raise SpotifyTokenError(
                "invalid_response",
                "Spotify returned an unsupported token type.",
            )

        expires_in = _response_expires_in(
            payload
        )

        scopes = _response_scopes(
            payload,
            checked_scopes,
        )

        return SpotifyTokenBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=expires_in,
            granted_scopes=scopes,
            obtained_at=now,
            authorized_at=now,
        )

    def refresh_access_token(
        self,
        current: SpotifyTokenBundle,
    ) -> SpotifyTokenBundle:
        if not isinstance(
            current,
            SpotifyTokenBundle,
        ):
            raise TypeError(
                "current must be a SpotifyTokenBundle"
            )

        if not current.refresh_token:
            raise SpotifyTokenError(
                "reauthorization_required",
                "Spotify must be reconnected before refreshing.",
            )

        now = _safe_timestamp(
            self._clock
        )

        payload = self._post_form(
            (
                (
                    "grant_type",
                    "refresh_token",
                ),
                (
                    "refresh_token",
                    current.refresh_token,
                ),
                (
                    "client_id",
                    self._client_id,
                ),
            )
        )

        access_token = _response_string(
            payload,
            "access_token",
            required=True,
        )

        replacement_refresh_token = (
            _response_string(
                payload,
                "refresh_token",
                required=False,
            )
        )

        refresh_token = (
            replacement_refresh_token
            or current.refresh_token
        )

        token_type = _response_string(
            payload,
            "token_type",
            required=True,
        )

        if token_type.casefold() != "bearer":
            raise SpotifyTokenError(
                "invalid_response",
                "Spotify returned an unsupported token type.",
            )

        expires_in = _response_expires_in(
            payload
        )

        scopes = _response_scopes(
            payload,
            current.granted_scopes,
        )

        return SpotifyTokenBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=expires_in,
            granted_scopes=scopes,
            obtained_at=now,
            authorized_at=current.authorized_at,
        )
