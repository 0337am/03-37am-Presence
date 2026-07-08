from __future__ import annotations

import ctypes
from ctypes import wintypes


class LastInputInfo(ctypes.Structure):
    _fields_ = [
        (
            "cbSize",
            wintypes.UINT,
        ),
        (
            "dwTime",
            wintypes.DWORD,
        ),
    ]


class WindowsIdleMonitor:
    """
    Reads the time since the user's last keyboard
    or mouse input using the Windows API.
    """

    @staticmethod
    def idle_seconds() -> float:
        last_input = LastInputInfo()

        last_input.cbSize = ctypes.sizeof(
            LastInputInfo
        )

        success = (
            ctypes.windll.user32
            .GetLastInputInfo(
                ctypes.byref(last_input)
            )
        )

        if not success:
            return 0.0

        current_tick = (
            ctypes.windll.kernel32
            .GetTickCount()
        )

        elapsed_milliseconds = (
            current_tick
            - last_input.dwTime
        ) & 0xFFFFFFFF

        return max(
            0.0,
            elapsed_milliseconds / 1000.0,
        )

    @classmethod
    def is_idle(
        cls,
        threshold_seconds: int,
    ) -> bool:
        safe_threshold = max(
            1,
            int(threshold_seconds),
        )

        return (
            cls.idle_seconds()
            >= safe_threshold
        )