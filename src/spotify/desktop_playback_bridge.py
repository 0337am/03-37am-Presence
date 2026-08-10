from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum


UIA_BUTTON_CONTROL_TYPE_ID = 50000
UIA_DATA_GRID_CONTROL_TYPE_ID = 50028

DEFAULT_MAX_NODES = 20_000
DEFAULT_MAX_DEPTH = 60


class SpotifyDesktopDiscoveryStatus(
    str,
    Enum,
):
    READY = "ready"
    SPOTIFY_NOT_FOUND = "spotify_not_found"
    PLAYLIST_NOT_FOUND = "playlist_not_found"
    PLAY_CONTROL_NOT_FOUND = (
        "play_control_not_found"
    )
    PLAY_CONTROL_UNAVAILABLE = (
        "play_control_unavailable"
    )
    AUTOMATION_UNAVAILABLE = (
        "automation_unavailable"
    )
    ERROR = "error"


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyDesktopDiscoveryResult:
    status: SpotifyDesktopDiscoveryStatus
    playlist_name: str
    title: str
    artist: str
    button_name: str = ""
    already_playing: bool = False
    now_playing_confirmed: bool = False
    message: str = ""

    @property
    def ready(
        self,
    ) -> bool:
        return (
            self.status
            is SpotifyDesktopDiscoveryStatus.READY
        )


class SpotifyDesktopAutomationUnavailable(
    RuntimeError
):
    pass


def _validated_text(
    value,
    field_name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be a string"
        )

    checked = value.strip()

    if (
        not checked
        or checked != value
    ):
        raise ValueError(
            f"{field_name} is invalid"
        )

    return checked


def _semantic_text(
    value,
) -> str:
    return " ".join(
        str(
            value
            or ""
        ).split()
    ).casefold()


