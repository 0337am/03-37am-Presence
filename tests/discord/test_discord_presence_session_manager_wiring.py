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
    def test_main_window_imports_manager_and_music_lane(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        self.assertIn(
            "MUSIC_LANE_ID",
            source,
        )

        self.assertIn(
            "DiscordPresenceSessionManager",
            source,
        )

    def test_manager_uses_shared_library_resolver_before_legacy_runtime(
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

        manager_index = (
            init_source.index(
                "self.discord_session_manager = ("
            )
        )

        legacy_index = (
            init_source.index(
                "self.discord = ("
            )
        )

        self.assertIn(
            (
                "self.discord_application_library_store"
                ".get"
            ),
            init_source,
        )

        self.assertLess(
            manager_index,
            legacy_index,
        )

    def test_presence_controller_receives_legacy_and_manager(
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
            "PresenceController(",
            init_source,
        )

        self.assertIn(
            "self.discord,",
            init_source,
        )

        self.assertIn(
            "discord_session_manager=(",
            init_source,
        )

        self.assertIn(
            "self.discord_session_manager",
            init_source,
        )

    def test_connect_services_defers_discord_startup_to_saved_mode(
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

        self.assertNotIn(
            "self.discord.connect()",
            method,
        )

        self.assertIn(
            "self.presence_controller.apply_saved_mode",
            method,
        )

        self.assertIn(
            "QTimer.singleShot(",
            method,
        )

    def test_status_snapshot_reads_music_lane_observability(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        method = _method_source(
            source,
            "MainWindow",
            "_discord_status_snapshot",
        )

        for expected in (
            "MUSIC_LANE_ID",
            "profile_identity_for_lane",
            "lane_is_connected",
            "lane_is_running",
        ):
            self.assertIn(
                expected,
                method,
            )

    def test_status_snapshot_retains_legacy_branch_for_non_music_or_afk(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        method = _method_source(
            source,
            "MainWindow",
            "_discord_status_snapshot",
        )

        self.assertIn(
            'active_mode == "music"',
            method,
        )

        self.assertIn(
            "not auto_afk_active",
            method,
        )

        self.assertIn(
            '"discord"',
            method,
        )

    def test_refresh_status_uses_transport_snapshot(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        method = _method_source(
            source,
            "MainWindow",
            "refresh_discord_status",
        )

        self.assertIn(
            "self._discord_status_snapshot()",
            method,
        )

        self.assertNotIn(
            "self.discord.is_connected",
            method,
        )

        self.assertNotIn(
            "self.discord.profile_identity",
            method,
        )

    def test_diagnostics_uses_transport_snapshot(
        self,
    ):
        source = _read(
            MAIN_WINDOW_PATH
        )

        method = _method_source(
            source,
            "MainWindow",
            "collect_diagnostics",
        )

        self.assertIn(
            "self._discord_status_snapshot()",
            method,
        )

        self.assertNotIn(
            "self.discord.is_connected",
            method,
        )

    def test_shutdown_closes_manager_before_legacy_runtime(
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

        self.assertIn(
            "except Exception:",
            method[
                manager_index:
                legacy_index
            ],
        )

    def test_secondary_runtime_is_controller_owned_but_ui_inactive(
        self,
    ):
        main_source = _read(
            MAIN_WINDOW_PATH
        )

        controller_source = _read(
            CONTROLLER_PATH
        )

        presence_source = _read(
            PRESENCE_PAGE_PATH
        )

        settings_source = _read(
            SETTINGS_PATH
        )

        build_pages = _method_source(
            main_source,
            "MainWindow",
            "build_pages",
        )

        self.assertIn(
            "discord_identity_runtime=(",
            build_pages,
        )

        self.assertIn(
            "self.discord",
            build_pages,
        )

        self.assertIn(
            "SECONDARY_LANE_ID",
            controller_source,
        )

        self.assertIn(
            "apply_secondary_mode",
            controller_source,
        )

        self.assertIn(
            "_publish_secondary_with_manager",
            controller_source,
        )

        self.assertIn(
            "update_secondary",
            controller_source,
        )

        self.assertNotIn(
            "SECONDARY_LANE_ID",
            main_source,
        )

        self.assertNotIn(
            ".update_secondary(",
            main_source,
        )

        self.assertNotIn(
            "apply_secondary_mode",
            main_source,
        )

        self.assertNotIn(
            "DiscordPresenceSessionManager",
            presence_source,
        )

        self.assertNotIn(
            "DiscordPresenceSessionManager",
            settings_source,
        )


if __name__ == "__main__":
    unittest.main()
