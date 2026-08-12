from __future__ import annotations

import atexit
import ctypes
import os
from ctypes import wintypes

from PyQt6.QtCore import (
    QCoreApplication,
    QEventLoop,
    QTimer,
    Qt,
)
from PyQt6.QtWidgets import QApplication


WH_CBT = 5

HCBT_MOVESIZE = 0
HCBT_ACTIVATE = 5
HCBT_CREATEWND = 3

DWMWA_TRANSITIONS_FORCEDISABLED = 3

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_NOOWNERZORDER = 0x0200

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class CREATESTRUCTW(ctypes.Structure):
    _fields_ = [
        (
            "lpCreateParams",
            ctypes.c_void_p,
        ),
        (
            "hInstance",
            ctypes.c_void_p,
        ),
        (
            "hMenu",
            ctypes.c_void_p,
        ),
        (
            "hwndParent",
            ctypes.c_void_p,
        ),
        ("cy", ctypes.c_int),
        ("cx", ctypes.c_int),
        ("y", ctypes.c_int),
        ("x", ctypes.c_int),
        ("style", ctypes.c_long),
        (
            "lpszName",
            ctypes.c_void_p,
        ),
        (
            "lpszClass",
            ctypes.c_void_p,
        ),
        (
            "dwExStyle",
            ctypes.c_uint32,
        ),
    ]


class CBT_CREATEWNDW(ctypes.Structure):
    _fields_ = [
        (
            "lpcs",
            ctypes.POINTER(
                CREATESTRUCTW
            ),
        ),
        (
            "hwndInsertAfter",
            ctypes.c_void_p,
        ),
    ]


_user32 = ctypes.WinDLL(
    "user32",
    use_last_error=True,
)

_kernel32 = ctypes.WinDLL(
    "kernel32",
    use_last_error=True,
)

_dwmapi = ctypes.WinDLL(
    "dwmapi",
    use_last_error=True,
)


_GetSystemMetrics = (
    _user32.GetSystemMetrics
)

_GetSystemMetrics.argtypes = [
    ctypes.c_int
]

_GetSystemMetrics.restype = (
    ctypes.c_int
)


_GetClassNameW = (
    _user32.GetClassNameW
)

_GetClassNameW.argtypes = [
    wintypes.HWND,
    wintypes.LPWSTR,
    ctypes.c_int,
]

_GetClassNameW.restype = (
    ctypes.c_int
)


_IsWindow = _user32.IsWindow

_IsWindow.argtypes = [
    wintypes.HWND
]

_IsWindow.restype = (
    wintypes.BOOL
)


_GetWindowRect = (
    _user32.GetWindowRect
)

_GetWindowRect.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(
        RECT
    ),
]

_GetWindowRect.restype = (
    wintypes.BOOL
)


_GetWindowThreadProcessId = (
    _user32.GetWindowThreadProcessId
)

_GetWindowThreadProcessId.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(
        wintypes.DWORD
    ),
]

_GetWindowThreadProcessId.restype = (
    wintypes.DWORD
)


HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    ctypes.c_int,
    ctypes.c_size_t,
    ctypes.c_ssize_t,
)


_SetWindowsHookExW = (
    _user32.SetWindowsHookExW
)

_SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    HOOKPROC,
    ctypes.c_void_p,
    ctypes.c_uint32,
]

_SetWindowsHookExW.restype = (
    ctypes.c_void_p
)


_CallNextHookEx = (
    _user32.CallNextHookEx
)

_CallNextHookEx.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_size_t,
    ctypes.c_ssize_t,
]

_CallNextHookEx.restype = (
    ctypes.c_ssize_t
)


_UnhookWindowsHookEx = (
    _user32.UnhookWindowsHookEx
)

_UnhookWindowsHookEx.argtypes = [
    ctypes.c_void_p
]

_UnhookWindowsHookEx.restype = (
    wintypes.BOOL
)


_GetCurrentThreadId = (
    _kernel32.GetCurrentThreadId
)

_GetCurrentThreadId.argtypes = []

_GetCurrentThreadId.restype = (
    ctypes.c_uint32
)


_BeginDeferWindowPos = (
    _user32.BeginDeferWindowPos
)

