from __future__ import annotations

import ast
import inspect
import textwrap
import unittest
from types import SimpleNamespace

from src.discord.extended_presence import (
    CustomPresenceUpdate,
    ExtendedDiscordPresence,
    SongPresenceUpdate,
)
from src.discord.presence import (
    DiscordPresence,
)
from src.discord.presence_controller import (
    PresenceController,
)
from src.discord.presence_link_buttons import (
    PresenceLinkButton,
)
from src.discord.presence_modes import (
    PresenceMode,
)


class FakeRpc:
    def __init__(self):
        self.updates = []
        self.clear_count = 0

    def update(
        self,
        **options,
    ):
        self.updates.append(
            dict(options)
        )

    def clear(self):
        self.clear_count += 1


class FakeArtworkUploader:
    is_configured = False


def make_song(
    *,
    title="Track",
    artist="Artist",
    playing=True,
):
    return SimpleNamespace(
        title=title,
        artist=artist,
        album="Album",
        duration="3:00",
        position="0:30",
        playing=playing,
        artwork_bytes=b"",
        source_app="Spotify.exe",
    )


def model_buttons():
    return (
        PresenceLinkButton(
            label="Website",
            url="https://example.com/",
        ),
        PresenceLinkButton(
            label="Discord",
            url="https://discord.com/",
        ),
    )


def rpc_buttons():
    return [
        {
            "label": "Website",
            "url": "https://example.com/",
        },
        {
            "label": "Discord",
            "url": "https://discord.com/",
        },
    ]


def method_node(method):
    source = textwrap.dedent(
        inspect.getsource(
            method
        )
    )

    tree = ast.parse(
        source
    )

    return tree.body[0]


def calls_named(
    node,
    name,
):
    result = []

    for candidate in ast.walk(
        node
    ):
        if not isinstance(
            candidate,
            ast.Call,
        ):
            continue

        function = candidate.func

        if (
            isinstance(
                function,
                ast.Attribute,
            )
            and function.attr == name
        ):
            result.append(
                candidate
            )

    return result


def has_keyword(
    call,
    name,
):
    return any(
        keyword.arg == name
        for keyword in call.keywords
    )


class DiscordBaseMusicButtonPublishingTests(
    unittest.TestCase
):
    def make_presence(self):
        presence = DiscordPresence(
            artwork_uploader=(
                FakeArtworkUploader()
            )
        )

        presence.rpc = FakeRpc()

        return presence

    def test_music_publish_without_buttons_omits_button_field(
        self,
    ):
        presence = self.make_presence()

        presence._publish_song(
            make_song(),
            buttons=[],
        )

        self.assertNotIn(
            "buttons",
            presence.rpc.updates[-1],
        )

    def test_music_publish_sends_configured_buttons(
        self,
    ):
        presence = self.make_presence()

        presence._publish_song(
            make_song(),
            buttons=rpc_buttons(),
        )

        self.assertEqual(
            presence.rpc.updates[-1][
                "buttons"
            ],
            rpc_buttons(),
        )


