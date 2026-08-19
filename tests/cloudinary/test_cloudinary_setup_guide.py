from __future__ import annotations

import os
from pathlib import Path
import unittest
from tests.repo_paths import REPO_ROOT


os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtWidgets import (
    QApplication,
)

from src.ui.cloudinary_setup_guide import (
    CLOUDINARY_DASHBOARD_URL,
    CLOUDINARY_UPLOAD_PRESETS_DOCS_URL,
    CLOUDINARY_UPLOAD_PRESETS_URL,
    CloudinarySetupGuide,
    cloudinary_setup_checklist,
)


ROOT = REPO_ROOT

CARD_PATH = (
    ROOT
    / "src"
    / "ui"
    / "artwork_hosting_card.py"
)

GUIDE_PATH = (
    ROOT
    / "src"
    / "ui"
    / "cloudinary_setup_guide.py"
)


class CloudinarySetupGuideTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

        cls.card_source = (
            CARD_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

        cls.guide_source = (
            GUIDE_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

    def test_guide_has_five_steps(self):
        self.assertEqual(
            len(
                CloudinarySetupGuide
                .guide_steps()
            ),
            5,
        )

    def test_checklist_contains_required_values(self):
        checklist = (
            cloudinary_setup_checklist()
        )

        self.assertIn(
            "Cloud name",
            checklist,
        )

        self.assertIn(
            "unsigned upload preset",
            checklist,
        )

        self.assertIn(
            "Test connection",
            checklist,
        )

    def test_security_warning_rejects_secrets(self):
        checklist = (
            cloudinary_setup_checklist()
        )

        self.assertIn(
            "Never enter an API key",
            checklist,
        )

        self.assertIn(
            "Never enter an API secret",
            checklist,
        )

        self.assertNotIn(
            "QLineEdit",
            self.guide_source,
        )

    def test_official_cloudinary_links_are_https(self):
        for url in (
            CLOUDINARY_DASHBOARD_URL,
            CLOUDINARY_UPLOAD_PRESETS_URL,
            CLOUDINARY_UPLOAD_PRESETS_DOCS_URL,
        ):
            self.assertTrue(
                url.startswith(
                    "https://"
                )
            )

            self.assertIn(
                "cloudinary.com",
                url,
            )

    def test_links_use_injected_opener(self):
        opened = []

        def opener(url):
            opened.append(
                url.toString()
            )
            return True

        dialog = CloudinarySetupGuide(
            url_opener=opener
        )

        try:
            self.assertTrue(
                dialog.open_dashboard()
            )

            self.assertTrue(
                dialog.open_upload_presets()
            )

            self.assertTrue(
                dialog.open_documentation()
            )

            self.assertEqual(
                opened,
                [
                    CLOUDINARY_DASHBOARD_URL,
                    CLOUDINARY_UPLOAD_PRESETS_URL,
                    (
                        CLOUDINARY_UPLOAD_PRESETS_DOCS_URL
                    ),
                ],
            )

        finally:
            dialog.close()

    def test_card_has_setup_guide_button(self):
        self.assertIn(
            '"Cloudinary setup guide"',
            self.card_source,
        )

        self.assertIn(
            "self.show_setup_guide",
            self.card_source,
        )

        self.assertIn(
            "CloudinarySetupGuide",
            self.card_source,
        )

    def test_guide_does_not_change_preferences(self):
        self.assertNotIn(
            "CloudinaryPreferencesStore",
            self.guide_source,
        )

        self.assertNotIn(
            "preferences_store",
            self.guide_source,
        )

        self.assertNotIn(
            ".save(",
            self.guide_source,
        )

        self.assertNotIn(
            ".update(",
            self.guide_source,
        )

    def test_no_network_request_code_exists(self):
        self.assertNotIn(
            "urllib",
            self.guide_source,
        )

        self.assertNotIn(
            "requests",
            self.guide_source,
        )

        self.assertNotIn(
            "urlopen",
            self.guide_source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
