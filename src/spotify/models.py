from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from numbers import Real

from src.spotify.constants import normalize_scopes


def _require_nonempty_text(
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

    if not value.strip():
        raise ValueError(
            f"{field_name} cannot be empty"
        )

    return value


def _require_optional_text(
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

    return value


def _require_timestamp(
    value: object,
    field_name: str,
) -> float:
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
        raise TypeError(
            f"{field_name} must be a number"
        )

    numeric = float(
        value
    )

    if numeric < 0:
        raise ValueError(
            f"{field_name} cannot be negative"
        )

    return numeric


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyTokenBundle:
    access_token: str = field(
        repr=False
    )
    refresh_token: str = field(
        default="",
        repr=False,
    )
    token_type: str = "Bearer"
    expires_in: int = 3600
    granted_scopes: tuple[str, ...] = ()
    obtained_at: float = 0.0
    authorized_at: float = 0.0

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_text(
            self.access_token,
            "access_token",
        )

        _require_optional_text(
            self.refresh_token,
            "refresh_token",
        )

        token_type = (
            _require_nonempty_text(
                self.token_type,
                "token_type",
            )
            .strip()
        )

        if (
            isinstance(
                self.expires_in,
                bool,
            )
            or not isinstance(
                self.expires_in,
                int,
            )
        ):
            raise TypeError(
                "expires_in must be an integer"
            )

        if self.expires_in <= 0:
            raise ValueError(
                "expires_in must be positive"
            )

        scopes = tuple(
            self.granted_scopes
        )

        if scopes:
            scopes = normalize_scopes(
                scopes
            )

        obtained_at = _require_timestamp(
            self.obtained_at,
            "obtained_at",
        )

        authorized_at = _require_timestamp(
            self.authorized_at,
            "authorized_at",
        )

        object.__setattr__(
            self,
            "token_type",
            token_type,
        )

        object.__setattr__(
            self,
            "granted_scopes",
            scopes,
        )

        object.__setattr__(
            self,
            "obtained_at",
            obtained_at,
        )

        object.__setattr__(
            self,
            "authorized_at",
            authorized_at,
        )

    @property
    def expires_at(
        self,
    ) -> float:
        return (
            self.obtained_at
            + self.expires_in
        )

    @property
    def has_refresh_token(
        self,
    ) -> bool:
        return bool(
            self.refresh_token
        )

    def is_access_token_expired(
        self,
        at_time: float,
        *,
        skew_seconds: float = 30.0,
    ) -> bool:
        now = _require_timestamp(
            at_time,
            "at_time",
        )

        skew = _require_timestamp(
            skew_seconds,
            "skew_seconds",
        )

        return (
            now
            >= self.expires_at - skew
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyAccount:
    account_id: str
    display_name: str = ""
    user_id: str = ""
    uri: str = ""
    profile_url: str = ""
    image_url: str = ""

    def __post_init__(
        self,
    ) -> None:
        account_id = (
            _require_nonempty_text(
                self.account_id,
                "account_id",
            )
            .strip()
        )

        object.__setattr__(
            self,
            "account_id",
            account_id,
        )

        for field_name in (
            "display_name",
            "user_id",
            "uri",
            "profile_url",
            "image_url",
        ):
            _require_optional_text(
                getattr(
                    self,
                    field_name,
                ),
                field_name,
            )
