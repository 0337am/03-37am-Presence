from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import json
import math
import os
from pathlib import Path
import time
import uuid

from src.spotify.models import (
    SpotifyTokenBundle,
)
from src.spotify.windows_dpapi import (
    WindowsDpapiError,
)
from src.spotify.windows_dpapi import (
    protect_data,
)
from src.spotify.windows_dpapi import (
    unprotect_data,
)


SPOTIFY_CREDENTIAL_SCHEMA = 1

SPOTIFY_CREDENTIAL_KIND = (
    "spotify_oauth_token"
)

SPOTIFY_CREDENTIAL_DIRECTORY = (
    "0337am Presence"
)

SPOTIFY_CREDENTIAL_FILENAME = (
    "spotify_auth.dat"
)

MAX_SPOTIFY_CREDENTIAL_BYTES = (
    256 * 1024
)


class SpotifyCredentialStoreError(
    RuntimeError
):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        quarantine_path: Path | None = None,
    ) -> None:
        super().__init__(
            message
        )

        self.error_code = error_code
        self.message = message
        self.quarantine_path = (
            quarantine_path
        )


class _CredentialPayloadError(
    ValueError
):
    pass


def default_spotify_credential_path(
    local_app_data: str | os.PathLike | None = None,
) -> Path:
    if local_app_data is None:
        local_app_data = os.environ.get(
            "LOCALAPPDATA",
            "",
        )

    if isinstance(
        local_app_data,
        os.PathLike,
    ):
        local_app_data = os.fspath(
            local_app_data
        )

    if not isinstance(
        local_app_data,
        str,
    ):
        raise TypeError(
            "LOCALAPPDATA path must be a string or path."
        )

    checked = local_app_data.strip()

    if not checked:
        raise SpotifyCredentialStoreError(
            "local_app_data_unavailable",
            (
                "The local application data directory "
                "is unavailable."
            ),
        )

    return (
        Path(
            checked
        )
        / SPOTIFY_CREDENTIAL_DIRECTORY
        / SPOTIFY_CREDENTIAL_FILENAME
    )


def _is_finite_number(
    value,
) -> bool:
    return (
        not isinstance(
            value,
            bool,
        )
        and isinstance(
            value,
            (
                int,
                float,
            ),
        )
        and math.isfinite(
            float(
                value
            )
        )
    )


def _token_payload(
    token: SpotifyTokenBundle,
) -> dict:
    if not isinstance(
        token,
        SpotifyTokenBundle,
    ):
        raise TypeError(
            "token must be a SpotifyTokenBundle"
        )

    return {
        "schema": (
            SPOTIFY_CREDENTIAL_SCHEMA
        ),
        "kind": (
            SPOTIFY_CREDENTIAL_KIND
        ),
        "token": {
            "access_token": (
                token.access_token
            ),
            "refresh_token": (
                token.refresh_token
            ),
            "token_type": (
                token.token_type
            ),
            "expires_in": (
                token.expires_in
            ),
            "granted_scopes": list(
                token.granted_scopes
            ),
            "obtained_at": (
                token.obtained_at
            ),
            "authorized_at": (
                token.authorized_at
            ),
        },
    }


def _encode_token(
    token: SpotifyTokenBundle,
) -> bytes:
    payload = _token_payload(
        token
    )

    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise SpotifyCredentialStoreError(
            "serialize_failed",
            (
                "Spotify credentials could not "
                "be prepared for secure storage."
            ),
        ) from None

    return text.encode(
        "utf-8"
    )


def _require_exact_keys(
    mapping: dict,
    expected: set[str],
) -> None:
    if set(
        mapping.keys()
    ) != expected:
        raise _CredentialPayloadError(
            "Unexpected credential fields."
        )