_BeginDeferWindowPos.argtypes = [
    ctypes.c_int
]

_BeginDeferWindowPos.restype = (
    ctypes.c_void_p
)


_DeferWindowPos = (
    _user32.DeferWindowPos
)

_DeferWindowPos.argtypes = [
    ctypes.c_void_p,
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]

_DeferWindowPos.restype = (
    ctypes.c_void_p
)


_EndDeferWindowPos = (
    _user32.EndDeferWindowPos
)

_EndDeferWindowPos.argtypes = [
    ctypes.c_void_p
]

_EndDeferWindowPos.restype = (
    wintypes.BOOL
)


_DwmSetWindowAttribute = (
    _dwmapi.DwmSetWindowAttribute
)

_DwmSetWindowAttribute.argtypes = [
    wintypes.HWND,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.DWORD,
]

_DwmSetWindowAttribute.restype = (
    ctypes.c_long
)


_DwmFlush = _dwmapi.DwmFlush

_DwmFlush.argtypes = []

_DwmFlush.restype = ctypes.c_long


_virtual_left = int(
    _GetSystemMetrics(
        SM_XVIRTUALSCREEN
    )
)

_virtual_top = int(
    _GetSystemMetrics(
        SM_YVIRTUALSCREEN
    )
)

_virtual_width = int(
    _GetSystemMetrics(
        SM_CXVIRTUALSCREEN
    )
)

_virtual_height = int(
    _GetSystemMetrics(
        SM_CYVIRTUALSCREEN
    )
)


OFFSCREEN_X = (
    _virtual_left
    - _virtual_width
    - 5000
)

OFFSCREEN_Y = (
    _virtual_top
    - _virtual_height
    - 5000
)


_state = {
    "staging": True,
    "main": 0,
    "titlebars": set(),
    "desired": {},
}


_hook_handle = None
_hook_callback = None

_original_show = None
_original_hide = None

_installed_class = None


def _native_class(hwnd: int) -> str:
    buffer = (
        ctypes.create_unicode_buffer(
            256
        )
    )

    count = _GetClassNameW(
        wintypes.HWND(hwnd),
        buffer,
        len(buffer),
    )

    if count <= 0:
        return ""

    return buffer.value


def _window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()

    _GetWindowThreadProcessId(
        wintypes.HWND(hwnd),
        ctypes.byref(pid),
    )

    return int(pid.value)


def _get_rect(
    hwnd: int,
) -> tuple[int, int, int, int] | None:
    rect = RECT()

    if not _GetWindowRect(
        wintypes.HWND(hwnd),
        ctypes.byref(rect),
    ):
        return None

    return (
        int(rect.left),
        int(rect.top),
        int(rect.right),
        int(rect.bottom),
    )


def _set_transition_disabled(
    hwnd: int,
    disabled: bool,
) -> int:
    value = wintypes.BOOL(
        1 if disabled else 0
    )

    return int(
        _DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            wintypes.DWORD(
                DWMWA_TRANSITIONS_FORCEDISABLED
            ),
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    )


def _valid_target(
    hwnd: int,
) -> bool:
    return bool(
        hwnd
        and _IsWindow(
            wintypes.HWND(hwnd)
        )
        and _window_pid(hwnd)
        == os.getpid()
    )


