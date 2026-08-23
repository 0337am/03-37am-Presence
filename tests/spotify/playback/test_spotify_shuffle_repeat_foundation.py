from __future__ import annotations

import unittest
from urllib.parse import (
    parse_qs,
    urlsplit,
)

from src.spotify.playback_service import (
    SpotifyPlaybackService,
)
from src.spotify.qt_playback_runtime import (
    SPOTIFY_PLAYBACK_CONTROL_METHODS,
    SpotifyQtPlaybackRuntime,
)
from src.spotify.web_api import (
    SpotifyWebApiClient,
)


DEVICE_ID = (
    "0d1841b0976bae2a3a310dd74c0f3df354899bc8"
)


class WebHarness:
    def __init__(
        self,
    ):
        self.calls = []

    def _request_no_content(
        self,
        url,
        access_token,
        *,
        method,
    ):
        self.calls.append(
            (
                url,
                access_token,
                method,
            )
        )


class ServiceHarness:
    def __init__(
        self,
    ):
        self.calls = []

    def _run_transport_control(
        self,
        *args,
    ):
        self.calls.append(
            args
        )
        return "ready"

    def _error(
        self,
        error_code,
        message,
        **kwargs,
    ):
        del kwargs
        return (
            "error",
            error_code,
            message,
        )


class RuntimeHarness:
    def __init__(
        self,
    ):
        self.calls = []

    def _start_control(
        self,
        control_name,
        *,
        control_argument=None,
    ):
        self.calls.append(
            (
                control_name,
                control_argument,
            )
        )


