from PyQt6.QtCore import QObject, QSettings, pyqtSignal

from src.discord.presence_modes import (
    MODE_DEFAULTS,
    PresenceMode,
    VALID_MODES,
)


class PresenceController(QObject):
    mode_changed = pyqtSignal(dict)

    def __init__(self, discord_presence):
        super().__init__()

        self.discord = discord_presence
        self.store = QSettings(
            "0337am",
            "Presence",
        )

    @property
    def active_mode(self) -> str:
        mode = str(
            self.store.value(
                "presence/active_mode",
                "music",
            )
        ).strip().lower()

        if mode not in VALID_MODES:
            return "music"

        return mode

    def load_mode(
        self,
        mode: str,
    ) -> PresenceMode:
        normalized = str(
            mode or "music"
        ).strip().lower()

        if normalized not in VALID_MODES:
            normalized = "custom"

        defaults = MODE_DEFAULTS.get(
            normalized,
            {
                "title": "",
                "message": "",
            },
        )

        title = str(
            self.store.value(
                f"presence/{normalized}/title",
                defaults.get("title", ""),
            )
            or ""
        )

        message = str(
            self.store.value(
                f"presence/{normalized}/message",
                defaults.get("message", ""),
            )
            or ""
        )

        image_path = str(
            self.store.value(
                f"presence/{normalized}/image_path",
                "",
            )
            or ""
        )

        show_elapsed = self.store.value(
            f"presence/{normalized}/show_elapsed",
            False,
            type=bool,
        )

        return PresenceMode(
            mode=normalized,
            title=title,
            message=message,
            image_path=image_path,
            show_elapsed=show_elapsed,
        )

    def save_mode(
        self,
        presence_mode: PresenceMode,
    ):
        mode = presence_mode.normalized_mode()

        self.store.setValue(
            "presence/active_mode",
            mode,
        )

        if mode not in {
            "music",
            "disabled",
        }:
            self.store.setValue(
                f"presence/{mode}/title",
                presence_mode.title,
            )

            self.store.setValue(
                f"presence/{mode}/message",
                presence_mode.message,
            )

            self.store.setValue(
                f"presence/{mode}/image_path",
                presence_mode.image_path,
            )

            self.store.setValue(
                f"presence/{mode}/show_elapsed",
                presence_mode.show_elapsed,
            )

        self.store.sync()

    def apply_mode(
        self,
        presence_mode: PresenceMode,
    ):
        mode = presence_mode.normalized_mode()

        self.save_mode(presence_mode)

        if mode == "music":
            latest_song = getattr(
                self,
                "_latest_song",
                None,
            )

            if latest_song is not None:
                self.discord.update_song(
                    latest_song
                )

        elif mode == "disabled":
            self.discord.clear_presence()

        else:
            payload = presence_mode.to_payload()

            self.discord.update_custom(
                title=payload["title"],
                message=payload["message"],
                image_bytes=payload["image_bytes"],
                image_name=payload["image_name"],
                show_elapsed=payload["show_elapsed"],
            )

        self.mode_changed.emit(
            presence_mode.to_payload()
        )

    def apply_saved_mode(self):
        presence_mode = self.load_mode(
            self.active_mode
        )

        self.apply_mode(presence_mode)

    def handle_song(self, song):
        self._latest_song = song

        if self.active_mode == "music":
            self.discord.update_song(song)

