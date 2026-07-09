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

        self._auto_afk_active = False
        self._mode_before_auto_afk = None

        self._latest_song = None

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

    @staticmethod
    def _has_song(
        song,
    ) -> bool:
        if song is None:
            return False

        title = str(
            getattr(
                song,
                "title",
                "",
            )
            or ""
        ).strip()

        return bool(title)

    def apply_mode(
        self,
        presence_mode: PresenceMode,
    ):
        mode = presence_mode.normalized_mode()

        if self._auto_afk_active:
            self._auto_afk_active = False
            self._mode_before_auto_afk = None

        self.save_mode(presence_mode)

        if mode == "music":
            latest_song = self._latest_song

            if self._has_song(
                latest_song
            ):
                self.discord.update_song(
                    latest_song
                )
            else:
                self.discord.clear_presence()

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

    @property
    def auto_afk_active(self) -> bool:
        return self._auto_afk_active

    def enter_auto_afk(self):
        if self._auto_afk_active:
            return

        current_mode = self.active_mode

        if current_mode in {
            "afk",
            "disabled",
        }:
            return

        self._mode_before_auto_afk = (
            current_mode
        )

        self._auto_afk_active = True

        afk_mode = self.load_mode(
            "afk"
        )

        payload = afk_mode.to_payload()

        self.discord.update_custom(
            title=payload["title"],
            message=payload["message"],
            image_bytes=payload["image_bytes"],
            image_name=payload["image_name"],
            show_elapsed=payload["show_elapsed"],
        )

        self.mode_changed.emit(
            payload
        )

    def leave_auto_afk(self):
        if not self._auto_afk_active:
            return

        restore_mode = (
            self._mode_before_auto_afk
            or self.active_mode
        )

        self._auto_afk_active = False
        self._mode_before_auto_afk = None

        presence_mode = self.load_mode(
            restore_mode
        )

        self.apply_mode(
            presence_mode
        )

    def handle_song(self, song):
        self._latest_song = song

        if self._auto_afk_active:
            return

        if self.active_mode != "music":
            return

        if self._has_song(
            song
        ):
            self.discord.update_song(
                song
            )
            return

        self.discord.clear_presence()
