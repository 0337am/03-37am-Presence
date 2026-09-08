from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from PyQt6.QtCore import QSettings

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY_ID,
)
from src.discord.presence_controller import (
    PresenceController,
)
from src.discord.presence_modes import (
    PresenceMode,
)


class FakeDiscord:
    is_connected = False
    is_running = False

    def connect(self):
        self.is_connected = True
        self.is_running = True
        return True

    def clear_presence(self):
        return None

    def close(self):
        self.is_connected = False
        self.is_running = False

    def update_custom(
        self,
        **_kwargs,
    ):
        return None


class FakeManager:

    def __init__(self):
        self.secondary_updates = []
        self.primary_updates = []
        self.release_calls = []
        self.release_result = True

    def update_secondary(
        self,
        application_entry_id,
        **kwargs,
    ):
        self.secondary_updates.append(
            (
                application_entry_id,
                dict(kwargs),
            )
        )

        return True

    def update_primary_custom(
        self,
        application_entry_id,
        **kwargs,
    ):
        self.primary_updates.append(
            (
                application_entry_id,
                dict(kwargs),
            )
        )

        return True


    def release_lane(
        self,
        lane_id,
    ):
        self.release_calls.append(
            lane_id
        )

        return self.release_result


class SecondaryPersistenceAutoAfkTests(
    unittest.TestCase
):
    def setUp(self):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.settings_path = (
            Path(
                self.temp.name
            )
            / "presence-test.ini"
        )

    def tearDown(self):
        self.temp.cleanup()

    def store(
        self,
        *,
        mode="music",
    ):
        result = QSettings(
            str(
                self.settings_path
            ),
            QSettings.Format.IniFormat,
        )

        result.setValue(
            "presence/active_mode",
            mode,
        )

        result.sync()

        return result

    def controller(
        self,
        manager=None,
        *,
        mode="music",
    ):
        result = PresenceController(
            FakeDiscord(),
            discord_session_manager=(
                manager
                if manager is not None
                else FakeManager()
            ),
        )

        result.store = self.store(
            mode=mode
        )

        return result

    @staticmethod
    def secondary():
        return PresenceMode(
            mode="custom",
            application_entry_id=(
                BUILTIN_APPLICATION_ENTRY_ID
            ),
            title="Floor 35",
            message="Solo",
            artwork_hover_text=(
                "Persistent hover"
            ),
            show_elapsed=True,
        )

    def test_explicit_store_is_ini_not_registry(
        self,
    ):
        controller = self.controller()

        filename = (
            controller.store.fileName()
        )

        self.assertTrue(
            filename
            .lower()
            .endswith(
                "presence-test.ini"
            )
        )

        self.assertNotIn(
            "HKEY_CURRENT_USER",
            filename,
        )

    def test_secondary_presence_restores_after_restart(
        self,
    ):
        first = self.controller()

        self.assertTrue(
            first.apply_secondary_mode(
                self.secondary()
            )
        )

        first.store.sync()

        manager = FakeManager()

        second = self.controller(
            manager
        )

        self.assertTrue(
            second.restore_secondary_mode()
        )

        self.assertEqual(
            len(
                manager.secondary_updates
            ),
            1,
        )

        restored = (
            second.secondary_presence_mode
        )

        self.assertIsNotNone(
            restored
        )

        self.assertEqual(
            restored.title,
            "Floor 35",
        )

        self.assertEqual(
            restored.message,
            "Solo",
        )

        self.assertEqual(
            restored.artwork_hover_text,
            "Persistent hover",
        )

    def test_manual_clear_removes_persisted_secondary(
        self,
    ):
        manager = FakeManager()

        first = self.controller(
            manager
        )

        self.assertTrue(
            first.apply_secondary_mode(
                self.secondary()
            )
        )

        self.assertTrue(
            first.store.contains(
                "presence/secondary_persisted"
            )
        )

        self.assertTrue(
            first.clear_secondary_mode()
        )

        self.assertEqual(
            manager.release_calls,
            [
                "secondary",
            ],
        )

        self.assertFalse(
            first.store.contains(
                "presence/secondary_persisted"
            )
        )

        second = self.controller()

        self.assertFalse(
            second.restore_secondary_mode()
        )


    def test_failed_live_clear_still_removes_persisted_secondary(
        self,
    ):
        manager = FakeManager()

        first = self.controller(
            manager
        )

        mode = self.secondary()

        self.assertTrue(
            first.apply_secondary_mode(
                mode
            )
        )

        self.assertTrue(
            first.store.contains(
                "presence/secondary_persisted"
            )
        )

        manager.release_result = False

        self.assertFalse(
            first.clear_secondary_mode()
        )

        self.assertIs(
            first.secondary_presence_mode,
            mode,
        )

        self.assertFalse(
            first.store.contains(
                "presence/secondary_persisted"
            )
        )

        second = self.controller()

        self.assertFalse(
            second.restore_secondary_mode()
        )

    def test_auto_afk_changes_primary_without_touching_secondary(
        self,
    ):
        manager = FakeManager()

        controller = self.controller(
            manager
        )

        controller.store.setValue(
            "presence/afk/artwork_hover_text",
            "AFK hover",
        )

        controller.store.sync()

        mode = self.secondary()

        self.assertTrue(
            controller.apply_secondary_mode(
                mode
            )
        )

        secondary_count = len(
            manager.secondary_updates
        )

        controller.enter_auto_afk()

        self.assertTrue(
            controller.auto_afk_active
        )

        self.assertIs(
            controller.secondary_presence_mode,
            mode,
        )

        self.assertEqual(
            len(
                manager.primary_updates
            ),
            1,
        )

        self.assertEqual(
            manager
            .primary_updates[
                0
            ][
                1
            ][
                "image_name"
            ],
            "AFK hover",
        )

        self.assertEqual(
            len(
                manager.secondary_updates
            ),
            secondary_count,
        )

        self.assertEqual(
            manager.release_calls,
            [],
        )

        controller.leave_auto_afk()

        self.assertFalse(
            controller.auto_afk_active
        )

        self.assertIs(
            controller.secondary_presence_mode,
            mode,
        )

    def test_persisted_secondary_does_not_restore_over_non_music_primary(
        self,
    ):
        first = self.controller()

        self.assertTrue(
            first.apply_secondary_mode(
                self.secondary()
            )
        )

        first.store.setValue(
            "presence/active_mode",
            "working",
        )

        first.store.sync()

        second = PresenceController(
            FakeDiscord(),
            discord_session_manager=(
                FakeManager()
            ),
        )

        second.store = QSettings(
            str(
                self.settings_path
            ),
            QSettings.Format.IniFormat,
        )

        self.assertEqual(
            second.active_mode,
            "working",
        )

        self.assertFalse(
            second.restore_secondary_mode()
        )

    def test_apply_saved_mode_restores_primary_before_secondary(
        self,
    ):
        controller = self.controller()

        events = []

        controller.load_mode = (
            lambda mode: (
                events.append(
                    (
                        "load",
                        mode,
                    )
                )
                or PresenceMode(
                    mode="music"
                )
            )
        )

        controller.apply_mode = (
            lambda mode: events.append(
                (
                    "primary",
                    mode.mode,
                )
            )
        )

        controller.restore_secondary_mode = (
            lambda: (
                events.append(
                    (
                        "secondary",
                        None,
                    )
                )
                or True
            )
        )

        controller.apply_saved_mode()

        self.assertEqual(
            events,
            [
                (
                    "load",
                    "music",
                ),
                (
                    "primary",
                    "music",
                ),
                (
                    "secondary",
                    None,
                ),
            ],
        )


class SessionManagerPrimaryCustomContractTests(
    unittest.TestCase
):
    def test_primary_custom_uses_music_lane(
        self,
    ):
        source = Path(
            "src/discord/session_manager.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        tree = ast.parse(
            source
        )

        cls = next(
            node
            for node in tree.body
            if (
                isinstance(
                    node,
                    ast.ClassDef,
                )
                and node.name
                == "DiscordPresenceSessionManager"
            )
        )

        method = next(
            node
            for node in cls.body
            if (
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and node.name
                == "update_primary_custom"
            )
        )

        segment = ast.get_source_segment(
            source,
            method,
        )

        self.assertIn(
            "MUSIC_LANE_ID",
            segment,
        )

        self.assertNotIn(
            "SECONDARY_LANE_ID",
            segment,
        )


if __name__ == "__main__":
    unittest.main()
