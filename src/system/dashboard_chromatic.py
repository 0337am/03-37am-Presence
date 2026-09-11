from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, replace
from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor, QImage


CHROMATIC_MODE_MANUAL = "manual"
CHROMATIC_MODE_BACKGROUND = "background"

CHROMATIC_EFFECT_SOLID = "solid"
CHROMATIC_EFFECT_GRADIENT = "gradient"
CHROMATIC_EFFECT_NEON = "neon"
CHROMATIC_EFFECT_PRISM = "prism"

DEFAULT_EFFECT_STYLE = CHROMATIC_EFFECT_SOLID

VALID_CHROMATIC_EFFECTS = frozenset(
    {
        CHROMATIC_EFFECT_SOLID,
        CHROMATIC_EFFECT_GRADIENT,
        CHROMATIC_EFFECT_NEON,
        CHROMATIC_EFFECT_PRISM,
    }
)

VALID_CHROMATIC_MODES = frozenset(
    {
        CHROMATIC_MODE_MANUAL,
        CHROMATIC_MODE_BACKGROUND,
    }
)

CHROMATIC_SETTINGS_PREFIX = "dashboard/chromatic"

DEFAULT_MANUAL_ACCENT = "#ff79b9"
DEFAULT_STRENGTH = 80

MIN_STRENGTH = 0
MAX_STRENGTH = 100

MAX_PALETTE_COLOURS = 3
MAX_SAMPLE_AXIS = 96

_MIN_SAMPLE_ALPHA = 96
_MIN_SAMPLE_SATURATION = 0.16
_MIN_SAMPLE_VALUE = 0.14

_TARGET_ACCENT_CONTRAST = 4.5

_HEX_RE = re.compile(
    r"^#(?P<rgb>[0-9a-fA-F]{6})$"
)


class DashboardChromaticError(ValueError):
    pass


def normalise_hex_colour(
    value,
    *,
    fallback="",
):
    raw = str(
        value
        or ""
    ).strip()

    if re.fullmatch(
        r"#[0-9a-fA-F]{3}",
        raw,
    ):
        raw = (
            "#"
            + "".join(
                character * 2
                for character in raw[1:]
            )
        )

    match = _HEX_RE.fullmatch(
        raw
    )

    if match is None:
        return str(
            fallback
            or ""
        ).strip().lower()

    return (
        "#"
        + match.group(
            "rgb"
        ).lower()
    )


def _require_colour(
    value,
    *,
    field_name,
    allow_empty=False,
):
    raw = str(
        value
        or ""
    ).strip()

    if allow_empty and not raw:
        return ""

    normalised = normalise_hex_colour(
        raw
    )

    if not normalised:
        raise DashboardChromaticError(
            field_name
            + " must be a #RRGGBB colour."
        )

    return normalised


def _clamp_strength(value):
    try:
        number = int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        number = DEFAULT_STRENGTH

    return max(
        MIN_STRENGTH,
        min(
            MAX_STRENGTH,
            number,
        ),
    )


