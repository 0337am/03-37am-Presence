from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum
import ntpath
import time

from src.music.windows_media import (
    WindowsMedia,
)


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


class SpotifyDesktopPlaybackStatus(
    str,
    Enum,
):
    PLAYED = "played"
    ALREADY_PLAYING = "already_playing"
    SPOTIFY_NOT_FOUND = "spotify_not_found"
    PLAYLIST_NOT_FOUND = "playlist_not_found"
    PLAY_CONTROL_NOT_FOUND = (
        "play_control_not_found"
    )
    PLAY_CONTROL_UNAVAILABLE = (
        "play_control_unavailable"
    )
    PLAYBACK_NOT_CONFIRMED = (
        "playback_not_confirmed"
    )
    AUTOMATION_UNAVAILABLE = (
        "automation_unavailable"
    )
    ERROR = "error"


@dataclass(
    frozen=True,
    slots=True,
)
class SpotifyDesktopPlaybackResult:
    status: SpotifyDesktopPlaybackStatus
    playlist_name: str
    title: str
    artist: str
    message: str = ""
    now_playing_confirmed: bool = False
    media_session_confirmed: bool = False

    @property
    def success(
        self,
    ) -> bool:
        return self.status in {
            SpotifyDesktopPlaybackStatus.PLAYED,
            SpotifyDesktopPlaybackStatus.ALREADY_PLAYING,
        }


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


