import unittest
from pathlib import Path

from src.version import (
    APP_VERSION,
    DISPLAY_VERSION,
    RELEASE_NAME,
)


class ReleaseMetadataTests(
    unittest.TestCase
):
    def test_python_version_metadata(
        self,
    ):
        self.assertEqual(
            APP_VERSION,
            "2.6.0",
        )

        self.assertEqual(
            RELEASE_NAME,
            "Library & Insights Update",
        )

        self.assertEqual(
            DISPLAY_VERSION,
            (
                "v2.6.0 - "
                "Library & Insights Update"
            ),
        )

    def test_windows_version_metadata(
        self,
    ):
        source = Path(
            "version_info.txt"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "filevers=(2, 6, 0, 0)",
            source,
        )

        self.assertIn(
            "prodvers=(2, 6, 0, 0)",
            source,
        )

        self.assertEqual(
            source.count('"2.6.0.0"'),
            2,
        )

        self.assertIn(
            (
                "03:37am Presence - "
                "Library & Insights Update"
            ),
            source,
        )

    def test_changelog_starts_with_v26(
        self,
    ):
        source = Path(
            "CHANGELOG.md"
        ).read_text(
            encoding="utf-8"
        )

        v26_position = source.index(
            "## v2.6.0 - Library & Insights Update"
        )

        v25_position = source.index(
            "## v2.5.0 - Control Room Update"
        )

        self.assertLess(
            v26_position,
            v25_position,
        )

        self.assertIn(
            "Released 17 July 2026.",
            source,
        )

        self.assertIn(
            "Detailed timeline tracking begins",
            source,
        )

        self.assertIn(
            "spreadsheet-formula characters",
            source,
        )

    def test_readme_describes_v26(
        self,
    ):
        source = Path(
            "README.MD"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "## v2.6.0 highlights",
            source,
        )

        self.assertNotIn(
            "## v2.5.0 highlights",
            source,
        )

        self.assertIn(
            "Library Summary and Listening Activity CSV",
            source,
        )

        self.assertIn(
            "confirmed activity",
            source,
        )

        self.assertIn(
            "Artwork recovery",
            source,
        )


if __name__ == "__main__":
    unittest.main()
