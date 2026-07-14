from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Callable

from src.ui.custom_cards import (
    LAUNCHER_TARGET_APPLICATION,
    LAUNCHER_TARGET_FILE,
    LAUNCHER_TARGET_FOLDER,
    LauncherCardData,
)


SCRIPT_TARGET_EXTENSIONS = frozenset(
    {
        ".bat",
        ".cmd",
        ".js",
        ".jse",
        ".ps1",
        ".vbe",
        ".vbs",
        ".wsf",
        ".wsh",
    }
)


@dataclass(
    frozen=True,
    slots=True,
)
class PreparedLauncherTarget:
    path: Path
    target_kind: str
    requires_script_confirmation: bool


def is_script_target(
    target: str | Path,
) -> bool:
    return (
        Path(target).suffix.casefold()
        in SCRIPT_TARGET_EXTENSIONS
    )


def _validate_target_path(
    path: Path,
    target_kind: str,
):
    if not path.exists():
        raise FileNotFoundError(
            "The saved Launcher target could "
            "not be found:\n"
            f"{path}"
        )

    if (
        target_kind
        == LAUNCHER_TARGET_FOLDER
    ):
        if not path.is_dir():
            raise ValueError(
                "The saved Launcher target is "
                "not a folder."
            )

        return

    if target_kind in {
        LAUNCHER_TARGET_APPLICATION,
        LAUNCHER_TARGET_FILE,
    }:
        if not path.is_file():
            kind_label = (
                "application"
                if target_kind
                == LAUNCHER_TARGET_APPLICATION
                else "file"
            )

            raise ValueError(
                "The saved Launcher target is "
                f"not a {kind_label} file."
            )

        return

    raise ValueError(
        "The saved Launcher target type "
        "is not supported."
    )


def prepare_launcher_target(
    card: LauncherCardData,
) -> PreparedLauncherTarget:
    if not isinstance(
        card,
        LauncherCardData,
    ):
        raise TypeError(
            "Expected LauncherCardData."
        )

    validated_card = (
        LauncherCardData.from_dict(
            card.to_dict()
        )
    )

    if not validated_card.is_configured:
        raise ValueError(
            "Choose a local target before opening."
        )

    path = validated_card.target_path

    if path is None:
        raise ValueError(
            "Choose a local target before opening."
        )

    _validate_target_path(
        path,
        validated_card.target_kind,
    )

    return PreparedLauncherTarget(
        path=path,
        target_kind=(
            validated_card.target_kind
        ),
        requires_script_confirmation=(
            is_script_target(path)
        ),
    )


def open_prepared_launcher_target(
    prepared: PreparedLauncherTarget,
    *,
    opener: Callable[[str], object]
    | None = None,
):
    if not isinstance(
        prepared,
        PreparedLauncherTarget,
    ):
        raise TypeError(
            "Expected PreparedLauncherTarget."
        )

    # Check again immediately before handing the
    # path to Windows. The target could have moved
    # since the button was drawn or confirmed.
    _validate_target_path(
        prepared.path,
        prepared.target_kind,
    )

    selected_opener = opener

    if selected_opener is None:
        selected_opener = getattr(
            os,
            "startfile",
            None,
        )

    if selected_opener is None:
        raise OSError(
            "Launcher targets can only be opened "
            "on Windows."
        )

    # A single validated path is passed directly
    # to Windows. No arguments or command strings
    # are accepted by this interface.
    selected_opener(
        os.fspath(
            prepared.path
        )
    )
