from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SCHEMA_VERSION = 1
GRID_COLUMNS = 12
MAX_GRID_ROWS = 20


@dataclass(frozen=True)
class DashboardCardSpec:
    card_id: str
    title: str
    minimum_column_span: int
    maximum_column_span: int
    minimum_row_span: int = 1
    maximum_row_span: int = 2
    movable: bool = True
    resizable: bool = True
    hideable: bool = True


CARD_SPECS = {
    "now_playing": DashboardCardSpec(
        card_id="now_playing",
        title="Now Playing",
        minimum_column_span=5,
        maximum_column_span=12,
    ),
    "discord_preview": DashboardCardSpec(
        card_id="discord_preview",
        title="Discord Preview",
        minimum_column_span=4,
        maximum_column_span=12,
    ),
    "recently_played": DashboardCardSpec(
        card_id="recently_played",
        title="Recently Played",
        minimum_column_span=4,
        maximum_column_span=12,
    ),
    "quick_access": DashboardCardSpec(
        card_id="quick_access",
        title="Quick Access",
        minimum_column_span=3,
        maximum_column_span=8,
    ),
    "library_status": DashboardCardSpec(
        card_id="library_status",
        title="Library Status",
        minimum_column_span=3,
        maximum_column_span=8,
    ),
    "discord_status": DashboardCardSpec(
        card_id="discord_status",
        title="Discord Status",
        minimum_column_span=3,
        maximum_column_span=6,
        maximum_row_span=1,
    ),
    "music_status": DashboardCardSpec(
        card_id="music_status",
        title="Music Status",
        minimum_column_span=3,
        maximum_column_span=6,
        maximum_row_span=1,
    ),
    "auto_afk": DashboardCardSpec(
        card_id="auto_afk",
        title="Auto AFK",
        minimum_column_span=3,
        maximum_column_span=6,
        maximum_row_span=1,
    ),
}


CARD_ORDER = tuple(
    CARD_SPECS.keys()
)


@dataclass(frozen=True)
class DashboardCardLayout:
    card_id: str
    row: int
    column: int
    column_span: int
    row_span: int = 1
    visible: bool = True

    def to_dict(self) -> dict:
        return {
            "card_id": self.card_id,
            "row": self.row,
            "column": self.column,
            "column_span": self.column_span,
            "row_span": self.row_span,
            "visible": self.visible,
        }

    @classmethod
    def from_dict(
        cls,
        payload,
    ) -> "DashboardCardLayout":
        if not isinstance(payload, dict):
            raise ValueError(
                "Dashboard card data must be an object."
            )

        return cls(
            card_id=str(
                payload.get(
                    "card_id",
                    "",
                )
            ).strip(),
            row=_strict_integer(
                payload.get("row"),
                "row",
            ),
            column=_strict_integer(
                payload.get("column"),
                "column",
            ),
            column_span=_strict_integer(
                payload.get("column_span"),
                "column_span",
            ),
            row_span=_strict_integer(
                payload.get(
                    "row_span",
                    1,
                ),
                "row_span",
            ),
            visible=_strict_boolean(
                payload.get(
                    "visible",
                    True,
                ),
                "visible",
            ),
        )


@dataclass(frozen=True)
class DashboardLayout:
    cards: tuple[DashboardCardLayout, ...]
    locked: bool = True
    preset: str = "Default"
    schema_version: int = SCHEMA_VERSION

    def card(
        self,
        card_id: str,
    ) -> DashboardCardLayout:
        for card in self.cards:
            if card.card_id == card_id:
                return card

        raise KeyError(card_id)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "locked": self.locked,
            "preset": self.preset,
            "cards": [
                card.to_dict()
                for card in self.cards
            ],
        }

    @classmethod
    def from_dict(
        cls,
        payload,
    ) -> "DashboardLayout":
        if not isinstance(payload, dict):
            raise ValueError(
                "Dashboard layout data must be an object."
            )

        schema_version = _strict_integer(
            payload.get(
                "schema_version",
                SCHEMA_VERSION,
            ),
            "schema_version",
        )

        if schema_version != SCHEMA_VERSION:
            raise ValueError(
                "Unsupported dashboard layout version."
            )

        cards_payload = payload.get(
            "cards"
        )

        if not isinstance(
            cards_payload,
            list,
        ):
            raise ValueError(
                "Dashboard cards must be a list."
            )

        layout = cls(
            cards=tuple(
                DashboardCardLayout.from_dict(
                    card
                )
                for card in cards_payload
            ),
            locked=_strict_boolean(
                payload.get(
                    "locked",
                    True,
                ),
                "locked",
            ),
            preset=str(
                payload.get(
                    "preset",
                    "Custom",
                )
                or "Custom"
            ).strip(),
            schema_version=schema_version,
        )

        validate_layout(layout)
        return layout


def _strict_integer(
    value,
    field_name: str,
) -> int:
    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be an integer."
        )

    try:
        converted = int(value)
    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            f"{field_name} must be an integer."
        ) from error

    if str(value).strip() != str(converted):
        if not isinstance(value, int):
            raise ValueError(
                f"{field_name} must be an integer."
            )

    return converted


