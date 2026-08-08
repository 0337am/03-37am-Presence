from __future__ import annotations

from collections.abc import Iterable


SPOTIFY_ACCOUNTS_BASE_URL = "https://accounts.spotify.com"
SPOTIFY_AUTHORIZE_URL = (
    f"{SPOTIFY_ACCOUNTS_BASE_URL}/authorize"
)
SPOTIFY_TOKEN_URL = (
    f"{SPOTIFY_ACCOUNTS_BASE_URL}/api/token"
)
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"

# Spotify application Client IDs are public identifiers.
# OAuth credentials and refresh tokens are never stored here.
SPOTIFY_PUBLIC_CLIENT_ID = (
    "2e081ef05a434508b7158732cb45cfaa"
)

SPOTIFY_LOOPBACK_HOST = "127.0.0.1"
SPOTIFY_CALLBACK_PORT = 43821
SPOTIFY_CALLBACK_PATH = "/callback"

# This exact loopback URI is registered in the Spotify Developer
# Dashboard. The desktop app must use the same fixed port.
SPOTIFY_LOOPBACK_REGISTRATION_URI = (
    f"http://{SPOTIFY_LOOPBACK_HOST}:"
    f"{SPOTIFY_CALLBACK_PORT}"
    f"{SPOTIFY_CALLBACK_PATH}"
)

SPOTIFY_PKCE_CHALLENGE_METHOD = "S256"
SPOTIFY_PKCE_MIN_VERIFIER_LENGTH = 43
SPOTIFY_PKCE_MAX_VERIFIER_LENGTH = 128

# Scopes are grouped by feature so the app can ask only for
# permissions belonging to features that are actually available.
SPOTIFY_SCOPE_USER_READ_PRIVATE = (
    "user-read-private"
)

SPOTIFY_SCOPE_USER_READ_PLAYBACK_STATE = (
    "user-read-playback-state"
)

SPOTIFY_SCOPE_USER_MODIFY_PLAYBACK_STATE = (
    "user-modify-playback-state"
)

SPOTIFY_SCOPE_USER_LIBRARY_READ = (
    "user-library-read"
)

SPOTIFY_SCOPE_PLAYLIST_READ_PRIVATE = (
    "playlist-read-private"
)

SPOTIFY_SCOPE_PLAYLIST_READ_COLLABORATIVE = (
    "playlist-read-collaborative"
)

SPOTIFY_SCOPE_USER_READ_RECENTLY_PLAYED = (
    "user-read-recently-played"
)

SPOTIFY_ACCOUNT_SCOPES = (
    SPOTIFY_SCOPE_USER_READ_PRIVATE,
)

SPOTIFY_PLAYBACK_READ_SCOPES = (
    SPOTIFY_SCOPE_USER_READ_PLAYBACK_STATE,
)

SPOTIFY_PLAYBACK_CONTROL_SCOPES = (
    SPOTIFY_SCOPE_USER_MODIFY_PLAYBACK_STATE,
)

SPOTIFY_LIBRARY_READ_SCOPES = (
    SPOTIFY_SCOPE_USER_LIBRARY_READ,
)

SPOTIFY_PLAYLIST_READ_SCOPES = (
    SPOTIFY_SCOPE_PLAYLIST_READ_PRIVATE,
    SPOTIFY_SCOPE_PLAYLIST_READ_COLLABORATIVE,
)

SPOTIFY_RECENTLY_PLAYED_SCOPES = (
    SPOTIFY_SCOPE_USER_READ_RECENTLY_PLAYED,
)

# Initial account connection deliberately asks for only the account
# permission. Later feature patches can combine their own groups.
SPOTIFY_CONNECT_SCOPES = SPOTIFY_ACCOUNT_SCOPES


def normalize_scopes(
    scopes: Iterable[str],
) -> tuple[str, ...]:
    if isinstance(
        scopes,
        str,
    ):
        raise TypeError(
            "scopes must be an iterable of scope names, not a string"
        )

    normalized: list[str] = []
    seen: set[str] = set()

    for raw_scope in scopes:
        if not isinstance(
            raw_scope,
            str,
        ):
            raise TypeError(
                "every Spotify scope must be a string"
            )

        scope = raw_scope.strip()

        if not scope:
            raise ValueError(
                "Spotify scopes cannot be empty"
            )

        if any(
            character.isspace()
            for character in scope
        ):
            raise ValueError(
                "each Spotify scope must be one token"
            )

        if scope in seen:
            continue

        seen.add(
            scope
        )
        normalized.append(
            scope
        )

    if not normalized:
        raise ValueError(
            "at least one Spotify scope is required"
        )

    return tuple(
        normalized
    )


def combine_scopes(
    *groups: Iterable[str],
) -> tuple[str, ...]:
    combined: list[str] = []

    for group in groups:
        if isinstance(
            group,
            str,
        ):
            raise TypeError(
                "scope groups must contain iterables, not strings"
            )

        combined.extend(
            group
        )

    return normalize_scopes(
        combined
    )


def build_loopback_redirect_uri(
    port: int,
) -> str:
    if (
        isinstance(
            port,
            bool,
        )
        or not isinstance(
            port,
            int,
        )
    ):
        raise TypeError(
            "Spotify callback port must be an integer"
        )

    if not 1 <= port <= 65535:
        raise ValueError(
            "Spotify callback port must be between 1 and 65535"
        )

    return (
        f"http://{SPOTIFY_LOOPBACK_HOST}:"
        f"{port}{SPOTIFY_CALLBACK_PATH}"
    )