def _decode_token(
    plaintext: bytes,
) -> SpotifyTokenBundle:
    if not isinstance(
        plaintext,
        bytes,
    ):
        raise _CredentialPayloadError(
            "Credential payload is not bytes."
        )

    if not plaintext:
        raise _CredentialPayloadError(
            "Credential payload is empty."
        )

    try:
        payload = json.loads(
            plaintext.decode(
                "utf-8"
            )
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise _CredentialPayloadError(
            "Credential payload is invalid."
        ) from None

    if not isinstance(
        payload,
        dict,
    ):
        raise _CredentialPayloadError(
            "Credential payload is not an object."
        )

    _require_exact_keys(
        payload,
        {
            "schema",
            "kind",
            "token",
        },
    )

    schema = payload[
        "schema"
    ]

    if (
        isinstance(
            schema,
            bool,
        )
        or not isinstance(
            schema,
            int,
        )
        or schema
        != SPOTIFY_CREDENTIAL_SCHEMA
    ):
        raise _CredentialPayloadError(
            "Unsupported credential schema."
        )

    if (
        payload[
            "kind"
        ]
        != SPOTIFY_CREDENTIAL_KIND
    ):
        raise _CredentialPayloadError(
            "Unexpected credential kind."
        )

    token_data = payload[
        "token"
    ]

    if not isinstance(
        token_data,
        dict,
    ):
        raise _CredentialPayloadError(
            "Credential token is not an object."
        )

    _require_exact_keys(
        token_data,
        {
            "access_token",
            "refresh_token",
            "token_type",
            "expires_in",
            "granted_scopes",
            "obtained_at",
            "authorized_at",
        },
    )

    access_token = token_data[
        "access_token"
    ]

    refresh_token = token_data[
        "refresh_token"
    ]

    token_type = token_data[
        "token_type"
    ]

    expires_in = token_data[
        "expires_in"
    ]

    granted_scopes = token_data[
        "granted_scopes"
    ]

    obtained_at = token_data[
        "obtained_at"
    ]

    authorized_at = token_data[
        "authorized_at"
    ]

    if (
        not isinstance(
            access_token,
            str,
        )
        or not access_token
    ):
        raise _CredentialPayloadError(
            "Access token is invalid."
        )

    if (
        refresh_token is not None
        and (
            not isinstance(
                refresh_token,
                str,
            )
            or not refresh_token
        )
    ):
        raise _CredentialPayloadError(
            "Refresh token is invalid."
        )

    if (
        not isinstance(
            token_type,
            str,
        )
        or not token_type
    ):
        raise _CredentialPayloadError(
            "Token type is invalid."
        )

    if (
        isinstance(
            expires_in,
            bool,
        )
        or not isinstance(
            expires_in,
            int,
        )
        or expires_in <= 0
    ):
        raise _CredentialPayloadError(
            "Token lifetime is invalid."
        )

    if not isinstance(
        granted_scopes,
        list,
    ):
        raise _CredentialPayloadError(
            "Granted scopes are invalid."
        )

    if any(
        not isinstance(
            scope,
            str,
        )
        or not scope
        for scope in granted_scopes
    ):
        raise _CredentialPayloadError(
            "Granted scopes are invalid."
        )

    if len(
        set(
            granted_scopes
        )
    ) != len(
        granted_scopes
    ):
        raise _CredentialPayloadError(
            "Granted scopes contain duplicates."
        )

    if not _is_finite_number(
        obtained_at
    ):
        raise _CredentialPayloadError(
            "Token acquisition time is invalid."
        )

    if not _is_finite_number(
        authorized_at
    ):
        raise _CredentialPayloadError(
            "Authorization time is invalid."
        )

    try:
        return SpotifyTokenBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            expires_in=expires_in,
            granted_scopes=tuple(
                granted_scopes
            ),
            obtained_at=float(
                obtained_at
            ),
            authorized_at=float(
                authorized_at
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        raise _CredentialPayloadError(
            "Credential token model is invalid."
        ) from None


class SpotifyCredentialStore:
    def __init__(
        self,
        path: str | os.PathLike | None = None,
        *,
        protect_fn: Callable[
            [bytes],
            bytes,
        ] = protect_data,
        unprotect_fn: Callable[
            [bytes],
            bytes,
        ] = unprotect_data,
        replace_fn: Callable = os.replace,
        clock: Callable[
            [],
            float,
        ] = time.time,
    ) -> None:
        if path is None:
            checked_path = (
                default_spotify_credential_path()
            )
        else:
            checked_path = Path(
                path
            )

        if not callable(
            protect_fn
        ):
            raise TypeError(
                "protect_fn must be callable"
            )

        if not callable(
            unprotect_fn
        ):
            raise TypeError(
                "unprotect_fn must be callable"
            )

        if not callable(
            replace_fn
        ):
            raise TypeError(
                "replace_fn must be callable"
            )

        if not callable(
            clock
        ):
            raise TypeError(
                "clock must be callable"
            )

        self._path = checked_path
        self._protect_fn = protect_fn
        self._unprotect_fn = (
            unprotect_fn
        )
        self._replace_fn = replace_fn
        self._clock = clock

    @property
    def path(
        self,
    ) -> Path:
        return self._path

    @property
    def exists(
        self,
    ) -> bool:
        return self._path.is_file()

    def _quarantine_existing(
        self,
    ) -> Path | None:
        if not self._path.exists():
            return None

        try:
            timestamp = datetime.fromtimestamp(
                float(
                    self._clock()
                )
            ).strftime(
                "%Y%m%d-%H%M%S"
            )
        except Exception:
            timestamp = (
                "unknown-time"
            )

        base_name = (
            "spotify_auth.invalid-"
            f"{timestamp}"
        )

        candidate = (
            self._path.parent
            / f"{base_name}.dat"
        )

        suffix = 1

        while candidate.exists():
            candidate = (
                self._path.parent
                / (
                    f"{base_name}-"
                    f"{suffix}.dat"
                )
            )

            suffix += 1

        try:
            os.replace(
                self._path,
                candidate,
            )
        except FileNotFoundError:
            return None
        except OSError:
            raise SpotifyCredentialStoreError(
                "quarantine_failed",
                (
                    "Invalid Spotify credentials "
                    "could not be quarantined."
                ),
            ) from None

        return candidate

    def _raise_corrupt(
        self,
    ) -> None:
        quarantine_path = (
            self._quarantine_existing()
        )

        raise SpotifyCredentialStoreError(
            "credential_corrupt",
            (
                "Saved Spotify credentials are invalid. "
                "Spotify must be connected again."
            ),
            quarantine_path=(
                quarantine_path
            ),
        ) from None

    def save(
        self,
        token: SpotifyTokenBundle,
    ) -> Path:
        plaintext = _encode_token(
            token
        )

        try:
            protected = self._protect_fn(
                plaintext
            )
        except WindowsDpapiError:
            raise SpotifyCredentialStoreError(
                "protection_failed",
                (
                    "Spotify credentials could not "
                    "be protected by Windows."
                ),
            ) from None

        if (
            not isinstance(
                protected,
                bytes,
            )
            or not protected
        ):
            raise SpotifyCredentialStoreError(
                "protection_failed",
                (
                    "Windows returned invalid protected "
                    "Spotify credentials."
                ),
            )

        if len(
            protected
        ) > MAX_SPOTIFY_CREDENTIAL_BYTES:
            raise SpotifyCredentialStoreError(
                "credential_too_large",
                (
                    "Protected Spotify credentials "
                    "are unexpectedly large."
                ),
            )

        parent = self._path.parent

        try:
            parent.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError:
            raise SpotifyCredentialStoreError(
                "directory_failed",
                (
                    "Spotify credential storage "
                    "could not be prepared."
                ),
            ) from None

        temporary_path = (
            parent
            / (
                f".{self._path.name}."
                f"{uuid.uuid4().hex}.tmp"
            )
        )

        try:
            with temporary_path.open(
                "xb"
            ) as handle:
                handle.write(
                    protected
                )

                handle.flush()

                os.fsync(
                    handle.fileno()
                )

            self._replace_fn(
                temporary_path,
                self._path,
            )

        except OSError:
            try:
                temporary_path.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

            raise SpotifyCredentialStoreError(
                "save_failed",
                (
                    "Spotify credentials could not "
                    "be saved safely."
                ),
            ) from None

        return self._path

    def load(
        self,
    ) -> SpotifyTokenBundle | None:
        try:
            size = self._path.stat().st_size
        except FileNotFoundError:
            return None
        except OSError:
            raise SpotifyCredentialStoreError(
                "load_failed",
                (
                    "Saved Spotify credentials "
                    "could not be read."
                ),
            ) from None

        if (
            size <= 0
            or size > MAX_SPOTIFY_CREDENTIAL_BYTES
        ):
            self._raise_corrupt()

        try:
            protected = self._path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError:
            raise SpotifyCredentialStoreError(
                "load_failed",
                (
                    "Saved Spotify credentials "
                    "could not be read."
                ),
            ) from None

        if (
            not protected
            or len(
                protected
            ) > MAX_SPOTIFY_CREDENTIAL_BYTES
        ):
            self._raise_corrupt()

        try:
            plaintext = self._unprotect_fn(
                protected
            )
        except WindowsDpapiError:
            self._raise_corrupt()

        try:
            token = _decode_token(
                plaintext
            )
        except _CredentialPayloadError:
            self._raise_corrupt()

        return token

    def delete(
        self,
    ) -> bool:
        try:
            self._path.unlink()
        except FileNotFoundError:
            return False
        except OSError:
            raise SpotifyCredentialStoreError(
                "delete_failed",
                (
                    "Saved Spotify credentials "
                    "could not be removed."
                ),
            ) from None

        return True
