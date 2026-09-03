from __future__ import annotations

import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.discord.presence_modes import (
    PresenceMode,
)
from src.ui.presence_page import (
    PresencePage,
)


REPO = Path(
    __file__
).resolve().parents[2]

PRESENCE_PATH = (
    REPO / "src/ui/presence_page.py"
)

MAIN_WINDOW_PATH = (
    REPO / "src/ui/main_window.py"
)


USER_ENTRY_ID = (
    "discord_app_0123456789abcdef"
)

STORED_ENTRY_ID = (
    "discord_app_aaaaaaaaaaaaaaaa"
)


class FakeButton:
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


class FakeStatus:
    def __init__(
        self,
    ):
        self.text = ""

    def setText(
        self,
        value,
    ):
        self.text = str(
            value
        )


class FakeModeBox:
    def __init__(
        self,
        text="Custom",
    ):
        self._text = text

    def currentText(
        self,
    ):
        return self._text


class FakePreset:
    def __init__(
        self,
        presence_mode,
    ):
        self.presence_mode = (
            presence_mode
        )

    def to_presence_mode(
        self,
    ):
        return self.presence_mode


class FakeController:
    def __init__(
        self,
        *,
        active_mode="music",
        stored_mode=None,
        publish_result=True,
        clear_result=True,
    ):
        self.active_mode = active_mode
        self.secondary_presence_mode = None

        self.stored_mode = (
            stored_mode
            or PresenceMode(
                mode="custom",
                application_entry_id=(
                    STORED_ENTRY_ID
                ),
            )
        )

        self.publish_result = (
            publish_result
        )

        self.clear_result = (
            clear_result
        )

        self.applied = []
        self.clear_calls = 0

    def load_mode(
        self,
        mode,
    ):
        return self.stored_mode

    def apply_secondary_mode(
        self,
        presence_mode,
    ):
        self.applied.append(
            presence_mode
        )

        if self.publish_result:
            self.secondary_presence_mode = (
                presence_mode
            )

        return self.publish_result

    def clear_secondary_mode(
        self,
    ):
        self.clear_calls += 1

        if self.clear_result:
            self.secondary_presence_mode = None

        return self.clear_result


def read_source(
    path,
):
    return path.read_text(
        encoding="utf-8-sig"
    )


def method_source(
    source,
    class_name,
    method_name,
):
    tree = ast.parse(
        source
    )

    classes = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.ClassDef,
            )
            and node.name == class_name
        )
    ]

    if len(classes) != 1:
        raise AssertionError(
            "Expected one class "
            + class_name
        )

    methods = [
        node
        for node in classes[
            0
        ].body
        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and node.name == method_name
        )
    ]

    if len(methods) != 1:
        raise AssertionError(
            "Expected one method "
            + method_name
        )

    return ast.get_source_segment(
        source,
        methods[
            0
        ],
    )