def _coerce_bool(
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

    if isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        return bool(
            value
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
        "",
    }:
        return False

    return bool(
        default
    )


def _normalise_mode(value):
    mode = str(
        value
        or ""
    ).strip().casefold()

    if mode not in VALID_CHROMATIC_MODES:
        return CHROMATIC_MODE_BACKGROUND

    return mode


def _normalise_effect_style(
    value,
):
    style = str(
        value
        or ""
    ).strip().casefold()

    if style not in VALID_CHROMATIC_EFFECTS:
        return DEFAULT_EFFECT_STYLE

    return style


def _normalise_palette(values):
    if isinstance(
        values,
        str,
    ):
        try:
            values = json.loads(
                values
            )

        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            values = []

    if not isinstance(
        values,
        (
            list,
            tuple,
        ),
    ):
        return ()

    result = []

    for value in values:
        colour = normalise_hex_colour(
            value
        )

        if (
            not colour
            or colour in result
        ):
            continue

        result.append(
            colour
        )

        if (
            len(result)
            >= MAX_PALETTE_COLOURS
        ):
            break

    return tuple(
        result
    )


@dataclass(
    frozen=True,
)
class DashboardChromaticPalette:
    colours: tuple[str, ...] = ()

    def __post_init__(
        self,
    ):
        normalised = _normalise_palette(
            self.colours
        )

        if tuple(
            self.colours
        ) != normalised:
            raise DashboardChromaticError(
                "Palette colours must be unique "
                "normalised #RRGGBB values."
            )

    @classmethod
    def build(
        cls,
        colours=(),
    ):
        return cls(
            colours=_normalise_palette(
                colours
            )
        )

    @property
    def primary(self):
        return (
            self.colours[0]
            if self.colours
            else ""
        )

    @property
    def secondary(self):
        return (
            self.colours[1]
            if len(self.colours) >= 2
            else ""
        )

    @property
    def tertiary(self):
        return (
            self.colours[2]
            if len(self.colours) >= 3
            else ""
        )


@dataclass(
    frozen=True,
)
class DashboardChromaticPreferences:
    enabled: bool = False
    mode: str = CHROMATIC_MODE_BACKGROUND
    effect_style: str = DEFAULT_EFFECT_STYLE
    manual_accent: str = DEFAULT_MANUAL_ACCENT
    strength: int = DEFAULT_STRENGTH
    locked: bool = False
    matched_accent: str = ""
    matched_palette: tuple[str, ...] = ()

    def __post_init__(
        self,
    ):
        if not isinstance(
            self.enabled,
            bool,
        ):
            raise DashboardChromaticError(
                "enabled must be boolean."
            )

        if (
            self.mode
            not in VALID_CHROMATIC_MODES
        ):
            raise DashboardChromaticError(
                "Unknown Chromatic mode."
            )

        if (
            self.effect_style
            not in VALID_CHROMATIC_EFFECTS
        ):
            raise DashboardChromaticError(
                "Unknown Chromatic effect style."
            )

        if (
            self.manual_accent
            != _require_colour(
                self.manual_accent,
                field_name="manual_accent",
            )
        ):
            raise DashboardChromaticError(
                "manual_accent must be normalised."
            )

        if (
            not isinstance(
                self.strength,
                int,
            )
            or isinstance(
                self.strength,
                bool,
            )
            or not (
                MIN_STRENGTH
                <= self.strength
                <= MAX_STRENGTH
            )
        ):
            raise DashboardChromaticError(
                "strength must be 0..100."
            )

        if not isinstance(
            self.locked,
            bool,
        ):
            raise DashboardChromaticError(
                "locked must be boolean."
            )

        matched = _require_colour(
            self.matched_accent,
            field_name="matched_accent",
            allow_empty=True,
        )

        if matched != self.matched_accent:
            raise DashboardChromaticError(
                "matched_accent must be normalised."
            )

        palette = _normalise_palette(
            self.matched_palette
        )

        if tuple(
            self.matched_palette
        ) != palette:
            raise DashboardChromaticError(
                "matched_palette must be normalised."
            )

    @classmethod
    def build(
        cls,
        *,
        enabled=False,
        mode=CHROMATIC_MODE_BACKGROUND,
        effect_style=DEFAULT_EFFECT_STYLE,
        manual_accent=DEFAULT_MANUAL_ACCENT,
        strength=DEFAULT_STRENGTH,
        locked=False,
        matched_accent="",
        matched_palette=(),
    ):
        palette = _normalise_palette(
            matched_palette
        )

        matched = normalise_hex_colour(
            matched_accent
        )

        if not matched and palette:
            matched = palette[0]

        manual = normalise_hex_colour(
            manual_accent,
            fallback=DEFAULT_MANUAL_ACCENT,
        )

        return cls(
            enabled=_coerce_bool(
                enabled
            ),
            mode=_normalise_mode(
                mode
            ),
            effect_style=_normalise_effect_style(
                effect_style
            ),
            manual_accent=manual,
            strength=_clamp_strength(
                strength
            ),
            locked=_coerce_bool(
                locked
            ),
            matched_accent=matched,
            matched_palette=palette,
        )


class DashboardChromaticPreferencesStore:

    def __init__(
        self,
        settings=None,
    ):
        self.settings = (
            settings
            if settings is not None
            else QSettings(
                "0337am",
                "Presence",
            )
        )

    @staticmethod
    def _key(name):
        return (
            CHROMATIC_SETTINGS_PREFIX
            + "/"
            + str(name)
        )

    def load(self):
        return (
            DashboardChromaticPreferences
            .build(
                enabled=self.settings.value(
                    self._key(
                        "enabled"
                    ),
                    False,
                ),
                mode=self.settings.value(
                    self._key(
                        "mode"
                    ),
                    CHROMATIC_MODE_BACKGROUND,
                ),
                effect_style=self.settings.value(
                    self._key(
                        "effect_style"
                    ),
                    DEFAULT_EFFECT_STYLE,
                ),
                manual_accent=self.settings.value(
                    self._key(
                        "manual_accent"
                    ),
                    DEFAULT_MANUAL_ACCENT,
                ),
                strength=self.settings.value(
                    self._key(
                        "strength"
                    ),
                    DEFAULT_STRENGTH,
                ),
                locked=self.settings.value(
                    self._key(
                        "locked"
                    ),
                    False,
                ),
                matched_accent=self.settings.value(
                    self._key(
                        "matched_accent"
                    ),
                    "",
                ),
                matched_palette=self.settings.value(
                    self._key(
                        "palette"
                    ),
                    "[]",
                ),
            )
        )

    def save(
        self,
        preferences,
    ):
        if not isinstance(
            preferences,
            DashboardChromaticPreferences,
        ):
            raise TypeError(
                "preferences must be "
                "DashboardChromaticPreferences."
            )

        values = {
            "enabled":
                preferences.enabled,

            "mode":
                preferences.mode,

            "manual_accent":
                preferences.manual_accent,

            "strength":
                preferences.strength,

            "locked":
                preferences.locked,

            "matched_accent":
                preferences.matched_accent,

            "palette":
                json.dumps(
                    list(
                        preferences.matched_palette
                    ),
                    separators=(
                        ",",
                        ":",
                    ),
                ),
        }

        for name, value in values.items():
            self.settings.setValue(
                self._key(
                    name
                ),
                value,
            )

        effect_key = self._key(
            "effect_style"
        )

        if (
            preferences.effect_style
            == DEFAULT_EFFECT_STYLE
        ):
            self.settings.remove(
                effect_key
            )

        else:
            self.settings.setValue(
                effect_key,
                preferences.effect_style,
            )

        self.settings.sync()


def _rgb_tuple(colour):
    normalised = _require_colour(
        colour,
        field_name="colour",
    )

    value = QColor(
        normalised
    )

    return (
        value.red(),
        value.green(),
        value.blue(),
    )


def relative_luminance(colour):
    red, green, blue = _rgb_tuple(
        colour
    )

    def linear(value):
        value = value / 255.0

        if value <= 0.04045:
            return value / 12.92

        return (
            (
                value
                + 0.055
            )
            / 1.055
        ) ** 2.4

    return (
        0.2126 * linear(red)
        + 0.7152 * linear(green)
        + 0.0722 * linear(blue)
    )


def contrast_ratio(
    first,
    second,
):
    first_value = relative_luminance(
        first
    )

    second_value = relative_luminance(
        second
    )

    lighter = max(
        first_value,
        second_value,
    )

    darker = min(
        first_value,
        second_value,
    )

    return (
        lighter
        + 0.05
    ) / (
        darker
        + 0.05
    )


def _colour_distance(
    first,
    second,
):
    first_rgb = _rgb_tuple(
        first
    )

    second_rgb = _rgb_tuple(
        second
    )

    return math.sqrt(
        sum(
            (
                (left - right)
                / 255.0
            ) ** 2
            for left, right in zip(
                first_rgb,
                second_rgb,
            )
        )
    )


def _hue_distance(
    first,
    second,
):
    first_colour = QColor(
        _require_colour(
            first,
            field_name="first",
        )
    )

    second_colour = QColor(
        _require_colour(
            second,
            field_name="second",
        )
    )

    first_hue = first_colour.hsvHueF()
    second_hue = second_colour.hsvHueF()

    if first_hue < 0 or second_hue < 0:
        return 0.0

    difference = abs(
        first_hue
        - second_hue
    )

    return min(
        difference,
        1.0 - difference,
    )


def _candidate_is_distinct(
    candidate,
    selected,
):
    for existing in selected:
        if (
            _hue_distance(
                candidate,
                existing,
            )
            < 0.055
            and _colour_distance(
                candidate,
                existing,
            )
            < 0.22
        ):
            return False

    return True


def extract_dashboard_palette(image):
    if (
        not isinstance(
            image,
            QImage,
        )
        or image.isNull()
        or image.width() <= 0
        or image.height() <= 0
    ):
        return (
            DashboardChromaticPalette()
        )

    width = image.width()
    height = image.height()

    step = max(
        1,
        math.ceil(
            max(
                width,
                height,
            )
            / MAX_SAMPLE_AXIS
        ),
    )

    buckets = {}

    for y in range(
        0,
        height,
        step,
    ):
        for x in range(
            0,
            width,
            step,
        ):
            colour = image.pixelColor(
                x,
                y,
            )

            if (
                colour.alpha()
                < _MIN_SAMPLE_ALPHA
            ):
                continue

            hue = colour.hsvHueF()
            saturation = colour.hsvSaturationF()
            value = colour.valueF()

            if (
                hue < 0
                or saturation
                < _MIN_SAMPLE_SATURATION
                or value
                < _MIN_SAMPLE_VALUE
            ):
                continue

            if (
                value > 0.97
                and saturation < 0.35
            ):
                continue

            key = (
                int(
                    hue * 24
                ) % 24,
                min(
                    3,
                    int(
                        saturation * 4
                    ),
                ),
                min(
                    3,
                    int(
                        value * 4
                    ),
                ),
            )

            entry = buckets.setdefault(
                key,
                {
                    "count": 0,
                    "red": 0,
                    "green": 0,
                    "blue": 0,
                    "quality": 0.0,
                },
            )

            entry["count"] += 1
            entry["red"] += colour.red()
            entry["green"] += colour.green()
            entry["blue"] += colour.blue()

            chroma_quality = (
                0.35
                + saturation * 1.35
            )

            brightness_quality = (
                0.72
                + 0.28
                * (
                    1.0
                    - abs(
                        value
                        - 0.68
                    )
                )
            )

            entry["quality"] += (
                chroma_quality
                * brightness_quality
            )

    ranked = []

    for entry in buckets.values():
        count = int(
            entry["count"]
        )

        if count <= 0:
            continue

        colour = QColor(
            round(
                entry["red"]
                / count
            ),
            round(
                entry["green"]
                / count
            ),
            round(
                entry["blue"]
                / count
            ),
        ).name(
            QColor.NameFormat.HexRgb
        ).lower()

        score = (
            float(
                entry["quality"]
            )
            * math.sqrt(
                count
            )
        )

        ranked.append(
            (
                score,
                count,
                colour,
            )
        )

    ranked.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            item[2],
        )
    )

    selected = []

    for _, _, colour in ranked:
        if not _candidate_is_distinct(
            colour,
            selected,
        ):
            continue

        selected.append(
            colour
        )

        if (
            len(selected)
            >= MAX_PALETTE_COLOURS
        ):
            break

    return (
        DashboardChromaticPalette
        .build(
            selected
        )
    )


