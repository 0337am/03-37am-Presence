from __future__ import annotations

import unittest
from dataclasses import dataclass, field

from src.spotify.desktop_playback_bridge import (
    SpotifyDesktopDiscoveryStatus,
    SpotifyDesktopPlaybackBridge,
)


BUTTON = 50000
GRID = 50028
DATA_ITEM = 50029
TEXT = 50020


@dataclass
class FakeElement:
    name: str
    control_type: int
    children: list = field(
        default_factory=list
    )
    invoke: bool = False


class FakeBackend:
    def __init__(
        self,
        root,
        *,
        hwnd=123,
        fail=False,
    ):
        self.root = root
        self.hwnd = hwnd
        self.fail = fail

    def find_spotify_window(
        self,
    ):
        if self.fail:
            raise RuntimeError(
                "simulated backend failure"
            )

        return self.hwnd

    def root_from_handle(
        self,
        hwnd,
    ):
        return self.root

    def iter_descendants(
        self,
        root,
    ):
        stack = list(
            reversed(
                root.children
            )
        )

        while stack:
            element = stack.pop()

            yield element

            stack.extend(
                reversed(
                    element.children
                )
            )

    def name(
        self,
        element,
    ):
        return element.name

    def control_type(
        self,
        element,
    ):
        return element.control_type

    def supports_invoke(
        self,
        element,
    ):
        return element.invoke


def tree(
    *,
    playlist_name="WGC Forever",
    button_name=(
        "Play CELLOPHANE by WesGhost"
    ),
    invoke=True,
    include_playlist=True,
    include_button=True,
    outside_button=False,
    now_playing=False,
):
    playlist_children = []

    if include_button:
        playlist_children.append(
            FakeElement(
                button_name,
                BUTTON,
                invoke=invoke,
            )
        )

    children = []

    if outside_button:
        children.append(
            FakeElement(
                "Play CELLOPHANE by WesGhost",
                BUTTON,
                invoke=True,
            )
        )

    if include_playlist:
        children.append(
            FakeElement(
                playlist_name,
                GRID,
                children=playlist_children,
            )
        )

    if now_playing:
        children.append(
            FakeElement(
                (
                    "Now playing: "
                    "CELLOPHANE by WesGhost"
                ),
                TEXT,
            )
        )

    return FakeElement(
        "Spotify Premium",
        50032,
        children=children,
    )


class SpotifyDesktopPlaybackBridgeTests(
    unittest.TestCase
):
    def bridge(
        self,
        root=None,
        **backend_options,
    ):
        if root is None:
            root = tree()

        return SpotifyDesktopPlaybackBridge(
            FakeBackend(
                root,
                **backend_options,
            )
        )

    def discover(
        self,
        bridge=None,
        **overrides,
    ):
        if bridge is None:
            bridge = self.bridge()

        arguments = {
            "playlist_name": (
                "WGC Forever"
            ),
            "title": "CELLOPHANE",
            "artist": "WesGhost",
        }

        arguments.update(
            overrides
        )

        return (
            bridge.discover_local_track(
                **arguments
            )
        )

    def test_ready_when_exact_semantic_button_exists(
        self,
    ):
        result = self.discover()

        self.assertTrue(
            result.ready
        )

        self.assertEqual(
            result.status,
            SpotifyDesktopDiscoveryStatus.READY,
        )

        self.assertEqual(
            result.button_name,
            "Play CELLOPHANE by WesGhost",
        )

        self.assertFalse(
            result.already_playing
        )

    def test_now_playing_marker_is_reported(
        self,
    ):
        result = self.discover(
            self.bridge(
                tree(
                    now_playing=True
                )
            )
        )

        self.assertTrue(
            result.now_playing_confirmed
        )

    def test_pause_button_means_track_is_already_playing(
        self,
    ):
        result = self.discover(
            self.bridge(
                tree(
                    button_name=(
                        "Pause CELLOPHANE "
                        "by WesGhost"
                    ),
                    invoke=False,
                )
            )
        )

        self.assertTrue(
            result.ready
        )

        self.assertTrue(
            result.already_playing
        )

    def test_button_outside_playlist_is_ignored(
        self,
    ):
        result = self.discover(
            self.bridge(
                tree(
                    include_button=False,
                    outside_button=True,
                )
            )
        )

        self.assertEqual(
            result.status,
            (
                SpotifyDesktopDiscoveryStatus
                .PLAY_CONTROL_NOT_FOUND
            ),
        )

    def test_missing_spotify_window_is_safe(
        self,
    ):
        result = self.discover(
            self.bridge(
                hwnd=None
            )
        )

        self.assertEqual(
            result.status,
            (
                SpotifyDesktopDiscoveryStatus
                .SPOTIFY_NOT_FOUND
            ),
        )

    def test_missing_playlist_is_safe(
        self,
    ):
        result = self.discover(
            self.bridge(
                tree(
                    include_playlist=False
                )
            )
        )

        self.assertEqual(
            result.status,
            (
                SpotifyDesktopDiscoveryStatus
                .PLAYLIST_NOT_FOUND
            ),
        )

    def test_missing_play_control_is_safe(
        self,
    ):
        result = self.discover(
            self.bridge(
                tree(
                    include_button=False
                )
            )
        )

        self.assertEqual(
            result.status,
            (
                SpotifyDesktopDiscoveryStatus
                .PLAY_CONTROL_NOT_FOUND
            ),
        )

    def test_non_invokable_play_control_is_rejected(
        self,
    ):
        result = self.discover(
            self.bridge(
                tree(
                    invoke=False
                )
            )
        )

        self.assertEqual(
            result.status,
            (
                SpotifyDesktopDiscoveryStatus
                .PLAY_CONTROL_UNAVAILABLE
            ),
        )

    def test_backend_failure_is_user_safe(
        self,
    ):
        result = self.discover(
            self.bridge(
                fail=True
            )
        )

        self.assertEqual(
            result.status,
            SpotifyDesktopDiscoveryStatus.ERROR,
        )

    def test_multi_artist_semantic_name_is_supported(
        self,
    ):
        root = tree(
            button_name=(
                "Play CHOKEHOLD by "
                "WesGhost, Resentvul"
            )
        )

        result = self.discover(
            self.bridge(
                root
            ),
            title="CHOKEHOLD",
            artist=(
                "WesGhost, Resentvul"
            ),
        )

        self.assertTrue(
            result.ready
        )

    def test_playlist_name_must_be_nonempty(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            self.discover(
                playlist_name=""
            )

    def test_track_identity_must_be_nonempty(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            self.discover(
                title=""
            )

        with self.assertRaises(
            ValueError
        ):
            self.discover(
                artist=""
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
