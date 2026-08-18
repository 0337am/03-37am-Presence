import unittest
from unittest.mock import patch

from src.discord.presence import DiscordPresence
from src.discord.ready_identity_presence import (
    PROFILE_IDENTITY_FIELDS,
    ReadyIdentityPresence,
)


class FakeReadyPresence:
    def __init__(
        self,
        client_id,
    ):
        self.client_id = client_id

        self.ready_identity = {
            "user_id": "123456789",
            "username": "03.37am",
            "display_name": "03:37am",
            "avatar_hash": "avatarhash",
        }

    def connect(self):
        return None

    def clear(self):
        return None

    def close(self):
        return None


class DiscordProfileIdentitySnapshotTests(
    unittest.TestCase
):
    def test_ready_payload_keeps_only_profile_fields(self):
        payload = {
            "cmd": "DISPATCH",
            "evt": "READY",
            "data": {
                "user": {
                    "id": "123456789",
                    "username": "03.37am",
                    "global_name": "03:37am",
                    "avatar": "avatarhash",
                    "email": "not-for-preview@example.com",
                    "phone": "not-for-preview",
                    "token": "not-for-preview",
                }
            },
        }

        identity = (
            ReadyIdentityPresence
            .identity_from_ready_payload(
                payload
            )
        )

        self.assertEqual(
            set(identity),
            set(PROFILE_IDENTITY_FIELDS),
        )
        self.assertEqual(
            identity["user_id"],
            "123456789",
        )
        self.assertEqual(
            identity["username"],
            "03.37am",
        )
        self.assertEqual(
            identity["display_name"],
            "03:37am",
        )
        self.assertEqual(
            identity["avatar_hash"],
            "avatarhash",
        )

        self.assertNotIn(
            "email",
            identity,
        )
        self.assertNotIn(
            "phone",
            identity,
        )
        self.assertNotIn(
            "token",
            identity,
        )

    def test_username_is_display_name_fallback(self):
        payload = {
            "data": {
                "user": {
                    "id": "1",
                    "username": "fallback-name",
                    "avatar": None,
                }
            }
        }

        identity = (
            ReadyIdentityPresence
            .identity_from_ready_payload(
                payload
            )
        )

        self.assertEqual(
            identity["display_name"],
            "fallback-name",
        )

    def test_invalid_ready_payload_is_safe(self):
        for payload in (
            None,
            {},
            {"data": None},
            {"data": {}},
            {"data": {"user": None}},
        ):
            self.assertEqual(
                ReadyIdentityPresence
                .identity_from_ready_payload(
                    payload
                ),
                {},
            )

    def test_discord_presence_captures_ready_identity(self):
        presence = DiscordPresence(
            artwork_uploader=object()
        )

        with patch(
            "src.discord.presence.Presence",
            FakeReadyPresence,
        ):
            connected = (
                presence._open_connection()
            )

        self.assertTrue(
            connected
        )
        self.assertEqual(
            presence.profile_identity,
            {
                "user_id": "123456789",
                "username": "03.37am",
                "display_name": "03:37am",
                "avatar_hash": "avatarhash",
            },
        )

        presence._disconnect()

    def test_profile_identity_returns_defensive_copy(self):
        presence = DiscordPresence(
            artwork_uploader=object()
        )

        presence._set_profile_identity(
            {
                "user_id": "1",
                "username": "user",
                "display_name": "Display",
                "avatar_hash": "hash",
                "secret": "discard-me",
            }
        )

        snapshot = (
            presence.profile_identity
        )

        snapshot["username"] = "changed"

        self.assertEqual(
            presence.profile_identity[
                "username"
            ],
            "user",
        )
        self.assertNotIn(
            "secret",
            presence.profile_identity,
        )


if __name__ == "__main__":
    unittest.main()