def extract_dashboard_palette_from_path(
    image_path,
):
    raw = str(
        image_path
        or ""
    ).strip()

    if not raw:
        return (
            DashboardChromaticPalette()
        )

    path = Path(
        raw
    )

    if not path.is_file():
        return (
            DashboardChromaticPalette()
        )

    return extract_dashboard_palette(
        QImage(
            str(path)
        )
    )


def blend_colours(
    base,
    overlay,
    amount,
):
    base_rgb = _rgb_tuple(
        base
    )

    overlay_rgb = _rgb_tuple(
        overlay
    )

    try:
        ratio = float(
            amount
        )

    except (
        TypeError,
        ValueError,
    ):
        ratio = 0.0

    ratio = max(
        0.0,
        min(
            1.0,
            ratio,
        ),
    )

    values = [
        round(
            left
            + (
                right
                - left
            )
            * ratio
        )
        for left, right in zip(
            base_rgb,
            overlay_rgb,
        )
    ]

    return QColor(
        *values
    ).name(
        QColor.NameFormat.HexRgb
    ).lower()


def apply_accent_strength(
    source_accent,
    base_accent,
    strength,
):
    source = _require_colour(
        source_accent,
        field_name="source_accent",
    )

    base = _require_colour(
        base_accent,
        field_name="base_accent",
    )

    return blend_colours(
        base,
        source,
        (
            _clamp_strength(
                strength
            )
            / 100.0
        ),
    )


