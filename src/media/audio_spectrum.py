from __future__ import annotations

import math

from functools import lru_cache


SPECTRUM_BAND_FREQUENCIES = (
    63,
    125,
    250,
    500,
    1000,
    2000,
    4000,
    8000,
)

SPECTRUM_BAND_RANGES = (
    (40.0, 90.0),
    (90.0, 180.0),
    (180.0, 350.0),
    (350.0, 700.0),
    (700.0, 1400.0),
    (1400.0, 2800.0),
    (2800.0, 5600.0),
    (5600.0, 11000.0),
)

SPECTRUM_BAND_GAIN_DB = (
    0.0,
    0.0,
    0.5,
    1.0,
    1.5,
    2.0,
    2.5,
    4.0,
)

SPECTRUM_GLYPHS = (
    "▁",
    "▂",
    "▃",
    "▄",
    "▅",
    "▆",
    "▇",
    "█",
)

DEFAULT_ATTACK = 0.72
DEFAULT_RELEASE = 0.24

DEFAULT_FLOOR_DB = -60.0
DEFAULT_REFERENCE_DB = -12.0

DEFAULT_ADAPTIVE_HEADROOM_DB = 7.0
DEFAULT_ADAPTIVE_RANGE_DB = 42.0
DEFAULT_ADAPTIVE_ATTACK = 0.65
DEFAULT_ADAPTIVE_RELEASE = 0.025
DEFAULT_MINIMUM_REFERENCE_DB = -36.0
DEFAULT_MAXIMUM_REFERENCE_DB = 6.0

MAX_ANALYSIS_SAMPLES = 1024
MIN_ANALYSIS_SAMPLES = 64

_MIN_AMPLITUDE = 1.0e-12

_ZERO_LEVELS = (
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
)


def _validated_coefficient(
    value,
    name: str,
) -> float:
    if isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"{name} must be a finite number between 0 and 1."
        )

    try:
        checked = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            f"{name} must be a finite number between 0 and 1."
        ) from error

    if (
        not math.isfinite(
            checked
        )
        or checked <= 0.0
        or checked > 1.0
    ):
        raise ValueError(
            f"{name} must be a finite number between 0 and 1."
        )

    return checked


def _validated_positive(
    value,
    name: str,
) -> float:
    if isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"{name} must be a positive finite number."
        )

    try:
        checked = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            f"{name} must be a positive finite number."
        ) from error

    if (
        not math.isfinite(
            checked
        )
        or checked <= 0.0
    ):
        raise ValueError(
            f"{name} must be a positive finite number."
        )

    return checked


def _validated_db(
    value,
    name: str,
) -> float:
    if isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"{name} must be finite."
        )

    try:
        checked = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            f"{name} must be finite."
        ) from error

    if not math.isfinite(
        checked
    ):
        raise ValueError(
            f"{name} must be finite."
        )

    return checked


def _validated_sample_rate(
    sample_rate,
) -> float:
    if isinstance(
        sample_rate,
        bool,
    ):
        raise ValueError(
            "sample_rate must be a positive finite number."
        )

    try:
        checked = float(
            sample_rate
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            "sample_rate must be a positive finite number."
        ) from error

    if (
        not math.isfinite(
            checked
        )
        or checked <= 0.0
    ):
        raise ValueError(
            "sample_rate must be a positive finite number."
        )

    return checked


def _validated_samples(
    samples,
) -> tuple[float, ...]:
    if samples is None:
        raise ValueError(
            "samples are required."
        )

    try:
        values = tuple(
            float(
                value
            )
            for value in samples
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            "samples must contain finite numeric values."
        ) from error

    if any(
        not math.isfinite(
            value
        )
        for value in values
    ):
        raise ValueError(
            "samples must contain finite numeric values."
        )

    return values


def _analysis_size(
    sample_count: int,
) -> int:
    limited = min(
        int(
            sample_count
        ),
        MAX_ANALYSIS_SAMPLES,
    )

    if limited < MIN_ANALYSIS_SAMPLES:
        return 0

    return 1 << (
        limited.bit_length()
        - 1
    )


@lru_cache(
    maxsize=8,
)
def _hann_window(
    size: int,
) -> tuple[float, ...]:
    if size <= 1:
        return (
            1.0,
        ) * max(
            1,
            size,
        )

    denominator = float(
        size - 1
    )

    return tuple(
        0.5
        - 0.5
        * math.cos(
            (
                2.0
                * math.pi
                * index
            )
            / denominator
        )
        for index in range(
            size
        )
    )


@lru_cache(
    maxsize=8,
)
def _bit_reversed_indices(
    size: int,
) -> tuple[int, ...]:
    bits = (
        size.bit_length()
        - 1
    )

    indices = []

    for value in range(
        size
    ):
        source = value
        reversed_value = 0

        for _ in range(
            bits
        ):
            reversed_value = (
                reversed_value << 1
            ) | (
                source & 1
            )

            source >>= 1

        indices.append(
            reversed_value
        )

    return tuple(
        indices
    )


