from __future__ import annotations

import inspect
import unittest
from dataclasses import replace
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QFrame,
)

from src.ui.dashboard import (
    DashboardPage,
)
from src.ui.dashboard_layout import (
    preset_layout,
)


def queue_layout(
    *,
    visible=False,
    locked=False,
):
    base = preset_layout(
        "Default"
    )

    cards = tuple(
        replace(
            card,
            visible=bool(
                visible
            ),
        )
        if card.card_id == "queue"
        else card
        for card in base.cards
    )

    return replace(
        base,
        cards=cards,
        locked=bool(
            locked
        ),
        preset="Custom",
    )


class FakeAction:

    def __init__(
        self,
    ):
        self.visible = None
        self.enabled = None

    def setVisible(
        self,
        value,
    ):
        self.visible = bool(
            value
        )

    def setEnabled(
        self,
        value,
    ):
        self.enabled = bool(
            value
        )


class QueueActionHarness:

    def __init__(
        self,
        layout,
    ):
        self.dashboard_layout_state = (
            layout
        )

        self.visibility_calls = []
        self.sync_calls = 0

    def set_dashboard_card_visibility(
        self,
        card_id,
        visible,
    ):
        self.visibility_calls.append(
            (
                card_id,
                visible,
            )
        )

    def sync_dashboard_layout_controls(
        self,
    ):
        self.sync_calls += 1


class QueueSyncHarness:

    def __init__(
        self,
        layout,
    ):
        self.dashboard_layout_state = (
            layout
        )

        self.layout_add_queue_action = (
            FakeAction()
        )


class DashboardQueueAddCardTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(
        cls,
    ):
        app = QApplication.instance()

        if app is None:
            app = QApplication([])

        cls.app = app

    def test_queue_shell_builder_creates_inert_card(
        self,
    ):
        harness = type(
            "Harness",
            (),
            {},
        )()

        DashboardPage.build_queue_card(
            harness
        )

        self.addCleanup(
            harness.queue_card.deleteLater
        )

        self.assertIsInstance(
            harness.queue_card,
            QFrame,
        )

        self.assertEqual(
            harness.queue_card.objectName(),
            "queueCard",
        )

        self.assertGreaterEqual(
            harness.queue_card.minimumHeight(),
            270,
        )

        labels = [
            label.text()
            for label in (
                harness.queue_card
                .findChildren(
                    QLabel
                )
            )
        ]

        self.assertIn(
            "SPOTIFY QUEUE",
            labels,
        )

        self.assertIn(
            (
                "Queue content will "
                "appear here."
            ),
            labels,
        )

    def test_add_queue_card_reveals_hidden_entry(
        self,
    ):
        harness = QueueActionHarness(
            queue_layout(
                visible=False,
                locked=False,
            )
        )

        DashboardPage.add_queue_card(
            harness
        )

        self.assertEqual(
            harness.visibility_calls,
            [
                (
                    "queue",
                    True,
                ),
            ],
        )

        self.assertEqual(
            harness.sync_calls,
            0,
        )

    def test_add_queue_card_cannot_duplicate_visible_queue(
        self,
    ):
        harness = QueueActionHarness(
            queue_layout(
                visible=True,
                locked=False,
            )
        )

        DashboardPage.add_queue_card(
            harness
        )

        self.assertEqual(
            harness.visibility_calls,
            [],
        )

        self.assertEqual(
            harness.sync_calls,
            1,
        )

    def test_add_queue_card_respects_layout_lock(
        self,
    ):
        harness = QueueActionHarness(
            queue_layout(
                visible=False,
                locked=True,
            )
        )

        DashboardPage.add_queue_card(
            harness
        )

        self.assertEqual(
            harness.visibility_calls,
            [],
        )

        self.assertEqual(
            harness.sync_calls,
            1,
        )

    def test_add_queue_action_tracks_visibility_and_lock(
        self,
    ):
        cases = (
            (
                False,
                False,
                True,
                True,
            ),
            (
                False,
                True,
                True,
                False,
            ),
            (
                True,
                False,
                False,
                False,
            ),
            (
                True,
                True,
                False,
                False,
            ),
        )

        for (
            visible,
            locked,
            expected_visible,
            expected_enabled,
        ) in cases:
            with self.subTest(
                visible=visible,
                locked=locked,
            ):
                harness = QueueSyncHarness(
                    queue_layout(
                        visible=visible,
                        locked=locked,
                    )
                )

                (
                    DashboardPage
                    .sync_dashboard_add_queue_action(
                        harness
                    )
                )

                self.assertEqual(
                    (
                        harness
                        .layout_add_queue_action
                        .visible
                    ),
                    expected_visible,
                )

                self.assertEqual(
                    (
                        harness
                        .layout_add_queue_action
                        .enabled
                    ),
                    expected_enabled,
                )

    def test_build_ui_registers_queue_widget(
        self,
    ):
        source = inspect.getsource(
            DashboardPage.build_ui
        )

        self.assertIn(
            "self.build_queue_card()",
            source,
        )

        self.assertIn(
            '"queue"',
            source,
        )

        self.assertIn(
            "self.queue_card",
            source,
        )

    def test_add_card_menu_wires_spotify_queue_action(
        self,
    ):
        source = inspect.getsource(
            (
                DashboardPage
                .build_dashboard_layout_toolbar
            )
        )

        self.assertIn(
            "layout_add_queue_action",
            source,
        )

        self.assertIn(
            '"Spotify Queue"',
            source,
        )

        self.assertIn(
            "DashboardPage.add_queue_card",
            source,
        )

    def test_layout_control_sync_updates_queue_add_action(
        self,
    ):
        source = inspect.getsource(
            (
                DashboardPage
                .sync_dashboard_layout_controls
            )
        )

        self.assertIn(
            (
                "DashboardPage."
                "sync_dashboard_add_queue_action"
            ),
            source,
        )

    def test_queue_shell_uses_existing_dashboard_card_style(
        self,
    ):
        source_path = Path(
            inspect.getsourcefile(
                DashboardPage
            )
        )

        source = source_path.read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "QFrame#queueCard {{",
            source,
        )

        self.assertIn(
            (
                'QFrame#queueCard'
                '[dashboardEditing="true"],'
            ),
            source,
        )


if __name__ == "__main__":
    unittest.main()
