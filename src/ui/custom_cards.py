from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


SCHEMA_VERSION = 1
LINK_CARD_TYPE = "link"
MAX_CUSTOM_CARDS = 100
MAX_TITLE_LENGTH = 80
MAX_URL_LENGTH = 2048
MAX_ICON_LENGTH = 8
MAX_DESCRIPTION_LENGTH = 300
MAX_BUTTON_LABEL_LENGTH = 30

_CARD_ID_PATTERN = re.compile(
    r"^custom_[a-z][a-z0-9_]{0,31}_[0-9a-f]{32}$"
)
_ACCENT_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
_ALLOWED_WEB_SCHEMES = frozenset({"http", "https"})


def _strict_text(
    value,
    field_name: str,
    maximum_length: int,
    *,
    allow_empty: bool = True,
) -> str:
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be text."
        )

    cleaned = value.strip()

    if not allow_empty and not cleaned:
        raise ValueError(
            f"{field_name} cannot be empty."
        )

    if len(cleaned) > maximum_length:
        raise ValueError(
            f"{field_name} is too long."
        )

    return cleaned


def normalize_web_url(value: str) -> str:
    raw = _strict_text(
        value,
        "Destination URL",
        MAX_URL_LENGTH,
        allow_empty=False,
    )

    if any(
        character.isspace()
        or ord(character) < 32
        or ord(character) == 127
        for character in raw
    ):
        raise ValueError(
            "Destination URL cannot contain whitespace or control characters."
        )

    try:
        parsed = urlsplit(raw)
    except ValueError as error:
        raise ValueError(
            "Destination URL is malformed."
        ) from error

    scheme = parsed.scheme.casefold()

    if scheme not in _ALLOWED_WEB_SCHEMES:
        raise ValueError(
            "Only http:// and https:// links are allowed."
        )

    if not parsed.netloc or not parsed.hostname:
        raise ValueError(
            "Destination URL must include a valid host."
        )

    if parsed.username is not None or parsed.password is not None:
        raise ValueError(
            "Destination URL cannot contain embedded login details."
        )

    try:
        parsed.hostname.encode("idna")
        _ = parsed.port
    except (UnicodeError, ValueError) as error:
        raise ValueError(
            "Destination URL contains an invalid host or port."
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

    if len(normalized) > MAX_URL_LENGTH:
        raise ValueError(
            "Destination URL is too long."
        )

    return normalized


def display_domain(url: str) -> str:
    normalized = normalize_web_url(url)
    hostname = urlsplit(normalized).hostname or ""

    if hostname.casefold().startswith("www."):
        hostname = hostname[4:]

    return hostname


def normalize_accent(value: str) -> str:
    accent = _strict_text(
        value,
        "Accent colour",
        7,
    )

    if not accent:
        return ""

    if not _ACCENT_PATTERN.fullmatch(accent):
        raise ValueError(
            "Accent colour must use #RRGGBB format."
        )

    return accent.lower()


def new_card_id(card_type: str) -> str:
    normalized_type = str(
        card_type or ""
    ).strip().casefold()

    if not re.fullmatch(
        r"[a-z][a-z0-9_]{0,31}",
        normalized_type,
    ):
        raise ValueError(
            "Custom card type is invalid."
        )

    return (
        f"custom_{normalized_type}_"
        f"{uuid.uuid4().hex}"
    )


def validate_card_id(
    value: str,
    expected_type: str | None = None,
) -> str:
    card_id = _strict_text(
        value,
        "Custom card ID",
        80,
        allow_empty=False,
    )

    if not _CARD_ID_PATTERN.fullmatch(card_id):
        raise ValueError(
            "Custom card ID is invalid."
        )

    if expected_type is not None:
        prefix = f"custom_{expected_type}_"

        if not card_id.startswith(prefix):
            raise ValueError(
                "Custom card ID does not match its card type."
            )

    return card_id


@dataclass(frozen=True)
class LinkCardData:
    card_id: str
    title: str
    url: str
    icon: str = ""
    description: str = ""
    button_label: str = "Open"
    accent: str = ""

    @property
    def card_type(self) -> str:
        return LINK_CARD_TYPE

    @property
    def domain(self) -> str:
        return display_domain(self.url)

    def to_dict(self) -> dict:
        return {
            "id": self.card_id,
            "type": self.card_type,
            "title": self.title,
            "url": self.url,
            "icon": self.icon,
            "description": self.description,
            "button_label": self.button_label,
            "accent": self.accent,
        }

    @classmethod
    def from_dict(
        cls,
        payload,
    ) -> "LinkCardData":
        if not isinstance(payload, dict):
            raise ValueError(
                "Custom card data must be an object."
            )

        card_type = _strict_text(
            payload.get("type", ""),
            "Custom card type",
            32,
            allow_empty=False,
        ).casefold()

        if card_type != LINK_CARD_TYPE:
            raise ValueError(
                "Unsupported custom card type."
            )

        url = normalize_web_url(
            payload.get("url", "")
        )

        title = _strict_text(
            payload.get("title", ""),
            "Title",
            MAX_TITLE_LENGTH,
        )

        if not title:
            title = display_domain(url)

        button_label = _strict_text(
            payload.get(
                "button_label",
                "Open",
            ),
            "Button label",
            MAX_BUTTON_LABEL_LENGTH,
        )

        if not button_label:
            button_label = "Open"

        return cls(
            card_id=validate_card_id(
                payload.get("id", ""),
                LINK_CARD_TYPE,
            ),
            title=title,
            url=url,
            icon=_strict_text(
                payload.get("icon", ""),
                "Icon or emoji",
                MAX_ICON_LENGTH,
            ),
            description=_strict_text(
                payload.get("description", ""),
                "Description",
                MAX_DESCRIPTION_LENGTH,
            ),
            button_label=button_label,
            accent=normalize_accent(
                payload.get("accent", "")
            ),
        )


def create_link_card(
    *,
    url: str,
    title: str = "",
    icon: str = "",
    description: str = "",
    button_label: str = "Open",
    accent: str = "",
    card_id: str | None = None,
) -> LinkCardData:
    payload = {
        "id": card_id or new_card_id(
            LINK_CARD_TYPE
        ),
        "type": LINK_CARD_TYPE,
        "title": title,
        "url": url,
        "icon": icon,
        "description": description,
        "button_label": button_label,
        "accent": accent,
    }

    return LinkCardData.from_dict(
        payload
    )


def duplicate_link_card(
    card: LinkCardData,
) -> LinkCardData:
    if not isinstance(card, LinkCardData):
        raise TypeError(
            "Expected LinkCardData."
        )

    return replace(
        card,
        card_id=new_card_id(
            LINK_CARD_TYPE
        ),
    )


_CARD_LOADERS = {
    LINK_CARD_TYPE: LinkCardData.from_dict,
}


def custom_card_from_dict(payload):
    if not isinstance(payload, dict):
        raise ValueError(
            "Custom card data must be an object."
        )

    card_type = _strict_text(
        payload.get("type", ""),
        "Custom card type",
        32,
        allow_empty=False,
    ).casefold()

    loader = _CARD_LOADERS.get(
        card_type
    )

    if loader is None:
        raise ValueError(
            f"Unsupported custom card type: {card_type}"
        )

    return loader(payload)


def validate_custom_cards(cards) -> tuple[LinkCardData, ...]:
    try:
        normalized = tuple(cards)
    except TypeError as error:
        raise ValueError(
            "Custom cards must be a collection."
        ) from error

    if len(normalized) > MAX_CUSTOM_CARDS:
        raise ValueError(
            "Too many custom cards are saved."
        )

    card_ids = []

    for card in normalized:
        if not isinstance(card, LinkCardData):
            raise TypeError(
                "Unsupported custom card object."
            )

        validated = LinkCardData.from_dict(
            card.to_dict()
        )
        card_ids.append(
            validated.card_id
        )

    if len(card_ids) != len(set(card_ids)):
        raise ValueError(
            "Custom cards contain duplicate IDs."
        )

    return normalized


class CustomCardStore:
    def __init__(
        self,
        path: Path | str | None = None,
    ):
        self.path = (
            Path(path)
            if path is not None
            else self.default_path()
        )

    @staticmethod
    def default_path() -> Path:
        local_app_data = str(
            os.getenv(
                "LOCALAPPDATA",
                "",
            )
            or ""
        ).strip()

        if local_app_data:
            root = Path(local_app_data)
        else:
            root = (
                Path.home()
                / ".0337am-presence"
            )

        return (
            root
            / "0337am Presence"
            / "custom_cards.json"
        )

    def load(self) -> tuple[LinkCardData, ...]:
        if not self.path.exists():
            return ()

        try:
            payload = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )

            if not isinstance(payload, dict):
                raise ValueError(
                    "Custom card storage must be an object."
                )

            schema_version = payload.get(
                "schema_version"
            )

            if (
                isinstance(schema_version, bool)
                or schema_version != SCHEMA_VERSION
            ):
                raise ValueError(
                    "Unsupported custom card storage version."
                )

            cards_payload = payload.get(
                "cards",
                [],
            )

            if not isinstance(cards_payload, list):
                raise ValueError(
                    "Custom cards must be a list."
                )

            cards = tuple(
                custom_card_from_dict(item)
                for item in cards_payload
            )

            return validate_custom_cards(
                cards
            )

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as error:
            self._quarantine_invalid_file()

            print(
                "Custom card storage was invalid and "
                f"has been reset: {error}"
            )

            return ()

    def save(
        self,
        cards,
    ) -> tuple[LinkCardData, ...]:
        validated = validate_custom_cards(
            cards
        )

        payload = json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "cards": [
                    card.to_dict()
                    for card in validated
                ],
            },
            indent=2,
            ensure_ascii=False,
        )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self.path.with_name(
            self.path.name + ".tmp"
        )

        try:
            with temporary_path.open(
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write(payload)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(
                temporary_path,
                self.path,
            )

        except Exception:
            temporary_path.unlink(
                missing_ok=True
            )
            raise

        return validated

    def upsert(
        self,
        card: LinkCardData,
    ) -> tuple[LinkCardData, ...]:
        validated_card = LinkCardData.from_dict(
            card.to_dict()
        )
        cards = list(self.load())

        for index, existing in enumerate(cards):
            if existing.card_id == validated_card.card_id:
                cards[index] = validated_card
                break
        else:
            cards.append(validated_card)

        return self.save(cards)

    def delete(
        self,
        card_id: str,
    ) -> tuple[LinkCardData, ...]:
        validated_id = validate_card_id(
            card_id
        )
        cards = tuple(
            card
            for card in self.load()
            if card.card_id != validated_id
        )
        return self.save(cards)

    def _quarantine_invalid_file(self):
        if not self.path.exists():
            return

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        quarantine_path = self.path.with_name(
            self.path.name
            + f".corrupt_{timestamp}"
        )

        try:
            os.replace(
                self.path,
                quarantine_path,
            )
        except OSError:
            pass
