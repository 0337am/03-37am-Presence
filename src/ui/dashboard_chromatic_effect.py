from __future__ import annotations

import math

from PyQt6.QtCore import (
    QEvent,
    QPointF,
    QRectF,
    Qt,
    QTimer,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QLinearGradient,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import QWidget

from src.system.dashboard_chromatic import (
    CHROMATIC_EFFECT_GRADIENT,
    CHROMATIC_EFFECT_NEON,
    CHROMATIC_EFFECT_PRISM,
    CHROMATIC_EFFECT_SOLID,
    VALID_CHROMATIC_EFFECTS,
)


FRAME_INTERVAL_MS = 33

ANIMATED_EFFECTS = frozenset(
    {
        CHROMATIC_EFFECT_GRADIENT,
        CHROMATIC_EFFECT_NEON,
        CHROMATIC_EFFECT_PRISM,
    }
)


def _normalise_style(
    value,
):
    value = str(
        value
        or ""
    ).strip().casefold()

    if value not in VALID_CHROMATIC_EFFECTS:
        return CHROMATIC_EFFECT_SOLID

    return value


def _normalise_intensity(
    value,
):
    try:
        value = int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        value = 0

    return max(
        0,
        min(
            100,
            value,
        ),
    )


def _normalise_colours(
    values,
):
    result = []

    if not isinstance(
        values,
        (
            list,
            tuple,
        ),
    ):
        values = ()

    for raw in values:
        colour = QColor(
            str(
                raw
                or ""
            )
        )

        if not colour.isValid():
            continue

        value = colour.name(
            QColor.NameFormat.HexRgb
        ).lower()

        if value not in result:
            result.append(
                value
            )

    if not result:
        result.append(
            "#ff79b9"
        )

    return tuple(
        result
    )


def _alpha_colour(
    colour,
    alpha,
):
    value = QColor(
        colour
    )

    value.setAlpha(
        max(
            0,
            min(
                255,
                int(
                    alpha
                ),
            ),
        )
    )

    return value


def _gradient_brush(
    rect,
    colours,
    phase,
    alpha,
):
    centre = rect.center()

    angle = (
        float(
            phase
        )
        * math.tau
    )

    length = max(
        rect.width(),
        rect.height(),
        1.0,
    )

    dx = (
        math.cos(
            angle
        )
        * length
        * 0.55
    )

    dy = (
        math.sin(
            angle
        )
        * length
        * 0.55
    )

    gradient = QLinearGradient(
        QPointF(
            centre.x() - dx,
            centre.y() - dy,
        ),
        QPointF(
            centre.x() + dx,
            centre.y() + dy,
        ),
    )

    values = list(
        colours[
            :5
        ]
    )

    if not values:
        values = [
            "#ff79b9",
        ]

    if len(
        values
    ) == 1:
        values.append(
            values[0]
        )

    denominator = max(
        1,
        len(
            values
        )
        - 1,
    )

    for (
        index,
        colour,
    ) in enumerate(
        values
    ):
        gradient.setColorAt(
            (
                index
                / denominator
            ),
            _alpha_colour(
                colour,
                alpha,
            ),
        )

    return QBrush(
        gradient
    )


def _prism_brush(
    rect,
    colours,
    phase,
    alpha,
):
    values = list(
        colours
    )

    while len(
        values
    ) < 3:
        values.append(
            values[-1]
        )

    gradient = QConicalGradient(
        rect.center(),
        (
            float(
                phase
            )
            * 360.0
        ),
    )

    for index, colour in enumerate(
        values
    ):
        gradient.setColorAt(
            (
                index
                / len(
                    values
                )
            ),
            _alpha_colour(
                colour,
                alpha,
            ),
        )

    gradient.setColorAt(
        1.0,
        _alpha_colour(
            values[0],
            alpha,
        ),
    )

    return QBrush(
        gradient
    )


def _effect_brush(
    rect,
    style,
    colours,
    phase,
    alpha,
):
    if (
        style
        == CHROMATIC_EFFECT_GRADIENT
    ):
        return _gradient_brush(
            rect,
            colours,
            phase,
            alpha,
        )

    if (
        style
        == CHROMATIC_EFFECT_PRISM
    ):
        return _prism_brush(
            rect,
            colours,
            phase,
            alpha,
        )

    return QBrush(
        _alpha_colour(
            colours[0],
            alpha,
        )
    )


def paint_chromatic_frame(
    painter,
    rect,
    *,
    style,
    colours,
    intensity,
    phase,
    radius=12.0,
):
    style = _normalise_style(
        style
    )

    colours = _normalise_colours(
        colours
    )

    intensity = _normalise_intensity(
        intensity
    )

    if (
        intensity <= 0
        or rect.width() < 8
        or rect.height() < 8
    ):
        return False

    strength = (
        intensity
        / 100.0
    )

    painter.save()

    try:
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        painter.setBrush(
            Qt.BrushStyle.NoBrush
        )

        if (
            style
            == CHROMATIC_EFFECT_NEON
        ):
            pulse = (
                0.68
                + (
                    0.32
                    * (
                        (
                            math.sin(
                                float(
                                    phase
                                )
                                * math.tau
                            )
                            + 1.0
                        )
                        / 2.0
                    )
                )
            )

            for width, alpha_scale in (
                (
                    12.0,
                    0.24,
                ),
                (
                    7.0,
                    0.43,
                ),
                (
                    3.8,
                    0.68,
                ),
            ):
                pen = QPen(
                    QBrush(
                        _alpha_colour(
                            colours[0],
                            (
                                100
                                * strength
                                * pulse
                                * alpha_scale
                            ),
                        )
                    ),
                    max(
                        1.0,
                        width
                        * strength,
                    ),
                )

                pen.setJoinStyle(
                    Qt.PenJoinStyle.RoundJoin
                )

                painter.setPen(
                    pen
                )

                painter.drawRoundedRect(
                    rect,
                    radius,
                    radius,
                )

            painter.setPen(
                QPen(
                    QBrush(
                        _alpha_colour(
                            colours[0],
                            (
                                170
                                + (
                                    85
                                    * strength
                                    * pulse
                                )
                            ),
                        )
                    ),
                    (
                        1.2
                        + (
                            1.5
                            * strength
                        )
                    ),
                )
            )

            painter.drawRoundedRect(
                rect,
                radius,
                radius,
            )

            return True

        painter.setPen(
            QPen(
                _effect_brush(
                    rect,
                    style,
                    colours,
                    phase,
                    (
                        48
                        + (
                            72
                            * strength
                        )
                    ),
                ),
                (
                    2.2
                    + (
                        3.8
                        * strength
                    )
                ),
            )
        )

        painter.drawRoundedRect(
            rect,
            radius,
            radius,
        )

        painter.setPen(
            QPen(
                _effect_brush(
                    rect,
                    style,
                    colours,
                    phase,
                    (
                        150
                        + (
                            105
                            * strength
                        )
                    ),
                ),
                (
                    1.15
                    + (
                        1.7
                        * strength
                    )
                ),
            )
        )

        painter.drawRoundedRect(
            rect,
            radius,
            radius,
        )

        return True

    finally:
        painter.restore()


class DashboardChromaticEffectOverlay(
    QWidget
):

    def __init__(
        self,
        parent,
        *,
        target_provider=None,
    ):
        super().__init__(
            parent
        )

        self._target_provider = (
            target_provider
        )

        self._enabled = False
        self._effect_style = (
            CHROMATIC_EFFECT_SOLID
        )
        self._intensity = 0
        self._colours = (
            "#ff79b9",
        )
        self._phase = 0.0

        self.setObjectName(
            "dashboardChromaticEffectOverlay"
        )

        self.setAttribute(
            Qt.WidgetAttribute
            .WA_TransparentForMouseEvents,
            True,
        )

        self.setAttribute(
            Qt.WidgetAttribute
            .WA_NoSystemBackground,
            True,
        )

        self.setAttribute(
            Qt.WidgetAttribute
            .WA_TranslucentBackground,
            True,
        )

        self.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        self._animation_timer = QTimer(
            self
        )

        self._animation_timer.setInterval(
            FRAME_INTERVAL_MS
        )

        self._animation_timer.timeout.connect(
            self._tick
        )

        parent.installEventFilter(
            self
        )

        self._sync_geometry()
        self.hide()

    @property
    def effect_style(self):
        return self._effect_style

    @property
    def colours(self):
        return self._colours

    @property
    def intensity(self):
        return self._intensity

    def configure(
        self,
        *,
        enabled,
        style,
        intensity,
        colours,
    ):
        self._enabled = bool(
            enabled
        )

        self._effect_style = (
            _normalise_style(
                style
            )
        )

        self._intensity = (
            _normalise_intensity(
                intensity
            )
        )

        self._colours = (
            _normalise_colours(
                colours
            )
        )

        active = (
            self._enabled
            and self._intensity > 0
        )

        if active:
            self._sync_geometry()
            self.show()
            self.raise_()

        else:
            self.hide()

        self._sync_animation()
        self.update()

    def _target_widgets(self):
        provider = (
            self._target_provider
        )

        if not callable(
            provider
        ):
            return ()

        try:
            values = provider()

        except Exception:
            return ()

        try:
            return tuple(
                values
            )

        except (
            TypeError,
            RuntimeError,
        ):
            return ()

    def _editing(
        self,
        widgets,
    ):
        for widget in widgets:
            if widget is None:
                continue

            try:
                if bool(
                    widget.property(
                        "dashboardEditing"
                    )
                ):
                    return True

            except RuntimeError:
                continue

        return False

    def _should_animate(self):
        return (
            self._enabled
            and self._intensity > 0
            and self._effect_style
            in ANIMATED_EFFECTS
            and self.isVisible()
        )

    def _sync_animation(self):
        if self._should_animate():
            if not self._animation_timer.isActive():
                self._animation_timer.start()

        elif self._animation_timer.isActive():
            self._animation_timer.stop()

    def _sync_geometry(self):
        parent = self.parentWidget()

        if parent is not None:
            self.setGeometry(
                parent.rect()
            )

    def _tick(self):
        if not self._should_animate():
            self._sync_animation()
            return

        step = (
            0.012
            if (
                self._effect_style
                == CHROMATIC_EFFECT_NEON
            )
            else 0.0065
        )

        self._phase = (
            self._phase
            + step
        ) % 1.0

        self.raise_()
        self.update()

    def eventFilter(
        self,
        watched,
        event,
    ):
        if watched is self.parentWidget():
            if event.type() in {
                QEvent.Type.Resize,
                QEvent.Type.Show,
                QEvent.Type.LayoutRequest,
            }:
                self._sync_geometry()
                self.raise_()
                self.update()

            elif (
                event.type()
                == QEvent.Type.ChildAdded
            ):
                QTimer.singleShot(
                    0,
                    self._raise_later,
                )

        return super().eventFilter(
            watched,
            event,
        )

    def _raise_later(self):
        if self._enabled:
            self.raise_()
            self.update()

    def showEvent(
        self,
        event,
    ):
        super().showEvent(
            event
        )

        self._sync_animation()

    def hideEvent(
        self,
        event,
    ):
        if self._animation_timer.isActive():
            self._animation_timer.stop()

        super().hideEvent(
            event
        )

    def paintEvent(
        self,
        event,
    ):
        if (
            not self._enabled
            or self._intensity <= 0
        ):
            return

        widgets = (
            self._target_widgets()
        )

        if self._editing(
            widgets
        ):
            return

        painter = QPainter(
            self
        )

        try:
            for widget in widgets:
                if widget is None:
                    continue

                try:
                    if not widget.isVisible():
                        continue

                    rect = QRectF(
                        widget.geometry()
                    )

                except RuntimeError:
                    continue

                rect.adjust(
                    3.0,
                    3.0,
                    -3.0,
                    -3.0,
                )

                paint_chromatic_frame(
                    painter,
                    rect,
                    style=(
                        self._effect_style
                    ),
                    colours=(
                        self._colours
                    ),
                    intensity=(
                        self._intensity
                    ),
                    phase=(
                        self._phase
                    ),
                    radius=12.0,
                )

        finally:
            painter.end()


class ChromaticEffectPreview(
    QWidget
):

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self._effect_style = (
            CHROMATIC_EFFECT_SOLID
        )
        self._intensity = 80
        self._colours = (
            "#ff79b9",
        )
        self._surface = (
            "#18181f"
        )
        self._text = (
            "#f4f4f6"
        )
        self._phase = 0.0

        self.setObjectName(
            "dashboardChromaticEffectPreview"
        )

        self.setMinimumHeight(
            72
        )

        self.setMaximumHeight(
            82
        )

        self.setAttribute(
            Qt.WidgetAttribute
            .WA_TransparentForMouseEvents,
            True,
        )

        self._animation_timer = QTimer(
            self
        )

        self._animation_timer.setInterval(
            FRAME_INTERVAL_MS
        )

        self._animation_timer.timeout.connect(
            self._tick
        )

    @property
    def effect_style(self):
        return self._effect_style

    @property
    def colours(self):
        return self._colours

    @property
    def intensity(self):
        return self._intensity

    def configure(
        self,
        *,
        style,
        intensity,
        colours,
        surface,
        text,
    ):
        self._effect_style = (
            _normalise_style(
                style
            )
        )

        self._intensity = (
            _normalise_intensity(
                intensity
            )
        )

        self._colours = (
            _normalise_colours(
                colours
            )
        )

        surface_colour = QColor(
            str(
                surface
                or ""
            )
        )

        if surface_colour.isValid():
            self._surface = (
                surface_colour.name(
                    QColor.NameFormat.HexRgb
                ).lower()
            )

        text_colour = QColor(
            str(
                text
                or ""
            )
        )

        if text_colour.isValid():
            self._text = (
                text_colour.name(
                    QColor.NameFormat.HexRgb
                ).lower()
            )

        self._sync_animation()
        self.update()

    def _should_animate(self):
        return (
            self._intensity > 0
            and self._effect_style
            in ANIMATED_EFFECTS
            and self.isVisible()
        )

    def _sync_animation(self):
        if self._should_animate():
            if not self._animation_timer.isActive():
                self._animation_timer.start()

        elif self._animation_timer.isActive():
            self._animation_timer.stop()

    def _tick(self):
        if not self._should_animate():
            self._sync_animation()
            return

        step = (
            0.012
            if (
                self._effect_style
                == CHROMATIC_EFFECT_NEON
            )
            else 0.0065
        )

        self._phase = (
            self._phase
            + step
        ) % 1.0

        self.update()

    def showEvent(
        self,
        event,
    ):
        super().showEvent(
            event
        )

        self._sync_animation()

    def hideEvent(
        self,
        event,
    ):
        if self._animation_timer.isActive():
            self._animation_timer.stop()

        super().hideEvent(
            event
        )

    def paintEvent(
        self,
        event,
    ):
        painter = QPainter(
            self
        )

        try:
            painter.setRenderHint(
                QPainter.RenderHint.Antialiasing,
                True,
            )

            rect = QRectF(
                self.rect()
            ).adjusted(
                6.0,
                6.0,
                -6.0,
                -6.0,
            )

            painter.setPen(
                Qt.PenStyle.NoPen
            )

            painter.setBrush(
                QColor(
                    self._surface
                )
            )

            painter.drawRoundedRect(
                rect,
                11.0,
                11.0,
            )

            paint_chromatic_frame(
                painter,
                rect.adjusted(
                    2.5,
                    2.5,
                    -2.5,
                    -2.5,
                ),
                style=(
                    self._effect_style
                ),
                colours=(
                    self._colours
                ),
                intensity=(
                    self._intensity
                ),
                phase=(
                    self._phase
                ),
                radius=9.0,
            )

            painter.setPen(
                QColor(
                    self._text
                )
            )

            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                "03:37am",
            )

        finally:
            painter.end()
