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
            "2.8.0",
        )

        self.assertEqual(
            RELEASE_NAME,
            "First-Run Polish",
        )

        self.assertEqual(
            DISPLAY_VERSION,
            "v2.8.0 - First-Run Polish",
        )

    def test_windows_version_metadata(self):
        source = Path(
            "version_info.txt"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "filevers=(2, 8, 0, 0)",
            source,
        )

        self.assertIn(
            "prodvers=(2, 8, 0, 0)",
            source,
        )

        self.assertEqual(
            source.count('"2.8.0.0"'),
            2,
        )

        self.assertIn(
            "03:37am Presence - First-Run Polish",
            source,
        )

    def test_changelog_starts_with_v28(self):
        source = Path(
            "CHANGELOG.md"
        ).read_text(
            encoding="utf-8"
        )

        v28 = source.index(
            "## v2.8.0 - First-Run Polish"
        )

        v27 = source.index(
            "## v2.7.0 - Updates & Distribution"
        )

        self.assertLess(
            v28,
            v27,
        )

        self.assertIn(
            "configurable global media hotkeys",
            source,
        )

        self.assertIn(
            "first-run Welcome experience",
            source,
        )

        self.assertIn(
            "honor `--minimized`",
            source,
        )

        self.assertIn(
            "does not automatically enable global hotkeys",
            source,
        )

    def test_readme_describes_v28(self):
        source = Path(
            "README.MD"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## v2.8.0 highlights",
            source,
        )

        self.assertNotIn(
            "## v2.7.0 highlights",
            source,
        )

        self.assertIn(
            "optional global media controls",
            source,
        )

        self.assertIn(
            "hotkeys disabled by default",
            source,
        )

        self.assertIn(
            "first-launch Welcome experience",
            source,
        )

        self.assertIn(
            "silent migration",
            source,
        )

        self.assertIn(
            "No automatic enabling of hotkeys",
            source,
        )


if __name__ == "__main__":
    unittest.main()
