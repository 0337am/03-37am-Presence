from pathlib import Path
import ast
import unittest


class PresenceLibraryIntegrationTests(
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

    def test_presence_page_imports_library_panel(self):
        self.assertIn(
            (
                "from src.ui.presence_library "
                "import PresenceLibraryPanel"
            ),
            self.source,
        )

    def test_build_installs_presence_studio_shell(self):
        method = self.method_source(
            "build_ui"
        )

        self.assertIn(
            "self._install_presence_studio_shell()",
            method,
        )

    def test_studio_hides_legacy_preset_toolbar(self):
        method = self.method_source(
            "_install_presence_studio_shell"
        )

        self.assertIn(
            "self.presets_card.setVisible(",
            method,
        )

        self.assertIn(
            "False",
            method,
        )

    def test_studio_uses_library_and_existing_workspace(self):
        method = self.method_source(
            "_install_presence_studio_shell"
        )

        for token in (
            "PresenceLibraryPanel(",
            "self.presence_library",
            "self.content_row",
            "self.studio_row",
            "Save to Library",
        ):
            self.assertIn(
                token,
                method,
            )

    def test_library_signals_use_existing_engine(self):
        method = self.method_source(
            "_install_presence_studio_shell"
        )

        for token in (
            "preset_selected.connect(",
            "self.open_library_preset",
            "preset_apply_requested.connect(",
            "self.apply_library_preset",
            "create_requested.connect(",
            "self.start_new_library_presence",
            "self.save_current_as_preset",
        ):
            self.assertIn(
                token,
                method,
            )

    def test_open_does_not_apply_to_discord(self):
        method = self.method_source(
            "open_library_preset"
        )

        self.assertNotIn(
            "controller.apply_mode",
            method,
        )

        self.assertIn(
            "preset.to_presence_mode()",
            method,
        )

        self.assertIn(
            "self.update_preview()",
            method,
        )

    def test_apply_reuses_existing_apply_selected_preset(self):
        method = self.method_source(
            "apply_library_preset"
        )

        self.assertIn(
            "self.apply_selected_preset()",
            method,
        )

    def test_new_presence_creates_custom_draft_only(self):
        method = self.method_source(
            "start_new_library_presence"
        )

        self.assertIn(
            'self.mode_box.findData(',
            method,
        )

        self.assertIn(
            '"custom"',
            method,
        )

        self.assertNotIn(
            "preset_store.create(",
            method,
        )

        self.assertNotIn(
            "controller.apply_mode",
            method,
        )

    def test_existing_preset_engine_remains(self):
        for method in (
            "save_current_as_preset",
            "apply_selected_preset",
            "update_selected_preset",
            "rename_selected_preset",
            "duplicate_selected_preset",
            "toggle_selected_preset_pin",
            "delete_selected_preset",
        ):
            self.assertIn(
                f"def {method}(",
                self.source,
            )

    def test_refresh_preset_box_also_refreshes_library(self):
        method = self.method_source(
            "refresh_preset_box"
        )

        self.assertIn(
            "self.refresh_presence_library(",
            method,
        )

    def test_theme_is_forwarded_to_library(self):
        method = self.method_source(
            "apply_theme"
        )

        self.assertIn(
            "library.apply_theme(",
            method,
        )

    def test_card_actions_route_to_existing_preset_engine(self):
        method = self.method_source(
            "handle_library_preset_action"
        )

        for token in (
            'action == "edit"',
            'action == "rename"',
            'action == "duplicate"',
            'action == "pin"',
            'action == "delete"',
            "self.open_library_preset(",
            "self.rename_selected_preset()",
            "self.duplicate_selected_preset()",
            "self.toggle_selected_preset_pin()",
            "self.delete_selected_preset()",
        ):
            self.assertIn(
                token,
                method,
            )

    def test_library_action_signal_is_connected(self):
        method = self.method_source(
            "_install_presence_studio_shell"
        )

        self.assertIn(
            "preset_action_requested.connect(",
            method,
        )

        self.assertIn(
            "self.handle_library_preset_action",
            method,
        )

    def test_delete_action_reuses_confirmed_delete_flow(self):
        router = self.method_source(
            "handle_library_preset_action"
        )

        delete_method = self.method_source(
            "delete_selected_preset"
        )

        self.assertIn(
            'action == "delete"',
            router,
        )

        self.assertIn(
            "self.delete_selected_preset()",
            router,
        )

        self.assertIn(
            "QMessageBox.question(",
            delete_method,
        )

        self.assertIn(
            "self.preset_store.delete(",
            delete_method,
        )

        self.assertIn(
            "self.refresh_preset_box()",
            delete_method,
        )

        self.assertIn(
            "self.presets_changed.emit()",
            delete_method,
        )


if __name__ == "__main__":
    unittest.main()
