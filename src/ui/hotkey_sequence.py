from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
)
from PyQt6.QtGui import (
    QKeySequence,
)

from src.system.global_hotkeys import (
    HotkeyBinding,
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_WIN,
)


SUPPORTED_KEY_HELP = (
    "Use a modifier such as Ctrl, Alt, Shift or Win "
    "with a letter, number, F-key, navigation key, "
    "Space, Tab, Enter, Backspace, Insert or Delete."
)


_QT_TO_VK = {
    int(
        Qt.Key.Key_Space
    ): 0x20,
    int(
        Qt.Key.Key_Tab
    ): 0x09,
    int(
        Qt.Key.Key_Backspace
    ): 0x08,
    int(
        Qt.Key.Key_Return
    ): 0x0D,
    int(
        Qt.Key.Key_Enter
    ): 0x0D,
    int(
        Qt.Key.Key_Escape
    ): 0x1B,
    int(
        Qt.Key.Key_Insert
    ): 0x2D,
    int(
        Qt.Key.Key_Delete
    ): 0x2E,
    int(
        Qt.Key.Key_Home
    ): 0x24,
    int(
        Qt.Key.Key_End
    ): 0x23,
    int(
        Qt.Key.Key_PageUp
    ): 0x21,
    int(
        Qt.Key.Key_PageDown
    ): 0x22,
    int(
        Qt.Key.Key_Left
    ): 0x25,
    int(
        Qt.Key.Key_Up
    ): 0x26,
    int(
        Qt.Key.Key_Right
    ): 0x27,
    int(
        Qt.Key.Key_Down
    ): 0x28,
}


_VK_NAMES = {
    0x20: "Space",
    0x09: "Tab",
    0x08: "Backspace",
    0x0D: "Return",
    0x1B: "Esc",
    0x2D: "Insert",
    0x2E: "Delete",
    0x24: "Home",
    0x23: "End",
    0x21: "PgUp",
    0x22: "PgDown",
    0x25: "Left",
    0x26: "Up",
    0x27: "Right",
    0x28: "Down",
}


def qt_key_to_virtual_key(
    qt_key: int,
) -> int:
    qt_key = int(
        qt_key
    )

    if 0x30 <= qt_key <= 0x39:
        return qt_key

    if 0x41 <= qt_key <= 0x5A:
        return qt_key

    direct = _QT_TO_VK.get(
        qt_key
    )

    if direct is not None:
        return direct

    first_function_key = int(
        Qt.Key.Key_F1
    )

    last_function_key = int(
        Qt.Key.Key_F24
    )

    if (
        first_function_key
        <= qt_key
        <= last_function_key
    ):
        return (
            0x70
            + (
                qt_key
                - first_function_key
            )
        )

    raise ValueError(
        "That key is not supported for "
        "a global media shortcut. "
        + SUPPORTED_KEY_HELP
    )


def virtual_key_name(
    virtual_key: int,
) -> str:
    virtual_key = int(
        virtual_key
    )

    if 0x30 <= virtual_key <= 0x39:
        return chr(
            virtual_key
        )

    if 0x41 <= virtual_key <= 0x5A:
        return chr(
            virtual_key
        )

    direct = _VK_NAMES.get(
        virtual_key
    )

    if direct is not None:
        return direct

    if 0x70 <= virtual_key <= 0x87:
        return (
            "F"
            + str(
                virtual_key
                - 0x70
                + 1
            )
        )

    raise ValueError(
        "The saved global shortcut uses "
        "an unsupported virtual key."
    )


def _windows_modifiers_from_qt(
    modifiers,
) -> int:
    result = 0

    if (
        modifiers
        & Qt.KeyboardModifier.ControlModifier
    ):
        result |= MOD_CONTROL

    if (
        modifiers
        & Qt.KeyboardModifier.AltModifier
    ):
        result |= MOD_ALT

    if (
        modifiers
        & Qt.KeyboardModifier.ShiftModifier
    ):
        result |= MOD_SHIFT

    if (
        modifiers
        & Qt.KeyboardModifier.MetaModifier
    ):
        result |= MOD_WIN

    return result


def binding_from_sequence(
    sequence: QKeySequence,
) -> HotkeyBinding | None:
    if not isinstance(
        sequence,
        QKeySequence,
    ):
        raise TypeError(
            "sequence must be a QKeySequence."
        )

    if sequence.count() == 0:
        return None

    if sequence.count() != 1:
        raise ValueError(
            "Global media shortcuts must "
            "contain exactly one key chord."
        )

    combination = sequence[
        0
    ]

    modifiers = (
        _windows_modifiers_from_qt(
            combination.keyboardModifiers()
        )
    )

    if modifiers == 0:
        raise ValueError(
            "Global media shortcuts must include "
            "Ctrl, Alt, Shift or Win so normal "
            "typing is never captured."
        )

    virtual_key = (
        qt_key_to_virtual_key(
            int(
                combination.key()
            )
        )
    )

    return HotkeyBinding(
        modifiers=modifiers,
        virtual_key=virtual_key,
    )


def binding_text(
    binding: HotkeyBinding,
) -> str:
    if not isinstance(
        binding,
        HotkeyBinding,
    ):
        raise TypeError(
            "binding must be a HotkeyBinding."
        )

    parts = []

    if (
        binding.modifiers
        & MOD_CONTROL
    ):
        parts.append(
            "Ctrl"
        )

    if (
        binding.modifiers
        & MOD_ALT
    ):
        parts.append(
            "Alt"
        )

    if (
        binding.modifiers
        & MOD_SHIFT
    ):
        parts.append(
            "Shift"
        )

    if (
        binding.modifiers
        & MOD_WIN
    ):
        parts.append(
            "Meta"
        )

    parts.append(
        virtual_key_name(
            binding.virtual_key
        )
    )

    return "+".join(
        parts
    )


def sequence_from_binding(
    binding: HotkeyBinding,
) -> QKeySequence:
    return QKeySequence(
        binding_text(
            binding
        )
    )
