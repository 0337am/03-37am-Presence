import inspect
from pathlib import Path
import unittest

import src.ui.discord_avatar_loader as avatar_loader
from src.ui.discord_avatar_loader import (
    DISCORD_AVATAR_SIZE,
    DiscordAvatarLoader,
    discord_avatar_url,
)


class DiscordAvatarLoaderTests(
    unittest.TestCase
):
    def test_custom_avatar_url(self):
        url = discord_avatar_url(
            "123456789012345678",
            "a_012345abcdef",
        )

        self.assertEqual(
            url,
            (
                "https://cdn.discordapp.com/"
                "avatars/123456789012345678/"
                "a_012345abcdef.png?size=128"
            ),
        )

    def test_default_avatar_url_uses_user_id(self):
        user_id = "123456789012345678"

        index = (
            int(user_id) >> 22
        ) % 6

        self.assertEqual(
            discord_avatar_url(
                user_id,
                "",
            ),
            (
                "https://cdn.discordapp.com/"
                f"embed/avatars/{index}.png"
            ),
        )

    def test_invalid_user_id_is_rejected(self):
        for value in (
            "",
            None,
            "not-a-user",
            "../123",
        ):
            self.assertEqual(
                discord_avatar_url(
                    value,
                    "abc",
                ),
                "",
            )

    def test_invalid_avatar_hash_is_rejected(self):
        self.assertEqual(
            discord_avatar_url(
                "123456789",
                "../avatar",
            ),
            "",
        )

    def test_image_size_must_be_supported_power_of_two(self):
        self.assertTrue(
            discord_avatar_url(
                "123456789",
                "abc",
                size=DISCORD_AVATAR_SIZE,
            )
        )

        self.assertEqual(
            discord_avatar_url(
                "123456789",
                "abc",
                size=100,
            ),
            "",
        )

    def test_loader_uses_qt_network_boundary(self):
        source = Path(
            inspect.getsourcefile(
                DiscordAvatarLoader
            )
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "QNetworkAccessManager",
            source,
        )
        self.assertIn(
            "setTransferTimeout",
            source,
        )
        self.assertIn(
            "DISCORD_AVATAR_MAX_BYTES",
            source,
        )

        self.assertNotIn(
            "requests.",
            source,
        )
        self.assertNotIn(
            "urllib",
            source,
        )
        self.assertNotIn(
            "access_token",
            source,
        )
        self.assertNotIn(
            "refresh_token",
            source,
        )

    def test_cdn_host_is_fixed(self):
        source = Path(
            avatar_loader.__file__
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "cdn.discordapp.com",
            source,
        )


if __name__ == "__main__":
    unittest.main()
