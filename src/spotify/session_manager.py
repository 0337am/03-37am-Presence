from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
import math
from numbers import Real
import time

from src.spotify.credential_store import (
    SpotifyCredentialStore,
)
from src.spotify.credential_store import (
    SpotifyCredentialStoreError,
)
from src.spotify.models import (
    SpotifyTokenBundle,
)
from src.spotify.token_client import (
    SpotifyTokenClient,
)
from src.spotify.token_client import (
    SpotifyTokenError,
)


DEFAULT_REFRESH_SKEW_SECONDS = 60.0


class SpotifySessionStatus(
    str,
    Enum,
):
    DISCONNECTED = "disconnected"
    READY = "ready"
    REFRESHED = "refreshed"
    REAUTHORIZATION_REQUIRED = (
        "reauthorization_required"
    )


class SpotifySessionManagerError(
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
class SpotifySessionResult:
    status: SpotifySessionStatus
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
            SpotifySessionStatus,
        ):
            raise TypeError(
                "status must be a SpotifySessionStatus"
            )

        connected_statuses = {
            SpotifySessionStatus.READY,
            SpotifySessionStatus.REFRESHED,
        }

        if self.status in connected_statuses:
            if not isinstance(
                self.token,
                SpotifyTokenBundle,
            ):
                raise ValueError(
                    "Connected Spotify session requires a token."
                )
        elif self.token is not None:
            raise ValueError(
                "Disconnected Spotify session cannot contain a token."
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
            SpotifySessionStatus.READY,
            SpotifySessionStatus.REFRESHED,
        }

    @property
    def refreshed(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifySessionStatus.REFRESHED
        )

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifySessionStatus.REAUTHORIZATION_REQUIRED
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


def _validate_refresh_skew(
    refresh_skew_seconds: float,
) -> float:
    if (
        isinstance(
            refresh_skew_seconds,
            bool,
        )
        or not isinstance(
            refresh_skew_seconds,
            Real,
        )
    ):
        raise TypeError(
            "refresh skew must be a number"
        )

    checked = float(
        refresh_skew_seconds
    )

    if (
        not math.isfinite(
            checked
        )
        or checked < 0
    ):
        raise ValueError(
            "refresh skew must be a finite non-negative number"
        )

    return checked


def _safe_clock_value(
    clock: Callable[
        [],
        float,
    ],
) -> float:
    try:
        value = clock()
    except Exception as error:
        raise SpotifySessionManagerError(
            "clock_failed",
            (
                "Spotify session timing could not "
                "be determined."
            ),
        ) from error

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
        raise SpotifySessionManagerError(
            "clock_failed",
            (
                "Spotify session timing could not "
                "be determined."
            ),
        )

    checked = float(
        value
    )

    if not math.isfinite(
        checked
    ):
        raise SpotifySessionManagerError(
            "clock_failed",
            (
                "Spotify session timing could not "
                "be determined."
            ),
        )

    return checked


def _token_needs_refresh(
    token: SpotifyTokenBundle,
    *,
    now: float,
    refresh_skew_seconds: float,
) -> bool:
    expires_at = (
        float(
            token.obtained_at
        )
        + float(
            token.expires_in
        )
    )

    return (
        now
        >= (
            expires_at
            - refresh_skew_seconds
        )
    )


