from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import patch

from src.discord.identity_preferences import (
    CUSTOM_APPLICATION_ID_SETTING_KEY,
    DEFAULT_DISCORD_APPLICATION_ID,
    IDENTITY_MODE_CUSTOM,
    MODE_SETTING_KEY,
    DiscordIdentityPreferencesStore,
)
from src.discord.presence import DiscordPresence


CUSTOM_APPLICATION_ID = (
    "123456789012345678"
)


def wait_until(
    predicate,
    *,
    timeout: float = 3.0,
):
    deadline = (
        time.monotonic()
        + timeout
    )

    while time.monotonic() < deadline:
        if predicate():
            return

        time.sleep(
            0.01
        )

    raise AssertionError(
        "Timed out waiting for Discord "
        "runtime state."
    )


class FakeRpc:
    def __init__(
        self,
        client_id,
    ):
        self.client_id = client_id
        self.connected = False
        self.clear_count = 0
        self.closed = False
        self.close_thread_id = None

    def connect(self):
        self.connected = True

    def clear(self):
        self.clear_count += 1

    def close(self):
        self.closed = True
        self.close_thread_id = (
            threading.get_ident()
        )

    def update(
        self,
        **options,
    ):
        pass


class FakeRpcFactory:
    def __init__(self):
        self.instances = []
        self.lock = threading.Lock()

    def __call__(
        self,
        client_id,
    ):
        instance = FakeRpc(
            client_id
        )

        with self.lock:
            self.instances.append(
                instance
            )

        return instance

    def count(self):
        with self.lock:
            return len(
                self.instances
            )

    def item(
        self,
        index,
    ):
        with self.lock:
            return self.instances[
                index
            ]


class DiscordIdentityRuntimeTests(
    unittest.TestCase
):
    def make_presence(
        self,
    ):
        presence = DiscordPresence(
            artwork_uploader=object()
        )

        presence.RECONNECT_DELAY_SECONDS = (
            0.05
        )

        presence.MIN_UPDATE_INTERVAL_SECONDS = (
            0.0
        )

        return presence

    def test_request_before_worker_start_changes_identity_without_thread(self):
        presence = self.make_presence()

        resolved = (
            presence.request_client_id(
                CUSTOM_APPLICATION_ID
            )
        )

        self.assertEqual(
            resolved,
            CUSTOM_APPLICATION_ID,
        )

        self.assertEqual(
            presence.active_client_id,
            CUSTOM_APPLICATION_ID,
        )

        self.assertFalse(
            presence.is_running
        )

    def test_requesting_same_identity_does_not_reconnect(self):
        factory = FakeRpcFactory()
        presence = self.make_presence()

        with patch(
            "src.discord.presence.Presence",
            factory,
        ):
            try:
                presence.connect()

                wait_until(
                    lambda:
                    factory.count() == 1
                )

                resolved = (
                    presence.request_client_id(
                        DEFAULT_DISCORD_APPLICATION_ID
                    )
                )

                self.assertEqual(
                    resolved,
                    DEFAULT_DISCORD_APPLICATION_ID,
                )

                time.sleep(
                    0.15
                )

                self.assertEqual(
                    factory.count(),
                    1,
                )

            finally:
                presence.close()

    def test_live_identity_switch_is_worker_owned(self):
        factory = FakeRpcFactory()
        presence = self.make_presence()

        caller_thread_id = (
            threading.get_ident()
        )

        with patch(
            "src.discord.presence.Presence",
            factory,
        ):
            try:
                presence.connect()

                wait_until(
                    lambda:
                    factory.count() == 1
                )

                first_rpc = factory.item(
                    0
                )

                self.assertEqual(
                    first_rpc.client_id,
                    DEFAULT_DISCORD_APPLICATION_ID,
                )

                presence.update_song(
                    None
                )

                wait_until(
                    lambda:
                    first_rpc.clear_count >= 1
                )

                presence.request_client_id(
                    CUSTOM_APPLICATION_ID
                )

                wait_until(
                    lambda:
                    factory.count() >= 2
                )

                second_rpc = factory.item(
                    1
                )

                wait_until(
                    lambda:
                    first_rpc.closed
                )

                self.assertEqual(
                    second_rpc.client_id,
                    CUSTOM_APPLICATION_ID,
                )

                self.assertNotEqual(
                    first_rpc.close_thread_id,
                    caller_thread_id,
                )

                wait_until(
                    lambda:
                    second_rpc.clear_count >= 1
                )

            finally:
                presence.close()

    def test_song_queue_cannot_replace_identity_switch_request(self):
        factory = FakeRpcFactory()
        presence = self.make_presence()

        with patch(
            "src.discord.presence.Presence",
            factory,
        ):
            try:
                presence.connect()

                wait_until(
                    lambda:
                    factory.count() == 1
                )

                presence.request_client_id(
                    CUSTOM_APPLICATION_ID
                )

                presence.update_song(
                    None
                )

                wait_until(
                    lambda:
                    factory.count() >= 2
                )

                second_rpc = factory.item(
                    1
                )

                self.assertEqual(
                    second_rpc.client_id,
                    CUSTOM_APPLICATION_ID,
                )

                wait_until(
                    lambda:
                    second_rpc.clear_count >= 1
                )

            finally:
                presence.close()


class DiscordIdentityStartupWiringTests(
    unittest.TestCase
):
    def test_main_window_loads_identity_before_presence_construction(self):
        from pathlib import Path

        source = (
            Path(
                "src/ui/main_window.py"
            )
            .read_text(
                encoding="utf-8-sig"
            )
        )

        store_position = source.index(
            "DiscordIdentityPreferencesStore()"
        )

        presence_position = source.index(
            "ExtendedDiscordPresence("
        )

        self.assertLess(
            store_position,
            presence_position,
        )

        self.assertIn(
            "resolved_application_id",
            source[
                store_position:
                presence_position + 300
            ],
        )

    def test_invalid_persisted_identity_starts_with_official_identity(self):
        from pathlib import Path
        import tempfile

        from PyQt6.QtCore import QSettings

        with tempfile.TemporaryDirectory() as temp:
            settings = QSettings(
                str(
                    Path(temp)
                    / "identity.ini"
                ),
                QSettings.Format.IniFormat,
            )

            settings.setValue(
                MODE_SETTING_KEY,
                IDENTITY_MODE_CUSTOM,
            )

            settings.setValue(
                CUSTOM_APPLICATION_ID_SETTING_KEY,
                "invalid",
            )

            settings.sync()

            store = (
                DiscordIdentityPreferencesStore(
                    settings
                )
            )

            preferences = (
                store.load()
            )

            presence = DiscordPresence(
                artwork_uploader=object(),
                client_id=(
                    preferences
                    .resolved_application_id
                ),
            )

            self.assertEqual(
                presence.active_client_id,
                DEFAULT_DISCORD_APPLICATION_ID,
            )


if __name__ == "__main__":
    unittest.main()
