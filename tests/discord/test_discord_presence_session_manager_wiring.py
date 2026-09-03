from __future__ import annotations

import ast
import unittest
from pathlib import Path


MAIN_WINDOW_PATH = Path(
    "src/ui/main_window.py"
)

CONTROLLER_PATH = Path(
    "src/discord/presence_controller.py"
)

PRESENCE_PAGE_PATH = Path(
    "src/ui/presence_page.py"
)

SETTINGS_PATH = Path(
    "src/ui/settings.py"
)


def _read(
    path: Path,
) -> str:
    return path.read_text(
        encoding="utf-8-sig"
    )


def _method_source(
    source: str,
    class_name: str,
    method_name: str,
) -> str:
    tree = ast.parse(
        source
    )

    for node in tree.body:
        if not (
            isinstance(
                node,
                ast.ClassDef,
            )
            and node.name == class_name
        ):
            continue

        matches = [
            child
            for child in node.body
            if (
                isinstance(
                    child,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                )
                and child.name
                == method_name
            )
        ]

        if len(matches) != 1:
            raise AssertionError(
                f"Expected one "
                f"{class_name}.{method_name}, "
                f"found {len(matches)}."
            )

        segment = ast.get_source_segment(
            source,
            matches[0],
        )

        if not segment:
            raise AssertionError(
                "Could not recover method source."
            )

        return segment

    raise AssertionError(
        f"Class {class_name!r} was not found."
    )


class DiscordPresenceSessionManagerWiringTests(
    unittest.TestCase
):
    def test_main_window_imports_session_manager(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        self.assertIn(
            (
                "from src.discord.session_manager import (\n"
                "    DiscordPresenceSessionManager,\n"
                ")"
            ),
            source,
        )

    def test_manager_uses_shared_application_library_resolver(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        init_source = _method_source(
            source,
            "MainWindow",
            "__init__",
        )

        self.assertIn(
            "self.discord_session_manager = (",
            init_source,
        )

        self.assertIn(
            "DiscordPresenceSessionManager(",
            init_source,
        )

        self.assertIn(
            (
                "self.discord_application_library_store"
                ".get"
            ),
            init_source,
        )

        self.assertNotIn(
            "session_factory=",
            init_source,
        )

    def test_manager_is_composed_after_library_migration_before_legacy_rpc(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        init_source = _method_source(
            source,
            "MainWindow",
            "__init__",
        )

        migration_index = (
            init_source.index(
                "migrate_legacy_discord_identity_to_library("
            )
        )

        manager_index = (
            init_source.index(
                "self.discord_session_manager = ("
            )
        )

        legacy_rpc_index = (
            init_source.index(
                "self.discord = ("
            )
        )

        self.assertLess(
            migration_index,
            manager_index,
        )

        self.assertLess(
            manager_index,
            legacy_rpc_index,
        )

    def test_presence_controller_still_receives_legacy_discord_session(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        init_source = _method_source(
            source,
            "MainWindow",
            "__init__",
        )

        controller_index = (
            init_source.index(
                "self.presence_controller = ("
            )
        )

        controller_source = init_source[
            controller_index:
        ]

        self.assertIn(
            "PresenceController(",
            controller_source,
        )

        self.assertIn(
            "self.discord",
            controller_source,
        )

        self.assertNotIn(
            (
                "PresenceController(\n"
                "                "
                "self.discord_session_manager"
            ),
            controller_source,
        )

    def test_connect_services_starts_only_legacy_discord_session(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        method = _method_source(
            source,
            "MainWindow",
            "connect_services",
        )

        self.assertEqual(
            method.count(
                "self.discord.connect()"
            ),
            1,
        )

        self.assertNotIn(
            "discord_session_manager",
            method,
        )

        self.assertIn(
            (
                "self.presence_controller"
                ".apply_saved_mode"
            ),
            method,
        )

    def test_session_manager_is_dormant_outside_construction_and_shutdown(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        self.assertEqual(
            source.count(
                "self.discord_session_manager"
            ),
            2,
        )

        for forbidden in (
            (
                "self.discord_session_manager"
                ".ensure_lane("
            ),
            (
                "self.discord_session_manager"
                ".update_music("
            ),
            (
                "self.discord_session_manager"
                ".update_secondary("
            ),
            (
                "self.discord_session_manager"
                ".clear_lane("
            ),
            (
                "self.discord_session_manager"
                ".release_lane("
            ),
        ):
            self.assertNotIn(
                forbidden,
                source,
            )

    def test_shutdown_closes_manager_before_legacy_discord(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        method = _method_source(
            source,
            "MainWindow",
            "shutdown",
        )

        manager_index = method.index(
            (
                "self.discord_session_manager"
                ".close()"
            )
        )

        legacy_index = method.index(
            "self.discord.close()"
        )

        self.assertLess(
            manager_index,
            legacy_index,
        )

    def test_manager_shutdown_failure_cannot_skip_legacy_close(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        method = _method_source(
            source,
            "MainWindow",
            "shutdown",
        )

        manager_index = method.index(
            (
                "self.discord_session_manager"
                ".close()"
            )
        )

        legacy_index = method.index(
            "self.discord.close()"
        )

        between = method[
            manager_index:
            legacy_index
        ]

        before_manager = method[
            :manager_index
        ]

        self.assertIn(
            "try:",
            before_manager,
        )

        self.assertIn(
            "except Exception:",
            between,
        )

        self.assertIn(
            "pass",
            between,
        )

    def test_presence_controller_has_no_manager_wiring_yet(
        self,
    ):
        source = _read(
            CONTROLLER_PATH
        )

        self.assertNotIn(
            "DiscordPresenceSessionManager",
            source,
        )

        self.assertNotIn(
            "discord_session_manager",
            source,
        )

    def test_presence_ui_and_settings_have_no_manager_wiring_yet(
        self,
    ):
        for path in (
            PRESENCE_PAGE_PATH,
            SETTINGS_PATH,
        ):
            source = _read(
                path
            )

            self.assertNotIn(
                "DiscordPresenceSessionManager",
                source,
            )

            self.assertNotIn(
                "discord_session_manager",
                source,
            )


if __name__ == "__main__":
    unittest.main()
