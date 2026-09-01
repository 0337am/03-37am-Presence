from __future__ import annotations

import urllib.parse

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
    "03-37am-Presence/3.3.0 Spotify-Web-API"
)

CURRENT_USER_PROFILE_URL = (
    f"{SPOTIFY_API_BASE_URL}/me"
)

START_PLAYBACK_PATH = (
    "/me/player/play"
)

PAUSE_PLAYBACK_PATH = (
    "/me/player/pause"
)

NEXT_PLAYBACK_PATH = (
    "/me/player/next"
)

PREVIOUS_PLAYBACK_PATH = (
    "/me/player/previous"
)

SEEK_PLAYBACK_PATH = (
    "/me/player/seek"
)


SHUFFLE_PLAYBACK_PATH = (
    "/me/player/shuffle"
)

REPEAT_PLAYBACK_PATH = (
    "/me/player/repeat"
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




MAX_SPOTIFY_API_URL_LENGTH = 8192


def _contains_control_character(
    value: str,
) -> bool:
    return any(
        ord(character) < 32
        or ord(character) == 127
        for character in value
    )


def _validate_spotify_api_path(
    path: str,
) -> str:
    if not isinstance(
        path,
        str,
    ):
        raise TypeError(
            "Spotify API path must be a string."
        )

    if (
        not path
        or path == "/"
    ):
        raise ValueError(
            "Spotify API path must identify an endpoint."
        )

    if (
        path != path.strip()
        or any(
            character.isspace()
            for character in path
        )
        or _contains_control_character(
            path
        )
    ):
        raise ValueError(
            "Spotify API path contains invalid characters."
        )

    if "\\" in path:
        raise ValueError(
            "Spotify API path cannot contain backslashes."
        )

    if (
        not path.startswith(
            "/"
        )
        or path.startswith(
            "//"
        )
    ):
        raise ValueError(
            (
                "Spotify API path must be an "
                "absolute API path without a host."
            )
        )

    try:
        path.encode(
            "ascii"
        )
    except UnicodeEncodeError as error:
        raise ValueError(
            "Spotify API path must use ASCII characters."
        ) from error

    try:
        parsed = urllib.parse.urlsplit(
            path
        )
    except ValueError as error:
        raise ValueError(
            "Spotify API path is malformed."
        ) from error

    if (
        parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            (
                "Spotify API path cannot include "
                "a scheme, host, query, or fragment."
            )
        )

    decoded_once = urllib.parse.unquote(
        parsed.path
    )

    decoded_twice = urllib.parse.unquote(
        decoded_once
    )

    for decoded in (
        decoded_once,
        decoded_twice,
    ):
        if (
            _contains_control_character(
                decoded
            )
            or any(
                character.isspace()
                for character in decoded
            )
        ):
            raise ValueError(
                (
                    "Spotify API path contains "
                    "invalid encoded characters."
                )
            )

        segments = decoded.split(
            "/"
        )

        if any(
            segment in {
                ".",
                "..",
            }
            for segment in segments
        ):
            raise ValueError(
                (
                    "Spotify API path cannot "
                    "contain traversal segments."
                )
            )

    return parsed.path


def _spotify_api_query_string(
    query: Mapping | None,
) -> str:
    if query is None:
        return ""

    if not isinstance(
        query,
        Mapping,
    ):
        raise TypeError(
            "Spotify API query must be a mapping or None."
        )

    pairs = []

    for key, value in query.items():
        if not isinstance(
            key,
            str,
        ):
            raise TypeError(
                "Spotify API query keys must be strings."
            )

        if (
            not key
            or not key.isascii()
            or any(
                not (
                    character.isalnum()
                    or character
                    in "_-."
                )
                for character in key
            )
        ):
            raise ValueError(
                "Spotify API query contains an invalid key."
            )

        if value is None:
            continue

        if isinstance(
            value,
            bool,
        ):
            rendered = (
                "true"
                if value
                else "false"
            )

        elif (
            isinstance(
                value,
                int,
            )
            and not isinstance(
                value,
                bool,
            )
        ):
            rendered = str(
                value
            )

        elif isinstance(
            value,
            str,
        ):
            rendered = value

        else:
            raise TypeError(
                (
                    "Spotify API query values must "
                    "be strings, integers, booleans, "
                    "or None."
                )
            )

        if _contains_control_character(
            rendered
        ):
            raise ValueError(
                (
                    "Spotify API query values cannot "
                    "contain control characters."
                )
            )

        pairs.append(
            (
                key,
                rendered,
            )
        )

    return urllib.parse.urlencode(
        pairs
    )


def _build_spotify_api_url(
    path: str,
    query: Mapping | None = None,
) -> str:
    safe_path = (
        _validate_spotify_api_path(
            path
        )
    )

    base_url = (
        SPOTIFY_API_BASE_URL.rstrip(
            "/"
        )
    )

    url = (
        base_url
        + safe_path
    )

    query_string = (
        _spotify_api_query_string(
            query
        )
    )

    if query_string:
        url = (
            url
            + "?"
            + query_string
        )

    if (
        len(
            url
        )
        > MAX_SPOTIFY_API_URL_LENGTH
    ):
        raise ValueError(
            "Spotify API request URL is too long."
        )

    base_parts = urllib.parse.urlsplit(
        base_url
    )

    request_parts = urllib.parse.urlsplit(
        url
    )

    required_path_prefix = (
        base_parts.path.rstrip(
            "/"
        )
        + "/"
    )

    if (
        request_parts.scheme
        != "https"
        or request_parts.scheme
        != base_parts.scheme
        or request_parts.netloc
        != base_parts.netloc
        or not request_parts.path.startswith(
            required_path_prefix
        )
    ):
        raise ValueError(
            "Spotify API request URL is outside the trusted API origin."
        )

    return url


def _validate_spotify_api_request_url(
    url: str,
) -> str:
    if not isinstance(
        url,
        str,
    ):
        raise TypeError(
            "Spotify API URL must be a string."
        )

    if (
        not url
        or url != url.strip()
        or _contains_control_character(
            url
        )
        or any(
            character.isspace()
            for character in url
        )
    ):
        raise ValueError(
            "Unsupported Spotify API URL."
        )

    if (
        len(
            url
        )
        > MAX_SPOTIFY_API_URL_LENGTH
    ):
        raise ValueError(
            "Spotify API request URL is too long."
        )

    try:
        request_parts = urllib.parse.urlsplit(
            url
        )

        base_url = (
            SPOTIFY_API_BASE_URL.rstrip(
                "/"
            )
        )

        base_parts = urllib.parse.urlsplit(
            base_url
        )

    except ValueError as error:
        raise ValueError(
            "Unsupported Spotify API URL."
        ) from error

    base_path = (
        base_parts.path.rstrip(
            "/"
        )
    )

    required_path_prefix = (
        base_path
        + "/"
    )

    if (
        request_parts.scheme
        != "https"
        or request_parts.scheme
        != base_parts.scheme
        or request_parts.netloc
        != base_parts.netloc
        or bool(
            request_parts.fragment
        )
        or not request_parts.path.startswith(
            required_path_prefix
        )
    ):
        raise ValueError(
            "Unsupported Spotify API URL."
        )

    endpoint_path = request_parts.path[
        len(
            base_path
        ):
    ]

    _validate_spotify_api_path(
        endpoint_path
    )

    return url


def _validate_spotify_track_uri(
    spotify_uri: str,
) -> str:
    if not isinstance(
        spotify_uri,
        str,
    ):
        raise TypeError(
            "Spotify track URI must be a string."
        )

    if (
        not spotify_uri
        or spotify_uri
        != spotify_uri.strip()
    ):
        raise ValueError(
            "Spotify track URI is invalid."
        )

    if any(
        character.isspace()
        or ord(character) < 32
        or ord(character) == 127
        for character in spotify_uri
    ):
        raise ValueError(
            "Spotify track URI is invalid."
        )

    prefix = (
        "spotify:track:"
    )

    if not spotify_uri.startswith(
        prefix
    ):
        raise ValueError(
            (
                "Playback requires a Spotify "
                "catalogue track URI."
            )
        )

    track_id = spotify_uri[
        len(prefix):
    ]

    if (
        not track_id
        or not track_id.isascii()
        or not track_id.isalnum()
    ):
        raise ValueError(
            "Spotify track URI is invalid."
        )

    return spotify_uri


def _validate_spotify_queue_item_uri(
    spotify_uri: str,
) -> str:
    if not isinstance(
        spotify_uri,
        str,
    ):
        raise TypeError(
            "Spotify queue item URI must be a string."
        )

    checked = spotify_uri.strip()

    if checked != spotify_uri:
        raise ValueError(
            "Spotify queue item URI is invalid."
        )

    for prefix in (
        "spotify:track:",
        "spotify:episode:",
    ):
        if not checked.startswith(
            prefix
        ):
            continue

        item_id = checked[
            len(prefix):
        ]

        if (
            item_id
            and item_id.isascii()
            and item_id.isalnum()
        ):
            return checked

        break

    raise ValueError(
        "Spotify queue item URI is invalid."
    )



def _validate_spotify_album_uri(
    spotify_uri: str,
) -> str:
    if not isinstance(
        spotify_uri,
        str,
    ):
        raise TypeError(
            "Spotify album URI must be a string."
        )

    checked = spotify_uri.strip()
    prefix = "spotify:album:"

    if (
        not checked.startswith(prefix)
        or checked != spotify_uri
    ):
        raise ValueError(
            "Spotify album URI is invalid."
        )

    album_id = checked[
        len(prefix):
    ]

    if (
        not album_id
        or not album_id.isascii()
        or not album_id.isalnum()
    ):
        raise ValueError(
            "Spotify album URI is invalid."
        )

    return checked


def _validate_spotify_playlist_uri(
    spotify_uri: str,
) -> str:
    if not isinstance(
        spotify_uri,
        str,
    ):
        raise TypeError(
            "Spotify playlist URI must be a string."
        )

    checked = spotify_uri.strip()

    prefix = "spotify:playlist:"

    if (
        not checked.startswith(prefix)
        or checked != spotify_uri
    ):
        raise ValueError(
            "Spotify playlist URI is invalid."
        )

    playlist_id = checked[
        len(prefix):
    ]

    if (
        not playlist_id
        or not playlist_id.isascii()
        or not playlist_id.isalnum()
    ):
        raise ValueError(
            "Spotify playlist URI is invalid."
        )

    return checked


def _validate_spotify_playlist_position(
    position,
) -> int:
    if (
        isinstance(
            position,
            bool,
        )
        or not isinstance(
            position,
            int,
        )
    ):
        raise TypeError(
            (
                "Spotify playlist position "
                "must be an integer."
            )
        )

    if position < 0:
        raise ValueError(
            (
                "Spotify playlist position "
                "cannot be negative."
            )
        )

    return position


def _validate_spotify_device_id(
    device_id,
) -> str:
    if not isinstance(
        device_id,
        str,
    ):
        raise TypeError(
            "Spotify device ID must be a string."
        )

    checked = device_id.strip()

    if (
        not checked
        or checked != device_id
        or len(checked) > 256
    ):
        raise ValueError(
            "Spotify device ID is invalid."
        )

    if any(
        character.isspace()
        or ord(character) < 32
        or ord(character) == 127
        for character in checked
    ):
        raise ValueError(
            "Spotify device ID is invalid."
        )

    return checked


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
        url = _validate_spotify_api_request_url(
            url
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

    def _put_json_no_content(
        self,
        url: str,
        access_token: str,
        payload,
    ) -> None:
        url = (
            _validate_spotify_api_request_url(
                url
            )
        )

        token = _validate_access_token(
            access_token
        )

        try:
            body = json.dumps(
                payload,
                ensure_ascii=True,
                separators=(
                    ",",
                    ":",
                ),
            ).encode(
                "utf-8"
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                (
                    "Spotify request payload "
                    "could not be encoded."
                )
            ) from error

        request = Request(
            url,
            data=body,
            method="PUT",
            headers={
                "Accept": "application/json",
                "Authorization": (
                    f"Bearer {token}"
                ),
                "Content-Type": (
                    "application/json"
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

                if 200 <= status <= 299:
                    return

                response_body = (
                    _read_limited_body(
                        response
                    )
                )

                _raise_http_error(
                    status,
                    headers=(
                        _response_headers(
                            response
                        )
                    ),
                    payload=(
                        _safe_error_payload(
                            response_body
                        )
                    ),
                )

        except HTTPError as error:
            try:
                try:
                    response_body = (
                        error.read(
                            MAX_SPOTIFY_API_RESPONSE_BYTES
                            + 1
                        )
                    )

                except Exception:
                    response_body = b""

                if (
                    len(
                        response_body
                    )
                    > MAX_SPOTIFY_API_RESPONSE_BYTES
                ):
                    response_body = b""

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

                payload = (
                    _safe_error_payload(
                        response_body
                    )
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
                (
                    "Spotify API request "
                    "timed out."
                ),
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

    def _request_no_content(
        self,
        url: str,
        access_token: str,
        *,
        method: str,
    ) -> None:
        url = (
            _validate_spotify_api_request_url(
                url
            )
        )

        token = _validate_access_token(
            access_token
        )

        if not isinstance(
            method,
            str,
        ):
            raise TypeError(
                (
                    "Spotify request method "
                    "must be a string."
                )
            )

        checked_method = (
            method.strip().upper()
        )

        if checked_method not in {
            "PUT",
            "POST",
        }:
            raise ValueError(
                (
                    "Spotify no-content "
                    "request method must "
                    "be PUT or POST."
                )
            )

        request = Request(
            url,
            method=checked_method,
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

                if 200 <= status <= 299:
                    return

                response_body = (
                    _read_limited_body(
                        response
                    )
                )

                _raise_http_error(
                    status,
                    headers=(
                        _response_headers(
                            response
                        )
                    ),
                    payload=(
                        _safe_error_payload(
                            response_body
                        )
                    ),
                )

        except HTTPError as error:
            try:
                try:
                    response_body = (
                        error.read(
                            MAX_SPOTIFY_API_RESPONSE_BYTES
                            + 1
                        )
                    )

                except Exception:
                    response_body = b""

                if (
                    len(
                        response_body
                    )
                    > MAX_SPOTIFY_API_RESPONSE_BYTES
                ):
                    response_body = b""

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

                payload = (
                    _safe_error_payload(
                        response_body
                    )
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
                (
                    "Spotify API request "
                    "timed out."
                ),
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

    def _playback_control_no_content(
        self,
        path: str,
        access_token: str,
        *,
        device_id: str | None = None,
        method: str,
    ) -> None:
        query = None

        if device_id is not None:
            query = {
                "device_id": (
                    _validate_spotify_device_id(
                        device_id
                    )
                ),
            }

        url = _build_spotify_api_url(
            path,
            query,
        )

        self._request_no_content(
            url,
            access_token,
            method=method,
        )

    def get_queue(
        self,
        access_token: str,
    ):
        return self.get_json(
            access_token,
            "/me/player/queue",
        )

    def add_to_queue(
        self,
        access_token: str,
        spotify_uri: str,
        *,
        device_id: str | None = None,
    ) -> None:
        checked_uri = (
            _validate_spotify_queue_item_uri(
                spotify_uri
            )
        )

        query = {
            "uri": checked_uri,
        }

        if device_id is not None:
            query["device_id"] = (
                _validate_spotify_device_id(
                    device_id
                )
            )

        url = _build_spotify_api_url(
            "/me/player/queue",
            query,
        )

        self._request_no_content(
            url,
            access_token,
            method="POST",
        )

    def resume_playback(
        self,
        access_token: str,
        *,
        device_id: str | None = None,
    ) -> None:
        self._playback_control_no_content(
            START_PLAYBACK_PATH,
            access_token,
            device_id=device_id,
            method="PUT",
        )

    def pause_playback(
        self,
        access_token: str,
        *,
        device_id: str | None = None,
    ) -> None:
        self._playback_control_no_content(
            PAUSE_PLAYBACK_PATH,
            access_token,
            device_id=device_id,
            method="PUT",
        )

    def skip_next(
        self,
        access_token: str,
        *,
        device_id: str | None = None,
    ) -> None:
        self._playback_control_no_content(
            NEXT_PLAYBACK_PATH,
            access_token,
            device_id=device_id,
            method="POST",
        )

    def skip_previous(
        self,
        access_token: str,
        *,
        device_id: str | None = None,
    ) -> None:
        self._playback_control_no_content(
            PREVIOUS_PLAYBACK_PATH,
            access_token,
            device_id=device_id,
            method="POST",
        )

    def set_shuffle(
        self,
        access_token: str,
        state: bool,
        *,
        device_id: str | None = None,
    ) -> None:
        if not isinstance(
            state,
            bool,
        ):
            raise TypeError(
                (
                    "Spotify shuffle state "
                    "must be a boolean."
                )
            )

        query = {
            "state": (
                "true"
                if state
                else "false"
            ),
        }

        if device_id is not None:
            query["device_id"] = (
                _validate_spotify_device_id(
                    device_id
                )
            )

        url = _build_spotify_api_url(
            SHUFFLE_PLAYBACK_PATH,
            query,
        )

        self._request_no_content(
            url,
            access_token,
            method="PUT",
        )

    def set_repeat_mode(
        self,
        access_token: str,
        state: str,
        *,
        device_id: str | None = None,
    ) -> None:
        if not isinstance(
            state,
            str,
        ):
            raise TypeError(
                (
                    "Spotify repeat state "
                    "must be a string."
                )
            )

        checked = state.strip()

        if (
            checked != state
            or checked
            not in {
                "off",
                "context",
                "track",
            }
        ):
            raise ValueError(
                "Spotify repeat state is invalid."
            )

        query = {
            "state": checked,
        }

        if device_id is not None:
            query["device_id"] = (
                _validate_spotify_device_id(
                    device_id
                )
            )

        url = _build_spotify_api_url(
            REPEAT_PLAYBACK_PATH,
            query,
        )

        self._request_no_content(
            url,
            access_token,
            method="PUT",
        )

    def seek_to_position(
        self,
        access_token: str,
        position_ms: int,
        *,
        device_id: str | None = None,
    ) -> None:
        if isinstance(
            position_ms,
            bool,
        ) or not isinstance(
            position_ms,
            int,
        ):
            raise TypeError(
                "position_ms must be an integer"
            )

        if position_ms < 0:
            raise ValueError(
                "position_ms cannot be negative"
            )

        query = {
            "position_ms": position_ms,
        }

        if device_id is not None:
            query["device_id"] = (
                _validate_spotify_device_id(
                    device_id
                )
            )

        url = _build_spotify_api_url(
            SEEK_PLAYBACK_PATH,
            query,
        )

        self._request_no_content(
            url,
            access_token,
            method="PUT",
        )

    def start_playback(
        self,
        access_token: str,
        spotify_uri: str,
        *,
        device_id: str | None = None,
    ) -> None:
        uri = (
            _validate_spotify_track_uri(
                spotify_uri
            )
        )

        query = None

        if device_id is not None:
            query = {
                "device_id": (
                    _validate_spotify_device_id(
                        device_id
                    )
                ),
            }

        url = _build_spotify_api_url(
            START_PLAYBACK_PATH,
            query,
        )

        self._put_json_no_content(
            url,
            access_token,
            {
                "uris": [
                    uri,
                ],
            },
        )

    def start_album_playback(
        self,
        access_token: str,
        album_uri: str,
        spotify_uri: str,
        *,
        device_id: str | None = None,
    ) -> None:
        context_uri = (
            _validate_spotify_album_uri(
                album_uri
            )
        )

        track_uri = (
            _validate_spotify_track_uri(
                spotify_uri
            )
        )

        query = None

        if device_id is not None:
            query = {
                "device_id": (
                    _validate_spotify_device_id(
                        device_id
                    )
                ),
            }

        url = _build_spotify_api_url(
            START_PLAYBACK_PATH,
            query,
        )

        self._put_json_no_content(
            url,
            access_token,
            {
                "context_uri": context_uri,
                "offset": {
                    "uri": track_uri,
                },
            },
        )

    def start_playlist_playback(
        self,
        access_token: str,
        playlist_uri: str,
        spotify_uri: str,
        *,
        device_id: str | None = None,
    ) -> None:
        context_uri = (
            _validate_spotify_playlist_uri(
                playlist_uri
            )
        )

        track_uri = (
            _validate_spotify_track_uri(
                spotify_uri
            )
        )

        query = None

        if device_id is not None:
            query = {
                "device_id": (
                    _validate_spotify_device_id(
                        device_id
                    )
                ),
            }

        url = _build_spotify_api_url(
            START_PLAYBACK_PATH,
            query,
        )

        self._put_json_no_content(
            url,
            access_token,
            {
                "context_uri": context_uri,
                "offset": {
                    "uri": track_uri,
                },
            },
        )

    def start_playlist_position_playback(
        self,
        access_token: str,
        playlist_uri: str,
        position: int,
        *,
        device_id: str | None = None,
    ) -> None:
        context_uri = (
            _validate_spotify_playlist_uri(
                playlist_uri
            )
        )

        playlist_position = (
            _validate_spotify_playlist_position(
                position
            )
        )

        query = None

        if device_id is not None:
            query = {
                "device_id": (
                    _validate_spotify_device_id(
                        device_id
                    )
                ),
            }

        url = _build_spotify_api_url(
            START_PLAYBACK_PATH,
            query,
        )

        self._put_json_no_content(
            url,
            access_token,
            {
                "context_uri": context_uri,
                "offset": {
                    "position": (
                        playlist_position
                    ),
                },
                "position_ms": 0,
            },
        )

    def get_available_devices(
        self,
        access_token: str,
    ) -> dict[str, Any]:
        return self.get_json(
            access_token,
            "/me/player/devices",
        )

    def get_json(
        self,
        access_token: str,
        path: str,
        *,
        query: Mapping | None = None,
    ) -> dict[str, Any]:
        url = _build_spotify_api_url(
            path,
            query,
        )

        return self._get_json(
            url,
            access_token,
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
