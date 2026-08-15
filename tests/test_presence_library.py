from dataclasses import dataclass
from pathlib import Path
import ast
import sys
import unittest

from PyQt6.QtWidgets import (
    QApplication,
)

from src.ui.presence_library import (
    PresenceLibraryCard,
    PresenceLibraryPanel,
)


@dataclass(frozen=True)
class FakePreset:
    preset_id: str
    name: str
    mode: str
    title: str = ""
    message: str = ""
    image_path: str = ""
    show_elapsed: bool = False
    pinned: bool = False


class PresenceLibraryTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication(
                sys.argv
            )
        )

    def make_presets(
        self,
    ):
        return (
            FakePreset(
                preset_id="sleep",
                name="Sleeping",
                mode="sleep",
                title="Probably asleep",
                message="Do not wake me",
            ),
            FakePreset(
                preset_id="away",
                name="Away",
                mode="afk",
                title="Away right now",
                message="Replies not guaranteed",
                pinned=True,
            ),
            FakePreset(
                preset_id="work",
                name="Working",
                mode="working",
                title="Locked in",
                message="Replies may be slow",
            ),
        )

    def test_panel_has_library_controls(self):
        panel = PresenceLibraryPanel()

        self.assertEqual(
            panel.heading.text(),
            "PRESENCE LIBRARY",
        )

        self.assertTrue(
            panel.search_input.isClearButtonEnabled()
        )

        self.assertEqual(
            panel.create_button.text(),
            "+ New Presence",
        )

        panel.deleteLater()

    def test_filter_control_reserves_dropdown_space(self):
        panel = PresenceLibraryPanel()

        self.assertGreaterEqual(
            panel.filter_box.minimumWidth(),
            100,
        )

        panel.apply_theme(
            {}
        )

        style = panel.styleSheet()

        self.assertIn(
            "padding-right: 30px",
            style,
        )

        self.assertIn(
            "presenceLibraryFilter::drop-down",
            style,
        )

        self.assertIn(
            "width: 26px",
            style,
        )

        panel.deleteLater()

    def test_pinned_presets_sort_first(self):
        panel = PresenceLibraryPanel()

        panel.set_presets(
            self.make_presets()
        )

        first = (
            panel.grid
            .itemAtPosition(
                0,
                0,
            )
            .widget()
        )

        self.assertIsInstance(
            first,
            PresenceLibraryCard,
        )

        self.assertEqual(
            first.preset_id,
            "away",
        )

        panel.deleteLater()

    def test_search_filters_title_and_message(self):
        panel = PresenceLibraryPanel()

        panel.set_presets(
            self.make_presets()
        )

        panel.search_input.setText(
            "wake"
        )

        self.app.processEvents()

        self.assertEqual(
            set(
                panel.cards.keys()
            ),
            {
                "sleep",
            },
        )

        panel.deleteLater()

    def test_pinned_filter_only_shows_pinned(self):
        panel = PresenceLibraryPanel()

        panel.set_presets(
            self.make_presets()
        )

        index = panel.filter_box.findData(
            "pinned"
        )

        self.assertGreaterEqual(
            index,
            0,
        )

        panel.filter_box.setCurrentIndex(
            index
        )

        self.app.processEvents()

        self.assertEqual(
            set(
                panel.cards.keys()
            ),
            {
                "away",
            },
        )

        panel.deleteLater()

    def test_mode_filter(self):
        panel = PresenceLibraryPanel()

        panel.set_presets(
            self.make_presets()
        )

        index = panel.filter_box.findData(
            "working"
        )

        panel.filter_box.setCurrentIndex(
            index
        )

        self.app.processEvents()

        self.assertEqual(
            set(
                panel.cards.keys()
            ),
            {
                "work",
            },
        )

        panel.deleteLater()

    def test_selection_signal_updates_selected_card(self):
        panel = PresenceLibraryPanel()

        panel.set_presets(
            self.make_presets()
        )

        received = []

        panel.preset_selected.connect(
            received.append
        )

        panel.cards[
            "sleep"
        ].selected.emit(
            "sleep"
        )

        self.app.processEvents()

        self.assertEqual(
            panel.selected_id,
            "sleep",
        )

        self.assertEqual(
            received,
            [
                "sleep",
            ],
        )

        panel.deleteLater()

    def test_apply_signal_is_forwarded(self):
        panel = PresenceLibraryPanel()

        panel.set_presets(
            self.make_presets()
        )

        received = []

        panel.preset_apply_requested.connect(
            received.append
        )

        panel.cards[
            "away"
        ].apply_button.click()

        self.app.processEvents()

        self.assertEqual(
            received,
            [
                "away",
            ],
        )

        panel.deleteLater()

    def test_selected_id_is_visual_state(self):
        panel = PresenceLibraryPanel()

        panel.set_presets(
            self.make_presets(),
            selected_id="work",
        )

        self.assertTrue(
            panel.cards[
                "work"
            ].property(
                "selected"
            )
        )

        panel.deleteLater()

    def test_pinned_card_uses_compact_marker(self):
        card = PresenceLibraryCard(
            FakePreset(
                preset_id="away",
                name="Away",
                mode="afk",
                pinned=True,
            )
        )

        self.assertEqual(
            card.pin_badge.text(),
            "PIN",
        )

        self.assertEqual(
            card.pin_badge.toolTip(),
            "Pinned Presence",
        )

        self.assertTrue(
            card.pin_badge.isVisible()
            or not card.isVisible()
        )

        self.assertEqual(
            card.artwork.width(),
            96,
        )

        self.assertEqual(
            card.artwork.height(),
            96,
        )

        card.deleteLater()

    def test_library_disables_horizontal_scrolling(self):
        source = Path(
            "src/ui/presence_library.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "ScrollBarAlwaysOff",
            source,
        )

    def test_missing_artwork_has_safe_fallback(self):
        card = PresenceLibraryCard(
            FakePreset(
                preset_id="missing",
                name="Missing",
                mode="custom",
                image_path=(
                    str(
                        Path(
                            "__definitely_missing__.png"
                        )
                    )
                ),
            )
        )

        self.assertTrue(
            card.artwork.text()
        )

        self.assertTrue(
            card.artwork.pixmap().isNull()
        )

        card.deleteLater()

    def test_component_has_no_storage_or_discord_side_effects(self):
        source = Path(
            "src/ui/presence_library.py"
        ).read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source
        )

        forbidden = (
            "PresencePresetStore",
            "PresenceController",
            "pypresence",
            "QSettings",
            "requests",
            "urllib",
            "rpc.update",
            "update_custom",
        )

        for token in forbidden:
            self.assertNotIn(
                token,
                source,
            )

        self.assertIsNotNone(
            tree
        )

    def test_card_exposes_compact_action_menu(self):
        card = PresenceLibraryCard(
            FakePreset(
                preset_id="away",
                name="Away",
                mode="afk",
                pinned=True,
            )
        )

        self.assertEqual(
            card.open_button.text(),
            "Edit",
        )

        self.assertEqual(
            card.menu_button.text(),
            "...",
        )

        self.assertEqual(
            card.menu_button.toolTip(),
            "Presence actions",
        )

        card.deleteLater()

    def test_card_action_signal_uses_preset_id_and_action(self):
        card = PresenceLibraryCard(
            FakePreset(
                preset_id="away",
                name="Away",
                mode="afk",
            )
        )

        received = []

        card.action_requested.connect(
            lambda preset_id, action:
            received.append(
                (
                    preset_id,
                    action,
                )
            )
        )

        card._emit_action(
            "duplicate"
        )

        self.assertEqual(
            received,
            [
                (
                    "away",
                    "duplicate",
                ),
            ],
        )

        card.deleteLater()

    def test_panel_forwards_card_actions(self):
        panel = PresenceLibraryPanel()

        panel.set_presets(
            self.make_presets()
        )

        received = []

        panel.preset_action_requested.connect(
            lambda preset_id, action:
            received.append(
                (
                    preset_id,
                    action,
                )
            )
        )

        panel.cards[
            "away"
        ].action_requested.emit(
            "away",
            "delete",
        )

        self.app.processEvents()

        self.assertEqual(
            received,
            [
                (
                    "away",
                    "delete",
                ),
            ],
        )

        panel.deleteLater()


if __name__ == "__main__":
    unittest.main()
