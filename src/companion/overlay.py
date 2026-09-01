from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QSize,
    Qt,
)
from PyQt6.QtGui import QMovie, QPixmap
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

ANIMATED_ASSET_SUFFIXES = frozenset(
    {
        ".gif",
    }
)


class CompanionOverlay(QWidget):
    """
    Independent transparent Desktop Companion window.

    Static images and animated GIFs are rendered locally through Qt.
    Global input reactions, fullscreen policy, settings UI, and runtime
    ownership intentionally remain outside this component.
    """

    def __init__(
        self,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._source_pixmap = QPixmap()

        self._movie: QMovie | None = None
        self._movie_buffer: QBuffer | None = None
        self._movie_source_size = QSize()

        self._asset_path = ""
        self._scale_percent = 100
        self._animation_speed_percent = 100

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
    def animation_speed_percent(self) -> int:
        return self._animation_speed_percent

    @property
    def is_animated(self) -> bool:
        return self._movie is not None

    @property
    def source_size(self) -> tuple[int, int]:
        if self._movie is not None:
            if not self._movie_source_size.isValid():
                return (0, 0)

            return (
                self._movie_source_size.width(),
                self._movie_source_size.height(),
            )

        if self._source_pixmap.isNull():
            return (0, 0)

        return (
            self._source_pixmap.width(),
            self._source_pixmap.height(),
        )

    def set_asset(
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

        if suffix in ANIMATED_ASSET_SUFFIXES:
            self.set_animated_asset(
                candidate
            )
            return

        if suffix in STATIC_ASSET_SUFFIXES:
            self.set_static_asset(
                candidate
            )
            return

        raise ValueError(
            "Unsupported Desktop Companion asset format."
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

        if suffix in ANIMATED_ASSET_SUFFIXES:
            raise ValueError(
                "GIF assets must use the animated Companion loader."
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

        self._release_movie()

        self._source_pixmap = pixmap
        self._asset_path = str(candidate)

        self._refresh_rendered_pixmap()

    def set_animated_asset(
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

        if candidate.suffix.lower() not in ANIMATED_ASSET_SUFFIXES:
            raise ValueError(
                "Animated Companion assets must use GIF."
            )

        if not candidate.is_file():
            raise FileNotFoundError(
                f"Companion asset does not exist: {candidate}"
            )

        try:
            raw_data = candidate.read_bytes()
        except OSError as error:
            raise ValueError(
                "Companion GIF could not be read."
            ) from error

        if not raw_data:
            raise ValueError(
                "Companion GIF is empty."
            )

        movie_buffer = QBuffer()

        movie_buffer.setData(
            QByteArray(raw_data)
        )

        if not movie_buffer.open(
            QIODevice.OpenModeFlag.ReadOnly
        ):
            raise ValueError(
                "Companion GIF buffer could not be opened."
            )

        movie = QMovie(
            movie_buffer,
            QByteArray(b"gif"),
        )

        movie_buffer.setParent(
            movie
        )

        movie.setCacheMode(
            QMovie.CacheMode.CacheNone
        )

        movie.setSpeed(
            self._animation_speed_percent
        )

        if not movie.isValid():
            raise ValueError(
                "Companion GIF could not be decoded."
            )

        if not movie.jumpToFrame(0):
            movie.stop()

            raise ValueError(
                "Companion GIF has no readable first frame."
            )

        first_frame = movie.currentPixmap()

        if first_frame.isNull():
            movie.stop()

            raise ValueError(
                "Companion GIF first frame is invalid."
            )

        source_size = first_frame.size()

        if not source_size.isValid():
            movie.stop()

            raise ValueError(
                "Companion GIF has invalid dimensions."
            )

        self._release_movie()

        self._source_pixmap = QPixmap()
        self._movie = movie
        self._movie_buffer = movie_buffer
        self._movie_source_size = source_size
        self._asset_path = str(candidate)

        self._image_label.clear()

        self._image_label.setMovie(
            movie
        )

        self._refresh_animated_size()

        movie.start()

    def clear_asset(self) -> None:
        self._release_movie()

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

        if self._movie is not None:
            self._refresh_animated_size()
        elif not self._source_pixmap.isNull():
            self._refresh_rendered_pixmap()

    def set_animation_speed_percent(
        self,
        speed_percent: int,
    ) -> None:
        if (
            isinstance(speed_percent, bool)
            or not isinstance(speed_percent, int)
        ):
            raise ValueError(
                "Companion animation speed must be an integer."
            )

        if not (
            MIN_ANIMATION_SPEED_PERCENT
            <= speed_percent
            <= MAX_ANIMATION_SPEED_PERCENT
        ):
            raise ValueError(
                "Companion animation speed is outside "
                "the supported range."
            )

        self._animation_speed_percent = speed_percent

        if self._movie is not None:
            self._movie.setSpeed(
                speed_percent
            )

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

        self.set_animation_speed_percent(
            preferences.animation_speed_percent
        )

        if preferences.asset_path:
            self.set_asset(
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

        has_asset = (
            self._movie is not None
            or not self._source_pixmap.isNull()
        )

        if (
            preferences.enabled
            and has_asset
        ):
            self.show()

            if self._movie is not None:
                self._movie.start()
        else:
            if self._movie is not None:
                self._movie.stop()

            self.hide()

    def closeEvent(
        self,
        event,
    ) -> None:
        self._release_movie()

        super().closeEvent(
            event
        )

    def _release_movie(self) -> None:
        movie = self._movie
        movie_buffer = self._movie_buffer

        if movie is not None:
            movie.stop()

            self._image_label.setMovie(
                None
            )

        if movie_buffer is not None:
            movie_buffer.close()

        self._movie = None
        self._movie_buffer = None
        self._movie_source_size = QSize()

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

    def _refresh_animated_size(
        self,
    ) -> None:
        if self._movie is None:
            return

        if not self._movie_source_size.isValid():
            return

        width = max(
            1,
            round(
                self._movie_source_size.width()
                * self._scale_percent
                / 100
            ),
        )

        height = max(
            1,
            round(
                self._movie_source_size.height()
                * self._scale_percent
                / 100
            ),
        )

        target_size = QSize(
            width,
            height,
        )

        self._movie.setScaledSize(
            target_size
        )

        self._image_label.resize(
            target_size
        )

        self.resize(
            target_size
        )