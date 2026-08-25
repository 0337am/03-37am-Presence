from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from src.ui.custom_cards import (
    MAX_CUSTOM_CARDS,
    validate_card_id,
)


SCHEMA_VERSION = 3
CANVAS_UNITS = 10000


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
    "queue": DashboardCardSpec(
        card_id="queue",
        title="Spotify Queue",
        minimum_column_span=4,
        maximum_column_span=12,
    ),
}


CARD_ORDER = tuple(
    CARD_SPECS.keys()
)


CUSTOM_CARD_SPEC = DashboardCardSpec(
    card_id="custom",
    title="Custom card",
    minimum_column_span=1,
    maximum_column_span=12,
    minimum_row_span=1,
    maximum_row_span=12,
)


def is_custom_dashboard_card_id(
    card_id: str,
) -> bool:
    try:
        validate_card_id(card_id)
    except (TypeError, ValueError):
        return False

    return True


def dashboard_card_spec(
    card_id: str,
) -> DashboardCardSpec:
    spec = CARD_SPECS.get(card_id)

    if spec is not None:
        return spec

    if is_custom_dashboard_card_id(card_id):
        return replace(
            CUSTOM_CARD_SPEC,
            card_id=card_id,
        )

    raise KeyError(card_id)


@dataclass(frozen=True)
class DashboardCardLayout:
    card_id: str
    x: int
    y: int
    width: int
    height: int
    z_index: int = 0
    visible: bool = True

    def to_dict(self) -> dict:
        return {
            "card_id": self.card_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "z_index": self.z_index,
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
            x=_strict_integer(
                payload.get("x"),
                "x",
            ),
            y=_strict_integer(
                payload.get("y"),
                "y",
            ),
            width=_strict_integer(
                payload.get("width"),
                "width",
            ),
            height=_strict_integer(
                payload.get("height"),
                "height",
            ),
            z_index=_strict_integer(
                payload.get(
                    "z_index",
                    0,
                ),
                "z_index",
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
                1,
            ),
            "schema_version",
        )

        if schema_version == 1:
            return _migrate_v1_payload(
                payload
            )

        if schema_version == 2:
            return _migrate_v2_payload(
                payload
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

        return validate_layout(
            layout
        )


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

    if len(layout.cards) < len(CARD_ORDER):
        raise ValueError(
            "The dashboard layout must contain every built-in card."
        )

    if len(layout.cards) > (
        len(CARD_ORDER)
        + MAX_CUSTOM_CARDS
    ):
        raise ValueError(
            "The dashboard layout contains too many custom cards."
        )

    card_ids = [
        card.card_id
        for card in layout.cards
    ]

    if len(card_ids) != len(
        set(card_ids)
    ):
        raise ValueError(
            "The dashboard layout contains duplicate cards."
        )

    built_in_ids = {
        card_id
        for card_id in card_ids
        if card_id in CARD_SPECS
    }

    if built_in_ids != set(CARD_ORDER):
        raise ValueError(
            "The dashboard layout contains missing built-in cards."
        )

    for card_id in card_ids:
        if card_id in CARD_SPECS:
            continue

        try:
            validate_card_id(card_id)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "The dashboard layout contains an unknown card."
            ) from error

    for card in layout.cards:
        spec = dashboard_card_spec(
            card.card_id
        )

        if not (
            0
            <= card.x
            < CANVAS_UNITS
        ):
            raise ValueError(
                f"{spec.title} has an invalid horizontal position."
            )

        if not (
            0
            <= card.y
            < CANVAS_UNITS
        ):
            raise ValueError(
                f"{spec.title} has an invalid vertical position."
            )

        if not (
            1
            <= card.width
            <= CANVAS_UNITS
        ):
            raise ValueError(
                f"{spec.title} has an invalid width."
            )

        if not (
            1
            <= card.height
            <= CANVAS_UNITS
        ):
            raise ValueError(
                f"{spec.title} has an invalid height."
            )

        if (
            card.x
            + card.width
            > CANVAS_UNITS
        ):
            raise ValueError(
                f"{spec.title} extends beyond the dashboard width."
            )

        if (
            card.y
            + card.height
            > CANVAS_UNITS
        ):
            raise ValueError(
                f"{spec.title} extends beyond the dashboard height."
            )

        if not (
            0
            <= card.z_index
            <= 1000000
        ):
            raise ValueError(
                f"{spec.title} has an invalid layer."
            )

    return layout


def move_card_freeform(
    layout: DashboardLayout,
    card_id: str,
    x: int,
    y: int,
    z_index: int | None = None,
) -> DashboardLayout:
    validated = validate_layout(
        layout
    )

    try:
        moving_card = validated.card(
            card_id
        )
    except KeyError as error:
        raise ValueError(
            "The dashboard card to move is unknown."
        ) from error

    spec = dashboard_card_spec(
        moving_card.card_id
    )

    if not moving_card.visible:
        raise ValueError(
            "A hidden dashboard card cannot be moved."
        )

    if not spec.movable:
        raise ValueError(
            f"{spec.title} cannot be moved."
        )

    requested_x = _strict_integer(
        x,
        "x",
    )

    requested_y = _strict_integer(
        y,
        "y",
    )

    requested_z = (
        moving_card.z_index
        if z_index is None
        else _strict_integer(
            z_index,
            "z_index",
        )
    )

    moved_card = replace(
        moving_card,
        x=requested_x,
        y=requested_y,
        z_index=requested_z,
    )

    updated = replace(
        validated,
        cards=tuple(
            moved_card
            if card.card_id == card_id
            else card
            for card in validated.cards
        ),
        preset="Custom",
    )

    return validate_layout(
        updated
    )


