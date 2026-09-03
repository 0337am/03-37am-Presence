from PyQt6.QtCore import QObject, QSettings, pyqtSignal

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY_ID,
    is_valid_user_entry_id,
)

from src.discord.session_manager import (
    MUSIC_LANE_ID,
    SECONDARY_LANE_ID,
)

from src.discord.presence_modes import (
    DEFAULT_PARTY_CURRENT,
    DEFAULT_PARTY_MAXIMUM,
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
    secondary_mode_changed = pyqtSignal(dict)

    def __init__(
        self,
        discord_presence,
        *,
        discord_session_manager=None,
    ):
        super().__init__()

        self.discord = discord_presence

        self.discord_session_manager = (
            discord_session_manager
        )

        self.store = QSettings(
            "0337am",
            "Presence",
        )

        self._auto_afk_active = False
        self._mode_before_auto_afk = None

        self._latest_song = None
        self._secondary_presence_mode = None

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

    @staticmethod
    def _normalized_application_entry_id(
        value,
    ) -> str:
        entry_id = (
            str(
                value or ""
            )
            .replace("\x00", "")
            .strip()
        )

        if (
            entry_id
            == BUILTIN_APPLICATION_ENTRY_ID
        ):
            return entry_id

        if is_valid_user_entry_id(
            entry_id
        ):
            return entry_id

        return (
            BUILTIN_APPLICATION_ENTRY_ID
        )

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

        application_entry_id = (
            PresenceController
            ._normalized_application_entry_id(
                self.store.value(
                    (
                        f"presence/{normalized}/"
                        "application_entry_id"
                    ),
                    BUILTIN_APPLICATION_ENTRY_ID,
                )
            )
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

        show_party = self.store.value(
            f"presence/{normalized}/show_party",
            False,
            type=bool,
        )

        party_current = self.store.value(
            f"presence/{normalized}/party_current",
            DEFAULT_PARTY_CURRENT,
        )

        party_maximum = self.store.value(
            f"presence/{normalized}/party_maximum",
            DEFAULT_PARTY_MAXIMUM,
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
            application_entry_id=(
                application_entry_id
            ),
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
            show_party=(
                bool(show_party)
                if normalized == "custom"
                else False
            ),
            party_current=party_current,
            party_maximum=party_maximum,
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

        requested_application_entry_id = (
            presence_mode
            .normalized_application_entry_id()
        )

        if (
            mode != "disabled"
            and requested_application_entry_id
            is not None
        ):
            self.store.setValue(
                (
                    f"presence/{mode}/"
                    "application_entry_id"
                ),
                (
                    PresenceController
                    ._normalized_application_entry_id(
                        requested_application_entry_id
                    )
                ),
            )

        if mode == "music":
            self.store.setValue(
                f"presence/{mode}/show_loop_count",
                bool(
                    presence_mode.show_loop_count
                ),
            )

        if mode == "custom":
            party_current, party_maximum = (
                presence_mode.normalized_party_size()
            )

            self.store.setValue(
                f"presence/{mode}/show_party",
                presence_mode.party_enabled(),
            )

            self.store.setValue(
                f"presence/{mode}/party_current",
                party_current,
            )

            self.store.setValue(
                f"presence/{mode}/party_maximum",
                party_maximum,
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

    @property
    def secondary_presence_mode(
        self,
    ) -> PresenceMode | None:
        candidate = getattr(
            self,
            "_secondary_presence_mode",
            None,
        )

        if isinstance(
            candidate,
            PresenceMode,
        ):
            return candidate

        return None

    @property
    def secondary_mode(
        self,
    ) -> str | None:
        candidate = (
            self.secondary_presence_mode
        )

        if candidate is None:
            return None

        try:
            mode = (
                candidate.normalized_mode()
            )

        except Exception:
            return None

        if mode in {
            "music",
            "disabled",
        }:
            return None

        return mode

    @staticmethod
    def _secondary_application_entry_id(
        presence_mode: PresenceMode,
    ) -> str:
        entry_id = (
            presence_mode
            .normalized_application_entry_id()
        )

        return (
            entry_id
            or BUILTIN_APPLICATION_ENTRY_ID
        )

    def _release_secondary_lane(
        self,
    ) -> bool:
        manager = getattr(
            self,
            "discord_session_manager",
            None,
        )

        if manager is None:
            return True

        release_lane = getattr(
            manager,
            "release_lane",
            None,
        )

        if not callable(
            release_lane
        ):
            return False

        try:
            return bool(
                release_lane(
                    SECONDARY_LANE_ID
                )
            )

        except Exception:
            return False

    def _publish_secondary_with_manager(
        self,
        presence_mode: PresenceMode,
    ) -> bool:
        manager = getattr(
            self,
            "discord_session_manager",
            None,
        )

        if manager is None:
            return False

        try:
            application_entry_id = (
                self
                ._secondary_application_entry_id(
                    presence_mode
                )
            )

            payload = (
                presence_mode.to_payload()
            )

            discord_buttons = (
                self._discord_buttons_for_mode(
                    presence_mode
                )
            )

        except Exception:
            return False

        update_secondary = getattr(
            manager,
            "update_secondary",
            None,
        )

        if not callable(
            update_secondary
        ):
            return False

        try:
            published = bool(
                update_secondary(
                    application_entry_id,
                    title=payload["title"],
                    message=payload["message"],
                    image_bytes=(
                        payload["image_bytes"]
                    ),
                    image_name=(
                        payload["image_name"]
                    ),
                    show_elapsed=(
                        payload["show_elapsed"]
                    ),
                    buttons=discord_buttons,
                    party_size=(
                        payload["party_size"]
                    ),
                )
            )

        except Exception:
            published = False

        if published:
            return True

        self._release_secondary_lane()

        return False

    def apply_secondary_mode(
        self,
        presence_mode: PresenceMode,
    ) -> bool:
        if not isinstance(
            presence_mode,
            PresenceMode,
        ):
            return False

        try:
            mode = (
                presence_mode
                .normalized_mode()
            )

        except Exception:
            return False

        if mode == "music":
            return False

        if mode == "disabled":
            return self.clear_secondary_mode()

        if not self._publish_secondary_with_manager(
            presence_mode
        ):
            previous = getattr(
                self,
                "_secondary_presence_mode",
                None,
            )

            self._secondary_presence_mode = None

            if previous is not None:
                secondary_signal = getattr(
                    self,
                    "secondary_mode_changed",
                    None,
                )

                emit = getattr(
                    secondary_signal,
                    "emit",
                    None,
                )

                if callable(
                    emit
                ):
                    try:
                        emit({})

                    except Exception:
                        pass

            return False

        self._secondary_presence_mode = (
            presence_mode
        )

        secondary_signal = getattr(
            self,
            "secondary_mode_changed",
            None,
        )

        emit = getattr(
            secondary_signal,
            "emit",
            None,
        )

        if callable(
            emit
        ):
            try:
                emit(
                    presence_mode.to_payload()
                )

            except Exception:
                pass

        return True

    def clear_secondary_mode(
        self,
    ) -> bool:
        if not self._release_secondary_lane():
            return False

        previous = getattr(
            self,
            "_secondary_presence_mode",
            None,
        )

        self._secondary_presence_mode = None

        if previous is None:
            return True

        secondary_signal = getattr(
            self,
            "secondary_mode_changed",
            None,
        )

        emit = getattr(
            secondary_signal,
            "emit",
            None,
        )

        if callable(
            emit
        ):
            try:
                emit({})

            except Exception:
                pass

        return True

    def _release_music_lane(
        self,
    ) -> bool:
        manager = getattr(
            self,
            "discord_session_manager",
            None,
        )

        if manager is None:
            return True

        release_lane = getattr(
            manager,
            "release_lane",
            None,
        )

        if not callable(
            release_lane
        ):
            return False

        try:
            return bool(
                release_lane(
                    MUSIC_LANE_ID
                )
            )

        except Exception:
            return False

    def _stop_legacy_discord(
        self,
    ) -> bool:
        try:
            is_connected = bool(
                getattr(
                    self.discord,
                    "is_connected",
                    False,
                )
            )

        except Exception:
            is_connected = True

        try:
            is_running = bool(
                getattr(
                    self.discord,
                    "is_running",
                    False,
                )
            )

        except Exception:
            is_running = True

        if (
            not is_connected
            and not is_running
        ):
            return True

        success = True

        clear_presence = getattr(
            self.discord,
            "clear_presence",
            None,
        )

        if callable(
            clear_presence
        ):
            try:
                clear_presence()

            except Exception:
                success = False

        close = getattr(
            self.discord,
            "close",
            None,
        )

        if callable(
            close
        ):
            try:
                close()

            except Exception:
                success = False

        return success

    def _start_legacy_discord(
        self,
    ) -> bool:
        connect = getattr(
            self.discord,
            "connect",
            None,
        )

        if not callable(
            connect
        ):
            return False

        try:
            return (
                connect()
                is not False
            )

        except Exception:
            return False

    @staticmethod
    def _music_application_entry_id(
        presence_mode: PresenceMode,
    ) -> str:
        entry_id = (
            presence_mode
            .normalized_application_entry_id()
        )

        return (
            entry_id
            or BUILTIN_APPLICATION_ENTRY_ID
        )

    def _publish_music_with_manager(
        self,
        presence_mode: PresenceMode,
        song,
    ) -> bool:
        manager = getattr(
            self,
            "discord_session_manager",
            None,
        )

        if manager is None:
            return False

        application_entry_id = (
            self._music_application_entry_id(
                presence_mode
            )
        )

        discord_buttons = (
            self._discord_buttons_for_mode(
                presence_mode
            )
        )

        if self._has_song(
            song
        ):
            update_music = getattr(
                manager,
                "update_music",
                None,
            )

            if not callable(
                update_music
            ):
                return False

            try:
                return bool(
                    update_music(
                        application_entry_id,
                        song,
                        buttons=discord_buttons,
                        show_loop_count=bool(
                            presence_mode
                            .show_loop_count
                        ),
                    )
                )

            except Exception:
                return False

        ensure_lane = getattr(
            manager,
            "ensure_lane",
            None,
        )

        clear_lane = getattr(
            manager,
            "clear_lane",
            None,
        )

        if (
            not callable(
                ensure_lane
            )
            or not callable(
                clear_lane
            )
        ):
            return False

        try:
            binding = ensure_lane(
                MUSIC_LANE_ID,
                application_entry_id,
            )

            if binding is None:
                return False

            return bool(
                clear_lane(
                    MUSIC_LANE_ID
                )
            )

        except Exception:
            return False

    def set_music_loop_count_enabled(
        self,
        enabled: bool,
    ):
        checked = bool(
            enabled
        )

        self.store.setValue(
            "presence/music/show_loop_count",
            checked,
        )

        self.store.sync()

        manager = getattr(
            self,
            "discord_session_manager",
            None,
        )

        if manager is not None:
            if self.active_mode != "music":
                return

            music_mode = self.load_mode(
                "music"
            )

            if not self._stop_legacy_discord():
                self._release_music_lane()
                return

            self._publish_music_with_manager(
                music_mode,
                self._latest_song,
            )

            return

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

        latest_song = (
            self._latest_song
        )

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
        mode = (
            presence_mode
            .normalized_mode()
        )

        if self._auto_afk_active:
            self._auto_afk_active = False
            self._mode_before_auto_afk = None

        self.save_mode(presence_mode)

        manager = getattr(
            self,
            "discord_session_manager",
            None,
        )

        if manager is not None:
            if mode == "music":
                if self._stop_legacy_discord():
                    music_mode = self.load_mode(
                        "music"
                    )

                    self._publish_music_with_manager(
                        music_mode,
                        self._latest_song,
                    )

                else:
                    self._release_music_lane()

            elif mode == "disabled":
                self.clear_secondary_mode()
                self._release_music_lane()
                self._stop_legacy_discord()

            else:
                if (
                    self.clear_secondary_mode()
                    and self._release_music_lane()
                    and self._start_legacy_discord()
                ):
                    payload = (
                        presence_mode
                        .to_payload()
                    )

                    discord_buttons = (
                        self._discord_buttons_for_mode(
                            presence_mode
                        )
                    )

                    self.discord.update_custom(
                        title=payload["title"],
                        message=payload["message"],
                        image_bytes=(
                            payload["image_bytes"]
                        ),
                        image_name=(
                            payload["image_name"]
                        ),
                        show_elapsed=(
                            payload["show_elapsed"]
                        ),
                        buttons=discord_buttons,
                        party_size=(
                            payload["party_size"]
                        ),
                    )

        else:
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
                            presence_mode
                            .show_loop_count
                        )
                    )

                latest_song = (
                    self._latest_song
                )

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
                payload = (
                    presence_mode
                    .to_payload()
                )

                self.discord.update_custom(
                    title=payload["title"],
                    message=payload["message"],
                    image_bytes=(
                        payload["image_bytes"]
                    ),
                    image_name=(
                        payload["image_name"]
                    ),
                    show_elapsed=(
                        payload["show_elapsed"]
                    ),
                    buttons=discord_buttons,
                    party_size=(
                        payload["party_size"]
                    ),
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

    def enter_auto_afk(
        self,
    ):
        if self._auto_afk_active:
            return

        current_mode = (
            self.active_mode
        )

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

        payload = (
            afk_mode.to_payload()
        )

        discord_buttons = (
            self._discord_buttons_for_mode(
                afk_mode
            )
        )

        manager = getattr(
            self,
            "discord_session_manager",
            None,
        )

        if manager is not None:
            if not self._release_music_lane():
                self.mode_changed.emit(
                    payload
                )
                return

            if not self._start_legacy_discord():
                self.mode_changed.emit(
                    payload
                )
                return

        self.discord.update_custom(
            title=payload["title"],
            message=payload["message"],
            image_bytes=(
                payload["image_bytes"]
            ),
            image_name=(
                payload["image_name"]
            ),
            show_elapsed=(
                payload["show_elapsed"]
            ),
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

    def handle_song(
        self,
        song,
    ):
        self._latest_song = song

        if self._auto_afk_active:
            return

        if self.active_mode != "music":
            return

        manager = getattr(
            self,
            "discord_session_manager",
            None,
        )

        if manager is not None:
            if not self._stop_legacy_discord():
                self._release_music_lane()
                return

            music_mode = self.load_mode(
                "music"
            )

            self._publish_music_with_manager(
                music_mode,
                song,
            )

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
