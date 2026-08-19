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

    def normalized_mode(self) -> str:
        normalized = str(
            self.mode or "music"
        ).strip().lower()

        if normalized not in VALID_MODES:
            return "custom"

        return normalized

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

        return {
            "mode": self.normalized_mode(),
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