class SpotifyWindowsMediaPlaybackVerifier:
    def __init__(
        self,
        media=None,
    ) -> None:
        self._media = (
            WindowsMedia()
            if media is None
            else media
        )

        reader = getattr(
            self._media,
            "get_spotify_playback_state",
            None,
        )

        if not callable(
            reader
        ):
            raise TypeError(
                (
                    "media must provide "
                    "get_spotify_playback_state()"
                )
            )

    def confirms_playing(
        self,
        *,
        title: str,
        artist: str,
    ) -> bool:
        expected_title = (
            _semantic_text(
                title
            )
        )

        expected_artist = (
            _semantic_text(
                artist
            )
        )

        try:
            state = (
                self._media
                .get_spotify_playback_state()
            )

        except Exception:
            return False

        if not bool(
            getattr(
                state,
                "playing",
                False,
            )
        ):
            return False

        actual_title = (
            _semantic_text(
                getattr(
                    state,
                    "title",
                    "",
                )
            )
        )

        actual_artist = (
            _semantic_text(
                getattr(
                    state,
                    "artist",
                    "",
                )
            )
        )

        return (
            actual_title
            == expected_title
            and actual_artist
            == expected_artist
        )


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

    @staticmethod
    def _process_image_path(
        kernel32,
        pid: int,
    ) -> str:
        process_query_limited_information = (
            0x1000
        )

        handle = kernel32.OpenProcess(
            process_query_limited_information,
            False,
            pid,
        )

        if not handle:
            return ""

        try:
            size = wintypes.DWORD(
                32768
            )

            buffer = (
                ctypes.create_unicode_buffer(
                    size.value
                )
            )

            success = (
                kernel32
                .QueryFullProcessImageNameW(
                    handle,
                    0,
                    buffer,
                    ctypes.byref(
                        size
                    ),
                )
            )

            if not success:
                return ""

            return (
                buffer.value.strip()
            )

        finally:
            kernel32.CloseHandle(
                handle
            )

    @staticmethod
    def _is_spotify_window_candidate(
        *,
        title: str,
        process_path: str,
    ) -> bool:
        executable = (
            ntpath.basename(
                str(
                    process_path
                    or ""
                )
            )
            .strip()
            .casefold()
        )

        if executable == "spotify.exe":
            return True

        return (
            "spotify"
            in str(
                title
                or ""
            ).casefold()
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

        kernel32 = ctypes.WinDLL(
            "kernel32",
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

        user32.GetWindowThreadProcessId.argtypes = (
            wintypes.HWND,
            ctypes.POINTER(
                wintypes.DWORD
            ),
        )

        user32.GetWindowThreadProcessId.restype = (
            wintypes.DWORD
        )

        kernel32.OpenProcess.argtypes = (
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        )

        kernel32.OpenProcess.restype = (
            wintypes.HANDLE
        )

        kernel32.QueryFullProcessImageNameW.argtypes = (
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(
                wintypes.DWORD
            ),
        )

        kernel32.QueryFullProcessImageNameW.restype = (
            wintypes.BOOL
        )

        kernel32.CloseHandle.argtypes = (
            wintypes.HANDLE,
        )

        kernel32.CloseHandle.restype = (
            wintypes.BOOL
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

            pid = wintypes.DWORD()

            user32.GetWindowThreadProcessId(
                hwnd,
                ctypes.byref(
                    pid
                ),
            )

            process_path = ""

            if pid.value:
                try:
                    process_path = (
                        self._process_image_path(
                            kernel32,
                            pid.value,
                        )
                    )

                except Exception:
                    process_path = ""

            if not (
                self
                ._is_spotify_window_candidate(
                    title=title,
                    process_path=process_path,
                )
            ):
                return True

            executable = (
                ntpath.basename(
                    process_path
                ).casefold()
                if process_path
                else ""
            )

            process_match = (
                executable
                == "spotify.exe"
            )

            candidates.append(
                (
                    process_match,
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

        # Process identity outranks title text.
        candidates.sort(
            key=lambda item: (
                not item[0],
            )
        )

        return candidates[0][1]

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

    def invoke(
        self,
        element,
    ) -> None:
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

            if pattern is None:
                raise RuntimeError(
                    "InvokePattern unavailable."
                )

            invoke_pattern = (
                pattern.QueryInterface(
                    self._client
                    .IUIAutomationInvokePattern
                )
            )

            invoke_pattern.Invoke()

        except Exception as error:
            raise RuntimeError(
                (
                    "Spotify's Play control "
                    "could not be invoked."
                )
            ) from error


class SpotifyDesktopPlaybackBridge:
    def __init__(
        self,
        backend=None,
        *,
        verification_attempts: int = 20,
        verification_interval: float = 0.10,
        media_verifier=None,
        sleep_fn=None,
    ) -> None:
        self._backend = (
            WindowsSpotifyUiAutomationBackend()
            if backend is None
            else backend
        )

        if (
            isinstance(
                verification_attempts,
                bool,
            )
            or not isinstance(
                verification_attempts,
                int,
            )
            or verification_attempts < 1
        ):
            raise ValueError(
                (
                    "verification_attempts must "
                    "be a positive integer"
                )
            )

        if (
            isinstance(
                verification_interval,
                bool,
            )
            or not isinstance(
                verification_interval,
                (int, float),
            )
            or verification_interval < 0
        ):
            raise ValueError(
                (
                    "verification_interval must "
                    "be zero or greater"
                )
            )

        if sleep_fn is None:
            sleep_fn = time.sleep

        if not callable(
            sleep_fn
        ):
            raise TypeError(
                "sleep_fn must be callable"
            )

        self._verification_attempts = (
            verification_attempts
        )

        self._verification_interval = float(
            verification_interval
        )

        self._sleep = sleep_fn

        if media_verifier is None:
            media_verifier = (
                SpotifyWindowsMediaPlaybackVerifier()
            )

        confirms_playing = getattr(
            media_verifier,
            "confirms_playing",
            None,
        )

        if not callable(
            confirms_playing
        ):
            raise TypeError(
                (
                    "media_verifier must provide "
                    "confirms_playing()"
                )
            )

        self._media_verifier = (
            media_verifier
        )

        required = (
            "find_spotify_window",
            "root_from_handle",
            "iter_descendants",
            "name",
            "control_type",
            "supports_invoke",
            "invoke",
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

    def _find_playlist_grid(
        self,
        root,
        playlist_name: str,
    ):
        expected_playlist = (
            _semantic_text(
                playlist_name
            )
        )

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
                return element

        return None

    def _find_track_button(
        self,
        playlist_grid,
        *,
        title: str,
        artist: str,
        action: str,
    ):
        expected = _semantic_text(
            (
                action
                + " "
                + title
                + " by "
                + artist
            )
        )

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

            if (
                _semantic_text(
                    self._backend.name(
                        element
                    )
                )
                == expected
            ):
                return element

        return None

    def _verified_playing_state(
        self,
        *,
        hwnd,
        playlist_name: str,
        title: str,
        artist: str,
    ) -> tuple[bool, bool]:
        root = (
            self._backend
            .root_from_handle(
                hwnd
            )
        )

        if root is None:
            return (
                False,
                False,
            )

        now_playing = (
            self._now_playing_confirmed(
                root,
                title,
                artist,
            )
        )

        if now_playing:
            return (
                True,
                True,
            )

        playlist_grid = (
            self._find_playlist_grid(
                root,
                playlist_name,
            )
        )

        if playlist_grid is None:
            return (
                False,
                False,
            )

        pause_control = (
            self._find_track_button(
                playlist_grid,
                title=title,
                artist=artist,
                action="Pause",
            )
        )

        if pause_control is not None:
            return (
                True,
                False,
            )

        return (
            False,
            False,
        )

    @staticmethod
    def _playback_status_from_discovery(
        status,
    ) -> SpotifyDesktopPlaybackStatus:
        mapping = {
            (
                SpotifyDesktopDiscoveryStatus
                .SPOTIFY_NOT_FOUND
            ): (
                SpotifyDesktopPlaybackStatus
                .SPOTIFY_NOT_FOUND
            ),
            (
                SpotifyDesktopDiscoveryStatus
                .PLAYLIST_NOT_FOUND
            ): (
                SpotifyDesktopPlaybackStatus
                .PLAYLIST_NOT_FOUND
            ),
            (
                SpotifyDesktopDiscoveryStatus
                .PLAY_CONTROL_NOT_FOUND
            ): (
                SpotifyDesktopPlaybackStatus
                .PLAY_CONTROL_NOT_FOUND
            ),
            (
                SpotifyDesktopDiscoveryStatus
                .PLAY_CONTROL_UNAVAILABLE
            ): (
                SpotifyDesktopPlaybackStatus
                .PLAY_CONTROL_UNAVAILABLE
            ),
            (
                SpotifyDesktopDiscoveryStatus
                .AUTOMATION_UNAVAILABLE
            ): (
                SpotifyDesktopPlaybackStatus
                .AUTOMATION_UNAVAILABLE
            ),
        }

        return mapping.get(
            status,
            SpotifyDesktopPlaybackStatus.ERROR,
        )

    def play_local_track(
        self,
        *,
        playlist_name,
        title,
        artist,
    ) -> SpotifyDesktopPlaybackResult:
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

        discovery = (
            self.discover_local_track(
                playlist_name=playlist,
                title=track_title,
                artist=track_artist,
            )
        )

        if not discovery.ready:
            return (
                SpotifyDesktopPlaybackResult(
                    status=(
                        self
                        ._playback_status_from_discovery(
                            discovery.status
                        )
                    ),
                    playlist_name=playlist,
                    title=track_title,
                    artist=track_artist,
                    message=discovery.message,
                    now_playing_confirmed=(
                        discovery
                        .now_playing_confirmed
                    ),
                )
            )

        if discovery.already_playing:
            return (
                SpotifyDesktopPlaybackResult(
                    status=(
                        SpotifyDesktopPlaybackStatus
                        .ALREADY_PLAYING
                    ),
                    playlist_name=playlist,
                    title=track_title,
                    artist=track_artist,
                    message=(
                        "Spotify is already playing "
                        "this local track."
                    ),
                    now_playing_confirmed=(
                        discovery
                        .now_playing_confirmed
                    ),
                )
            )

        try:
            hwnd = (
                self._backend
                .find_spotify_window()
            )

            if not hwnd:
                return (
                    SpotifyDesktopPlaybackResult(
                        status=(
                            SpotifyDesktopPlaybackStatus
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
                    SpotifyDesktopPlaybackResult(
                        status=(
                            SpotifyDesktopPlaybackStatus
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

            playlist_grid = (
                self._find_playlist_grid(
                    root,
                    playlist,
                )
            )

            if playlist_grid is None:
                return (
                    SpotifyDesktopPlaybackResult(
                        status=(
                            SpotifyDesktopPlaybackStatus
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

            play_control = (
                self._find_track_button(
                    playlist_grid,
                    title=track_title,
                    artist=track_artist,
                    action="Play",
                )
            )

            if play_control is None:
                pause_control = (
                    self._find_track_button(
                        playlist_grid,
                        title=track_title,
                        artist=track_artist,
                        action="Pause",
                    )
                )

                if pause_control is not None:
                    return (
                        SpotifyDesktopPlaybackResult(
                            status=(
                                SpotifyDesktopPlaybackStatus
                                .ALREADY_PLAYING
                            ),
                            playlist_name=playlist,
                            title=track_title,
                            artist=track_artist,
                            message=(
                                "Spotify is already "
                                "playing this local track."
                            ),
                            now_playing_confirmed=(
                                self
                                ._now_playing_confirmed(
                                    root,
                                    track_title,
                                    track_artist,
                                )
                            ),
                        )
                    )

                return (
                    SpotifyDesktopPlaybackResult(
                        status=(
                            SpotifyDesktopPlaybackStatus
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

            if not self._backend.supports_invoke(
                play_control
            ):
                return (
                    SpotifyDesktopPlaybackResult(
                        status=(
                            SpotifyDesktopPlaybackStatus
                            .PLAY_CONTROL_UNAVAILABLE
                        ),
                        playlist_name=playlist,
                        title=track_title,
                        artist=track_artist,
                        message=(
                            "Spotify's local-track play "
                            "control is unavailable."
                        ),
                    )
                )

            self._backend.invoke(
                play_control
            )

            now_playing_confirmed = False

            for attempt in range(
                self._verification_attempts
            ):
                media_session_confirmed = (
                    self._media_verifier
                    .confirms_playing(
                        title=track_title,
                        artist=track_artist,
                    )
                )

                if media_session_confirmed:
                    return (
                        SpotifyDesktopPlaybackResult(
                            status=(
                                SpotifyDesktopPlaybackStatus
                                .PLAYED
                            ),
                            playlist_name=playlist,
                            title=track_title,
                            artist=track_artist,
                            message=(
                                "Spotify started the "
                                "local track."
                            ),
                            media_session_confirmed=True,
                        )
                    )

                (
                    playing_confirmed,
                    now_playing_confirmed,
                ) = (
                    self._verified_playing_state(
                        hwnd=hwnd,
                        playlist_name=playlist,
                        title=track_title,
                        artist=track_artist,
                    )
                )

                if playing_confirmed:
                    return (
                        SpotifyDesktopPlaybackResult(
                            status=(
                                SpotifyDesktopPlaybackStatus
                                .PLAYED
                            ),
                            playlist_name=playlist,
                            title=track_title,
                            artist=track_artist,
                            message=(
                                "Spotify started the "
                                "local track."
                            ),
                            now_playing_confirmed=(
                                now_playing_confirmed
                            ),
                        )
                    )

                if (
                    attempt
                    < self._verification_attempts - 1
                    and self._verification_interval > 0
                ):
                    self._sleep(
                        self._verification_interval
                    )

            return (
                SpotifyDesktopPlaybackResult(
                    status=(
                        SpotifyDesktopPlaybackStatus
                        .PLAYBACK_NOT_CONFIRMED
                    ),
                    playlist_name=playlist,
                    title=track_title,
                    artist=track_artist,
                    message=(
                        "Spotify did not confirm that "
                        "the local track started."
                    ),
                    now_playing_confirmed=(
                        now_playing_confirmed
                    ),
                )
            )

        except SpotifyDesktopAutomationUnavailable:
            return (
                SpotifyDesktopPlaybackResult(
                    status=(
                        SpotifyDesktopPlaybackStatus
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
                SpotifyDesktopPlaybackResult(
                    status=(
                        SpotifyDesktopPlaybackStatus
                        .ERROR
                    ),
                    playlist_name=playlist,
                    title=track_title,
                    artist=track_artist,
                    message=(
                        "Spotify local-track playback "
                        "could not be started."
                    ),
                )
            )

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

            now_playing = (
                self._now_playing_confirmed(
                    root,
                    track_title,
                    track_artist,
                )
            )

            if (
                play_control is None
                and now_playing
            ):
                return (
                    SpotifyDesktopDiscoveryResult(
                        status=(
                            SpotifyDesktopDiscoveryStatus
                            .READY
                        ),
                        playlist_name=playlist,
                        title=track_title,
                        artist=track_artist,
                        button_name="",
                        already_playing=True,
                        now_playing_confirmed=True,
                        message=(
                            "Spotify is already playing "
                            "this local track."
                        ),
                    )
                )

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
