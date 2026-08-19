import ast
import unittest
from types import SimpleNamespace

from src.ui.presence_page import (
    PresencePage,
)
from tests.repo_paths import (
    REPO_ROOT,
)


PAGE_PATH = (
    REPO_ROOT
    / "src"
    / "ui"
    / "presence_page.py"
)


class PresenceStudioLoopCountUiTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.source = PAGE_PATH.read_text(
            encoding="utf-8-sig"
        )

    def test_constructs_music_loop_checkbox(
        self,
    ):
        self.assertIn(
            "Show song loop count on Discord",
            self.source,
        )

        self.assertIn(
            '"loopCountBox"',
            self.source,
        )

    def test_checkbox_is_added_to_context_card_layout(
        self,
    ):
        tree = ast.parse(
            self.source
        )

        context_layout_names = set()

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Assign,
            ):
                continue

            if len(
                node.targets
            ) != 1:
                continue

            target = node.targets[0]

            if not isinstance(
                target,
                ast.Name,
            ):
                continue

            if not isinstance(
                node.value,
                ast.Call,
            ):
                continue

            if not isinstance(
                node.value.func,
                ast.Name,
            ):
                continue

            if (
                node.value.func.id
                != "QVBoxLayout"
            ):
                continue

            for arg in node.value.args:
                if (
                    isinstance(
                        arg,
                        ast.Attribute,
                    )
                    and arg.attr
                    == "studio_context_card"
                ):
                    context_layout_names.add(
                        target.id
                    )

        self.assertEqual(
            len(
                context_layout_names
            ),
            1,
        )

        layout_name = next(
            iter(
                context_layout_names
            )
        )

        found = False

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            if not isinstance(
                node.func,
                ast.Attribute,
            ):
                continue

            if (
                node.func.attr
                != "addWidget"
            ):
                continue

            if not (
                isinstance(
                    node.func.value,
                    ast.Name,
                )
                and node.func.value.id
                == layout_name
            ):
                continue

            if any(
                isinstance(
                    arg,
                    ast.Attribute,
                )
                and arg.attr
                == "loop_count_box"
                for arg in node.args
            ):
                found = True

        self.assertTrue(
            found
        )

    def test_checkbox_is_music_only(
        self,
    ):
        self.assertIn(
            "loop_count_box.setVisible(",
            self.source,
        )

        self.assertIn(
            "loop_count_box.setEnabled(",
            self.source,
        )

        self.assertIn(
            'mode == "music"',
            self.source,
        )

    def test_editor_collects_music_loop_setting(
        self,
    ):
        self.assertIn(
            "show_loop_count=show_loop_count",
            self.source,
        )

        self.assertIn(
            "loop_count_box.isChecked()",
            self.source,
        )

    def test_missing_checkbox_is_backward_compatible(
        self,
    ):
        proxy = SimpleNamespace(
            current_mode="music",
            title_input=SimpleNamespace(
                text=lambda: ""
            ),
            message_input=SimpleNamespace(
                text=lambda: ""
            ),
            image_path="",
            elapsed_box=SimpleNamespace(
                isChecked=lambda: False
            ),
            show_link_buttons_box=SimpleNamespace(
                isChecked=lambda: False
            ),
            _editor_presence_buttons=(
                lambda: ()
            ),
        )

        mode = (
            PresencePage
            .current_editor_presence_mode(
                proxy
            )
        )

        self.assertFalse(
            mode.show_loop_count
        )

    def test_present_checked_checkbox_is_collected(
        self,
    ):
        proxy = SimpleNamespace(
            current_mode="music",
            title_input=SimpleNamespace(
                text=lambda: ""
            ),
            message_input=SimpleNamespace(
                text=lambda: ""
            ),
            image_path="",
            elapsed_box=SimpleNamespace(
                isChecked=lambda: False
            ),
            loop_count_box=SimpleNamespace(
                isChecked=lambda: True
            ),
            show_link_buttons_box=SimpleNamespace(
                isChecked=lambda: False
            ),
            _editor_presence_buttons=(
                lambda: ()
            ),
        )

        mode = (
            PresencePage
            .current_editor_presence_mode(
                proxy
            )
        )

        self.assertTrue(
            mode.show_loop_count
        )

    def test_checkbox_safely_mirrors_all_restore_sites(
        self,
    ):
        self.assertEqual(
            self.source.count(
                "_loop_count_box.setChecked("
            ),
            4,
        )

        self.assertEqual(
            self.source.count(
                "_loop_count_box.blockSignals("
            ),
            8,
        )

        self.assertGreaterEqual(
            self.source.count(
                '"loop_count_box"'
            ),
            10,
        )

    def test_checkbox_uses_presence_theme(
        self,
    ):
        self.assertEqual(
            self.source.count(
                "QCheckBox#loopCountBox"
            ),
            4,
        )

    def test_checkbox_updates_preview(
        self,
    ):
        self.assertIn(
            "self.loop_count_box.toggled.connect(\n"
            "            self.update_preview",
            self.source,
        )

    def test_switch_to_music_reloads_saved_music_presence(
        self,
    ):
        self.assertEqual(
            self.source.count(
                'self.controller.load_mode(\n'
                '                "music"\n'
                '            )'
            ),
            2,
        )

    def test_blank_music_constructor_no_longer_overwrites_setting(
        self,
    ):
        self.assertNotIn(
            'PresenceMode(\n'
            '                mode="music"\n'
            '            )',
            self.source,
        )

    def test_ui_patch_does_not_render_discord_loop_text(
        self,
    ):
        self.assertNotIn(
            "Loop ×",
            self.source,
        )


if __name__ == "__main__":
    unittest.main()