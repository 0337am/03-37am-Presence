from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from src.discord.application_library import (
    BUILTIN_APPLICATION_ENTRY_ID,
)
from src.discord.presence_controller import (
    PresenceController,
)
from src.discord.presence_modes import (
    PresenceMode,
)


USER_APPLICATION_ENTRY_ID = (
    "discord_app_0123456789abcdef"
)

SECOND_APPLICATION_ENTRY_ID = (
    "discord_app_fedcba9876543210"
)


class _MemorySettings:
    def __init__(
        self,
        values=None,
    ):
        self.values = dict(
            values or {}
        )
        self.sync_count = 0

    def value(
        self,
        key,
        default=None,
        type=None,
    ):
        value = self.values.get(
            key,
            default,
        )

        if type is bool:
            return bool(
                value
            )

        return value

    def setValue(
        self,
        key,
        value,
    ):
        self.values[
            key
        ] = value

    def sync(self):
        self.sync_count += 1

    def contains(
        self,
        key,
    ):
        return key in self.values


def _controller(
    values=None,
) -> PresenceController:
    controller = PresenceController(
        object()
    )

    controller.store = _MemorySettings(
        values
    )

    return controller


class PresenceModeApplicationAssignmentTests(
    unittest.TestCase
):
    def test_unspecified_assignment_remains_none_in_raw_model(
        self,
    ):
        mode = PresenceMode(
            mode="custom"
        )

        self.assertIsNone(
            mode.application_entry_id
        )

        self.assertIsNone(
            mode.normalized_application_entry_id()
        )

    def test_assignment_is_exposed_in_payload(
        self,
    ):
        mode = PresenceMode(
            mode="custom",
            application_entry_id=(
                USER_APPLICATION_ENTRY_ID
            ),
        )

        self.assertEqual(
            mode.to_payload()[
                "application_entry_id"
            ],
            USER_APPLICATION_ENTRY_ID,
        )

    def test_assignment_normalization_trims_text(
        self,
    ):
        mode = PresenceMode(
            mode="custom",
            application_entry_id=(
                "  "
                + USER_APPLICATION_ENTRY_ID
                + "  "
            ),
        )

        self.assertEqual(
            mode.normalized_application_entry_id(),
            USER_APPLICATION_ENTRY_ID,
        )

    def test_blank_assignment_is_unspecified(
        self,
    ):
        mode = PresenceMode(
            mode="custom",
            application_entry_id="   ",
        )

        self.assertIsNone(
            mode.normalized_application_entry_id()
        )


