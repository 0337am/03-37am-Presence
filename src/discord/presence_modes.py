import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from src.discord.presence_link_buttons import (
    PresenceLinkButton,
    normalize_presence_buttons,
)


VALID_MODES = {
    "music",
    "afk",
    "sleep",
    "working",
    "custom",
    "disabled",
}

DEFAULT_PARTY_CURRENT = 1
DEFAULT_PARTY_MAXIMUM = 2
MAX_PARTY_SIZE = 9999

MODE_NAMES = {
    "music": "Music",
    "afk": "AFK",
    "sleep": "Sleep",
    "working": "Working",
    "custom": "Custom",
    "disabled": "Disabled",
}

MODE_DEFAULTS = {
    "afk": {
        "title": "Away right now",
        "message": "Replies not guaranteed",
    },
    "sleep": {
        "title": "Sleeping",
        "message": "Wont reply until awake",
    },
    "working": {
        "title": "Working",
        "message": "Replies may be slow",
    },
    "custom": {
        "title": "Custom Presence",
        "message": "Custom Presence",
    },
}

APP_DATA_DIRECTORY = (
    Path(os.getenv("LOCALAPPDATA", str(Path.home())))
    / "0337am Presence"
)

PRESENCE_IMAGE_DIRECTORY = (
    APP_DATA_DIRECTORY / "presence_images"
)


@dataclass
class PresenceMode:
    mode: str = "music"
    title: str = ""
    message: str = ""
    image_path: str = ""
    show_elapsed: bool = False
    show_buttons: bool = False
    buttons: tuple[PresenceLinkButton, ...] = ()
    show_loop_count: bool = False
    show_party: bool = False
    party_current: int = DEFAULT_PARTY_CURRENT
    party_maximum: int = DEFAULT_PARTY_MAXIMUM
    application_entry_id: str | None = None
    artwork_hover_text: str = ""

    def normalized_mode(self) -> str:
        normalized = str(
            self.mode or "music"
        ).strip().lower()

        if normalized not in VALID_MODES:
            return "custom"

        return normalized

    def normalized_application_entry_id(
        self,
    ) -> str | None:
        if self.application_entry_id is None:
            return None

        entry_id = (
            str(
                self.application_entry_id
            )
            .replace("\x00", "")
            .strip()
        )

        return (
            entry_id
            or None
        )

    def normalized_artwork_hover_text(
        self,
    ) -> str:
        if self.normalized_mode() in {
            "music",
            "disabled",
        }:
            return ""

        return (
            str(
                self.artwork_hover_text
                or ""
            )
            .replace("\x00", "")
            .strip()[
                :128
            ]
        )

    @staticmethod
    def _normalized_party_value(
        value,
        default: int,
    ) -> int:
        try:
            normalized = int(value)
        except (
            TypeError,
            ValueError,
        ):
            normalized = int(default)

        return max(
            1,
            min(
                normalized,
                MAX_PARTY_SIZE,
            ),
        )

    def normalized_party_size(
        self,
    ) -> tuple[int, int]:
        current = self._normalized_party_value(
            self.party_current,
            DEFAULT_PARTY_CURRENT,
        )

        maximum = self._normalized_party_value(
            self.party_maximum,
            DEFAULT_PARTY_MAXIMUM,
        )

        if maximum < current:
            maximum = current

        return (
            current,
            maximum,
        )

    def party_enabled(self) -> bool:
        return bool(
            self.normalized_mode() == "custom"
            and self.show_party
        )

    def discord_party_size(
        self,
    ) -> list[int] | None:
        if not self.party_enabled():
            return None

        current, maximum = (
            self.normalized_party_size()
        )

        return [
            current,
            maximum,
        ]

    def resolved_title(self) -> str:
        mode = self.normalized_mode()

        default = MODE_DEFAULTS.get(
            mode,
            {},
        ).get(
            "title",
            "",
        )

        return str(
            self.title or default
        ).strip()

    def resolved_message(self) -> str:
        mode = self.normalized_mode()

        default = MODE_DEFAULTS.get(
            mode,
            {},
        ).get(
            "message",
            "",
        )

        return str(
            self.message or default
        ).strip()

    def image_bytes(self):
        path = Path(self.image_path)

        if not path.exists():
            return None

        try:
            return path.read_bytes()
        except OSError:
            return None

    def image_name(self) -> str:
        path = Path(self.image_path)

        if not path.exists():
            return ""

        return path.stem

    def normalized_buttons(
        self,
    ) -> tuple[PresenceLinkButton, ...]:
        if self.normalized_mode() == "disabled":
            return ()

        return normalize_presence_buttons(
            self.buttons
        )

    def link_buttons_enabled(
        self,
    ) -> bool:
        if self.normalized_mode() == "disabled":
            return False

        return bool(
            self.show_buttons
        )

    def to_payload(self) -> dict:
        buttons = self.normalized_buttons()

        party_current, party_maximum = (
            self.normalized_party_size()
        )

        return {
            "mode": self.normalized_mode(),
            "application_entry_id": (
                self.normalized_application_entry_id()
            ),
            "title": self.resolved_title(),
            "message": self.resolved_message(),
            "image_bytes": self.image_bytes(),
            "image_name": self.image_name(),
            "show_elapsed": bool(
                self.show_elapsed
            ),
            "show_loop_count": bool(
                self.show_loop_count
                if self.normalized_mode() == "music"
                else False
            ),
            "show_party": self.party_enabled(),
            "party_current": party_current,
            "party_maximum": party_maximum,
            "party_size": self.discord_party_size(),
            "show_buttons": (
                self.link_buttons_enabled()
            ),
            "buttons": [
                button.to_dict()
                for button in buttons
            ],
        }


def save_mode_image(
    source_path: str,
    mode: str,
) -> str:
    source = Path(source_path)

    if not source.exists():
        return ""

    normalized_mode = str(
        mode or "custom"
    ).strip().lower()

    if normalized_mode not in VALID_MODES:
        normalized_mode = "custom"

    suffix = source.suffix.lower()

    if suffix not in {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    }:
        suffix = ".png"

    try:
        PRESENCE_IMAGE_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        for existing_file in (
            PRESENCE_IMAGE_DIRECTORY.glob(
                f"{normalized_mode}.*"
            )
        ):
            try:
                existing_file.unlink()
            except OSError:
                pass

        destination = (
            PRESENCE_IMAGE_DIRECTORY
            / f"{normalized_mode}{suffix}"
        )

        shutil.copy2(
            source,
            destination,
        )

        return str(destination)

    except OSError:
        return ""


def remove_mode_image(
    image_path: str,
):
    path = Path(image_path)

    if not path.exists():
        return

    try:
        path.unlink()
    except OSError:
        pass

