from __future__ import annotations

import unittest

from src.discord.extended_presence import (
    CustomPresenceUpdate,
    ExtendedDiscordPresence,
)


class FakeRpc:
    def __init__(self):
        self.updates = []

    def update(
        self,
        **options,
    ):
        self.updates.append(
            dict(options)
        )


class FakeArtworkUploader:
    is_configured = False


class DiscordPartyPresenceTests(
    unittest.TestCase
):
    @staticmethod
    def make_presence():
        presence = ExtendedDiscordPresence(
            artwork_uploader=(
                FakeArtworkUploader()
            )
        )

        presence.rpc = FakeRpc()

        return presence

    def test_old_constructor_defaults_party_off(self):
        update = CustomPresenceUpdate(
            title="Custom",
            message="Status",
            image_bytes=None,
            image_name="",
            show_elapsed=False,
            started_at=None,
        )

        self.assertIsNone(
            update.party_size
        )

    def test_native_party_size_is_published(self):
        presence = self.make_presence()

        update = CustomPresenceUpdate(
            title="Floor 22",
            message="Exploring",
            image_bytes=None,
            image_name="",
            show_elapsed=False,
            started_at=None,
            party_size=(1, 2),
        )

        presence._publish_custom(
            update
        )

        self.assertEqual(
            presence.rpc.updates[-1][
                "party_size"
            ],
            [1, 2],
        )

    def test_disabled_party_is_omitted(self):
        presence = self.make_presence()

        update = CustomPresenceUpdate(
            title="Custom",
            message="Status",
            image_bytes=None,
            image_name="",
            show_elapsed=False,
            started_at=None,
        )

        presence._publish_custom(
            update
        )

        self.assertNotIn(
            "party_size",
            presence.rpc.updates[-1],
        )

    def test_update_custom_queues_party_with_presence(self):
        presence = self.make_presence()

        presence.update_custom(
            title="Floor 22",
            message="Exploring",
            party_size=[4, 10],
        )

        update = (
            presence._updates
            .get_nowait()
        )

        self.assertEqual(
            update.party_size,
            (4, 10),
        )

    def test_invalid_party_size_fails_closed(self):
        presence = self.make_presence()

        presence.update_custom(
            title="Custom",
            message="Status",
            party_size=[5, 2],
        )

        update = (
            presence._updates
            .get_nowait()
        )

        self.assertIsNone(
            update.party_size
        )

    def test_party_change_changes_dedupe_key(self):
        first = CustomPresenceUpdate(
            title="Floor 22",
            message="Exploring",
            image_bytes=None,
            image_name="",
            show_elapsed=False,
            started_at=None,
            party_size=(1, 2),
        )

        second = CustomPresenceUpdate(
            title="Floor 22",
            message="Exploring",
            image_bytes=None,
            image_name="",
            show_elapsed=False,
            started_at=None,
            party_size=(2, 2),
        )

        first_key = (
            ExtendedDiscordPresence
            ._make_presence_key(
                first
            )
        )

        second_key = (
            ExtendedDiscordPresence
            ._make_presence_key(
                second
            )
        )

        self.assertNotEqual(
            first_key,
            second_key,
        )


if __name__ == "__main__":
    unittest.main()