class SpotifyShuffleRepeatFoundationTests(
    unittest.TestCase
):
    def test_web_shuffle_contract_and_device(
        self,
    ):
        first = WebHarness()

        SpotifyWebApiClient.set_shuffle(
            first,
            "token",
            True,
        )

        url, token, method = first.calls[0]

        parsed = urlsplit(
            url
        )

        self.assertTrue(
            parsed.path.endswith(
                "/me/player/shuffle"
            )
        )

        self.assertEqual(
            parse_qs(
                parsed.query
            ).get(
                "state"
            ),
            [
                "true",
            ],
        )

        self.assertEqual(
            token,
            "token",
        )

        self.assertEqual(
            method,
            "PUT",
        )

        second = WebHarness()

        SpotifyWebApiClient.set_shuffle(
            second,
            "token",
            False,
            device_id=DEVICE_ID,
        )

        query = parse_qs(
            urlsplit(
                second.calls[0][0]
            ).query
        )

        self.assertEqual(
            query.get(
                "state"
            ),
            [
                "false",
            ],
        )

        self.assertEqual(
            query.get(
                "device_id"
            ),
            [
                DEVICE_ID,
            ],
        )

    def test_web_shuffle_rejects_non_boolean(
        self,
    ):
        harness = WebHarness()

        with self.assertRaises(
            TypeError
        ):
            SpotifyWebApiClient.set_shuffle(
                harness,
                "token",
                1,
            )

        self.assertEqual(
            harness.calls,
            [],
        )

    def test_web_repeat_contract_for_all_modes(
        self,
    ):
        for mode in (
            "off",
            "context",
            "track",
        ):
            with self.subTest(
                mode=mode
            ):
                harness = WebHarness()

                SpotifyWebApiClient.set_repeat_mode(
                    harness,
                    "token",
                    mode,
                    device_id=DEVICE_ID,
                )

                url, token, method = harness.calls[0]

                parsed = urlsplit(
                    url
                )

                self.assertTrue(
                    parsed.path.endswith(
                        "/me/player/repeat"
                    )
                )

                query = parse_qs(
                    parsed.query
                )

                self.assertEqual(
                    query.get(
                        "state"
                    ),
                    [
                        mode,
                    ],
                )

                self.assertEqual(
                    query.get(
                        "device_id"
                    ),
                    [
                        DEVICE_ID,
                    ],
                )

                self.assertEqual(
                    token,
                    "token",
                )

                self.assertEqual(
                    method,
                    "PUT",
                )

    def test_web_repeat_rejects_invalid_modes(
        self,
    ):
        harness = WebHarness()

        for invalid in (
            "playlist",
            " context ",
        ):
            with self.subTest(
                invalid=invalid
            ):
                with self.assertRaises(
                    ValueError
                ):
                    SpotifyWebApiClient.set_repeat_mode(
                        harness,
                        "token",
                        invalid,
                    )

        with self.assertRaises(
            TypeError
        ):
            SpotifyWebApiClient.set_repeat_mode(
                harness,
                "token",
                True,
            )

        self.assertEqual(
            harness.calls,
            [],
        )

    def test_service_shuffle_routes_argument(
        self,
    ):
        harness = ServiceHarness()

        result = SpotifyPlaybackService.set_shuffle(
            harness,
            True,
        )

        self.assertEqual(
            result,
            "ready",
        )

        self.assertEqual(
            harness.calls,
            [
                (
                    "set_shuffle",
                    "Spotify shuffle was updated.",
                    True,
                ),
            ],
        )

    def test_service_repeat_routes_argument(
        self,
    ):
        harness = ServiceHarness()

        result = SpotifyPlaybackService.set_repeat_mode(
            harness,
            "track",
        )

        self.assertEqual(
            result,
            "ready",
        )

        self.assertEqual(
            harness.calls,
            [
                (
                    "set_repeat_mode",
                    (
                        "Spotify repeat mode "
                        "was updated."
                    ),
                    "track",
                ),
            ],
        )

    def test_service_rejects_invalid_states(
        self,
    ):
        shuffle = ServiceHarness()

        result = SpotifyPlaybackService.set_shuffle(
            shuffle,
            1,
        )

        self.assertEqual(
            result[0:2],
            (
                "error",
                "invalid_shuffle_state",
            ),
        )

        self.assertEqual(
            shuffle.calls,
            [],
        )

        for invalid in (
            "playlist",
            " track ",
            True,
        ):
            with self.subTest(
                invalid=invalid
            ):
                repeat = ServiceHarness()

                result = SpotifyPlaybackService.set_repeat_mode(
                    repeat,
                    invalid,
                )

                self.assertEqual(
                    result[0:2],
                    (
                        "error",
                        "invalid_repeat_mode",
                    ),
                )

                self.assertEqual(
                    repeat.calls,
                    [],
                )

    def test_runtime_registry_contains_controls(
        self,
    ):
        self.assertIn(
            "seek_to_seconds",
            SPOTIFY_PLAYBACK_CONTROL_METHODS,
        )

        self.assertIn(
            "set_shuffle",
            SPOTIFY_PLAYBACK_CONTROL_METHODS,
        )

        self.assertIn(
            "set_repeat_mode",
            SPOTIFY_PLAYBACK_CONTROL_METHODS,
        )

    def test_runtime_shuffle_routes_argument(
        self,
    ):
        harness = RuntimeHarness()

        SpotifyQtPlaybackRuntime.set_shuffle(
            harness,
            True,
        )

        self.assertEqual(
            harness.calls,
            [
                (
                    "set_shuffle",
                    True,
                ),
            ],
        )

        with self.assertRaises(
            TypeError
        ):
            SpotifyQtPlaybackRuntime.set_shuffle(
                harness,
                1,
            )

    def test_runtime_repeat_routes_and_validates(
        self,
    ):
        harness = RuntimeHarness()

        SpotifyQtPlaybackRuntime.set_repeat_mode(
            harness,
            "context",
        )

        self.assertEqual(
            harness.calls,
            [
                (
                    "set_repeat_mode",
                    "context",
                ),
            ],
        )

        with self.assertRaises(
            ValueError
        ):
            SpotifyQtPlaybackRuntime.set_repeat_mode(
                harness,
                " context ",
            )

        with self.assertRaises(
            TypeError
        ):
            SpotifyQtPlaybackRuntime.set_repeat_mode(
                harness,
                True,
            )


if __name__ == "__main__":
    unittest.main()
