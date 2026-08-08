from __future__ import annotations

from collections.abc import Mapping
from email.message import Message
import json
from numbers import Real
import socket
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)

from src.spotify.constants import (
    SPOTIFY_API_BASE_URL,
)
from src.spotify.models import (
    SpotifyAccount,
)


DEFAULT_SPOTIFY_API_TIMEOUT_SECONDS = 10.0
MAX_SPOTIFY_API_RESPONSE_BYTES = 1024 * 1024

SPOTIFY_API_USER_AGENT = (
    "03-37am-Presence/2.9 Spotify-Web-API"
)

CURRENT_USER_PROFILE_URL = (
    f"{SPOTIFY_API_BASE_URL}/me"
)


class SpotifyWebApiError(
    RuntimeError
):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(
            message
        )

        self.error_code = (
            str(
                error_code
            ).strip()
        )

        self.message = str(
            message
        ).strip()

        self.retry_after_seconds = (
            retry_after_seconds
        )


class _NoSpotifyRedirectHandler(
    HTTPRedirectHandler
):
    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl,
    ):
        return None


def _default_urlopen(
    request,
    *,
    timeout,
):
    opener = build_opener(
        _NoSpotifyRedirectHandler()
    )

    return opener.open(
        request,
        timeout=timeout,
    )


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
            "Spotify API timeout must be a number"
        )

    timeout = float(
        timeout_seconds
    )

    if timeout <= 0:
        raise ValueError(
            "Spotify API timeout must be positive"
        )

    return timeout


def _validate_access_token(
    access_token: str,
) -> str:
    if not isinstance(
        access_token,
        str,
    ):
        raise TypeError(
            "Spotify access token must be a string"
        )

    checked = access_token.strip()

    if not checked:
        raise ValueError(
            "Spotify access token cannot be empty"
        )

    if any(
        character.isspace()
        for character in checked
    ):
        raise ValueError(
            "Spotify access token cannot contain whitespace"
        )

    return checked


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
    fallback: str,
) -> str:
    geturl = getattr(
        response,
        "geturl",
        None,
    )

    if callable(
        geturl
    ):
        value = geturl()

        if isinstance(
            value,
            str,
        ):
            return value

    return fallback


def _response_headers(
    response: Any,
):
    return getattr(
        response,
        "headers",
        None,
    )


def _header_value(
    headers: Any,
    name: str,
) -> str | None:
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

    value = get(
        name
    )

    if value is None:
        return None

    return str(
        value
    ).strip()


def _content_length(
    response: Any,
) -> int | None:
    raw = _header_value(
        _response_headers(
            response
        ),
        "Content-Length",
    )

    if raw is None:
        return None

    try:
        value = int(
            raw
        )

    except (
        TypeError,
        ValueError,
    ):
        raise SpotifyWebApiError(
            "invalid_response",
            (
                "Spotify returned an invalid "
                "Content-Length header."
            ),
        ) from None

    if value < 0:
        raise SpotifyWebApiError(
            "invalid_response",
            (
                "Spotify returned an invalid "
                "Content-Length header."
            ),
        )

    return value


def _read_limited_body(
    response: Any,
) -> bytes:
    content_length = _content_length(
        response
    )

    if (
        content_length is not None
        and content_length
        > MAX_SPOTIFY_API_RESPONSE_BYTES
    ):
        raise SpotifyWebApiError(
            "response_too_large",
            "Spotify returned too much data.",
        )

    body = response.read(
        MAX_SPOTIFY_API_RESPONSE_BYTES
        + 1
    )

    if not isinstance(
        body,
        bytes,
    ):
        raise SpotifyWebApiError(
            "invalid_response",
            "Spotify returned invalid response data.",
        )

    if len(
        body
    ) > MAX_SPOTIFY_API_RESPONSE_BYTES:
        raise SpotifyWebApiError(
            "response_too_large",
            "Spotify returned too much data.",
        )

    return body


