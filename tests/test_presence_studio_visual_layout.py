from pathlib import Path
import ast
import unittest


class PresenceStudioVisualLayoutTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(
            "src/ui/presence_page.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        cls.tree = ast.parse(
            cls.source
        )

    def method_source(
        self,
        name,
    ):
        lines = self.source.splitlines()

        for node in ast.walk(
            self.tree
        ):
            if (
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and node.name == name
            ):
                return "\n".join(
                    lines[
                        node.lineno - 1:
                        node.end_lineno
                    ]
                )

        raise AssertionError(
            f"Method not found: {name}"
        )

    def test_old_full_width_mode_card_is_hidden(self):
        method = self.method_source(
            "_install_presence_studio_shell"
        )

        self.assertIn(
            "self.mode_card.setVisible(",
            method,
        )

    def test_workspace_has_current_presence_hierarchy(self):
        method = self.method_source(
            "_install_presence_studio_shell"
        )

        for token in (
            "presenceStudioWorkspace",
            "CURRENT PRESENCE",
            "presenceStudioModeBadge",
            "presenceStudioActionBar",
        ):
            self.assertIn(
                token,
                method,
            )

    def test_mode_rail_uses_real_mode_definitions(self):
        method = self.method_source(
            "_install_presence_studio_shell"
        )

        self.assertIn(
            "for mode, display_name in MODE_NAMES.items():",
            method,
        )

        self.assertIn(
            "self.studio_mode_buttons",
            method,
        )

    def test_mode_rail_reuses_hidden_mode_box_engine(self):
        method = self.method_source(
            "select_studio_mode"
        )

        self.assertIn(
            "self.mode_box.findData(",
            method,
        )

        self.assertIn(
            "self.mode_box.setCurrentIndex(",
            method,
        )

    def test_preview_has_bounded_hero_height(self):
        method = self.method_source(
            "_install_presence_studio_shell"
        )

        self.assertIn(
            "self.preview_card.setMaximumHeight(",
            method,
        )

    def test_editor_and_artwork_are_contained(self):
        method = self.method_source(
            "_install_presence_studio_shell"
        )

        self.assertIn(
            "self.studio_editor_container",
            method,
        )

        self.assertIn(
            "self.editor_card",
            method,
        )

        self.assertIn(
            "self.image_card",
            method,
        )

    def test_music_and_disabled_use_context_panel(self):
        method = self.method_source(
            "update_editor_state"
        )

        self.assertIn(
            "AUTOMATIC MUSIC PRESENCE",
            method,
        )

        self.assertIn(
            "RICH PRESENCE IS OFF",
            method,
        )

        self.assertIn(
            "context_card.setVisible(",
            method,
        )

    def test_action_visibility_tracks_mode(self):
        method = self.method_source(
            "update_editor_state"
        )

        self.assertIn(
            'mode == "custom"',
            method,
        )

        self.assertIn(
            'mode != "music"',
            method,
        )

        self.assertIn(
            "save_button.setVisible(",
            method,
        )

    def test_music_preview_never_keeps_invalid_custom_artwork(self):
        method = self.method_source(
            "update_preview"
        )

        music_branch = method.split(
            'if mode == "music":',
            1,
        )[1].split(
            'if mode == "disabled":',
            1,
        )[0]

        self.assertIn(
            "self.preview_image.clear()",
            music_branch,
        )

        self.assertIn(
            '"MUSIC"',
            music_branch,
        )

    def test_empty_image_path_is_not_treated_as_current_directory(self):
        method = self.method_source(
            "update_image_preview"
        )

        self.assertIn(
            "not self.image_path",
            method,
        )

        self.assertIn(
            "not path.is_file()",
            method,
        )

    def test_theme_styles_new_workspace(self):
        method = self.method_source(
            "_apply_presence_studio_theme"
        )

        for token in (
            "presenceStudioWorkspace",
            "presenceStudioModeButton",
            "presenceStudioContext",
            "presenceStudioActionBar",
        ):
            self.assertIn(
                token,
                method,
            )

        apply_theme = self.method_source(
            "apply_theme"
        )

        self.assertIn(
            "self._apply_presence_studio_theme(",
            apply_theme,
        )


if __name__ == "__main__":
    unittest.main()