class ExtendedPresenceButtonPublishingTests(
    unittest.TestCase
):
    def make_presence(self):
        presence = ExtendedDiscordPresence(
            artwork_uploader=(
                FakeArtworkUploader()
            )
        )

        presence.rpc = FakeRpc()

        return presence

    def test_old_custom_update_constructor_remains_compatible(
        self,
    ):
        update = CustomPresenceUpdate(
            title="Custom",
            message="Status",
            image_bytes=None,
            image_name="",
            show_elapsed=False,
            started_at=None,
        )

        self.assertEqual(
            update.buttons,
            (),
        )

    def test_custom_publish_sends_buttons(
        self,
    ):
        presence = self.make_presence()

        update = CustomPresenceUpdate(
            title="Custom",
            message="Status",
            image_bytes=None,
            image_name="",
            show_elapsed=False,
            started_at=None,
            buttons=(
                (
                    "Website",
                    "https://example.com/",
                ),
            ),
        )

        presence._publish_custom(
            update
        )

        self.assertEqual(
            presence.rpc.updates[-1][
                "buttons"
            ],
            [
                {
                    "label": "Website",
                    "url": "https://example.com/",
                }
            ],
        )

    def test_custom_without_buttons_omits_button_field(
        self,
    ):
        presence = self.make_presence()

        update = CustomPresenceUpdate(
            title="Custom",
            message="Status",
            image_bytes=None,
            image_name="",
            show_elapsed=False,
            started_at=None,
            buttons=(),
        )

        presence._publish_custom(
            update
        )

        self.assertNotIn(
            "buttons",
            presence.rpc.updates[-1],
        )

    def test_update_custom_queues_normalized_buttons(
        self,
    ):
        presence = self.make_presence()

        presence.update_custom(
            title="Custom",
            message="Status",
            buttons=rpc_buttons(),
        )

        item = (
            presence._updates
            .get_nowait()
        )

        self.assertIsInstance(
            item,
            CustomPresenceUpdate,
        )

        self.assertEqual(
            item.buttons,
            (
                (
                    "Website",
                    "https://example.com/",
                ),
                (
                    "Discord",
                    "https://discord.com/",
                ),
            ),
        )

    def test_update_song_queues_song_and_buttons_together(
        self,
    ):
        presence = self.make_presence()

        song = make_song()

        presence.update_song(
            song,
            buttons=rpc_buttons(),
        )

        item = (
            presence._updates
            .get_nowait()
        )

        self.assertIsInstance(
            item,
            SongPresenceUpdate,
        )

        self.assertIs(
            item.song,
            song,
        )

        self.assertEqual(
            item.buttons,
            (
                (
                    "Website",
                    "https://example.com/",
                ),
                (
                    "Discord",
                    "https://discord.com/",
                ),
            ),
        )

    def test_song_wrapper_preserves_playing_state(
        self,
    ):
        update = SongPresenceUpdate(
            song=make_song(
                playing=True
            ),
            buttons=(),
        )

        self.assertTrue(
            update.playing
        )

    def test_song_wrapper_publishes_music_buttons(
        self,
    ):
        presence = self.make_presence()

        item = SongPresenceUpdate(
            song=make_song(),
            buttons=(
                (
                    "Website",
                    "https://example.com/",
                ),
            ),
        )

        presence._publish_song(
            item
        )

        self.assertEqual(
            presence.rpc.updates[-1][
                "buttons"
            ],
            [
                {
                    "label": "Website",
                    "url": "https://example.com/",
                }
            ],
        )

    def test_music_dedupe_key_changes_when_only_buttons_change(
        self,
    ):
        song = make_song()

        first = SongPresenceUpdate(
            song=song,
            buttons=(),
        )

        second = SongPresenceUpdate(
            song=song,
            buttons=(
                (
                    "Website",
                    "https://example.com/",
                ),
            ),
        )

        self.assertNotEqual(
            ExtendedDiscordPresence
            ._make_presence_key(
                first
            ),
            ExtendedDiscordPresence
            ._make_presence_key(
                second
            ),
        )

    def test_custom_dedupe_key_changes_when_only_buttons_change(
        self,
    ):
        first = CustomPresenceUpdate(
            title="Custom",
            message="Status",
            image_bytes=None,
            image_name="",
            show_elapsed=False,
            started_at=None,
            buttons=(),
        )

        second = CustomPresenceUpdate(
            title="Custom",
            message="Status",
            image_bytes=None,
            image_name="",
            show_elapsed=False,
            started_at=None,
            buttons=(
                (
                    "Website",
                    "https://example.com/",
                ),
            ),
        )

        self.assertNotEqual(
            ExtendedDiscordPresence
            ._make_presence_key(
                first
            ),
            ExtendedDiscordPresence
            ._make_presence_key(
                second
            ),
        )


class ControllerButtonPayloadTests(
    unittest.TestCase
):
    def test_enabled_custom_mode_returns_rpc_buttons(
        self,
    ):
        result = (
            PresenceController
            ._discord_buttons_for_mode(
                PresenceMode(
                    mode="custom",
                    show_buttons=True,
                    buttons=model_buttons(),
                )
            )
        )

        self.assertEqual(
            result,
            rpc_buttons(),
        )

    def test_hidden_buttons_return_explicit_empty_list(
        self,
    ):
        result = (
            PresenceController
            ._discord_buttons_for_mode(
                PresenceMode(
                    mode="custom",
                    show_buttons=False,
                    buttons=model_buttons(),
                )
            )
        )

        self.assertEqual(
            result,
            [],
        )

    def test_music_uses_same_button_contract(
        self,
    ):
        result = (
            PresenceController
            ._discord_buttons_for_mode(
                PresenceMode(
                    mode="music",
                    show_buttons=True,
                    buttons=model_buttons(),
                )
            )
        )

        self.assertEqual(
            result,
            rpc_buttons(),
        )


class ControllerPublishingAstTests(
    unittest.TestCase
):
    def test_apply_mode_forwards_buttons_to_music_and_custom(
        self,
    ):
        node = method_node(
            PresenceController.apply_mode
        )

        song_calls = calls_named(
            node,
            "update_song",
        )

        custom_calls = calls_named(
            node,
            "update_custom",
        )

        self.assertTrue(
            any(
                has_keyword(
                    call,
                    "buttons",
                )
                for call in song_calls
            )
        )

        self.assertTrue(
            any(
                has_keyword(
                    call,
                    "buttons",
                )
                for call in custom_calls
            )
        )

    def test_auto_afk_forwards_saved_buttons(
        self,
    ):
        node = method_node(
            PresenceController.enter_auto_afk
        )

        calls = calls_named(
            node,
            "update_custom",
        )

        self.assertTrue(
            any(
                has_keyword(
                    call,
                    "buttons",
                )
                for call in calls
            )
        )

    def test_automatic_music_updates_forward_buttons(
        self,
    ):
        node = method_node(
            PresenceController.handle_song
        )

        update_calls = calls_named(
            node,
            "update_song",
        )

        self.assertTrue(
            any(
                has_keyword(
                    call,
                    "buttons",
                )
                for call in update_calls
            )
        )

        load_calls = calls_named(
            node,
            "load_mode",
        )

        music_load = False

        for call in load_calls:
            for argument in call.args:
                if (
                    isinstance(
                        argument,
                        ast.Constant,
                    )
                    and argument.value == "music"
                ):
                    music_load = True

        self.assertTrue(
            music_load
        )


if __name__ == "__main__":
    unittest.main()