class PresenceControllerApplicationAssignmentTests(
    unittest.TestCase
):
    def test_old_mode_without_assignment_defaults_to_builtin(
        self,
    ):
        controller = _controller()

        mode = controller.load_mode(
            "custom"
        )

        self.assertEqual(
            mode.application_entry_id,
            BUILTIN_APPLICATION_ENTRY_ID,
        )

    def test_explicit_builtin_assignment_round_trips(
        self,
    ):
        controller = _controller()

        controller.save_mode(
            PresenceMode(
                mode="custom",
                application_entry_id=(
                    BUILTIN_APPLICATION_ENTRY_ID
                ),
            )
        )

        restored = controller.load_mode(
            "custom"
        )

        self.assertEqual(
            restored.application_entry_id,
            BUILTIN_APPLICATION_ENTRY_ID,
        )

    def test_user_application_assignment_round_trips(
        self,
    ):
        controller = _controller()

        controller.save_mode(
            PresenceMode(
                mode="custom",
                application_entry_id=(
                    USER_APPLICATION_ENTRY_ID
                ),
            )
        )

        restored = controller.load_mode(
            "custom"
        )

        self.assertEqual(
            restored.application_entry_id,
            USER_APPLICATION_ENTRY_ID,
        )

    def test_missing_but_valid_reference_is_preserved(
        self,
    ):
        controller = _controller(
            {
                (
                    "presence/custom/"
                    "application_entry_id"
                ): USER_APPLICATION_ENTRY_ID,
            }
        )

        restored = controller.load_mode(
            "custom"
        )

        self.assertEqual(
            restored.application_entry_id,
            USER_APPLICATION_ENTRY_ID,
        )

    def test_malformed_saved_reference_fails_closed_to_builtin(
        self,
    ):
        controller = _controller(
            {
                (
                    "presence/custom/"
                    "application_entry_id"
                ): "../../not-an-entry",
            }
        )

        restored = controller.load_mode(
            "custom"
        )

        self.assertEqual(
            restored.application_entry_id,
            BUILTIN_APPLICATION_ENTRY_ID,
        )

    def test_malformed_explicit_assignment_saves_builtin(
        self,
    ):
        controller = _controller()

        controller.save_mode(
            PresenceMode(
                mode="custom",
                application_entry_id=(
                    "not-a-library-entry"
                ),
            )
        )

        self.assertEqual(
            controller.store.values[
                (
                    "presence/custom/"
                    "application_entry_id"
                )
            ],
            BUILTIN_APPLICATION_ENTRY_ID,
        )

    def test_unaware_editor_does_not_overwrite_assignment(
        self,
    ):
        controller = _controller(
            {
                (
                    "presence/custom/"
                    "application_entry_id"
                ): USER_APPLICATION_ENTRY_ID,
            }
        )

        controller.save_mode(
            PresenceMode(
                mode="custom",
                title="Edited title",
                message="Edited message",
            )
        )

        self.assertEqual(
            controller.store.values[
                (
                    "presence/custom/"
                    "application_entry_id"
                )
            ],
            USER_APPLICATION_ENTRY_ID,
        )

    def test_mode_assignments_are_independent(
        self,
    ):
        controller = _controller()

        controller.save_mode(
            PresenceMode(
                mode="music",
                application_entry_id=(
                    USER_APPLICATION_ENTRY_ID
                ),
            )
        )

        controller.save_mode(
            PresenceMode(
                mode="custom",
                application_entry_id=(
                    SECOND_APPLICATION_ENTRY_ID
                ),
            )
        )

        music = controller.load_mode(
            "music"
        )

        custom = controller.load_mode(
            "custom"
        )

        self.assertEqual(
            music.application_entry_id,
            USER_APPLICATION_ENTRY_ID,
        )

        self.assertEqual(
            custom.application_entry_id,
            SECOND_APPLICATION_ENTRY_ID,
        )

    def test_disabled_mode_does_not_persist_assignment(
        self,
    ):
        controller = _controller()

        controller.save_mode(
            PresenceMode(
                mode="disabled",
                application_entry_id=(
                    USER_APPLICATION_ENTRY_ID
                ),
            )
        )

        self.assertFalse(
            controller.store.contains(
                (
                    "presence/disabled/"
                    "application_entry_id"
                )
            )
        )

    def test_loaded_payload_reports_effective_assignment(
        self,
    ):
        controller = _controller(
            {
                (
                    "presence/working/"
                    "application_entry_id"
                ): USER_APPLICATION_ENTRY_ID,
            }
        )

        mode = controller.load_mode(
            "working"
        )

        self.assertEqual(
            mode.to_payload()[
                "application_entry_id"
            ],
            USER_APPLICATION_ENTRY_ID,
        )

    def test_load_mode_preserves_unbound_lightweight_shell_compatibility(
        self,
    ):
        shell = SimpleNamespace(
            store=_MemorySettings()
        )

        mode = PresenceController.load_mode(
            shell,
            "music",
        )

        self.assertEqual(
            mode.application_entry_id,
            BUILTIN_APPLICATION_ENTRY_ID,
        )


class PresenceApplicationAssignmentBoundaryTests(
    unittest.TestCase
):
    def test_a04_controller_does_not_own_preset_persistence(
        self,
    ):
        controller_source = Path(
            "src/discord/presence_controller.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        mode_source = Path(
            "src/discord/presence_modes.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertNotIn(
            "PresencePresetStore",
            controller_source,
        )

        self.assertNotIn(
            "PresencePreset",
            controller_source,
        )

        self.assertNotIn(
            "presence_presets",
            mode_source,
        )

    def test_controller_does_not_switch_discord_identity(
        self,
    ):
        source = Path(
            "src/discord/presence_controller.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertNotIn(
            "request_client_id",
            source,
        )

        self.assertNotIn(
            "ExtendedDiscordPresence",
            source,
        )

        self.assertNotIn(
            "pypresence",
            source.casefold(),
        )

    def test_main_window_controller_wiring_is_unchanged(
        self,
    ):
        source = Path(
            "src/ui/main_window.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        start = source.index(
            "self.presence_controller = ("
        )

        end = source.index(
            "self.afk_preferences_store = (",
            start,
        )

        wiring = source[
            start:end
        ]

        self.assertIn(
            "PresenceController(",
            wiring,
        )

        self.assertIn(
            "self.discord",
            wiring,
        )

        self.assertNotIn(
            "discord_application_library_store",
            wiring,
        )


if __name__ == "__main__":
    unittest.main()