@lru_cache(
    maxsize=32,
)
def _stage_twiddles(
    size: int,
) -> tuple[complex, ...]:
    half = (
        size // 2
    )

    return tuple(
        complex(
            math.cos(
                (
                    -2.0
                    * math.pi
                    * index
                )
                / size
            ),
            math.sin(
                (
                    -2.0
                    * math.pi
                    * index
                )
                / size
            ),
        )
        for index in range(
            half
        )
    )


def _fft_real(
    samples,
) -> list[complex]:
    size = len(
        samples
    )

    if (
        size < 1
        or size & (
            size - 1
        )
    ):
        raise ValueError(
            "FFT sample size must be a positive power of two."
        )

    reversed_indices = (
        _bit_reversed_indices(
            size
        )
    )

    data = [
        complex(
            samples[index],
            0.0,
        )
        for index in reversed_indices
    ]

    stage_size = 2

    while stage_size <= size:
        half = (
            stage_size // 2
        )

        twiddles = (
            _stage_twiddles(
                stage_size
            )
        )

        for start in range(
            0,
            size,
            stage_size,
        ):
            for offset in range(
                half
            ):
                left_index = (
                    start
                    + offset
                )

                right_index = (
                    left_index
                    + half
                )

                left = data[
                    left_index
                ]

                right = (
                    data[
                        right_index
                    ]
                    * twiddles[
                        offset
                    ]
                )

                data[
                    left_index
                ] = (
                    left
                    + right
                )

                data[
                    right_index
                ] = (
                    left
                    - right
                )

        stage_size *= 2

    return data


def _band_amplitudes(
    samples,
    sample_rate: float,
) -> tuple[float, ...]:
    size = len(
        samples
    )

    window = (
        _hann_window(
            size
        )
    )

    windowed = [
        samples[index]
        * window[index]
        for index in range(
            size
        )
    ]

    spectrum = (
        _fft_real(
            windowed
        )
    )

    window_sum = sum(
        window
    )

    if window_sum <= 0.0:
        return _ZERO_LEVELS

    amplitude_scale = (
        2.0
        / window_sum
    )

    nyquist_bin = (
        size // 2
    )

    amplitudes = []

    for low_hz, high_hz in (
        SPECTRUM_BAND_RANGES
    ):
        start_bin = max(
            1,
            math.ceil(
                (
                    low_hz
                    * size
                )
                / sample_rate
            ),
        )

        end_bin = min(
            nyquist_bin + 1,
            math.ceil(
                (
                    high_hz
                    * size
                )
                / sample_rate
            ),
        )

        if end_bin <= start_bin:
            amplitudes.append(
                0.0
            )
            continue

        power = 0.0

        for bin_index in range(
            start_bin,
            end_bin,
        ):
            value = spectrum[
                bin_index
            ]

            power += (
                value.real
                * value.real
                + value.imag
                * value.imag
            )

        if power <= 0.0:
            amplitudes.append(
                0.0
            )
            continue

        amplitudes.append(
            amplitude_scale
            * math.sqrt(
                power
            )
        )

    return tuple(
        amplitudes
    )


