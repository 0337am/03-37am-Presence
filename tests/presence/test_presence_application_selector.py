
from __future__ import annotations

import ast
import unittest
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
)

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY,
    BUILTIN_APPLICATION_ENTRY_ID,
    DiscordApplicationEntry,
)

from src.discord.presence_modes import (
    PresenceMode,
)

from src.ui.presence_page import (
    PresencePage,
)


ROOT = Path(
    __file__
).resolve().parents[2]

PRESENCE_PATH = (
    ROOT
    / "src"
    / "ui"
    / "presence_page.py"
)

MAIN_PATH = (
    ROOT
    / "src"
    / "ui"
    / "main_window.py"
)

USER_ENTRY_ID = (
    "discord_app_0123456789abcdef"
)

USER_APPLICATION_ID = (
    "1096663809097203752"
)


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
            and node.name
            == class_name
        )
    ]

    if len(classes) != 1:
        raise AssertionError(
            "class not unique"
        )

    methods = [
        node
        for node in classes[0].body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name
            == method_name
        )
    ]

    if len(methods) != 1:
        raise AssertionError(
            "method not unique"
        )

    segment = ast.get_source_segment(
        source,
        methods[0],
    )

    if segment is None:
        raise AssertionError(
            "method source unavailable"
        )

    return segment


class FakeStore:
    def __init__(
        self,
        entries,
    ):
        self.entries = list(
            entries
        )

    def list_entries(
        self,
    ):
        return list(
            self.entries
        )


class FailingStore:
    def list_entries(
        self,
    ):
        raise OSError(
            "simulated failure"
        )


class FakeController:
    def __init__(
        self,
        entry_id,
    ):
        self.entry_id = entry_id

    def load_mode(
        self,
        mode,
    ):
        return PresenceMode(
            mode=mode,
            application_entry_id=(
                self.entry_id
            ),
        )


class Harness:
    current_application_entry_id = (
        PresencePage
        .current_application_entry_id
    )

    refresh_application_box = (
        PresencePage
        .refresh_application_box
    )

    _sync_application_box_from_mode = (
        PresencePage
        ._sync_application_box_from_mode
    )

    def __init__(
        self,
        store,
        entry_id=(
            BUILTIN_APPLICATION_ENTRY_ID
        ),
    ):
        self.application_box = (
            QComboBox()
        )

        self.discord_application_store = (
            store
        )

        self.controller = (
            FakeController(
                entry_id
            )
        )

        self.current_mode = "custom"

        self._application_store_available = (
            False
        )

        self._loading_application_box = (
            False
        )


class Toggle:
    def __init__(
        self,
        checked=False,
    ):
        self.checked = bool(
            checked
        )

    def isChecked(
        self,
    ):
        return self.checked


class TextField:
    def __init__(
        self,
        value="",
    ):
        self.value = value

    def text(
        self,
    ):
        return self.value


class LegacyEditorProxy:
    current_editor_presence_mode = (
        PresencePage
        .current_editor_presence_mode
    )

    def __init__(
        self,
    ):
        self.current_mode = "custom"

        self.show_link_buttons_box = (
            Toggle(
                False
            )
        )

        self.show_party_box = (
            Toggle(
                False
            )
        )

        self.title_input = (
            TextField(
                "Legacy editor"
            )
        )

        self.message_input = (
            TextField(
                "Proxy compatibility"
            )
        )

        self.image_path = ""

        self.elapsed_box = (
            Toggle(
                False
            )
        )

    def _editor_presence_buttons(
        self,
    ):
        return ()


class PresenceApplicationSelectorTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

        cls.user_entry = (
            DiscordApplicationEntry(
                entry_id=(
                    USER_ENTRY_ID
                ),
                name=(
                    "Sword Art Online"
                ),
                application_id=(
                    USER_APPLICATION_ID
                ),
                builtin=False,
            )
        )

    def make_store(
        self,
    ):
        return FakeStore(
            [
                BUILTIN_APPLICATION_ENTRY,
                self.user_entry,
            ]
        )

    def test_store_population_uses_stable_entry_ids(
        self,
    ):
        harness = Harness(
            self.make_store()
        )

        harness.refresh_application_box(
            USER_ENTRY_ID
        )

        self.assertEqual(
            harness.application_box.count(),
            2,
        )

        self.assertEqual(
            harness.application_box.itemData(
                0
            ),
            BUILTIN_APPLICATION_ENTRY_ID,
        )

        self.assertEqual(
            harness.application_box.itemData(
                1
            ),
            USER_ENTRY_ID,
        )

        self.assertEqual(
            harness.current_application_entry_id(),
            USER_ENTRY_ID,
        )

    def test_missing_reference_is_preserved_as_unavailable(
        self,
    ):
        missing = (
            "discord_app_deadbeefdeadbeef"
        )

        harness = Harness(
            self.make_store()
        )

        harness.refresh_application_box(
            missing
        )

        self.assertEqual(
            harness.current_application_entry_id(),
            missing,
        )

        self.assertIn(
            "Unavailable",
            harness.application_box.currentText(),
        )

        self.assertTrue(
            harness.application_box.isEnabled()
        )

    def test_rename_refresh_preserves_stable_selection(
        self,
    ):
        store = self.make_store()

        harness = Harness(
            store
        )

        harness.refresh_application_box(
            USER_ENTRY_ID
        )

        store.entries = [
            BUILTIN_APPLICATION_ENTRY,
            DiscordApplicationEntry(
                entry_id=(
                    USER_ENTRY_ID
                ),
                name="SAO Renamed",
                application_id=(
                    USER_APPLICATION_ID
                ),
                builtin=False,
            ),
        ]

        harness.refresh_application_box()

        self.assertEqual(
            harness.current_application_entry_id(),
            USER_ENTRY_ID,
        )

        self.assertEqual(
            harness.application_box.currentText(),
            "SAO Renamed",
        )

    def test_store_failure_disables_selector_without_losing_reference(
        self,
    ):
        missing = (
            "discord_app_deadbeefdeadbeef"
        )

        harness = Harness(
            FailingStore(),
            entry_id=missing,
        )

        harness.refresh_application_box(
            missing
        )

        self.assertFalse(
            harness.application_box.isEnabled()
        )

        self.assertEqual(
            harness.current_application_entry_id(),
            missing,
        )

    def test_disabled_mode_disables_selector(
        self,
    ):
        harness = Harness(
            self.make_store()
        )

        harness.current_mode = (
            "disabled"
        )

        harness.refresh_application_box(
            BUILTIN_APPLICATION_ENTRY_ID
        )

        self.assertFalse(
            harness.application_box.isEnabled()
        )

        self.assertEqual(
            harness.current_application_entry_id(),
            BUILTIN_APPLICATION_ENTRY_ID,
        )

    def test_legacy_editor_proxy_remains_backward_compatible(
        self,
    ):
        proxy = LegacyEditorProxy()

        mode = (
            proxy
            .current_editor_presence_mode()
        )

        self.assertEqual(
            mode.title,
            "Legacy editor",
        )

        self.assertEqual(
            mode.message,
            "Proxy compatibility",
        )

        self.assertIsNone(
            mode.normalized_application_entry_id()
        )

    def test_constructor_accepts_shared_application_store(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        constructor = method_source(
            source,
            "PresencePage",
            "__init__",
        )

        self.assertIn(
            "discord_application_store=None",
            constructor,
        )

        self.assertIn(
            "self.discord_application_store",
            constructor,
        )

    def test_selector_is_owned_by_visible_studio_shell(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        shell = method_source(
            source,
            "PresencePage",
            "_install_presence_studio_shell",
        )

        self.assertIn(
            '"Discord Application"',
            shell,
        )

        self.assertIn(
            "self.application_box = QComboBox()",
            shell,
        )

        self.assertIn(
            "applicationBox",
            shell,
        )

        self.assertIn(
            "application_row",
            shell,
        )

    def test_current_editor_mode_reads_selector_defensively(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        method = method_source(
            source,
            "PresencePage",
            "current_editor_presence_mode",
        )

        self.assertIn(
            (
                '"current_application_entry_id"'
            ),
            method,
        )

        self.assertIn(
            "callable(",
            method,
        )

        self.assertIn(
            (
                "application_entry_id="
                "application_entry_id"
            ),
            method,
        )

        self.assertNotIn(
            (
                "self."
                "current_application_entry_id()"
            ),
            method,
        )

    def test_mode_and_preset_load_paths_sync_selector(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        for method_name in (
            "load_mode",
            "apply_selected_preset",
            "open_library_preset",
        ):
            method = method_source(
                source,
                "PresencePage",
                method_name,
            )

            self.assertIn(
                "_sync_application_box_from_mode",
                method,
            )

    def test_secondary_helper_prefers_visible_selector(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        method = method_source(
            source,
            "PresencePage",
            (
                "_secondary_editor_"
                "application_entry_id"
            ),
        )

        selector_position = (
            method.find(
                "current_application_entry_id"
            )
        )

        preset_position = (
            method.find(
                "selected_preset"
            )
        )

        self.assertGreaterEqual(
            selector_position,
            0,
        )

        self.assertGreater(
            preset_position,
            selector_position,
        )

    def test_selector_signal_and_theme_are_present(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        signals = method_source(
            source,
            "PresencePage",
            "connect_signals",
        )

        self.assertIn(
            (
                "self.application_box."
                "currentIndexChanged.connect"
            ),
            signals,
        )

        self.assertIn(
            "_on_application_changed",
            signals,
        )

        self.assertIn(
            "QComboBox#applicationBox",
            source,
        )

        self.assertIn(
            "QComboBox#applicationBox:hover",
            source,
        )

        self.assertIn(
            (
                "QComboBox#applicationBox"
                "::drop-down"
            ),
            source,
        )

    def test_main_window_passes_shared_store_and_refreshes(
        self,
    ):
        source = read_source(
            MAIN_PATH
        )

        build_pages = method_source(
            source,
            "MainWindow",
            "build_pages",
        )

        self.assertIn(
            "discord_application_store=(",
            build_pages,
        )

        self.assertIn(
            (
                "self."
                "discord_application_library_store"
            ),
            build_pages,
        )

        self.assertIn(
            "entries_changed",
            build_pages,
        )

        self.assertIn(
            "refresh_application_box",
            build_pages,
        )

    def test_presence_page_does_not_own_discord_rpc_runtime(
        self,
    ):
        source = read_source(
            PRESENCE_PATH
        )

        tree = ast.parse(
            source
        )

        modules = set()

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                for alias in node.names:
                    modules.add(
                        alias.name
                    )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                modules.add(
                    node.module
                    or ""
                )

        self.assertNotIn(
            "pypresence",
            modules,
        )

        self.assertNotIn(
            "src.discord.extended_presence",
            modules,
        )

        self.assertNotIn(
            "src.discord.session_manager",
            modules,
        )

        for token in (
            "self.rpc",
            ".ensure_lane(",
            ".release_lane(",
            ".update_secondary(",
        ):
            self.assertNotIn(
                token,
                source,
            )


if __name__ == "__main__":
    unittest.main()
