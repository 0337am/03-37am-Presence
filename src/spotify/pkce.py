from __future__ import annotations

import base64
from dataclasses import dataclass
from dataclasses import field
import hashlib
import secrets
import string

from src.spotify.constants import (
    SPOTIFY_PKCE_MAX_VERIFIER_LENGTH,
)
from src.spotify.constants import (
    SPOTIFY_PKCE_MIN_VERIFIER_LENGTH,
)


PKCE_ALLOWED_CHARACTERS = (
    string.ascii_letters
    + string.digits
    + "-._~"
)


@dataclass(
    frozen=True,
    slots=True,
)
class PkcePair:
    verifier: str = field(
        repr=False
    )
    challenge: str


def validate_code_verifier(
    verifier: str,
) -> str:
    if not isinstance(
        verifier,
        str,
    ):
        raise TypeError(
            "PKCE code verifier must be a string"
        )

    length = len(
        verifier
    )

    if not (
        SPOTIFY_PKCE_MIN_VERIFIER_LENGTH
        <= length
        <= SPOTIFY_PKCE_MAX_VERIFIER_LENGTH
    ):
        raise ValueError(
            "PKCE code verifier must contain "
            f"{SPOTIFY_PKCE_MIN_VERIFIER_LENGTH} to "
            f"{SPOTIFY_PKCE_MAX_VERIFIER_LENGTH} characters"
        )

    if any(
        character
        not in PKCE_ALLOWED_CHARACTERS
        for character in verifier
    ):
        raise ValueError(
            "PKCE code verifier contains an invalid character"
        )

    return verifier


def generate_code_verifier(
    length: int = 64,
) -> str:
    if (
        isinstance(
            length,
            bool,
        )
        or not isinstance(
            length,
            int,
        )
    ):
        raise TypeError(
            "PKCE verifier length must be an integer"
        )

    if not (
        SPOTIFY_PKCE_MIN_VERIFIER_LENGTH
        <= length
        <= SPOTIFY_PKCE_MAX_VERIFIER_LENGTH
    ):
        raise ValueError(
            "PKCE verifier length is outside the RFC 7636 range"
        )

    verifier = "".join(
        secrets.choice(
            PKCE_ALLOWED_CHARACTERS
        )
        for _ in range(
            length
        )
    )

    return validate_code_verifier(
        verifier
    )


def derive_code_challenge(
    verifier: str,
) -> str:
    checked = validate_code_verifier(
        verifier
    )

    digest = hashlib.sha256(
        checked.encode(
            "ascii"
        )
    ).digest()

    return (
        base64.urlsafe_b64encode(
            digest
        )
        .rstrip(
            b"="
        )
        .decode(
            "ascii"
        )
    )


def generate_pkce_pair(
    length: int = 64,
) -> PkcePair:
    verifier = generate_code_verifier(
        length
    )

    return PkcePair(
        verifier=verifier,
        challenge=derive_code_challenge(
            verifier
        ),
    )
