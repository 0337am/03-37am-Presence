from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QColor, QImage


PALETTE_SOURCE_THEME = "theme"
PALETTE_SOURCE_BACKGROUND = "background"
PALETTE_SOURCE_MANUAL = "manual"

VALID_PALETTE_SOURCES = frozenset(
    {
        PALETTE_SOURCE_THEME,
        PALETTE_SOURCE_BACKGROUND,
        PALETTE_SOURCE_MANUAL,
    }
)

MAX_PALETTE_COLOURS = 5
DEFAULT_PRIMARY = "#ff79b9"

DEFAULT_MANUAL_PALETTE = (
    DEFAULT_PRIMARY,
    DEFAULT_PRIMARY,
    DEFAULT_PRIMARY,
    DEFAULT_PRIMARY,
    DEFAULT_PRIMARY,
)

DEFAULT_MANUAL_COUNT = 1
DEFAULT_COLOUR_STRENGTH = 80
SETTINGS_PREFIX = "dashboard/palette"


def _bool_value(
    value,
    default=False,
):
    if isinstance(
        value,
        bool,
    ):
        return value

    if value is None:
        return bool(
            default
        )

    text = str(
        value
    ).strip().casefold()

    if text in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True

    if text in {
        "0",
        "false",
        "no",
        "off",
    }:
        return False

    return bool(
        default
    )


def _int_value(
    value,
    default,
    minimum,
    maximum,
):
    try:
        value = int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        value = int(
            default
        )

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def _hex_colour(
    value,
    fallback="",
):
    colour = QColor(
        str(
            value
            or ""
        )
    )

    if not colour.isValid():
        return fallback

    return colour.name(
        QColor.NameFormat.HexRgb
    ).lower()


def normalise_palette(
    values,
    maximum=MAX_PALETTE_COLOURS,
):
    if isinstance(
        values,
        str,
    ):
        try:
            values = json.loads(
                values
            )

        except Exception:
            values = ()

    if not isinstance(
        values,
        (
            list,
            tuple,
        ),
    ):
        values = ()

    result = []

    for raw in values:
        colour = _hex_colour(
            raw
        )

        if not colour:
            continue

        result.append(
            colour
        )

        if (
            len(
                result
            )
            >= maximum
        ):
            break

    return tuple(
        result
    )


def normalise_manual_palette(
    values,
):
    if isinstance(
        values,
        str,
    ):
        try:
            values = json.loads(
                values
            )

        except Exception:
            values = ()

    if not isinstance(
        values,
        (
            list,
            tuple,
        ),
    ):
        values = ()

    result = []

    for raw in values[
        :MAX_PALETTE_COLOURS
    ]:
        result.append(
            _hex_colour(
                raw,
                fallback=DEFAULT_PRIMARY,
            )
        )

    pad = (
        result[0]
        if result
        else DEFAULT_PRIMARY
    )

    while (
        len(
            result
        )
        < MAX_PALETTE_COLOURS
    ):
        result.append(
            pad
        )

    return tuple(
        result[
            :MAX_PALETTE_COLOURS
        ]
    )


