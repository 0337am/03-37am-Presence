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
            "3.4.0",
        )

        self.assertEqual(
            RELEASE_NAME,
            "Multi-Presence",
        )

        self.assertEqual(
            DISPLAY_VERSION,
            "v3.4.0 - Multi-Presence",
        )

    def test_windows_version_metadata(self):
        source = Path(
            "version_info.txt"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "filevers=(3, 4, 0, 0)",
            source,
        )

        self.assertIn(
            "prodvers=(3, 4, 0, 0)",
            source,
        )

        self.assertEqual(
            source.count('"3.4.0.0"'),
            2,
        )

        self.assertIn(
            "03:37am Presence - Multi-Presence",
            source,
        )

    def test_changelog_starts_with_v340(self):
        source = Path(
            "CHANGELOG.md"
        ).read_text(
            encoding="utf-8"
        )

        v340 = source.index(
            "## v3.4.0 - Multi-Presence"
        )

        v330 = source.index(
            "## v3.3.0 - Desktop Companion"
        )

        self.assertLess(
            v340,
            v330,
        )

        required = (
            "Released 4 September 2026.",
            "Discord Application Library",
            "per-Presence Discord Application assignment",
            "Music + Secondary Presence",
            "Apply as Secondary",
            "Settings Backup and Restore",
            "artwork hover text",
            "Auto AFK",
            "duplicate Discord Application IDs",
            "public Application IDs only",
        )

        for value in required:
            self.assertIn(
                value,
                source,
            )

    def test_readme_describes_v340(self):
        source = Path(
            "README.MD"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## v3.4.0 highlights",
            source,
        )

        self.assertNotIn(
            "## v3.3.0 highlights",
            source,
        )

        required = (
            "Discord Application Library",
            "Per-Presence applications",
            "Music + Secondary Presence",
            "Presence Studio controls",
            "Settings Backup and Restore",
            "Artwork hover text",
            "Auto AFK",
            "public Discord Application IDs",
        )

        for value in required:
            self.assertIn(
                value,
                source,
            )

    def test_spotify_user_agent_tracks_v340(self):
        source = Path(
            "src/spotify/web_api.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "03-37am-Presence/3.4.0 Spotify-Web-API",
            source,
        )

        self.assertNotIn(
            "03-37am-Presence/3.3.0 Spotify-Web-API",
            source,
        )


if __name__ == "__main__":
    unittest.main()
