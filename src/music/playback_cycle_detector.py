from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Hashable


DEFAULT_NEAR_END_SECONDS = 2.5
DEFAULT_NEAR_START_SECONDS = 2.5
DEFAULT_MINIMUM_BACKWARD_JUMP_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class PlaybackCycleObservation:
    """Result of one playback-cycle observation."""

    replayed: bool
    cycle_index: int
    identity_changed: bool


class PlaybackCycleDetector:
    """
    Detect conservative same-track end-to-start playback cycles.

    The detector deliberately does not treat every backwards position change
    as a replay. A replay requires the same track identity, an earlier sample
    near the end of the track, a new sample near the beginning, a sufficiently
    large backwards jump, and active playback.

    Known seeks can explicitly suppress replay detection. When the caller knows
    that track-repeat is disabled, repeat_track=False also suppresses detection.
    """

    def __init__(
        self,
        *,
        near_end_seconds: float = DEFAULT_NEAR_END_SECONDS,
        near_start_seconds: float = DEFAULT_NEAR_START_SECONDS,
        minimum_backward_jump_seconds: float = (
            DEFAULT_MINIMUM_BACKWARD_JUMP_SECONDS
        ),
    ) -> None:
        self.near_end_seconds = self._checked_threshold(
            near_end_seconds,
            "near_end_seconds",
        )
        self.near_start_seconds = self._checked_threshold(
            near_start_seconds,
            "near_start_seconds",
        )
        self.minimum_backward_jump_seconds = self._checked_threshold(
            minimum_backward_jump_seconds,
            "minimum_backward_jump_seconds",
        )

        self.clear()

    @staticmethod
    def _checked_threshold(
        value: float,
        name: str,
    ) -> float:
        checked = float(value)

        if not math.isfinite(checked) or checked < 0.0:
            raise ValueError(
                f"{name} must be a finite non-negative number."
            )

        return checked

    @staticmethod
    def _safe_seconds(
        value: float | None,
    ) -> float | None:
        if value is None:
            return None

        try:
            checked = float(value)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(checked) or checked < 0.0:
            return None

        return checked

    def clear(self) -> None:
        self._identity: Hashable | None = None
        self._cycle_index = 0
        self._last_position_seconds: float | None = None
        self._last_duration_seconds: float | None = None
        self._last_playing = False

    @property
    def cycle_index(self) -> int:
        return self._cycle_index

    @property
    def identity(self) -> Hashable | None:
        return self._identity

    def observe(
        self,
        *,
        identity: Hashable | None,
        position_seconds: float | None,
        duration_seconds: float | None,
        playing: bool,
        repeat_track: bool | None = None,
        explicit_seek: bool = False,
    ) -> PlaybackCycleObservation:
        position = self._safe_seconds(
            position_seconds
        )
        duration = self._safe_seconds(
            duration_seconds
        )
        playing = bool(playing)

        if identity is None:
            identity_changed = (
                self._identity is not None
            )

            self.clear()

            return PlaybackCycleObservation(
                replayed=False,
                cycle_index=0,
                identity_changed=identity_changed,
            )

        identity_changed = (
            identity != self._identity
        )

        if identity_changed:
            self._identity = identity
            self._cycle_index = 0
            self._last_position_seconds = position
            self._last_duration_seconds = duration
            self._last_playing = playing

            return PlaybackCycleObservation(
                replayed=False,
                cycle_index=0,
                identity_changed=True,
            )

        replayed = self._is_replay(
            position_seconds=position,
            duration_seconds=duration,
            playing=playing,
            repeat_track=repeat_track,
            explicit_seek=bool(
                explicit_seek
            ),
        )

        if replayed:
            self._cycle_index += 1

        self._last_position_seconds = position
        self._last_duration_seconds = duration
        self._last_playing = playing

        return PlaybackCycleObservation(
            replayed=replayed,
            cycle_index=self._cycle_index,
            identity_changed=False,
        )

    def _is_replay(
        self,
        *,
        position_seconds: float | None,
        duration_seconds: float | None,
        playing: bool,
        repeat_track: bool | None,
        explicit_seek: bool,
    ) -> bool:
        if explicit_seek:
            return False

        if repeat_track is False:
            return False

        if not playing or not self._last_playing:
            return False

        if (
            position_seconds is None
            or duration_seconds is None
            or duration_seconds <= 0.0
            or self._last_position_seconds is None
        ):
            return False

        previous_position = (
            self._last_position_seconds
        )

        end_window = min(
            self.near_end_seconds,
            duration_seconds * 0.25,
        )

        start_window = min(
            self.near_start_seconds,
            duration_seconds * 0.25,
        )

        near_end_threshold = max(
            0.0,
            duration_seconds - end_window,
        )

        minimum_jump = min(
            self.minimum_backward_jump_seconds,
            duration_seconds * 0.5,
        )

        backward_jump = (
            previous_position
            - position_seconds
        )

        return (
            previous_position
            >= near_end_threshold
            and position_seconds
            <= start_window
            and backward_jump
            >= minimum_jump
        )


__all__ = [
    "DEFAULT_MINIMUM_BACKWARD_JUMP_SECONDS",
    "DEFAULT_NEAR_END_SECONDS",
    "DEFAULT_NEAR_START_SECONDS",
    "PlaybackCycleDetector",
    "PlaybackCycleObservation",
]