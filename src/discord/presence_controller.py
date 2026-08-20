from PyQt6.QtCore import QObject, QSettings, pyqtSignal

from src.discord.presence_modes import (
    MODE_DEFAULTS,
    PresenceMode,
    VALID_MODES,
)

from src.discord.presence_link_buttons import (
    PresenceLinkButtonError,
    decode_presence_buttons,
    encode_presence_buttons,
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

        show_loop_count = self.store.value(
            f"presence/{normalized}/show_loop_count",
            False,
            type=bool,
        )

        show_buttons = self.store.value(
            f"presence/{normalized}/show_buttons",
            False,
            type=bool,
        )

        try:
            buttons = decode_presence_buttons(
                self.store.value(
                    f"presence/{normalized}/buttons",
                    "",
                )
            )
        except PresenceLinkButtonError:
            show_buttons = False
            buttons = ()

        return PresenceMode(
            mode=normalized,
            title=title,
            message=message,
            image_path=image_path,
            show_elapsed=show_elapsed,
            show_buttons=show_buttons,
            buttons=buttons,
            show_loop_count=(
                bool(show_loop_count)
                if normalized == "music"
                else False
            ),
        )

    def save_mode(
        self,
        presence_mode: PresenceMode,
    ):
        mode = presence_mode.normalized_mode()

        buttons_json = ""
        show_buttons = False

        if mode != "disabled":
            buttons_json = encode_presence_buttons(
                presence_mode.normalized_buttons()
            )

            show_buttons = (
                presence_mode.link_buttons_enabled()
            )

        self.store.setValue(
            "presence/active_mode",
            mode,
        )

        if mode == "music":
            self.store.setValue(
                f"presence/{mode}/show_loop_count",
                bool(
                    presence_mode.show_loop_count
                ),
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

        if mode != "disabled":
            self.store.setValue(
                f"presence/{mode}/show_buttons",
                show_buttons,
            )

            self.store.setValue(
                f"presence/{mode}/buttons",
                buttons_json,
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

    @staticmethod
    def _discord_buttons_for_mode(
        presence_mode: PresenceMode,
    ) -> list[dict]:
        if not presence_mode.link_buttons_enabled():
            return []

        return [
            button.to_dict()
            for button in (
                presence_mode
                .normalized_buttons()
            )
        ]

    def set_music_loop_count_enabled(
        self,
        enabled: bool,
    ):
        checked = bool(enabled)

        self.store.setValue(
            "presence/music/show_loop_count",
            checked,
        )
        self.store.sync()

        loop_count_setter = getattr(
            self.discord,
            "set_music_loop_count_enabled",
            None,
        )

        if callable(
            loop_count_setter
        ):
            loop_count_setter(
                checked
            )

        if self.active_mode != "music":
            return

        latest_song = self._latest_song

        if not self._has_song(
            latest_song
        ):
            return

        music_mode = self.load_mode(
            "music"
        )

        discord_buttons = (
            self._discord_buttons_for_mode(
                music_mode
            )
        )

        self.discord.update_song(
            latest_song,
            buttons=discord_buttons,
        )

    def apply_mode(
        self,
        presence_mode: PresenceMode,
    ):
        mode = presence_mode.normalized_mode()

        if self._auto_afk_active:
            self._auto_afk_active = False
            self._mode_before_auto_afk = None

        self.save_mode(presence_mode)

        discord_buttons = (
            self._discord_buttons_for_mode(
                presence_mode
            )
        )

        if mode == "music":
            loop_count_setter = getattr(
                self.discord,
                "set_music_loop_count_enabled",
                None,
            )

            if callable(
                loop_count_setter
            ):
                loop_count_setter(
                    bool(
                        presence_mode.show_loop_count
                    )
                )

            latest_song = self._latest_song

            if self._has_song(
                latest_song
            ):
                self.discord.update_song(
                    latest_song,
                    buttons=discord_buttons,
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
                buttons=discord_buttons,
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

        if current_mode not in {
            "music",
            "custom",
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

        discord_buttons = (
            self._discord_buttons_for_mode(
                afk_mode
            )
        )

        self.discord.update_custom(
            title=payload["title"],
            message=payload["message"],
            image_bytes=payload["image_bytes"],
            image_name=payload["image_name"],
            show_elapsed=payload["show_elapsed"],
            buttons=discord_buttons,
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
            music_mode = self.load_mode(
                "music"
            )

            discord_buttons = (
                self._discord_buttons_for_mode(
                    music_mode
                )
            )

            self.discord.update_song(
                song,
                buttons=discord_buttons,
            )
            return

        self.discord.clear_presence()
