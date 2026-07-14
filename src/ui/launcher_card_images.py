from __future__ import annotations

import hashlib
import os
from pathlib import Path

from PyQt6.QtCore import (
    QByteArray,
    QBuffer,
    QIODevice,
    Qt,
)
from PyQt6.QtGui import QImageReader

from src.ui.custom_cards import (
    normalize_launcher_image_asset,
)


MAX_LAUNCHER_IMAGE_BYTES = (
    12 * 1024 * 1024
)
MAX_LAUNCHER_IMAGE_PIXELS = (
    25_000_000
)
MAX_LAUNCHER_IMAGE_EDGE = 512

SUPPORTED_LAUNCHER_IMAGE_SUFFIXES = (
    frozenset(
        {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
        }
    )
)


def launcher_card_image_root(
    root: Path | str | None = None,
) -> Path:
    if root is not None:
        return Path(root)

    local_app_data = str(
        os.getenv(
            "LOCALAPPDATA",
            "",
        )
        or ""
    ).strip()

    if local_app_data:
        base = Path(local_app_data)
    else:
        base = (
            Path.home()
            / ".0337am-presence"
        )

    return (
        base
        / "0337am Presence"
        / "launcher_card_images"
    )


def launcher_card_image_file(
    image_asset: str,
    root: Path | str | None = None,
) -> Path | None:
    normalized = (
        normalize_launcher_image_asset(
            image_asset
        )
    )

    if not normalized:
        return None

    return (
        launcher_card_image_root(root)
        / f"{normalized}.png"
    )


def cached_launcher_card_image_path(
    image_asset: str,
    root: Path | str | None = None,
) -> Path | None:
    path = launcher_card_image_file(
        image_asset,
        root,
    )

    if (
        path is None
        or not path.is_file()
    ):
        return None

    return path


def _normalise_image_file(
    source_path: Path,
) -> bytes:
    file_size = source_path.stat().st_size

    if file_size <= 0:
        raise ValueError(
            "The selected image file is empty."
        )

    if (
        file_size
        > MAX_LAUNCHER_IMAGE_BYTES
    ):
        raise ValueError(
            "The selected image is too large. "
            "Choose an image smaller than 12 MB."
        )

    reader = QImageReader(
        str(source_path)
    )
    reader.setAutoTransform(True)
    reader.setDecideFormatFromContent(True)

    announced_size = reader.size()

    if (
        announced_size.isValid()
        and announced_size.width() > 0
        and announced_size.height() > 0
        and (
            announced_size.width()
            * announced_size.height()
            > MAX_LAUNCHER_IMAGE_PIXELS
        )
    ):
        raise ValueError(
            "The selected image dimensions "
            "are too large."
        )

    image = reader.read()

    if image.isNull():
        message = (
            reader.errorString().strip()
            or "Unsupported or damaged image."
        )

        raise ValueError(
            "The selected image could not "
            f"be read: {message}"
        )

    if (
        image.width()
        * image.height()
        > MAX_LAUNCHER_IMAGE_PIXELS
    ):
        raise ValueError(
            "The selected image dimensions "
            "are too large."
        )

    if (
        image.width()
        > MAX_LAUNCHER_IMAGE_EDGE
        or image.height()
        > MAX_LAUNCHER_IMAGE_EDGE
    ):
        image = image.scaled(
            MAX_LAUNCHER_IMAGE_EDGE,
            MAX_LAUNCHER_IMAGE_EDGE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    output = QByteArray()
    buffer = QBuffer(output)

    if not buffer.open(
        QIODevice.OpenModeFlag.WriteOnly
    ):
        raise ValueError(
            "The selected image could not "
            "be prepared."
        )

    saved = image.save(
        buffer,
        "PNG",
    )
    buffer.close()

    if not saved:
        raise ValueError(
            "The selected image could not "
            "be converted to PNG."
        )

    return bytes(output)


def import_launcher_card_image(
    source: Path | str,
    root: Path | str | None = None,
) -> str:
    if not isinstance(
        source,
        (
            str,
            Path,
        ),
    ):
        raise TypeError(
            "Launcher image source must "
            "be a local path."
        )

    raw_source = os.fspath(source).strip()

    if not raw_source:
        raise ValueError(
            "Choose an image file."
        )

    if (
        raw_source.startswith("\\\\")
        or raw_source.startswith("//")
    ):
        raise ValueError(
            "Network image paths are not supported."
        )

    source_path = Path(
        raw_source
    ).expanduser()

    if not source_path.is_absolute():
        raise ValueError(
            "Launcher image paths must "
            "be absolute."
        )

    if not source_path.is_file():
        raise FileNotFoundError(
            "The selected image file "
            "could not be found."
        )

    if (
        source_path.suffix.casefold()
        not in SUPPORTED_LAUNCHER_IMAGE_SUFFIXES
    ):
        raise ValueError(
            "Choose a PNG, JPG, JPEG, "
            "or WebP image."
        )

    png_bytes = _normalise_image_file(
        source_path
    )

    image_asset = hashlib.sha256(
        png_bytes
    ).hexdigest()

    destination = (
        launcher_card_image_file(
            image_asset,
            root,
        )
    )

    if destination is None:
        raise RuntimeError(
            "The Launcher image asset "
            "could not be prepared."
        )

    if destination.is_file():
        return image_asset

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        destination.with_name(
            destination.name + ".tmp"
        )
    )

    try:
        with temporary_path.open(
            "wb",
        ) as handle:
            handle.write(png_bytes)
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            destination,
        )

    except Exception:
        temporary_path.unlink(
            missing_ok=True
        )
        raise

    return image_asset


def prune_launcher_card_images(
    referenced_assets,
    root: Path | str | None = None,
) -> tuple[Path, ...]:
    normalized_assets = {
        normalized
        for normalized in (
            normalize_launcher_image_asset(
                item
            )
            for item in referenced_assets
        )
        if normalized
    }

    image_root = (
        launcher_card_image_root(root)
    )

    if not image_root.is_dir():
        return ()

    removed = []

    for path in image_root.glob(
        "*.png"
    ):
        try:
            asset = (
                normalize_launcher_image_asset(
                    path.stem
                )
            )
        except ValueError:
            continue

        if asset in normalized_assets:
            continue

        try:
            path.unlink()
        except FileNotFoundError:
            continue

        removed.append(path)

    return tuple(removed)
