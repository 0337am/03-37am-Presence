import inspect
import os
import unittest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtWidgets import QApplication

from src.ui.dashboard import DashboardPage


class QuickAccessIconTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_known_semantic_icons_render(self):
        for icon_key in (
            "afk",
            "custom",
            "presets",
            "settings",
        ):
            with self.subTest(
                icon_key=icon_key
            ):
                icon = (
                    DashboardPage
                    ._quick_access_icon(
                        icon_key,
                        "#ffffff",
                    )
                )

                self.assertFalse(
                    icon.isNull()
                )

    def test_unknown_icon_is_safely_empty(self):
        icon = (
            DashboardPage
            ._quick_access_icon(
                "unknown",
                "#ffffff",
            )
        )

        self.assertTrue(
            icon.isNull()
        )

    def test_refresh_uses_semantic_icon_keys(self):
        source = inspect.getsource(
            DashboardPage
            .refresh_quick_access_buttons
        )

        for marker in (
            '"afk"',
            '"custom"',
            '"presets"',
            '"settings"',
            "icon_key=",
        ):
            self.assertIn(
                marker,
                source,
            )

        for legacy in (
            "chr(0x2659)",
            "chr(0x270E)",
            "chr(0x2605)",
            "chr(0x2699)",
        ):
            self.assertNotIn(
                legacy,
                source,
            )

    def test_header_uses_clean_text_only_heading(self):
        source = inspect.getsource(
            DashboardPage
            .build_quick_access_card
        )

        self.assertIn(
            '"QUICK ACCESS"',
            source,
        )

        self.assertNotIn(
            "\u03df  QUICK ACCESS",
            source,
        )

    def test_refresh_uses_model_icon_key_without_legacy_nameerror(
        self,
    ):
        source = inspect.getsource(
            DashboardPage
            .refresh_quick_access_buttons
        )

        self.assertIn(
            "quick_access_item.icon_key",
            source,
        )

        self.assertNotIn(
            "icon_key=icon,",
            source,
        )


    def test_icon_refresh_sets_real_button_icon(self):
        source = inspect.getsource(
            DashboardPage
            ._refresh_quick_access_icons
        )

        self.assertIn(
            "button.setIcon(",
            source,
        )

        self.assertIn(
            "_quick_access_icon(",
            source,
        )

    def test_responsive_text_no_longer_embeds_icon_glyph(self):
        source = inspect.getsource(
            DashboardPage
            .update_quick_access_layout
        )

        self.assertIn(
            'text = item["title"]',
            source,
        )

        self.assertNotIn(
            "item['icon']",
            source,
        )

        self.assertNotIn(
            'item["icon"]',
            source,
        )


if __name__ == "__main__":
    unittest.main()
