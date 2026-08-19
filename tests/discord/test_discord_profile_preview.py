import os
import unittest
from pathlib import Path
from tests.repo_paths import REPO_ROOT

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication

from src.ui.discord_profile_preview import (
    DiscordProfilePreview,
)


class DiscordProfilePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_default_preview_is_safe(self):
        preview = DiscordProfilePreview()

        self.assertEqual(
            preview.profile_name.text(),
            "Discord profile",
        )
        self.assertEqual(
            preview.profile_status.text(),
            "Offline",
        )
        self.assertEqual(
            preview.activity_title.text(),
            "Nothing playing",
        )
        self.assertTrue(
            preview.activity_progress.isHidden()
        )

    def test_profile_identity_can_be_updated(self):
        preview = DiscordProfilePreview()

        preview.set_profile(
            display_name="03:37am",
            username="03.37am",
            status="Idle",
        )

        self.assertEqual(
            preview.profile_name.text(),
            "03:37am",
        )
        self.assertEqual(
            preview.profile_username.text(),
            "03.37am",
        )
        self.assertFalse(
            preview.profile_username.isHidden()
        )
        self.assertEqual(
            preview.profile_status.text(),
            "Idle",
        )
        self.assertEqual(
            preview.profile_avatar.text(),
            "0",
        )

    def test_blank_profile_status_hides_chip(self):
        preview = DiscordProfilePreview()

        preview.set_profile(
            display_name="03:37am",
            username="@03.37am",
            status="",
        )

        self.assertTrue(
            preview.profile_status.isHidden()
        )

    def test_profile_avatar_accepts_pixmap(self):
        preview = DiscordProfilePreview()

        avatar = QPixmap(
            64,
            64,
        )
        avatar.fill()

        preview.set_profile(
            display_name="03:37am",
            avatar=avatar,
        )

        self.assertFalse(
            preview.profile_avatar.pixmap().isNull()
        )
        self.assertEqual(
            preview.profile_avatar.text(),
            "",
        )

    def test_activity_can_render_live_music_values(self):
        preview = DiscordProfilePreview()

        artwork = QPixmap(
            80,
            80,
        )
        artwork.fill()

        preview.set_activity(
            title="Plug",
            artist="Juice WRLD",
            album="Goodbye & Good Riddance (Sessions)",
            time_text="3:40 / 3:58",
            source_label="Spotify",
            application_name="03:37am",
            artwork=artwork,
            progress_percent=94,
        )

        self.assertEqual(
            preview.activity_title.text(),
            "Plug",
        )
        self.assertEqual(
            preview.activity_artist.text(),
            "Juice WRLD",
        )
        self.assertEqual(
            preview.activity_album.text(),
            "Goodbye & Good Riddance (Sessions)",
        )
        self.assertEqual(
            preview.activity_time.text(),
            "3:40 / 3:58",
        )
        self.assertEqual(
            preview.activity_source_badge.text(),
            "SPOTIFY",
        )
        self.assertEqual(
            preview.activity_application.text(),
            "03:37am",
        )
        self.assertEqual(
            preview.activity_progress.value(),
            94,
        )
        self.assertFalse(
            preview.activity_progress.isHidden()
        )
        self.assertFalse(
            preview.activity_artwork.pixmap().isNull()
        )

    def test_optional_activity_fields_hide_cleanly(self):
        preview = DiscordProfilePreview()

        preview.set_activity(
            title="AFK",
            source_label="Presence",
        )

        self.assertTrue(
            preview.activity_artist.isHidden()
        )
        self.assertTrue(
            preview.activity_album.isHidden()
        )
        self.assertTrue(
            preview.activity_time.isHidden()
        )
        self.assertTrue(
            preview.activity_progress.isHidden()
        )

    def test_progress_is_safely_bounded(self):
        preview = DiscordProfilePreview()

        preview.set_activity(
            title="Test",
            progress_percent=500,
        )

        self.assertEqual(
            preview.activity_progress.value(),
            100,
        )

        preview.set_activity(
            title="Test",
            progress_percent=-50,
        )

        self.assertEqual(
            preview.activity_progress.value(),
            0,
        )

    def test_compact_mode_uses_dashboard_geometry(self):
        preview = DiscordProfilePreview()

        preview.set_compact(True)

        self.assertEqual(
            preview.profile_avatar.width(),
            52,
        )
        self.assertEqual(
            preview.activity_artwork.width(),
            58,
        )
        self.assertEqual(
            preview.profile_panel.minimumWidth(),
            105,
        )
        self.assertTrue(
            preview.activity_application.isHidden()
        )

        root_margins = (
            preview.root_layout.contentsMargins()
        )

        self.assertEqual(
            root_margins.left(),
            8,
        )
        self.assertEqual(
            root_margins.top(),
            7,
        )

        body_margins = (
            preview.preview_body_layout.contentsMargins()
        )

        self.assertEqual(
            body_margins.left(),
            8,
        )
        self.assertEqual(
            body_margins.top(),
            8,
        )

    def test_expanded_mode_restores_rich_geometry(self):
        preview = DiscordProfilePreview()

        preview.set_compact(True)
        preview.set_compact(False)

        self.assertEqual(
            preview.profile_avatar.width(),
            88,
        )
        self.assertEqual(
            preview.activity_artwork.width(),
            96,
        )
        self.assertEqual(
            preview.profile_panel.minimumWidth(),
            180,
        )
        self.assertFalse(
            preview.activity_application.isHidden()
        )

    def test_open_button_emits_request(self):
        preview = DiscordProfilePreview()
        requests = []

        preview.open_discord_requested.connect(
            lambda: requests.append(True)
        )

        preview.open_discord_button.click()

        self.assertEqual(
            requests,
            [True],
        )

    def test_widget_owns_no_discord_network_or_credentials(self):
        source = (
            REPO_ROOT
            / "src"
            / "ui"
            / "discord_profile_preview.py"
        ).read_text(
            encoding="utf-8"
        )

        forbidden = (
            "pypresence",
            "requests.",
            "urllib.",
            "src.discord",
            "client_id",
            "access_token",
            "refresh_token",
        )

        for value in forbidden:
            self.assertNotIn(
                value,
                source,
            )


if __name__ == "__main__":
    unittest.main()