class WindowsSpotifyUiAutomationBackend:
    def __init__(
        self,
        *,
        max_nodes: int = DEFAULT_MAX_NODES,
        max_depth: int = DEFAULT_MAX_DEPTH,
    ) -> None:
        if (
            isinstance(
                max_nodes,
                bool,
            )
            or not isinstance(
                max_nodes,
                int,
            )
            or max_nodes < 1
        ):
            raise ValueError(
                "max_nodes must be a positive integer"
            )

        if (
            isinstance(
                max_depth,
                bool,
            )
            or not isinstance(
                max_depth,
                int,
            )
            or max_depth < 1
        ):
            raise ValueError(
                "max_depth must be a positive integer"
            )

        self._max_nodes = max_nodes
        self._max_depth = max_depth

        self._uia = None
        self._walker = None
        self._client = None

    def _ensure_runtime(
        self,
    ) -> None:
        if self._uia is not None:
            return

        try:
            import comtypes.client

            comtypes.client.GetModule(
                "UIAutomationCore.dll"
            )

            from comtypes.gen import (
                UIAutomationClient,
            )

            uia = (
                comtypes.client.CreateObject(
                    UIAutomationClient
                    .CUIAutomation
                    ._reg_clsid_,
                    interface=(
                        UIAutomationClient
                        .IUIAutomation
                    ),
                )
            )

        except Exception as error:
            raise SpotifyDesktopAutomationUnavailable(
                (
                    "Windows UI Automation "
                    "could not be initialized."
                )
            ) from error

        if uia is None:
            raise SpotifyDesktopAutomationUnavailable(
                (
                    "Windows UI Automation "
                    "returned no client."
                )
            )

        walker = uia.RawViewWalker

        if walker is None:
            raise SpotifyDesktopAutomationUnavailable(
                (
                    "Windows UI Automation "
                    "raw view is unavailable."
                )
            )

        self._uia = uia
        self._walker = walker
        self._client = (
            UIAutomationClient
        )

    @staticmethod
    def _window_title(
        user32,
        hwnd,
    ) -> str:
        length = (
            user32.GetWindowTextLengthW(
                hwnd
            )
        )

        if length <= 0:
            return ""

        buffer = (
            ctypes.create_unicode_buffer(
                length + 1
            )
        )

        user32.GetWindowTextW(
            hwnd,
            buffer,
            len(buffer),
        )

        return (
            buffer.value.strip()
        )

    def find_spotify_window(
        self,
    ):
        if (
            getattr(
                ctypes,
                "WinDLL",
                None,
            )
            is None
        ):
            raise SpotifyDesktopAutomationUnavailable(
                (
                    "Spotify desktop automation "
                    "requires Windows."
                )
            )

        user32 = ctypes.WinDLL(
            "user32",
            use_last_error=True,
        )

        callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM,
        )

        user32.EnumWindows.argtypes = (
            callback_type,
            wintypes.LPARAM,
        )

        user32.EnumWindows.restype = (
            wintypes.BOOL
        )

        user32.IsWindowVisible.argtypes = (
            wintypes.HWND,
        )

        user32.IsWindowVisible.restype = (
            wintypes.BOOL
        )

        user32.GetWindowTextLengthW.argtypes = (
            wintypes.HWND,
        )

        user32.GetWindowTextLengthW.restype = (
            ctypes.c_int
        )

        user32.GetWindowTextW.argtypes = (
            wintypes.HWND,
            wintypes.LPWSTR,
            ctypes.c_int,
        )

        user32.GetWindowTextW.restype = (
            ctypes.c_int
        )

        candidates = []

        @callback_type
        def callback(
            hwnd,
            lparam,
        ):
            if not user32.IsWindowVisible(
                hwnd
            ):
                return True

            title = self._window_title(
                user32,
                hwnd,
            )

            if (
                title
                and "spotify"
                in title.casefold()
            ):
                candidates.append(
                    (
                        int(
                            hwnd
                        ),
                        title,
                    )
                )

            return True

        if not user32.EnumWindows(
            callback,
            0,
        ):
            raise ctypes.WinError(
                ctypes.get_last_error()
            )

        if not candidates:
            return None

        preferred_titles = (
            "spotify premium",
            "spotify",
        )

        for preferred in preferred_titles:
            for hwnd, title in candidates:
                if (
                    title.casefold()
                    == preferred
                ):
                    return hwnd

        return candidates[0][0]

    def root_from_handle(
        self,
        hwnd,
    ):
        self._ensure_runtime()

        if not hwnd:
            return None

        try:
            return (
                self._uia.ElementFromHandle(
                    ctypes.c_void_p(
                        int(
                            hwnd
                        )
                    )
                )
            )

        except TypeError:
            return (
                self._uia.ElementFromHandle(
                    int(
                        hwnd
                    )
                )
            )

    @staticmethod
    def name(
        element,
    ) -> str:
        try:
            return str(
                element.CurrentName
                or ""
            ).strip()

        except Exception:
            return ""

    @staticmethod
    def control_type(
        element,
    ) -> int:
        try:
            return int(
                element.CurrentControlType
            )

        except Exception:
            return -1

    def iter_descendants(
        self,
        root,
    ):
        self._ensure_runtime()

        if root is None:
            return

        stack = [
            (
                root,
                0,
            )
        ]

        visited = 0

        while stack:
            element, depth = (
                stack.pop()
            )

            if depth > 0:
                visited += 1

                if (
                    visited
                    > self._max_nodes
                ):
                    return

                yield element

            if (
                depth
                >= self._max_depth
            ):
                continue

            try:
                child = (
                    self._walker
                    .GetFirstChildElement(
                        element
                    )
                )

            except Exception:
                child = None

            children = []
            child_guard = 0

            while child is not None:
                child_guard += 1

                if child_guard > 5000:
                    break

                children.append(
                    child
                )

                try:
                    child = (
                        self._walker
                        .GetNextSiblingElement(
                            child
                        )
                    )

                except Exception:
                    break

            for child in reversed(
                children
            ):
                stack.append(
                    (
                        child,
                        depth + 1,
                    )
                )

    def supports_invoke(
        self,
        element,
    ) -> bool:
        self._ensure_runtime()

        pattern_id = getattr(
            self._client,
            "UIA_InvokePatternId",
            10000,
        )

        try:
            pattern = (
                element.GetCurrentPattern(
                    pattern_id
                )
            )

        except Exception:
            return False

        return pattern is not None


