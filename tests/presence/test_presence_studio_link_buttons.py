from __future__ import annotations

from pathlib import Path
import sys
import unittest

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLineEdit,
)

from src.discord.presence_link_buttons import (
    MAX_PRESENCE_LINK_LABEL_LENGTH,
    MAX_PRESENCE_LINK_URL_LENGTH,
    PresenceLinkButton,
    PresenceLinkButtonError,
)
from src.discord.presence_modes import (
    PresenceMode,
)
from src.ui.presence_page import (
    PresencePage,
)


def ensure_app():
    app = QApplication.instance()

    if app is None:
        app = QApplication(
            sys.argv
        )

    return app


class EditorProxy:
    _editor_presence_buttons = (
        PresencePage._editor_presence_buttons
    )
    _load_link_button_editor = (
        PresencePage._load_link_button_editor
    )
    _clear_link_button_editor = (
        PresencePage._clear_link_button_editor
    )
    current_editor_presence_mode = (
        PresencePage.current_editor_presence_mode
    )

    def __init__(
        self,
        mode="custom",
    ):
        self.current_mode = mode
        self.title_input = QLineEdit()
        self.message_input = QLineEdit()
        self.elapsed_box = QCheckBox()
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

        self.image_path = ""


class PresenceStudioLinkButtonTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = ensure_app()

    def test_editor_collects_enabled_button(
        self,
    ):
        proxy = EditorProxy()

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
            "https://example.com/"
        )

        mode = (
            proxy.current_editor_presence_mode()
        )

        self.assertTrue(
            mode.show_buttons
        )

        self.assertEqual(
            len(mode.buttons),
            1,
        )

        self.assertEqual(
            mode.buttons[0].label,
            "Website",
        )

    def test_hidden_button_configuration_is_retained(
        self,
    ):
        proxy = EditorProxy()

        proxy.show_link_buttons_box.setChecked(
            False
        )
        proxy.link_button_label_inputs[
            0
        ].setText(
            "Website"
        )
        proxy.link_button_url_inputs[
            0
        ].setText(
            "https://example.com/"
        )

        mode = (
            proxy.current_editor_presence_mode()
        )

        self.assertFalse(
            mode.show_buttons
        )

        self.assertEqual(
            len(mode.buttons),
            1,
        )

    def test_two_buttons_are_collected_in_order(
        self,
    ):
        proxy = EditorProxy()

        proxy.show_link_buttons_box.setChecked(
            True
        )

        values = (
            (
                "Website",
                "https://example.com/",
            ),
            (
                "Discord",
                "https://discord.com/",
            ),
        )

        for index, (
            label,
            url,
        ) in enumerate(values):
            proxy.link_button_label_inputs[
                index
            ].setText(
                label
            )

            proxy.link_button_url_inputs[
                index
            ].setText(
                url
            )

        mode = (
            proxy.current_editor_presence_mode()
        )

        self.assertEqual(
            tuple(
                button.label
                for button in mode.buttons
            ),
            (
                "Website",
                "Discord",
            ),
        )

    def test_half_filled_button_is_rejected(
        self,
    ):
        proxy = EditorProxy()

        proxy.link_button_label_inputs[
            0
        ].setText(
            "Website"
        )

        with self.assertRaises(
            PresenceLinkButtonError
        ):
            proxy.current_editor_presence_mode()

    def test_unsafe_url_is_rejected(
        self,
    ):
        proxy = EditorProxy()

        proxy.link_button_label_inputs[
            0
        ].setText(
            "Unsafe"
        )
        proxy.link_button_url_inputs[
            0
        ].setText(
            "file:///secret"
        )

        with self.assertRaises(
            PresenceLinkButtonError
        ):
            proxy.current_editor_presence_mode()

    def test_loader_restores_visibility_and_buttons(
        self,
    ):
        proxy = EditorProxy()

        mode = PresenceMode(
            mode="custom",
            show_buttons=True,
            buttons=(
                PresenceLinkButton(
                    label="Website",
                    url=(
                        "https://example.com/"
                    ),
                ),
                PresenceLinkButton(
                    label="Discord",
                    url=(
                        "https://discord.com/"
                    ),
                ),
            ),
        )

        proxy._load_link_button_editor(
            mode
        )

        self.assertTrue(
            proxy.show_link_buttons_box.isChecked()
        )

        self.assertEqual(
            proxy.link_button_label_inputs[
                0
            ].text(),
            "Website",
        )

        self.assertEqual(
            proxy.link_button_label_inputs[
                1
            ].text(),
            "Discord",
        )

    def test_loader_clears_unused_second_button(
        self,
    ):
        proxy = EditorProxy()

        proxy.link_button_label_inputs[
            1
        ].setText(
            "Old"
        )
        proxy.link_button_url_inputs[
            1
        ].setText(
            "https://old.example/"
        )

        proxy._load_link_button_editor(
            PresenceMode(
                mode="custom",
                buttons=(
                    PresenceLinkButton(
                        label="Only",
                        url=(
                            "https://example.com/"
                        ),
                    ),
                ),
            )
        )

        self.assertEqual(
            proxy.link_button_label_inputs[
                1
            ].text(),
            "",
        )

        self.assertEqual(
            proxy.link_button_url_inputs[
                1
            ].text(),
            "",
        )

    def test_clear_editor_removes_draft(
        self,
    ):
        proxy = EditorProxy()

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
            "https://example.com/"
        )

        proxy._clear_link_button_editor()

        self.assertFalse(
            proxy.show_link_buttons_box.isChecked()
        )

        self.assertEqual(
            proxy.link_button_label_inputs[
                0
            ].text(),
            "",
        )

        self.assertEqual(
            proxy.link_button_url_inputs[
                0
            ].text(),
            "",
        )

    def test_music_collects_buttons_and_disabled_ignores_stale_editor_links(
        self,
    ):
        music = EditorProxy(
            mode="music"
        )

        music.show_link_buttons_box.setChecked(
            True
        )

        music.link_button_label_inputs[
            0
        ].setText(
            "Website"
        )

        music.link_button_url_inputs[
            0
        ].setText(
            "https://example.com/"
        )

        music_mode = (
            music.current_editor_presence_mode()
        )

        self.assertTrue(
            music_mode.show_buttons
        )

        self.assertEqual(
            len(
                music_mode.buttons
            ),
            1,
        )

        disabled = EditorProxy(
            mode="disabled"
        )

        disabled.show_link_buttons_box.setChecked(
            True
        )

        disabled.link_button_label_inputs[
            0
        ].setText(
            "Incomplete"
        )

        disabled_mode = (
            disabled.current_editor_presence_mode()
        )

        self.assertFalse(
            disabled_mode.show_buttons
        )

        self.assertEqual(
            disabled_mode.buttons,
            (),
        )

    def test_source_builds_two_bounded_fields(
        self,
    ):
        source = Path(
            "src/ui/presence_page.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "presenceStudioLinkButtonsCard",
            source,
        )

        self.assertIn(
            "presenceStudioLinkButtonSlot",
            source,
        )

        self.assertIn(
            "self.show_link_buttons_box",
            source,
        )

        self.assertIn(
            "self.link_button_label_inputs",
            source,
        )

        self.assertIn(
            "self.link_button_url_inputs",
            source,
        )

        self.assertIn(
            "MAX_PRESENCE_LINK_LABEL_LENGTH",
            source,
        )

        self.assertIn(
            "MAX_PRESENCE_LINK_URL_LENGTH",
            source,
        )

        self.assertNotIn(
            "label_input.setMaximumWidth(",
            source,
        )

    def test_discord_limits_remain_expected(
        self,
    ):
        self.assertEqual(
            MAX_PRESENCE_LINK_LABEL_LENGTH,
            32,
        )

        self.assertEqual(
            MAX_PRESENCE_LINK_URL_LENGTH,
            512,
        )

    def test_link_button_help_explains_discord_self_view_limitation(
        self,
    ):
        from pathlib import Path

        source = Path(
            "src/ui/presence_page.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "Discord hides your own Rich Presence buttons",
            source,
        )

        self.assertIn(
            "but other users can see them.",
            source,
        )

    def test_library_and_mode_load_paths_restore_buttons(
        self,
    ):
        import inspect

        for method_name in (
            "open_library_preset",
            "apply_selected_preset",
            "load_mode",
        ):
            method = getattr(
                PresencePage,
                method_name,
            )

            method_source = inspect.getsource(
                method
            )

            self.assertIn(
                "_load_link_button_editor",
                method_source,
            )

    def test_new_presence_clears_button_editor(
        self,
    ):
        import inspect

        source = inspect.getsource(
            PresencePage.start_new_library_presence
        )

        self.assertIn(
            "_clear_link_button_editor",
            source,
        )

    def test_standalone_card_supports_music_but_not_disabled(
        self,
    ):
        import inspect

        source = inspect.getsource(
            PresencePage.update_editor_state
        )

        self.assertIn(
            'mode != "disabled"',
            source,
        )

        self.assertIn(
            "self.link_buttons_editor.setVisible(",
            source,
        )

        self.assertIn(
            "save_button.setVisible(",
            source,
        )

        collector = inspect.getsource(
            PresencePage.current_editor_presence_mode
        )

        self.assertIn(
            'if mode == "disabled":',
            collector,
        )

        self.assertNotIn(
            '"music",\n            "disabled"',
            collector,
        )

    def test_custom_reset_removes_link_button_keys(
        self,
    ):
        import inspect

        source = inspect.getsource(
            PresencePage.reset_custom_presence
        )

        self.assertIn(
            '"presence/custom/show_buttons"',
            source,
        )

        self.assertIn(
            '"presence/custom/buttons"',
            source,
        )


if __name__ == "__main__":
    unittest.main()
