from __future__ import annotations

import ast
import unittest
from pathlib import Path


def _source(
    relative: str,
) -> str:
    return Path(
        relative
    ).read_text(
        encoding="utf-8-sig"
    )


def _function_source(
    relative: str,
    function_name: str,
) -> str:
    source = _source(
        relative
    )

    tree = ast.parse(
        source
    )

    matches = [
        node
        for node in ast.walk(tree)
        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and node.name
            == function_name
        )
    ]

    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one "
            f"{function_name!r} in "
            f"{relative}, found "
            f"{len(matches)}."
        )

    segment = ast.get_source_segment(
        source,
        matches[0],
    )

    if not segment:
        raise AssertionError(
            "Could not recover source for "
            f"{function_name!r}."
        )

    return segment


class SavedPresenceApplicationApplyPathTests(
    unittest.TestCase
):
    def test_presence_studio_applies_exact_preset_presence_mode(
        self,
    ):
        method = _function_source(
            "src/ui/presence_page.py",
            "apply_selected_preset",
        )

        conversion = method.index(
            "preset.to_presence_mode()"
        )

        apply_call = method.index(
            "self.controller.apply_mode("
        )

        self.assertLess(
            conversion,
            apply_call,
        )

        self.assertIn(
            "presence_mode",
            method[
                apply_call:
            ],
        )

        self.assertNotIn(
            "PresenceMode(",
            method,
        )

    def test_presence_library_reuses_selected_preset_apply_path(
        self,
    ):
        method = _function_source(
            "src/ui/presence_page.py",
            "apply_library_preset",
        )

        self.assertIn(
            "self.apply_selected_preset()",
            method,
        )

        self.assertNotIn(
            "PresenceMode(",
            method,
        )

        self.assertNotIn(
            "to_presence_mode(",
            method,
        )

    def test_dashboard_handler_applies_exact_preset_presence_mode(
        self,
    ):
        method = _function_source(
            "src/ui/main_window.py",
            "apply_presence_preset_from_dashboard",
        )

        load_index = method.index(
            "presence_preset_store.get("
        )

        conversion_index = method.index(
            "preset.to_presence_mode()"
        )

        apply_index = method.index(
            "self.presence_controller.apply_mode("
        )

        self.assertLess(
            load_index,
            conversion_index,
        )

        self.assertLess(
            conversion_index,
            apply_index,
        )

        self.assertNotIn(
            "PresenceMode(",
            method,
        )

    def test_dashboard_signal_routes_to_central_preset_handler(
        self,
    ):
        source = _source(
            "src/ui/main_window.py"
        )

        signal_index = source.index(
            (
                "apply_presence_preset_requested"
                ".connect("
            )
        )

        handler_index = source.index(
            (
                "self."
                "apply_presence_preset_from_dashboard"
            ),
            signal_index,
        )

        self.assertLess(
            signal_index,
            handler_index,
        )

    def test_quick_access_emits_preset_id_without_rebuilding_mode(
        self,
    ):
        method = _function_source(
            "src/ui/dashboard.py",
            "refresh_quick_access_buttons",
        )

        self.assertIn(
            '"presence_preset"',
            method,
        )

        self.assertIn(
            "apply_presence_preset_requested.emit(",
            method,
        )

        self.assertIn(
            "preset_id",
            method,
        )

        self.assertNotIn(
            "to_presence_mode(",
            method,
        )

        self.assertNotIn(
            "PresenceMode(",
            method,
        )

    def test_controller_persists_assignment_before_live_presence_update(
        self,
    ):
        apply_method = _function_source(
            "src/discord/presence_controller.py",
            "apply_mode",
        )

        save_method = _function_source(
            "src/discord/presence_controller.py",
            "save_mode",
        )

        save_index = apply_method.index(
            "self.save_mode(presence_mode)"
        )

        discord_index = apply_method.index(
            "self.discord."
        )

        self.assertLess(
            save_index,
            discord_index,
        )

        self.assertIn(
            "normalized_application_entry_id()",
            save_method,
        )

        self.assertIn(
            '"application_entry_id"',
            save_method,
        )

        self.assertIn(
            "requested_application_entry_id",
            save_method,
        )


if __name__ == "__main__":
    unittest.main()