class SpotifyDesktopPlaybackBridge:
    def __init__(
        self,
        backend=None,
    ) -> None:
        self._backend = (
            WindowsSpotifyUiAutomationBackend()
            if backend is None
            else backend
        )

        required = (
            "find_spotify_window",
            "root_from_handle",
            "iter_descendants",
            "name",
            "control_type",
            "supports_invoke",
        )

        missing = [
            member
            for member in required
            if not callable(
                getattr(
                    self._backend,
                    member,
                    None,
                )
            )
        ]

        if missing:
            raise TypeError(
                (
                    "backend is missing: "
                    + ", ".join(
                        missing
                    )
                )
            )

    def _now_playing_confirmed(
        self,
        root,
        title: str,
        artist: str,
    ) -> bool:
        expected = _semantic_text(
            (
                "Now playing: "
                + title
                + " by "
                + artist
            )
        )

        for element in (
            self._backend
            .iter_descendants(
                root
            )
        ):
            if (
                _semantic_text(
                    self._backend.name(
                        element
                    )
                )
                == expected
            ):
                return True

        return False

    def discover_local_track(
        self,
        *,
        playlist_name,
        title,
        artist,
    ) -> SpotifyDesktopDiscoveryResult:
        playlist = _validated_text(
            playlist_name,
            "playlist_name",
        )

        track_title = _validated_text(
            title,
            "title",
        )

        track_artist = _validated_text(
            artist,
            "artist",
        )

        try:
            hwnd = (
                self._backend
                .find_spotify_window()
            )

            if not hwnd:
                return (
                    SpotifyDesktopDiscoveryResult(
                        status=(
                            SpotifyDesktopDiscoveryStatus
                            .SPOTIFY_NOT_FOUND
                        ),
                        playlist_name=playlist,
                        title=track_title,
                        artist=track_artist,
                        message=(
                            "Spotify desktop is not open."
                        ),
                    )
                )

            root = (
                self._backend
                .root_from_handle(
                    hwnd
                )
            )

            if root is None:
                return (
                    SpotifyDesktopDiscoveryResult(
                        status=(
                            SpotifyDesktopDiscoveryStatus
                            .AUTOMATION_UNAVAILABLE
                        ),
                        playlist_name=playlist,
                        title=track_title,
                        artist=track_artist,
                        message=(
                            "Spotify desktop could not "
                            "be inspected."
                        ),
                    )
                )

            expected_playlist = (
                _semantic_text(
                    playlist
                )
            )

            playlist_grid = None

            for element in (
                self._backend
                .iter_descendants(
                    root
                )
            ):
                if (
                    self._backend
                    .control_type(
                        element
                    )
                    != UIA_DATA_GRID_CONTROL_TYPE_ID
                ):
                    continue

                if (
                    _semantic_text(
                        self._backend.name(
                            element
                        )
                    )
                    == expected_playlist
                ):
                    playlist_grid = element
                    break

            if playlist_grid is None:
                return (
                    SpotifyDesktopDiscoveryResult(
                        status=(
                            SpotifyDesktopDiscoveryStatus
                            .PLAYLIST_NOT_FOUND
                        ),
                        playlist_name=playlist,
                        title=track_title,
                        artist=track_artist,
                        message=(
                            "Open this playlist in "
                            "Spotify desktop first."
                        ),
                    )
                )

            expected_play = _semantic_text(
                (
                    "Play "
                    + track_title
                    + " by "
                    + track_artist
                )
            )

            expected_pause = _semantic_text(
                (
                    "Pause "
                    + track_title
                    + " by "
                    + track_artist
                )
            )

            play_control = None
            button_name = ""
            already_playing = False

            for element in (
                self._backend
                .iter_descendants(
                    playlist_grid
                )
            ):
                if (
                    self._backend
                    .control_type(
                        element
                    )
                    != UIA_BUTTON_CONTROL_TYPE_ID
                ):
                    continue

                name = (
                    self._backend.name(
                        element
                    )
                )

                semantic_name = (
                    _semantic_text(
                        name
                    )
                )

                if (
                    semantic_name
                    == expected_pause
                ):
                    play_control = element
                    button_name = name
                    already_playing = True
                    break

                if (
                    semantic_name
                    == expected_play
                ):
                    play_control = element
                    button_name = name

            if play_control is None:
                return (
                    SpotifyDesktopDiscoveryResult(
                        status=(
                            SpotifyDesktopDiscoveryStatus
                            .PLAY_CONTROL_NOT_FOUND
                        ),
                        playlist_name=playlist,
                        title=track_title,
                        artist=track_artist,
                        message=(
                            "Spotify's local-track play "
                            "control could not be found."
                        ),
                    )
                )

            now_playing = (
                self._now_playing_confirmed(
                    root,
                    track_title,
                    track_artist,
                )
            )

            if (
                not already_playing
                and not self._backend
                .supports_invoke(
                    play_control
                )
            ):
                return (
                    SpotifyDesktopDiscoveryResult(
                        status=(
                            SpotifyDesktopDiscoveryStatus
                            .PLAY_CONTROL_UNAVAILABLE
                        ),
                        playlist_name=playlist,
                        title=track_title,
                        artist=track_artist,
                        button_name=button_name,
                        now_playing_confirmed=(
                            now_playing
                        ),
                        message=(
                            "Spotify's local-track play "
                            "control is unavailable."
                        ),
                    )
                )

            return (
                SpotifyDesktopDiscoveryResult(
                    status=(
                        SpotifyDesktopDiscoveryStatus
                        .READY
                    ),
                    playlist_name=playlist,
                    title=track_title,
                    artist=track_artist,
                    button_name=button_name,
                    already_playing=(
                        already_playing
                    ),
                    now_playing_confirmed=(
                        now_playing
                    ),
                    message=(
                        "Spotify local-track playback "
                        "control is ready."
                    ),
                )
            )

        except SpotifyDesktopAutomationUnavailable:
            return (
                SpotifyDesktopDiscoveryResult(
                    status=(
                        SpotifyDesktopDiscoveryStatus
                        .AUTOMATION_UNAVAILABLE
                    ),
                    playlist_name=playlist,
                    title=track_title,
                    artist=track_artist,
                    message=(
                        "Windows UI Automation "
                        "is unavailable."
                    ),
                )
            )

        except Exception:
            return (
                SpotifyDesktopDiscoveryResult(
                    status=(
                        SpotifyDesktopDiscoveryStatus
                        .ERROR
                    ),
                    playlist_name=playlist,
                    title=track_title,
                    artist=track_artist,
                    message=(
                        "Spotify desktop could not "
                        "be inspected."
                    ),
                )
            )
