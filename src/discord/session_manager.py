from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY_ID,
    DiscordApplicationEntry,
    is_valid_user_entry_id,
)
from src.discord.extended_presence import (
    ExtendedDiscordPresence,
)
from src.discord.identity_preferences import (
    validate_discord_application_id,
)


MUSIC_LANE_ID = "music"
SECONDARY_LANE_ID = "secondary"

DISCORD_PRESENCE_LANE_IDS = (
    MUSIC_LANE_ID,
    SECONDARY_LANE_ID,
)


class DiscordPresenceSessionManagerError(
    ValueError
):
    pass


@dataclass(frozen=True, slots=True)
class DiscordPresenceSessionBinding:
    lane_id: str
    application_entry_id: str
    application_id: str


@dataclass(slots=True)
class _ActiveDiscordPresenceSession:
    binding: DiscordPresenceSessionBinding
    session: object


class DiscordPresenceSessionManager:
    """
    Owns the two v3.4 Discord Presence lanes.

    The manager never owns raw PyPresence RPC objects.
    Each ExtendedDiscordPresence session keeps its existing
    worker-owned RPC lifecycle.
    """

    def __init__(
        self,
        application_resolver: Callable[
            [str],
            DiscordApplicationEntry | None,
        ],
        *,
        session_factory=None,
    ) -> None:
        if not callable(
            application_resolver
        ):
            raise TypeError(
                "application_resolver must be callable."
            )

        if (
            session_factory is not None
            and not callable(
                session_factory
            )
        ):
            raise TypeError(
                "session_factory must be callable."
            )

        self._application_resolver = (
            application_resolver
        )

        self._session_factory = (
            session_factory
            or self._default_session_factory
        )

        self._sessions: dict[
            str,
            _ActiveDiscordPresenceSession,
        ] = {}

        self._last_errors: dict[
            str,
            str,
        ] = {}

        self._closed = False

    @staticmethod
    def _default_session_factory(
        *,
        client_id: str,
    ):
        return ExtendedDiscordPresence(
            client_id=client_id
        )

    @staticmethod
    def _normalize_lane_id(
        lane_id: object,
    ) -> str:
        normalized = str(
            lane_id or ""
        ).strip().lower()

        if (
            normalized
            not in DISCORD_PRESENCE_LANE_IDS
        ):
            raise (
                DiscordPresenceSessionManagerError(
                    "Discord Presence lane is invalid."
                )
            )

        return normalized

    @staticmethod
    def _normalize_application_entry_id(
        entry_id: object,
    ) -> str:
        normalized = (
            str(
                entry_id or ""
            )
            .replace("\x00", "")
            .strip()
        )

        if (
            normalized
            == BUILTIN_APPLICATION_ENTRY_ID
        ):
            return normalized

        if is_valid_user_entry_id(
            normalized
        ):
            return normalized

        raise DiscordPresenceSessionManagerError(
            "Discord application reference is invalid."
        )

    @property
    def is_closed(self) -> bool:
        return self._closed

    def binding_for_lane(
        self,
        lane_id: object,
    ) -> (
        DiscordPresenceSessionBinding
        | None
    ):
        lane = self._normalize_lane_id(
            lane_id
        )

        state = self._sessions.get(
            lane
        )

        if state is None:
            return None

        return state.binding

    def active_bindings(
        self,
    ) -> tuple[
        DiscordPresenceSessionBinding,
        ...,
    ]:
        return tuple(
            self._sessions[
                lane_id
            ].binding
            for lane_id
            in DISCORD_PRESENCE_LANE_IDS
            if lane_id in self._sessions
        )

    def last_error_for_lane(
        self,
        lane_id: object,
    ) -> str:
        lane = self._normalize_lane_id(
            lane_id
        )

        return self._last_errors.get(
            lane,
            "",
        )

    def ensure_lane(
        self,
        lane_id: object,
        application_entry_id: object,
    ) -> (
        DiscordPresenceSessionBinding
        | None
    ):
        lane = self._normalize_lane_id(
            lane_id
        )

        if self._closed:
            self._last_errors[
                lane
            ] = (
                "Discord Presence session manager "
                "is closed."
            )
            return None

        entry = self._resolve_entry(
            lane,
            application_entry_id,
        )

        if entry is None:
            return None

        application_id = (
            validate_discord_application_id(
                entry.application_id
            )
        )

        for (
            other_lane,
            other_state,
        ) in self._sessions.items():
            if other_lane == lane:
                continue

            if (
                other_state
                .binding
                .application_id
                == application_id
            ):
                self._fail_lane(
                    lane,
                    (
                        "Discord application is already "
                        "active in another Presence lane."
                    ),
                )
                return None

        current = self._sessions.get(
            lane
        )

        if (
            current is not None
            and current.binding
            .application_entry_id
            == entry.entry_id
            and current.binding
            .application_id
            == application_id
        ):
            try:
                connected = (
                    current.session.connect()
                )

            except Exception:
                self._fail_lane(
                    lane,
                    (
                        "Discord Presence session "
                        "could not reconnect."
                    ),
                )
                return None

            if connected is False:
                self._fail_lane(
                    lane,
                    (
                        "Discord Presence session "
                        "could not reconnect."
                    ),
                )
                return None

            self._last_errors.pop(
                lane,
                None,
            )

            return current.binding

        if current is not None:
            self._release_state(
                lane
            )

        session = None

        try:
            session = self._session_factory(
                client_id=application_id
            )

        except Exception:
            self._last_errors[
                lane
            ] = (
                "Discord Presence session "
                "could not be created."
            )
            return None

        if not self._valid_session(
            session
        ):
            self._best_effort_close_candidate(
                session
            )

            self._last_errors[
                lane
            ] = (
                "Discord Presence session "
                "interface is invalid."
            )
            return None

        try:
            connected = session.connect()

        except Exception:
            self._best_effort_close_candidate(
                session
            )

            self._last_errors[
                lane
            ] = (
                "Discord Presence session "
                "could not start."
            )
            return None

        if connected is False:
            self._best_effort_close_candidate(
                session
            )

            self._last_errors[
                lane
            ] = (
                "Discord Presence session "
                "could not start."
            )
            return None

        binding = (
            DiscordPresenceSessionBinding(
                lane_id=lane,
                application_entry_id=(
                    entry.entry_id
                ),
                application_id=(
                    application_id
                ),
            )
        )

        self._sessions[
            lane
        ] = (
            _ActiveDiscordPresenceSession(
                binding=binding,
                session=session,
            )
        )

        self._last_errors.pop(
            lane,
            None,
        )

        return binding

    def update_music(
        self,
        application_entry_id: object,
        song,
        *,
        buttons=None,
        show_loop_count: bool | None = None,
    ) -> bool:
        if (
            show_loop_count is not None
            and not isinstance(
                show_loop_count,
                bool,
            )
        ):
            self._last_errors[
                MUSIC_LANE_ID
            ] = (
                "Discord music loop-count "
                "setting is invalid."
            )
            return False

        binding = self.ensure_lane(
            MUSIC_LANE_ID,
            application_entry_id,
        )

        if binding is None:
            return False

        state = self._sessions.get(
            MUSIC_LANE_ID
        )

        if state is None:
            return False

        if show_loop_count is not None:
            loop_count_setter = getattr(
                state.session,
                "set_music_loop_count_enabled",
                None,
            )

            if callable(
                loop_count_setter
            ):
                try:
                    loop_count_setter(
                        show_loop_count
                    )

                except Exception:
                    self._last_errors[
                        MUSIC_LANE_ID
                    ] = (
                        "Discord music loop-count "
                        "setting failed."
                    )
                    return False

        try:
            state.session.update_song(
                song,
                buttons=buttons,
            )

        except Exception:
            self._last_errors[
                MUSIC_LANE_ID
            ] = (
                "Discord music Presence "
                "update failed."
            )
            return False

        self._last_errors.pop(
            MUSIC_LANE_ID,
            None,
        )

        return True

    def update_secondary(
        self,
        application_entry_id: object,
        *,
        title: str,
        message: str,
        image_bytes=None,
        image_name: str = "",
        show_elapsed: bool = False,
        buttons=None,
        party_size=None,
    ) -> bool:
        binding = self.ensure_lane(
            SECONDARY_LANE_ID,
            application_entry_id,
        )

        if binding is None:
            return False

        state = self._sessions.get(
            SECONDARY_LANE_ID
        )

        if state is None:
            return False

        try:
            state.session.update_custom(
                title=title,
                message=message,
                image_bytes=image_bytes,
                image_name=image_name,
                show_elapsed=show_elapsed,
                buttons=buttons,
                party_size=party_size,
            )

        except Exception:
            self._last_errors[
                SECONDARY_LANE_ID
            ] = (
                "Discord secondary Presence "
                "update failed."
            )
            return False

        self._last_errors.pop(
            SECONDARY_LANE_ID,
            None,
        )

        return True

    def clear_lane(
        self,
        lane_id: object,
    ) -> bool:
        lane = self._normalize_lane_id(
            lane_id
        )

        state = self._sessions.get(
            lane
        )

        if state is None:
            return True

        try:
            state.session.clear_presence()

        except Exception:
            self._last_errors[
                lane
            ] = (
                "Discord Presence lane "
                "could not be cleared."
            )
            return False

        self._last_errors.pop(
            lane,
            None,
        )

        return True

    def release_lane(
        self,
        lane_id: object,
    ) -> bool:
        lane = self._normalize_lane_id(
            lane_id
        )

        released = self._release_state(
            lane
        )

        if released:
            self._last_errors.pop(
                lane,
                None,
            )

        return released

    def close(self) -> bool:
        if self._closed:
            return True

        success = True

        for lane_id in (
            SECONDARY_LANE_ID,
            MUSIC_LANE_ID,
        ):
            if not self._release_state(
                lane_id
            ):
                success = False

        self._closed = True

        return success

    def _resolve_entry(
        self,
        lane: str,
        application_entry_id: object,
    ) -> DiscordApplicationEntry | None:
        try:
            normalized_id = (
                self
                ._normalize_application_entry_id(
                    application_entry_id
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            self._fail_lane(
                lane,
                (
                    "Discord application reference "
                    "is unavailable."
                ),
            )
            return None

        try:
            entry = (
                self._application_resolver(
                    normalized_id
                )
            )

        except Exception:
            self._fail_lane(
                lane,
                (
                    "Discord application reference "
                    "could not be resolved."
                ),
            )
            return None

        if entry is None:
            self._fail_lane(
                lane,
                (
                    "Discord application reference "
                    "is unavailable."
                ),
            )
            return None

        if not isinstance(
            entry,
            DiscordApplicationEntry,
        ):
            self._fail_lane(
                lane,
                (
                    "Discord application reference "
                    "is invalid."
                ),
            )
            return None

        if (
            entry.entry_id
            != normalized_id
        ):
            self._fail_lane(
                lane,
                (
                    "Discord application reference "
                    "did not resolve safely."
                ),
            )
            return None

        try:
            validate_discord_application_id(
                entry.application_id
            )

        except (
            TypeError,
            ValueError,
        ):
            self._fail_lane(
                lane,
                (
                    "Discord application ID "
                    "is invalid."
                ),
            )
            return None

        return entry

    @staticmethod
    def _valid_session(
        session,
    ) -> bool:
        if session is None:
            return False

        return all(
            callable(
                getattr(
                    session,
                    method_name,
                    None,
                )
            )
            for method_name in (
                "connect",
                "update_song",
                "update_custom",
                "clear_presence",
                "close",
            )
        )

    def _fail_lane(
        self,
        lane: str,
        message: str,
    ) -> None:
        self._release_state(
            lane
        )

        self._last_errors[
            lane
        ] = str(
            message or ""
        ).strip()

    def _release_state(
        self,
        lane: str,
    ) -> bool:
        state = self._sessions.pop(
            lane,
            None,
        )

        if state is None:
            return True

        success = True

        try:
            state.session.clear_presence()

        except Exception:
            success = False

        try:
            state.session.close()

        except Exception:
            success = False

        if not success:
            self._last_errors[
                lane
            ] = (
                "Discord Presence lane "
                "cleanup failed."
            )

        return success

    @staticmethod
    def _best_effort_close_candidate(
        session,
    ) -> None:
        close = getattr(
            session,
            "close",
            None,
        )

        if not callable(
            close
        ):
            return

        try:
            close()

        except Exception:
            pass
