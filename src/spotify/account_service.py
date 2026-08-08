from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.spotify.models import (
    SpotifyAccount,
    SpotifyTokenBundle,
)
from src.spotify.session_manager import (
    SpotifySessionManagerError,
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiClient,
    SpotifyWebApiError,
)


class SpotifyAccountServiceStatus(
    str,
    Enum,
):
    DISCONNECTED = "disconnected"
    READY = "ready"
    REFRESHED = "refreshed"
    REAUTHORIZATION_REQUIRED = (
        "reauthorization_required"
    )


class SpotifyAccountServiceError(
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

        self.error_code = str(
            error_code
        ).strip()

        self.message = str(
            message
        ).strip()

        self.retry_after_seconds = (
            retry_after_seconds
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyAccountServiceResult:
    status: SpotifyAccountServiceStatus
    account: SpotifyAccount | None = None
    message: str = ""

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            SpotifyAccountServiceStatus,
        ):
            raise TypeError(
                (
                    "status must be a "
                    "SpotifyAccountServiceStatus"
                )
            )

        if not isinstance(
            self.message,
            str,
        ):
            raise TypeError(
                "message must be a string"
            )

        account_required = (
            self.status
            in {
                SpotifyAccountServiceStatus.READY,
                SpotifyAccountServiceStatus.REFRESHED,
            }
        )

        if account_required:
            if not isinstance(
                self.account,
                SpotifyAccount,
            ):
                raise ValueError(
                    (
                        "Connected Spotify account "
                        "states require an account."
                    )
                )

        elif self.account is not None:
            raise ValueError(
                (
                    "Disconnected Spotify account "
                    "states cannot contain an account."
                )
            )

    @property
    def connected(
        self,
    ) -> bool:
        return (
            self.status
            in {
                SpotifyAccountServiceStatus.READY,
                SpotifyAccountServiceStatus.REFRESHED,
            }
        )

    @property
    def refreshed(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyAccountServiceStatus.REFRESHED
        )

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyAccountServiceStatus.REAUTHORIZATION_REQUIRED
        )


class SpotifyAccountService:
    def __init__(
        self,
        session_manager,
        *,
        api_client=None,
    ) -> None:
        resolve = getattr(
            session_manager,
            "resolve",
            None,
        )

        if not callable(
            resolve
        ):
            raise TypeError(
                (
                    "session_manager must provide "
                    "a callable resolve method"
                )
            )

        if api_client is None:
            api_client = (
                SpotifyWebApiClient()
            )

        get_profile = getattr(
            api_client,
            "get_current_user_profile",
            None,
        )

        if not callable(
            get_profile
        ):
            raise TypeError(
                (
                    "api_client must provide a callable "
                    "get_current_user_profile method"
                )
            )

        self._session_manager = (
            session_manager
        )

        self._api_client = (
            api_client
        )

    def _resolve_session(
        self,
    ):
        try:
            return (
                self._session_manager
                .resolve()
            )

        except SpotifySessionManagerError:
            raise SpotifyAccountServiceError(
                "session_error",
                (
                    "The Spotify session could not "
                    "be restored securely."
                ),
            ) from None

        except Exception:
            raise SpotifyAccountServiceError(
                "session_error",
                (
                    "The Spotify session could not "
                    "be restored."
                ),
            ) from None

    def _session_result(
        self,
        session,
    ) -> SpotifyAccountServiceResult | None:
        status = getattr(
            session,
            "status",
            None,
        )

        if (
            status
            is SpotifySessionStatus.DISCONNECTED
        ):
            return SpotifyAccountServiceResult(
                status=(
                    SpotifyAccountServiceStatus
                    .DISCONNECTED
                ),
                message="Spotify is not connected.",
            )

        if (
            status
            is SpotifySessionStatus
            .REAUTHORIZATION_REQUIRED
        ):
            return SpotifyAccountServiceResult(
                status=(
                    SpotifyAccountServiceStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                message=(
                    "Spotify must be connected again."
                ),
            )

        if status not in {
            SpotifySessionStatus.READY,
            SpotifySessionStatus.REFRESHED,
        }:
            raise SpotifyAccountServiceError(
                "invalid_session_state",
                (
                    "Spotify returned an unexpected "
                    "session state."
                ),
            )

        return None

    def _session_token(
        self,
        session,
    ) -> SpotifyTokenBundle:
        token = getattr(
            session,
            "token",
            None,
        )

        if not isinstance(
            token,
            SpotifyTokenBundle,
        ):
            raise SpotifyAccountServiceError(
                "invalid_session",
                (
                    "Spotify returned an invalid "
                    "authenticated session."
                ),
            )

        if not token.access_token:
            raise SpotifyAccountServiceError(
                "invalid_session",
                (
                    "Spotify returned an invalid "
                    "authenticated session."
                ),
            )

        return token

    def _load_account(
        self,
        token: SpotifyTokenBundle,
    ) -> SpotifyAccount:
        try:
            account = (
                self._api_client
                .get_current_user_profile(
                    token.access_token
                )
            )

        except SpotifyWebApiError as error:
            if (
                error.error_code
                == "reauthorization_required"
            ):
                raise

            raise SpotifyAccountServiceError(
                error.error_code,
                error.message,
                retry_after_seconds=(
                    error.retry_after_seconds
                ),
            ) from None

        except Exception:
            raise SpotifyAccountServiceError(
                "api_error",
                (
                    "Spotify account information "
                    "could not be loaded."
                ),
            ) from None

        if not isinstance(
            account,
            SpotifyAccount,
        ):
            raise SpotifyAccountServiceError(
                "invalid_account",
                (
                    "Spotify returned invalid "
                    "account information."
                ),
            )

        return account

    def get_current_account(
        self,
    ) -> SpotifyAccountServiceResult:
        session = (
            self._resolve_session()
        )

        immediate_result = (
            self._session_result(
                session
            )
        )

        if immediate_result is not None:
            return immediate_result

        token = self._session_token(
            session
        )

        try:
            account = self._load_account(
                token
            )

        except SpotifyWebApiError as error:
            if (
                error.error_code
                == "reauthorization_required"
            ):
                return SpotifyAccountServiceResult(
                    status=(
                        SpotifyAccountServiceStatus
                        .REAUTHORIZATION_REQUIRED
                    ),
                    message=(
                        "Spotify must be connected again."
                    ),
                )

            raise

        session_status = getattr(
            session,
            "status",
            None,
        )

        if (
            session_status
            is SpotifySessionStatus.REFRESHED
        ):
            result_status = (
                SpotifyAccountServiceStatus
                .REFRESHED
            )

            message = (
                "Spotify account loaded after "
                "refreshing the session."
            )

        else:
            result_status = (
                SpotifyAccountServiceStatus
                .READY
            )

            message = (
                "Spotify account loaded."
            )

        return SpotifyAccountServiceResult(
            status=result_status,
            account=account,
            message=message,
        )
