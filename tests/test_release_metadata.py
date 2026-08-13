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
            "3.0.0",
        )

        self.assertEqual(
            RELEASE_NAME,
            "Overhaul",
        )

        self.assertEqual(
            DISPLAY_VERSION,
            "v3.0.0 - Overhaul",
        )

    def test_windows_version_metadata(self):
        source = Path(
            "version_info.txt"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "filevers=(3, 0, 0, 0)",
            source,
        )

        self.assertIn(
            "prodvers=(3, 0, 0, 0)",
            source,
        )

        self.assertEqual(
            source.count('"3.0.0.0"'),
            2,
        )

        self.assertIn(
            "03:37am Presence - Overhaul",
            source,
        )

    def test_changelog_starts_with_v30(self):
        source = Path(
            "CHANGELOG.md"
        ).read_text(
            encoding="utf-8"
        )

        v30 = source.index(
            "## v3.0.0 - Overhaul"
        )

        v29 = source.index(
            "## v2.9.0 - Spotify Integration"
        )

        self.assertLess(
            v30,
            v29,
        )

        self.assertIn(
            "Released 13 August 2026.",
            source,
        )

        self.assertIn(
            "Settings categories",
            source,
        )

        self.assertIn(
            "custom Discord Application ID",
            source,
        )

        self.assertIn(
            "Spotify playlist track artwork",
            source,
        )

        self.assertIn(
            "audio-reactive Spotify equalizer",
            source,
        )

        self.assertIn(
            "foreground focus",
            source,
        )

    def test_readme_describes_v30(self):
        source = Path(
            "README.MD"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## v3.0.0 highlights",
            source,
        )

        self.assertNotIn(
            "## v2.9.0 highlights",
            source,
        )

        self.assertIn(
            "custom Discord Application ID",
            source,
        )

        self.assertIn(
            "playlist track artwork",
            source,
        )

        self.assertIn(
            "audio-reactive Spotify equalizer",
            source,
        )

        self.assertIn(
            "foreground focus",
            source,
        )

    def test_spotify_user_agent_tracks_v30(self):
        source = Path(
            "src/spotify/web_api.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "03-37am-Presence/3.0 Spotify-Web-API",
            source,
        )

        self.assertNotIn(
            "03-37am-Presence/2.9 Spotify-Web-API",
            source,
        )


if __name__ == "__main__":
    unittest.main()
