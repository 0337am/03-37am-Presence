import unittest
from types import SimpleNamespace

from src.discord.presence_controller import (
    PresenceController,
)
from src.discord.presence_modes import (
    PresenceMode,
)


class FakeStore:
    def __init__(
        self,
        initial=None,
    ):
        self.data = dict(
            initial or {}
        )
        self.sync_count = 0

    def value(
        self,
        key,
        default=None,
        type=None,
    ):
        value = self.data.get(
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
        self.data[key] = value

    def sync(self):
        self.sync_count += 1


class DiscordLoopCountPreferenceTests(
    unittest.TestCase
):
    def test_presence_mode_defaults_loop_count_off(
        self,
    ):
        mode = PresenceMode(
            mode="music"
        )

        self.assertFalse(
            mode.show_loop_count
        )

    def test_legacy_positional_presence_mode_order_is_preserved(
        self,
    ):
        mode = PresenceMode(
            "custom",
            "Title",
            "Message",
            "",
            False,
            True,
            (),
        )

        self.assertTrue(
            mode.show_buttons
        )
        self.assertEqual(
            mode.buttons,
            (),
        )
        self.assertFalse(
            mode.show_loop_count
        )

    def test_music_payload_can_enable_loop_count(
        self,
    ):
        mode = PresenceMode(
            mode="music",
            show_loop_count=True,
        )

        self.assertTrue(
            mode.to_payload()[
                "show_loop_count"
            ]
        )

    def test_non_music_payload_suppresses_loop_count(
        self,
    ):
        mode = PresenceMode(
            mode="custom",
            show_loop_count=True,
        )

        self.assertFalse(
            mode.to_payload()[
                "show_loop_count"
            ]
        )

    def test_controller_load_defaults_music_loop_count_off(
        self,
    ):
        shell = SimpleNamespace(
            store=FakeStore()
        )

        mode = PresenceController.load_mode(
            shell,
            "music",
        )

        self.assertFalse(
            mode.show_loop_count
        )

    def test_controller_load_restores_music_loop_count(
        self,
    ):
        shell = SimpleNamespace(
            store=FakeStore(
                {
                    "presence/music/show_loop_count": True,
                }
            )
        )

        mode = PresenceController.load_mode(
            shell,
            "music",
        )

        self.assertTrue(
            mode.show_loop_count
        )

    def test_controller_load_suppresses_non_music_loop_count(
        self,
    ):
        shell = SimpleNamespace(
            store=FakeStore(
                {
                    "presence/custom/show_loop_count": True,
                }
            )
        )

        mode = PresenceController.load_mode(
            shell,
            "custom",
        )

        self.assertFalse(
            mode.show_loop_count
        )

    def test_controller_save_persists_music_loop_count(
        self,
    ):
        store = FakeStore()

        shell = SimpleNamespace(
            store=store
        )

        PresenceController.save_mode(
            shell,
            PresenceMode(
                mode="music",
                show_loop_count=True,
            ),
        )

        self.assertIs(
            store.data[
                "presence/music/show_loop_count"
            ],
            True,
        )

    def test_controller_save_does_not_create_custom_loop_setting(
        self,
    ):
        store = FakeStore()

        shell = SimpleNamespace(
            store=store
        )

        PresenceController.save_mode(
            shell,
            PresenceMode(
                mode="custom",
                show_loop_count=True,
            ),
        )

        self.assertNotIn(
            "presence/custom/show_loop_count",
            store.data,
        )


if __name__ == "__main__":
    unittest.main()