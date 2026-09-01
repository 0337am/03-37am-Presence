from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.companion.preferences import (
    MAX_ANIMATION_SPEED_PERCENT,
    MAX_OPACITY,
    MAX_SCALE_PERCENT,
    MIN_ANIMATION_SPEED_PERCENT,
    MIN_OPACITY,
    MIN_SCALE_PERCENT,
    CompanionPreferences,
)


STATIC_ASSET_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    }
)


class CompanionOverlay(QWidget):
    """
    Independent transparent Desktop Companion window.

    A03 intentionally supports static images only. GIF animation,
    fullscreen policy, settings UI, and runtime ownership belong to
    later milestones.
    """

    def __init__(
        self,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._source_pixmap = QPixmap()
        self._asset_path = ""
        self._scale_percent = 100

        self.setObjectName(
            "companionOverlay"
        )

        self.setWindowTitle(
            "03:37am Desktop Companion"
        )

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating,
            True,
        )

        self._image_label = QLabel(self)

        self._image_label.setObjectName(
            "companionImage"
        )

        self._image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self._image_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(0)

        layout.addWidget(
            self._image_label
        )

        self.set_click_through(True)

    @property
    def asset_path(self) -> str:
        return self._asset_path

    @property
    def scale_percent(self) -> int:
        return self._scale_percent

    @property
    def source_size(self) -> tuple[int, int]:
        if self._source_pixmap.isNull():
            return (0, 0)

        return (
            self._source_pixmap.width(),
            self._source_pixmap.height(),
        )

    def set_static_asset(
        self,
        path: str | Path,
    ) -> None:
        if not isinstance(
            path,
            (str, Path),
        ):
            raise TypeError(
                "Companion asset path must be a string or Path."
            )

        candidate = Path(path)

        suffix = candidate.suffix.lower()

        if suffix == ".gif":
            raise ValueError(
                "GIF rendering is deferred to the animation milestone."
            )

        if suffix not in STATIC_ASSET_SUFFIXES:
            raise ValueError(
                "Static Companion assets must use PNG, JPG, "
                "JPEG, or WebP."
            )

        if not candidate.is_file():
            raise FileNotFoundError(
                f"Companion asset does not exist: {candidate}"
            )

        pixmap = QPixmap(
            str(candidate)
        )

        if pixmap.isNull():
            raise ValueError(
                "Companion asset could not be decoded as an image."
            )

        self._source_pixmap = pixmap
        self._asset_path = str(candidate)

        self._refresh_rendered_pixmap()

    def clear_asset(self) -> None:
        self._source_pixmap = QPixmap()
        self._asset_path = ""

        self._image_label.clear()

        self.resize(
            1,
            1,
        )

    def set_scale_percent(
        self,
        scale_percent: int,
    ) -> None:
        if (
            isinstance(scale_percent, bool)
            or not isinstance(scale_percent, int)
        ):
            raise ValueError(
                "Companion scale must be an integer."
            )

        if not (
            MIN_SCALE_PERCENT
            <= scale_percent
            <= MAX_SCALE_PERCENT
        ):
            raise ValueError(
                "Companion scale is outside the supported range."
            )

        self._scale_percent = scale_percent

        if not self._source_pixmap.isNull():
            self._refresh_rendered_pixmap()

    def set_companion_opacity(
        self,
        opacity: float,
    ) -> None:
        if (
            isinstance(opacity, bool)
            or not isinstance(
                opacity,
                (int, float),
            )
        ):
            raise ValueError(
                "Companion opacity must be numeric."
            )

        normalized = float(opacity)

        if not (
            MIN_OPACITY
            <= normalized
            <= MAX_OPACITY
        ):
            raise ValueError(
                "Companion opacity is outside the supported range."
            )

        self.setWindowOpacity(
            normalized
        )

    def set_always_on_top(
        self,
        enabled: bool,
    ) -> None:
        if not isinstance(enabled, bool):
            raise ValueError(
                "always_on_top must be a boolean."
            )

        was_visible = self.isVisible()

        self.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint,
            enabled,
        )

        if was_visible:
            self.show()

    def set_click_through(
        self,
        enabled: bool,
    ) -> None:
        if not isinstance(enabled, bool):
            raise ValueError(
                "click_through must be a boolean."
            )

        was_visible = self.isVisible()

        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            enabled,
        )

        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput,
            enabled,
        )

        if was_visible:
            self.show()

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

        if not (
            MIN_ANIMATION_SPEED_PERCENT
            <= preferences.animation_speed_percent
            <= MAX_ANIMATION_SPEED_PERCENT
        ):
            raise ValueError(
                "Companion animation speed is invalid."
            )

        self.set_scale_percent(
            preferences.scale_percent
        )

        self.set_companion_opacity(
            preferences.opacity
        )

        self.set_always_on_top(
            preferences.always_on_top
        )

        self.set_click_through(
            preferences.click_through
        )

        if preferences.asset_path:
            self.set_static_asset(
                preferences.asset_path
            )
        else:
            self.clear_asset()

        if (
            preferences.remember_position
            and preferences.position_x is not None
            and preferences.position_y is not None
        ):
            self.move(
                preferences.position_x,
                preferences.position_y,
            )

        if (
            preferences.enabled
            and not self._source_pixmap.isNull()
        ):
            self.show()
        else:
            self.hide()

    def _refresh_rendered_pixmap(
        self,
    ) -> None:
        if self._source_pixmap.isNull():
            self._image_label.clear()
            return

        width = max(
            1,
            round(
                self._source_pixmap.width()
                * self._scale_percent
                / 100
            ),
        )

        height = max(
            1,
            round(
                self._source_pixmap.height()
                * self._scale_percent
                / 100
            ),
        )

        rendered = self._source_pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self._image_label.setPixmap(
            rendered
        )

        self._image_label.resize(
            rendered.size()
        )

        self.resize(
            rendered.size()
        )