class PresenceSecondaryStudioUiTests(
    unittest.TestCase
):
    def test_studio_defines_secondary_buttons(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        self.assertIn(
            '"Apply as Secondary"',
            source,
        )

        self.assertIn(
            '"Clear Secondary"',
            source,
        )

        self.assertIn(
            "self.apply_secondary_button",
            source,
        )

        self.assertIn(
            "self.clear_secondary_button",
            source,
        )

    def test_secondary_buttons_use_existing_secondary_style(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        self.assertGreaterEqual(
            source.count(
                '"secondaryButton"'
            ),
            4,
        )

    def test_secondary_buttons_are_wired_to_controller_ui_methods(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        self.assertIn(
            "self.apply_secondary_button.clicked.connect(",
            source,
        )

        self.assertIn(
            "self.apply_secondary_presence",
            source,
        )

        self.assertIn(
            "self.clear_secondary_button.clicked.connect(",
            source,
        )

        self.assertIn(
            "self.clear_secondary_presence",
            source,
        )

    def test_secondary_signal_refreshes_studio_controls(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        self.assertIn(
            "self.controller.secondary_mode_changed.connect(",
            source,
        )

        self.assertIn(
            "self._refresh_secondary_controls",
            source,
        )

    def test_selected_preset_application_assignment_is_preferred(
        self,
    ):
        preset_mode = PresenceMode(
            mode="custom",
            application_entry_id=(
                USER_ENTRY_ID
            ),
        )

        shell = SimpleNamespace(
            current_mode="custom",
            selected_preset=(
                lambda: FakePreset(
                    preset_mode
                )
            ),
            controller=FakeController(),
        )

        result = (
            PresencePage
            ._secondary_editor_application_entry_id(
                shell
            )
        )

        self.assertEqual(
            result,
            USER_ENTRY_ID,
        )

    def test_stored_mode_application_assignment_is_fallback(
        self,
    ):
        stored = PresenceMode(
            mode="custom",
            application_entry_id=(
                STORED_ENTRY_ID
            ),
        )

        shell = SimpleNamespace(
            current_mode="custom",
            selected_preset=lambda: None,
            controller=FakeController(
                stored_mode=stored
            ),
        )

        result = (
            PresencePage
            ._secondary_editor_application_entry_id(
                shell
            )
        )

        self.assertEqual(
            result,
            STORED_ENTRY_ID,
        )

    def test_preset_for_different_mode_is_not_reused(
        self,
    ):
        preset_mode = PresenceMode(
            mode="working",
            application_entry_id=(
                USER_ENTRY_ID
            ),
        )

        stored = PresenceMode(
            mode="custom",
            application_entry_id=(
                STORED_ENTRY_ID
            ),
        )

        shell = SimpleNamespace(
            current_mode="custom",
            selected_preset=(
                lambda: FakePreset(
                    preset_mode
                )
            ),
            controller=FakeController(
                stored_mode=stored
            ),
        )

        result = (
            PresencePage
            ._secondary_editor_application_entry_id(
                shell
            )
        )

        self.assertEqual(
            result,
            STORED_ENTRY_ID,
        )

    def test_apply_secondary_requires_music_as_primary(
        self,
    ):
        controller = FakeController(
            active_mode="custom"
        )

        status = FakeStatus()

        shell = SimpleNamespace(
            current_mode="custom",
            controller=controller,
            status_label=status,
            _refresh_secondary_controls=(
                lambda: None
            ),
        )

        PresencePage.apply_secondary_presence(
            shell
        )

        self.assertEqual(
            controller.applied,
            [],
        )

        self.assertIn(
            "Music",
            status.text,
        )

    def test_music_editor_cannot_be_secondary(
        self,
    ):
        controller = FakeController()

        status = FakeStatus()

        shell = SimpleNamespace(
            current_mode="music",
            controller=controller,
            status_label=status,
            _refresh_secondary_controls=(
                lambda: None
            ),
        )

        PresencePage.apply_secondary_presence(
            shell
        )

        self.assertEqual(
            controller.applied,
            [],
        )

        self.assertIn(
            "cannot",
            status.text.lower(),
        )

    def test_disabled_editor_cannot_be_secondary(
        self,
    ):
        controller = FakeController()

        status = FakeStatus()

        shell = SimpleNamespace(
            current_mode="disabled",
            controller=controller,
            status_label=status,
            _refresh_secondary_controls=(
                lambda: None
            ),
        )

        PresencePage.apply_secondary_presence(
            shell
        )

        self.assertEqual(
            controller.applied,
            [],
        )

    def test_custom_editor_routes_to_secondary_controller(
        self,
    ):
        controller = FakeController()

        status = FakeStatus()

        editor_mode = PresenceMode(
            mode="custom",
            title="Floor 35",
            message="Solo",
        )

        refresh_calls = []

        shell = SimpleNamespace(
            current_mode="custom",
            controller=controller,
            status_label=status,
            mode_box=FakeModeBox(
                "Custom"
            ),
            current_editor_presence_mode=(
                lambda: editor_mode
            ),
            _secondary_editor_application_entry_id=(
                lambda: USER_ENTRY_ID
            ),
            _refresh_secondary_controls=(
                lambda: refresh_calls.append(
                    True
                )
            ),
        )

        PresencePage.apply_secondary_presence(
            shell
        )

        self.assertEqual(
            len(
                controller.applied
            ),
            1,
        )

        self.assertIs(
            controller.applied[
                0
            ],
            editor_mode,
        )

        self.assertEqual(
            editor_mode.application_entry_id,
            USER_ENTRY_ID,
        )

        self.assertIn(
            "Secondary",
            status.text,
        )

        self.assertEqual(
            len(
                refresh_calls
            ),
            1,
        )

    def test_failed_secondary_publish_is_user_safe(
        self,
    ):
        controller = FakeController(
            publish_result=False
        )

        status = FakeStatus()

        shell = SimpleNamespace(
            current_mode="working",
            controller=controller,
            status_label=status,
            mode_box=FakeModeBox(
                "Working"
            ),
            current_editor_presence_mode=(
                lambda: PresenceMode(
                    mode="working"
                )
            ),
            _secondary_editor_application_entry_id=(
                lambda: USER_ENTRY_ID
            ),
            _refresh_secondary_controls=(
                lambda: None
            ),
        )

        PresencePage.apply_secondary_presence(
            shell
        )

        self.assertEqual(
            len(
                controller.applied
            ),
            1,
        )

        self.assertIn(
            "could not be published",
            status.text,
        )

    def test_clear_secondary_routes_only_to_secondary_controller(
        self,
    ):
        controller = FakeController()

        controller.secondary_presence_mode = (
            PresenceMode(
                mode="custom"
            )
        )

        status = FakeStatus()

        shell = SimpleNamespace(
            controller=controller,
            status_label=status,
            _refresh_secondary_controls=(
                lambda: None
            ),
        )

        PresencePage.clear_secondary_presence(
            shell
        )

        self.assertEqual(
            controller.clear_calls,
            1,
        )

        self.assertIn(
            "cleared",
            status.text.lower(),
        )

    def test_secondary_control_enablement_tracks_primary_and_secondary_state(
        self,
    ):
        controller = FakeController(
            active_mode="music"
        )

        apply_button = FakeButton()
        clear_button = FakeButton()

        shell = SimpleNamespace(
            current_mode="custom",
            controller=controller,
            apply_secondary_button=(
                apply_button
            ),
            clear_secondary_button=(
                clear_button
            ),
        )

        PresencePage._refresh_secondary_controls(
            shell
        )

        self.assertIs(
            apply_button.visible,
            True,
        )

        self.assertIs(
            apply_button.enabled,
            True,
        )

        self.assertIs(
            clear_button.enabled,
            False,
        )

        controller.secondary_presence_mode = (
            PresenceMode(
                mode="custom"
            )
        )

        PresencePage._refresh_secondary_controls(
            shell
        )

        self.assertIs(
            clear_button.enabled,
            True,
        )

        controller.active_mode = "custom"

        PresencePage._refresh_secondary_controls(
            shell
        )

        self.assertIs(
            apply_button.enabled,
            False,
        )

    def test_music_and_disabled_hide_secondary_apply_action(
        self,
    ):
        controller = FakeController()

        for mode in (
            "music",
            "disabled",
        ):
            apply_button = FakeButton()
            clear_button = FakeButton()

            shell = SimpleNamespace(
                current_mode=mode,
                controller=controller,
                apply_secondary_button=(
                    apply_button
                ),
                clear_secondary_button=(
                    clear_button
                ),
            )

            PresencePage._refresh_secondary_controls(
                shell
            )

            self.assertIs(
                apply_button.visible,
                False,
            )

            self.assertIs(
                apply_button.enabled,
                False,
            )

    def test_update_editor_state_refreshes_secondary_controls(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        update_editor = method_source(
            source,
            "PresencePage",
            "update_editor_state",
        )

        self.assertIn(
            "self._refresh_secondary_controls()",
            update_editor,
        )

    def test_primary_apply_path_remains_primary_only(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        apply_presence = method_source(
            source,
            "PresencePage",
            "apply_presence",
        )

        self.assertIn(
            "self.controller.apply_mode(",
            apply_presence,
        )

        self.assertNotIn(
            "apply_secondary_mode",
            apply_presence,
        )

    def test_saved_preset_apply_path_remains_primary_only(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        apply_preset = method_source(
            source,
            "PresencePage",
            "apply_selected_preset",
        )

        self.assertIn(
            "self.controller.apply_mode(",
            apply_preset,
        )

        self.assertNotIn(
            "apply_secondary_mode",
            apply_preset,
        )

    def test_main_window_does_not_activate_secondary_lane(
        self,
    ):
        source = read_source(
            MAIN_WINDOW_PATH
        )

        self.assertNotIn(
            "apply_secondary_mode(",
            source,
        )

        self.assertNotIn(
            "SECONDARY_LANE_ID",
            source,
        )

    def test_secondary_buttons_live_in_visible_studio_action_bar(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        tree = ast.parse(
            source
        )

        classes = [
            node
            for node in tree.body
            if (
                isinstance(
                    node,
                    ast.ClassDef,
                )
                and node.name == "PresencePage"
            )
        ]

        self.assertEqual(
            len(classes),
            1,
        )

        presence_class = classes[
            0
        ]

        methods = {
            node.name: node
            for node in presence_class.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }

        studio_method = methods.get(
            "_install_presence_studio_shell"
        )

        build_method = methods.get(
            "build_ui"
        )

        self.assertIsNotNone(
            studio_method
        )

        self.assertIsNotNone(
            build_method
        )

        def owned_widgets(
            method,
            layout_name,
        ):
            result = []

            for node in ast.walk(
                method
            ):
                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue

                function = node.func

                if not (
                    isinstance(
                        function,
                        ast.Attribute,
                    )
                    and function.attr
                    == "addWidget"
                    and isinstance(
                        function.value,
                        ast.Name,
                    )
                    and function.value.id
                    == layout_name
                    and node.args
                ):
                    continue

                argument = node.args[
                    0
                ]

                if not (
                    isinstance(
                        argument,
                        ast.Attribute,
                    )
                    and isinstance(
                        argument.value,
                        ast.Name,
                    )
                    and argument.value.id
                    == "self"
                ):
                    continue

                result.append(
                    argument.attr
                )

            return result

        visible_widgets = owned_widgets(
            studio_method,
            "action_layout",
        )

        legacy_widgets = owned_widgets(
            build_method,
            "bottom_layout",
        )

        self.assertIn(
            "apply_secondary_button",
            visible_widgets,
        )

        self.assertIn(
            "clear_secondary_button",
            visible_widgets,
        )

        self.assertNotIn(
            "apply_secondary_button",
            legacy_widgets,
        )

        self.assertNotIn(
            "clear_secondary_button",
            legacy_widgets,
        )

    def test_clear_secondary_is_hidden_until_secondary_is_active(
        self,
    ):
        controller = FakeController(
            active_mode="music"
        )

        apply_button = FakeButton()
        clear_button = FakeButton()

        shell = SimpleNamespace(
            current_mode="custom",
            controller=controller,
            apply_secondary_button=(
                apply_button
            ),
            clear_secondary_button=(
                clear_button
            ),
        )

        PresencePage._refresh_secondary_controls(
            shell
        )

        self.assertIs(
            clear_button.visible,
            False,
        )

        self.assertIs(
            clear_button.enabled,
            False,
        )

        controller.secondary_presence_mode = (
            PresenceMode(
                mode="custom"
            )
        )

        PresencePage._refresh_secondary_controls(
            shell
        )

        self.assertIs(
            clear_button.visible,
            True,
        )

        self.assertIs(
            clear_button.enabled,
            True,
        )


if __name__ == "__main__":
    unittest.main()
