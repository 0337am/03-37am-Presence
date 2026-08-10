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
            "2.9.0",
        )

        self.assertEqual(
            RELEASE_NAME,
            "Spotify Integration",
        )

        self.assertEqual(
            DISPLAY_VERSION,
            "v2.9.0 - Spotify Integration",
        )

    def test_windows_version_metadata(self):
        source = Path(
            "version_info.txt"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "filevers=(2, 9, 0, 0)",
            source,
        )

        self.assertIn(
            "prodvers=(2, 9, 0, 0)",
            source,
        )

        self.assertEqual(
            source.count('"2.9.0.0"'),
            2,
        )

        self.assertIn(
            "03:37am Presence - Spotify Integration",
            source,
        )

    def test_changelog_starts_with_v29(self):
        source = Path(
            "CHANGELOG.md"
        ).read_text(
            encoding="utf-8"
        )

        v29 = source.index(
            "## v2.9.0 - Spotify Integration"
        )

        v28 = source.index(
            "## v2.8.0 - First-Run Polish"
        )

        self.assertLess(
            v29,
            v28,
        )

        self.assertIn(
            "Released 10 August 2026.",
            source,
        )

        self.assertIn(
            "Spotify Search",
            source,
        )

        self.assertIn(
            "Liked Songs",
            source,
        )

        self.assertIn(
            "Spotify UI automation",
            source,
        )

        self.assertIn(
            "foreground focus",
            source,
        )

    def test_readme_describes_v29(self):
        source = Path(
            "README.MD"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## v2.9.0 highlights",
            source,
        )

        self.assertNotIn(
            "## v2.8.0 highlights",
            source,
        )

        self.assertIn(
            "Spotify Search",
            source,
        )

        self.assertIn(
            "Liked Songs",
            source,
        )

        self.assertIn(
            "Load more results",
            source,
        )

        self.assertIn(
            "foreground focus",
            source,
        )


if __name__ == "__main__":
    unittest.main()