class SpectrumAnalyzer:
    def __init__(
        self,
        *,
        attack: float = DEFAULT_ATTACK,
        release: float = DEFAULT_RELEASE,
        floor_db: float = DEFAULT_FLOOR_DB,
        reference_db: float = DEFAULT_REFERENCE_DB,
        adaptive_headroom_db: float = DEFAULT_ADAPTIVE_HEADROOM_DB,
        adaptive_range_db: float = DEFAULT_ADAPTIVE_RANGE_DB,
        adaptive_attack: float = DEFAULT_ADAPTIVE_ATTACK,
        adaptive_release: float = DEFAULT_ADAPTIVE_RELEASE,
        minimum_reference_db: float = DEFAULT_MINIMUM_REFERENCE_DB,
        maximum_reference_db: float = DEFAULT_MAXIMUM_REFERENCE_DB,
    ):
        self.attack = (
            _validated_coefficient(
                attack,
                "attack",
            )
        )

        self.release = (
            _validated_coefficient(
                release,
                "release",
            )
        )

        self.floor_db = (
            _validated_db(
                floor_db,
                "floor_db",
            )
        )

        self.reference_db = (
            _validated_db(
                reference_db,
                "reference_db",
            )
        )

        if (
            self.reference_db
            <= self.floor_db
        ):
            raise ValueError(
                "reference_db must be greater than floor_db."
            )

        self.adaptive_headroom_db = (
            _validated_positive(
                adaptive_headroom_db,
                "adaptive_headroom_db",
            )
        )

        self.adaptive_range_db = (
            _validated_positive(
                adaptive_range_db,
                "adaptive_range_db",
            )
        )

        self.adaptive_attack = (
            _validated_coefficient(
                adaptive_attack,
                "adaptive_attack",
            )
        )

        self.adaptive_release = (
            _validated_coefficient(
                adaptive_release,
                "adaptive_release",
            )
        )

        self.minimum_reference_db = (
            _validated_db(
                minimum_reference_db,
                "minimum_reference_db",
            )
        )

        self.maximum_reference_db = (
            _validated_db(
                maximum_reference_db,
                "maximum_reference_db",
            )
        )

        if (
            self.maximum_reference_db
            <= self.minimum_reference_db
        ):
            raise ValueError(
                "maximum_reference_db must be greater than minimum_reference_db."
            )

        self._adaptive_minimum_reference_db = max(
            self.minimum_reference_db,
            min(
                self.maximum_reference_db,
                self.reference_db,
            ),
        )

        self._levels = list(
            _ZERO_LEVELS
        )

        self._adaptive_reference_db = (
            max(
                self._adaptive_minimum_reference_db,
                min(
                    self.maximum_reference_db,
                    self.reference_db,
                ),
            )
        )

    @property
    def levels(
        self,
    ) -> tuple[float, ...]:
        return tuple(
            self._levels
        )

    @property
    def adaptive_reference_db(
        self,
    ) -> float:
        return float(
            self._adaptive_reference_db
        )

    def reset(
        self,
    ) -> None:
        self._levels = list(
            _ZERO_LEVELS
        )

        self._adaptive_reference_db = (
            max(
                self._adaptive_minimum_reference_db,
                min(
                    self.maximum_reference_db,
                    self.reference_db,
                ),
            )
        )

    def analyze(
        self,
        samples,
        sample_rate,
    ) -> tuple[float, ...]:
        checked_rate = (
            _validated_sample_rate(
                sample_rate
            )
        )

        checked_samples = (
            _validated_samples(
                samples
            )
        )

        size = (
            _analysis_size(
                len(
                    checked_samples
                )
            )
        )

        if size == 0:
            return self._smooth(
                _ZERO_LEVELS
            )

        selected = checked_samples[
            -size:
        ]

        amplitudes = (
            _band_amplitudes(
                selected,
                checked_rate,
            )
        )

        band_db = []

        for amplitude, gain_db in zip(
            amplitudes,
            SPECTRUM_BAND_GAIN_DB,
        ):
            if amplitude <= _MIN_AMPLITUDE:
                band_db.append(
                    None
                )
                continue

            db = (
                20.0
                * math.log10(
                    max(
                        amplitude,
                        _MIN_AMPLITUDE,
                    )
                )
                + gain_db
            )

            band_db.append(
                db
            )

        audible_db = [
            value
            for value in band_db
            if value is not None
        ]

        if not audible_db:
            return self._smooth(
                _ZERO_LEVELS
            )

        frame_peak_db = max(
            audible_db
        )

        target_reference_db = (
            frame_peak_db
            + self.adaptive_headroom_db
        )

        target_reference_db = max(
            self._adaptive_minimum_reference_db,
            min(
                self.maximum_reference_db,
                target_reference_db,
            ),
        )

        coefficient = (
            self.adaptive_attack
            if (
                target_reference_db
                >= self._adaptive_reference_db
            )
            else self.adaptive_release
        )

        self._adaptive_reference_db = (
            self._adaptive_reference_db
            + (
                target_reference_db
                - self._adaptive_reference_db
            )
            * coefficient
        )

        effective_reference_db = (
            self._adaptive_reference_db
        )

        effective_floor_db = max(
            self.floor_db,
            (
                effective_reference_db
                - self.adaptive_range_db
            ),
        )

        dynamic_range = (
            effective_reference_db
            - effective_floor_db
        )

        if dynamic_range <= 0.0:
            return self._smooth(
                _ZERO_LEVELS
            )

        targets = []

        for db in band_db:
            if db is None:
                level = 0.0

            else:
                level = (
                    (
                        db
                        - effective_floor_db
                    )
                    / dynamic_range
                )

                level = max(
                    0.0,
                    min(
                        1.0,
                        level,
                    ),
                )

            targets.append(
                level
            )

        return self._smooth(
            tuple(
                targets
            )
        )

    def _smooth(
        self,
        targets,
    ) -> tuple[float, ...]:
        updated = []

        for previous, target in zip(
            self._levels,
            targets,
        ):
            coefficient = (
                self.attack
                if target >= previous
                else self.release
            )

            value = (
                previous
                + (
                    target
                    - previous
                )
                * coefficient
            )

            value = max(
                0.0,
                min(
                    1.0,
                    value,
                ),
            )

            updated.append(
                value
            )

        self._levels = updated

        return tuple(
            updated
        )


def spectrum_levels_to_text(
    levels,
) -> str:
    try:
        checked = tuple(
            float(
                value
            )
            for value in levels
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            "Spectrum levels must contain numeric values."
        ) from error

    if len(
        checked
    ) != len(
        SPECTRUM_BAND_FREQUENCIES
    ):
        raise ValueError(
            "Spectrum levels must contain exactly eight values."
        )

    characters = []

    maximum_index = (
        len(
            SPECTRUM_GLYPHS
        )
        - 1
    )

    for value in checked:
        if not math.isfinite(
            value
        ):
            raise ValueError(
                "Spectrum levels must be finite."
            )

        bounded = max(
            0.0,
            min(
                1.0,
                value,
            ),
        )

        glyph_index = int(
            bounded
            * maximum_index
            + 0.5
        )

        characters.append(
            SPECTRUM_GLYPHS[
                glyph_index
            ]
        )

    return "".join(
        characters
    )