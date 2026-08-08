from __future__ import annotations

from dataclasses import dataclass
import math
import time
from collections.abc import Callable
from numbers import Real


DEFAULT_SEEK_THRESHOLD_SECONDS = 2.0
DEFAULT_BACKWARD_SEEK_THRESHOLD_SECONDS = 1.5
DEFAULT_STALE_TOLERANCE_SECONDS = 0.75
DEFAULT_MAX_EXTRAPOLATION_SECONDS = 5.0


@dataclass(
    frozen=True,
    slots=True,
)
class PlaybackPresentationState:
    position_seconds: float
    duration_seconds: float
    playing: bool


def _checked_seconds(
    value,
    name: str,
) -> float:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            Real,
        )
    ):
        raise TypeError(
            name
            + " must be a real number"
        )

    checked = float(
        value
    )

    if not math.isfinite(
        checked
    ):
        raise ValueError(
            name
            + " must be finite"
        )

    return max(
        0.0,
        checked,
    )


def _checked_identity(
    identity,
) -> tuple[str, ...]:
    if not isinstance(
        identity,
        tuple,
    ):
        raise TypeError(
            "identity must be a tuple"
        )

    if not all(
        isinstance(
            item,
            str,
        )
        for item in identity
    ):
        raise TypeError(
            (
                "identity entries must "
                "be strings"
            )
        )

    return tuple(
        item.strip()
        for item in identity
    )


def format_playback_time(
    seconds,
) -> str:
    checked = _checked_seconds(
        seconds,
        "seconds",
    )

    whole = int(
        checked
    )

    hours, remainder = divmod(
        whole,
        3600,
    )

    minutes, seconds_part = divmod(
        remainder,
        60,
    )

    if hours > 0:
        return (
            f"{hours}:"
            f"{minutes:02d}:"
            f"{seconds_part:02d}"
        )

    return (
        f"{minutes}:"
        f"{seconds_part:02d}"
    )


