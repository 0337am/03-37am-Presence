from __future__ import annotations

import inspect
import json
import sys
from types import SimpleNamespace
import unittest

from PyQt6.QtWidgets import QApplication

from src.system.quick_access_preferences import (
    MAX_DETAIL_LENGTH,
    MAX_TITLE_LENGTH,
    QuickAccessItem,
    QuickAccessPreferences,
    quick_access_preferences_from_payload,
    quick_access_preferences_to_payload,
)
from src.ui.custom_cards import (
    LauncherCardData,
)
from src.ui.dashboard import (
    DashboardPage,
)
from src.ui.quick_access_manager import (
    QuickAccessManagerDialog,
)
from src.ui.quick_access_picker import (
    QuickAccessPickerDialog,
)


CARD_A = (
    "custom_launcher_"
    + ("a" * 32)
)

CARD_B = (
    "custom_launcher_"
    + ("b" * 32)
)

WINDOWS_TARGET = (
    r"C:\Apps\Example\example.exe"
)


def make_card(
    *,
    card_id: str = CARD_A,
    title: str = "Example Launcher",
    description: str = "",
) -> LauncherCardData:
    return LauncherCardData(
        card_id=card_id,
        title=title,
        target=WINDOWS_TARGET,
        target_kind="application",
        icon="",
        image_asset="",
        description=description,
        button_label="Open",
        accent="",
    )


def launcher_item(
    card: LauncherCardData,
) -> QuickAccessItem:
    host = SimpleNamespace(
        custom_cards={
            card.card_id: card,
        }
    )

    items = (
        DashboardPage
        ._launcher_card_quick_access_items(
            host
        )
    )

    if len(items) != 1:
        raise AssertionError(
            "Expected exactly one Launcher item."
        )

    return items[0]


class _Signal:
    def __init__(
        self,
    ):
        self.calls = []

    def emit(
        self,
        *args,
    ):
        self.calls.append(
            args
        )


class _Recorder:
    def __init__(
        self,
    ):
        self.calls = []

    def __call__(
        self,
        *args,
        **kwargs,
    ):
        self.calls.append(
            (
                args,
                kwargs,
            )
        )


class _Grid:
    def count(
        self,
    ):
        return 0


class _PreferenceStore:
    def __init__(
        self,
        preferences,
    ):
        self.preferences = preferences

    def load(
        self,
    ):
        return self.preferences


class _PresetStore:
    def load(
        self,
    ):
        return ()

    def pinned(
        self,
    ):
        return ()


class _DashboardStub:
    def __init__(
        self,
        *,
        preferences,
        custom_cards,
    ):
        self.quick_access_grid = _Grid()
        self.quick_access_buttons = []

        self.quick_access_preferences_store = (
            _PreferenceStore(
                preferences
            )
        )

        self.presence_preset_store = (
            _PresetStore()
        )

        self.custom_cards = dict(
            custom_cards
        )

        self.navigate_requested = _Signal()
        self.apply_presence_mode_requested = _Signal()
        self.apply_presence_preset_requested = _Signal()

        self.open_launcher_card_target = (
            _Recorder()
        )

    def _make_quick_access_button(
        self,
        *,
        icon_key,
        title,
        detail,
        callback,
    ):
        return {
            "button": None,
            "icon_key": icon_key,
            "title": title,
            "detail": detail,
            "callback": callback,
        }

    def _refresh_quick_access_icons(
        self,
        theme=None,
    ):
        del theme

    def update_quick_access_layout(
        self,
        force=False,
    ):
        del force


class QuickAccessLauncherShortcutTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication(
                sys.argv[:1]
            )
        )

    def test_launcher_reference_round_trip(
        self,
    ):
        item = QuickAccessItem(
            item_id=(
                "launcher_card."
                + CARD_A
            ),
            kind="launcher_card",
            target=CARD_A,
            title="Example",
            detail="Application shortcut",
            icon_key="launcher",
            visible=False,
        )

        self.assertEqual(
            len(
                CARD_A
            ),
            48,
        )

        self.assertEqual(
            len(
                item.item_id
            ),
            62,
        )

        original = QuickAccessPreferences(
            items=(
                item,
            )
        )

        restored = (
            quick_access_preferences_from_payload(
                quick_access_preferences_to_payload(
                    original
                )
            )
        )

        self.assertEqual(
            restored,
            original,
        )

    def test_launcher_reference_rejects_non_launcher_card_id(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id=(
                    "launcher_card."
                    "custom_link_"
                    + ("a" * 32)
                ),
                kind="launcher_card",
                target=(
                    "custom_link_"
                    + ("a" * 32)
                ),
                title="Wrong",
                detail="Wrong",
                icon_key="launcher",
            )

    def test_launcher_reference_item_id_must_match_target(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id=(
                    "launcher_card."
                    + CARD_B
                ),
                kind="launcher_card",
                target=CARD_A,
                title="Wrong",
                detail="Wrong",
                icon_key="launcher",
            )

    def test_launcher_reference_icon_is_constrained(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            QuickAccessItem(
                item_id=(
                    "launcher_card."
                    + CARD_A
                ),
                kind="launcher_card",
                target=CARD_A,
                title="Wrong",
                detail="Wrong",
                icon_key="settings",
            )

    def test_dashboard_dynamic_launcher_uses_live_metadata_without_path_target(
        self,
    ):
        card = make_card(
            title=(
                "T"
                * 80
            ),
            description=(
                "D"
                * 300
            ),
        )

        item = launcher_item(
            card
        )

        self.assertEqual(
            item.target,
            CARD_A,
        )

        self.assertEqual(
            len(
                item.title
            ),
            MAX_TITLE_LENGTH,
        )

        self.assertEqual(
            len(
                item.detail
            ),
            MAX_DETAIL_LENGTH,
        )

        payload = (
            quick_access_preferences_to_payload(
                QuickAccessPreferences(
                    items=(
                        item,
                    )
                )
            )
        )

        encoded = json.dumps(
            payload
        )

        self.assertNotIn(
            WINDOWS_TARGET,
            encoded,
        )

    def test_dashboard_managed_launcher_uses_existing_open_route(
        self,
    ):
        card = make_card(
            title="Launcher Live",
        )

        item = launcher_item(
            card
        )

        dashboard = _DashboardStub(
            preferences=QuickAccessPreferences(
                items=(
                    item,
                )
            ),
            custom_cards={
                card.card_id: card,
            },
        )

        DashboardPage.refresh_quick_access_buttons(
            dashboard,
            force=True,
        )

        self.assertEqual(
            len(
                dashboard.quick_access_buttons
            ),
            1,
        )

        button = (
            dashboard.quick_access_buttons[
                0
            ]
        )

        self.assertEqual(
            button[
                "title"
            ],
            "Launcher Live",
        )

        button[
            "callback"
        ]()

        self.assertEqual(
            dashboard
            .open_launcher_card_target
            .calls,
            [
                (
                    (
                        CARD_A,
                    ),
                    {},
                ),
            ],
        )

    def test_dashboard_stale_launcher_fails_closed(
        self,
    ):
        item = launcher_item(
            make_card()
        )

        dashboard = _DashboardStub(
            preferences=QuickAccessPreferences(
                items=(
                    item,
                )
            ),
            custom_cards={},
        )

        DashboardPage.refresh_quick_access_buttons(
            dashboard,
            force=True,
        )

        self.assertEqual(
            dashboard.quick_access_buttons,
            [],
        )

        self.assertEqual(
            dashboard
            .open_launcher_card_target
            .calls,
            [],
        )

    def test_manager_refreshes_live_launcher_metadata(
        self,
    ):
        stale = QuickAccessItem(
            item_id=(
                "launcher_card."
                + CARD_A
            ),
            kind="launcher_card",
            target=CARD_A,
            title="Old title",
            detail="Old detail",
            icon_key="launcher",
            visible=False,
        )

        live = launcher_item(
            make_card(
                title="Renamed Launcher",
                description="Current description",
            )
        )

        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=(
                    stale,
                )
            ),
            dynamic_items=(
                live,
            ),
        )

        self.addCleanup(
            dialog.close
        )

        self.assertEqual(
            dialog._items[
                0
            ].title,
            "Renamed Launcher",
        )

        self.assertEqual(
            dialog._items[
                0
            ].detail,
            "Current description",
        )

        self.assertFalse(
            dialog._items[
                0
            ].visible
        )

    def test_manager_keeps_stale_launcher_reference(
        self,
    ):
        stale = QuickAccessItem(
            item_id=(
                "launcher_card."
                + CARD_A
            ),
            kind="launcher_card",
            target=CARD_A,
            title="Deleted Launcher",
            detail="Stale",
            icon_key="launcher",
            visible=True,
        )

        dialog = QuickAccessManagerDialog(
            QuickAccessPreferences(
                items=(
                    stale,
                )
            ),
            dynamic_items=(),
        )

        self.addCleanup(
            dialog.close
        )

        self.assertEqual(
            dialog._items,
            [
                stale,
            ],
        )

    def test_picker_lists_filters_and_keeps_duplicates_separate(
        self,
    ):
        first = launcher_item(
            make_card(
                card_id=CARD_A,
                title="First",
            )
        )

        second = launcher_item(
            make_card(
                card_id=CARD_B,
                title="Second",
            )
        )

        dialog = QuickAccessPickerDialog(
            (),
            dynamic_items=(
                first,
                second,
            ),
        )

        self.addCleanup(
            dialog.close
        )

        item_ids = {
            item.item_id
            for item in dialog._entries
        }

        self.assertIn(
            first.item_id,
            item_ids,
        )

        self.assertIn(
            second.item_id,
            item_ids,
        )

        filtered = QuickAccessPickerDialog(
            (
                first.item_id,
            ),
            dynamic_items=(
                first,
                second,
            ),
        )

        self.addCleanup(
            filtered.close
        )

        filtered_ids = {
            item.item_id
            for item in filtered._entries
        }

        self.assertNotIn(
            first.item_id,
            filtered_ids,
        )

        self.assertIn(
            second.item_id,
            filtered_ids,
        )

    def test_launcher_icon_renders(
        self,
    ):
        icon = (
            DashboardPage
            ._quick_access_icon(
                "launcher",
                "#ffffff",
            )
        )

        self.assertFalse(
            icon.isNull()
        )

    def test_launcher_edit_and_delete_refresh_quick_access(
        self,
    ):
        edit_source = inspect.getsource(
            DashboardPage
            .save_edited_launcher_card
        )

        delete_source = inspect.getsource(
            DashboardPage
            .delete_custom_card
        )

        for source in (
            edit_source,
            delete_source,
        ):
            self.assertIn(
                "refresh_quick_access_buttons",
                source,
            )

            self.assertIn(
                "force=True",
                source,
            )


if __name__ == "__main__":
    unittest.main()
