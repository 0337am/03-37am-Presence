from __future__ import annotations

import unittest
from pathlib import Path

from src.discord.application_library import (
    DiscordApplicationEntry,
)
from src.discord.session_manager import (
    MUSIC_LANE_ID,
    SECONDARY_LANE_ID,
    DiscordPresenceSessionManager,
    DiscordPresenceSessionManagerError,
)


MUSIC_ENTRY_ID = (
    "discord_app_0123456789abcdef"
)

SECONDARY_ENTRY_ID = (
    "discord_app_fedcba9876543210"
)

MUSIC_APPLICATION_ID = (
    "1523801127962022070"
)

SECONDARY_APPLICATION_ID = (
    "1096663809097203752"
)


MUSIC_ENTRY = DiscordApplicationEntry(
    entry_id=MUSIC_ENTRY_ID,
    name="Music",
    application_id=MUSIC_APPLICATION_ID,
)

SECONDARY_ENTRY = DiscordApplicationEntry(
    entry_id=SECONDARY_ENTRY_ID,
    name="Secondary",
    application_id=SECONDARY_APPLICATION_ID,
)


class FakeSession:
    def __init__(
        self,
        client_id,
    ):
        self.client_id = client_id

        self._is_connected = False
        self._is_running = False

        self._profile_identity = {}

        self.raise_connected = False
        self.raise_running = False
        self.raise_profile = False

        self.clear_count = 0
        self.close_count = 0

    @property
    def is_connected(self):
        if self.raise_connected:
            raise RuntimeError(
                "connected state failed"
            )

        return self._is_connected

    @property
    def is_running(self):
        if self.raise_running:
            raise RuntimeError(
                "running state failed"
            )

        return self._is_running

    @property
    def profile_identity(self):
        if self.raise_profile:
            raise RuntimeError(
                "profile state failed"
            )

        return self._profile_identity

    def connect(self):
        self._is_running = True
        self._is_connected = True
        return True

    def update_song(
        self,
        song,
        *,
        buttons=None,
    ):
        return None

    def update_custom(
        self,
        **payload,
    ):
        return None

    def clear_presence(self):
        self.clear_count += 1

    def close(self):
        self.close_count += 1
        self._is_connected = False
        self._is_running = False


class Factory:
    def __init__(self):
        self.sessions = []

    def __call__(
        self,
        *,
        client_id,
    ):
        session = FakeSession(
            client_id
        )

        self.sessions.append(
            session
        )

        return session


class Resolver:
    def __init__(self):
        self.entries = {
            MUSIC_ENTRY_ID: MUSIC_ENTRY,
            SECONDARY_ENTRY_ID: SECONDARY_ENTRY,
        }

    def __call__(
        self,
        entry_id,
    ):
        return self.entries.get(
            entry_id
        )


def make_manager():
    resolver = Resolver()
    factory = Factory()

    manager = DiscordPresenceSessionManager(
        resolver,
        session_factory=factory,
    )

    return (
        manager,
        resolver,
        factory,
    )