class PlaybackPresentationClock:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        seek_threshold_seconds: float = (
            DEFAULT_SEEK_THRESHOLD_SECONDS
        ),
        backward_seek_threshold_seconds: float = (
            DEFAULT_BACKWARD_SEEK_THRESHOLD_SECONDS
        ),
        stale_tolerance_seconds: float = (
            DEFAULT_STALE_TOLERANCE_SECONDS
        ),
        max_extrapolation_seconds: float = (
            DEFAULT_MAX_EXTRAPOLATION_SECONDS
        ),
    ) -> None:
        if not callable(
            clock
        ):
            raise TypeError(
                "clock must be callable"
            )

        self._clock = clock

        self._seek_threshold_seconds = (
            _checked_seconds(
                seek_threshold_seconds,
                "seek_threshold_seconds",
            )
        )

        self._backward_seek_threshold_seconds = (
            _checked_seconds(
                backward_seek_threshold_seconds,
                (
                    "backward_seek_threshold_seconds"
                ),
            )
        )

        self._stale_tolerance_seconds = (
            _checked_seconds(
                stale_tolerance_seconds,
                "stale_tolerance_seconds",
            )
        )

        self._max_extrapolation_seconds = (
            _checked_seconds(
                max_extrapolation_seconds,
                "max_extrapolation_seconds",
            )
        )

        if (
            self._seek_threshold_seconds
            <= 0.0
        ):
            raise ValueError(
                (
                    "seek_threshold_seconds must "
                    "be greater than zero"
                )
            )

        if (
            self._backward_seek_threshold_seconds
            <= 0.0
        ):
            raise ValueError(
                (
                    "backward_seek_threshold_seconds "
                    "must be greater than zero"
                )
            )

        if (
            self._max_extrapolation_seconds
            <= 0.0
        ):
            raise ValueError(
                (
                    "max_extrapolation_seconds must "
                    "be greater than zero"
                )
            )

        self.clear()

    def clear(
        self,
    ) -> None:
        self._identity = None
        self._anchor_position = 0.0
        self._anchor_time = None
        self._duration_seconds = 0.0
        self._playing = False
        self._last_authoritative_position = None

    @property
    def active(
        self,
    ) -> bool:
        return (
            self._anchor_time
            is not None
        )

    def _now(
        self,
    ) -> float:
        try:
            value = float(
                self._clock()
            )

        except Exception as error:
            raise RuntimeError(
                (
                    "Playback presentation clock "
                    "could not read monotonic time."
                )
            ) from error

        if not math.isfinite(
            value
        ):
            raise RuntimeError(
                (
                    "Playback presentation clock "
                    "returned invalid time."
                )
            )

        return value

    @staticmethod
    def _clamp_position(
        position_seconds: float,
        duration_seconds: float,
    ) -> float:
        position = max(
            0.0,
            position_seconds,
        )

        if duration_seconds > 0.0:
            position = min(
                position,
                duration_seconds,
            )

        return position

    def _position_at(
        self,
        now: float,
    ) -> float:
        position = (
            self._anchor_position
        )

        if (
            self._playing
            and self._anchor_time
            is not None
        ):
            elapsed = max(
                0.0,
                now
                - self._anchor_time,
            )

            position += elapsed

        if (
            self._playing
            and self._last_authoritative_position
            is not None
        ):
            maximum_from_snapshot = (
                self._last_authoritative_position
                + self._max_extrapolation_seconds
            )

            position = min(
                position,
                maximum_from_snapshot,
            )

        return self._clamp_position(
            position,
            self._duration_seconds,
        )

    def _reanchor(
        self,
        position_seconds: float,
        duration_seconds: float,
        playing: bool,
        identity: tuple[str, ...],
        now: float,
    ) -> None:
        self._identity = identity
        self._anchor_position = (
            self._clamp_position(
                position_seconds,
                duration_seconds,
            )
        )
        self._anchor_time = now
        self._duration_seconds = (
            duration_seconds
        )
        self._playing = playing
        self._last_authoritative_position = (
            self._anchor_position
        )

    def observe(
        self,
        *,
        position_seconds,
        duration_seconds,
        playing: bool,
        identity,
    ) -> None:
        position = _checked_seconds(
            position_seconds,
            "position_seconds",
        )

        duration = _checked_seconds(
            duration_seconds,
            "duration_seconds",
        )

        if not isinstance(
            playing,
            bool,
        ):
            raise TypeError(
                "playing must be a boolean"
            )

        checked_identity = (
            _checked_identity(
                identity
            )
        )

        position = (
            self._clamp_position(
                position,
                duration,
            )
        )

        now = self._now()

        if (
            not self.active
            or checked_identity
            != self._identity
            or playing
            != self._playing
        ):
            self._reanchor(
                position,
                duration,
                playing,
                checked_identity,
                now,
            )
            return

        self._duration_seconds = (
            duration
        )

        if not playing:
            self._reanchor(
                position,
                duration,
                False,
                checked_identity,
                now,
            )
            return

        predicted = (
            self._position_at(
                now
            )
        )

        previous_authoritative = (
            self._last_authoritative_position
        )

        backward_seek = (
            previous_authoritative
            is not None
            and position
            < (
                previous_authoritative
                - self._backward_seek_threshold_seconds
            )
        )

        forward_seek = (
            position
            > (
                predicted
                + self._seek_threshold_seconds
            )
        )

        if (
            backward_seek
            or forward_seek
        ):
            self._reanchor(
                position,
                duration,
                True,
                checked_identity,
                now,
            )
            return

        if (
            previous_authoritative
            is None
            or position
            > previous_authoritative
        ):
            self._last_authoritative_position = (
                position
            )

        snapshot_is_close_enough = (
            position
            >= (
                predicted
                - self._stale_tolerance_seconds
            )
        )

        if snapshot_is_close_enough:
            self._anchor_position = (
                position
            )
            self._anchor_time = now

    def current(
        self,
    ) -> PlaybackPresentationState | None:
        if not self.active:
            return None

        now = self._now()

        return PlaybackPresentationState(
            position_seconds=(
                self._position_at(
                    now
                )
            ),
            duration_seconds=(
                self._duration_seconds
            ),
            playing=self._playing,
        )