def resize_card_freeform(
    layout: DashboardLayout,
    card_id: str,
    width: int,
    height: int,
    z_index: int | None = None,
) -> DashboardLayout:
    validated = validate_layout(
        layout
    )

    try:
        resizing_card = validated.card(
            card_id
        )
    except KeyError as error:
        raise ValueError(
            "The dashboard card to resize is unknown."
        ) from error

    spec = dashboard_card_spec(
        resizing_card.card_id
    )

    if not resizing_card.visible:
        raise ValueError(
            "A hidden dashboard card cannot be resized."
        )

    if not spec.resizable:
        raise ValueError(
            f"{spec.title} cannot be resized."
        )

    requested_width = _strict_integer(
        width,
        "width",
    )

    requested_height = _strict_integer(
        height,
        "height",
    )

    requested_z = (
        resizing_card.z_index
        if z_index is None
        else _strict_integer(
            z_index,
            "z_index",
        )
    )

    resized_card = replace(
        resizing_card,
        width=requested_width,
        height=requested_height,
        z_index=requested_z,
    )

    updated = replace(
        validated,
        cards=tuple(
            resized_card
            if card.card_id == card_id
            else card
            for card in validated.cards
        ),
        preset="Custom",
    )

    return validate_layout(
        updated
    )



def _with_hidden_queue_card(
    cards,
) -> tuple[DashboardCardLayout, ...]:
    cards = tuple(
        cards
    )

    queue_cards = tuple(
        card
        for card in cards
        if card.card_id == "queue"
    )

    if len(queue_cards) > 1:
        raise ValueError(
            "The dashboard layout contains duplicate Queue cards."
        )

    if queue_cards:
        return cards

    z_index = (
        max(
            (
                card.z_index
                for card in cards
            ),
            default=0,
        )
        + 1
    )

    return (
        *cards,
        DashboardCardLayout(
            card_id="queue",
            x=0,
            y=3600,
            width=4900,
            height=4300,
            z_index=z_index,
            visible=False,
        ),
    )