def _strict_boolean(
    value,
    field_name: str,
) -> bool:
    if not isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be true or false."
        )

    return value


def _cards_overlap(
    first: DashboardCardLayout,
    second: DashboardCardLayout,
) -> bool:
    if not first.visible or not second.visible:
        return False

    first_right = (
        first.column
        + first.column_span
    )
    second_right = (
        second.column
        + second.column_span
    )

    first_bottom = (
        first.row
        + first.row_span
    )
    second_bottom = (
        second.row
        + second.row_span
    )

    return (
        first.column < second_right
        and second.column < first_right
        and first.row < second_bottom
        and second.row < first_bottom
    )


def validate_layout(
    layout: DashboardLayout,
) -> DashboardLayout:
    if not isinstance(
        layout,
        DashboardLayout,
    ):
        raise TypeError(
            "Expected a DashboardLayout."
        )

    if layout.schema_version != SCHEMA_VERSION:
        raise ValueError(
            "Unsupported dashboard layout version."
        )

    if len(layout.cards) != len(CARD_ORDER):
        raise ValueError(
            "The dashboard layout must contain every card."
        )

    card_ids = [
        card.card_id
        for card in layout.cards
    ]

    if set(card_ids) != set(CARD_ORDER):
        raise ValueError(
            "The dashboard layout contains missing "
            "or unknown cards."
        )

    if len(card_ids) != len(
        set(card_ids)
    ):
        raise ValueError(
            "The dashboard layout contains duplicate cards."
        )

    for card in layout.cards:
        spec = CARD_SPECS[
            card.card_id
        ]

        if not (
            0
            <= card.row
            < MAX_GRID_ROWS
        ):
            raise ValueError(
                f"{spec.title} has an invalid row."
            )

        if not (
            0
            <= card.column
            < GRID_COLUMNS
        ):
            raise ValueError(
                f"{spec.title} has an invalid column."
            )

        if not (
            spec.minimum_column_span
            <= card.column_span
            <= spec.maximum_column_span
        ):
            raise ValueError(
                f"{spec.title} has an invalid width."
            )

        if (
            card.column
            + card.column_span
            > GRID_COLUMNS
        ):
            raise ValueError(
                f"{spec.title} extends beyond the grid."
            )

        if not (
            spec.minimum_row_span
            <= card.row_span
            <= spec.maximum_row_span
        ):
            raise ValueError(
                f"{spec.title} has an invalid height."
            )

        if (
            card.row
            + card.row_span
            > MAX_GRID_ROWS
        ):
            raise ValueError(
                f"{spec.title} extends beyond the grid."
            )

    for index, first in enumerate(
        layout.cards
    ):
        for second in layout.cards[
            index + 1:
        ]:
            if _cards_overlap(
                first,
                second,
            ):
                raise ValueError(
                    "Dashboard cards overlap: "
                    f"{CARD_SPECS[first.card_id].title} "
                    "and "
                    f"{CARD_SPECS[second.card_id].title}."
                )

    return layout


def _make_layout(
    name: str,
    cards,
    locked: bool = True,
) -> DashboardLayout:
    layout = DashboardLayout(
        cards=tuple(
            DashboardCardLayout(
                card_id=card_id,
                row=row,
                column=column,
                column_span=column_span,
                row_span=row_span,
                visible=visible,
            )
            for (
                card_id,
                row,
                column,
                column_span,
                row_span,
                visible,
            ) in cards
        ),
        locked=locked,
        preset=name,
    )

    return validate_layout(
        layout
    )


