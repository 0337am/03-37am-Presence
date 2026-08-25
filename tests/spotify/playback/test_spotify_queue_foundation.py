from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from src.spotify.web_api import (
    SPOTIFY_API_BASE_URL,
    SpotifyWebApiClient,
)


class SpotifyQueueWebApiFoundationTests(
    unittest.TestCase
):
    @staticmethod
    def make_client():
        return SpotifyWebApiClient(
            urlopen=(
                lambda *args, **kwargs:
                None
            )
        )

    def test_get_queue_uses_player_queue_endpoint(
        self,
    ):
        client = self.make_client()
        payload = {
            "currently_playing": None,
            "queue": [],
        }

        with patch.object(
            client,
            "get_json",
            return_value=payload,
        ) as getter:
            result = client.get_queue(
                "test-access-token"
            )

        self.assertIs(
            result,
            payload,
        )
        getter.assert_called_once_with(
            "test-access-token",
            "/me/player/queue",
        )

    def test_add_track_to_queue_posts_encoded_uri(
        self,
    ):
        client = self.make_client()

        with patch.object(
            client,
            "_request_no_content",
        ) as request:
            client.add_to_queue(
                "test-access-token",
                "spotify:track:track123",
            )

        request.assert_called_once()

        url = request.call_args.args[0]
        token = request.call_args.args[1]
        parsed = urlsplit(url)

        self.assertEqual(
            (
                parsed.scheme
                + "://"
                + parsed.netloc
                + parsed.path
            ),
            (
                SPOTIFY_API_BASE_URL
                + "/me/player/queue"
            ),
        )
        self.assertEqual(
            parse_qs(parsed.query),
            {
                "uri": [
                    "spotify:track:track123",
                ],
            },
        )
        self.assertIn(
            "spotify%3Atrack%3Atrack123",
            parsed.query,
        )
        self.assertEqual(
            token,
            "test-access-token",
        )
        self.assertEqual(
            request.call_args.kwargs,
            {
                "method": "POST",
            },
        )

    def test_add_episode_to_queue_is_supported(
        self,
    ):
        client = self.make_client()

        with patch.object(
            client,
            "_request_no_content",
        ) as request:
            client.add_to_queue(
                "test-access-token",
                "spotify:episode:episode456",
            )

        parsed = urlsplit(
            request.call_args.args[0]
        )

        self.assertEqual(
            parse_qs(parsed.query),
            {
                "uri": [
                    "spotify:episode:episode456",
                ],
            },
        )
        self.assertEqual(
            request.call_args.kwargs,
            {
                "method": "POST",
            },
        )

    def test_add_to_queue_supports_optional_device_id(
        self,
    ):
        client = self.make_client()

        with patch.object(
            client,
            "_request_no_content",
        ) as request:
            client.add_to_queue(
                "test-access-token",
                "spotify:track:track123",
                device_id="device789",
            )

        parsed = urlsplit(
            request.call_args.args[0]
        )

        self.assertEqual(
            parse_qs(parsed.query),
            {
                "uri": [
                    "spotify:track:track123",
                ],
                "device_id": [
                    "device789",
                ],
            },
        )

    def test_invalid_queue_item_uris_are_rejected_before_request(
        self,
    ):
        client = self.make_client()

        invalid = (
            "spotify:album:album123",
            "spotify:track:",
            "spotify:episode:",
            " spotify:track:track123",
            "spotify:track:track123 ",
            "spotify:local:Artist:Album:Song:180",
            "spotify:track:bad-id",
        )

        with patch.object(
            client,
            "_request_no_content",
        ) as request:
            for value in invalid:
                with self.subTest(
                    value=value
                ):
                    with self.assertRaises(
                        ValueError
                    ):
                        client.add_to_queue(
                            "test-access-token",
                            value,
                        )

        request.assert_not_called()

    def test_queue_item_uri_type_is_validated_before_request(
        self,
    ):
        client = self.make_client()

        with patch.object(
            client,
            "_request_no_content",
        ) as request:
            for value in (
                None,
                123,
                object(),
            ):
                with self.subTest(
                    value=type(
                        value
                    ).__name__
                ):
                    with self.assertRaises(
                        TypeError
                    ):
                        client.add_to_queue(
                            "test-access-token",
                            value,
                        )

        request.assert_not_called()

    def test_device_id_type_is_validated_before_request(
        self,
    ):
        client = self.make_client()

        with patch.object(
            client,
            "_request_no_content",
        ) as request:
            with self.assertRaises(
                TypeError
            ):
                client.add_to_queue(
                    "test-access-token",
                    "spotify:track:track123",
                    device_id=123,
                )

        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
