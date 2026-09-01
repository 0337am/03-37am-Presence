from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import QObject, QRect, QTimer

from src.companion.preferences import CompanionPreferences


DWMWA_EXTENDED_FRAME_BOUNDS = 9
MONITOR_DEFAULTTONEAREST = 2
FRAME_TOLERANCE_PX = 2
DEFAULT_POLL_INTERVAL_MS = 750

RectTuple = tuple[
    int,
    int,
    int,
    int,
]


class _RECT(ctypes.Structure):
    _fields_ = (
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    )


class _MONITORINFO(ctypes.Structure):
    _fields_ = (
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", wintypes.DWORD),
    )


@dataclass(
    frozen=True,
    slots=True,
)
class ForegroundFullscreenState:
    is_fullscreen: bool = False
    monitor_rect: RectTuple | None = None


def _rect_tuple(
    rect: _RECT,
) -> RectTuple:
    return (
        int(rect.left),
        int(rect.top),
        int(rect.right),
        int(rect.bottom),
    )


def _qrect_tuple(
    rect: QRect,
) -> RectTuple:
    return (
        int(rect.x()),
        int(rect.y()),
        int(
            rect.x()
            + rect.width()
        ),
        int(
            rect.y()
            + rect.height()
        ),
    )


def _rects_match(
    first: RectTuple,
    second: RectTuple,
    *,
    tolerance: int = FRAME_TOLERANCE_PX,
) -> bool:
    if tolerance < 0:
        raise ValueError(
            "tolerance cannot be negative."
        )

    return all(
        abs(a - b) <= tolerance
        for a, b in zip(
            first,
            second,
        )
    )


def _classify_fullscreen_geometry(
    *,
    frame_rect: RectTuple,
    monitor_rect: RectTuple,
    visible: bool,
    iconic: bool,
    excluded_shell: bool,
) -> bool:
    return (
        visible
        and not iconic
        and not excluded_shell
        and _rects_match(
            frame_rect,
            monitor_rect,
        )
    )


def detect_foreground_fullscreen(
) -> ForegroundFullscreenState:
    """
    Inspect the current foreground window without changing it.

    Detection is intentionally fail-open. Any unavailable Win32/DWM
    information returns a non-fullscreen state so the Companion is
    never hidden because of a detector failure.
    """

    try:
        user32 = ctypes.WinDLL(
            "user32",
            use_last_error=True,
        )

        dwmapi = ctypes.WinDLL(
            "dwmapi",
            use_last_error=True,
        )

        user32.GetForegroundWindow.restype = (
            wintypes.HWND
        )

        user32.GetWindowRect.argtypes = (
            wintypes.HWND,
            ctypes.POINTER(_RECT),
        )
        user32.GetWindowRect.restype = (
            wintypes.BOOL
        )

        user32.IsWindowVisible.argtypes = (
            wintypes.HWND,
        )
        user32.IsWindowVisible.restype = (
            wintypes.BOOL
        )

        user32.IsIconic.argtypes = (
            wintypes.HWND,
        )
        user32.IsIconic.restype = (
            wintypes.BOOL
        )

        user32.GetShellWindow.restype = (
            wintypes.HWND
        )

        user32.GetDesktopWindow.restype = (
            wintypes.HWND
        )

        user32.MonitorFromWindow.argtypes = (
            wintypes.HWND,
            wintypes.DWORD,
        )
        user32.MonitorFromWindow.restype = (
            wintypes.HANDLE
        )

        user32.GetMonitorInfoW.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(_MONITORINFO),
        )
        user32.GetMonitorInfoW.restype = (
            wintypes.BOOL
        )

        dwmapi.DwmGetWindowAttribute.argtypes = (
            wintypes.HWND,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
        )
        dwmapi.DwmGetWindowAttribute.restype = (
            ctypes.c_long
        )

        hwnd = user32.GetForegroundWindow()

        if not hwnd:
            return ForegroundFullscreenState()

        visible = bool(
            user32.IsWindowVisible(
                hwnd
            )
        )

        iconic = bool(
            user32.IsIconic(
                hwnd
            )
        )

        shell = user32.GetShellWindow()
        desktop = user32.GetDesktopWindow()

        excluded_shell = (
            hwnd == shell
            or hwnd == desktop
        )

        monitor = user32.MonitorFromWindow(
            hwnd,
            MONITOR_DEFAULTTONEAREST,
        )

        if not monitor:
            return ForegroundFullscreenState()

        monitor_info = _MONITORINFO()
        monitor_info.cbSize = ctypes.sizeof(
            _MONITORINFO
        )

        if not user32.GetMonitorInfoW(
            monitor,
            ctypes.byref(
                monitor_info
            ),
        ):
            return ForegroundFullscreenState()

        monitor_rect = _rect_tuple(
            monitor_info.rcMonitor
        )

        frame_rect = _RECT()

        dwm_result = (
            dwmapi.DwmGetWindowAttribute(
                hwnd,
                DWMWA_EXTENDED_FRAME_BOUNDS,
                ctypes.byref(
                    frame_rect
                ),
                ctypes.sizeof(
                    frame_rect
                ),
            )
        )

        if dwm_result != 0:
            if not user32.GetWindowRect(
                hwnd,
                ctypes.byref(
                    frame_rect
                ),
            ):
                return ForegroundFullscreenState(
                    False,
                    monitor_rect,
                )

        frame_tuple = _rect_tuple(
            frame_rect
        )

        is_fullscreen = (
            _classify_fullscreen_geometry(
                frame_rect=frame_tuple,
                monitor_rect=monitor_rect,
                visible=visible,
                iconic=iconic,
                excluded_shell=excluded_shell,
            )
        )

        return ForegroundFullscreenState(
            is_fullscreen=is_fullscreen,
            monitor_rect=monitor_rect,
        )
    except Exception:
        return ForegroundFullscreenState()


