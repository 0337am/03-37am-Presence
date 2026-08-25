from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.spotify.session_manager import (
    SpotifySessionManagerError,
    SpotifySessionStatus,
)
from src.spotify.web_api import (
    SpotifyWebApiClient,
    SpotifyWebApiError,
)


class SpotifyPlaybackServiceStatus(
    str,
    Enum,
):
    READY = "ready"
    DISCONNECTED = "disconnected"
    REAUTHORIZATION_REQUIRED = (
        "reauthorization_required"
    )
    ERROR = "error"


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyPlaybackServiceResult:
    status: SpotifyPlaybackServiceStatus
    message: str = ""
    error_code: str = ""
    retry_after_seconds: int | None = None
    refreshed: bool = False

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            SpotifyPlaybackServiceStatus,
        ):
            raise TypeError(
                (
                    "status must be a "
                    "SpotifyPlaybackServiceStatus"
                )
            )

        if not isinstance(
            self.message,
            str,
        ):
            raise TypeError(
                "message must be a string"
            )

        if not isinstance(
            self.error_code,
            str,
        ):
            raise TypeError(
                "error_code must be a string"
            )

        if not isinstance(
            self.refreshed,
            bool,
        ):
            raise TypeError(
                "refreshed must be a boolean"
            )

        if (
            self.retry_after_seconds
            is not None
        ):
            if (
                isinstance(
                    self.retry_after_seconds,
                    bool,
                )
                or not isinstance(
                    self.retry_after_seconds,
                    int,
                )
            ):
                raise TypeError(
                    (
                        "retry_after_seconds must "
                        "be an integer or None"
                    )
                )

            if (
                self.retry_after_seconds
                < 0
            ):
                raise ValueError(
                    (
                        "retry_after_seconds cannot "
                        "be negative"
                    )
                )

        if (
            self.status
            is SpotifyPlaybackServiceStatus.ERROR
            and not self.error_code.strip()
        ):
            raise ValueError(
                (
                    "Playback error results require "
                    "an error_code."
                )
            )

        if (
            self.status
            is not SpotifyPlaybackServiceStatus.ERROR
            and self.error_code.strip()
        ):
            raise ValueError(
                (
                    "Non-error playback results "
                    "cannot expose an error_code."
                )
            )

    @property
    def ready(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyPlaybackServiceStatus.READY
        )

    @property
    def connected(
        self,
    ) -> bool:
        return (
            self.status
            is not SpotifyPlaybackServiceStatus
            .DISCONNECTED
        )

    @property
    def requires_reauthorization(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyPlaybackServiceStatus
            .REAUTHORIZATION_REQUIRED
        )


def _validate_catalogue_track_uri(
    spotify_uri,
) -> str:
    if not isinstance(
        spotify_uri,
        str,
    ):
        raise TypeError(
            "Spotify track URI must be a string."
        )

    checked = spotify_uri.strip()

    if not checked:
        raise ValueError(
            "Spotify track URI cannot be empty."
        )

    if len(checked) > 512:
        raise ValueError(
            "Spotify track URI is too long."
        )

    if any(
        ord(character) < 32
        or ord(character) == 127
        for character in checked
    ):
        raise ValueError(
            (
                "Spotify track URI cannot contain "
                "control characters."
            )
        )

    parts = checked.split(":")

    if (
        len(parts) != 3
        or parts[0] != "spotify"
        or parts[1] != "track"
        or not parts[2]
    ):
        raise ValueError(
            (
                "Playback requires a Spotify "
                "catalogue track URI."
            )
        )

    track_id = parts[2]

    if (
        not track_id.isascii()
        or not track_id.isalnum()
    ):
        raise ValueError(
            (
                "Spotify catalogue track URI "
                "contains an invalid track ID."
            )
        )

    return checked