class DiscordPresenceSessionManagerObservabilityTests(
    unittest.TestCase
):
    def test_unbound_lane_is_not_connected(
        self,
    ):
        manager, _, _ = make_manager()

        self.assertFalse(
            manager.lane_is_connected(
                MUSIC_LANE_ID
            )
        )

    def test_unbound_lane_is_not_running(
        self,
    ):
        manager, _, _ = make_manager()

        self.assertFalse(
            manager.lane_is_running(
                MUSIC_LANE_ID
            )
        )

    def test_unbound_lane_has_empty_profile_identity(
        self,
    ):
        manager, _, _ = make_manager()

        self.assertEqual(
            manager.profile_identity_for_lane(
                MUSIC_LANE_ID
            ),
            {},
        )

    def test_bound_lane_forwards_connection_truth(
        self,
    ):
        manager, _, factory = make_manager()

        manager.ensure_lane(
            MUSIC_LANE_ID,
            MUSIC_ENTRY_ID,
        )

        session = factory.sessions[
            0
        ]

        self.assertTrue(
            manager.lane_is_connected(
                MUSIC_LANE_ID
            )
        )

        self.assertTrue(
            manager.lane_is_running(
                MUSIC_LANE_ID
            )
        )

        session._is_connected = False

        self.assertFalse(
            manager.lane_is_connected(
                MUSIC_LANE_ID
            )
        )

        self.assertTrue(
            manager.lane_is_running(
                MUSIC_LANE_ID
            )
        )

    def test_profile_identity_is_forwarded_as_defensive_copy(
        self,
    ):
        manager, _, factory = make_manager()

        manager.ensure_lane(
            MUSIC_LANE_ID,
            MUSIC_ENTRY_ID,
        )

        source = {
            "username": "03:37am",
            "avatar_url": "https://example.com/avatar.png",
        }

        factory.sessions[
            0
        ]._profile_identity = source

        first = (
            manager.profile_identity_for_lane(
                MUSIC_LANE_ID
            )
        )

        self.assertEqual(
            first,
            source,
        )

        self.assertIsNot(
            first,
            source,
        )

        first[
            "username"
        ] = "changed"

        self.assertEqual(
            manager.profile_identity_for_lane(
                MUSIC_LANE_ID
            )[
                "username"
            ],
            "03:37am",
        )

    def test_non_dict_profile_identity_fails_closed(
        self,
    ):
        manager, _, factory = make_manager()

        manager.ensure_lane(
            MUSIC_LANE_ID,
            MUSIC_ENTRY_ID,
        )

        factory.sessions[
            0
        ]._profile_identity = (
            "not-a-dict"
        )

        self.assertEqual(
            manager.profile_identity_for_lane(
                MUSIC_LANE_ID
            ),
            {},
        )

    def test_observability_property_exceptions_fail_closed(
        self,
    ):
        manager, _, factory = make_manager()

        manager.ensure_lane(
            MUSIC_LANE_ID,
            MUSIC_ENTRY_ID,
        )

        session = factory.sessions[
            0
        ]

        session.raise_connected = True
        session.raise_running = True
        session.raise_profile = True

        self.assertFalse(
            manager.lane_is_connected(
                MUSIC_LANE_ID
            )
        )

        self.assertFalse(
            manager.lane_is_running(
                MUSIC_LANE_ID
            )
        )

        self.assertEqual(
            manager.profile_identity_for_lane(
                MUSIC_LANE_ID
            ),
            {},
        )

    def test_music_and_secondary_observability_are_independent(
        self,
    ):
        manager, _, factory = make_manager()

        manager.ensure_lane(
            MUSIC_LANE_ID,
            MUSIC_ENTRY_ID,
        )

        manager.ensure_lane(
            SECONDARY_LANE_ID,
            SECONDARY_ENTRY_ID,
        )

        music = factory.sessions[
            0
        ]

        secondary = factory.sessions[
            1
        ]

        music._profile_identity = {
            "username": "Music",
        }

        secondary._profile_identity = {
            "username": "Secondary",
        }

        music._is_connected = False

        self.assertFalse(
            manager.lane_is_connected(
                MUSIC_LANE_ID
            )
        )

        self.assertTrue(
            manager.lane_is_connected(
                SECONDARY_LANE_ID
            )
        )

        self.assertEqual(
            manager.profile_identity_for_lane(
                MUSIC_LANE_ID
            ),
            {
                "username": "Music",
            },
        )

        self.assertEqual(
            manager.profile_identity_for_lane(
                SECONDARY_LANE_ID
            ),
            {
                "username": "Secondary",
            },
        )

    def test_invalid_lane_is_rejected_consistently(
        self,
    ):
        manager, _, _ = make_manager()

        for method in (
            manager.lane_is_connected,
            manager.lane_is_running,
            manager.profile_identity_for_lane,
        ):
            with self.assertRaises(
                DiscordPresenceSessionManagerError
            ):
                method(
                    "third"
                )

    def test_observability_exposes_no_raw_session_accessor(
        self,
    ):
        source = Path(
            "src/discord/session_manager.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "def lane_is_connected(",
            source,
        )

        self.assertIn(
            "def lane_is_running(",
            source,
        )

        self.assertIn(
            "def profile_identity_for_lane(",
            source,
        )

        for forbidden in (
            "def session_for_lane(",
            "def rpc_for_lane(",
            "from src.ui",
        ):
            self.assertNotIn(
                forbidden,
                source,
            )


if __name__ == "__main__":
    unittest.main()
