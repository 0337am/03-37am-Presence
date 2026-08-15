import hashlib
import time
from dataclasses import dataclass

from src.discord.presence import DiscordPresence

from src.discord.presence_link_buttons import (
    normalize_presence_buttons,
)

try:
    from pypresence.types import ActivityType
except ImportError:
    ActivityType = None


@dataclass(frozen=True)
class SongPresenceUpdate:
    song: object
    buttons: tuple[tuple[str, str], ...]

    @property
    def playing(self) -> bool:
        return bool(
            getattr(
                self.song,
                "playing",
                False,
            )
        )


@dataclass(frozen=True)
class CustomPresenceUpdate:
    title: str
    message: str
    image_bytes: bytes | None
    image_name: str
    show_elapsed: bool
    started_at: int | None
    buttons: tuple[tuple[str, str], ...] = ()


class ExtendedDiscordPresence(DiscordPresence):
    @staticmethod
    def _normalize_rpc_buttons(
        buttons,
    ) -> tuple[tuple[str, str], ...]:
        normalized = normalize_presence_buttons(
            buttons
        )

        return tuple(
            (
                button.label,
                button.url,
            )
            for button in normalized
        )

    @staticmethod
    def _rpc_button_payload(
        buttons,
    ) -> list[dict]:
        return [
            {
                "label": label,
                "url": url,
            }
            for label, url in buttons
        ]

    def update_song(
        self,
        song,
        buttons=None,
    ):
        if self._stop_event.is_set():
            return

        if song is None:
            self._replace_queued_item(
                None
            )
            return

        update = SongPresenceUpdate(
            song=song,
            buttons=self._normalize_rpc_buttons(
                buttons
            ),
        )

        self._replace_queued_item(
            update
        )

    def update_custom(
        self,
        title: str,
        message: str,
        image_bytes=None,
        image_name: str = "",
        show_elapsed: bool = False,
        buttons=None,
    ):
        if self._stop_event.is_set():
            return

        update = CustomPresenceUpdate(
            title=str(
                title or ""
            ).strip(),
            message=str(
                message or ""
            ).strip(),
            image_bytes=image_bytes,
            image_name=str(
                image_name or ""
            ).strip(),
            show_elapsed=bool(
                show_elapsed
            ),
            started_at=(
                int(time.time())
                if show_elapsed
                else None
            ),
            buttons=self._normalize_rpc_buttons(
                buttons
            ),
        )

        self._replace_queued_item(
            update
        )

    def clear_presence(self):
        if self._stop_event.is_set():
            return

        self._replace_queued_item(None)

    def _publish_song(
        self,
        item,
    ):
        if isinstance(
            item,
            CustomPresenceUpdate,
        ):
            self._publish_custom(
                item
            )
            return

        if isinstance(
            item,
            SongPresenceUpdate,
        ):
            super()._publish_song(
                item.song,
                buttons=(
                    self._rpc_button_payload(
                        item.buttons
                    )
                ),
            )
            return

        super()._publish_song(
            item,
            buttons=[],
        )

    def _publish_custom(
        self,
        update: CustomPresenceUpdate,
    ):
        title = self._discord_text(
            update.title,
            fallback="Custom presence",
        )

        message = self._discord_text(
            update.message,
            fallback="Active",
        )

        options = {
            "details": title,
            "state": message,
        }

        button_payload = (
            self._rpc_button_payload(
                update.buttons
            )
        )

        if button_payload:
            options["buttons"] = (
                button_payload
            )

        if ActivityType is not None:
            playing_type = getattr(
                ActivityType,
                "PLAYING",
                None,
            )

            if playing_type is not None:
                options["activity_type"] = playing_type

        if (
            update.show_elapsed
            and update.started_at is not None
        ):
            options["start"] = update.started_at

        local_image_available = bool(
            update.image_bytes
        )

        artwork_url = None

        try:
            if (
                local_image_available
                and self.artwork_uploader.is_configured
            ):
                artwork_url = (
                    self.artwork_uploader
                    .get_or_upload(
                        update.image_bytes
                    )
                )

        except Exception as error:
            print(
                "Custom artwork upload failed; "
                "continuing without Discord artwork: "
                f"{error}"
            )

        if artwork_url:
            options["large_image"] = (
                artwork_url
            )

            options["large_text"] = (
                self._discord_text(
                    update.image_name,
                    fallback=title,
                )
            )

        self.rpc.update(**options)

        if artwork_url:
            image_status = (
                "personal Cloudinary image"
            )

        elif local_image_available:
            image_status = (
                "custom image kept on device"
            )

        else:
            image_status = (
                "without custom image"
            )

        print(
            f"Custom Discord presence updated: "
            f"{title} — {message} "
            f"({image_status})"
        )

    @staticmethod
    @staticmethod
    def _make_presence_key(item):
        if isinstance(
            item,
            CustomPresenceUpdate,
        ):
            if item.image_bytes:
                image_key = hashlib.sha256(
                    item.image_bytes
                ).hexdigest()
            else:
                image_key = ""

            return (
                "custom",
                item.title,
                item.message,
                item.image_name,
                item.show_elapsed,
                item.started_at,
                image_key,
                item.buttons,
            )

        if isinstance(
            item,
            SongPresenceUpdate,
        ):
            return (
                "music",
                *DiscordPresence._make_presence_key(
                    item.song
                ),
                item.buttons,
            )

        return DiscordPresence._make_presence_key(
            item
        )
