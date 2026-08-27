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
            "3.2.0",
        )

        self.assertEqual(
            RELEASE_NAME,
            "Playback & Quick Access",
        )

        self.assertEqual(
            DISPLAY_VERSION,
            "v3.2.0 - Playback & Quick Access",
        )

    def test_windows_version_metadata(self):
        source = Path(
            "version_info.txt"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "filevers=(3, 2, 0, 0)",
            source,
        )

        self.assertIn(
            "prodvers=(3, 2, 0, 0)",
            source,
        )

        self.assertEqual(
            source.count('"3.2.0.0"'),
            2,
        )

        self.assertIn(
            "03:37am Presence - Playback & Quick Access",
            source,
        )

    def test_changelog_starts_with_v32(self):
        source = Path(
            "CHANGELOG.md"
        ).read_text(
            encoding="utf-8"
        )

        v32 = source.index(
            "## v3.2.0 - Playback & Quick Access"
        )

        v31 = source.index(
            "## v3.1.0 - Discord Presence Studio"
        )

        self.assertLess(
            v32,
            v31,
        )

        self.assertIn(
            "Released 28 August 2026.",
            source,
        )

        self.assertIn(
            "Dashboard playback control row",
            source,
        )

        self.assertIn(
            "Loop ×N",
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

        self.assertIn(
            "Launcher Cards",
            source,
        )

        self.assertIn(
            "Spotify playlists",
            source,
        )

        self.assertIn(
            "does not start playback automatically",
            source,
        )

    def test_readme_describes_v32(self):
        source = Path(
            "README.MD"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## v3.2.0 highlights",
            source,
        )

        self.assertNotIn(
            "## v3.1.0 highlights",
            source,
        )

        self.assertIn(
            "Dashboard playback row",
            source,
        )

        self.assertIn(
            "Loop ×N",
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

        self.assertIn(
            "Launcher Cards",
            source,
        )

        self.assertIn(
            "Spotify playlists",
            source,
        )

    def test_spotify_user_agent_tracks_v32(self):
        source = Path(
            "src/spotify/web_api.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "03-37am-Presence/3.2.0 Spotify-Web-API",
            source,
        )

        self.assertNotIn(
            "03-37am-Presence/3.1.0 Spotify-Web-API",
            source,
        )


if __name__ == "__main__":
    unittest.main()
