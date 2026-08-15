from __future__ import annotations

import unittest

from src.discord.presence_link_buttons import (
    MAX_PRESENCE_LINK_LABEL_LENGTH,
    MAX_PRESENCE_LINK_URL_LENGTH,
    PresenceLinkButton,
    PresenceLinkButtonError,
    decode_presence_buttons,
    encode_presence_buttons,
    normalize_presence_buttons,
)
from src.discord.presence_modes import (
    PresenceMode,
)


class PresenceLinkButtonTests(
    unittest.TestCase
):
    def test_valid_button_normalizes(
        self,
    ):
        button = PresenceLinkButton(
            label="  Website  ",
            url=(
                "HTTPS://example.com/profile"
            ),
        ).normalized()

        self.assertEqual(
            button.label,
            "Website",
        )

        self.assertEqual(
            button.url,
            "https://example.com/profile",
        )

    def test_only_http_and_https_are_allowed(
        self,
    ):
        for url in (
            "javascript:alert(1)",
            "file:///C:/secret.txt",
            "spotify:track:abc",
            "ftp://example.com/file",
        ):
            with self.subTest(
                url=url
            ):
                with self.assertRaises(
                    PresenceLinkButtonError
                ):
                    PresenceLinkButton(
                        label="Open",
                        url=url,
                    ).normalized()

    def test_embedded_credentials_are_rejected(
        self,
    ):
        with self.assertRaises(
            PresenceLinkButtonError
        ):
            PresenceLinkButton(
                label="Open",
                url=(
                    "https://user:pass@example.com/"
                ),
            ).normalized()

    def test_url_whitespace_is_rejected(
        self,
    ):
        with self.assertRaises(
            PresenceLinkButtonError
        ):
            PresenceLinkButton(
                label="Open",
                url=(
                    "https://example.com/bad path"
                ),
            ).normalized()

    def test_empty_label_is_rejected(
        self,
    ):
        with self.assertRaises(
            PresenceLinkButtonError
        ):
            PresenceLinkButton(
                label="   ",
                url="https://example.com/",
            ).normalized()

    def test_label_limit_matches_discord_contract(
        self,
    ):
        accepted = PresenceLinkButton(
            label=(
                "L"
                * MAX_PRESENCE_LINK_LABEL_LENGTH
            ),
            url="https://example.com/",
        ).normalized()

        self.assertEqual(
            len(
                accepted.label
            ),
            (
                MAX_PRESENCE_LINK_LABEL_LENGTH
            ),
        )

        with self.assertRaises(
            PresenceLinkButtonError
        ):
            PresenceLinkButton(
                label=(
                    "L"
                    * (
                        MAX_PRESENCE_LINK_LABEL_LENGTH
                        + 1
                    )
                ),
                url="https://example.com/",
            ).normalized()

    def test_url_limit_matches_discord_contract(
        self,
    ):
        prefix = (
            "https://example.com/"
        )

        accepted_url = (
            prefix
            + (
                "a"
                * (
                    MAX_PRESENCE_LINK_URL_LENGTH
                    - len(prefix)
                )
            )
        )

        accepted = PresenceLinkButton(
            label="Open",
            url=accepted_url,
        ).normalized()

        self.assertEqual(
            len(
                accepted.url
            ),
            MAX_PRESENCE_LINK_URL_LENGTH,
        )

        with self.assertRaises(
            PresenceLinkButtonError
        ):
            PresenceLinkButton(
                label="Open",
                url=(
                    accepted_url
                    + "a"
                ),
            ).normalized()

    def test_at_most_two_buttons_are_allowed(
        self,
    ):
        buttons = tuple(
            PresenceLinkButton(
                label=f"Button {index}",
                url=(
                    f"https://example.com/{index}"
                ),
            )
            for index in range(
                3
            )
        )

        with self.assertRaises(
            PresenceLinkButtonError
        ):
            normalize_presence_buttons(
                buttons
            )

    def test_dictionary_entries_are_supported(
        self,
    ):
        buttons = normalize_presence_buttons(
            [
                {
                    "label": "Website",
                    "url": (
                        "https://example.com/"
                    ),
                },
                {
                    "label": "Discord",
                    "url": (
                        "https://discord.com/"
                    ),
                },
            ]
        )

        self.assertEqual(
            len(buttons),
            2,
        )

        self.assertEqual(
            buttons[0].label,
            "Website",
        )

        self.assertEqual(
            buttons[1].label,
            "Discord",
        )

    def test_json_round_trip(
        self,
    ):
        original = (
            PresenceLinkButton(
                label="Website",
                url=(
                    "https://example.com/"
                ),
            ),
            PresenceLinkButton(
                label="Discord",
                url=(
                    "https://discord.com/"
                ),
            ),
        )

        encoded = encode_presence_buttons(
            original
        )

        decoded = decode_presence_buttons(
            encoded
        )

        self.assertEqual(
            decoded,
            original,
        )


