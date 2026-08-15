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
            "3.1.0",
        )

        self.assertEqual(
            RELEASE_NAME,
            "Discord Presence Studio",
        )

        self.assertEqual(
            DISPLAY_VERSION,
            "v3.1.0 - Discord Presence Studio",
        )

    def test_windows_version_metadata(self):
        source = Path(
            "version_info.txt"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "filevers=(3, 1, 0, 0)",
            source,
        )

        self.assertIn(
            "prodvers=(3, 1, 0, 0)",
            source,
        )

        self.assertEqual(
            source.count('"3.1.0.0"'),
            2,
        )

        self.assertIn(
            "03:37am Presence - Discord Presence Studio",
            source,
        )

    def test_changelog_starts_with_v31(self):
        source = Path(
            "CHANGELOG.md"
        ).read_text(
            encoding="utf-8"
        )

        v31 = source.index(
            "## v3.1.0 - Discord Presence Studio"
        )

        v301 = source.index(
            "## v3.0.1 - Updater Relaunch Fix"
        )

        self.assertLess(
            v31,
            v301,
        )

        self.assertIn(
            "Released 15 August 2026.",
            source,
        )

        self.assertIn(
            "Discord profile and activity preview",
            source,
        )

        self.assertIn(
            "Presence Studio",
            source,
        )

        self.assertIn(
            "Rich Presence Link Buttons",
            source,
        )

        self.assertIn(
            "Show on Discord",
            source,
        )

        self.assertIn(
            "HTTP or HTTPS URLs",
            source,
        )

        self.assertIn(
            "Disabled Presence",
            source,
        )

    def test_readme_describes_v31(self):
        source = Path(
            "README.MD"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## v3.1.0 highlights",
            source,
        )

        self.assertNotIn(
            "## v3.0.1 highlights",
            source,
        )

        self.assertIn(
            "Presence Studio",
            source,
        )

        self.assertIn(
            "Discord profile and activity preview",
            source,
        )

        self.assertIn(
            "Rich Presence Link Buttons",
            source,
        )

        self.assertIn(
            "Show on Discord",
            source,
        )

    def test_spotify_user_agent_tracks_v31(self):
        source = Path(
            "src/spotify/web_api.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "03-37am-Presence/3.1.0 Spotify-Web-API",
            source,
        )

        self.assertNotIn(
            "03-37am-Presence/3.0.1 Spotify-Web-API",
            source,
        )


if __name__ == "__main__":
    unittest.main()