def sanitize_dashboard_accent(
    accent,
    background,
    *,
    minimum_contrast=_TARGET_ACCENT_CONTRAST,
):
    source = _require_colour(
        accent,
        field_name="accent",
    )

    backdrop = _require_colour(
        background,
        field_name="background",
    )

    try:
        minimum = float(
            minimum_contrast
        )

    except (
        TypeError,
        ValueError,
    ):
        minimum = _TARGET_ACCENT_CONTRAST

    minimum = max(
        1.0,
        min(
            21.0,
            minimum,
        ),
    )

    if (
        contrast_ratio(
            source,
            backdrop,
        )
        >= minimum
    ):
        return source

    colour = QColor(
        source
    )

    hue = colour.hslHueF()
    saturation = colour.hslSaturationF()
    lightness = colour.lightnessF()

    backdrop_is_dark = (
        relative_luminance(
            backdrop
        )
        < 0.42
    )

    target_lightness = (
        0.96
        if backdrop_is_dark
        else 0.04
    )

    for step in range(
        1,
        81,
    ):
        progress = step / 80.0

        candidate_lightness = (
            lightness
            + (
                target_lightness
                - lightness
            )
            * progress
        )

        if hue >= 0:
            candidate = QColor.fromHslF(
                hue,
                max(
                    0.28,
                    saturation,
                ),
                candidate_lightness,
                1.0,
            )

        else:
            gray = round(
                candidate_lightness
                * 255
            )

            candidate = QColor(
                gray,
                gray,
                gray,
            )

        candidate_hex = candidate.name(
            QColor.NameFormat.HexRgb
        ).lower()

        if (
            contrast_ratio(
                candidate_hex,
                backdrop,
            )
            >= minimum
        ):
            return candidate_hex

    black = "#000000"
    white = "#ffffff"

    return (
        black
        if contrast_ratio(
            black,
            backdrop,
        )
        >= contrast_ratio(
            white,
            backdrop,
        )
        else white
    )