def _make_layout(
    name: str,
    cards,
    locked: bool = True,
) -> DashboardLayout:
    layout = DashboardLayout(
        cards=_with_hidden_queue_card(
            DashboardCardLayout(
                card_id=card_id,
                x=x,
                y=y,
                width=width,
                height=height,
                z_index=z_index,
                visible=visible,
            )
            for (
                card_id,
                x,
                y,
                width,
                height,
                z_index,
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
            ("now_playing", 0, 0, 5750, 3400, 1, True),
            ("discord_preview", 5950, 0, 4050, 3400, 2, True),
            ("recently_played", 0, 3600, 3200, 4300, 3, True),
            ("quick_access", 3400, 3600, 3200, 4300, 4, True),
            ("library_status", 6800, 3600, 3200, 4300, 5, True),
            ("discord_status", 0, 8100, 3200, 1500, 6, True),
            ("music_status", 3400, 8100, 3200, 1500, 7, True),
            ("auto_afk", 6800, 8100, 3200, 1500, 8, True),
        ),
    ),
    "Media Focus": _make_layout(
        "Media Focus",
        (
            ("now_playing", 0, 0, 6550, 3400, 1, True),
            ("discord_preview", 6750, 0, 3250, 3400, 2, True),
            ("recently_played", 0, 3600, 4900, 4300, 3, True),
            ("library_status", 5100, 3600, 4900, 4300, 4, True),
            ("quick_access", 0, 3600, 3200, 4300, 5, False),
            ("discord_status", 0, 8100, 3200, 1500, 6, True),
            ("music_status", 3400, 8100, 3200, 1500, 7, True),
            ("auto_afk", 6800, 8100, 3200, 1500, 8, True),
        ),
    ),
    "Compact": _make_layout(
        "Compact",
        (
            ("now_playing", 0, 0, 4900, 3400, 1, True),
            ("discord_preview", 5100, 0, 4900, 3400, 2, True),
            ("recently_played", 0, 3600, 3200, 4300, 3, True),
            ("quick_access", 3400, 3600, 3200, 4300, 4, True),
            ("library_status", 6800, 3600, 3200, 4300, 5, True),
            ("discord_status", 0, 8100, 3200, 1500, 6, True),
            ("music_status", 3400, 8100, 3200, 1500, 7, True),
            ("auto_afk", 6800, 8100, 3200, 1500, 8, True),
        ),
    ),
    "Library Focus": _make_layout(
        "Library Focus",
        (
            ("recently_played", 0, 0, 6550, 3400, 1, True),
            ("library_status", 6750, 0, 3250, 3400, 2, True),
            ("now_playing", 0, 3600, 6550, 4300, 3, True),
            ("discord_preview", 6750, 3600, 3250, 4300, 4, True),
            ("quick_access", 0, 3600, 3200, 4300, 5, False),
            ("discord_status", 0, 8100, 3200, 1500, 6, True),
            ("music_status", 3400, 8100, 3200, 1500, 7, True),
            ("auto_afk", 6800, 8100, 3200, 1500, 8, True),
        ),
    ),
    "Minimal": _make_layout(
        "Minimal",
        (
            ("now_playing", 0, 0, 6550, 3400, 1, True),
            ("discord_preview", 6750, 0, 3250, 3400, 2, True),
            ("recently_played", 0, 3600, 3200, 4300, 3, False),
            ("quick_access", 3400, 3600, 3200, 4300, 4, False),
            ("library_status", 6800, 3600, 3200, 4300, 5, False),
            ("discord_status", 0, 8100, 3200, 1500, 6, False),
            ("music_status", 3400, 8100, 3200, 1500, 7, False),
            ("auto_afk", 6800, 8100, 3200, 1500, 8, False),
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



def _migrate_v2_payload(
    payload,
) -> DashboardLayout:
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

    migrated = DashboardLayout(
        cards=_with_hidden_queue_card(
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
        schema_version=SCHEMA_VERSION,
    )

    return validate_layout(
        migrated
    )


def _migrate_v1_payload(
    payload,
) -> DashboardLayout:
    locked = _strict_boolean(
        payload.get(
            "locked",
            True,
        ),
        "locked",
    )

    preset_name = str(
        payload.get(
            "preset",
            "Custom",
        )
        or "Custom"
    ).strip()

    if preset_name in PRESET_LAYOUTS:
        return replace(
            preset_layout(
                preset_name
            ),
            locked=locked,
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

    row_bands = {
        0: (0, 3400),
        1: (3600, 4300),
        2: (8100, 1500),
        3: (8100, 1500),
    }

    migrated_cards = []

    for index, card_payload in enumerate(
        cards_payload
    ):
        if not isinstance(
            card_payload,
            dict,
        ):
            raise ValueError(
                "Dashboard card data must be an object."
            )

        card_id = str(
            card_payload.get(
                "card_id",
                "",
            )
        ).strip()

        row = _strict_integer(
            card_payload.get(
                "row",
                0,
            ),
            "row",
        )

        column = _strict_integer(
            card_payload.get(
                "column",
                0,
            ),
            "column",
        )

        column_span = _strict_integer(
            card_payload.get(
                "column_span",
                1,
            ),
            "column_span",
        )

        row_span = _strict_integer(
            card_payload.get(
                "row_span",
                1,
            ),
            "row_span",
        )

        visible = _strict_boolean(
            card_payload.get(
                "visible",
                True,
            ),
            "visible",
        )

        left = round(
            (
                column
                / 12
            )
            * CANVAS_UNITS
        )

        right = round(
            (
                (
                    column
                    + column_span
                )
                / 12
            )
            * CANVAS_UNITS
        )

        horizontal_gap = 80

        x = left + (
            horizontal_gap
            if column > 0
            else 0
        )

        right -= (
            horizontal_gap
            if (
                column
                + column_span
                < 12
            )
            else 0
        )

        width = max(
            250,
            right - x,
        )

        if row in row_bands:
            y, height = row_bands[
                row
            ]

            if row_span > 1:
                final_row = min(
                    max(
                        row_bands
                    ),
                    row
                    + row_span
                    - 1,
                )

                final_y, final_height = (
                    row_bands[
                        final_row
                    ]
                )

                height = (
                    final_y
                    + final_height
                    - y
                )
        else:
            y = min(
                9000,
                max(
                    0,
                    row * 2200,
                ),
            )

            height = min(
                CANVAS_UNITS - y,
                max(
                    900,
                    row_span * 1800,
                ),
            )

        migrated_cards.append(
            DashboardCardLayout(
                card_id=card_id,
                x=x,
                y=y,
                width=width,
                height=height,
                z_index=index,
                visible=visible,
            )
        )

    migrated = DashboardLayout(
        cards=_with_hidden_queue_card(
            migrated_cards
        ),
        locked=locked,
        preset="Custom",
        schema_version=SCHEMA_VERSION,
    )

    return validate_layout(
        migrated
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

            source_version = _strict_integer(
                payload.get(
                    "schema_version",
                    1,
                ),
                "schema_version",
            )

            layout = DashboardLayout.from_dict(
                payload
            )

            if source_version in {1, 2}:
                self._backup_legacy_file()

                try:
                    self.save(
                        layout
                    )
                except OSError as error:
                    print(
                        "Dashboard layout migration could not "
                        f"be saved: {error}"
                    )

            return layout

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

    def _backup_legacy_file(self):
        if not self.path.exists():
            return

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup_path = self.path.with_name(
            self.path.name
            + f".v1_backup_{timestamp}"
        )

        try:
            shutil.copy2(
                self.path,
                backup_path,
            )
        except OSError:
            pass

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
