from __future__ import annotations

import unittest
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
)

from src.ui.presence_page import (
    PresencePage,
)


class PreviewProxy:
    _update_link_button_preview = (
        PresencePage._update_link_button_preview
    )

    def __init__(
        self,
        mode="custom",
    ):
        self.current_mode = mode

        self.show_link_buttons_box = (
            QCheckBox()
        )

        self.link_button_label_inputs = [
            QLineEdit(),
            QLineEdit(),
        ]

        self.link_button_url_inputs = [
            QLineEdit(),
            QLineEdit(),
        ]

        self.preview_link_buttons = [
            QLabel(),
            QLabel(),
        ]

        self.link_buttons_status = QLabel()


class PresenceStudioLinkButtonPreviewTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_enabled_two_buttons_render_in_order(
        self,
    ):
        proxy = PreviewProxy()

        proxy.show_link_buttons_box.setChecked(
            True
        )

        proxy.link_button_label_inputs[
            0
        ].setText(
            "Website"
        )

        proxy.link_button_url_inputs[
            0
        ].setText(
            "https://example.com"
        )

        proxy.link_button_label_inputs[
            1
        ].setText(
            "Discord"
        )

        proxy.link_button_url_inputs[
            1
        ].setText(
            "https://discord.com"
        )

        proxy._update_link_button_preview()

        self.assertEqual(
            proxy.preview_link_buttons[
                0
            ].text(),
            "Website",
        )

        self.assertEqual(
            proxy.preview_link_buttons[
                1
            ].text(),
            "Discord",
        )

        self.assertFalse(
            proxy.preview_link_buttons[
                0
            ].isHidden()
        )

        self.assertFalse(
            proxy.preview_link_buttons[
                1
            ].isHidden()
        )

        self.assertEqual(
            proxy.link_buttons_status.text(),
            "Visible to others on Discord",
        )

    def test_one_complete_button_only_shows_one(
        self,
    ):
        proxy = PreviewProxy()

        proxy.show_link_buttons_box.setChecked(
            True
        )

        proxy.link_button_label_inputs[
            0
        ].setText(
            "Website"
        )

        proxy.link_button_url_inputs[
            0
        ].setText(
            "https://example.com"
        )

        proxy._update_link_button_preview()

        self.assertFalse(
            proxy.preview_link_buttons[
                0
            ].isHidden()
        )

        self.assertTrue(
            proxy.preview_link_buttons[
                1
            ].isHidden()
        )

    def test_enabled_blank_rows_show_no_buttons_configured(
        self,
    ):
        proxy = PreviewProxy()

        proxy.show_link_buttons_box.setChecked(
            True
        )

        proxy._update_link_button_preview()

        self.assertTrue(
            proxy.preview_link_buttons[
                0
            ].isHidden()
        )

        self.assertTrue(
            proxy.preview_link_buttons[
                1
            ].isHidden()
        )

        self.assertEqual(
            proxy.link_buttons_status.text(),
            "No buttons configured",
        )

    def test_toggle_off_hides_preview_but_preserves_fields(
        self,
    ):
        proxy = PreviewProxy()

        proxy.link_button_label_inputs[
            0
        ].setText(
            "Website"
        )

        proxy.link_button_url_inputs[
            0
        ].setText(
            "https://example.com"
        )

        proxy.show_link_buttons_box.setChecked(
            False
        )

        proxy._update_link_button_preview()

        self.assertTrue(
            proxy.preview_link_buttons[
                0
            ].isHidden()
        )

        self.assertEqual(
            proxy.link_button_label_inputs[
                0
            ].text(),
            "Website",
        )

        self.assertEqual(
            proxy.link_button_url_inputs[
                0
            ].text(),
            "https://example.com",
        )

        self.assertEqual(
            proxy.link_buttons_status.text(),
            "Hidden on Discord - links saved",
        )

    def test_disabled_mode_is_always_buttonless(
        self,
    ):
        proxy = PreviewProxy(
            mode="disabled"
        )

        proxy.show_link_buttons_box.setChecked(
            True
        )

        proxy.link_button_label_inputs[
            0
        ].setText(
            "Website"
        )

        proxy.link_button_url_inputs[
            0
        ].setText(
            "https://example.com"
        )

        proxy._update_link_button_preview()

        self.assertTrue(
            proxy.preview_link_buttons[
                0
            ].isHidden()
        )

        self.assertTrue(
            proxy.preview_link_buttons[
                1
            ].isHidden()
        )

        self.assertEqual(
            proxy.link_buttons_status.text(),
            "Unavailable while Rich Presence is off",
        )

    def test_preview_controls_are_labels_not_buttons(
        self,
    ):
        proxy = PreviewProxy()

        for preview_button in (
            proxy.preview_link_buttons
        ):
            self.assertIsInstance(
                preview_button,
                QLabel,
            )

            self.assertNotIsInstance(
                preview_button,
                QPushButton,
            )

    def test_source_wires_live_editor_changes(
        self,
    ):
        source = Path(
            "src/ui/presence_page.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "self.show_link_buttons_box.toggled.connect(",
            source,
        )

        self.assertIn(
            "link_input.textChanged.connect(",
            source,
        )

        self.assertEqual(
            source.count(
                "self._update_link_button_preview()"
            ),
            1,
        )

    def test_preview_is_studio_only(
        self,
    ):
        presence_source = Path(
            "src/ui/presence_page.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        dashboard_source = Path(
            "src/ui/dashboard.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        shared_source = Path(
            "src/ui/discord_profile_preview.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            '"previewLinkButton"',
            presence_source,
        )

        self.assertNotIn(
            '"previewLinkButton"',
            dashboard_source,
        )

        self.assertNotIn(
            '"previewLinkButton"',
            shared_source,
        )


class PresenceStudioLinkButtonThemeTests(
    unittest.TestCase
):
    def test_preview_button_selector_uses_theme_dictionary(
        self,
    ):
        source = Path(
            "src/ui/presence_page.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        marker = (
            "QLabel#previewLinkButton {{"
        )

        start = source.index(
            marker
        )

        end = source.index(
            "\n            }}",
            start,
        )

        block = source[
            start:
            end
        ]

        self.assertIn(
            'color: {theme["text"]};',
            block,
        )

        self.assertIn(
            'background: {theme["card_alt"]};',
            block,
        )

        self.assertIn(
            'border: 1px solid {theme["border"]};',
            block,
        )

        self.assertNotIn(
            "color: {text};",
            block,
        )

        self.assertNotIn(
            "background: {card_alt};",
            block,
        )

        self.assertNotIn(
            "border: 1px solid {border};",
            block,
        )


if __name__ == "__main__":
    unittest.main()
