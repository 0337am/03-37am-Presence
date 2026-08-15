from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import (
    urlsplit,
    urlunsplit,
)


MAX_PRESENCE_LINK_BUTTONS = 2
MAX_PRESENCE_LINK_LABEL_LENGTH = 32
MAX_PRESENCE_LINK_URL_LENGTH = 512

_ALLOWED_SCHEMES = {
    "http",
    "https",
}


class PresenceLinkButtonError(
    ValueError
):
    pass


def _clean_label(
    value,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise PresenceLinkButtonError(
            "Button label must be text."
        )

    label = value.strip()

    if not label:
        raise PresenceLinkButtonError(
            "Button label cannot be empty."
        )

    if len(label) > (
        MAX_PRESENCE_LINK_LABEL_LENGTH
    ):
        raise PresenceLinkButtonError(
            "Button label is too long."
        )

    if any(
        ord(character) < 32
        or ord(character) == 127
        for character in label
    ):
        raise PresenceLinkButtonError(
            "Button label cannot contain "
            "control characters."
        )

    return label


def normalize_presence_link_url(
    value,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise PresenceLinkButtonError(
            "Button URL must be text."
        )

    raw = value.strip()

    if not raw:
        raise PresenceLinkButtonError(
            "Button URL cannot be empty."
        )

    if len(raw) > (
        MAX_PRESENCE_LINK_URL_LENGTH
    ):
        raise PresenceLinkButtonError(
            "Button URL is too long."
        )

    if any(
        character.isspace()
        or ord(character) < 32
        or ord(character) == 127
        for character in raw
    ):
        raise PresenceLinkButtonError(
            "Button URL cannot contain "
            "whitespace or control characters."
        )

    try:
        parsed = urlsplit(
            raw
        )
    except ValueError as error:
        raise PresenceLinkButtonError(
            "Button URL is malformed."
        ) from error

    scheme = parsed.scheme.casefold()

    if scheme not in _ALLOWED_SCHEMES:
        raise PresenceLinkButtonError(
            "Only http:// and https:// "
            "button links are allowed."
        )

    if (
        not parsed.netloc
        or not parsed.hostname
    ):
        raise PresenceLinkButtonError(
            "Button URL must include "
            "a valid host."
        )

    if (
        parsed.username is not None
        or parsed.password is not None
    ):
        raise PresenceLinkButtonError(
            "Button URL cannot contain "
            "embedded login details."
        )

    try:
        parsed.hostname.encode(
            "idna"
        )

        _ = parsed.port

    except (
        UnicodeError,
        ValueError,
    ) as error:
        raise PresenceLinkButtonError(
            "Button URL contains an "
            "invalid host or port."
        ) from error

    normalized = urlunsplit(
        (
            scheme,
            parsed.netloc,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )

    if len(normalized) > (
        MAX_PRESENCE_LINK_URL_LENGTH
    ):
        raise PresenceLinkButtonError(
            "Button URL is too long."
        )

    return normalized


@dataclass(frozen=True)
class PresenceLinkButton:
    label: str
    url: str

    def normalized(
        self,
    ) -> "PresenceLinkButton":
        return PresenceLinkButton(
            label=_clean_label(
                self.label
            ),
            url=normalize_presence_link_url(
                self.url
            ),
        )

    def to_dict(
        self,
    ) -> dict:
        button = self.normalized()

        return {
            "label": button.label,
            "url": button.url,
        }

    @classmethod
    def from_dict(
        cls,
        payload,
    ) -> "PresenceLinkButton":
        if not isinstance(
            payload,
            dict,
        ):
            raise PresenceLinkButtonError(
                "Presence button data "
                "must be an object."
            )

        return cls(
            label=payload.get(
                "label",
                "",
            ),
            url=payload.get(
                "url",
                "",
            ),
        ).normalized()


def normalize_presence_buttons(
    value,
) -> tuple[PresenceLinkButton, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        (
            str,
            bytes,
            bytearray,
            dict,
        ),
    ):
        raise PresenceLinkButtonError(
            "Presence buttons must be "
            "a collection."
        )

    try:
        items = tuple(
            value
        )
    except TypeError as error:
        raise PresenceLinkButtonError(
            "Presence buttons must be "
            "a collection."
        ) from error

    if len(items) > (
        MAX_PRESENCE_LINK_BUTTONS
    ):
        raise PresenceLinkButtonError(
            "Discord supports at most "
            "two Presence buttons."
        )

    normalized = []

    for item in items:
        if isinstance(
            item,
            PresenceLinkButton,
        ):
            button = (
                item.normalized()
            )

        elif isinstance(
            item,
            dict,
        ):
            button = (
                PresenceLinkButton
                .from_dict(
                    item
                )
            )

        else:
            raise PresenceLinkButtonError(
                "Presence button entries "
                "must be button objects."
            )

        normalized.append(
            button
        )

    return tuple(
        normalized
    )


def encode_presence_buttons(
    value,
) -> str:
    buttons = normalize_presence_buttons(
        value
    )

    return json.dumps(
        [
            button.to_dict()
            for button in buttons
        ],
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    )


def decode_presence_buttons(
    value,
) -> tuple[PresenceLinkButton, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        raw = value.strip()

        if not raw:
            return ()

        try:
            decoded = json.loads(
                raw
            )
        except json.JSONDecodeError as error:
            raise PresenceLinkButtonError(
                "Saved Presence button data "
                "is invalid."
            ) from error

        return normalize_presence_buttons(
            decoded
        )

    return normalize_presence_buttons(
        value
    )