class SpotifySessionManager:
    def __init__(
        self,
        client_id: str,
        *,
        store=None,
        token_client=None,
        clock: Callable[
            [],
            float,
        ] = time.time,
        refresh_skew_seconds: float = (
            DEFAULT_REFRESH_SKEW_SECONDS
        ),
    ) -> None:
        self._client_id = _validate_client_id(
            client_id
        )

        if store is None:
            store = SpotifyCredentialStore()

        for method_name in (
            "load",
            "save",
            "delete",
        ):
            method = getattr(
                store,
                method_name,
                None,
            )

            if not callable(
                method
            ):
                raise TypeError(
                    "store must provide load(), "
                    "save(), and delete()"
                )

        if token_client is None:
            token_client = SpotifyTokenClient(
                self._client_id
            )

        refresh_method = getattr(
            token_client,
            "refresh_access_token",
            None,
        )

        if not callable(
            refresh_method
        ):
            raise TypeError(
                "token_client must provide "
                "refresh_access_token()"
            )

        if not callable(
            clock
        ):
            raise TypeError(
                "clock must be callable"
            )

        self._store = store
        self._token_client = token_client
        self._clock = clock
        self._refresh_skew_seconds = (
            _validate_refresh_skew(
                refresh_skew_seconds
            )
        )

    @property
    def refresh_skew_seconds(
        self,
    ) -> float:
        return self._refresh_skew_seconds

    def _delete_unusable_credentials(
        self,
    ) -> None:
        try:
            self._store.delete()
        except SpotifyCredentialStoreError:
            raise SpotifySessionManagerError(
                "credential_delete_failed",
                (
                    "Unusable Spotify credentials "
                    "could not be removed."
                ),
            ) from None

    def persist_authorized_token(
        self,
        token: SpotifyTokenBundle,
    ) -> SpotifySessionResult:
        if not isinstance(
            token,
            SpotifyTokenBundle,
        ):
            raise TypeError(
                "token must be a SpotifyTokenBundle"
            )

        try:
            self._store.save(
                token
            )
        except SpotifyCredentialStoreError:
            raise SpotifySessionManagerError(
                "credential_save_failed",
                (
                    "Spotify credentials could not "
                    "be saved securely."
                ),
            ) from None

        return SpotifySessionResult(
            status=SpotifySessionStatus.READY,
            token=token,
            message=(
                "Spotify credentials were saved securely."
            ),
        )

    def disconnect(
        self,
    ) -> SpotifySessionResult:
        try:
            self._store.delete()
        except SpotifyCredentialStoreError:
            raise SpotifySessionManagerError(
                "disconnect_failed",
                (
                    "Spotify credentials could not "
                    "be removed."
                ),
            ) from None

        return SpotifySessionResult(
            status=(
                SpotifySessionStatus.DISCONNECTED
            ),
            message="Spotify is disconnected.",
        )

    def resolve(
        self,
    ) -> SpotifySessionResult:
        try:
            token = self._store.load()
        except SpotifyCredentialStoreError as error:
            if (
                error.error_code
                == "credential_corrupt"
            ):
                return SpotifySessionResult(
                    status=(
                        SpotifySessionStatus
                        .REAUTHORIZATION_REQUIRED
                    ),
                    message=(
                        "Saved Spotify credentials are invalid. "
                        "Reconnect Spotify."
                    ),
                )

            raise SpotifySessionManagerError(
                "credential_load_failed",
                (
                    "Saved Spotify credentials "
                    "could not be loaded."
                ),
            ) from None

        if token is None:
            return SpotifySessionResult(
                status=(
                    SpotifySessionStatus.DISCONNECTED
                ),
                message="Spotify is not connected.",
            )

        if not isinstance(
            token,
            SpotifyTokenBundle,
        ):
            raise SpotifySessionManagerError(
                "invalid_stored_token",
                (
                    "Saved Spotify credentials "
                    "returned an invalid token."
                ),
            )

        now = _safe_clock_value(
            self._clock
        )

        if not _token_needs_refresh(
            token,
            now=now,
            refresh_skew_seconds=(
                self._refresh_skew_seconds
            ),
        ):
            return SpotifySessionResult(
                status=SpotifySessionStatus.READY,
                token=token,
                message="Spotify session is ready.",
            )

        if not token.refresh_token:
            self._delete_unusable_credentials()

            return SpotifySessionResult(
                status=(
                    SpotifySessionStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                message=(
                    "Spotify must be connected again."
                ),
            )

        try:
            refreshed = (
                self._token_client
                .refresh_access_token(
                    token
                )
            )
        except SpotifyTokenError as error:
            if (
                error.error_code
                == "reauthorization_required"
            ):
                self._delete_unusable_credentials()

                return SpotifySessionResult(
                    status=(
                        SpotifySessionStatus
                        .REAUTHORIZATION_REQUIRED
                    ),
                    message=(
                        "Spotify authorization has expired. "
                        "Reconnect Spotify."
                    ),
                )

            raise SpotifySessionManagerError(
                "refresh_failed",
                (
                    "Spotify session could not "
                    "be refreshed."
                ),
            ) from None

        if not isinstance(
            refreshed,
            SpotifyTokenBundle,
        ):
            raise SpotifySessionManagerError(
                "invalid_refresh_result",
                (
                    "Spotify returned an invalid "
                    "refreshed session."
                ),
            )

        try:
            self._store.save(
                refreshed
            )
        except SpotifyCredentialStoreError:
            raise SpotifySessionManagerError(
                "credential_save_failed",
                (
                    "The refreshed Spotify session "
                    "could not be saved securely."
                ),
            ) from None

        return SpotifySessionResult(
            status=(
                SpotifySessionStatus.REFRESHED
            ),
            token=refreshed,
            message=(
                "Spotify session was refreshed."
            ),
        )
