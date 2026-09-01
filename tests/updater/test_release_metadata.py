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
            "3.2.2",
        )

        self.assertEqual(
            RELEASE_NAME,
            "Window & Tray Fixes",
        )

        self.assertEqual(
            DISPLAY_VERSION,
            "v3.2.2 - Window & Tray Fixes",
        )

    def test_windows_version_metadata(self):
        source = Path(
            "version_info.txt"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "filevers=(3, 2, 2, 0)",
            source,
        )

        self.assertIn(
            "prodvers=(3, 2, 2, 0)",
            source,
        )

        self.assertEqual(
            source.count('"3.2.2.0"'),
            2,
        )

        self.assertIn(
            "03:37am Presence - Window & Tray Fixes",
            source,
        )

    def test_changelog_starts_with_v322(self):
        source = Path(
            "CHANGELOG.md"
        ).read_text(
            encoding="utf-8"
        )

        v322 = source.index(
            "## v3.2.2 - Window & Tray Fixes"
        )

        v321 = source.index(
            "## v3.2.1 - Custom Presence Party"
        )

        self.assertLess(
            v322,
            v321,
        )

        self.assertIn(
            "Released 1 September 2026.",
            source,
        )

        self.assertIn(
            "recreated Qt window handle",
            source,
        )

        self.assertIn(
            "close button (`X`)",
            source,
        )

        self.assertIn(
            "Tray -> Hide window",
            source,
        )

        self.assertIn(
            "Startup hide suppression",
            source,
        )

        self.assertIn(
            "phantom-window protection",
            source,
        )

        self.assertIn(
            "Normal Windows taskbar minimize behavior is unchanged",
            source,
        )

        self.assertIn(
            "## v3.2.1 - Custom Presence Party",
            source,
        )

        self.assertIn(
            "Party / Group",
            source,
        )

        self.assertIn(
            "native Rich Presence party-size metadata",
            source,
        )

        self.assertIn(
            "Spotify Queue",
            source,
        )

        self.assertIn(
            "Quick Access 2.0",
            source,
        )

    def test_readme_describes_v322(self):
        source = Path(
            "README.MD"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## v3.2.2 highlights",
            source,
        )

        self.assertIn(
            "main-window startup handoff",
            source,
        )

        self.assertIn(
            "close button (`X`)",
            source,
        )

        self.assertIn(
            "Tray -> Hide window",
            source,
        )

        self.assertIn(
            "Tray -> Open",
            source,
        )

        self.assertIn(
            "Tray -> Quit",
            source,
        )

        self.assertIn(
            "Normal Windows taskbar minimize behavior remains unchanged",
            source,
        )

        self.assertIn(
            "### v3.2.1 feature highlights",
            source,
        )

        self.assertIn(
            "Party / Group",
            source,
        )

        self.assertIn(
            "`(x of y)` member count",
            source,
        )

        self.assertIn(
            "Dashboard playback row",
            source,
        )

        self.assertIn(
            "Spotify Queue",
            source,
        )

        self.assertIn(
            "Quick Access 2.0",
            source,
        )

    def test_spotify_user_agent_tracks_v322(self):
        source = Path(
            "src/spotify/web_api.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "03-37am-Presence/3.2.2 Spotify-Web-API",
            source,
        )

        self.assertNotIn(
            "03-37am-Presence/3.2.1 Spotify-Web-API",
            source,
        )


if __name__ == "__main__":
    unittest.main()