class PresenceModeLinkButtonTests(
    unittest.TestCase
):
    def make_buttons(
        self,
    ):
        return (
            PresenceLinkButton(
                label="Website",
                url=(
                    "https://example.com/"
                ),
            ),
            PresenceLinkButton(
                label="Discord",
                url=(
                    "https://discord.com/"
                ),
            ),
        )

    def test_buttons_are_retained_when_hidden(
        self,
    ):
        payload = PresenceMode(
            mode="custom",
            show_buttons=False,
            buttons=self.make_buttons(),
        ).to_payload()

        self.assertFalse(
            payload[
                "show_buttons"
            ]
        )

        self.assertEqual(
            len(
                payload[
                    "buttons"
                ]
            ),
            2,
        )

    def test_buttons_can_be_enabled(
        self,
    ):
        payload = PresenceMode(
            mode="custom",
            show_buttons=True,
            buttons=self.make_buttons(),
        ).to_payload()

        self.assertTrue(
            payload[
                "show_buttons"
            ]
        )

        self.assertEqual(
            payload[
                "buttons"
            ][0],
            {
                "label": "Website",
                "url": (
                    "https://example.com/"
                ),
            },
        )

    def test_non_custom_editable_modes_can_carry_buttons(
        self,
    ):
        for mode in (
            "afk",
            "sleep",
            "working",
            "custom",
        ):
            with self.subTest(
                mode=mode
            ):
                payload = PresenceMode(
                    mode=mode,
                    show_buttons=True,
                    buttons=(
                        self.make_buttons()[
                            :1
                        ]
                    ),
                ).to_payload()

                self.assertTrue(
                    payload[
                        "show_buttons"
                    ]
                )

                self.assertEqual(
                    len(
                        payload[
                            "buttons"
                        ]
                    ),
                    1,
                )

    def test_music_supports_buttons_and_disabled_suppresses_buttons(
        self,
    ):
        music_payload = PresenceMode(
            mode="music",
            show_buttons=True,
            buttons=self.make_buttons(),
        ).to_payload()

        self.assertTrue(
            music_payload[
                "show_buttons"
            ]
        )

        self.assertEqual(
            len(
                music_payload[
                    "buttons"
                ]
            ),
            2,
        )

        disabled_payload = PresenceMode(
            mode="disabled",
            show_buttons=True,
            buttons=self.make_buttons(),
        ).to_payload()

        self.assertFalse(
            disabled_payload[
                "show_buttons"
            ]
        )

        self.assertEqual(
            disabled_payload[
                "buttons"
            ],
            [],
        )

    def test_invalid_button_data_is_not_silently_published(
        self,
    ):
        mode = PresenceMode(
            mode="custom",
            show_buttons=True,
            buttons=(
                {
                    "label": "Unsafe",
                    "url": "file:///secret",
                },
            ),
        )

        with self.assertRaises(
            PresenceLinkButtonError
        ):
            mode.to_payload()


if __name__ == "__main__":
    unittest.main()