@dataclass(frozen=True)
class DashboardPalettePreferences:
    source: str = (
        PALETTE_SOURCE_THEME
    )

    manual_palette: tuple[str, ...] = (
        DEFAULT_MANUAL_PALETTE
    )

    manual_count: int = (
        DEFAULT_MANUAL_COUNT
    )

    matched_palette: tuple[str, ...] = ()

    strength: int = (
        DEFAULT_COLOUR_STRENGTH
    )

    locked: bool = False

    def __post_init__(
        self,
    ):
        if (
            self.source
            not in VALID_PALETTE_SOURCES
        ):
            raise ValueError(
                "Unknown Dashboard palette source."
            )

        if (
            len(
                self.manual_palette
            )
            != MAX_PALETTE_COLOURS
        ):
            raise ValueError(
                "Manual Dashboard palette must contain five slots."
            )

        for colour in (
            self.manual_palette
        ):
            if (
                _hex_colour(
                    colour
                )
                != colour
            ):
                raise ValueError(
                    "Manual Dashboard palette contains an invalid colour."
                )

        if not (
            1
            <= int(
                self.manual_count
            )
            <= MAX_PALETTE_COLOURS
        ):
            raise ValueError(
                "Manual Dashboard palette count is out of range."
            )

        if (
            len(
                self.matched_palette
            )
            > MAX_PALETTE_COLOURS
        ):
            raise ValueError(
                "Matched Dashboard palette is too large."
            )

        for colour in (
            self.matched_palette
        ):
            if (
                _hex_colour(
                    colour
                )
                != colour
            ):
                raise ValueError(
                    "Matched Dashboard palette contains an invalid colour."
                )

        if not (
            0
            <= int(
                self.strength
            )
            <= 100
        ):
            raise ValueError(
                "Dashboard colour strength is out of range."
            )

    @classmethod
    def build(
        cls,
        *,
        source=PALETTE_SOURCE_THEME,
        manual_palette=DEFAULT_MANUAL_PALETTE,
        manual_count=DEFAULT_MANUAL_COUNT,
        matched_palette=(),
        strength=DEFAULT_COLOUR_STRENGTH,
        locked=False,
    ):
        source_value = str(
            source
            or ""
        ).strip().casefold()

        if (
            source_value
            not in VALID_PALETTE_SOURCES
        ):
            source_value = (
                PALETTE_SOURCE_THEME
            )

        return cls(
            source=source_value,
            manual_palette=(
                normalise_manual_palette(
                    manual_palette
                )
            ),
            manual_count=_int_value(
                manual_count,
                DEFAULT_MANUAL_COUNT,
                1,
                MAX_PALETTE_COLOURS,
            ),
            matched_palette=(
                normalise_palette(
                    matched_palette
                )
            ),
            strength=_int_value(
                strength,
                DEFAULT_COLOUR_STRENGTH,
                0,
                100,
            ),
            locked=_bool_value(
                locked
            ),
        )


class DashboardPalettePreferencesStore:

    def __init__(
        self,
        settings=None,
    ):
        self.settings = (
            settings
            if settings
            is not None
            else QSettings(
                "0337am",
                "Presence",
            )
        )

    @staticmethod
    def _key(
        name,
    ):
        return (
            SETTINGS_PREFIX
            + "/"
            + str(
                name
            )
        )

    def load(
        self,
    ):
        try:
            return (
                DashboardPalettePreferences
                .build(
                    source=(
                        self.settings.value(
                            self._key(
                                "source"
                            ),
                            PALETTE_SOURCE_THEME,
                        )
                    ),
                    manual_palette=(
                        self.settings.value(
                            self._key(
                                "manual_palette"
                            ),
                            json.dumps(
                                DEFAULT_MANUAL_PALETTE
                            ),
                        )
                    ),
                    manual_count=(
                        self.settings.value(
                            self._key(
                                "manual_count"
                            ),
                            DEFAULT_MANUAL_COUNT,
                        )
                    ),
                    matched_palette=(
                        self.settings.value(
                            self._key(
                                "matched_palette"
                            ),
                            "[]",
                        )
                    ),
                    strength=(
                        self.settings.value(
                            self._key(
                                "strength"
                            ),
                            DEFAULT_COLOUR_STRENGTH,
                        )
                    ),
                    locked=(
                        self.settings.value(
                            self._key(
                                "locked"
                            ),
                            False,
                        )
                    ),
                )
            )

        except Exception:
            return (
                DashboardPalettePreferences()
            )

    def save(
        self,
        preferences,
    ):
        if not isinstance(
            preferences,
            DashboardPalettePreferences,
        ):
            raise TypeError(
                "preferences must be DashboardPalettePreferences."
            )

        values = {
            "source":
                preferences.source,

            "manual_palette":
                json.dumps(
                    list(
                        preferences.manual_palette
                    ),
                    separators=(
                        ",",
                        ":",
                    ),
                ),

            "manual_count":
                preferences.manual_count,

            "matched_palette":
                json.dumps(
                    list(
                        preferences.matched_palette
                    ),
                    separators=(
                        ",",
                        ":",
                    ),
                ),

            "strength":
                preferences.strength,

            "locked":
                preferences.locked,
        }

        for (
            name,
            value,
        ) in values.items():
            self.settings.setValue(
                self._key(
                    name
                ),
                value,
            )

        self.settings.sync()


