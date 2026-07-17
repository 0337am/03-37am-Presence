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
            "2.7.0",
        )

        self.assertEqual(
            RELEASE_NAME,
            "Updates & Distribution",
        )

        self.assertEqual(
            DISPLAY_VERSION,
            "v2.7.0 - Updates & Distribution",
        )

    def test_windows_version_metadata(self):
        source = Path(
            "version_info.txt"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "filevers=(2, 7, 0, 0)",
            source,
        )

        self.assertIn(
            "prodvers=(2, 7, 0, 0)",
            source,
        )

        self.assertEqual(
            source.count('"2.7.0.0"'),
            2,
        )

        self.assertIn(
            "03:37am Presence - Updates & Distribution",
            source,
        )

    def test_changelog_starts_with_v27(self):
        source = Path(
            "CHANGELOG.md"
        ).read_text(
            encoding="utf-8"
        )

        v27 = source.index(
            "## v2.7.0 - Updates & Distribution"
        )

        v26 = source.index(
            "## v2.6.0 - Library & Insights Update"
        )

        self.assertLess(
            v27,
            v26,
        )

        self.assertIn(
            "Status: Release rehearsal.",
            source,
        )

        self.assertIn(
            "mandatory SHA-256 verification",
            source,
        )

        self.assertIn(
            "guided Cloudinary setup dialog",
            source,
        )

    def test_readme_describes_v27(self):
        source = Path(
            "README.MD"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## v2.7.0 highlights",
            source,
        )

        self.assertNotIn(
            "## v2.6.0 highlights",
            source,
        )

        self.assertIn(
            "published SHA-256 checksum",
            source,
        )

        self.assertIn(
            "explicit approval",
            source,
        )

        self.assertIn(
            "guided Cloudinary setup",
            source,
        )

        self.assertIn(
            "No silent installs",
            source,
        )


if __name__ == "__main__":
    unittest.main()