PRESET_LAYOUTS = {
    "Default": _make_layout(
        "Default",
        (
            (
                "now_playing",
                0,
                0,
                7,
                1,
                True,
            ),
            (
                "discord_preview",
                0,
                7,
                5,
                1,
                True,
            ),
            (
                "recently_played",
                1,
                0,
                4,
                1,
                True,
            ),
            (
                "quick_access",
                1,
                4,
                4,
                1,
                True,
            ),
            (
                "library_status",
                1,
                8,
                4,
                1,
                True,
            ),
            (
                "discord_status",
                2,
                0,
                4,
                1,
                True,
            ),
            (
                "music_status",
                2,
                4,
                4,
                1,
                True,
            ),
            (
                "auto_afk",
                2,
                8,
                4,
                1,
                True,
            ),
        ),
    ),
    "Media Focus": _make_layout(
        "Media Focus",
        (
            (
                "now_playing",
                0,
                0,
                8,
                1,
                True,
            ),
            (
                "discord_preview",
                0,
                8,
                4,
                1,
                True,
            ),
            (
                "recently_played",
                1,
                0,
                6,
                1,
                True,
            ),
            (
                "library_status",
                1,
                6,
                6,
                1,
                True,
            ),
            (
                "quick_access",
                3,
                0,
                4,
                1,
                False,
            ),
            (
                "discord_status",
                2,
                0,
                4,
                1,
                True,
            ),
            (
                "music_status",
                2,
                4,
                4,
                1,
                True,
            ),
            (
                "auto_afk",
                2,
                8,
                4,
                1,
                True,
            ),
        ),
    ),
    "Compact": _make_layout(
        "Compact",
        (
            (
                "now_playing",
                0,
                0,
                6,
                1,
                True,
            ),
            (
                "discord_preview",
                0,
                6,
                6,
                1,
                True,
            ),
            (
                "recently_played",
                1,
                0,
                4,
                1,
                True,
            ),
            (
                "quick_access",
                1,
                4,
                4,
                1,
                True,
            ),
            (
                "library_status",
                1,
                8,
                4,
                1,
                True,
            ),
            (
                "discord_status",
                2,
                0,
                4,
                1,
                True,
            ),
            (
                "music_status",
                2,
                4,
                4,
                1,
                True,
            ),
            (
                "auto_afk",
                2,
                8,
                4,
                1,
                True,
            ),
        ),
    ),
    "Library Focus": _make_layout(
        "Library Focus",
        (
            (
                "recently_played",
                0,
                0,
                8,
                1,
                True,
            ),
            (
                "library_status",
                0,
                8,
                4,
                1,
                True,
            ),
            (
                "now_playing",
                1,
                0,
                8,
                1,
                True,
            ),
            (
                "discord_preview",
                1,
                8,
                4,
                1,
                True,
            ),
            (
                "quick_access",
                3,
                0,
                4,
                1,
                False,
            ),
            (
                "discord_status",
                2,
                0,
                4,
                1,
                True,
            ),
            (
                "music_status",
                2,
                4,
                4,
                1,
                True,
            ),
            (
                "auto_afk",
                2,
                8,
                4,
                1,
                True,
            ),
        ),
    ),
    "Minimal": _make_layout(
        "Minimal",
        (
            (
                "now_playing",
                0,
                0,
                8,
                1,
                True,
            ),
            (
                "discord_preview",
                0,
                8,
                4,
                1,
                True,
            ),
            (
                "recently_played",
                1,
                0,
                4,
                1,
                False,
            ),
            (
                "quick_access",
                1,
                4,
                4,
                1,
                False,
            ),
            (
                "library_status",
                1,
                8,
                4,
                1,
                False,
            ),
            (
                "discord_status",
                2,
                0,
                4,
                1,
                False,
            ),
            (
                "music_status",
                2,
                4,
                4,
                1,
                False,
            ),
            (
                "auto_afk",
                2,
                8,
                4,
                1,
                False,
            ),
        ),
    ),
}


def available_presets() -> tuple[str, ...]:
    return tuple(
        PRESET_LAYOUTS.keys()
    )


def preset_layout(
    name: str,
) -> DashboardLayout:
    normalized = str(
        name or ""
    ).strip().casefold()

    for preset_name, layout in (
        PRESET_LAYOUTS.items()
    ):
        if (
            preset_name.casefold()
            == normalized
        ):
            return layout

    raise KeyError(
        f"Unknown dashboard preset: {name}"
    )


class DashboardLayoutStore:
    def __init__(
        self,
        path: Path | str | None = None,
    ):
        self.path = (
            Path(path)
            if path is not None
            else self.default_path()
        )

    @staticmethod
    def default_path() -> Path:
        local_app_data = str(
            os.getenv(
                "LOCALAPPDATA",
                "",
            )
            or ""
        ).strip()

        if local_app_data:
            root = Path(
                local_app_data
            )
        else:
            root = (
                Path.home()
                / ".0337am-presence"
            )

        return (
            root
            / "0337am Presence"
            / "dashboard_layout.json"
        )

    def load(self) -> DashboardLayout:
        if not self.path.exists():
            return preset_layout(
                "Default"
            )

        try:
            payload = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )

            return DashboardLayout.from_dict(
                payload
            )

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as error:
            self._quarantine_invalid_file()

            print(
                "Dashboard layout was invalid and "
                "has been reset: "
                f"{error}"
            )

            return preset_layout(
                "Default"
            )

    def save(
        self,
        layout: DashboardLayout,
    ) -> DashboardLayout:
        validated = validate_layout(
            layout
        )

        payload = json.dumps(
            validated.to_dict(),
            indent=2,
            ensure_ascii=False,
        )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self.path.with_name(
            self.path.name
            + ".tmp"
        )

        try:
            with temporary_path.open(
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write(payload)
                handle.write("\n")
                handle.flush()
                os.fsync(
                    handle.fileno()
                )

            os.replace(
                temporary_path,
                self.path,
            )

        except Exception:
            temporary_path.unlink(
                missing_ok=True
            )
            raise

        return validated

    def apply_preset(
        self,
        name: str,
    ) -> DashboardLayout:
        return self.save(
            preset_layout(name)
        )

    def reset(self) -> DashboardLayout:
        return self.apply_preset(
            "Default"
        )

    def _quarantine_invalid_file(self):
        if not self.path.exists():
            return

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        quarantine_path = (
            self.path.with_name(
                self.path.name
                + f".corrupt_{timestamp}"
            )
        )

        try:
            os.replace(
                self.path,
                quarantine_path,
            )
        except OSError:
            pass