@HOOKPROC
def _cbt_hook(
    n_code,
    w_param,
    l_param,
):
    hwnd = int(
        w_param or 0
    )

    try:
        if (
            n_code
            == HCBT_CREATEWND
            and _state["staging"]
        ):
            info = ctypes.cast(
                l_param,
                ctypes.POINTER(
                    CBT_CREATEWNDW
                ),
            ).contents

            create = (
                info.lpcs.contents
            )

            class_name = (
                _native_class(hwnd)
            )

            width = int(
                create.cx
            )

            height = int(
                create.cy
            )

            is_main = (
                not _state["main"]
                and "QWindowIcon"
                in class_name
                and width >= 500
                and height >= 400
            )

            is_titlebar = (
                class_name
                == "_q_titlebar"
                and width >= 400
                and 0
                < height
                <= 100
            )

            if is_main:
                _state["main"] = hwnd

                _state["desired"][
                    hwnd
                ] = (
                    int(create.x),
                    int(create.y),
                    int(
                        create.x
                        + width
                    ),
                    int(
                        create.y
                        + height
                    ),
                )

                create.x = OFFSCREEN_X
                create.y = OFFSCREEN_Y

            elif is_titlebar:
                _state["titlebars"].add(
                    hwnd
                )

                _state["desired"][
                    hwnd
                ] = (
                    int(create.x),
                    int(create.y),
                    int(
                        create.x
                        + width
                    ),
                    int(
                        create.y
                        + height
                    ),
                )

                create.x = OFFSCREEN_X
                create.y = OFFSCREEN_Y

        elif (
            n_code
            == HCBT_MOVESIZE
            and _state["staging"]
            and hwnd
        ):
            is_target = (
                hwnd
                == _state["main"]
                or hwnd
                in _state["titlebars"]
            )

            if is_target:
                rect = ctypes.cast(
                    l_param,
                    ctypes.POINTER(
                        RECT
                    ),
                ).contents

                requested = (
                    int(rect.left),
                    int(rect.top),
                    int(rect.right),
                    int(rect.bottom),
                )

                _state["desired"][
                    hwnd
                ] = requested

                width = (
                    requested[2]
                    - requested[0]
                )

                height = (
                    requested[3]
                    - requested[1]
                )

                rect.left = OFFSCREEN_X
                rect.top = OFFSCREEN_Y

                rect.right = (
                    OFFSCREEN_X
                    + width
                )

                rect.bottom = (
                    OFFSCREEN_Y
                    + height
                )

        elif (
            n_code
            == HCBT_ACTIVATE
            and _state["staging"]
            and hwnd
            and (
                hwnd
                == _state["main"]
                or hwnd
                in _state["titlebars"]
            )
        ):
            return 1

    except Exception:
        pass

    return _CallNextHookEx(
        _hook_handle,
        n_code,
        w_param,
        l_param,
    )


def _install_hook() -> None:
    global _hook_handle
    global _hook_callback

    if _hook_handle:
        return

    _hook_callback = _cbt_hook

    thread_id = int(
        _GetCurrentThreadId()
    )

    _hook_handle = (
        _SetWindowsHookExW(
            WH_CBT,
            _hook_callback,
            None,
            thread_id,
        )
    )

    if not _hook_handle:
        raise OSError(
            ctypes.get_last_error(),
            "SetWindowsHookExW failed",
        )


def _uninstall_hook() -> None:
    global _hook_handle
    global _hook_callback

    if _hook_handle:
        _UnhookWindowsHookEx(
            _hook_handle
        )

    _hook_handle = None
    _hook_callback = None


def _current_titlebars() -> tuple[int, ...]:
    return tuple(
        hwnd
        for hwnd in sorted(
            _state["titlebars"]
        )
        if _valid_target(hwnd)
    )


def _target_rect(
    hwnd: int,
    main_rect: tuple[
        int,
        int,
        int,
        int,
    ],
) -> tuple[int, int, int, int]:
    saved = _state[
        "desired"
    ].get(hwnd)

    current = _get_rect(
        hwnd
    )

    if current is None:
        raise RuntimeError(
            f"No rect for HWND {hwnd}"
        )

    width = (
        current[2]
        - current[0]
    )

    height = (
        current[3]
        - current[1]
    )

    if hwnd == _state["main"]:
        if saved is None:
            raise RuntimeError(
                "No desired main rect "
                "was captured."
            )

        return saved

    return (
        main_rect[0],
        main_rect[1],
        main_rect[0]
        + width,
        main_rect[1]
        + height,
    )