class CompanionFullscreenController(
    QObject
):
    """
    Poll foreground fullscreen state on the Qt UI thread.

    The controller never activates, moves, resizes, or otherwise
    manipulates the foreground application.
    """

    def __init__(
        self,
        overlay,
        *,
        detector: Callable[
            [],
            ForegroundFullscreenState,
        ] = detect_foreground_fullscreen,
        poll_interval_ms: int = DEFAULT_POLL_INTERVAL_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(
            parent
        )

        if not callable(
            detector
        ):
            raise TypeError(
                "detector must be callable."
            )

        if (
            isinstance(
                poll_interval_ms,
                bool,
            )
            or not isinstance(
                poll_interval_ms,
                int,
            )
            or poll_interval_ms < 100
        ):
            raise ValueError(
                "poll_interval_ms must be an integer >= 100."
            )

        if not hasattr(
            overlay,
            "set_policy_hidden",
        ):
            raise TypeError(
                "overlay must provide set_policy_hidden()."
            )

        if not hasattr(
            overlay,
            "screen",
        ):
            raise TypeError(
                "overlay must provide screen()."
            )

        self._overlay = overlay
        self._detector = detector
        self._hide_in_fullscreen = False

        self._timer = QTimer(
            self
        )
        self._timer.setInterval(
            poll_interval_ms
        )
        self._timer.timeout.connect(
            self.poll_now
        )

    @property
    def hide_in_fullscreen(self) -> bool:
        return self._hide_in_fullscreen

    @property
    def is_polling(self) -> bool:
        return self._timer.isActive()

    def apply_preferences(
        self,
        preferences: CompanionPreferences,
    ) -> None:
        if not isinstance(
            preferences,
            CompanionPreferences,
        ):
            raise TypeError(
                "preferences must be a CompanionPreferences instance."
            )

        self.set_enabled(
            preferences.hide_in_fullscreen
        )

    def set_enabled(
        self,
        enabled: bool,
    ) -> None:
        if not isinstance(
            enabled,
            bool,
        ):
            raise ValueError(
                "enabled must be a boolean."
            )

        self._hide_in_fullscreen = enabled

        if not enabled:
            self._timer.stop()

            self._overlay.set_policy_hidden(
                False
            )

            return

        if not self._timer.isActive():
            self._timer.start()

        self.poll_now()

    def stop(self) -> None:
        self._timer.stop()
        self._hide_in_fullscreen = False

        self._overlay.set_policy_hidden(
            False
        )

    def poll_now(self) -> bool:
        if not self._hide_in_fullscreen:
            self._overlay.set_policy_hidden(
                False
            )

            return False

        try:
            state = self._detector()
        except Exception:
            state = ForegroundFullscreenState()

        if not isinstance(
            state,
            ForegroundFullscreenState,
        ):
            state = ForegroundFullscreenState()

        should_hide = False

        if (
            state.is_fullscreen
            and state.monitor_rect is not None
        ):
            screen = self._overlay.screen()

            if screen is not None:
                try:
                    companion_monitor = (
                        _qrect_tuple(
                            screen.geometry()
                        )
                    )

                    should_hide = (
                        _rects_match(
                            companion_monitor,
                            state.monitor_rect,
                        )
                    )
                except Exception:
                    should_hide = False

        self._overlay.set_policy_hidden(
            should_hide
        )

        return should_hide
