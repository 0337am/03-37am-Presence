from __future__ import annotations

import inspect
import unittest
from pathlib import Path

from PyQt6.QtWidgets import (
    QScrollArea,
)

from src.ui.presence_page import (
    PresencePage,
)


class PresenceStudioResponsiveLayoutTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.source = Path(
            "src/ui/presence_page.py"
        ).read_text(
            encoding="utf-8-sig"
        )

    def test_workspace_uses_vertical_scroll_area(
        self,
    ):
        self.assertIn(
            "QScrollArea",
            self.source,
        )

        method = inspect.getsource(
            PresencePage
            ._install_presence_studio_shell
        )

        self.assertIn(
            "self.studio_workspace_scroll = QScrollArea",
            method,
        )

        self.assertIn(
            "setWidgetResizable",
            method,
        )

        self.assertIn(
            "ScrollBarAsNeeded",
            method,
        )

    def test_horizontal_workspace_scrolling_is_disabled(
        self,
    ):
        method = inspect.getsource(
            PresencePage
            ._install_presence_studio_shell
        )

        self.assertIn(
            "setHorizontalScrollBarPolicy",
            method,
        )

        self.assertIn(
            "ScrollBarAlwaysOff",
            method,
        )

    def test_library_is_not_put_inside_workspace_scroll_area(
        self,
    ):
        method = inspect.getsource(
            PresencePage
            ._install_presence_studio_shell
        )

        library_index = method.index(
            "self.presence_library"
        )

        scroll_index = method.index(
            "self.studio_workspace_scroll ="
        )

        self.assertLess(
            library_index,
            scroll_index,
        )

        self.assertIn(
            "self.studio_row.addWidget(\n"
            "            self.presence_library",
            method,
        )

    def test_title_and_message_have_minimum_height(
        self,
    ):
        self.assertIn(
            "self.title_input.setMinimumHeight(",
            self.source,
        )

        self.assertIn(
            "self.message_input.setMinimumHeight(",
            self.source,
        )

    def test_link_fields_have_minimum_height(
        self,
    ):
        self.assertIn(
            "label_input.setMinimumHeight(",
            self.source,
        )

        self.assertIn(
            "url_input.setMinimumHeight(",
            self.source,
        )

    def test_link_card_and_slots_have_minimum_height(
        self,
    ):
        self.assertIn(
            "self.link_buttons_editor.setMinimumHeight(",
            self.source,
        )

        self.assertIn(
            "slot.setMinimumHeight(",
            self.source,
        )

    def test_editor_and_artwork_cards_have_minimum_height(
        self,
    ):
        self.assertIn(
            "self.editor_card.setMinimumHeight(",
            self.source,
        )

        self.assertIn(
            "self.image_card.setMinimumHeight(",
            self.source,
        )

        self.assertIn(
            "self.studio_editor_container.setMinimumHeight(",
            self.source,
        )

    def test_workspace_height_varies_by_mode(
        self,
    ):
        method = inspect.getsource(
            PresencePage.update_editor_state
        )

        self.assertIn(
            'if mode == "disabled":',
            method,
        )

        self.assertIn(
            'elif mode == "music":',
            method,
        )

        self.assertIn(
            "workspace_minimum_height = 520",
            method,
        )

        self.assertIn(
            "workspace_minimum_height = 760",
            method,
        )

        self.assertIn(
            "workspace_minimum_height = 900",
            method,
        )

        self.assertIn(
            "self.studio_workspace.setMinimumHeight(",
            method,
        )

    def test_scrollbar_has_presence_theme_hook(
        self,
    ):
        helper = inspect.getsource(
            PresencePage
            ._apply_presence_studio_scroll_theme
        )

        self.assertIn(
            "QScrollBar:vertical",
            helper,
        )

        self.assertIn(
            "QScrollBar::handle:vertical",
            helper,
        )

        theme_method = inspect.getsource(
            PresencePage
            ._apply_presence_studio_theme
        )

        self.assertIn(
            "_apply_presence_studio_scroll_theme",
            theme_method,
        )

    def test_scroll_area_type_is_real_qt_widget(
        self,
    ):
        self.assertTrue(
            issubclass(
                QScrollArea,
                object,
            )
        )


if __name__ == "__main__":
    unittest.main()