def resolve_dashboard_accent(
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
        DashboardChromaticPreferences,
    ):
        raise TypeError(
            "preferences must be "
            "DashboardChromaticPreferences."
        )

    base_accent = normalise_hex_colour(
        base_theme.get(
            "accent",
            DEFAULT_MANUAL_ACCENT,
        ),
        fallback=DEFAULT_MANUAL_ACCENT,
    )

    if not preferences.enabled:
        return base_accent

    if (
        preferences.mode
        == CHROMATIC_MODE_MANUAL
    ):
        source = preferences.manual_accent

    else:
        source = (
            preferences.matched_accent
            or base_accent
        )

    blended = apply_accent_strength(
        source,
        base_accent,
        preferences.strength,
    )

    background = normalise_hex_colour(
        base_theme.get(
            "background",
            "#140812",
        ),
        fallback="#140812",
    )

    return sanitize_dashboard_accent(
        blended,
        background,
    )



def _derive_effect_colour(
    colour,
    hue_delta,
):
    source = QColor(
        _require_colour(
            colour,
            field_name="colour",
        )
    )

    hue = source.hsvHueF()

    if hue < 0:
        hue = 0.0

    saturation = max(
        0.55,
        source.hsvSaturationF(),
    )

    value = max(
        0.72,
        source.valueF(),
    )

    derived = QColor.fromHsvF(
        (
            hue
            + float(
                hue_delta
            )
        )
        % 1.0,
        min(
            1.0,
            saturation,
        ),
        min(
            1.0,
            value,
        ),
        1.0,
    )

    return derived.name(
        QColor.NameFormat.HexRgb
    ).lower()


