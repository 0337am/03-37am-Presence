from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from dataclasses import field
import secrets
import string
from urllib.parse import parse_qs
from urllib.parse import urlencode
from urllib.parse import urlsplit

from src.spotify.constants import (
    SPOTIFY_AUTHORIZE_URL,
)
from src.spotify.constants import (
    SPOTIFY_CALLBACK_PATH,
)
from src.spotify.constants import (
    SPOTIFY_CONNECT_SCOPES,
)
from src.spotify.constants import (
    SPOTIFY_LOOPBACK_HOST,
)
from src.spotify.constants import (
    SPOTIFY_PKCE_CHALLENGE_METHOD,
)
from src.spotify.constants import normalize_scopes
from src.spotify.pkce import (
    derive_code_challenge,
)
from src.spotify.pkce import (
    generate_code_verifier,
)
from src.spotify.pkce import (
    validate_code_verifier,
)


OAUTH_STATE_MIN_CHARACTERS = 32
OAUTH_STATE_MAX_CHARACTERS = 256
OAUTH_STATE_MIN_RANDOM_BYTES = 24
OAUTH_STATE_MAX_RANDOM_BYTES = 128

OAUTH_STATE_ALLOWED_CHARACTERS = (
    string.ascii_letters
    + string.digits
    + "-_"
)


