from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
)

from src.ui.custom_cards import (
    LAUNCHER_TARGET_FOLDER,
    create_launcher_card,
    create_link_card,
)
from src.ui.dashboard import DashboardPage
from src.ui.launcher_cards import (
    LauncherCardWidget,
)
from src.ui.link_cards import (
    LinkCardWidget,
)


_APP = QApplication.instance()

if _APP is None:
    _APP = QApplication([])


class _ThemeManagerStub:
    def theme(self):
        return {
            "background": "#101014",
            "card": "#18181d",
            "card_alt": "#222229",
            "border": "#34343e",
            "text": "#f5f5f7",
            "muted": "#a0a0ad",
            "accent": "#a970ff",
            "warning": "#f0a45d",
        }


class _DashboardFactoryStub:
    def __init__(self):
        self.dashboard_canvas = QWidget()
        self.theme_manager = (
            _ThemeManagerStub()
        )
        self.opened_urls = []
        self.opened_launcher_ids = []

    def open_link_card_url(
        self,
        url,
    ):
        self.opened_urls.append(url)

    def open_launcher_card_target(
        self,
        card_id,
    ):
        self.opened_launcher_ids.append(
            card_id
        )

    def create_link_card_widget(
        self,
        card,
    ):
        return (
            DashboardPage
            .create_link_card_widget(
                self,
                card,
            )
        )

    def create_launcher_card_widget(
        self,
        card,
    ):
        return (
            DashboardPage
            .create_launcher_card_widget(
                self,
                card,
            )
        )


class DashboardLauncherIntegrationTests(
    unittest.TestCase
):
    def test_factory_creates_enabled_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            card = create_launcher_card(
                target=directory,
                target_kind=(
                    LAUNCHER_TARGET_FOLDER
                ),
                title="Projects",
            )

            factory = _DashboardFactoryStub()

            widget = (
                DashboardPage
                .create_custom_card_widget(
                    factory,
                    card,
                )
            )

            self.assertIsInstance(
                widget,
                LauncherCardWidget,
            )
            self.assertTrue(
                widget.launch_enabled
            )
            self.assertTrue(
                widget.open_button.isEnabled()
            )

            widget.open_button.click()

            self.assertEqual(
                factory.opened_launcher_ids,
                [card.card_id],
            )

            widget.close()
            factory.dashboard_canvas.close()

    def test_link_factory_still_works(self):
        card = create_link_card(
            url="https://example.com",
            title="Example",
        )

        factory = _DashboardFactoryStub()

        widget = (
            DashboardPage
            .create_custom_card_widget(
                factory,
                card,
            )
        )

        self.assertIsInstance(
            widget,
            LinkCardWidget,
        )

        widget.close()
        factory.dashboard_canvas.close()

    def test_unknown_custom_object_is_rejected(self):
        factory = _DashboardFactoryStub()

        with self.assertRaises(TypeError):
            (
                DashboardPage
                .create_custom_card_widget(
                    factory,
                    object(),
                )
            )

        factory.dashboard_canvas.close()

    def test_dashboard_contains_launcher_routes(self):
        import inspect

        source = inspect.getsource(
            DashboardPage
        )

        for required_text in [
            '"Launcher card"',
            'f"Edit {card_kind} card"',
            'f"Duplicate {card_kind} card"',
            "def add_launcher_card",
            "def edit_custom_card",
            "def edit_custom_launcher_card",
            "def save_edited_launcher_card",
            "def duplicate_custom_card",
            "def duplicate_custom_launcher_card",
            "widget.launch_requested.connect",
            "widget.set_launch_enabled(True)",
            "def open_launcher_card_target",
        ]:
            self.assertIn(
                required_text,
                source,
            )

        self.assertNotIn(
            "shell=True",
            source,
        )


if __name__ == "__main__":
    unittest.main()
