import unittest
from pathlib import Path

from src.version import (
    APP_VERSION,
    DISPLAY_VERSION,
    RELEASE_NAME,
)


class ReleaseMetadataTests(unittest.TestCase):

    def test_python_version_metadata(self):
        self.assertEqual(
            APP_VERSION,
            "3.5.0",
        )

        self.assertEqual(
            RELEASE_NAME,
            "Playlist Cards & Chromatic Dashboard",
        )

        self.assertEqual(
            DISPLAY_VERSION,
            "v3.5.0 - Playlist Cards & Chromatic Dashboard",
        )


    def test_windows_version_metadata(self):
        source = Path(
            "version_info.txt"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "filevers=(3, 5, 0, 0)",
            source,
        )

        self.assertIn(
            "prodvers=(3, 5, 0, 0)",
            source,
        )

        self.assertEqual(
            source.count('"3.5.0.0"'),
            2,
        )

        self.assertIn(
            "03:37am Presence - Playlist Cards & Chromatic Dashboard",
            source,
        )


    def test_changelog_starts_with_v341(self):
        source = Path(
            "CHANGELOG.md"
        ).read_text(
            encoding="utf-8"
        )

        v341 = source.index(
            "## v3.5.0 - Playlist Cards & Chromatic Dashboard"
        )

        v340 = source.index(
            "## v3.4.0 - Multi-Presence"
        )

        self.assertLess(
            v341,
            v340,
        )

        section = source[v341:v340]

        required = (
            "Released 8 September 2026.",
            "Secondary Presence is now persistent",
            "Auto AFK",
            "Clear Secondary",
            "Disabled",
            "Settings category navigation",
            "fail closed",
            "Spotify playback",
        )

        for expected in required:
            self.assertIn(
                expected,
                section,
            )


    def test_readme_describes_v341(self):
        source = Path(
            "README.MD"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## v3.5.0 highlights",
            source,
        )

        self.assertNotIn(
            "## v3.4.0 highlights",
            source,
        )

        required = (
            "focused stability update",
            "Secondary Presence",
            "Auto AFK",
            "Clear Secondary",
            "Disabled",
            "Settings categories",
            "local-file playback safety",
        )

        for expected in required:
            self.assertIn(
                expected,
                source,
            )


    def test_spotify_user_agent_tracks_v341(self):
        source = Path(
            "src/spotify/web_api.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "03-37am-Presence/3.5.0 Spotify-Web-API",
            source,
        )

        self.assertNotIn(
            "03-37am-Presence/3.4.0 Spotify-Web-API",
            source,
        )


if __name__ == "__main__":
    unittest.main()
