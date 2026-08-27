from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


CATALOGUE_KIND_BUILTIN = "builtin"

MAX_ITEM_ID_LENGTH = 96
MAX_KIND_LENGTH = 32
MAX_TARGET_LENGTH = 64
MAX_TITLE_LENGTH = 96
MAX_DETAIL_LENGTH = 160
MAX_ICON_KEY_LENGTH = 64


def _strict_text(
    value,
    field_name: str,
    maximum: int,
    *,
    casefold: bool = False,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be text."
        )

    normalized = value.strip()

    if casefold:
        normalized = normalized.casefold()

    if not normalized:
        raise ValueError(
            f"{field_name} cannot be empty."
        )

    if len(normalized) > maximum:
        raise ValueError(
            f"{field_name} is too long."
        )

    return normalized


@dataclass(frozen=True)
class QuickAccessCatalogueEntry:
    item_id: str
    kind: str
    target: str
    title: str
    detail: str
    icon_key: str
    included_by_default: bool = False

    def __post_init__(
        self,
    ) -> None:
        item_id = _strict_text(
            self.item_id,
            "item_id",
            MAX_ITEM_ID_LENGTH,
            casefold=True,
        )

        kind = _strict_text(
            self.kind,
            "kind",
            MAX_KIND_LENGTH,
            casefold=True,
        )

        target = _strict_text(
            self.target,
            "target",
            MAX_TARGET_LENGTH,
            casefold=True,
        )

        title = _strict_text(
            self.title,
            "title",
            MAX_TITLE_LENGTH,
        )

        detail = _strict_text(
            self.detail,
            "detail",
            MAX_DETAIL_LENGTH,
        )

        icon_key = _strict_text(
            self.icon_key,
            "icon_key",
            MAX_ICON_KEY_LENGTH,
            casefold=True,
        )

        if type(
            self.included_by_default
        ) is not bool:
            raise TypeError(
                "included_by_default must be boolean."
            )

        if kind != CATALOGUE_KIND_BUILTIN:
            raise ValueError(
                "Unsupported Quick Access catalogue kind."
            )

        expected_item_id = (
            "builtin."
            + target
        )

        if item_id != expected_item_id:
            raise ValueError(
                "Built-in Quick Access item_id must match "
                "its target."
            )

        object.__setattr__(
            self,
            "item_id",
            item_id,
        )

        object.__setattr__(
            self,
            "kind",
            kind,
        )

        object.__setattr__(
            self,
            "target",
            target,
        )

        object.__setattr__(
            self,
            "title",
            title,
        )

        object.__setattr__(
            self,
            "detail",
            detail,
        )

        object.__setattr__(
            self,
            "icon_key",
            icon_key,
        )


_QUICK_ACCESS_CATALOGUE = (
    QuickAccessCatalogueEntry(
        item_id="builtin.afk",
        kind="builtin",
        target="afk",
        title="AFK",
        detail="Set AFK presence",
        icon_key="afk",
        included_by_default=True,
    ),
    QuickAccessCatalogueEntry(
        item_id="builtin.custom",
        kind="builtin",
        target="custom",
        title="Custom",
        detail="Create a presence",
        icon_key="custom",
        included_by_default=True,
    ),
    QuickAccessCatalogueEntry(
        item_id="builtin.presets",
        kind="builtin",
        target="presets",
        title="Presets",
        detail="Manage presence modes",
        icon_key="presets",
        included_by_default=True,
    ),
    QuickAccessCatalogueEntry(
        item_id="builtin.settings",
        kind="builtin",
        target="settings",
        title="Settings",
        detail="Configure application",
        icon_key="settings",
        included_by_default=True,
    ),
    QuickAccessCatalogueEntry(
        item_id="builtin.presence",
        kind="builtin",
        target="presence",
        title="Presence",
        detail="Open Presence Studio",
        icon_key="presence",
    ),
    QuickAccessCatalogueEntry(
        item_id="builtin.library",
        kind="builtin",
        target="library",
        title="Library",
        detail="Open music library",
        icon_key="library",
    ),
    QuickAccessCatalogueEntry(
        item_id="builtin.spotify",
        kind="builtin",
        target="spotify",
        title="Spotify",
        detail="Open Spotify",
        icon_key="spotify",
    ),
    QuickAccessCatalogueEntry(
        item_id="builtin.about",
        kind="builtin",
        target="about",
        title="About",
        detail="Open app information",
        icon_key="about",
    ),
)


def _validate_catalogue(
    entries: tuple[
        QuickAccessCatalogueEntry,
        ...,
    ],
) -> None:
    item_ids = [
        entry.item_id
        for entry in entries
    ]

    targets = [
        entry.target
        for entry in entries
    ]

    if len(
        item_ids
    ) != len(
        set(
            item_ids
        )
    ):
        raise ValueError(
            "Quick Access catalogue item IDs must be unique."
        )

    if len(
        targets
    ) != len(
        set(
            targets
        )
    ):
        raise ValueError(
            "Quick Access catalogue targets must be unique."
        )


_validate_catalogue(
    _QUICK_ACCESS_CATALOGUE
)


def quick_access_catalogue(
) -> tuple[
    QuickAccessCatalogueEntry,
    ...,
]:
    return _QUICK_ACCESS_CATALOGUE


def default_quick_access_catalogue(
) -> tuple[
    QuickAccessCatalogueEntry,
    ...,
]:
    return tuple(
        entry
        for entry in _QUICK_ACCESS_CATALOGUE
        if entry.included_by_default
    )


def optional_quick_access_catalogue(
) -> tuple[
    QuickAccessCatalogueEntry,
    ...,
]:
    return tuple(
        entry
        for entry in _QUICK_ACCESS_CATALOGUE
        if not entry.included_by_default
    )


def quick_access_catalogue_entry(
    item_id: str,
) -> QuickAccessCatalogueEntry | None:
    normalized = str(
        item_id
        or ""
    ).strip().casefold()

    for entry in _QUICK_ACCESS_CATALOGUE:
        if entry.item_id == normalized:
            return entry

    return None


def quick_access_catalogue_entry_for_target(
    target: str,
) -> QuickAccessCatalogueEntry | None:
    normalized = str(
        target
        or ""
    ).strip().casefold()

    for entry in _QUICK_ACCESS_CATALOGUE:
        if entry.target == normalized:
            return entry

    return None


def addable_quick_access_catalogue(
    existing_item_ids: Iterable[str],
) -> tuple[
    QuickAccessCatalogueEntry,
    ...,
]:
    existing = {
        str(
            item_id
            or ""
        ).strip().casefold()
        for item_id in existing_item_ids
    }

    return tuple(
        entry
        for entry in _QUICK_ACCESS_CATALOGUE
        if entry.item_id not in existing
    )