def _move_targets_onscreen() -> tuple[int, ...]:
    main_hwnd = int(
        _state["main"]
    )

    if not _valid_target(
        main_hwnd
    ):
        raise RuntimeError(
            "Main HWND is unavailable."
        )

    main_rect = _state[
        "desired"
    ].get(main_hwnd)

    if main_rect is None:
        raise RuntimeError(
            "No final main rect captured."
        )

    titlebars = (
        _current_titlebars()
    )

    handles = (
        main_hwnd,
        *titlebars,
    )

    for hwnd in handles:
        _set_transition_disabled(
            hwnd,
            True,
        )

    _DwmFlush()

    hdwp = _BeginDeferWindowPos(
        len(handles)
    )

    if not hdwp:
        raise OSError(
            ctypes.get_last_error(),
            "BeginDeferWindowPos failed",
        )

    flags = (
        SWP_NOZORDER
        | SWP_NOACTIVATE
        | SWP_NOOWNERZORDER
    )

    for hwnd in handles:
        rect = _target_rect(
            hwnd,
            main_rect,
        )

        width = (
            rect[2]
            - rect[0]
        )

        height = (
            rect[3]
            - rect[1]
        )

        hdwp = _DeferWindowPos(
            hdwp,
            wintypes.HWND(hwnd),
            None,
            int(rect[0]),
            int(rect[1]),
            int(width),
            int(height),
            flags,
        )

        if not hdwp:
            raise OSError(
                ctypes.get_last_error(),
                "DeferWindowPos failed",
            )

    if not _EndDeferWindowPos(
        hdwp
    ):
        raise OSError(
            ctypes.get_last_error(),
            "EndDeferWindowPos failed",
        )

    _DwmFlush()

    return handles


def _restore_transitions(
    handles: tuple[int, ...],
) -> None:
    for hwnd in handles:
        if _valid_target(hwnd):
            _set_transition_disabled(
                hwnd,
                False,
            )


def install_startup_native_stage(
    window_class,
) -> bool:
    global _original_show
    global _original_hide
    global _installed_class

    if os.name != "nt":
        return False

    if _installed_class is window_class:
        return True

    if _installed_class is not None:
        return False

    _state["staging"] = True
    _state["main"] = 0
    _state["titlebars"].clear()
    _state["desired"].clear()

    _install_hook()

    _original_show = (
        window_class.show
    )

    _original_hide = (
        window_class.hide
    )

    def staged_hide(self):
        if (
            getattr(
                self,
                "_0337_stage_prepared",
                False,
            )
            and not getattr(
                self,
                "_0337_stage_complete",
                False,
            )
        ):
            return None

        return _original_hide(
            self
        )

    def staged_show(self):
        hidden_attribute = (
            Qt.WidgetAttribute
            .WA_DontShowOnScreen
        )

        activation_attribute = (
            Qt.WidgetAttribute
            .WA_ShowWithoutActivating
        )

        prepared = getattr(
            self,
            "_0337_stage_prepared",
            False,
        )

        complete = getattr(
            self,
            "_0337_stage_complete",
            False,
        )

        if complete:
            return _original_show(
                self
            )

        if (
            not prepared
            and self.testAttribute(
                hidden_attribute
            )
        ):
            self.setAttribute(
                activation_attribute,
                True,
            )

            self.setAttribute(
                hidden_attribute,
                False,
            )

            result = _original_show(
                self
            )

            if not _state["main"]:
                raise RuntimeError(
                    "CBT did not capture "
                    "the main HWND."
                )

            QCoreApplication.sendPostedEvents()

            QApplication.processEvents(
                QEventLoop
                .ProcessEventsFlag
                .ExcludeUserInputEvents
            )

            self.update()

            QApplication.processEvents(
                QEventLoop
                .ProcessEventsFlag
                .ExcludeUserInputEvents
            )

            self.repaint()

            _DwmFlush()

            self._0337_stage_prepared = (
                True
            )

            return result

        if prepared:
            QCoreApplication.sendPostedEvents()

            QApplication.processEvents(
                QEventLoop
                .ProcessEventsFlag
                .ExcludeUserInputEvents
            )

            self.repaint()

            _DwmFlush()

            _state["staging"] = False

            _uninstall_hook()

            handles = (
                _move_targets_onscreen()
            )

            self._0337_stage_complete = (
                True
            )

            self.setAttribute(
                activation_attribute,
                False,
            )

            QTimer.singleShot(
                500,
                lambda saved=handles: (
                    _restore_transitions(
                        saved
                    )
                ),
            )

            return None

        return _original_show(
            self
        )

    window_class.show = staged_show
    window_class.hide = staged_hide

    _installed_class = (
        window_class
    )

    return True


atexit.register(
    _uninstall_hook
)