def _colour_metrics(
    colour,
):
    qcolour = QColor(
        colour
    )

    red = (
        qcolour.redF()
    )

    green = (
        qcolour.greenF()
    )

    blue = (
        qcolour.blueF()
    )

    maximum = max(
        red,
        green,
        blue,
    )

    minimum = min(
        red,
        green,
        blue,
    )

    value = maximum

    saturation = (
        0.0
        if maximum <= 0.0
        else (
            maximum
            - minimum
        )
        / maximum
    )

    hue = (
        qcolour.hsvHueF()
    )

    if hue < 0.0:
        hue = 0.0

    return (
        hue,
        saturation,
        value,
    )


def _useful_sample(
    colour,
):
    if (
        colour.alpha()
        < 64
    ):
        return False

    (
        _,
        saturation,
        value,
    ) = _colour_metrics(
        colour
    )

    if value < 0.12:
        return False

    if (
        value > 0.96
        and saturation < 0.16
    ):
        return False

    if saturation < 0.20:
        return False

    if (
        value < 0.30
        and saturation < 0.34
    ):
        return False

    return True


def _colour_distance(
    first,
    second,
):
    one = QColor(
        first
    )

    two = QColor(
        second
    )

    red = (
        one.redF()
        - two.redF()
    )

    green = (
        one.greenF()
        - two.greenF()
    )

    blue = (
        one.blueF()
        - two.blueF()
    )

    return math.sqrt(
        red
        * red
        + green
        * green
        + blue
        * blue
    )


def _hue_distance(
    first,
    second,
):
    first_hue = (
        QColor(
            first
        ).hsvHueF()
    )

    second_hue = (
        QColor(
            second
        ).hsvHueF()
    )

    if (
        first_hue < 0.0
        or second_hue < 0.0
    ):
        return 0.0

    distance = abs(
        first_hue
        - second_hue
    )

    return min(
        distance,
        1.0
        - distance,
    )