class OAuthValidationError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class AuthorizationRequest:
    url: str = field(
        repr=False
    )
    client_id: str
    redirect_uri: str
    state: str = field(
        repr=False
    )
    code_verifier: str = field(
        repr=False
    )
    code_challenge: str = ""
    scopes: tuple[str, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class AuthorizationCallback:
    code: str = field(
        default="",
        repr=False,
    )
    state: str = field(
        default="",
        repr=False,
    )
    error: str = ""
    error_description: str = ""

    @property
    def approved(
        self,
    ) -> bool:
        return bool(
            self.code
        ) and not bool(
            self.error
        )

    @property
    def denied(
        self,
    ) -> bool:
        return bool(
            self.error
        )


def validate_oauth_state(
    state: str,
) -> str:
    if not isinstance(
        state,
        str,
    ):
        raise TypeError(
            "OAuth state must be a string"
        )

    if not (
        OAUTH_STATE_MIN_CHARACTERS
        <= len(
            state
        )
        <= OAUTH_STATE_MAX_CHARACTERS
    ):
        raise OAuthValidationError(
            "OAuth state has an unsafe length"
        )

    if any(
        character
        not in OAUTH_STATE_ALLOWED_CHARACTERS
        for character in state
    ):
        raise OAuthValidationError(
            "OAuth state contains an invalid character"
        )

    return state


def generate_oauth_state(
    random_bytes: int = 32,
) -> str:
    if (
        isinstance(
            random_bytes,
            bool,
        )
        or not isinstance(
            random_bytes,
            int,
        )
    ):
        raise TypeError(
            "OAuth state entropy size must be an integer"
        )

    if not (
        OAUTH_STATE_MIN_RANDOM_BYTES
        <= random_bytes
        <= OAUTH_STATE_MAX_RANDOM_BYTES
    ):
        raise ValueError(
            "OAuth state entropy size is outside the safe range"
        )

    state = secrets.token_urlsafe(
        random_bytes
    )

    return validate_oauth_state(
        state
    )


def validate_loopback_redirect_uri(
    redirect_uri: str,
    *,
    require_port: bool = True,
) -> str:
    if not isinstance(
        redirect_uri,
        str,
    ):
        raise TypeError(
            "Spotify redirect URI must be a string"
        )

    if not redirect_uri:
        raise OAuthValidationError(
            "Spotify redirect URI cannot be empty"
        )

    try:
        parts = urlsplit(
            redirect_uri
        )
        port = parts.port
    except ValueError as error:
        raise OAuthValidationError(
            "Spotify redirect URI contains an invalid port"
        ) from error

    if parts.scheme != "http":
        raise OAuthValidationError(
            "Spotify loopback redirect must use HTTP"
        )

    if parts.hostname != SPOTIFY_LOOPBACK_HOST:
        raise OAuthValidationError(
            "Spotify redirect must use explicit 127.0.0.1"
        )

    if (
        parts.username is not None
        or parts.password is not None
    ):
        raise OAuthValidationError(
            "Spotify redirect URI cannot contain credentials"
        )

    if parts.path != SPOTIFY_CALLBACK_PATH:
        raise OAuthValidationError(
            "Spotify redirect URI has an unexpected callback path"
        )

    if parts.query:
        raise OAuthValidationError(
            "Spotify redirect URI cannot contain a query string"
        )

    if parts.fragment:
        raise OAuthValidationError(
            "Spotify redirect URI cannot contain a fragment"
        )

    if (
        require_port
        and port is None
    ):
        raise OAuthValidationError(
            "Spotify authorization redirect requires a callback port"
        )

    expected_netloc = (
        SPOTIFY_LOOPBACK_HOST
        if port is None
        else (
            f"{SPOTIFY_LOOPBACK_HOST}:"
            f"{port}"
        )
    )

    if parts.netloc != expected_netloc:
        raise OAuthValidationError(
            "Spotify redirect URI has an unexpected authority"
        )

    return redirect_uri


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

    cleaned = client_id.strip()

    if not cleaned:
        raise OAuthValidationError(
            "Spotify client ID cannot be empty"
        )

    if any(
        character.isspace()
        for character in cleaned
    ):
        raise OAuthValidationError(
            "Spotify client ID cannot contain whitespace"
        )

    return cleaned


def build_authorization_request(
    client_id: str,
    redirect_uri: str,
    *,
    scopes: Iterable[str] = SPOTIFY_CONNECT_SCOPES,
    state: str | None = None,
    code_verifier: str | None = None,
) -> AuthorizationRequest:
    checked_client_id = _validate_client_id(
        client_id
    )

    checked_redirect_uri = (
        validate_loopback_redirect_uri(
            redirect_uri,
            require_port=True,
        )
    )

    checked_scopes = normalize_scopes(
        scopes
    )

    checked_state = (
        generate_oauth_state()
        if state is None
        else validate_oauth_state(
            state
        )
    )

    checked_verifier = (
        generate_code_verifier()
        if code_verifier is None
        else validate_code_verifier(
            code_verifier
        )
    )

    challenge = derive_code_challenge(
        checked_verifier
    )

    parameters = (
        (
            "client_id",
            checked_client_id,
        ),
        (
            "response_type",
            "code",
        ),
        (
            "redirect_uri",
            checked_redirect_uri,
        ),
        (
            "state",
            checked_state,
        ),
        (
            "scope",
            " ".join(
                checked_scopes
            ),
        ),
        (
            "code_challenge_method",
            SPOTIFY_PKCE_CHALLENGE_METHOD,
        ),
        (
            "code_challenge",
            challenge,
        ),
    )

    url = (
        f"{SPOTIFY_AUTHORIZE_URL}?"
        f"{urlencode(parameters)}"
    )

    return AuthorizationRequest(
        url=url,
        client_id=checked_client_id,
        redirect_uri=checked_redirect_uri,
        state=checked_state,
        code_verifier=checked_verifier,
        code_challenge=challenge,
        scopes=checked_scopes,
    )


def _single_query_value(
    parameters: dict[str, list[str]],
    name: str,
) -> str | None:
    values = parameters.get(
        name,
        []
    )

    if len(
        values
    ) > 1:
        raise OAuthValidationError(
            f"Spotify callback contains duplicate {name!r}"
        )

    if not values:
        return None

    return values[0]


def parse_authorization_callback(
    callback_url: str,
    *,
    expected_redirect_uri: str,
    expected_state: str,
) -> AuthorizationCallback:
    if not isinstance(
        callback_url,
        str,
    ):
        raise TypeError(
            "Spotify callback URL must be a string"
        )

    checked_redirect_uri = (
        validate_loopback_redirect_uri(
            expected_redirect_uri,
            require_port=True,
        )
    )

    checked_state = validate_oauth_state(
        expected_state
    )

    expected = urlsplit(
        checked_redirect_uri
    )

    try:
        actual = urlsplit(
            callback_url
        )
        actual_port = actual.port
    except ValueError as error:
        raise OAuthValidationError(
            "Spotify callback contains an invalid port"
        ) from error

    if (
        actual.username is not None
        or actual.password is not None
    ):
        raise OAuthValidationError(
            "Spotify callback cannot contain credentials"
        )

    if actual.fragment:
        raise OAuthValidationError(
            "Spotify callback cannot contain a fragment"
        )

    if (
        actual.scheme != expected.scheme
        or actual.hostname != expected.hostname
        or actual_port != expected.port
        or actual.path != expected.path
    ):
        raise OAuthValidationError(
            "Spotify callback target does not match the expected redirect"
        )

    parameters = parse_qs(
        actual.query,
        keep_blank_values=True,
    )

    returned_state = _single_query_value(
        parameters,
        "state",
    )

    if returned_state is None:
        raise OAuthValidationError(
            "Spotify callback did not return OAuth state"
        )

    if not secrets.compare_digest(
        returned_state,
        checked_state,
    ):
        raise OAuthValidationError(
            "Spotify callback OAuth state does not match"
        )

    code = _single_query_value(
        parameters,
        "code",
    )

    error = _single_query_value(
        parameters,
        "error",
    )

    error_description = _single_query_value(
        parameters,
        "error_description",
    )

    if (
        code is not None
        and error is not None
    ):
        raise OAuthValidationError(
            "Spotify callback cannot contain both code and error"
        )

    if error is not None:
        if not error.strip():
            raise OAuthValidationError(
                "Spotify callback returned an empty error"
            )

        return AuthorizationCallback(
            state=returned_state,
            error=error,
            error_description=(
                error_description
                or ""
            ),
        )

    if error_description is not None:
        raise OAuthValidationError(
            "Spotify callback returned an error description without an error"
        )

    if (
        code is None
        or not code.strip()
    ):
        raise OAuthValidationError(
            "Spotify callback did not return an authorization code"
        )

    return AuthorizationCallback(
        code=code,
        state=returned_state,
    )