class SpotifyPlaybackService:
    def __init__(
        self,
        session_manager,
        *,
        api_client=None,
    ) -> None:
        resolve = getattr(
            session_manager,
            "resolve",
            None,
        )

        if not callable(
            resolve
        ):
            raise TypeError(
                (
                    "session_manager must provide "
                    "a callable resolve method"
                )
            )

        if api_client is None:
            api_client = (
                SpotifyWebApiClient()
            )

        start_playback = getattr(
            api_client,
            "start_playback",
            None,
        )

        if not callable(
            start_playback
        ):
            raise TypeError(
                (
                    "api_client must provide a "
                    "callable start_playback method"
                )
            )

        start_playlist_playback = getattr(
            api_client,
            "start_playlist_playback",
            None,
        )

        if not callable(
            start_playlist_playback
        ):
            raise TypeError(
                (
                    "api_client must provide a "
                    "callable start_playlist_playback "
                    "method"
                )
            )

        start_playlist_position_playback = getattr(
            api_client,
            "start_playlist_position_playback",
            None,
        )

        if not callable(
            start_playlist_position_playback
        ):
            raise TypeError(
                (
                    "api_client must provide a "
                    "callable "
                    "start_playlist_position_playback "
                    "method"
                )
            )

        get_available_devices = getattr(
            api_client,
            "get_available_devices",
            None,
        )

        if not callable(
            get_available_devices
        ):
            raise TypeError(
                (
                    "api_client must provide a "
                    "callable get_available_devices "
                    "method"
                )
            )

        self._session_manager = (
            session_manager
        )

        self._api_client = (
            api_client
        )

    @staticmethod
    def _error(
        error_code: str,
        message: str,
        *,
        retry_after_seconds=None,
        refreshed: bool = False,
    ) -> SpotifyPlaybackServiceResult:
        return SpotifyPlaybackServiceResult(
            status=(
                SpotifyPlaybackServiceStatus.ERROR
            ),
            message=message,
            error_code=(
                str(
                    error_code
                    or "playback_error"
                )
            ),
            retry_after_seconds=(
                retry_after_seconds
            ),
            refreshed=refreshed,
        )

    def _resolve_session(
        self,
    ):
        try:
            session = (
                self._session_manager
                .resolve()
            )

        except SpotifySessionManagerError:
            return (
                "",
                False,
                self._error(
                    "session_error",
                    (
                        "Spotify playback could not "
                        "restore the saved session."
                    ),
                ),
            )

        except Exception:
            return (
                "",
                False,
                self._error(
                    "session_error",
                    (
                        "Spotify playback could not "
                        "restore the saved session."
                    ),
                ),
            )

        status = getattr(
            session,
            "status",
            None,
        )

        if (
            status
            is SpotifySessionStatus.DISCONNECTED
        ):
            return (
                "",
                False,
                SpotifyPlaybackServiceResult(
                    status=(
                        SpotifyPlaybackServiceStatus
                        .DISCONNECTED
                    ),
                    message=(
                        "Connect Spotify before "
                        "starting playback."
                    ),
                ),
            )

        if (
            status
            is SpotifySessionStatus
            .REAUTHORIZATION_REQUIRED
        ):
            return (
                "",
                False,
                SpotifyPlaybackServiceResult(
                    status=(
                        SpotifyPlaybackServiceStatus
                        .REAUTHORIZATION_REQUIRED
                    ),
                    message=(
                        "Reconnect Spotify before "
                        "starting playback."
                    ),
                ),
            )

        if status not in {
            SpotifySessionStatus.READY,
            SpotifySessionStatus.REFRESHED,
        }:
            return (
                "",
                False,
                self._error(
                    "invalid_session_state",
                    (
                        "Spotify returned an "
                        "unexpected session state."
                    ),
                ),
            )

        refreshed = (
            status
            is SpotifySessionStatus.REFRESHED
        )

        token = getattr(
            session,
            "token",
            None,
        )

        access_token = getattr(
            token,
            "access_token",
            None,
        )

        if (
            not isinstance(
                access_token,
                str,
            )
            or not access_token
        ):
            return (
                "",
                refreshed,
                self._error(
                    "invalid_session",
                    (
                        "Spotify playback could not "
                        "use the saved session."
                    ),
                    refreshed=refreshed,
                ),
            )

        return (
            access_token,
            refreshed,
            None,
        )

    def _api_error(
        self,
        error,
        *,
        refreshed: bool,
    ) -> SpotifyPlaybackServiceResult:
        error_code = str(
            getattr(
                error,
                "error_code",
                "",
            )
            or "spotify_api_error"
        )

        if (
            error_code
            == "reauthorization_required"
        ):
            return SpotifyPlaybackServiceResult(
                status=(
                    SpotifyPlaybackServiceStatus
                    .REAUTHORIZATION_REQUIRED
                ),
                message=(
                    "Reconnect Spotify before "
                    "starting playback."
                ),
                refreshed=refreshed,
            )

        retry_after = getattr(
            error,
            "retry_after_seconds",
            None,
        )

        if (
            isinstance(
                retry_after,
                bool,
            )
            or not isinstance(
                retry_after,
                int,
            )
        ):
            retry_after = None

        if (
            error_code
            in {
                "rate_limited",
                "quota_exceeded",
            }
        ):
            message = (
                "Spotify is limiting playback "
                "requests. Try again shortly."
            )

        elif (
            error_code
            in {
                "forbidden",
                "playback_forbidden",
            }
        ):
            message = (
                "Spotify could not start playback "
                "on the current device."
            )

        else:
            message = (
                "Spotify playback could not "
                "be started."
            )

        return self._error(
            error_code,
            message,
            retry_after_seconds=(
                retry_after
            ),
            refreshed=refreshed,
        )

    @staticmethod
    def _usable_device_id(
        payload,
    ) -> str | None:
        if not isinstance(
            payload,
            dict,
        ):
            return None

        devices = payload.get(
            "devices",
            (),
        )

        if not isinstance(
            devices,
            list,
        ):
            return None

        usable = []

        for device in devices:
            if not isinstance(
                device,
                dict,
            ):
                continue

            if bool(
                device.get(
                    "is_restricted",
                    False,
                )
            ):
                continue

            device_id = device.get(
                "id"
            )

            if not isinstance(
                device_id,
                str,
            ):
                continue

            device_id = device_id.strip()

            if not device_id:
                continue

            usable.append(
                (
                    device,
                    device_id,
                )
            )

        for (
            device,
            device_id,
        ) in usable:
            if bool(
                device.get(
                    "is_active",
                    False,
                )
            ):
                return device_id

        for (
            device,
            device_id,
        ) in usable:
            device_type = str(
                device.get(
                    "type",
                    "",
                )
                or ""
            ).strip().lower()

            if device_type == "computer":
                return device_id

        if usable:
            return usable[0][1]

        return None

    @staticmethod
    def _album_uri(
        album_id,
    ) -> str:
        if not isinstance(
            album_id,
            str,
        ):
            raise TypeError(
                "album_id must be a string"
            )

        checked = album_id.strip()

        if (
            not checked
            or not checked.isascii()
            or not checked.isalnum()
        ):
            raise ValueError(
                "album_id is invalid"
            )

        return (
            "spotify:album:"
            + checked
        )

    @staticmethod
    def _playlist_uri(
        playlist_id,
    ) -> str:
        if not isinstance(
            playlist_id,
            str,
        ):
            raise TypeError(
                "playlist_id must be a string"
            )

        checked = playlist_id.strip()

        if (
            not checked
            or not checked.isascii()
            or not checked.isalnum()
        ):
            raise ValueError(
                "playlist_id is invalid"
            )

        return (
            "spotify:playlist:"
            + checked
        )

    @staticmethod
    def _playlist_position(
        position,
    ) -> int:
        if (
            isinstance(
                position,
                bool,
            )
            or not isinstance(
                position,
                int,
            )
        ):
            raise TypeError(
                (
                    "playlist position must "
                    "be an integer"
                )
            )

        if position < 0:
            raise ValueError(
                (
                    "playlist position cannot "
                    "be negative"
                )
            )

        return position

    def _run_transport_control(
        self,
        api_method_name: str,
        success_message: str,
        *api_args,
    ) -> SpotifyPlaybackServiceResult:
        api_method = getattr(
            self._api_client,
            api_method_name,
            None,
        )

        if not callable(api_method):
            return self._error(
                "invalid_playback_api",
                (
                    "Spotify playback controls "
                    "are unavailable."
                ),
            )

        (
            access_token,
            refreshed,
            session_error,
        ) = self._resolve_session()

        if session_error is not None:
            return session_error

        device_id = None

        try:
            device_payload = (
                self._api_client
                .get_available_devices(
                    access_token
                )
            )

            device_id = (
                self._usable_device_id(
                    device_payload
                )
            )

        except SpotifyWebApiError as error:
            error_code = str(
                getattr(
                    error,
                    "error_code",
                    "",
                )
                or ""
            )

            if (
                error_code
                == "reauthorization_required"
            ):
                return self._api_error(
                    error,
                    refreshed=refreshed,
                )

            device_id = None

        except Exception:
            device_id = None

        try:
            api_method(
                access_token,
                *api_args,
                device_id=device_id,
            )

        except SpotifyWebApiError as error:
            return self._api_error(
                error,
                refreshed=refreshed,
            )

        except (
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_playback_request",
                (
                    "Spotify playback control "
                    "request was invalid."
                ),
                refreshed=refreshed,
            )

        except Exception:
            return self._error(
                "playback_failed",
                (
                    "Spotify playback control "
                    "failed."
                ),
                refreshed=refreshed,
            )

        return SpotifyPlaybackServiceResult(
            status=(
                SpotifyPlaybackServiceStatus.READY
            ),
            message=success_message,
            refreshed=refreshed,
        )

    def set_shuffle(
        self,
        enabled,
    ) -> SpotifyPlaybackServiceResult:
        if not isinstance(
            enabled,
            bool,
        ):
            return self._error(
                "invalid_shuffle_state",
                "Spotify shuffle state is invalid.",
            )

        return self._run_transport_control(
            "set_shuffle",
            "Spotify shuffle was updated.",
            enabled,
        )

    def set_repeat_mode(
        self,
        mode,
    ) -> SpotifyPlaybackServiceResult:
        if not isinstance(
            mode,
            str,
        ):
            return self._error(
                "invalid_repeat_mode",
                "Spotify repeat mode is invalid.",
            )

        checked = mode.strip()

        if (
            checked != mode
            or checked
            not in {
                "off",
                "context",
                "track",
            }
        ):
            return self._error(
                "invalid_repeat_mode",
                "Spotify repeat mode is invalid.",
            )

        return self._run_transport_control(
            "set_repeat_mode",
            "Spotify repeat mode was updated.",
            checked,
        )

    def seek_to_seconds(
        self,
        seconds,
    ) -> SpotifyPlaybackServiceResult:
        if isinstance(
            seconds,
            bool,
        ):
            return self._error(
                "invalid_seek_position",
                "Spotify seek position is invalid.",
            )

        try:
            from math import isfinite

            position_seconds = float(
                seconds
            )

            if (
                not isfinite(
                    position_seconds
                )
                or position_seconds < 0
            ):
                raise ValueError

            position_ms = int(
                round(
                    position_seconds
                    * 1000.0
                )
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return self._error(
                "invalid_seek_position",
                "Spotify seek position is invalid.",
            )

        return self._run_transport_control(
            "seek_to_position",
            "Spotify playback position updated.",
            position_ms,
        )

    def add_to_queue(
        self,
        spotify_uri,
    ) -> SpotifyPlaybackServiceResult:
        return self._run_transport_control(
            "add_to_queue",
            "Spotify item added to Queue.",
            spotify_uri,
        )

    def resume_playback(
        self,
    ) -> SpotifyPlaybackServiceResult:
        return self._run_transport_control(
            "resume_playback",
            "Spotify playback resumed.",
        )

    def pause_playback(
        self,
    ) -> SpotifyPlaybackServiceResult:
        return self._run_transport_control(
            "pause_playback",
            "Spotify playback paused.",
        )

    def skip_next(
        self,
    ) -> SpotifyPlaybackServiceResult:
        return self._run_transport_control(
            "skip_next",
            "Skipped to the next Spotify item.",
        )

    def skip_previous(
        self,
    ) -> SpotifyPlaybackServiceResult:
        return self._run_transport_control(
            "skip_previous",
            "Skipped to the previous Spotify item.",
        )

    def play_track(
        self,
        spotify_uri,
    ) -> SpotifyPlaybackServiceResult:
        try:
            checked_uri = (
                _validate_catalogue_track_uri(
                    spotify_uri
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_track_uri",
                (
                    "This item is not a playable "
                    "Spotify catalogue track."
                ),
            )

        (
            access_token,
            refreshed,
            session_error,
        ) = self._resolve_session()

        if session_error is not None:
            return session_error

        device_id = None

        try:
            device_payload = (
                self._api_client
                .get_available_devices(
                    access_token
                )
            )

            device_id = (
                self._usable_device_id(
                    device_payload
                )
            )

        except SpotifyWebApiError as error:
            error_code = str(
                getattr(
                    error,
                    "error_code",
                    "",
                )
                or ""
            )

            if (
                error_code
                == "reauthorization_required"
            ):
                return self._api_error(
                    error,
                    refreshed=refreshed,
                )

            # Device discovery is helpful but not
            # required. Spotify can still target an
            # already-active device when no ID is sent.
            device_id = None

        except Exception:
            device_id = None

        try:
            self._api_client.start_playback(
                access_token,
                checked_uri,
                device_id=device_id,
            )

        except SpotifyWebApiError as error:
            return self._api_error(
                error,
                refreshed=refreshed,
            )

        except (
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_playback_request",
                (
                    "Spotify playback could not "
                    "use this track."
                ),
                refreshed=refreshed,
            )

        except Exception:
            return self._error(
                "playback_failed",
                (
                    "Spotify playback could not "
                    "be started."
                ),
                refreshed=refreshed,
            )

        return SpotifyPlaybackServiceResult(
            status=(
                SpotifyPlaybackServiceStatus.READY
            ),
            message=(
                "Spotify playback started."
            ),
            refreshed=refreshed,
        )

    def play_playlist_position(
        self,
        playlist_id,
        position,
    ) -> SpotifyPlaybackServiceResult:
        try:
            playlist_uri = (
                self._playlist_uri(
                    playlist_id
                )
            )

            checked_position = (
                self._playlist_position(
                    position
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_playlist_playback",
                (
                    "This playlist position "
                    "could not be started."
                ),
            )

        (
            access_token,
            refreshed,
            session_error,
        ) = self._resolve_session()

        if session_error is not None:
            return session_error

        device_id = None

        try:
            device_payload = (
                self._api_client
                .get_available_devices(
                    access_token
                )
            )

            device_id = (
                self._usable_device_id(
                    device_payload
                )
            )

        except SpotifyWebApiError as error:
            error_code = str(
                getattr(
                    error,
                    "error_code",
                    "",
                )
                or ""
            )

            if (
                error_code
                == "reauthorization_required"
            ):
                return self._api_error(
                    error,
                    refreshed=refreshed,
                )

            # Device discovery is helpful but not
            # required. Spotify can still target an
            # already-active device when no ID is sent.
            device_id = None

        except Exception:
            device_id = None

        try:
            (
                self._api_client
                .start_playlist_position_playback(
                    access_token,
                    playlist_uri,
                    checked_position,
                    device_id=device_id,
                )
            )

        except SpotifyWebApiError as error:
            return self._api_error(
                error,
                refreshed=refreshed,
            )

        except (
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_playback_request",
                (
                    "Spotify playback could not "
                    "use this playlist position."
                ),
                refreshed=refreshed,
            )

        except Exception:
            return self._error(
                "playback_failed",
                (
                    "Spotify playback could not "
                    "be started."
                ),
                refreshed=refreshed,
            )

        return SpotifyPlaybackServiceResult(
            status=(
                SpotifyPlaybackServiceStatus.READY
            ),
            message=(
                "Spotify playlist playback "
                "started."
            ),
            refreshed=refreshed,
        )

    def play_album_track(
        self,
        album_id,
        spotify_uri,
    ) -> SpotifyPlaybackServiceResult:
        try:
            album_uri = (
                self._album_uri(
                    album_id
                )
            )

            checked_uri = (
                _validate_catalogue_track_uri(
                    spotify_uri
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_album_playback",
                (
                    "This item could not be "
                    "started from the album."
                ),
            )

        (
            access_token,
            refreshed,
            session_error,
        ) = self._resolve_session()

        if session_error is not None:
            return session_error

        device_id = None

        try:
            device_payload = (
                self._api_client
                .get_available_devices(
                    access_token
                )
            )

            device_id = (
                self._usable_device_id(
                    device_payload
                )
            )

        except SpotifyWebApiError as error:
            error_code = str(
                getattr(
                    error,
                    "error_code",
                    "",
                )
                or ""
            )

            if (
                error_code
                == "reauthorization_required"
            ):
                return self._api_error(
                    error,
                    refreshed=refreshed,
                )

            device_id = None

        except Exception:
            device_id = None

        try:
            self._api_client.start_album_playback(
                access_token,
                album_uri,
                checked_uri,
                device_id=device_id,
            )

        except SpotifyWebApiError as error:
            return self._api_error(
                error,
                refreshed=refreshed,
            )

        except (
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_playback_request",
                (
                    "Spotify playback could not "
                    "use this album item."
                ),
                refreshed=refreshed,
            )

        except Exception:
            return self._error(
                "playback_failed",
                (
                    "Spotify playback could not "
                    "be started."
                ),
                refreshed=refreshed,
            )

        return SpotifyPlaybackServiceResult(
            status=(
                SpotifyPlaybackServiceStatus.READY
            ),
            message=(
                "Spotify album playback "
                "started."
            ),
            refreshed=refreshed,
        )

    def play_playlist_track(
        self,
        playlist_id,
        spotify_uri,
    ) -> SpotifyPlaybackServiceResult:
        try:
            playlist_uri = (
                self._playlist_uri(
                    playlist_id
                )
            )

            checked_uri = (
                _validate_catalogue_track_uri(
                    spotify_uri
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_playlist_playback",
                (
                    "This item could not be "
                    "started from the playlist."
                ),
            )

        (
            access_token,
            refreshed,
            session_error,
        ) = self._resolve_session()

        if session_error is not None:
            return session_error

        device_id = None

        try:
            device_payload = (
                self._api_client
                .get_available_devices(
                    access_token
                )
            )

            device_id = (
                self._usable_device_id(
                    device_payload
                )
            )

        except SpotifyWebApiError as error:
            error_code = str(
                getattr(
                    error,
                    "error_code",
                    "",
                )
                or ""
            )

            if (
                error_code
                == "reauthorization_required"
            ):
                return self._api_error(
                    error,
                    refreshed=refreshed,
                )

            # Device discovery is helpful but not
            # required. Spotify can still target an
            # already-active device when no ID is sent.
            device_id = None

        except Exception:
            device_id = None

        try:
            self._api_client.start_playlist_playback(
                access_token,
                playlist_uri,
                checked_uri,
                device_id=device_id,
            )

        except SpotifyWebApiError as error:
            return self._api_error(
                error,
                refreshed=refreshed,
            )

        except (
            TypeError,
            ValueError,
        ):
            return self._error(
                "invalid_playback_request",
                (
                    "Spotify playback could not "
                    "use this playlist item."
                ),
                refreshed=refreshed,
            )

        except Exception:
            return self._error(
                "playback_failed",
                (
                    "Spotify playback could not "
                    "be started."
                ),
                refreshed=refreshed,
            )

        return SpotifyPlaybackServiceResult(
            status=(
                SpotifyPlaybackServiceStatus.READY
            ),
            message=(
                "Spotify playlist playback "
                "started."
            ),
            refreshed=refreshed,
        )
