from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal


DEFAULT_ALIGNMENT_THRESHOLD = 8

GuideOrientation = Literal[
    "vertical",
    "horizontal",
]

GuideSource = Literal[
    "card",
    "canvas",
]


@dataclass(
    frozen=True,
    slots=True,
)
class AlignmentRect:
    x: int
    y: int
    width: int
    height: int

    @property
    def left(self) -> int:
        return self.x

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def top(self) -> int:
        return self.y

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def center_x(self) -> int:
        return (
            self.x
            + self.width // 2
        )

    @property
    def center_y(self) -> int:
        return (
            self.y
            + self.height // 2
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AlignmentGuide:
    orientation: GuideOrientation
    position: int
    source: GuideSource
    kind: str


@dataclass(
    frozen=True,
    slots=True,
)
class AlignmentResult:
    rect: AlignmentRect
    guides: tuple[
        AlignmentGuide,
        ...,
    ]
    snapped_x: bool
    snapped_y: bool


@dataclass(
    frozen=True,
    slots=True,
)
class _AxisCandidate:
    value: int
    guide_position: int
    source: GuideSource
    kind: str
    kind_priority: int


def _clamp(
    value: int,
    minimum: int,
    maximum: int,
) -> int:
    return min(
        maximum,
        max(
            minimum,
            int(value),
        ),
    )


def _valid_rectangles(
    rectangles: Iterable[
        AlignmentRect
    ],
) -> tuple[
    AlignmentRect,
    ...,
]:
    return tuple(
        AlignmentRect(
            x=int(rectangle.x),
            y=int(rectangle.y),
            width=int(rectangle.width),
            height=int(rectangle.height),
        )
        for rectangle in rectangles
        if (
            int(rectangle.width) > 0
            and int(rectangle.height) > 0
        )
    )


def _choose_axis_candidate(
    requested: int,
    candidates: Iterable[
        _AxisCandidate
    ],
    minimum: int,
    maximum: int,
    threshold: int,
) -> _AxisCandidate | None:
    threshold = max(
        0,
        int(threshold),
    )

    eligible = tuple(
        candidate
        for candidate in candidates
        if (
            minimum
            <= candidate.value
            <= maximum
            and abs(
                candidate.value
                - requested
            )
            <= threshold
        )
    )

    if not eligible:
        return None

    card_candidates = tuple(
        candidate
        for candidate in eligible
        if candidate.source == "card"
    )

    pool = (
        card_candidates
        if card_candidates
        else eligible
    )

    return min(
        pool,
        key=lambda candidate: (
            abs(
                candidate.value
                - requested
            ),
            candidate.kind_priority,
            candidate.guide_position,
            candidate.value,
        ),
    )


def _move_x_candidates(
    width: int,
    canvas_width: int,
    other_rectangles: tuple[
        AlignmentRect,
        ...,
    ],
) -> tuple[
    _AxisCandidate,
    ...,
]:
    candidates = []

    for rectangle in other_rectangles:
        candidates.extend(
            (
                _AxisCandidate(
                    value=rectangle.left,
                    guide_position=rectangle.left,
                    source="card",
                    kind="matching edge",
                    kind_priority=0,
                ),
                _AxisCandidate(
                    value=(
                        rectangle.right
                        - width
                    ),
                    guide_position=rectangle.right,
                    source="card",
                    kind="matching edge",
                    kind_priority=0,
                ),
                _AxisCandidate(
                    value=(
                        rectangle.center_x
                        - width // 2
                    ),
                    guide_position=rectangle.center_x,
                    source="card",
                    kind="centre",
                    kind_priority=1,
                ),
                _AxisCandidate(
                    value=(
                        rectangle.left
                        - width
                    ),
                    guide_position=rectangle.left,
                    source="card",
                    kind="adjacent edge",
                    kind_priority=2,
                ),
                _AxisCandidate(
                    value=rectangle.right,
                    guide_position=rectangle.right,
                    source="card",
                    kind="adjacent edge",
                    kind_priority=2,
                ),
            )
        )

    candidates.extend(
        (
            _AxisCandidate(
                value=0,
                guide_position=0,
                source="canvas",
                kind="edge",
                kind_priority=0,
            ),
            _AxisCandidate(
                value=(
                    canvas_width
                    - width
                ),
                guide_position=canvas_width,
                source="canvas",
                kind="edge",
                kind_priority=0,
            ),
            _AxisCandidate(
                value=(
                    canvas_width // 2
                    - width // 2
                ),
                guide_position=(
                    canvas_width // 2
                ),
                source="canvas",
                kind="centre",
                kind_priority=1,
            ),
        )
    )

    return tuple(candidates)


def _move_y_candidates(
    height: int,
    canvas_height: int,
    other_rectangles: tuple[
        AlignmentRect,
        ...,
    ],
) -> tuple[
    _AxisCandidate,
    ...,
]:
    candidates = []

    for rectangle in other_rectangles:
        candidates.extend(
            (
                _AxisCandidate(
                    value=rectangle.top,
                    guide_position=rectangle.top,
                    source="card",
                    kind="matching edge",
                    kind_priority=0,
                ),
                _AxisCandidate(
                    value=(
                        rectangle.bottom
                        - height
                    ),
                    guide_position=rectangle.bottom,
                    source="card",
                    kind="matching edge",
                    kind_priority=0,
                ),
                _AxisCandidate(
                    value=(
                        rectangle.center_y
                        - height // 2
                    ),
                    guide_position=rectangle.center_y,
                    source="card",
                    kind="centre",
                    kind_priority=1,
                ),
                _AxisCandidate(
                    value=(
                        rectangle.top
                        - height
                    ),
                    guide_position=rectangle.top,
                    source="card",
                    kind="adjacent edge",
                    kind_priority=2,
                ),
                _AxisCandidate(
                    value=rectangle.bottom,
                    guide_position=rectangle.bottom,
                    source="card",
                    kind="adjacent edge",
                    kind_priority=2,
                ),
            )
        )

    candidates.extend(
        (
            _AxisCandidate(
                value=0,
                guide_position=0,
                source="canvas",
                kind="edge",
                kind_priority=0,
            ),
            _AxisCandidate(
                value=(
                    canvas_height
                    - height
                ),
                guide_position=canvas_height,
                source="canvas",
                kind="edge",
                kind_priority=0,
            ),
            _AxisCandidate(
                value=(
                    canvas_height // 2
                    - height // 2
                ),
                guide_position=(
                    canvas_height // 2
                ),
                source="canvas",
                kind="centre",
                kind_priority=1,
            ),
        )
    )

    return tuple(candidates)


def snap_moving_rect(
    *,
    requested_x: int,
    requested_y: int,
    width: int,
    height: int,
    canvas_width: int,
    canvas_height: int,
    other_rectangles: Iterable[
        AlignmentRect
    ] = (),
    threshold: int = (
        DEFAULT_ALIGNMENT_THRESHOLD
    ),
) -> AlignmentResult:
    canvas_width = max(
        1,
        int(canvas_width),
    )
    canvas_height = max(
        1,
        int(canvas_height),
    )

    width = _clamp(
        width,
        1,
        canvas_width,
    )
    height = _clamp(
        height,
        1,
        canvas_height,
    )

    maximum_x = max(
        0,
        canvas_width - width,
    )
    maximum_y = max(
        0,
        canvas_height - height,
    )

    x = _clamp(
        requested_x,
        0,
        maximum_x,
    )
    y = _clamp(
        requested_y,
        0,
        maximum_y,
    )

    rectangles = _valid_rectangles(
        other_rectangles
    )

    x_candidate = _choose_axis_candidate(
        x,
        _move_x_candidates(
            width,
            canvas_width,
            rectangles,
        ),
        0,
        maximum_x,
        threshold,
    )

    y_candidate = _choose_axis_candidate(
        y,
        _move_y_candidates(
            height,
            canvas_height,
            rectangles,
        ),
        0,
        maximum_y,
        threshold,
    )

    guides = []

    if x_candidate is not None:
        x = x_candidate.value

        guides.append(
            AlignmentGuide(
                orientation="vertical",
                position=(
                    x_candidate
                    .guide_position
                ),
                source=x_candidate.source,
                kind=x_candidate.kind,
            )
        )

    if y_candidate is not None:
        y = y_candidate.value

        guides.append(
            AlignmentGuide(
                orientation="horizontal",
                position=(
                    y_candidate
                    .guide_position
                ),
                source=y_candidate.source,
                kind=y_candidate.kind,
            )
        )

    return AlignmentResult(
        rect=AlignmentRect(
            x=x,
            y=y,
            width=width,
            height=height,
        ),
        guides=tuple(guides),
        snapped_x=(
            x_candidate is not None
        ),
        snapped_y=(
            y_candidate is not None
        ),
    )


def _resize_x_candidates(
    x: int,
    canvas_width: int,
    other_rectangles: tuple[
        AlignmentRect,
        ...,
    ],
) -> tuple[
    _AxisCandidate,
    ...,
]:
    candidates = []

    for rectangle in other_rectangles:
        candidates.extend(
            (
                _AxisCandidate(
                    value=(
                        rectangle.left
                        - x
                    ),
                    guide_position=rectangle.left,
                    source="card",
                    kind="edge",
                    kind_priority=0,
                ),
                _AxisCandidate(
                    value=(
                        rectangle.right
                        - x
                    ),
                    guide_position=rectangle.right,
                    source="card",
                    kind="edge",
                    kind_priority=0,
                ),
                _AxisCandidate(
                    value=(
                        rectangle.center_x
                        - x
                    ),
                    guide_position=rectangle.center_x,
                    source="card",
                    kind="centre",
                    kind_priority=1,
                ),
            )
        )

    candidates.extend(
        (
            _AxisCandidate(
                value=(
                    canvas_width - x
                ),
                guide_position=canvas_width,
                source="canvas",
                kind="edge",
                kind_priority=0,
            ),
            _AxisCandidate(
                value=(
                    canvas_width // 2
                    - x
                ),
                guide_position=(
                    canvas_width // 2
                ),
                source="canvas",
                kind="centre",
                kind_priority=1,
            ),
        )
    )

    return tuple(candidates)


def _resize_y_candidates(
    y: int,
    canvas_height: int,
    other_rectangles: tuple[
        AlignmentRect,
        ...,
    ],
) -> tuple[
    _AxisCandidate,
    ...,
]:
    candidates = []

    for rectangle in other_rectangles:
        candidates.extend(
            (
                _AxisCandidate(
                    value=(
                        rectangle.top
                        - y
                    ),
                    guide_position=rectangle.top,
                    source="card",
                    kind="edge",
                    kind_priority=0,
                ),
                _AxisCandidate(
                    value=(
                        rectangle.bottom
                        - y
                    ),
                    guide_position=rectangle.bottom,
                    source="card",
                    kind="edge",
                    kind_priority=0,
                ),
                _AxisCandidate(
                    value=(
                        rectangle.center_y
                        - y
                    ),
                    guide_position=rectangle.center_y,
                    source="card",
                    kind="centre",
                    kind_priority=1,
                ),
            )
        )

    candidates.extend(
        (
            _AxisCandidate(
                value=(
                    canvas_height - y
                ),
                guide_position=canvas_height,
                source="canvas",
                kind="edge",
                kind_priority=0,
            ),
            _AxisCandidate(
                value=(
                    canvas_height // 2
                    - y
                ),
                guide_position=(
                    canvas_height // 2
                ),
                source="canvas",
                kind="centre",
                kind_priority=1,
            ),
        )
    )

    return tuple(candidates)


def snap_resizing_rect(
    *,
    x: int,
    y: int,
    requested_width: int,
    requested_height: int,
    minimum_width: int,
    minimum_height: int,
    canvas_width: int,
    canvas_height: int,
    other_rectangles: Iterable[
        AlignmentRect
    ] = (),
    threshold: int = (
        DEFAULT_ALIGNMENT_THRESHOLD
    ),
) -> AlignmentResult:
    canvas_width = max(
        1,
        int(canvas_width),
    )
    canvas_height = max(
        1,
        int(canvas_height),
    )

    x = _clamp(
        x,
        0,
        canvas_width - 1,
    )
    y = _clamp(
        y,
        0,
        canvas_height - 1,
    )

    maximum_width = max(
        1,
        canvas_width - x,
    )
    maximum_height = max(
        1,
        canvas_height - y,
    )

    minimum_width = _clamp(
        minimum_width,
        1,
        maximum_width,
    )
    minimum_height = _clamp(
        minimum_height,
        1,
        maximum_height,
    )

    width = _clamp(
        requested_width,
        minimum_width,
        maximum_width,
    )
    height = _clamp(
        requested_height,
        minimum_height,
        maximum_height,
    )

    rectangles = _valid_rectangles(
        other_rectangles
    )

    width_candidate = (
        _choose_axis_candidate(
            width,
            _resize_x_candidates(
                x,
                canvas_width,
                rectangles,
            ),
            minimum_width,
            maximum_width,
            threshold,
        )
    )

    height_candidate = (
        _choose_axis_candidate(
            height,
            _resize_y_candidates(
                y,
                canvas_height,
                rectangles,
            ),
            minimum_height,
            maximum_height,
            threshold,
        )
    )

    guides = []

    if width_candidate is not None:
        width = width_candidate.value

        guides.append(
            AlignmentGuide(
                orientation="vertical",
                position=(
                    width_candidate
                    .guide_position
                ),
                source=(
                    width_candidate.source
                ),
                kind=width_candidate.kind,
            )
        )

    if height_candidate is not None:
        height = height_candidate.value

        guides.append(
            AlignmentGuide(
                orientation="horizontal",
                position=(
                    height_candidate
                    .guide_position
                ),
                source=(
                    height_candidate.source
                ),
                kind=height_candidate.kind,
            )
        )

    return AlignmentResult(
        rect=AlignmentRect(
            x=x,
            y=y,
            width=width,
            height=height,
        ),
        guides=tuple(guides),
        snapped_x=(
            width_candidate is not None
        ),
        snapped_y=(
            height_candidate is not None
        ),
    )