def _decode_json_object(
    body: bytes,
) -> dict[str, Any]:
    try:
        payload = json.loads(
            body.decode(
                "utf-8"
            )
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise SpotifyWebApiError(
            "invalid_response",
            "Spotify returned invalid JSON.",
        ) from None

    if not isinstance(
        payload,
        dict,
    ):
        raise SpotifyWebApiError(
            "invalid_response",
            "Spotify returned an invalid JSON object.",
        )

    return payload


def _retry_after_seconds(
    headers: Any,
) -> int | None:
    raw = _header_value(
        headers,
        "Retry-After",
    )

    if not raw:
        return None

    try:
        value = int(
            raw
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if value < 0:
        return None

    return value


def _safe_error_payload(
    body: bytes,
) -> dict[str, Any]:
    if not body:
        return {}

    if len(
        body
    ) > MAX_SPOTIFY_API_RESPONSE_BYTES:
        return {}

    try:
        payload = json.loads(
            body.decode(
                "utf-8"
            )
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return {}

    if not isinstance(
        payload,
        dict,
    ):
        return {}

    return payload


def _quota_exceeded(
    payload: Mapping[str, Any],
) -> bool:
    reason = payload.get(
        "reason"
    )

    if (
        isinstance(
            reason,
            str,
        )
        and reason.strip().upper()
        == "QUOTA_EXCEEDED"
    ):
        return True

    error_object = payload.get(
        "error"
    )

    if not isinstance(
        error_object,
        dict,
    ):
        return False

    nested_reason = error_object.get(
        "reason"
    )

    return (
        isinstance(
            nested_reason,
            str,
        )
        and nested_reason.strip().upper()
        == "QUOTA_EXCEEDED"
    )


def _raise_http_error(
    status: int,
    *,
    headers: Any = None,
    payload: Mapping[str, Any] | None = None,
) -> None:
    checked_payload = (
        payload
        if payload is not None
        else {}
    )

    if status == 401:
        raise SpotifyWebApiError(
            "reauthorization_required",
            (
                "Spotify authorization is no "
                "longer valid."
            ),
        )

    if status == 403:
        raise SpotifyWebApiError(
            "forbidden",
            (
                "Spotify did not allow this "
                "request."
            ),
        )

    if status == 404:
        raise SpotifyWebApiError(
            "not_found",
            (
                "The requested Spotify resource "
                "was not found."
            ),
        )

    if status == 429:
        retry_after = (
            _retry_after_seconds(
                headers
            )
        )

        if _quota_exceeded(
            checked_payload
        ):
            raise SpotifyWebApiError(
                "quota_exceeded",
                (
                    "Spotify's development quota "
                    "has been reached."
                ),
                retry_after_seconds=(
                    retry_after
                ),
            )

        raise SpotifyWebApiError(
            "rate_limited",
            (
                "Spotify is rate limiting "
                "requests."
            ),
            retry_after_seconds=(
                retry_after
            ),
        )

    if status in (
        500,
        502,
        503,
        504,
    ):
        raise SpotifyWebApiError(
            "spotify_unavailable",
            (
                "Spotify is temporarily "
                "unavailable."
            ),
        )

    raise SpotifyWebApiError(
        "http_error",
        (
            "Spotify returned an unexpected "
            "HTTP response."
        ),
    )


def _required_string(
    payload: Mapping[str, Any],
    name: str,
) -> str:
    value = payload.get(
        name
    )

    if not isinstance(
        value,
        str,
    ):
        raise SpotifyWebApiError(
            "invalid_response",
            (
                f"Spotify profile field "
                f"{name!r} was invalid."
            ),
        )

    checked = value.strip()

    if not checked:
        raise SpotifyWebApiError(
            "invalid_response",
            (
                f"Spotify profile field "
                f"{name!r} was empty."
            ),
        )

    return checked


def _optional_string(
    payload: Mapping[str, Any],
    name: str,
) -> str:
    value = payload.get(
        name
    )

    if value is None:
        return ""

    if not isinstance(
        value,
        str,
    ):
        raise SpotifyWebApiError(
            "invalid_response",
            (
                f"Spotify profile field "
                f"{name!r} was invalid."
            ),
        )

    return value.strip()


def _profile_url(
    payload: Mapping[str, Any],
) -> str:
    external_urls = payload.get(
        "external_urls"
    )

    if external_urls is None:
        return ""

    if not isinstance(
        external_urls,
        dict,
    ):
        raise SpotifyWebApiError(
            "invalid_response",
            (
                "Spotify profile external URLs "
                "were invalid."
            ),
        )

    return _optional_string(
        external_urls,
        "spotify",
    )


def _profile_image_url(
    payload: Mapping[str, Any],
) -> str:
    images = payload.get(
        "images"
    )

    if images is None:
        return ""

    if not isinstance(
        images,
        list,
    ):
        raise SpotifyWebApiError(
            "invalid_response",
            (
                "Spotify profile images were "
                "invalid."
            ),
        )

    if not images:
        return ""

    first = images[0]

    if not isinstance(
        first,
        dict,
    ):
        raise SpotifyWebApiError(
            "invalid_response",
            (
                "Spotify profile image was "
                "invalid."
            ),
        )

    return _optional_string(
        first,
        "url",
    )


def spotify_account_from_payload(
    payload: Mapping[str, Any],
) -> SpotifyAccount:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise TypeError(
            "payload must be a mapping"
        )

    return SpotifyAccount(
        account_id=_required_string(
            payload,
            "account_id",
        ),
        display_name=_optional_string(
            payload,
            "display_name",
        ),
        user_id=_optional_string(
            payload,
            "id",
        ),
        uri=_optional_string(
            payload,
            "uri",
        ),
        profile_url=_profile_url(
            payload
        ),
        image_url=_profile_image_url(
            payload
        ),
    )


class SpotifyWebApiClient:
    def __init__(
        self,
        *,
        urlopen=None,
        timeout_seconds: float = (
            DEFAULT_SPOTIFY_API_TIMEOUT_SECONDS
        ),
    ) -> None:
        self._urlopen = (
            _default_urlopen
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

    def _get_json(
        self,
        url: str,
        access_token: str,
    ) -> dict[str, Any]:
        if url != CURRENT_USER_PROFILE_URL:
            raise ValueError(
                "Unsupported Spotify API URL."
            )

        token = _validate_access_token(
            access_token
        )

        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": (
                    f"Bearer {token}"
                ),
                "User-Agent": (
                    SPOTIFY_API_USER_AGENT
                ),
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
                        response,
                        url,
                    )
                    != url
                ):
                    raise SpotifyWebApiError(
                        "untrusted_response",
                        (
                            "Spotify API response came "
                            "from an unexpected URL."
                        ),
                    )

                status = _response_status(
                    response
                )

                body = _read_limited_body(
                    response
                )

                if not 200 <= status <= 299:
                    _raise_http_error(
                        status,
                        headers=(
                            _response_headers(
                                response
                            )
                        ),
                        payload=(
                            _safe_error_payload(
                                body
                            )
                        ),
                    )

        except HTTPError as error:
            try:
                try:
                    body = error.read(
                        MAX_SPOTIFY_API_RESPONSE_BYTES
                        + 1
                    )

                except Exception:
                    body = b""

                if len(
                    body
                ) > MAX_SPOTIFY_API_RESPONSE_BYTES:
                    body = b""

                status = int(
                    getattr(
                        error,
                        "code",
                        0,
                    )
                    or 0
                )

                headers = getattr(
                    error,
                    "headers",
                    None,
                )

                payload = _safe_error_payload(
                    body
                )

            finally:
                try:
                    error.close()

                except Exception:
                    pass

            _raise_http_error(
                status,
                headers=headers,
                payload=payload,
            )

        except (
            socket.timeout,
            TimeoutError,
        ) as error:
            raise SpotifyWebApiError(
                "timeout",
                "Spotify API request timed out.",
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
                raise SpotifyWebApiError(
                    "timeout",
                    (
                        "Spotify API request "
                        "timed out."
                    ),
                ) from error

            raise SpotifyWebApiError(
                "network_error",
                "Could not reach Spotify.",
            ) from error

        return _decode_json_object(
            body
        )

    def get_current_user_profile(
        self,
        access_token: str,
    ) -> SpotifyAccount:
        payload = self._get_json(
            CURRENT_USER_PROFILE_URL,
            access_token,
        )

        return spotify_account_from_payload(
            payload
        )