def extract_dashboard_palette_from_image(
    image,
):
    if not isinstance(
        image,
        QImage,
    ):
        return ()

    if image.isNull():
        return ()

    sample = (
        image.convertToFormat(
            QImage.Format.Format_ARGB32
        )
    )

    if (
        sample.width() > 72
        or sample.height() > 72
    ):
        sample = sample.scaled(
            72,
            72,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    buckets = {}

    for y in range(
        sample.height()
    ):
        for x in range(
            sample.width()
        ):
            colour = (
                QColor.fromRgba(
                    sample.pixel(
                        x,
                        y,
                    )
                )
            )

            if not _useful_sample(
                colour
            ):
                continue

            key = (
                colour.red()
                // 32,
                colour.green()
                // 32,
                colour.blue()
                // 32,
            )

            bucket = (
                buckets.setdefault(
                    key,
                    [
                        0,
                        0,
                        0,
                        0,
                    ],
                )
            )

            bucket[0] += 1
            bucket[1] += (
                colour.red()
            )
            bucket[2] += (
                colour.green()
            )
            bucket[3] += (
                colour.blue()
            )

    candidates = []

    for (
        count,
        red,
        green,
        blue,
    ) in buckets.values():
        if count <= 0:
            continue

        colour = QColor(
            round(
                red
                / count
            ),
            round(
                green
                / count
            ),
            round(
                blue
                / count
            ),
        )

        value = colour.name(
            QColor.NameFormat.HexRgb
        ).lower()

        (
            _,
            saturation,
            brightness,
        ) = _colour_metrics(
            colour
        )

        score = (
            float(
                count
            )
            * (
                0.42
                + saturation
            )
            * (
                0.52
                + brightness
            )
        )

        candidates.append(
            (
                score,
                value,
            )
        )

    candidates.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    selected = []

    for (
        _,
        colour,
    ) in candidates:
        if not selected:
            selected.append(
                colour
            )

        else:
            distinct = all(
                (
                    _colour_distance(
                        colour,
                        existing,
                    )
                    >= 0.18
                )
                or (
                    _hue_distance(
                        colour,
                        existing,
                    )
                    >= 0.075
                )
                for existing
                in selected
            )

            if distinct:
                selected.append(
                    colour
                )

        if (
            len(
                selected
            )
            >= MAX_PALETTE_COLOURS
        ):
            break

    if (
        len(
            selected
        )
        < MAX_PALETTE_COLOURS
    ):
        for (
            _,
            colour,
        ) in candidates:
            if colour in selected:
                continue

            if all(
                _colour_distance(
                    colour,
                    existing,
                )
                >= 0.11
                for existing
                in selected
            ):
                selected.append(
                    colour
                )

            if (
                len(
                    selected
                )
                >= MAX_PALETTE_COLOURS
            ):
                break

    return tuple(
        selected[
            :MAX_PALETTE_COLOURS
        ]
    )


def extract_dashboard_palette_from_path(
    path,
):
    value = str(
        path
        or ""
    ).strip()

    if not value:
        return ()

    image_path = Path(
        value
    )

    if not image_path.is_file():
        return ()

    image = QImage(
        str(
            image_path
        )
    )

    return (
        extract_dashboard_palette_from_image(
            image
        )
    )


def update_matched_palette(
    preferences,
    colours,
    *,
    force=False,
):
    if not isinstance(
        preferences,
        DashboardPalettePreferences,
    ):
        raise TypeError(
            "preferences must be DashboardPalettePreferences."
        )

    if (
        preferences.locked
        and not force
    ):
        return preferences

    return replace(
        preferences,
        matched_palette=(
            normalise_palette(
                colours
            )
        ),
    )


def resolve_dashboard_palette(
    base_theme,
    preferences,
):
    if not isinstance(
        base_theme,
        dict,
    ):
        raise TypeError(
            "base_theme must be a dict."
        )

    if not isinstance(
        preferences,
        DashboardPalettePreferences,
    ):
        raise TypeError(
            "preferences must be DashboardPalettePreferences."
        )

    base_accent = _hex_colour(
        base_theme.get(
            "accent",
            DEFAULT_PRIMARY,
        ),
        fallback=DEFAULT_PRIMARY,
    )

    if (
        preferences.source
        == PALETTE_SOURCE_MANUAL
    ):
        colours = tuple(
            preferences.manual_palette[
                :preferences.manual_count
            ]
        )

        if colours:
            return colours

    elif (
        preferences.source
        == PALETTE_SOURCE_BACKGROUND
    ):
        colours = tuple(
            preferences.matched_palette
        )

        if colours:
            return colours

    return (
        base_accent,
    )


def _mix_colour(
    base,
    overlay,
    amount,
):
    base_colour = QColor(
        _hex_colour(
            base,
            fallback="#000000",
        )
    )

    overlay_colour = QColor(
        _hex_colour(
            overlay,
            fallback=(
                base_colour.name(
                    QColor.NameFormat.HexRgb
                )
            ),
        )
    )

    amount = max(
        0.0,
        min(
            1.0,
            float(
                amount
            ),
        ),
    )

    red = round(
        base_colour.red()
        * (
            1.0
            - amount
        )
        + overlay_colour.red()
        * amount
    )

    green = round(
        base_colour.green()
        * (
            1.0
            - amount
        )
        + overlay_colour.green()
        * amount
    )

    blue = round(
        base_colour.blue()
        * (
            1.0
            - amount
        )
        + overlay_colour.blue()
        * amount
    )

    return QColor(
        red,
        green,
        blue,
    ).name(
        QColor.NameFormat.HexRgb
    ).lower()


def _relative_luminance(
    colour,
):
    qcolour = QColor(
        colour
    )

    components = []

    for value in (
        qcolour.redF(),
        qcolour.greenF(),
        qcolour.blueF(),
    ):
        if value <= 0.04045:
            components.append(
                value
                / 12.92
            )

        else:
            components.append(
                (
                    (
                        value
                        + 0.055
                    )
                    / 1.055
                )
                ** 2.4
            )

    return (
        0.2126
        * components[0]
        + 0.7152
        * components[1]
        + 0.0722
        * components[2]
    )


def _contrast_ratio(
    first,
    second,
):
    one = (
        _relative_luminance(
            first
        )
    )

    two = (
        _relative_luminance(
            second
        )
    )

    lighter = max(
        one,
        two,
    )

    darker = min(
        one,
        two,
    )

    return (
        lighter
        + 0.05
    ) / (
        darker
        + 0.05
    )


def _safe_static_accent(
    colour,
    background,
):
    colour = _hex_colour(
        colour,
        fallback=DEFAULT_PRIMARY,
    )

    background = _hex_colour(
        background,
        fallback="#140812",
    )

    if (
        _contrast_ratio(
            colour,
            background,
        )
        >= 3.0
    ):
        return colour

    source = QColor(
        colour
    )

    hue = (
        source.hsvHueF()
    )

    if hue < 0.0:
        hue = 0.0

    saturation = max(
        source.hsvSaturationF(),
        0.45,
    )

    for value in (
        0.72,
        0.80,
        0.88,
        0.96,
        1.0,
    ):
        candidate = (
            QColor.fromHsvF(
                hue,
                min(
                    1.0,
                    saturation,
                ),
                value,
                1.0,
            )
            .name(
                QColor.NameFormat.HexRgb
            )
            .lower()
        )

        if (
            _contrast_ratio(
                candidate,
                background,
            )
            >= 3.0
        ):
            return candidate

    return colour


def build_dashboard_palette_theme(
    base_theme,
    preferences,
):
    if not isinstance(
        base_theme,
        dict,
    ):
        raise TypeError(
            "base_theme must be a dict."
        )

    if not isinstance(
        preferences,
        DashboardPalettePreferences,
    ):
        raise TypeError(
            "preferences must be DashboardPalettePreferences."
        )

    result = dict(
        base_theme
    )

    if (
        preferences.source
        == PALETTE_SOURCE_THEME
        or preferences.strength <= 0
    ):
        return result

    palette = (
        resolve_dashboard_palette(
            base_theme,
            preferences,
        )
    )

    if not palette:
        return result

    strength = (
        preferences.strength
        / 100.0
    )

    background = _hex_colour(
        base_theme.get(
            "background",
            "#140812",
        ),
        fallback="#140812",
    )

    primary = (
        _safe_static_accent(
            palette[0],
            background,
        )
    )

    secondary = (
        palette[1]
        if len(
            palette
        ) > 1
        else primary
    )

    tertiary = (
        palette[2]
        if len(
            palette
        ) > 2
        else primary
    )

    fourth = (
        palette[3]
        if len(
            palette
        ) > 3
        else secondary
    )

    fifth = (
        palette[4]
        if len(
            palette
        ) > 4
        else tertiary
    )

    result["accent"] = (
        _mix_colour(
            base_theme.get(
                "accent",
                DEFAULT_PRIMARY,
            ),
            primary,
            strength,
        )
    )

    result["border"] = (
        _mix_colour(
            base_theme.get(
                "border",
                "#34343e",
            ),
            secondary,
            strength
            * 0.34,
        )
    )

    result["card"] = (
        _mix_colour(
            base_theme.get(
                "card",
                "#18181f",
            ),
            tertiary,
            strength
            * 0.10,
        )
    )

    result["card_alt"] = (
        _mix_colour(
            base_theme.get(
                "card_alt",
                "#202028",
            ),
            fourth,
            strength
            * 0.13,
        )
    )

    if "selection" in result:
        result["selection"] = (
            _mix_colour(
                result[
                    "selection"
                ],
                fifth,
                strength
                * 0.28,
            )
        )

    return result


def effect_colours_for_style(
    palette,
    effect_style,
):
    colours = (
        normalise_palette(
            palette
        )
    )

    if not colours:
        colours = (
            DEFAULT_PRIMARY,
        )

    style = str(
        effect_style
        or ""
    ).strip().casefold()

    if style in {
        "solid",
        "neon",
    }:
        return (
            colours[0],
        )

    return tuple(
        colours
    )