def resolve_dashboard_effect_colours(
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
        DashboardChromaticPreferences,
    ):
        raise TypeError(
            "preferences must be "
            "DashboardChromaticPreferences."
        )

    base_accent = normalise_hex_colour(
        base_theme.get(
            "accent",
            DEFAULT_MANUAL_ACCENT,
        ),
        fallback=DEFAULT_MANUAL_ACCENT,
    )

    background = normalise_hex_colour(
        base_theme.get(
            "background",
            "#140812",
        ),
        fallback="#140812",
    )

    if (
        preferences.mode
        == CHROMATIC_MODE_MANUAL
    ):
        source_colours = [
            preferences.manual_accent,
        ]

    else:
        source_colours = list(
            preferences.matched_palette
        )

        if (
            not source_colours
            and preferences.matched_accent
        ):
            source_colours.append(
                preferences.matched_accent
            )

        if not source_colours:
            source_colours.append(
                base_accent
            )

    colours = []

    for raw in source_colours:
        value = normalise_hex_colour(
            raw
        )

        if not value:
            continue

        value = sanitize_dashboard_accent(
            value,
            background,
        )

        if value not in colours:
            colours.append(
                value
            )

    if not colours:
        colours.append(
            sanitize_dashboard_accent(
                base_accent,
                background,
            )
        )

    if (
        preferences.effect_style
        == CHROMATIC_EFFECT_PRISM
    ):
        required = 3

    elif (
        preferences.effect_style
        == CHROMATIC_EFFECT_GRADIENT
    ):
        required = 2

    else:
        required = 1

    offsets = (
        0.11,
        0.31,
        0.53,
        0.71,
    )

    index = 0

    while (
        len(
            colours
        )
        < required
        and index < 16
    ):
        derived = _derive_effect_colour(
            colours[0],
            offsets[
                index
                % len(
                    offsets
                )
            ],
        )

        index += 1

        derived = sanitize_dashboard_accent(
            derived,
            background,
        )

        if derived not in colours:
            colours.append(
                derived
            )

    return tuple(
        colours[
            :required
        ]
    )


def build_dashboard_chromatic_theme(
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
        DashboardChromaticPreferences,
    ):
        raise TypeError(
            "preferences must be "
            "DashboardChromaticPreferences."
        )

    result = dict(
        base_theme
    )

    if not preferences.enabled:
        return result

    accent = resolve_dashboard_accent(
        result,
        preferences,
    )

    result["accent"] = accent

    tint_strength = (
        preferences.strength
        / 100.0
    )

    card = normalise_hex_colour(
        result.get(
            "card",
            "#352747",
        ),
        fallback="#352747",
    )

    card_alt = normalise_hex_colour(
        result.get(
            "card_alt",
            "#3e2e54",
        ),
        fallback="#3e2e54",
    )

    border = normalise_hex_colour(
        result.get(
            "border",
            "#5c4777",
        ),
        fallback="#5c4777",
    )

    result["card"] = blend_colours(
        card,
        accent,
        0.06 * tint_strength,
    )

    result["card_alt"] = blend_colours(
        card_alt,
        accent,
        0.12 * tint_strength,
    )

    result["border"] = blend_colours(
        border,
        accent,
        0.34 * tint_strength,
    )

    return result


def update_matched_palette(
    preferences,
    palette,
    *,
    force=False,
):
    if not isinstance(
        preferences,
        DashboardChromaticPreferences,
    ):
        raise TypeError(
            "preferences must be "
            "DashboardChromaticPreferences."
        )

    if not isinstance(
        palette,
        DashboardChromaticPalette,
    ):
        raise TypeError(
            "palette must be "
            "DashboardChromaticPalette."
        )

    if (
        preferences.locked
        and not bool(
            force
        )
    ):
        return preferences

    return replace(
        preferences,
        matched_accent=palette.primary,
        matched_palette=palette.colours,
    )
